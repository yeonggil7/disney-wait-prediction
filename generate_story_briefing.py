"""
ストーリーズ用「朝のお知らせ / 夕方プレビュー」画像 (1080x1920) 生成モジュール

シンプルで一目で分かる構成:
  - 上部: 大きな日付 + 挨拶 ("☀️おはよう / 🌙明日は")
  - 中央: 大きな混雑度ラベル + 平均待ち時間
  - 下: 「★狙い目アトラクション」「▲最も混むアトラクション」「ピーク時間」
  - フッター: CTA

Variants:
  - mode='morning'  : 当日の予報を朝8時前後に
  - mode='preview'  : 翌日の予報を夕方17時前後に
  - mode='evening'  : 当日の答え合わせ速報 (実測あれば)
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
    PARK_THEMES,
)
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3


_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']


# =============================================================================
# データ
# =============================================================================
def _build_briefing(date_str: str, park: str) -> dict:
    """その日のサマリ (平均待ち / 狙い目 / 最も混むライド / ピーク時間) を返す"""
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
    if valid.empty:
        return None

    avg_wait = float(valid['predicted_wait_time'].mean())
    avg_by_time = valid.groupby('time')['predicted_wait_time'].mean()
    peak_time = avg_by_time.idxmax()

    # アトラクション別の最大混雑
    by_attr = valid.groupby('attraction_name')['predicted_wait_time'].agg(['mean', 'max'])
    busiest = by_attr['max'].idxmax()
    busiest_max = by_attr.loc[busiest, 'max']

    # 9:30〜19:00 で各アトラクションの最早 calm time
    window = valid[(valid['time'] >= '09:30') & (valid['time'] < '19:00')]
    calm_pick = None
    if not window.empty:
        # 最も低い平均待ちのアトラクション
        attr_min = window.groupby('attraction_name')['predicted_wait_time'].min()
        target_attr = attr_min.idxmin()
        sub = window[window['attraction_name'] == target_attr].sort_values('time')
        min_wait = sub['predicted_wait_time'].min()
        threshold = max(min_wait * 1.2, min_wait + 5)
        calm_rows = sub[sub['predicted_wait_time'] <= threshold]
        if not calm_rows.empty:
            calm_pick = (target_attr, calm_rows.iloc[0]['time'], min_wait)

    return {
        'date': date_str,
        'park': park,
        'avg_wait': avg_wait,
        'peak_time': peak_time,
        'busiest_attraction': short_map.get(busiest, busiest),
        'busiest_wait': busiest_max,
        'calm_pick': calm_pick,
        'short_map': short_map,
        'closures': closures,
    }


# =============================================================================
# 描画
# =============================================================================
def _congestion_label_color(avg_wait: float):
    if avg_wait >= 70:
        return ('激混み', '#E84C5C')
    if avg_wait >= 55:
        return ('混雑', '#F2A93B')
    if avg_wait >= 40:
        return ('やや混雑', '#F5D261')
    return ('快適', '#7CC07F')


def _draw_briefing(stats: dict, mode: str, output_file: str,
                    handle: str = '@disney_ai_wait'):
    """1080x1920 ストーリーズ画像を描画"""
    park = stats['park']
    theme = PARK_THEMES[park]
    accent = theme['accent']
    park_name = theme['name']
    date_str = stats['date']

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_ja = get_day_of_week_ja(date_str)

    if mode == 'morning':
        greeting = "おはよう ★"
        subtitle = "今日の予報"
    elif mode == 'preview':
        greeting = "明日のディズニー"
        subtitle = "翌日の予報"
    else:
        greeting = "本日のお疲れさま"
        subtitle = "本日の振り返り"

    fig = plt.figure(figsize=(10.8, 19.2), dpi=100, facecolor=LIGHT_BG)

    # ============================================================
    # ヘッダー (上 25%)
    # ============================================================
    header_ax = fig.add_axes([0, 0.75, 1, 0.25])
    header_ax.set_xlim(0, 1)
    header_ax.set_ylim(0, 1)
    header_ax.axis('off')

    header_ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=accent))
    header_ax.text(0.5, 0.76, greeting,
                   fontsize=46, ha='center', va='center',
                   color='white', fontweight='bold')
    header_ax.text(0.5, 0.50, park_name, fontsize=34,
                   ha='center', va='center', color='white', fontweight='bold')
    header_ax.text(0.5, 0.26,
                   f"{dt.month}月{dt.day}日({day_ja}) {subtitle}",
                   fontsize=24, ha='center', va='center', color='white')

    # ============================================================
    # 中央: 混雑度バッジ
    # ============================================================
    center_ax = fig.add_axes([0.05, 0.55, 0.90, 0.18])
    center_ax.set_xlim(0, 1)
    center_ax.set_ylim(0, 1)
    center_ax.axis('off')

    cong_label, cong_color = _congestion_label_color(stats['avg_wait'])
    center_ax.add_patch(FancyBboxPatch(
        (0.05, 0.10), 0.90, 0.80,
        boxstyle="round,pad=0.01,rounding_size=0.06",
        facecolor=cong_color, edgecolor='none',
    ))
    center_ax.text(0.5, 0.65, cong_label,
                   fontsize=44, ha='center', va='center',
                   color='white', fontweight='bold')
    center_ax.text(0.5, 0.30,
                   f"AI予測 平均 {stats['avg_wait']:.0f}分待ち",
                   fontsize=26, ha='center', va='center',
                   color='white', fontweight='bold')

    # ============================================================
    # 下: 3つのキー情報
    # ============================================================
    info_ax = fig.add_axes([0.05, 0.18, 0.90, 0.34])
    info_ax.set_xlim(0, 1)
    info_ax.set_ylim(0, 1)
    info_ax.axis('off')

    cards = []
    if stats.get('calm_pick'):
        attr_name, calm_time, min_wait = stats['calm_pick']
        short_name = stats['short_map'].get(attr_name, attr_name)
        cards.append(("★ 一番の狙い目",
                      f"{short_name}",
                      f"{calm_time}〜  最短{int(min_wait)}分", '#2BB673'))
    cards.append(("▲ 最も混むライド",
                  f"{stats['busiest_attraction']}",
                  f"最大 {int(stats['busiest_wait'])}分待ち", '#E84C5C'))
    cards.append(("● ピーク時間帯",
                  f"{stats['peak_time']}",
                  "前後を避けるとスムーズ", '#5B7FFF'))

    n = len(cards)
    card_h = 0.32
    gap = 0.02
    total_h = card_h * n + gap * (n - 1)
    start_y = (1 - total_h) / 2 + total_h
    for i, (label, value, sub, color) in enumerate(cards):
        y = start_y - (card_h + gap) * i
        info_ax.add_patch(FancyBboxPatch(
            (0.0, y - card_h), 1.0, card_h,
            boxstyle="round,pad=0.005,rounding_size=0.025",
            facecolor='#FFFFFF', edgecolor=color, linewidth=2.5,
        ))
        info_ax.text(0.04, y - 0.05, label,
                     fontsize=18, ha='left', va='top',
                     color=color, fontweight='bold')
        info_ax.text(0.96, y - 0.05, value,
                     fontsize=22, ha='right', va='top',
                     color=TEXT_PRIMARY, fontweight='bold')
        info_ax.text(0.04, y - card_h + 0.02, sub,
                     fontsize=15, ha='left', va='bottom',
                     color=TEXT_SECONDARY)

    # ============================================================
    # フッター (下 14%) — CTA
    # ============================================================
    footer_ax = fig.add_axes([0, 0, 1, 0.14])
    footer_ax.set_xlim(0, 1)
    footer_ax.set_ylim(0, 1)
    footer_ax.axis('off')

    footer_ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=accent, alpha=0.18))
    footer_ax.text(0.5, 0.65,
                   "詳しい時間帯別予報はフィード投稿へ",
                   fontsize=20, ha='center', va='center',
                   color=TEXT_PRIMARY, fontweight='bold')
    footer_ax.text(0.5, 0.30, handle,
                   fontsize=22, ha='center', va='center',
                   color=accent, fontweight='bold')

    plt.savefig(output_file, dpi=100, facecolor=LIGHT_BG,
                bbox_inches=None, pad_inches=0)
    plt.close()


# =============================================================================
# 公開関数
# =============================================================================
def generate_story_briefing(date_str: str, park: str = 'sea',
                             mode: str = 'morning',
                             output_dir: str = 'predictions_x',
                             handle: str = '@disney_ai_wait'):
    """ストーリーズ briefing 画像を生成。 (path, stats) を返す"""
    os.makedirs(output_dir, exist_ok=True)
    stats = _build_briefing(date_str, park)
    if stats is None:
        return None, None

    output_file = os.path.join(
        output_dir, f"ig_story_{mode}_{park}_{date_str}.png"
    )
    _draw_briefing(stats, mode, output_file, handle=handle)
    print(f"✅ ストーリーズbriefing生成: {output_file}")
    return output_file, stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str,
                        default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--mode', choices=['morning', 'preview', 'evening'],
                        default='morning')
    args = parser.parse_args()

    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    for p in parks:
        generate_story_briefing(args.date, park=p, mode=args.mode)
