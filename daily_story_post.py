#!/usr/bin/env python3
"""
Instagram ストーリーズ自動投稿スクリプト

朝・夕の2回ストーリーズに「速報briefing」を投稿する。

CIスケジュール例 (UTC / JST=UTC+9):
  - 22:30 UTC = 翌日 07:30 JST  → mode=morning  (当日の予報)
  - 08:00 UTC = 当日 17:00 JST  → mode=preview  (翌日の予報)

使い方:
  python daily_story_post.py --mode morning --dry-run
  python daily_story_post.py --mode morning --post
  python daily_story_post.py --mode preview --post
  python daily_story_post.py --mode morning --post --park sea
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

from generate_story_briefing import generate_story_briefing
from generate_instagram_heatmap import PARK_THEMES


def main():
    parser = argparse.ArgumentParser(description='Instagram ストーリーズ自動投稿')
    parser.add_argument('--mode', choices=['morning', 'preview', 'evening'],
                        default='morning',
                        help='morning=当日 / preview=翌日 / evening=当日振り返り')
    parser.add_argument('--date', type=str, default=None,
                        help='対象日 (省略時は mode に応じて自動)')
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    parser.add_argument('--post', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    # 日付決定
    now = datetime.now()
    if args.date:
        date = args.date
    elif args.mode == 'preview':
        date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    elif args.mode == 'evening':
        date = now.strftime('%Y-%m-%d')
    else:  # morning
        date = now.strftime('%Y-%m-%d')

    if args.sea_only:
        parks = ['sea']
    elif args.land_only:
        parks = ['land']
    elif args.park == 'both':
        parks = ['sea', 'land']
    else:
        parks = [args.park]

    print(f"\n📖 ストーリーズ投稿: mode={args.mode} date={date} parks={parks}\n")

    images = {}
    for park in parks:
        img, _ = generate_story_briefing(date, park=park, mode=args.mode)
        if img is None:
            print(f"⚠️ {park}: スキップ")
            continue
        images[park] = img
        print(f"🖼️  {PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']}: {img}")

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
        for park in parks:
            if park not in images:
                continue
            print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} ストーリーズ投稿中...")
            if poster.post_story(images[park]):
                posted += 1
            time.sleep(10)

        print(f"\n✅ {posted}件のストーリーズ投稿完了")
    elif args.dry_run:
        print(f"\n🔍 ドライラン: {len(images)}件スキップ")
    else:
        print("\n💡 投稿するには --post を追加")

    return 0


if __name__ == '__main__':
    sys.exit(main())
