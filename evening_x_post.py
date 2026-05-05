#!/usr/bin/env python3
"""
夕方17時の「今から入る人へ」投稿スクリプト

設計:
- 17時から入園する人 / これから残り時間を勝負する人向け
- 中心テーマは「閉園前に乗れるか判定」
- 21:00閉園の場合、20:00時点で30分以下なら候補
- 20:30以降は乗れない可能性が高い
- 18-20時の予測待ち時間も補足
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
    format_close_judge_block,
    format_pre_close_candidates,
)


EVENING_OPENINGS = [
    "今から入る人へ",
    "残り時間で勝負する人へ",
    "閉園前に乗れる候補まとめ",
]

EVENING_CTA = [
    "保存して21時直前まで参考に！",
    "夜狙い派はフォローしておくと便利",
    "明日の予測は20時に投稿します",
]


def _round_up_10(x):
    return int(math.ceil(max(x, 0) / 10) * 10)


def _get_evening_insights(date_str: str, park: str):
    """夜の候補と閉園前判定の元データを返す"""
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
    time_slots = [f"{h:02d}:{m:02d}" for h in range(17, 22) for m in (0, 30)]
    predictions = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)
    if predictions is None or predictions.empty:
        return None

    # 18:00 と 19:00 のスナップショットを参考値として
    snap_18 = predictions[predictions['time'] == '18:00']
    snap_19 = predictions[predictions['time'] == '19:00']
    waits_18 = {row['attraction_name']: _round_up_10(row['predicted_wait_time']) for _, row in snap_18.iterrows()}
    waits_19 = {row['attraction_name']: _round_up_10(row['predicted_wait_time']) for _, row in snap_19.iterrows()}

    return {
        'predictions': predictions,
        'short_names': short,
        'closures': closures,
        'waits_18': waits_18,
        'waits_19': waits_19,
        'attractions': attractions,
    }


def create_evening_tweet(date_str: str, park: str) -> str:
    day_name = _get_weekday_ja(date_str)
    dt = datetime.strptime(date_str, '%Y-%m-%d')

    opener = random.choice(EVENING_OPENINGS)
    cta = random.choice(EVENING_CTA)

    if park == 'sea':
        emoji, name = '🌊', 'ディズニーシー'
        tags = '#TDS #TDR_now'
        park_key = 'sea'
    else:
        emoji, name = '🏰', 'ディズニーランド'
        tags = '#TDL #TDR_now'
        park_key = 'land'

    insights = _get_evening_insights(date_str, park)
    _, closing = get_park_hours(date_str, park_key)

    tweet = f"{emoji} {opener}\n"
    tweet += f"今日の{name} {dt.month}/{dt.day}({day_name})\n\n"

    if insights:
        candidates = compute_pre_close_candidates(
            insights['predictions'],
            closing_time=closing,
            short_names=insights['short_names'],
            excluded=insights['closures'].keys(),
        )

        tweet += "🌙 夜の候補:\n"
        tweet += format_pre_close_candidates(candidates, closing_time=closing, max_n=4) + "\n"

        # 19:00 時点の高待ち（避けた方がいい）
        if insights['waits_19']:
            short = insights['short_names']
            high19 = sorted(
                [(short.get(a, a[:8]), w) for a, w in insights['waits_19'].items() if w >= 60],
                key=lambda x: x[1], reverse=True,
            )[:3]
            if high19:
                tweet += "\n⛔ 19:00時点で長め\n"
                for n, w in high19:
                    tweet += f"・{n} 約{w}分\n"

        tweet += "\n" + format_close_judge_block(closing) + "\n"
    else:
        tweet += "\n"

    tweet += f"\n{cta}\n"
    tweet += tags

    return _trim_tweet(tweet)


def main():
    parser = argparse.ArgumentParser(description='夕方17時：今から入る人へ・閉園前判定')
    today = datetime.now().strftime('%Y-%m-%d')
    parser.add_argument('--date', '-d', type=str, default=today)
    parser.add_argument('--post', '-p', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    args = parser.parse_args()

    date = args.date
    random.seed(datetime.now().timetuple().tm_yday + 17)

    print('=' * 60)
    print('🌆 夕方17時：今から入る人へ・閉園前判定')
    print(f'📅 {date}')
    print('=' * 60)

    if args.post and not args.dry_run:
        if not check_connection():
            print('❌ 接続失敗')
            return 1

    posted = 0

    if not args.land_only:
        sea_tweet = create_evening_tweet(date, 'sea')
        print(sea_tweet)
        print(f'📊 {_twitter_len(sea_tweet)}/280')
        if args.post and not args.dry_run:
            print('\n📤 シー投稿中...')
            if post_to_twitter(sea_tweet):
                posted += 1

    if not args.sea_only:
        land_tweet = create_evening_tweet(date, 'land')
        print(land_tweet)
        print(f'📊 {_twitter_len(land_tweet)}/280')
        if args.post and not args.dry_run:
            print('\n📤 ランド投稿中...')
            import time
            time.sleep(5)
            if post_to_twitter(land_tweet):
                posted += 1

    if args.post and not args.dry_run:
        print(f'\n✅ {posted}件投稿完了')
    return 0


if __name__ == '__main__':
    sys.exit(main())
