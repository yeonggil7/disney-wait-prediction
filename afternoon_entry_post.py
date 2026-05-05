#!/usr/bin/env python3
"""
午後入園者向け 回り方ガイド投稿

- 14:00 投稿 → 15時入園者向け（残り約6時間）
- 16:00 投稿 → 17時入園者向け（残り約4時間）

予測データから「入園時点の待ち時間が短い順」でおすすめルートを提示。
閉園前の注意事項も付与する。
"""

import os
import sys
import math
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from post_via_xharness import post_to_twitter, check_connection
from closing_time_helper import get_park_hours, format_close_judge_block_short

from generate_x_heatmap import (
    get_sea_closures,
    get_land_closures,
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES,
)

SEA_SHORT = {
    'ソアリン': 'ソアリン',
    'アナとエルサ': 'アナ雪',
    'センターオブジアース': 'センター',
    'タワーオブテラー': 'タワテラ',
    'トイストーリーマニア': 'トイマニ',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーパン',
    'プラザグリーティング': 'プラグリ',
    'レイジングスピリッツ': 'レイジング',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
}

LAND_SHORT = {
    '美女と野獣の物語': '美女と野獣',
    'モンスターズ・インク': 'モンスターズ',
    'ミート・ミッキー': 'ミッキー',
    'プーさんのハニーハント': 'プーさん',
    'ベイマックスのハッピーライド': 'ベイマックス',
    'ビッグサンダーマウンテン': 'ビッグサンダー',
    'スプラッシュマウンテン': 'スプラッシュ',
}


def _round10(x):
    return int(math.ceil(max(x, 0) / 10) * 10)


def _twitter_len(text):
    WEIGHT1_RANGES = [
        (0x0000, 0x10FF), (0x2000, 0x200D),
        (0x2010, 0x201F), (0x2032, 0x2037),
    ]
    count = 0
    for ch in text:
        cp = ord(ch)
        w = 2
        for lo, hi in WEIGHT1_RANGES:
            if lo <= cp <= hi:
                w = 1
                break
        count += w
    return count


def _trim_tweet(tweet):
    lines = tweet.split('\n')
    while _twitter_len('\n'.join(lines)) > 280 and len(lines) > 5:
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('  →') or lines[i].startswith('・'):
                lines.pop(i)
                break
        else:
            break
    return '\n'.join(lines)


def _get_predictions(date_str: str, park: str) -> pd.DataFrame | None:
    """予測DFを返す"""
    if park == 'sea':
        from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
        predictor = DisneySeaWaitTimePredictorV3()
        targets = SEA_TARGET_ATTRACTIONS
        closures = get_sea_closures(date_str)
    else:
        from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
        predictor = DisneyLandWaitTimePredictorV3()
        targets = LAND_TARGET_ATTRACTIONS
        closures = get_land_closures(date_str)

    attractions = [a for a in targets if a not in closures]
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]
    preds = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)
    return preds


def _build_route(predictions: pd.DataFrame, entry_hour: int, closing: str,
                 short_names: dict, closures: dict) -> dict | None:
    """入園時刻から閉園までの回り方を組み立てる。

    Returns dict with:
        'first_picks': [(name, wait)] -- 入園直後に行くべき（待ち短い順）
        'later_picks': [(name, wait)] -- 夜に回せる（夜になると空く）
        'skip':        [(name, wait)] -- 待ち時間が長く時間不足で厳しい
        'night_candidates': [(name, wait)] -- 20:00時点で30分以下
    """
    if predictions is None or predictions.empty:
        return None

    entry_time = f"{entry_hour:02d}:00"
    excluded = set(closures.keys())

    entry_rows = predictions[predictions['time'] == entry_time]
    if entry_rows.empty:
        return None

    night_time = "20:00"
    night_rows = predictions[predictions['time'] == night_time]
    night_map = {}
    for _, r in night_rows.iterrows():
        night_map[r['attraction_name']] = _round10(r['predicted_wait_time'])

    closing_dt = datetime.strptime(closing, "%H:%M")
    remaining_min = (closing_dt - datetime.strptime(entry_time, "%H:%M")).total_seconds() / 60

    first_picks = []
    later_picks = []
    skip = []

    for _, row in entry_rows.iterrows():
        attr = row['attraction_name']
        if attr in excluded:
            continue
        sname = short_names.get(attr, attr[:8])
        entry_wait = _round10(row['predicted_wait_time'])
        night_wait = night_map.get(attr)

        if entry_wait <= 30:
            first_picks.append((sname, entry_wait))
        elif night_wait is not None and night_wait <= 30 and entry_wait > 40:
            later_picks.append((sname, entry_wait, night_wait))
        elif entry_wait > remaining_min * 0.5:
            skip.append((sname, entry_wait))

    first_picks.sort(key=lambda x: x[1])
    later_picks.sort(key=lambda x: x[2])
    skip.sort(key=lambda x: x[1], reverse=True)

    night_candidates = []
    for _, r in night_rows.iterrows():
        attr = r['attraction_name']
        if attr in excluded:
            continue
        w = _round10(r['predicted_wait_time'])
        if w <= 30:
            sname = short_names.get(attr, attr[:8])
            night_candidates.append((sname, w))
    night_candidates.sort(key=lambda x: x[1])

    return {
        'first_picks': first_picks,
        'later_picks': later_picks,
        'skip': skip,
        'night_candidates': night_candidates,
    }


def create_tweet(date_str: str, park: str, entry_hour: int,
                 predictions: pd.DataFrame) -> str:
    """入園時刻別の回り方ツイートを生成"""
    day_ja = ['月', '火', '水', '木', '金', '土', '日']
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = day_ja[dt.weekday()]

    park_key = 'sea' if park == 'sea' else 'land'
    _, closing = get_park_hours(date_str, park_key)
    closing_h = int(closing.split(':')[0])
    remaining = closing_h - entry_hour

    if park == 'sea':
        emoji, name = '🌊', 'シー'
        short = SEA_SHORT
        closures = get_sea_closures(date_str)
        tags = '#TDS #TDR_now'
    else:
        emoji, name = '🏰', 'ランド'
        short = LAND_SHORT
        closures = get_land_closures(date_str)
        tags = '#TDL #TDR_now'

    route = _build_route(predictions, entry_hour, closing, short, closures)

    tweet = f"{emoji} 今日{entry_hour}時から{name}入る人へ\n"
    tweet += f"{dt.month}/{dt.day}({day_name}) 残り約{remaining}時間の回り方\n"

    if route is None:
        tweet += "\n予測データ取得できず\n"
        tweet += f"\n{tags}"
        return _trim_tweet(tweet)

    if route['first_picks']:
        tweet += f"\n🚀 入園したらすぐ\n"
        for n, w in route['first_picks'][:3]:
            tweet += f"・{n} {entry_hour}時 約{w}分\n"

    if route['later_picks']:
        tweet += f"\n🌙 夜に回した方がいい\n"
        for n, ew, nw in route['later_picks'][:3]:
            tweet += f"・{n} 今{ew}分→20時{nw}分\n"

    if route['skip'] and remaining <= 5:
        tweet += f"\n⛔ 時間的に厳しい\n"
        for n, w in route['skip'][:2]:
            tweet += f"・{n} {entry_hour}時 約{w}分\n"

    tweet += f"\n{format_close_judge_block_short(closing)}\n"
    tweet += f"\n{tags}"

    return _trim_tweet(tweet)


def main():
    parser = argparse.ArgumentParser(description='午後入園者向け回り方ガイド')
    today = datetime.now().strftime('%Y-%m-%d')
    parser.add_argument('--date', '-d', type=str, default=today)
    parser.add_argument('--entry', '-e', type=int, required=True,
                        choices=[15, 17], help='入園時刻 (15 or 17)')
    parser.add_argument('--post', '-p', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    args = parser.parse_args()

    date = args.date
    entry = args.entry

    print("=" * 60)
    print(f"🕐 {entry}時入園者向け回り方ガイド")
    print(f"📅 {date}")
    print("=" * 60)

    if args.post and not args.dry_run:
        if not check_connection():
            print("❌ 接続失敗")
            return 1

    posted = 0
    import time

    if not args.land_only:
        print(f"\n🌊 シー {entry}時入園の予測計算中...")
        preds = _get_predictions(date, 'sea')
        tweet = create_tweet(date, 'sea', entry, preds)
        print(tweet)
        tlen = _twitter_len(tweet)
        print(f"📊 {tlen}/280")

        if args.post and not args.dry_run:
            if tlen <= 280:
                print("📤 投稿中...")
                if post_to_twitter(tweet):
                    posted += 1
            else:
                print("❌ 文字数オーバー")

    if not args.sea_only:
        if posted > 0:
            time.sleep(5)
        print(f"\n🏰 ランド {entry}時入園の予測計算中...")
        preds = _get_predictions(date, 'land')
        tweet = create_tweet(date, 'land', entry, preds)
        print(tweet)
        tlen = _twitter_len(tweet)
        print(f"📊 {tlen}/280")

        if args.post and not args.dry_run:
            if tlen <= 280:
                print("📤 投稿中...")
                if post_to_twitter(tweet):
                    posted += 1
            else:
                print("❌ 文字数オーバー")

    if args.post and not args.dry_run:
        print(f"\n✅ {posted}件投稿完了")
    return 0


if __name__ == '__main__':
    sys.exit(main())
