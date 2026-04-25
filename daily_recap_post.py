#!/usr/bin/env python3
"""
答え合わせ投稿スクリプト

「昨日のAI予測 vs 実測」を Instagram に投稿するエントリポイント。
通常は実測データが揃った翌日 (=明けて0時以降) にCIで実行する想定。

使い方:
    python daily_recap_post.py --dry-run                   # 画像とキャプションだけ生成
    python daily_recap_post.py --post                      # 昨日分を投稿 (sea+land)
    python daily_recap_post.py --post --date 2026-04-19
    python daily_recap_post.py --post --carousel           # シー+ランドを1投稿カルーセルに
    python daily_recap_post.py --post --sea-only / --land-only
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from generate_recap_image import generate_recap_image
from generate_instagram_heatmap import PARK_THEMES


# ---------------------------------------------------------------------------
# キャプション
# ---------------------------------------------------------------------------
RECAP_HASHTAGS_COMMON = [
    '#ディズニー', '#disney', '#tdr', '#tdr_now',
    '#ディズニー待ち時間', '#ディズニー混雑', '#ディズニー予測',
    '#aiディズニー', '#ディズニー好きな人と繋がりたい', '#ディズニー旅行',
]

RECAP_HASHTAGS_SEA = [
    '#ディズニーシー', '#tokyodisneysea', '#tds', '#東京ディズニーシー',
    '#ソアリン', '#タワーオブテラー', '#トイストーリーマニア',
    '#アナとエルサのフローズンジャーニー', '#fantasysprings',
]
RECAP_HASHTAGS_LAND = [
    '#ディズニーランド', '#tokyodisneyland', '#tdl', '#東京ディズニーランド',
    '#美女と野獣', '#美女と野獣魔法のものがたり', '#ビッグサンダーマウンテン',
    '#プーさんのハニーハント', '#ベイマックス',
]


def _weekday_ja(date_str: str) -> str:
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]


def _build_caption(stats: dict, handle: str = '@disney_ai_wait') -> str:
    """答え合わせキャプション (〜2200文字)"""
    park = stats['park']
    date_str = stats['date']
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = _weekday_ja(date_str)

    if park == 'sea':
        emoji = '🌊'
        park_name = 'ディズニーシー'
        tags = RECAP_HASHTAGS_SEA + RECAP_HASHTAGS_COMMON
    else:
        emoji = '🏰'
        park_name = 'ディズニーランド'
        tags = RECAP_HASHTAGS_LAND + RECAP_HASHTAGS_COMMON

    try:
        sys.path.insert(0, str(PROJECT_DIR / 'scripts'))
        from trend_hashtags import get_trend_hashtags
        trend_tags = get_trend_hashtags(date=date_str, max_n=4, exclude=tags)
        if trend_tags:
            tags = trend_tags + tags
    except Exception:
        pass

    acc = stats['accuracy_within_10']
    mae = stats['overall_mae']
    per_attr = stats['per_attr']

    score_label = '優秀' if acc >= 70 else 'まずまず' if acc >= 50 else '修行中'

    # ベスト/ワースト
    best_row = per_attr.loc[per_attr['mae'].idxmin()]
    worst_row = per_attr.loc[per_attr['mae'].idxmax()]

    lines = [
        f"{emoji} {park_name} AI予測 答え合わせ",
        f"📅 {dt.month}月{dt.day}日({day}) の結果",
        "",
        f"🎯 ±10分以内的中率: {acc:.0f}%",
        f"📏 平均誤差: ±{mae:.0f}分",
        f"🏆 今日のAIスコア: {score_label}",
        "",
        "【アトラクション別 答え合わせ】",
    ]
    for _, row in per_attr.iterrows():
        err = row['mae']
        mark = '◎' if err <= 10 else '○' if err <= 20 else '△'
        lines.append(
            f"・{row['short_name']}: 予測{row['avg_pred']:.0f}分 / 実測{row['avg_actual']:.0f}分  {mark} ±{err:.0f}分"
        )

    lines += [
        "",
        f"💡 ベスト的中: {best_row['short_name']} (±{best_row['mae']:.0f}分)",
        f"⚠️ 要修行: {worst_row['short_name']} (±{worst_row['mae']:.0f}分)",
        "",
        "―――――――――――――――",
        "📲 毎日20時に翌日の予測を投稿中",
        f"👉 フォローはプロフィールから {handle}",
        "💾 保存して旅行プランに役立てて♪",
        "",
        "※AI予測です。実際の待ち時間とは異なる場合があります",
        "",
        ' '.join(tags),
    ]

    caption = '\n'.join(lines)
    if len(caption) > 2200:
        caption = caption[:2197] + '...'
    return caption


def _build_carousel_caption(stats_list: list, handle: str = '@disney_ai_wait') -> str:
    """シー+ランド合体カルーセル用キャプション"""
    if not stats_list:
        return ''
    date_str = stats_list[0]['date']
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = _weekday_ja(date_str)
    overall_acc = sum(s['accuracy_within_10'] for s in stats_list) / len(stats_list)
    overall_mae = sum(s['overall_mae'] for s in stats_list) / len(stats_list)

    head = [
        f"🎯 AI予測 答え合わせ ({dt.month}/{dt.day} {day})",
        "",
        f"📊 シー&ランド総合 ±10分以内的中: {overall_acc:.0f}%",
        f"📏 平均誤差: ±{overall_mae:.0f}分",
        "",
        "👉 スワイプでパーク別 答え合わせ",
        "",
    ]
    body = []
    for s in stats_list:
        park_name = PARK_THEMES[s['park']]['name']
        emoji = PARK_THEMES[s['park']]['emoji']
        body.append(
            f"{emoji} {park_name}: ±10分以内 {s['accuracy_within_10']:.0f}% / 平均誤差 ±{s['overall_mae']:.0f}分"
        )

    foot = [
        "",
        "―――――――――――――――",
        "📲 毎日20時に翌日の予測を投稿中",
        f"👉 フォロー&保存推奨 {handle}",
        "",
        ' '.join(set(RECAP_HASHTAGS_SEA + RECAP_HASHTAGS_LAND + RECAP_HASHTAGS_COMMON)),
    ]
    cap = '\n'.join(head + body + foot)
    if len(cap) > 2200:
        cap = cap[:2197] + '...'
    return cap


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Instagram 答え合わせ投稿')
    parser.add_argument('--date', type=str,
                        default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                        help='対象日 (デフォルト: 昨日)')
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    parser.add_argument('--carousel', action='store_true', help='シー+ランドを1投稿カルーセルに')
    parser.add_argument('--post', action='store_true', help='実際にInstagramへ投稿')
    parser.add_argument('--dry-run', action='store_true', help='画像とキャプションだけ生成')
    args = parser.parse_args()

    if args.sea_only:
        parks = ['sea']
    elif args.land_only:
        parks = ['land']
    elif args.park == 'both':
        parks = ['sea', 'land']
    else:
        parks = [args.park]

    date = args.date
    print(f"\n🎯 答え合わせ投稿: {date} (parks={parks})\n")

    images = {}
    stats_map = {}
    captions = {}

    for park in parks:
        img, stats = generate_recap_image(date, park=park)
        if img is None:
            print(f"⚠️ {park}: スキップ (実測 or 予測データ不足)")
            continue
        images[park] = img
        stats_map[park] = stats
        captions[park] = _build_caption(stats)

        print("\n" + "=" * 60)
        print(f"{PARK_THEMES[park]['emoji']} 【{PARK_THEMES[park]['name']}】キャプション:")
        print("-" * 60)
        print(captions[park])
        print("-" * 60)
        print(f"📏 文字数: {len(captions[park])}/2200")
        print(f"🖼️  画像: {img}")

    if not images:
        # データ未到着 (前日CSV未push 等) は CI を赤くせずスキップ
        print("⚠️ 投稿対象がありません（実測データ未着のためスキップ）")
        print("💡 ローカル daily_scrape.py が CSV を push 後、再実行してください")
        return 0

    if args.post and not args.dry_run:
        from post_via_instagram import (
            _get_default_poster, _select_backend, check_connection,
        )
        backend = _select_backend()
        print(f"\n📡 Instagram バックエンド: {backend}")
        if not check_connection():
            print("❌ Instagram 接続失敗")
            return 1
        poster = _get_default_poster()

        posted = 0
        if args.carousel and len(parks) > 1:
            ordered_imgs = [images[p] for p in parks if p in images]
            combo_caption = _build_carousel_caption([stats_map[p] for p in parks if p in stats_map])
            print(f"\n🎠 カルーセル投稿中（{len(ordered_imgs)}枚）...")
            if poster.post_carousel(ordered_imgs, combo_caption):
                posted += 1
        else:
            for park in parks:
                if park not in images:
                    continue
                print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} 答え合わせ投稿中...")
                if poster.post_photo(images[park], captions[park]):
                    posted += 1
                time.sleep(15)

        print(f"\n✅ {posted}件の投稿が完了しました")
    elif args.dry_run:
        print(f"\n🔍 ドライラン: {len(images)}件スキップ")
    else:
        print("\n💡 投稿するには --post オプションを追加してください")

    return 0


if __name__ == '__main__':
    sys.exit(main())
