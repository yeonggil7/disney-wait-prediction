#!/usr/bin/env python3
"""
朝7時の「今日行く人へ」投稿スクリプト

朝イチで「行くべき / 避けるべき」アトラクションを、
当日のAI予測から抽出して投稿する。

設計:
- 朝イチ（9:00）の予測待ち時間が低い人気アトラクション = 行くべき
- 朝イチで既に高待ち時間 = 避けて午後・閉園前狙い
- 閉園前判定（21:00閉園、20:00時点≤30分が候補）も併記
"""

import os
import sys
import random
import argparse
import math
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
    _twitter_len,
    _trim_tweet,
    _get_weekday_ja,
    SEA_SHORT_NAMES,
    LAND_SHORT_NAMES,
)
from generate_x_heatmap import (
    generate_sea_heatmap,
    generate_land_heatmap,
    get_sea_closures,
    get_land_closures,
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES,
)
from closing_time_helper import (
    get_park_hours,
    compute_pre_close_candidates,
    format_close_judge_block_short,
    format_pre_close_candidates,
)


MORNING_GREETINGS = [
    "おはようございます！",
    "Good morning!",
]

MORNING_CTA = [
    "今日行く人はいいねで教えて！",
    "保存して当日チェックしてね",
    "朝イチで動く人をフォロー！毎朝7時にお届け中",
    "今日も楽しんできてね！",
]


def _round_up_10(x):
    return int(math.ceil(max(x, 0) / 10) * 10)


def _get_morning_split(date_str: str, park: str):
    """朝イチの予測から「行くべき / 避けるべき」を分類して返す。

    Returns
    -------
    dict | None: {
        'go_first': [(short_name, wait_min), ...],   # 9:00時点が短い → 朝イチ突撃
        'avoid_morning': [(short_name, max_wait), ...],  # 9:00時点で既に長い → 午後狙い
        'predictions': pd.DataFrame,
        'short_names': dict,
        'closures': dict,
        'congestion': str,
        'congestion_emoji': str,
    }
    """
    if park == 'sea':
        from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
        predictor = DisneySeaWaitTimePredictorV3()
        targets = SEA_TARGET_ATTRACTIONS
        short = SEA_SHORT_NAMES
        closures = get_sea_closures(date_str)
    else:
        from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
        predictor = DisneyLandWaitTimePredictorV3()
        targets = LAND_TARGET_ATTRACTIONS
        short = LAND_SHORT_NAMES
        closures = get_land_closures(date_str)

    attractions = [a for a in targets if a not in closures]
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]
    predictions = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)
    if predictions is None or predictions.empty:
        return None

    # 朝イチ = 9:00 の予測
    morning = predictions[predictions['time'] == '09:00']
    morning_map = {row['attraction_name']: row['predicted_wait_time'] for _, row in morning.iterrows()}
    max_by_attr = predictions.groupby('attraction_name')['predicted_wait_time'].max()

    go_first = []
    avoid_morning = []
    for attr in attractions:
        if attr not in morning_map:
            continue
        m_wait = _round_up_10(morning_map[attr])
        max_wait = _round_up_10(max_by_attr.get(attr, 0))
        sname = short.get(attr, attr[:8])
        if m_wait <= 30:
            go_first.append((sname, m_wait))
        elif max_wait >= 60 and m_wait >= 40:
            avoid_morning.append((sname, max_wait))

    go_first.sort(key=lambda x: x[1])
    avoid_morning.sort(key=lambda x: x[1], reverse=True)

    avg = predictions['predicted_wait_time'].mean()
    if avg >= 60:
        congestion, emoji = '激混み', '🔴'
    elif avg >= 40:
        congestion, emoji = '混雑', '🟠'
    elif avg >= 25:
        congestion, emoji = 'やや混雑', '🟡'
    else:
        congestion, emoji = '空いてる', '🟢'

    return {
        'go_first': go_first,
        'avoid_morning': avoid_morning,
        'predictions': predictions,
        'short_names': short,
        'closures': closures,
        'congestion': congestion,
        'congestion_emoji': emoji,
    }


def create_morning_tweet(date_str: str, park: str) -> str:
    """朝7時用：今日行く人への朝イチ判断ツイート"""
    day_name = _get_weekday_ja(date_str)
    dt = datetime.strptime(date_str, "%Y-%m-%d")

    greeting = random.choice(MORNING_GREETINGS)
    cta = random.choice(MORNING_CTA)

    if park == "sea":
        emoji, name = "🌊", "ディズニーシー"
        display = SEA_DISPLAY_NAMES
        tags = "#TDS #TDR_now"
        park_key = 'sea'
    else:
        emoji, name = "🏰", "ディズニーランド"
        display = LAND_DISPLAY_NAMES
        tags = "#TDL #TDR_now"
        park_key = 'land'

    info = _get_morning_split(date_str, park)
    _, closing = get_park_hours(date_str, park_key)

    tweet = f"{greeting}\n"
    tweet += f"{emoji} 今日{name}行く人へ\n"
    tweet += f"{dt.month}/{dt.day}({day_name})"

    if info:
        tweet += f" {info['congestion_emoji']}{info['congestion']}\n\n"

        # 朝イチで行くべき
        if info['go_first']:
            tweet += "🚀 朝イチで行くべき\n"
            for n, w in info['go_first'][:3]:
                tweet += f"・{n} 9:00時点 約{w}分\n"

        # 朝イチで避けるべき
        if info['avoid_morning']:
            tweet += "\n⚠️ 朝イチは避ける(午後or夜狙い)\n"
            for n, w in info['avoid_morning'][:3]:
                tweet += f"・{n} 最大{w}分\n"

        # 閉園前候補
        candidates = compute_pre_close_candidates(
            info['predictions'],
            closing_time=closing,
            short_names=info['short_names'],
            excluded=info['closures'].keys(),
        )
        if candidates:
            tweet += "\n🌙 夜の候補:\n"
            tweet += format_pre_close_candidates(candidates, closing_time=closing, max_n=3) + "\n"

        tweet += format_close_judge_block_short(closing) + "\n"
    else:
        tweet += "\n\n"

    if info and info['closures']:
        closed_names = [display.get(a, a)[:6] for a in info['closures'].keys()]
        tweet += f"※休止: {', '.join(closed_names)}\n"

    tweet += f"\n{cta}\n"
    tweet += tags

    return _trim_tweet(tweet)


def main():
    parser = argparse.ArgumentParser(description="朝7時：今日行く人への朝イチ判断投稿")
    today = datetime.now().strftime("%Y-%m-%d")
    parser.add_argument("--date", "-d", type=str, default=today)
    parser.add_argument("--post", "-p", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sea-only", action="store_true")
    parser.add_argument("--land-only", action="store_true")
    parser.add_argument("--no-image", action="store_true",
                        help="画像を生成・添付しない（テキストのみ）")
    parser.add_argument("--output", "-o", type=str, default="predictions_x")
    args = parser.parse_args()

    date = args.date
    random.seed(datetime.now().timetuple().tm_yday)

    print("=" * 60)
    print("🌅 朝7時：今日行く人への朝イチ判断")
    print(f"📅 {date}")
    print("=" * 60)

    if args.post and not args.dry_run:
        if not check_connection():
            print("❌ 接続失敗")
            return 1

    posted = 0

    if not args.land_only:
        sea_img = None
        if not args.no_image:
            print("\n🌊 シー ヒートマップ生成中...")
            sea_img = generate_sea_heatmap(date, args.output)
        sea_tweet = create_morning_tweet(date, "sea")
        print(sea_tweet)
        print(f"📊 {_twitter_len(sea_tweet)}/280")

        if args.post and not args.dry_run:
            print("\n📤 シー投稿中...")
            images = [sea_img] if sea_img else None
            if post_to_twitter(sea_tweet, images):
                posted += 1

    if not args.sea_only:
        land_img = None
        if not args.no_image:
            print("\n🏰 ランド ヒートマップ生成中...")
            land_img = generate_land_heatmap(date, args.output)
        land_tweet = create_morning_tweet(date, "land")
        print(land_tweet)
        print(f"📊 {_twitter_len(land_tweet)}/280")

        if args.post and not args.dry_run:
            print("\n📤 ランド投稿中...")
            import time
            time.sleep(5)
            images = [land_img] if land_img else None
            if post_to_twitter(land_tweet, images):
                posted += 1

    if args.post and not args.dry_run:
        print(f"\n✅ {posted}件投稿完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
