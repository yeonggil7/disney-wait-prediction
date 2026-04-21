#!/usr/bin/env python3
"""
Instagram投稿用 待ち時間ヒートマップ生成スクリプト（縦長 1080x1350 / 4:5）

- フィード推奨アスペクト 4:5（1080x1350）
- 縦長レイアウト: 時間 = 行、アトラクション = 列
- ヘッダー（パーク名・日付・混雑度）+ ヒートマップ + フッター（凡例・ハンドル）
- ストーリーズ用 9:16（1080x1920）も生成可能
"""

import os
import sys
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

# 既存ロジック流用
from generate_x_heatmap import (
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES,
    get_sea_closures,
    get_land_closures,
    round_up_to_10,
    get_day_of_week_ja,
)
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3


# -----------------------------------------------------------------------------
# 日本語フォント（絵文字フォールバック付き）
# -----------------------------------------------------------------------------
_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'Noto Sans CJK',
             'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji',
             'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
_selected = [f for f in _jp_fonts if f in _available] or ['sans-serif']
plt.rcParams['font.family'] = _selected
# 一部の絵文字に対するフォールバック警告を抑制
import warnings as _warnings
_warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


# -----------------------------------------------------------------------------
# 表示用短縮名（Instagramでも幅を圧縮）
# -----------------------------------------------------------------------------
SEA_SHORT_DISPLAY = {
    'ソアリン': 'ソアリン',
    'アナとエルサ': 'アナとエルサ',
    'センターオブジアース': 'センター',
    'タワーオブテラー': 'タワテラ',
    'トイストーリーマニア': 'トイマニ',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーパン',
    'プラザグリーティング': 'プラグリ',
    'レイジングスピリッツ': 'レイジング',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
}

LAND_SHORT_DISPLAY = {
    '美女と野獣の物語': '美女と野獣',
    'モンスターズ・インク': 'モンスターズ',
    'ミート・ミッキー': 'ミッキー',
    'プーさんのハニーハント': 'プーさん',
    'ベイマックスのハッピーライド': 'ベイマックス',
    'ビッグサンダーマウンテン': 'ビッグサンダー',
    'スプラッシュマウンテン': 'スプラッシュ',
}


# -----------------------------------------------------------------------------
# カラーパレット（明るいライトテーマ / Disneyマジカルパステル）
# -----------------------------------------------------------------------------
_PASTEL_COLORS = [
    '#A8E6CF',  # 5分     - ミントグリーン
    '#B4E394',  # 緑     - 若葉
    '#FFE08A',  # 黄緑   - レモンイエロー
    '#FFC97A',  # 黄     - パンプキン
    '#FF9F70',  # オレンジ - ピーチ
    '#FF7A7A',  # 赤     - コーラルピンク
    '#E84C5C',  # 濃赤   - ストロベリーレッド
]
INSTAGRAM_CMAP = LinearSegmentedColormap.from_list('insta_pastel', _PASTEL_COLORS, N=256)

# 凡例で使う代表色（5段階・ヒートマップに準拠）
LEGEND_COLORS = ['#B4E394', '#FFE08A', '#FFC97A', '#FF9F70', '#FF7A7A']

# ライトテーマ共通色
LIGHT_BG = '#FAFBFC'             # オフホワイト（純白より少し柔らかい）
TEXT_PRIMARY = '#1F2937'         # 濃いグレー（黒より優しい）
TEXT_SECONDARY = '#6B7280'       # ミドルグレー
DIVIDER = '#E5E7EB'              # 区切り線
CLOSED_CELL = '#F3F4F6'          # 休止セル背景


# -----------------------------------------------------------------------------
# 共通: 予測データ取得
# -----------------------------------------------------------------------------
def _build_pivot(date_str, park):
    """指定パークの予測ピボットテーブルを返す (rows=time, cols=attraction)。"""
    if park == 'sea':
        targets = SEA_TARGET_ATTRACTIONS
        display = SEA_DISPLAY_NAMES
        short = SEA_SHORT_DISPLAY
        closures = get_sea_closures(date_str)
        predictor = DisneySeaWaitTimePredictorV3()
    else:
        targets = LAND_TARGET_ATTRACTIONS
        display = LAND_DISPLAY_NAMES
        short = LAND_SHORT_DISPLAY
        closures = get_land_closures(date_str)
        predictor = DisneyLandWaitTimePredictorV3()

    if not predictor.load_models():
        print("❌ モデルが見つかりません")
        return None, None, None

    attractions_to_predict = [a for a in targets if a not in closures]

    # 9:00〜21:00 を 30分間隔で
    time_slots = sorted(
        [f"{h:02d}:15" for h in range(9, 21)] +
        [f"{h:02d}:45" for h in range(9, 21)]
    )

    predictions = predictor.predict(
        date=date_str,
        time_slots=time_slots,
        attractions=attractions_to_predict,
    )
    if predictions is None:
        return None, None, None

    for attraction in closures:
        for t in time_slots:
            predictions = pd.concat([predictions, pd.DataFrame([{
                'date': date_str,
                'time': t,
                'attraction_name': attraction,
                'predicted_wait_time': -1,
            }])], ignore_index=True)

    predictions = predictions[predictions['attraction_name'].isin(targets)]
    predictions['short_name'] = predictions['attraction_name'].map(short)
    predictions['wait_rounded'] = predictions['predicted_wait_time'].apply(round_up_to_10)

    pivot = predictions.pivot_table(
        values='wait_rounded',
        index='time',
        columns='short_name',
        aggfunc='mean',
    )

    # 列順を固定（人気順）
    ordered = [short[a] for a in targets if a in short]
    pivot = pivot.reindex(columns=[c for c in ordered if c in pivot.columns])

    return pivot, closures, predictions


def _summary_stats(predictions):
    """混雑度・平均・空き時間を算出"""
    valid = predictions[predictions['predicted_wait_time'] >= 0]
    avg_wait = int(valid['predicted_wait_time'].mean()) if not valid.empty else 0

    avg_by_time = valid.groupby('time')['predicted_wait_time'].mean()
    calm_time = avg_by_time.idxmin() if not avg_by_time.empty else '--:--'
    peak_time = avg_by_time.idxmax() if not avg_by_time.empty else '--:--'

    # 各アトラクションの狙い目タイム (9:30〜19:00)
    # - 開園直後(9:15)は混雑が一極集中しやすいため除外
    # - 閉園間際に最小値が偏らないよう、最小値から+20%以内に収まる「最も早い時間帯」を採用
    per_attraction_calm = {}
    window = valid[(valid['time'] >= '09:30') & (valid['time'] < '19:00')]
    if not window.empty:
        for short_name, grp in window.groupby('short_name'):
            grp_sorted = grp.sort_values('time')
            min_wait = grp_sorted['predicted_wait_time'].min()
            threshold = max(min_wait * 1.2, min_wait + 5)  # 5分または20%の余裕
            calm_rows = grp_sorted[grp_sorted['predicted_wait_time'] <= threshold]
            per_attraction_calm[short_name] = calm_rows.iloc[0]['time']

    if avg_wait >= 60:
        cong = ('激混み', '#E84C5C')
    elif avg_wait >= 40:
        cong = ('混雑', '#FF9F70')
    elif avg_wait >= 25:
        cong = ('やや混雑', '#FFC97A')
    else:
        cong = ('快適', '#7AC97F')

    return {
        'avg_wait': avg_wait,
        'calm_time': calm_time,
        'peak_time': peak_time,
        'per_attraction_calm': per_attraction_calm,
        'congestion': cong[0],
        'congestion_color': cong[1],
    }


# -----------------------------------------------------------------------------
# 描画: 4:5 フィード版（1080x1350）
# -----------------------------------------------------------------------------
def _draw_feed_portrait(pivot, stats, date_str, park_name, park_emoji,
                         accent_color, bg_color, output_file, handle="@disney_ai_wait"):
    """4:5 縦長 (1080x1350) のフィード画像を描画 — ライトテーマ"""

    # 1080 x 1350 px (DPI=100 → figsize 10.8 x 13.5)
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=LIGHT_BG)

    day_name = get_day_of_week_ja(date_str)
    dt = datetime.strptime(date_str, '%Y-%m-%d')

    # ============================================================
    # ヘッダー (上 18%) — 大胆なカラーブロックで「スクロールを止める」
    # ============================================================
    header_ax = fig.add_axes([0, 0.82, 1, 0.18])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis('off')

    # 上部: パーク色のフルワイドカラーブロック
    header_ax.add_patch(plt.Rectangle((0, 0.40), 1, 0.60,
                                       facecolor=accent_color, transform=header_ax.transAxes))

    # 「明日の○○混雑予報」ヒーローテキスト
    hero_label = "明日の" if dt.date() > datetime.now().date() else "本日の"
    header_ax.text(0.06, 0.85, f"{hero_label}{park_name}",
                   fontsize=20, ha='left', va='center',
                   color='white', fontweight='bold', alpha=0.95)
    header_ax.text(0.06, 0.65, "AI 混雑予報",
                   fontsize=42, ha='left', va='center',
                   color='white', fontweight='bold')

    # 日付（右上、白文字大きく）
    date_text = f"{dt.month}/{dt.day}"
    header_ax.text(0.94, 0.78, date_text, fontsize=52,
                   ha='right', va='center', color='white', fontweight='bold')
    header_ax.text(0.94, 0.50, f"({day_name})", fontsize=22,
                   ha='right', va='center', color='white', fontweight='bold', alpha=0.85)

    # 混雑度バッジ（混雑度カラーで塗った大型バッジ）
    badge_text = f"{stats['congestion']}   /   平均 {stats['avg_wait']} 分待ち"
    header_ax.text(0.5, 0.18, badge_text, fontsize=19,
                   ha='center', va='center',
                   color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.7',
                             facecolor=stats['congestion_color'],
                             edgecolor='white', linewidth=2))

    # ============================================================
    # ヒートマップ (中央 ~56%)
    # ============================================================
    heatmap_ax = fig.add_axes([0.10, 0.23, 0.85, 0.57])
    heatmap_ax.set_facecolor(LIGHT_BG)

    display_data = pivot.copy().astype(float)
    mask = display_data < 0
    display_data[mask] = np.nan

    heatmap_ax.imshow(
        display_data.values,
        aspect='auto',
        cmap=INSTAGRAM_CMAP,
        vmin=0, vmax=150,
    )

    n_rows, n_cols = display_data.shape
    for i in range(n_rows):
        for j in range(n_cols):
            v = pivot.iloc[i, j]
            if pd.isna(v):
                continue
            if v < 0:
                continue
            text = f'{int(v)}'
            # ライトテーマ: 全セルで濃い文字色を使用 (パステル背景でも読みやすい)
            heatmap_ax.text(j, i, text, ha='center', va='center',
                            fontsize=11, fontweight='bold', color='#1a1a1a')

    # 休止セルのオーバーレイ
    for i in range(n_rows):
        for j in range(n_cols):
            if mask.iloc[i, j]:
                heatmap_ax.add_patch(plt.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1,
                    facecolor=CLOSED_CELL, edgecolor='none'))
                heatmap_ax.text(j, i, '休止', ha='center', va='center',
                                fontsize=9, color=TEXT_SECONDARY)

    # 各アトラクションの狙い目セルに枠線マーカー
    per_calm = stats.get('per_attraction_calm', {})
    time_to_idx = {t: i for i, t in enumerate(pivot.index)}
    for j, attr in enumerate(pivot.columns):
        recommended = per_calm.get(attr)
        if recommended is None:
            continue
        i = time_to_idx.get(recommended)
        if i is None:
            continue
        heatmap_ax.add_patch(plt.Rectangle(
            (j - 0.48, i - 0.48), 0.96, 0.96,
            facecolor='none', edgecolor='#1F4E79',
            linewidth=2.2, zorder=10,
        ))

    heatmap_ax.set_xticks(range(n_cols))
    heatmap_ax.set_xticklabels(list(pivot.columns), rotation=30, ha='right',
                               fontsize=11, color=TEXT_PRIMARY, fontweight='bold')
    heatmap_ax.set_yticks(range(n_rows))
    heatmap_ax.set_yticklabels(pivot.index, fontsize=10, color=TEXT_SECONDARY)

    for spine in heatmap_ax.spines.values():
        spine.set_visible(False)
    heatmap_ax.tick_params(axis='both', length=0)

    # ============================================================
    # フッター (下 21%) — 保存促進CTA + 凡例 + おすすめ/ピーク
    # ============================================================
    footer_ax = fig.add_axes([0, 0, 1, 0.21])
    footer_ax.set_xlim(0, 1)
    footer_ax.set_ylim(0, 1)
    footer_ax.axis('off')

    # 上部の細い区切り線
    footer_ax.add_patch(plt.Rectangle((0.06, 0.95), 0.88, 0.003,
                                       facecolor=DIVIDER, edgecolor='none'))

    # 凡例（上段・横一列）
    legend_labels = ['〜30分', '30-60分', '60-90分', '90-120分', '120分〜']
    box_w = 0.14
    box_h = 0.10
    gap = 0.018
    total_w = box_w * 5 + gap * 4
    legend_x_start = (1 - total_w) / 2
    legend_y = 0.78
    for k, (lbl, col) in enumerate(zip(legend_labels, LEGEND_COLORS)):
        x = legend_x_start + k * (box_w + gap)
        footer_ax.add_patch(FancyBboxPatch(
            (x, legend_y), box_w, box_h,
            boxstyle="round,pad=0.005,rounding_size=0.020",
            facecolor=col, edgecolor='none',
        ))
        footer_ax.text(x + box_w / 2, legend_y + box_h / 2, lbl,
                       fontsize=10, ha='center', va='center',
                       color='#1a1a1a', fontweight='bold')

    # 各アトラクションの狙い目タイム一覧（2カラム / 19時前）
    footer_ax.text(0.5, 0.66, "☆ 各アトラクションの狙い目タイム  (9:30〜19時)",
                   fontsize=12, ha='center', va='center',
                   color='#1F4E79', fontweight='bold')

    items = [(name, stats['per_attraction_calm'].get(name, '--:--'))
             for name in pivot.columns]
    n_items = len(items)
    n_per_col = (n_items + 1) // 2
    col_centers = [0.27, 0.73]
    row_top = 0.55
    row_h = 0.085
    for i, (name, t) in enumerate(items):
        col = i // n_per_col
        row = i % n_per_col
        y = row_top - row * row_h
        cx = col_centers[col]
        footer_ax.text(cx - 0.18, y, name, fontsize=11,
                       ha='left', va='center', color=TEXT_PRIMARY,
                       fontweight='bold')
        footer_ax.text(cx + 0.18, y, f"{t}〜",
                       fontsize=13, ha='right', va='center',
                       color='#1F8F4E', fontweight='bold')

    # 中央分割線（縦の細線）
    divider_top = max(0.20, row_top - (n_per_col - 1) * row_h - 0.02)
    footer_ax.add_patch(plt.Rectangle(
        (0.499, divider_top), 0.002, row_top + 0.05 - divider_top,
        facecolor=DIVIDER, edgecolor='none'))

    # CTA帯（下部、保存促進）
    footer_ax.add_patch(plt.Rectangle((0, 0), 1, 0.18,
                                       facecolor=accent_color, alpha=0.12,
                                       edgecolor='none'))
    footer_ax.text(0.5, 0.13, "保存して1日の予定に役立てて♪",
                   fontsize=14, ha='center', va='center',
                   color=TEXT_PRIMARY, fontweight='bold')
    footer_ax.text(0.5, 0.03, f"毎日20時に翌日の予報を投稿   {handle}",
                   fontsize=11, ha='center', va='center',
                   color=accent_color, fontweight='bold')

    plt.savefig(output_file, dpi=100, facecolor=LIGHT_BG, bbox_inches=None, pad_inches=0)
    plt.close()


# -----------------------------------------------------------------------------
# 描画: 9:16 ストーリーズ版（1080x1920）
# -----------------------------------------------------------------------------
def _draw_story_portrait(pivot, stats, date_str, park_name, park_emoji,
                          accent_color, bg_color, output_file, handle="@disney_ai_wait"):
    """9:16 縦長 (1080x1920) のストーリーズ画像を描画"""

    fig = plt.figure(figsize=(10.8, 19.2), dpi=100, facecolor=LIGHT_BG)

    day_name = get_day_of_week_ja(date_str)
    dt = datetime.strptime(date_str, '%Y-%m-%d')

    # ヘッダー（ライトテーマ）
    header_ax = fig.add_axes([0, 0.78, 1, 0.22])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis('off')

    header_ax.add_patch(plt.Rectangle((0, 0.30), 1, 0.70,
                                       facecolor=accent_color, transform=header_ax.transAxes))

    hero_label = "明日の" if dt.date() > datetime.now().date() else "本日の"
    header_ax.text(0.5, 0.85, f"{hero_label}{park_name}", fontsize=24,
                   ha='center', va='center', color='white', fontweight='bold', alpha=0.95)
    header_ax.text(0.5, 0.65, "AI 混雑予報", fontsize=48,
                   ha='center', va='center', color='white', fontweight='bold')
    header_ax.text(0.5, 0.45, f"{dt.month}/{dt.day} ({day_name})",
                   fontsize=42, ha='center', va='center', color='white', fontweight='bold')
    header_ax.text(0.5, 0.13,
                   f"{stats['congestion']}   /   平均 {stats['avg_wait']} 分待ち",
                   fontsize=22, ha='center', va='center',
                   color='white', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.8',
                             facecolor=stats['congestion_color'],
                             edgecolor='white', linewidth=2))

    # ヒートマップ
    heatmap_ax = fig.add_axes([0.10, 0.22, 0.85, 0.53])
    heatmap_ax.set_facecolor(LIGHT_BG)
    display_data = pivot.copy().astype(float)
    mask = display_data < 0
    display_data[mask] = np.nan
    heatmap_ax.imshow(display_data.values, aspect='auto',
                      cmap=INSTAGRAM_CMAP, vmin=0, vmax=150)

    n_rows, n_cols = display_data.shape
    for i in range(n_rows):
        for j in range(n_cols):
            v = pivot.iloc[i, j]
            if pd.isna(v):
                continue
            if v < 0:
                continue
            text = f'{int(v)}'
            heatmap_ax.text(j, i, text, ha='center', va='center',
                            fontsize=12, fontweight='bold', color='#1a1a1a')

    # 各アトラクションの狙い目セルに枠線マーカー
    per_calm = stats.get('per_attraction_calm', {})
    time_to_idx = {t: i for i, t in enumerate(pivot.index)}
    for j, attr in enumerate(pivot.columns):
        recommended = per_calm.get(attr)
        if recommended is None:
            continue
        i = time_to_idx.get(recommended)
        if i is None:
            continue
        heatmap_ax.add_patch(plt.Rectangle(
            (j - 0.48, i - 0.48), 0.96, 0.96,
            facecolor='none', edgecolor='#1F4E79',
            linewidth=2.4, zorder=10,
        ))

    heatmap_ax.set_xticks(range(n_cols))
    heatmap_ax.set_xticklabels(list(pivot.columns), rotation=30, ha='right',
                               fontsize=12, color=TEXT_PRIMARY, fontweight='bold')
    heatmap_ax.set_yticks(range(n_rows))
    heatmap_ax.set_yticklabels(pivot.index, fontsize=11, color=TEXT_SECONDARY)
    for spine in heatmap_ax.spines.values():
        spine.set_visible(False)
    heatmap_ax.tick_params(axis='both', length=0)

    for i in range(n_rows):
        for j in range(n_cols):
            if mask.iloc[i, j]:
                heatmap_ax.add_patch(plt.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1,
                    facecolor=CLOSED_CELL, edgecolor='none'))
                heatmap_ax.text(j, i, '休止', ha='center', va='center',
                                fontsize=10, color=TEXT_SECONDARY)

    # フッター
    footer_ax = fig.add_axes([0, 0, 1, 0.18])
    footer_ax.set_xlim(0, 1)
    footer_ax.set_ylim(0, 1)
    footer_ax.axis('off')

    footer_ax.add_patch(plt.Rectangle((0.06, 0.93), 0.88, 0.003,
                                       facecolor=DIVIDER, edgecolor='none'))

    footer_ax.text(0.5, 0.82, "☆ 各アトラクションの狙い目タイム  (9:30〜19時)",
                   fontsize=18, ha='center', va='center',
                   color='#1F4E79', fontweight='bold')

    items = [(name, stats['per_attraction_calm'].get(name, '--:--'))
             for name in pivot.columns]
    n_items = len(items)
    n_per_col = (n_items + 1) // 2
    col_centers = [0.27, 0.73]
    row_top = 0.70
    row_h = 0.10
    for i, (name, t) in enumerate(items):
        col = i // n_per_col
        row = i % n_per_col
        y = row_top - row * row_h
        cx = col_centers[col]
        footer_ax.text(cx - 0.18, y, name, fontsize=14,
                       ha='left', va='center', color=TEXT_PRIMARY,
                       fontweight='bold')
        footer_ax.text(cx + 0.18, y, f"{t}〜",
                       fontsize=16, ha='right', va='center',
                       color='#1F8F4E', fontweight='bold')

    footer_ax.add_patch(plt.Rectangle((0, 0), 1, 0.22,
                                       facecolor=accent_color, alpha=0.12,
                                       edgecolor='none'))
    footer_ax.text(0.5, 0.15, "保存して1日の予定に役立てて♪",
                   fontsize=17, ha='center', va='center',
                   color=TEXT_PRIMARY, fontweight='bold')
    footer_ax.text(0.5, 0.04, handle, fontsize=14,
                   ha='center', va='center', color=accent_color, fontweight='bold')

    plt.savefig(output_file, dpi=100, facecolor=LIGHT_BG, bbox_inches=None, pad_inches=0)
    plt.close()


# -----------------------------------------------------------------------------
# 公開関数
# -----------------------------------------------------------------------------
PARK_THEMES = {
    'sea':  {'name': 'ディズニーシー', 'emoji': '🌊',
             'accent': '#1F8FBE', 'bg': LIGHT_BG},   # シーは深いターコイズ
    'land': {'name': 'ディズニーランド', 'emoji': '🏰',
             'accent': '#D63384', 'bg': LIGHT_BG},   # ランドはローズマゼンタ
}


def generate_instagram_image(date_str, park='sea', layout='feed',
                             output_dir='predictions_x', handle='@disney_ai_wait'):
    """
    Instagram用ヒートマップ画像を生成

    Args:
        date_str: 'YYYY-MM-DD'
        park:    'sea' or 'land'
        layout:  'feed' (1080x1350, 4:5) または 'story' (1080x1920, 9:16)
        output_dir: 出力ディレクトリ
        handle:  Instagramハンドル（フッター表示用）

    Returns:
        生成画像のパス
    """
    os.makedirs(output_dir, exist_ok=True)
    theme = PARK_THEMES[park]

    print(f"\n{theme['emoji']} {theme['name']} Instagram {layout}画像を生成: {date_str}")

    pivot, closures, predictions = _build_pivot(date_str, park)
    if pivot is None:
        return None

    stats = _summary_stats(predictions)

    suffix = 'feed' if layout == 'feed' else 'story'
    output_file = os.path.join(
        output_dir,
        f"ig_{park}_{suffix}_{date_str}.png"
    )

    if layout == 'feed':
        _draw_feed_portrait(
            pivot, stats, date_str, theme['name'], theme['emoji'],
            theme['accent'], theme['bg'], output_file, handle=handle,
        )
    elif layout == 'story':
        _draw_story_portrait(
            pivot, stats, date_str, theme['name'], theme['emoji'],
            theme['accent'], theme['bg'], output_file, handle=handle,
        )
    else:
        raise ValueError(f"Unknown layout: {layout}")

    print(f"✅ 保存: {output_file}")
    return output_file


def generate_sea_instagram(date_str, layout='feed', output_dir='predictions_x',
                           handle='@disney_ai_wait'):
    return generate_instagram_image(date_str, 'sea', layout, output_dir, handle)


def generate_land_instagram(date_str, layout='feed', output_dir='predictions_x',
                            handle='@disney_ai_wait'):
    return generate_instagram_image(date_str, 'land', layout, output_dir, handle)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Instagram用 縦長ヒートマップ生成')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    parser.add_argument('--date', '-d', default=tomorrow,
                        help=f'予測日 (default: {tomorrow})')
    parser.add_argument('--park', '-p', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--layout', '-l', choices=['feed', 'story', 'both'], default='feed')
    parser.add_argument('--output', '-o', default='predictions_x')
    parser.add_argument('--handle', default='@disney_ai_wait')
    args = parser.parse_args()

    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    layouts = ['feed', 'story'] if args.layout == 'both' else [args.layout]

    generated = []
    for park in parks:
        for layout in layouts:
            path = generate_instagram_image(
                args.date, park, layout, args.output, args.handle
            )
            if path:
                generated.append(path)

    print("\n📁 生成ファイル:")
    for p in generated:
        print(f"   - {p}")


if __name__ == '__main__':
    main()
