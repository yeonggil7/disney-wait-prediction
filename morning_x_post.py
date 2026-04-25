#!/usr/bin/env python3
"""
朝7時の「今日の予測」投稿スクリプト

当日パークに行く人向けに、今日の混雑予測をコンパクトに投稿。
既存の daily_x_post.py（20時の翌日予測）とは別に、
当日朝にリマインド的に投稿する。
"""

import os
import sys
import random
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from post_via_xharness import post_to_twitter, check_connection
from daily_x_post import (
    _get_prediction_insights,
    _twitter_len,
    _trim_tweet,
    _get_weekday_ja,
    _is_weekend,
)
from generate_x_heatmap import (
    generate_sea_heatmap,
    generate_land_heatmap,
    get_sea_closures,
    get_land_closures,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES,
)

MORNING_GREETINGS = [
    "おはようございます!",
    "おはようございます!",
    "Good morning!",
]

MORNING_CTA = [
    "今日行く方はいいねで教えて!",
    "参考になったら保存しておいてね!",
    "フォローで毎朝お届け!",
    "今日も楽しんできてね!",
]


def create_morning_tweet(date_str: str, park: str) -> str:
    """当日朝用のコンパクト予測ツイート"""
    day_name = _get_weekday_ja(date_str)
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    greeting = random.choice(MORNING_GREETINGS)
    cta = random.choice(MORNING_CTA)

    if park == "sea":
        insights = _get_prediction_insights(date_str, "sea")
        closures = get_sea_closures(date_str)
        emoji, name = "🌊", "ディズニーシー"
        display = SEA_DISPLAY_NAMES
        tags = "#TDS #ディズニーシー #TDR_now"
    else:
        insights = _get_prediction_insights(date_str, "land")
        closures = get_land_closures(date_str)
        emoji, name = "🏰", "ディズニーランド"
        display = LAND_DISPLAY_NAMES
        tags = "#TDL #ディズニーランド #TDR_now"

    tweet = f"{greeting}\n"
    tweet += f"{emoji} 今日の{name} AI予測\n"
    tweet += f"{dt.month}/{dt.day}({day_name})"

    if insights:
        tweet += f" {insights['congestion_emoji']}{insights['congestion']}\n\n"
        for attr_name, wait in insights["attr_max_list"][:6]:
            tweet += f"▸ {attr_name} 最大{wait}分\n"
        tweet += f"\n⏰ 狙い目: {insights['calm_time']}〜\n"
    else:
        tweet += "\n\n"

    if closures:
        closed_names = [display.get(a, a)[:6] for a in closures.keys()]
        tweet += f"※休止: {', '.join(closed_names)}\n"

    tweet += f"\n{cta}\n"
    tweet += tags

    return _trim_tweet(tweet)


def main():
    parser = argparse.ArgumentParser(description="朝の今日の予測投稿")
    today = datetime.now().strftime("%Y-%m-%d")
    parser.add_argument("--date", "-d", type=str, default=today)
    parser.add_argument("--post", "-p", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sea-only", action="store_true")
    parser.add_argument("--land-only", action="store_true")
    parser.add_argument("--output", "-o", type=str, default="predictions_x")
    args = parser.parse_args()

    date = args.date
    random.seed(datetime.now().timetuple().tm_yday)

    print("=" * 60)
    print("🌅 朝のTDR AI予測投稿")
    print(f"📅 {date}")
    print("=" * 60)

    if args.post and not args.dry_run:
        if not check_connection():
            print("❌ 接続失敗")
            return 1

    posted = 0

    if not args.land_only:
        print("\n🌊 シー ヒートマップ生成中...")
        sea_img = generate_sea_heatmap(date, args.output)
        sea_tweet = create_morning_tweet(date, "sea")
        print(sea_tweet)
        print(f"📊 {_twitter_len(sea_tweet)}/280")

        if args.post and not args.dry_run and sea_img:
            print("\n📤 シー投稿中...")
            if post_to_twitter(sea_tweet, [sea_img]):
                posted += 1

    if not args.sea_only:
        print("\n🏰 ランド ヒートマップ生成中...")
        land_img = generate_land_heatmap(date, args.output)
        land_tweet = create_morning_tweet(date, "land")
        print(land_tweet)
        print(f"📊 {_twitter_len(land_tweet)}/280")

        if args.post and not args.dry_run and land_img:
            print("\n📤 ランド投稿中...")
            import time
            time.sleep(5)
            if post_to_twitter(land_tweet, [land_img]):
                posted += 1

    if args.post and not args.dry_run:
        print(f"\n✅ {posted}件投稿完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
