#!/usr/bin/env python3
"""
昼12時の「午前のおさらい・今からどう動くか」投稿スクリプト

設計:
- 今日のAI予測から、午前(9:00-12:00)に最も混雑が高かった/予想されたアトラクション
- 午後(13:00-17:00)に空きが期待できるアトラクション
- 閉園前判定（21:00閉園、20:00時点≤30分が候補）も併記
- 「今から入る人 / 既に入っている人」両方に向けた行動指針

リアルタイムの実測データは現状取得していないため、予測ベースで
「今からの動き方」を提示する。将来 daily_scrape を 12 時前にも回せば
"予測 vs 実測" のズレ表示に拡張可能。
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
    format_close_judge_block_short,
    format_pre_close_candidates,
)


NOON_OPENINGS = [
    "今からディズニー入る人へ",
    "午前のおさらいです",
    "ここからの動き方が大事",
]

NOON_CTA = [
    "保存して午後の参考に！",
    "刺さったらフォロー、毎日12時に更新中",
    "今日行ってる人はリプで「午前どうだった?」教えて！",
]


def _round_up_10(x):
    return int(math.ceil(max(x, 0) / 10) * 10)


def _get_noon_insights(date_str: str, park: str):
    """午前ピーク + 午後の空き候補 + 閉園前候補を返す"""
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

    morning = predictions[(predictions['time'] >= '09:00') & (predictions['time'] <= '12:00')]
    afternoon = predictions[(predictions['time'] >= '13:00') & (predictions['time'] <= '17:00')]

    # 午前ピーク（最大値）
    morning_peak = []
    if not morning.empty:
        m_max = morning.groupby('attraction_name')['predicted_wait_time'].max()
        for attr in attractions:
            if attr in m_max.index:
                morning_peak.append((short.get(attr, attr[:8]), _round_up_10(m_max[attr])))
        morning_peak.sort(key=lambda x: x[1], reverse=True)

    # 午後空き候補（13-17 の最小が 30 分以下）
    afternoon_slots = []
    if not afternoon.empty:
        a_min = afternoon.groupby('attraction_name')['predicted_wait_time'].min()
        for attr in attractions:
            if attr not in a_min.index:
                continue
            wait = _round_up_10(a_min[attr])
            if wait <= 30:
                afternoon_slots.append((short.get(attr, attr[:8]), wait))
        afternoon_slots.sort(key=lambda x: x[1])

    return {
        'morning_peak': morning_peak,
        'afternoon_slots': afternoon_slots,
        'predictions': predictions,
        'short_names': short,
        'closures': closures,
    }


def create_noon_tweet(date_str: str, park: str) -> str:
    day_name = _get_weekday_ja(date_str)
    dt = datetime.strptime(date_str, '%Y-%m-%d')

    opener = random.choice(NOON_OPENINGS)
    cta = random.choice(NOON_CTA)

    if park == 'sea':
        emoji, name = '🌊', 'ディズニーシー'
        tags = '#TDS #TDR_now'
        park_key = 'sea'
    else:
        emoji, name = '🏰', 'ディズニーランド'
        tags = '#TDL #TDR_now'
        park_key = 'land'

    insights = _get_noon_insights(date_str, park)
    _, closing = get_park_hours(date_str, park_key)

    tweet = f"{emoji} {opener}\n"
    tweet += f"今日の{name} {dt.month}/{dt.day}({day_name}) AI予測おさらい\n\n"

    if insights:
        if insights['morning_peak']:
            tweet += "📈 午前ピーク\n"
            for n, w in insights['morning_peak'][:3]:
                tweet += f"・{n} 最大{w}分\n"

        if insights['afternoon_slots']:
            tweet += "\n🍱 午後の空きが見える候補\n"
            for n, w in insights['afternoon_slots'][:3]:
                tweet += f"・{n} 最小{w}分前後\n"

        candidates = compute_pre_close_candidates(
            insights['predictions'],
            closing_time=closing,
            short_names=insights['short_names'],
            excluded=insights['closures'].keys(),
        )
        if candidates:
            tweet += "\n🌙 夜の候補:\n"
            tweet += format_pre_close_candidates(candidates, closing_time=closing, max_n=3) + "\n"

        tweet += format_close_judge_block_short(closing) + "\n"
    else:
        tweet += "\n"

    tweet += f"\n{cta}\n"
    tweet += tags

    return _trim_tweet(tweet)


def main():
    parser = argparse.ArgumentParser(description='昼12時：午前のおさらい・今からどう動くか')
    today = datetime.now().strftime('%Y-%m-%d')
    parser.add_argument('--date', '-d', type=str, default=today)
    parser.add_argument('--post', '-p', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    args = parser.parse_args()

    date = args.date
    random.seed(datetime.now().timetuple().tm_yday + 12)

    print('=' * 60)
    print('🍱 昼12時：午前のおさらい・今からどう動くか')
    print(f'📅 {date}')
    print('=' * 60)

    if args.post and not args.dry_run:
        if not check_connection():
            print('❌ 接続失敗')
            return 1

    posted = 0

    if not args.land_only:
        sea_tweet = create_noon_tweet(date, 'sea')
        print(sea_tweet)
        print(f'📊 {_twitter_len(sea_tweet)}/280')
        if args.post and not args.dry_run:
            print('\n📤 シー投稿中...')
            if post_to_twitter(sea_tweet):
                posted += 1

    if not args.sea_only:
        land_tweet = create_noon_tweet(date, 'land')
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
