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


def _hot_topic_image(date_str: str) -> str | None:
    """
    今日のトレンドダイジェスト JSON から「ホットトピック」画像を生成して返す。
    JSON が無い / トピックが拾えない場合は None。
    """
    import json
    sys.path.insert(0, str(PROJECT_DIR / 'scripts'))
    json_path = PROJECT_DIR / "reports" / f"disney_trend_{date_str}.json"
    if not json_path.exists():
        print(f"⚠️ トレンド JSON が見つからない: {json_path}")
        print("   先に scripts/generate_trend_digest.py --collect を実行してください")
        return None
    try:
        from generate_trend_digest import render_hot_topic_story_image
    except ImportError as e:
        print(f"❌ generate_trend_digest を import できません: {e}")
        return None
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ JSON 読み込み失敗: {e}")
        return None
    out_path = PROJECT_DIR / "predictions_x" / f"ig_story_hot_topic_{date_str}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok = render_hot_topic_story_image(data, str(out_path))
    if not ok:
        print("⚠️ ホットトピックを抽出できませんでした (ニュースが空 or 該当カテゴリなし)")
        return None
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(description='Instagram ストーリーズ自動投稿')
    parser.add_argument('--mode', choices=['morning', 'preview', 'evening', 'hot_topic'],
                        default='morning',
                        help='morning=当日 / preview=翌日 / evening=当日振り返り / hot_topic=今日のトレンド速報')
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
    if args.mode == 'hot_topic':
        # トレンドダイジェスト連動の単一ストーリー (パーク非依存)
        img = _hot_topic_image(date)
        if img is None:
            print("❌ ホットトピック画像が作れなかったため終了")
            return 1
        images['_hot'] = img
        print(f"🖼️  🔥 ホットトピック: {img}")
    else:
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
        if args.mode == 'hot_topic':
            print("\n🔥 ホットトピック ストーリーズ投稿中...")
            if poster.post_story(images['_hot']):
                posted += 1
        else:
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
