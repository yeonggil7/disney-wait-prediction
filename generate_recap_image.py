"""
答え合わせ画像 (1080x1350) 生成モジュール

「昨日のAI予測 vs 実測」を視覚化したInstagram用カルーセル画像を出力する。

使い方:
    from generate_recap_image import generate_recap_image
    path = generate_recap_image('2026-04-19', park='sea')
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

from generate_x_heatmap import (
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES,
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
    DIVIDER,
    PARK_THEMES,
)
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3


# 日本語フォント
_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']


# =============================================================================
# データ取得
# =============================================================================
def _load_actual(date_str: str, park: str) -> pd.DataFrame:
    """その日の実測 CSV を返す"""
    folder = 'Disneysea' if park == 'sea' else 'Disneyland'
    prefix = 'disneysea_daily_' if park == 'sea' else 'disneyland_daily_'
    path = f"{folder}/{prefix}{date_str}.csv"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    # raw_value=="-" は休園/未開園として除外
    df = df[df['raw_value'] != '-']
    df['wait_time'] = pd.to_numeric(df['wait_time'], errors='coerce')
    df = df.dropna(subset=['wait_time'])
    return df


def _predict(date_str: str, park: str) -> pd.DataFrame:
    """その日について予測を再実行"""
    if park == 'sea':
        targets = SEA_TARGET_ATTRACTIONS
        closures = get_sea_closures(date_str)
        predictor = DisneySeaWaitTimePredictorV3()
    else:
        targets = LAND_TARGET_ATTRACTIONS
        closures = get_land_closures(date_str)
        predictor = DisneyLandWaitTimePredictorV3()

    if not predictor.load_models():
        return None

    attractions = [a for a in targets if a not in closures]
    time_slots = sorted(
        [f"{h:02d}:15" for h in range(9, 21)] +
        [f"{h:02d}:45" for h in range(9, 21)]
    )
    return predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)


def _build_comparison(date_str: str, park: str):
    """予測 vs 実測のマージ済 DataFrame と各種統計を返す"""
    actual = _load_actual(date_str, park)
    pred = _predict(date_str, park)
    if actual is None or pred is None or pred.empty:
        return None

    short_map = SEA_SHORT_DISPLAY if park == 'sea' else LAND_SHORT_DISPLAY
    targets = SEA_TARGET_ATTRACTIONS if park == 'sea' else LAND_TARGET_ATTRACTIONS

    # 予測と実測を attraction_name + time でマージ
    merged = pred.merge(
        actual[['time', 'attraction_name', 'wait_time']],
        on=['attraction_name', 'time'],
        how='inner',
        suffixes=('_pred', '_actual'),
    )
    if merged.empty:
        return None

    merged = merged[merged['attraction_name'].isin(targets)]
    merged['short_name'] = merged['attraction_name'].map(short_map)
    merged['error'] = (merged['predicted_wait_time'] - merged['wait_time']).abs()

    # アトラクション別サマリ
    per_attr = merged.groupby(['attraction_name', 'short_name']).agg(
        avg_pred=('predicted_wait_time', 'mean'),
        avg_actual=('wait_time', 'mean'),
        max_actual=('wait_time', 'max'),
        mae=('error', 'mean'),
        n=('error', 'size'),
    ).reset_index()
    # 元の表示順 (人気順) で並べる
    order_map = {a: i for i, a in enumerate(targets)}
    per_attr['order'] = per_attr['attraction_name'].map(order_map)
    per_attr = per_attr.sort_values('order').reset_index(drop=True)

    overall_mae = float(merged['error'].mean())
    # 「±10分以内に当てた率」
    accuracy_within_10 = float((merged['error'] <= 10).mean()) * 100
    accuracy_within_20 = float((merged['error'] <= 20).mean()) * 100

    return {
        'merged': merged,
        'per_attr': per_attr,
        'overall_mae': overall_mae,
        'accuracy_within_10': accuracy_within_10,
        'accuracy_within_20': accuracy_within_20,
        'date': date_str,
        'park': park,
    }


# =============================================================================
# 画像描画
# =============================================================================
def _draw_recap(stats, output_file: str, handle: str = '@disney_ai_wait'):
    """1080x1350 の答え合わせ画像を描画"""

    park = stats['park']
    theme = PARK_THEMES[park]
    accent = theme['accent']
    park_name = theme['name']
    per_attr = stats['per_attr']
    date_str = stats['date']

    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=LIGHT_BG)

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_ja = get_day_of_week_ja(date_str)

    # ============================================================
    # ヘッダー (上 22%)
    # ============================================================
    header_ax = fig.add_axes([0, 0.78, 1, 0.22])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis('off')

    # 上段: フルワイドアクセント帯
    header_ax.add_patch(plt.Rectangle((0, 0.55), 1, 0.45, facecolor=accent))
    header_ax.text(0.06, 0.78, f"{park_name}", fontsize=18,
                   ha='left', va='center', color='white', fontweight='bold')
    header_ax.text(0.06, 0.62, "AI予測 答え合わせ", fontsize=30,
                   ha='left', va='center', color='white', fontweight='bold')
    header_ax.text(0.94, 0.78, f"{dt.month}/{dt.day}", fontsize=24,
                   ha='right', va='center', color='white', fontweight='bold')
    header_ax.text(0.94, 0.62, f"({day_ja})", fontsize=14,
                   ha='right', va='center', color='white')

    # 下段: 全体精度バッジ
    acc = stats['accuracy_within_10']
    mae = stats['overall_mae']
    badge_color = '#2BB673' if acc >= 70 else '#F2A93B' if acc >= 50 else '#E84C5C'
    badge_label = '優秀' if acc >= 70 else 'まずまず' if acc >= 50 else '修行中'

    header_ax.add_patch(FancyBboxPatch(
        (0.10, 0.10), 0.80, 0.36,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor=badge_color, edgecolor='none',
    ))
    header_ax.text(0.50, 0.35,
                   f"±10分以内的中  {acc:.0f}%   /   平均誤差 ±{mae:.0f}分",
                   fontsize=18, ha='center', va='center',
                   color='white', fontweight='bold')
    header_ax.text(0.50, 0.18, f"今日のAIスコア:  {badge_label}",
                   fontsize=14, ha='center', va='center',
                   color='white', fontweight='bold')

    # ============================================================
    # 本体: アトラクション別比較表 (中央 60%)
    # ============================================================
    body_ax = fig.add_axes([0.04, 0.16, 0.92, 0.60])
    body_ax.set_xlim(0, 1)
    body_ax.set_ylim(0, 1)
    body_ax.axis('off')

    # 列見出し
    body_ax.text(0.32, 0.97, "アトラクション", fontsize=12,
                 ha='left', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.text(0.55, 0.97, "AI予測", fontsize=12,
                 ha='center', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.text(0.72, 0.97, "実測", fontsize=12,
                 ha='center', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.text(0.90, 0.97, "誤差", fontsize=12,
                 ha='center', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.add_patch(plt.Rectangle((0.0, 0.93), 1.0, 0.003,
                                     facecolor=DIVIDER, edgecolor='none'))

    n = len(per_attr)
    if n == 0:
        body_ax.text(0.5, 0.5, "比較データなし", fontsize=20,
                     ha='center', va='center', color=TEXT_SECONDARY)
    else:
        row_top = 0.86
        row_h = min(0.10, 0.86 / max(n, 1))
        for i, row in per_attr.iterrows():
            y = row_top - i * row_h
            err = row['mae']
            # 行帯色 (誤差で着色)
            band_color = '#E8F8EF' if err <= 10 else '#FFF4E0' if err <= 20 else '#FCE8EA'
            badge_color = '#2BB673' if err <= 10 else '#F2A93B' if err <= 20 else '#E84C5C'
            badge_text = '◎' if err <= 10 else '○' if err <= 20 else '△'

            body_ax.add_patch(FancyBboxPatch(
                (0.0, y - row_h * 0.85), 1.0, row_h * 0.85,
                boxstyle="round,pad=0.005,rounding_size=0.015",
                facecolor=band_color, edgecolor='none',
            ))

            # アトラクション名
            body_ax.text(0.03, y - row_h * 0.42, row['short_name'],
                         fontsize=14, ha='left', va='center',
                         color=TEXT_PRIMARY, fontweight='bold')
            # 予測平均
            body_ax.text(0.55, y - row_h * 0.42, f"{row['avg_pred']:.0f}分",
                         fontsize=15, ha='center', va='center',
                         color=accent, fontweight='bold')
            # 実測平均
            body_ax.text(0.72, y - row_h * 0.42, f"{row['avg_actual']:.0f}分",
                         fontsize=15, ha='center', va='center',
                         color=TEXT_PRIMARY, fontweight='bold')
            # 誤差バッジ
            body_ax.add_patch(FancyBboxPatch(
                (0.83, y - row_h * 0.62), 0.14, row_h * 0.40,
                boxstyle="round,pad=0.005,rounding_size=0.025",
                facecolor=badge_color, edgecolor='none',
            ))
            body_ax.text(0.90, y - row_h * 0.42,
                         f"{badge_text} ±{err:.0f}分",
                         fontsize=12, ha='center', va='center',
                         color='white', fontweight='bold')

    # ============================================================
    # フッター (下 14%) — CTA
    # ============================================================
    footer_ax = fig.add_axes([0, 0, 1, 0.14])
    footer_ax.set_xlim(0, 1)
    footer_ax.set_ylim(0, 1)
    footer_ax.axis('off')

    footer_ax.add_patch(plt.Rectangle((0, 0), 1, 1,
                                       facecolor=accent, alpha=0.12,
                                       edgecolor='none'))
    footer_ax.text(0.5, 0.65,
                   "★ 毎日20時に翌日の予測を投稿中",
                   fontsize=15, ha='center', va='center',
                   color=TEXT_PRIMARY, fontweight='bold')
    footer_ax.text(0.5, 0.30,
                   f"フォロー&保存して旅行プランに  {handle}",
                   fontsize=13, ha='center', va='center',
                   color=accent, fontweight='bold')

    plt.savefig(output_file, dpi=100, facecolor=LIGHT_BG,
                bbox_inches=None, pad_inches=0)
    plt.close()


# =============================================================================
# 公開関数
# =============================================================================
def generate_recap_image(date_str: str, park: str = 'sea',
                          output_dir: str = 'predictions_x',
                          handle: str = '@disney_ai_wait'):
    """
    答え合わせ画像を生成。

    Args:
        date_str: 'YYYY-MM-DD' (実測がある日 / 通常は昨日)
        park:     'sea' or 'land'

    Returns:
        (画像パス, stats dict) または (None, None)
    """
    os.makedirs(output_dir, exist_ok=True)
    stats = _build_comparison(date_str, park)
    if stats is None:
        print(f"⚠️ {date_str} {park}: 予測 or 実測データが揃わずスキップ")
        return None, None

    output_file = os.path.join(
        output_dir, f"ig_recap_{park}_{date_str}.png"
    )
    _draw_recap(stats, output_file, handle=handle)
    print(f"✅ 答え合わせ画像生成: {output_file}")
    return output_file, stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str,
                        default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    args = parser.parse_args()

    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    for p in parks:
        generate_recap_image(args.date, park=p)
