#!/usr/bin/env python3
"""
週間混雑ランキング投稿スクリプト

毎週日曜21時 (CIで実行) に、翌週月曜〜日曜の混雑度ランキングを Instagram に投稿。

使い方:
    python weekly_ranking_post.py --dry-run
    python weekly_ranking_post.py --post                       # 翌週分を投稿
    python weekly_ranking_post.py --post --start 2026-04-21    # 起点日を指定
    python weekly_ranking_post.py --post --carousel            # シー+ランドを1投稿に
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

from generate_weekly_ranking_image import generate_weekly_ranking_image
from generate_instagram_heatmap import PARK_THEMES
from generate_x_heatmap import get_day_of_week_ja


HASHTAGS_COMMON = [
    '#ディズニー', '#disney', '#tdr', '#tdr_now',
    '#ディズニー混雑', '#ディズニー予測', '#ディズニー旅行',
    '#aiディズニー', '#ディズニー好きな人と繋がりたい',
    '#ディズニーカレンダー', '#週末ディズニー',
]
HASHTAGS_SEA = [
    '#ディズニーシー', '#tokyodisneysea', '#tds', '#東京ディズニーシー',
    '#ソアリン', '#fantasysprings', '#アナとエルサのフローズンジャーニー',
]
HASHTAGS_LAND = [
    '#ディズニーランド', '#tokyodisneyland', '#tdl', '#東京ディズニーランド',
    '#美女と野獣', '#美女と野獣魔法のものがたり', '#ビッグサンダーマウンテン',
]


def _build_caption(df, park: str, handle: str = '@disney_ai_wait') -> str:
    """週間ランキングのキャプション"""
    if park == 'sea':
        emoji = '🌊'
        park_name = 'ディズニーシー'
        tags = HASHTAGS_SEA + HASHTAGS_COMMON
    else:
        emoji = '🏰'
        park_name = 'ディズニーランド'
        tags = HASHTAGS_LAND + HASHTAGS_COMMON

    sorted_df = df.sort_values('avg_wait').reset_index(drop=True)
    best = sorted_df.iloc[0]
    worst = sorted_df.iloc[-1]
    best_dt = datetime.strptime(best['date'], '%Y-%m-%d')
    worst_dt = datetime.strptime(worst['date'], '%Y-%m-%d')
    start_dt = datetime.strptime(df.iloc[0]['date'], '%Y-%m-%d')
    end_dt = datetime.strptime(df.iloc[-1]['date'], '%Y-%m-%d')

    lines = [
        f"{emoji} {park_name} AI 週間混雑ランキング",
        f"📅 {start_dt.month}/{start_dt.day}〜{end_dt.month}/{end_dt.day} の予測",
        "",
        f"★ 狙い目DAY → {best_dt.month}/{best_dt.day}({get_day_of_week_ja(best['date'])})  平均±{best['avg_wait']:.0f}分",
        f"▲ 激混みDAY → {worst_dt.month}/{worst_dt.day}({get_day_of_week_ja(worst['date'])})  平均±{worst['avg_wait']:.0f}分",
        "",
        "【日別 平均待ち時間予測】",
    ]
    for _, row in df.iterrows():
        dt = datetime.strptime(row['date'], '%Y-%m-%d')
        day = get_day_of_week_ja(row['date'])
        rank_mark = ''
        if int(row['rank']) == 1:
            rank_mark = '  ★狙い目'
        elif int(row['rank']) == len(df):
            rank_mark = '  ▲激混み'
        lines.append(
            f"・{dt.month}/{dt.day}({day})  ±{row['avg_wait']:.0f}分{rank_mark}"
        )

    lines += [
        "",
        "💡 旅行プラン作成のヒント",
        "・狙い目DAYは平日 or 雨予報の日を狙うとさらに快適",
        "・週末・祝日はホテル泊で開園ダッシュ推奨",
        "",
        "―――――――――――――――",
        "📲 毎日20時に翌日の予測を投稿中",
        f"👉 フォローはプロフィールから {handle}",
        "💾 保存して旅行カレンダーに♪",
        "",
        "※AI予測です。実際の混雑とは異なる場合があります",
        "",
        ' '.join(tags),
    ]

    cap = '\n'.join(lines)
    if len(cap) > 2200:
        cap = cap[:2197] + '...'
    return cap


def _build_carousel_caption(dfs: dict, handle: str = '@disney_ai_wait') -> str:
    """シー+ランド合体カルーセル用キャプション"""
    parks = list(dfs.keys())
    first = dfs[parks[0]]
    start_dt = datetime.strptime(first.iloc[0]['date'], '%Y-%m-%d')
    end_dt = datetime.strptime(first.iloc[-1]['date'], '%Y-%m-%d')

    lines = [
        f"📅 AI 週間混雑ランキング ({start_dt.month}/{start_dt.day}〜{end_dt.month}/{end_dt.day})",
        "",
        "👉 スワイプでシー&ランドを比較",
        "",
    ]
    for park, df in dfs.items():
        emoji = PARK_THEMES[park]['emoji']
        park_name = PARK_THEMES[park]['name']
        sorted_df = df.sort_values('avg_wait').reset_index(drop=True)
        best = sorted_df.iloc[0]
        worst = sorted_df.iloc[-1]
        best_dt = datetime.strptime(best['date'], '%Y-%m-%d')
        worst_dt = datetime.strptime(worst['date'], '%Y-%m-%d')
        lines += [
            f"{emoji} {park_name}",
            f"  ★狙い目: {best_dt.month}/{best_dt.day}({get_day_of_week_ja(best['date'])}) ±{best['avg_wait']:.0f}分",
            f"  ▲激混み: {worst_dt.month}/{worst_dt.day}({get_day_of_week_ja(worst['date'])}) ±{worst['avg_wait']:.0f}分",
            "",
        ]
    lines += [
        "―――――――――――――――",
        "📲 毎日20時に翌日の予測を投稿中",
        f"💾 保存推奨 / フォロー {handle}",
        "",
        ' '.join(set(HASHTAGS_SEA + HASHTAGS_LAND + HASHTAGS_COMMON)),
    ]
    cap = '\n'.join(lines)
    if len(cap) > 2200:
        cap = cap[:2197] + '...'
    return cap


def main():
    parser = argparse.ArgumentParser(description='Instagram 週間ランキング投稿')
    # デフォルト: 来週月曜起点
    today = datetime.now()
    days_to_mon = (7 - today.weekday()) % 7 or 7
    default_start = (today + timedelta(days=days_to_mon)).strftime('%Y-%m-%d')

    parser.add_argument('--start', type=str, default=default_start,
                        help='起点日 (デフォルト: 次の月曜)')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    parser.add_argument('--carousel', action='store_true')
    parser.add_argument('--post', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.sea_only:
        parks = ['sea']
    elif args.land_only:
        parks = ['land']
    elif args.park == 'both':
        parks = ['sea', 'land']
    else:
        parks = [args.park]

    print(f"\n📅 週間ランキング投稿: 起点{args.start} ({args.days}日) parks={parks}\n")

    images = {}
    dfs = {}
    captions = {}

    for park in parks:
        img, df = generate_weekly_ranking_image(args.start, park=park, days=args.days)
        if img is None:
            continue
        images[park] = img
        dfs[park] = df
        captions[park] = _build_caption(df, park)

        print("\n" + "=" * 60)
        print(f"{PARK_THEMES[park]['emoji']} 【{PARK_THEMES[park]['name']}】キャプション:")
        print("-" * 60)
        print(captions[park])
        print("-" * 60)
        print(f"📏 文字数: {len(captions[park])}/2200")
        print(f"🖼️  画像: {img}")

    if not images:
        print("❌ 投稿対象なし")
        return 1

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
            combo = _build_carousel_caption({p: dfs[p] for p in parks if p in dfs})
            print(f"\n🎠 カルーセル投稿中（{len(ordered_imgs)}枚）...")
            if poster.post_carousel(ordered_imgs, combo):
                posted += 1
        else:
            for park in parks:
                if park not in images:
                    continue
                print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} 週間ランキング投稿中...")
                if poster.post_photo(images[park], captions[park]):
                    posted += 1
                time.sleep(15)

        print(f"\n✅ {posted}件の投稿が完了しました")
    elif args.dry_run:
        print(f"\n🔍 ドライラン: {len(images)}件スキップ")
    else:
        print("\n💡 投稿するには --post を追加")

    return 0


if __name__ == '__main__':
    sys.exit(main())
