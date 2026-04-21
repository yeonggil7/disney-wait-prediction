"""
週間ランキング画像 (1080x1350) 生成モジュール

来週7日間 (または指定期間) の予測平均待ち時間を集計し、
「狙い目DAY 👑」「激混みDAY 🔥」をランキング表示するInstagram用画像。
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
    get_sea_closures,
    get_land_closures,
    get_day_of_week_ja,
)
from generate_instagram_heatmap import (
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
def _build_daily_summary(date_str: str, park: str) -> dict:
    """指定日・パークの予測サマリ (avg_wait など) を返す"""
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
    pred = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)
    if pred is None or pred.empty:
        return None

    valid = pred[pred['predicted_wait_time'] >= 0]
    avg_wait = float(valid['predicted_wait_time'].mean()) if not valid.empty else 0
    peak_wait = float(valid['predicted_wait_time'].max()) if not valid.empty else 0
    return {
        'date': date_str,
        'park': park,
        'avg_wait': avg_wait,
        'peak_wait': peak_wait,
        'n_closures': len(closures),
    }


def _build_week(start_date: str, park: str, days: int = 7) -> pd.DataFrame:
    """start_date から days 日分の予測サマリを DataFrame で返す"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    rows = []
    for i in range(days):
        d = (start + timedelta(days=i)).strftime('%Y-%m-%d')
        s = _build_daily_summary(d, park)
        if s is not None:
            rows.append(s)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df['rank'] = df['avg_wait'].rank(method='min').astype(int)
    return df


# =============================================================================
# 画像描画
# =============================================================================
def _congestion_color(avg_wait: float) -> str:
    if avg_wait >= 70:
        return '#E84C5C'
    if avg_wait >= 55:
        return '#F2A93B'
    if avg_wait >= 40:
        return '#F5D261'
    return '#7CC07F'


def _congestion_label(avg_wait: float) -> str:
    if avg_wait >= 70:
        return '激混み'
    if avg_wait >= 55:
        return '混雑'
    if avg_wait >= 40:
        return 'やや混雑'
    return '快適'


def _draw_weekly_ranking(df: pd.DataFrame, park: str, output_file: str,
                          handle: str = '@disney_ai_wait'):
    """1080x1350 の週間ランキング画像を描画"""

    theme = PARK_THEMES[park]
    accent = theme['accent']
    park_name = theme['name']

    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=LIGHT_BG)

    start_dt = datetime.strptime(df.iloc[0]['date'], '%Y-%m-%d')
    end_dt = datetime.strptime(df.iloc[-1]['date'], '%Y-%m-%d')

    # ============================================================
    # ヘッダー (上 22%)
    # ============================================================
    header_ax = fig.add_axes([0, 0.78, 1, 0.22])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis('off')

    header_ax.add_patch(plt.Rectangle((0, 0.55), 1, 0.45, facecolor=accent))
    header_ax.text(0.06, 0.78, f"{park_name}", fontsize=18,
                   ha='left', va='center', color='white', fontweight='bold')
    header_ax.text(0.06, 0.62, "AI 週間混雑ランキング", fontsize=26,
                   ha='left', va='center', color='white', fontweight='bold')
    period = f"{start_dt.month}/{start_dt.day}〜{end_dt.month}/{end_dt.day}"
    header_ax.text(0.94, 0.70, period, fontsize=20,
                   ha='right', va='center', color='white', fontweight='bold')

    # 下段: 狙い目DAY / 激混みDAYのバッジ
    df_sorted = df.sort_values('avg_wait').reset_index(drop=True)
    best = df_sorted.iloc[0]
    worst = df_sorted.iloc[-1]
    best_dt = datetime.strptime(best['date'], '%Y-%m-%d')
    worst_dt = datetime.strptime(worst['date'], '%Y-%m-%d')
    best_day = get_day_of_week_ja(best['date'])
    worst_day = get_day_of_week_ja(worst['date'])

    header_ax.add_patch(FancyBboxPatch(
        (0.04, 0.10), 0.44, 0.36,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='#7CC07F', edgecolor='none',
    ))
    header_ax.text(0.26, 0.36, "★ 狙い目DAY",
                   fontsize=14, ha='center', va='center',
                   color='white', fontweight='bold')
    header_ax.text(0.26, 0.18,
                   f"{best_dt.month}/{best_dt.day}({best_day}) ±{best['avg_wait']:.0f}分",
                   fontsize=15, ha='center', va='center',
                   color='white', fontweight='bold')

    header_ax.add_patch(FancyBboxPatch(
        (0.52, 0.10), 0.44, 0.36,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='#E84C5C', edgecolor='none',
    ))
    header_ax.text(0.74, 0.36, "▲ 激混みDAY",
                   fontsize=14, ha='center', va='center',
                   color='white', fontweight='bold')
    header_ax.text(0.74, 0.18,
                   f"{worst_dt.month}/{worst_dt.day}({worst_day}) ±{worst['avg_wait']:.0f}分",
                   fontsize=15, ha='center', va='center',
                   color='white', fontweight='bold')

    # ============================================================
    # 本体: 7日間バー (中央 60%)
    # ============================================================
    body_ax = fig.add_axes([0.04, 0.16, 0.92, 0.60])
    body_ax.set_xlim(0, 1)
    body_ax.set_ylim(0, 1)
    body_ax.axis('off')

    # 列見出し
    body_ax.text(0.03, 0.97, "日付", fontsize=12,
                 ha='left', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.text(0.30, 0.97, "混雑度", fontsize=12,
                 ha='left', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.text(0.97, 0.97, "平均待ち", fontsize=12,
                 ha='right', va='top', color=TEXT_SECONDARY, fontweight='bold')
    body_ax.add_patch(plt.Rectangle((0.0, 0.93), 1.0, 0.003,
                                     facecolor=DIVIDER, edgecolor='none'))

    # 元順 (日付昇順) で並べる
    n = len(df)
    row_top = 0.86
    row_h = min(0.115, 0.86 / max(n, 1))
    max_wait = max(df['avg_wait'].max(), 80.0)

    for i, row in df.iterrows():
        y = row_top - i * row_h
        dt = datetime.strptime(row['date'], '%Y-%m-%d')
        day = get_day_of_week_ja(row['date'])
        is_weekend = day in ('土', '日')

        bg_color = '#FFF6F8' if is_weekend else '#F7F9FB'
        body_ax.add_patch(FancyBboxPatch(
            (0.0, y - row_h * 0.85), 1.0, row_h * 0.85,
            boxstyle="round,pad=0.005,rounding_size=0.015",
            facecolor=bg_color, edgecolor='none',
        ))

        # 日付
        date_label = f"{dt.month}/{dt.day}"
        day_color = '#E84C5C' if day == '日' else ('#1F8FBE' if day == '土' else TEXT_PRIMARY)
        body_ax.text(0.03, y - row_h * 0.42, date_label,
                     fontsize=18, ha='left', va='center',
                     color=TEXT_PRIMARY, fontweight='bold')
        body_ax.text(0.13, y - row_h * 0.42, f"({day})",
                     fontsize=14, ha='left', va='center',
                     color=day_color, fontweight='bold')

        # 混雑バー
        bar_x = 0.30
        bar_w_max = 0.55
        bar_w = (row['avg_wait'] / max_wait) * bar_w_max
        bar_color = _congestion_color(row['avg_wait'])
        body_ax.add_patch(FancyBboxPatch(
            (bar_x, y - row_h * 0.55), bar_w, row_h * 0.30,
            boxstyle="round,pad=0.002,rounding_size=0.012",
            facecolor=bar_color, edgecolor='none',
        ))
        body_ax.text(bar_x + 0.01, y - row_h * 0.40,
                     _congestion_label(row['avg_wait']),
                     fontsize=11, ha='left', va='center',
                     color='white', fontweight='bold')

        # ランクバッジ
        rank = int(row['rank'])
        rank_emoji = '★' if rank == 1 else ('▲' if rank == n else '・')
        if rank == 1:
            body_ax.text(0.20, y - row_h * 0.42, rank_emoji,
                         fontsize=16, ha='center', va='center',
                         color='#7CC07F', fontweight='bold')
        elif rank == n:
            body_ax.text(0.20, y - row_h * 0.42, rank_emoji,
                         fontsize=16, ha='center', va='center',
                         color='#E84C5C', fontweight='bold')

        # 平均待ち
        body_ax.text(0.97, y - row_h * 0.42,
                     f"{row['avg_wait']:.0f}分",
                     fontsize=18, ha='right', va='center',
                     color=accent, fontweight='bold')

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
    footer_ax.text(0.5, 0.65, "保存して旅行カレンダーの参考に♪",
                   fontsize=15, ha='center', va='center',
                   color=TEXT_PRIMARY, fontweight='bold')
    footer_ax.text(0.5, 0.30,
                   f"毎週日曜21時に翌週ランキングを投稿  {handle}",
                   fontsize=12, ha='center', va='center',
                   color=accent, fontweight='bold')

    plt.savefig(output_file, dpi=100, facecolor=LIGHT_BG,
                bbox_inches=None, pad_inches=0)
    plt.close()


# =============================================================================
# 公開関数
# =============================================================================
def generate_weekly_ranking_image(start_date: str, park: str = 'sea',
                                   days: int = 7,
                                   output_dir: str = 'predictions_x',
                                   handle: str = '@disney_ai_wait'):
    """週間ランキング画像を生成。 (image_path, dataframe) を返す"""
    os.makedirs(output_dir, exist_ok=True)
    df = _build_week(start_date, park, days=days)
    if df is None or df.empty:
        print(f"⚠️ {start_date} {park}: 週間予測データが取れませんでした")
        return None, None

    output_file = os.path.join(
        output_dir, f"ig_weekly_{park}_{start_date}.png"
    )
    _draw_weekly_ranking(df, park, output_file, handle=handle)
    print(f"✅ 週間ランキング画像生成: {output_file}")
    return output_file, df


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str,
                        default=datetime.now().strftime('%Y-%m-%d'),
                        help='起点日 (デフォルト: 今日)')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    args = parser.parse_args()
    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    for p in parks:
        generate_weekly_ranking_image(args.start, park=p, days=args.days)
