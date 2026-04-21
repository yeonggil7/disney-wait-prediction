"""
Instagram Reels 用 30秒(*) 動画生成モジュール

「30秒で分かる明日のディズニー混雑予報」コンセプトで、
24時間スロットの予測待ち時間を バーチャートレース 風にアニメーション化する。

(*) 厳密には 5〜90秒の範囲で `--duration` 指定可能。デフォルト 20s。

依存:
- matplotlib (フレーム描画)
- ffmpeg     (mp4 エンコード / 静音AACトラック)

出力:
- predictions_x/ig_reel_{park}_{date}.mp4
- predictions_x/ig_reel_{park}_{date}_cover.png  (Reels タブ用カバー画像)
"""

import os
import shutil
import tempfile
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

from generate_x_heatmap import (
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    get_sea_closures,
    get_land_closures,
    get_day_of_week_ja,
)
from generate_instagram_heatmap import (
    SEA_SHORT_DISPLAY,
    LAND_SHORT_DISPLAY,
    LIGHT_BG,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    PARK_THEMES,
)
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3

try:
    from generate_bgm import generate_bgm_wav  # noqa
    _BGM_AVAILABLE = True
except Exception as e:  # pragma: no cover
    _BGM_AVAILABLE = False
    print(f"⚠️ generate_bgm が読み込めませんでした: {e}")


# 日本語フォント
_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']

FPS = 24
INTRO_SEC = 2
OUTRO_SEC = 3

# bgm/ ディレクトリにユーザが配置した音源があれば優先
_BGM_DIR = os.path.join(os.path.dirname(__file__), 'bgm')
_BGM_AUDIO_EXTS = ('.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg')


def _resolve_bgm(bgm: str, park: str, duration: float, tmpdir: str):
    """
    BGM パスを決定する。

    - 'none' (大文字小文字無視) なら None
    - 'auto' なら:
        1. bgm/{park}.* があれば使う
        2. bgm/default.* があれば使う
        3. なければ generate_bgm でその場生成
    - それ以外は当該パスのファイルが存在するかチェックして返す
    """
    if not bgm or bgm.lower() == 'none':
        return None

    if bgm.lower() == 'auto':
        # 1) park 専用ファイル
        for ext in _BGM_AUDIO_EXTS:
            candidate = os.path.join(_BGM_DIR, f"{park}{ext}")
            if os.path.exists(candidate):
                return candidate
        # 2) default ファイル
        for ext in _BGM_AUDIO_EXTS:
            candidate = os.path.join(_BGM_DIR, f"default{ext}")
            if os.path.exists(candidate):
                return candidate
        # 3) 自動生成
        if not _BGM_AVAILABLE:
            print("⚠️ generate_bgm が使えないため BGM 無しで進行します")
            return None
        out_wav = os.path.join(tmpdir, f"_bgm_{park}.wav")
        try:
            return generate_bgm_wav(out_wav, duration=float(duration), park=park)
        except Exception as e:
            print(f"⚠️ BGM 自動生成失敗: {e}")
            return None

    # 明示パス
    if os.path.exists(bgm):
        return bgm
    print(f"⚠️ 指定された BGM が見つかりません: {bgm}")
    return None


# =============================================================================
# データ
# =============================================================================
def _build_predictions(date_str: str, park: str):
    """指定日の予測データを取得 (DataFrame)"""
    if park == 'sea':
        targets = SEA_TARGET_ATTRACTIONS
        short_map = SEA_SHORT_DISPLAY
        closures = get_sea_closures(date_str)
        predictor = DisneySeaWaitTimePredictorV3()
    else:
        targets = LAND_TARGET_ATTRACTIONS
        short_map = LAND_SHORT_DISPLAY
        closures = get_land_closures(date_str)
        predictor = DisneyLandWaitTimePredictorV3()

    if not predictor.load_models():
        return None, None, None, None

    attractions = [a for a in targets if a not in closures]
    time_slots = sorted(
        [f"{h:02d}:15" for h in range(9, 21)] +
        [f"{h:02d}:45" for h in range(9, 21)]
    )
    pred = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)
    if pred is None or pred.empty:
        return None, None, None, None

    valid = pred[pred['predicted_wait_time'] >= 0].copy()
    valid['short_name'] = valid['attraction_name'].map(short_map)
    return valid, time_slots, short_map, targets


def _summary(valid: pd.DataFrame):
    """サマリ (狙い目時間 / ピーク時間 / 平均待ち) を返す"""
    avg_by_time = valid.groupby('time')['predicted_wait_time'].mean()
    peak_time = avg_by_time.idxmax()

    window = valid[(valid['time'] >= '09:30') & (valid['time'] < '19:00')]
    if window.empty:
        calm_time = avg_by_time.idxmin()
    else:
        cw_avg = window.groupby('time')['predicted_wait_time'].mean()
        calm_time = cw_avg.idxmin()

    avg_wait = float(valid['predicted_wait_time'].mean())
    return {
        'avg_wait': avg_wait,
        'calm_time': calm_time,
        'peak_time': peak_time,
        'peak_wait': float(avg_by_time.max()),
    }


# =============================================================================
# フレーム描画
# =============================================================================
def _bar_color(wait: float) -> str:
    if wait >= 100:
        return '#E84C5C'
    if wait >= 70:
        return '#F2A93B'
    if wait >= 45:
        return '#F5D261'
    return '#7CC07F'


def _bg_color(time_str: str) -> str:
    """時刻に応じた淡い背景色 (朝→昼→夕)"""
    h = int(time_str.split(':')[0])
    if h < 11:
        return '#FFF4E6'  # 朝
    if h < 15:
        return '#FFFBEB'  # 昼
    if h < 18:
        return '#FFEFD9'  # 夕方
    return '#E8E5F0'      # 夜


def _draw_intro(fig, park_name: str, date_str: str, accent: str):
    """イントロフレーム (タイトルカード)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = get_day_of_week_ja(date_str)
    fig.patch.set_facecolor(LIGHT_BG)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    ax.add_patch(plt.Rectangle((0, 0.55), 1, 0.45, facecolor=accent))
    ax.text(0.5, 0.78, "30秒で分かる",
            fontsize=46, ha='center', va='center',
            color='white', fontweight='bold')
    ax.text(0.5, 0.66,
            f"{dt.month}/{dt.day}({day}) の{park_name}",
            fontsize=34, ha='center', va='center',
            color='white', fontweight='bold')

    ax.add_patch(FancyBboxPatch(
        (0.10, 0.25), 0.80, 0.18,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor=accent, edgecolor='none', alpha=0.15,
    ))
    ax.text(0.5, 0.34, "AI 待ち時間予報",
            fontsize=42, ha='center', va='center',
            color=accent, fontweight='bold')

    ax.text(0.5, 0.10, "▼ 1日のトレンドはこちら",
            fontsize=22, ha='center', va='center',
            color=TEXT_SECONDARY, fontweight='bold')


def _draw_cover(fig, park: str, park_name: str, date_str: str,
                summary: dict, valid: pd.DataFrame, accent: str,
                handle: str = '@disney_ai_wait'):
    """
    Reels カバー画像 (1080x1920) を描画。

    Instagram の表示パターン:
      - Reels タブ:  1080x1920 全体を表示
      - プロフィール グリッド: 中央 1080x1350 (4:5) でクロップ
        → y 軸で言うと上下 約14.8% (y∈[0.0, 0.148] / [0.852, 1.0]) は隠れる

    そのため:
      - グリッドで隠れる "アウター" : ブランド色のリッチな装飾, ロゴ
      - "セーフゾーン" 中央: 日付・パーク・ピーク/狙い目, ミニチャート, CTA
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = get_day_of_week_ja(date_str)

    # グラデーション背景（ブランド色 → 白寄り）
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_xlim(0, 1); bg.set_ylim(0, 1); bg.axis('off')
    grad = np.linspace(0.0, 1.0, 256).reshape(-1, 1)
    accent_rgb = _hex_to_rgb(accent)
    light_rgb = (1.0, 0.99, 0.96)
    grad_rgba = np.zeros((256, 1, 4))
    for i, t in enumerate(grad.flatten()):
        # 上が accent濃い → 下が淡いLIGHT
        c = (1 - t) * np.array(accent_rgb) + t * np.array(light_rgb)
        grad_rgba[i, 0, :3] = c
        grad_rgba[i, 0, 3] = 1.0
    bg.imshow(grad_rgba, aspect='auto', extent=(0, 1, 0, 1), interpolation='bilinear', zorder=0)

    # ===== TOP STRIP (グリッドで隠れる領域) =====
    # 上端 (y > 0.85) は装飾と "30秒で分かる" ブランドフック
    bg.text(0.5, 0.96, "30秒で分かる",
            fontsize=30, ha='center', va='center',
            color='white', fontweight='bold', zorder=3,
            path_effects=[_shadow(2)])
    bg.text(0.5, 0.91, "AI 待ち時間予報",
            fontsize=20, ha='center', va='center',
            color='white', alpha=0.95, fontweight='bold', zorder=3)

    # 上ストリップに装飾ライン
    bg.add_patch(plt.Rectangle((0.0, 0.875), 1.0, 0.003,
                               facecolor='white', alpha=0.45, zorder=2))

    # ===== SAFE ZONE (中央 4:5 で必ず見える) =====
    # 大型「日付」ピル
    bg.add_patch(FancyBboxPatch(
        (0.08, 0.74), 0.84, 0.10,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='white', edgecolor='none', alpha=0.97, zorder=2,
    ))
    bg.text(0.5, 0.79, f"{dt.month}月{dt.day}日（{day}）",
            fontsize=44, ha='center', va='center',
            color=accent, fontweight='bold', zorder=4)

    # パーク名 (大きく)
    bg.text(0.5, 0.685, park_name,
            fontsize=38, ha='center', va='center',
            color=TEXT_PRIMARY, fontweight='bold', zorder=3)
    bg.text(0.5, 0.642, "の混雑どうなる？",
            fontsize=22, ha='center', va='center',
            color=TEXT_SECONDARY, fontweight='bold', zorder=3)

    # ===== KPI 2カラム =====
    # 狙い目
    _kpi_card(bg, x=0.06, y=0.46, w=0.42, h=0.13,
              face='#7CC07F', label="★ 狙い目",
              value=summary['calm_time'])
    # ピーク
    _kpi_card(bg, x=0.52, y=0.46, w=0.42, h=0.13,
              face='#E84C5C', label="▲ ピーク",
              value=summary['peak_time'])

    # ===== ミニ折れ線 (1日の混雑トレンド) =====
    _mini_trendline(fig, valid, accent,
                    rect=[0.08, 0.235, 0.84, 0.18])

    # ===== タップ誘導 / "AI予報" バッジ =====
    bg.add_patch(FancyBboxPatch(
        (0.27, 0.16), 0.46, 0.06,
        boxstyle="round,pad=0.005,rounding_size=0.025",
        facecolor=accent, edgecolor='none', alpha=0.95, zorder=4,
    ))
    bg.text(0.5, 0.19, "▶ タップして再生",
            fontsize=22, ha='center', va='center',
            color='white', fontweight='bold', zorder=5)

    # ===== BOTTOM STRIP (グリッドで隠れる領域) =====
    bg.add_patch(plt.Rectangle((0.0, 0.0), 1.0, 0.115,
                               facecolor=accent, alpha=0.95, zorder=2))
    bg.text(0.04, 0.077, handle,
            fontsize=22, ha='left', va='center',
            color='white', fontweight='bold', zorder=4)
    bg.text(0.04, 0.040, "毎日20時 翌日の予報投稿",
            fontsize=14, ha='left', va='center',
            color='white', alpha=0.85, zorder=4)
    bg.text(0.96, 0.058, "保存推奨 ♪",
            fontsize=18, ha='right', va='center',
            color='white', fontweight='bold', zorder=4)


def _hex_to_rgb(hex_str: str):
    h = hex_str.lstrip('#')
    return (int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0)


def _shadow(offset: int = 2):
    """テキスト用の軽いドロップシャドウ effect"""
    import matplotlib.patheffects as pe
    return pe.withStroke(linewidth=offset, foreground='black', alpha=0.25)


def _kpi_card(ax, x: float, y: float, w: float, h: float,
              face: str, label: str, value: str):
    """カバー用 KPI カード"""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.005,rounding_size=0.03",
        facecolor=face, edgecolor='none', alpha=0.96, zorder=3,
    ))
    ax.text(x + w / 2, y + h * 0.72, label,
            fontsize=18, ha='center', va='center',
            color='white', fontweight='bold', zorder=4)
    ax.text(x + w / 2, y + h * 0.32, value,
            fontsize=36, ha='center', va='center',
            color='white', fontweight='bold', zorder=4)


def _mini_trendline(fig, valid: pd.DataFrame, accent: str, rect):
    """カバー用ミニ折れ線 (1日の平均待ち時間)"""
    avg = valid.groupby('time')['predicted_wait_time'].mean().sort_index()
    if avg.empty:
        return
    ax = fig.add_axes(rect)
    ax.set_facecolor((1, 1, 1, 0.85))
    for spine in ('top', 'right', 'left', 'bottom'):
        ax.spines[spine].set_visible(False)
    xs = list(range(len(avg)))
    ys = avg.values

    # フィル
    ax.fill_between(xs, ys, alpha=0.25, color=accent, zorder=1)
    ax.plot(xs, ys, color=accent, linewidth=3.5, zorder=2)

    # 最大点 / 最小点をマーク
    imax = int(np.argmax(ys))
    imin = int(np.argmin(ys[2:-2])) + 2 if len(ys) > 4 else int(np.argmin(ys))
    ax.scatter([imax], [ys[imax]], s=160, color='#E84C5C',
               edgecolors='white', linewidths=2.5, zorder=4)
    ax.scatter([imin], [ys[imin]], s=160, color='#2BB673',
               edgecolors='white', linewidths=2.5, zorder=4)

    # 端と最大/最小に時刻ラベル
    times = avg.index.tolist()
    ax.text(imax, ys[imax] + max(ys) * 0.10, times[imax],
            fontsize=12, ha='center', va='bottom',
            color='#E84C5C', fontweight='bold', zorder=5)
    ax.text(imin, ys[imin] - max(ys) * 0.10, times[imin],
            fontsize=12, ha='center', va='top',
            color='#2BB673', fontweight='bold', zorder=5)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-0.5, len(xs) - 0.5)
    ax.set_ylim(0, max(ys) * 1.30)

    # 上に小ラベル
    ax.text(0.02, 0.95, "1日の平均待ち時間",
            transform=ax.transAxes,
            fontsize=12, ha='left', va='top',
            color=TEXT_SECONDARY, fontweight='bold')


def _draw_outro(fig, park_name: str, date_str: str, summary: dict, accent: str,
                handle: str = '@disney_ai_wait'):
    """アウトロフレーム (CTA)"""
    fig.patch.set_facecolor(LIGHT_BG)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, facecolor=accent))
    ax.text(0.5, 0.91, "今日のまとめ",
            fontsize=36, ha='center', va='center',
            color='white', fontweight='bold')
    ax.text(0.5, 0.83, park_name,
            fontsize=26, ha='center', va='center', color='white')

    # 狙い目DAY
    ax.add_patch(FancyBboxPatch(
        (0.05, 0.55), 0.42, 0.18,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='#7CC07F', edgecolor='none',
    ))
    ax.text(0.26, 0.68, "★ 狙い目時間",
            fontsize=20, ha='center', va='center',
            color='white', fontweight='bold')
    ax.text(0.26, 0.59, summary['calm_time'],
            fontsize=34, ha='center', va='center',
            color='white', fontweight='bold')

    # 激混み
    ax.add_patch(FancyBboxPatch(
        (0.53, 0.55), 0.42, 0.18,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='#E84C5C', edgecolor='none',
    ))
    ax.text(0.74, 0.68, "▲ ピーク時間",
            fontsize=20, ha='center', va='center',
            color='white', fontweight='bold')
    ax.text(0.74, 0.59, summary['peak_time'],
            fontsize=34, ha='center', va='center',
            color='white', fontweight='bold')

    # CTAブロック
    ax.add_patch(FancyBboxPatch(
        (0.05, 0.20), 0.90, 0.30,
        boxstyle="round,pad=0.01,rounding_size=0.05",
        facecolor=accent, edgecolor='none', alpha=0.18,
    ))
    ax.text(0.5, 0.42, "保存して旅行プランに♪",
            fontsize=32, ha='center', va='center',
            color=TEXT_PRIMARY, fontweight='bold')
    ax.text(0.5, 0.32, "毎日20時に翌日の予報を投稿",
            fontsize=22, ha='center', va='center',
            color=accent, fontweight='bold')

    ax.text(0.5, 0.08, f"フォローはこちら → {handle}",
            fontsize=24, ha='center', va='center',
            color=accent, fontweight='bold')


def _draw_animated_frame(fig, park_name: str, date_str: str,
                         time_str: str, top_attr: pd.DataFrame,
                         summary: dict, accent: str, max_wait: float):
    """1スロット分の本編フレーム"""
    fig.patch.set_facecolor(_bg_color(time_str))

    # ヘッダー (上 16%)
    h_ax = fig.add_axes([0, 0.84, 1, 0.16])
    h_ax.set_xlim(0, 1); h_ax.set_ylim(0, 1); h_ax.axis('off')
    h_ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=accent))
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = get_day_of_week_ja(date_str)
    h_ax.text(0.05, 0.65, park_name,
              fontsize=24, ha='left', va='center',
              color='white', fontweight='bold')
    h_ax.text(0.05, 0.30, f"{dt.month}/{dt.day}({day}) AI 待ち時間予報",
              fontsize=18, ha='left', va='center', color='white')

    # 大きな時計 (上 中央)
    h_ax.text(0.95, 0.50, time_str,
              fontsize=60, ha='right', va='center',
              color='white', fontweight='bold')

    # メインバーチャート (中央 60%)
    body = fig.add_axes([0.04, 0.20, 0.92, 0.62])
    label_pad = max_wait * 0.50  # 左側のラベル領域 (データ座標)
    body.set_xlim(-label_pad, max_wait * 1.20)
    body.set_ylim(-0.5, len(top_attr) - 0.5)
    body.invert_yaxis()
    body.set_facecolor((1, 1, 1, 0))
    for spine in body.spines.values():
        spine.set_visible(False)
    body.set_xticks([])
    body.set_yticks([])

    bar_h = 0.7
    for i, (_, row) in enumerate(top_attr.iterrows()):
        wait = row['predicted_wait_time']
        color = _bar_color(wait)
        body.barh(i, wait, height=bar_h, color=color,
                  edgecolor='none', alpha=0.92)
        body.text(-max_wait * 0.03, i, row['short_name'],
                  fontsize=22, ha='right', va='center',
                  color=TEXT_PRIMARY, fontweight='bold')
        body.text(wait + max_wait * 0.015, i, f"{int(round(wait))}分",
                  fontsize=22, ha='left', va='center',
                  color=TEXT_PRIMARY, fontweight='bold')

    # 下: 現在の最も狙い目アトラクション (下 18%)
    f_ax = fig.add_axes([0, 0, 1, 0.18])
    f_ax.set_xlim(0, 1); f_ax.set_ylim(0, 1); f_ax.axis('off')
    f_ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=accent, alpha=0.12))

    # この時間の最も空いてるアトラクション
    if len(top_attr) > 0:
        best = top_attr.iloc[-1]
        f_ax.text(0.04, 0.70, "★ 今この時間の狙い目",
                  fontsize=18, ha='left', va='center',
                  color='#2BB673', fontweight='bold')
        f_ax.text(0.04, 0.30,
                  f"{best['short_name']}  {int(round(best['predicted_wait_time']))}分",
                  fontsize=26, ha='left', va='center',
                  color=TEXT_PRIMARY, fontweight='bold')

    # ピーク表示
    f_ax.text(0.96, 0.70, "今日の傾向",
              fontsize=14, ha='right', va='center',
              color=TEXT_SECONDARY, fontweight='bold')
    f_ax.text(0.96, 0.30,
              f"平均±{summary['avg_wait']:.0f}分 / ピーク{summary['peak_time']}",
              fontsize=14, ha='right', va='center',
              color=TEXT_SECONDARY)


def _interpolate_slots(valid: pd.DataFrame, time_slots: list, frames_per_slot: int):
    """スロット間で線形補間したフレームデータを yield する"""
    pivot = valid.pivot_table(values='predicted_wait_time',
                              index='time', columns='short_name', aggfunc='mean')
    pivot = pivot.reindex(time_slots).ffill().bfill()

    for slot_idx in range(len(time_slots) - 1):
        cur = pivot.iloc[slot_idx]
        nxt = pivot.iloc[slot_idx + 1]
        for f in range(frames_per_slot):
            alpha = f / frames_per_slot
            interp = cur * (1 - alpha) + nxt * alpha
            yield time_slots[slot_idx], interp

    # 最後のスロットはそのまま静止
    yield time_slots[-1], pivot.iloc[-1]


# =============================================================================
# メイン
# =============================================================================
def generate_reel_video(date_str: str, park: str = 'sea',
                         duration: int = 20,
                         output_dir: str = 'predictions_x',
                         handle: str = '@disney_ai_wait',
                         keep_frames: bool = False,
                         bgm: str = 'auto',
                         bgm_volume_db: float = -8.0,
                         cover_variant: str = 'new'):
    """
    リール動画 (mp4) とカバー画像 (png) を生成。

    Args:
        date_str       : 'YYYY-MM-DD'
        park           : 'sea' or 'land'
        duration       : 動画長 (秒) — IG Reels 5〜90秒
        bgm            : 'auto' (自動生成) / 'none' (静音) / 任意の音声ファイルパス
        bgm_volume_db  : BGM の音量 dB (負の値で控えめに / 既定 -16dB)
        cover_variant  : 'new' (専用デザイン) / 'old' (本編1フレーム目をコピー)
                         A/Bテスト用

    Returns:
        (mp4_path, cover_path) または (None, None)
    """
    if shutil.which("ffmpeg") is None:
        print("❌ ffmpeg が見つかりません")
        return None, None

    duration = max(5, min(90, duration))
    os.makedirs(output_dir, exist_ok=True)

    print(f"📹 リール動画生成開始: {park} {date_str} ({duration}s @ {FPS}fps)")

    valid, time_slots, short_map, _targets = _build_predictions(date_str, park)
    if valid is None:
        print("❌ 予測データ取得失敗")
        return None, None

    summary = _summary(valid)
    theme = PARK_THEMES[park]
    accent = theme['accent']
    park_name = theme['name']

    # 各バーの最大値
    max_wait = float(valid['predicted_wait_time'].max())

    # 全アトラクション (上位7)
    top_attr_names = (valid.groupby('short_name')['predicted_wait_time']
                      .mean().sort_values(ascending=False).head(7).index.tolist())

    intro_frames = INTRO_SEC * FPS
    outro_frames = OUTRO_SEC * FPS
    main_seconds = duration - INTRO_SEC - OUTRO_SEC
    main_frames = main_seconds * FPS

    # スロット数 (24) ≒ main_frames / frames_per_slot
    n_slots = len(time_slots)
    frames_per_slot = max(1, main_frames // (n_slots - 1))
    print(f"   intro={intro_frames}f / main={main_frames}f / outro={outro_frames}f"
          f"  ({frames_per_slot}f/slot × {n_slots-1} slots)")

    tmpdir = tempfile.mkdtemp(prefix="reel_frames_")
    cover_path = os.path.join(output_dir, f"ig_reel_{park}_{date_str}_cover.png")
    mp4_path = os.path.join(output_dir, f"ig_reel_{park}_{date_str}.mp4")

    frame_idx = 0
    try:
        # --- INTRO ---
        for _ in range(intro_frames):
            fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
            _draw_intro(fig, park_name, date_str, accent)
            fig.savefig(os.path.join(tmpdir, f"frame_{frame_idx:05d}.png"),
                        dpi=100, facecolor=fig.get_facecolor())
            plt.close(fig)
            frame_idx += 1

        # --- MAIN (バーチャートレース) ---
        first_main_frame_path = None
        slot_anim_count = 0
        for time_str, values in _interpolate_slots(valid, time_slots, frames_per_slot):
            slot_anim_count += 1
            if slot_anim_count > main_frames:
                break

            top_df = (pd.DataFrame({'short_name': values.index,
                                    'predicted_wait_time': values.values})
                      .dropna()
                      .sort_values('predicted_wait_time', ascending=False)
                      .head(7))
            # 順位安定化のため、ベース順 (top_attr_names) で並べる方が見やすい
            top_df['__order'] = top_df['short_name'].map(
                {n: i for i, n in enumerate(top_attr_names)})
            top_df = top_df.sort_values('__order').drop(columns='__order')

            fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
            _draw_animated_frame(fig, park_name, date_str, time_str,
                                  top_df, summary, accent, max_wait)
            frame_path = os.path.join(tmpdir, f"frame_{frame_idx:05d}.png")
            fig.savefig(frame_path, dpi=100, facecolor=fig.get_facecolor())
            plt.close(fig)
            if first_main_frame_path is None:
                first_main_frame_path = frame_path
            frame_idx += 1

        # 残り main_frames を埋める (最後の状態を維持)
        last_path = os.path.join(tmpdir, f"frame_{frame_idx-1:05d}.png")
        while frame_idx < intro_frames + main_frames:
            shutil.copy(last_path,
                        os.path.join(tmpdir, f"frame_{frame_idx:05d}.png"))
            frame_idx += 1

        # --- OUTRO ---
        for _ in range(outro_frames):
            fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
            _draw_outro(fig, park_name, date_str, summary, accent, handle=handle)
            fig.savefig(os.path.join(tmpdir, f"frame_{frame_idx:05d}.png"),
                        dpi=100, facecolor=fig.get_facecolor())
            plt.close(fig)
            frame_idx += 1

        print(f"   ✅ {frame_idx} フレーム生成完了")

        # --- カバー画像 (variant で切り替え) ---
        if cover_variant == 'old':
            # 旧仕様: 本編1フレーム目をそのままコピー
            if first_main_frame_path and os.path.exists(first_main_frame_path):
                shutil.copy(first_main_frame_path, cover_path)
            else:
                shutil.copy(os.path.join(tmpdir, "frame_00000.png"), cover_path)
            print(f"   ✅ カバー画像 (旧 / 1フレーム目): {cover_path}")
        else:
            try:
                cov_fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
                _draw_cover(cov_fig, park=park, park_name=park_name,
                            date_str=date_str, summary=summary,
                            valid=valid, accent=accent, handle=handle)
                cov_fig.savefig(cover_path, dpi=100,
                                facecolor=cov_fig.get_facecolor())
                plt.close(cov_fig)
                print(f"   ✅ カバー画像 (新 / 専用デザイン): {cover_path}")
            except Exception as e:
                print(f"   ⚠️ カバー専用デザイン失敗: {e} → 1フレーム目で代替")
                if first_main_frame_path and os.path.exists(first_main_frame_path):
                    shutil.copy(first_main_frame_path, cover_path)
                else:
                    shutil.copy(os.path.join(tmpdir, "frame_00000.png"), cover_path)

        # --- BGM 準備 ---
        bgm_path = _resolve_bgm(bgm, park=park, duration=duration, tmpdir=tmpdir)
        use_bgm = bgm_path is not None
        if use_bgm:
            print(f"   🎵 BGM: {os.path.basename(bgm_path)} (vol {bgm_volume_db:+.0f}dB)")
        else:
            print("   🔇 BGM: なし (静音)")

        # --- ffmpeg で mp4 化 ---
        if use_bgm:
            # BGM を 1秒フェードイン/アウト + dB 調整
            audio_filter = (
                f"volume={bgm_volume_db}dB,"
                f"afade=t=in:st=0:d=1.0,"
                f"afade=t=out:st={max(duration - 1.5, 0):.2f}:d=1.5,"
                "aresample=48000"
            )
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmpdir, "frame_%05d.png"),
                "-stream_loop", "-1",
                "-i", bgm_path,
                "-filter_complex", f"[1:a]{audio_filter}[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "22",
                "-preset", "medium",
                "-r", str(FPS),
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-movflags", "+faststart",
                "-t", str(duration),
                mp4_path,
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmpdir, "frame_%05d.png"),
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "22",
                "-preset", "medium",
                "-r", str(FPS),
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-movflags", "+faststart",
                "-t", str(duration),
                mp4_path,
            ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print("❌ ffmpeg エラー:")
            print(proc.stderr[-1500:])
            return None, None

        size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
        print(f"✅ mp4 生成完了: {mp4_path} ({size_mb:.1f}MB)")
        return mp4_path, cover_path
    finally:
        if not keep_frames:
            shutil.rmtree(tmpdir, ignore_errors=True)
        else:
            print(f"   📂 フレーム残置: {tmpdir}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, required=True)
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='sea')
    parser.add_argument('--duration', type=int, default=20)
    parser.add_argument('--keep-frames', action='store_true')
    parser.add_argument('--bgm', type=str, default='auto',
                        help="'auto' (自動生成 / bgm/ ディレクトリ優先), 'none' (静音), または音声ファイルパス")
    parser.add_argument('--bgm-volume-db', type=float, default=-8.0,
                        help='BGM音量 dB (負の値で控えめ。既定 -8dB)')
    parser.add_argument('--cover-variant', choices=['new', 'old'], default='new',
                        help='カバーデザイン (A/Bテスト用)')
    args = parser.parse_args()

    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    for p in parks:
        generate_reel_video(args.date, park=p, duration=args.duration,
                             keep_frames=args.keep_frames,
                             bgm=args.bgm,
                             bgm_volume_db=args.bgm_volume_db,
                             cover_variant=args.cover_variant)
