#!/usr/bin/env python3
"""
天候・イベント アダプティブ ストーリー を Instagram に投稿。

scripts/weather_adaptive.py で生成した画像を、トリガーが立った日のみ投稿。
通常の morning briefing とは別枠 で 1日に追加 1〜2 投稿。

使い方:
    python scripts/post_adaptive_story.py --date 2026-04-29
    python scripts/post_adaptive_story.py --date 2026-04-29 --post
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from scripts.weather_adaptive import generate_adaptive_story


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date",
                        default=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
    parser.add_argument("--post", action="store_true",
                        help="実投稿。指定しないとファイル生成のみ")
    parser.add_argument("--out-dir", default="predictions_x")
    args = parser.parse_args()

    print(f"📅 対象日: {args.date}")
    result = generate_adaptive_story(args.date, args.out_dir)
    trig = result["trigger"]
    print(f"🚦 trigger: {trig}")

    if trig == "none":
        print("✅ 今日はアダプティブ ストーリー不要 (晴れ + 平日)")
        return 0

    img = result["image_path"]
    print(f"🖼  生成: {img}")

    if not args.post:
        print("\n💡 --post で実投稿します")
        return 0

    # IG 投稿
    from post_via_instagram import _get_default_poster, check_connection
    if not check_connection():
        print("❌ IG 接続失敗")
        return 1
    poster = _get_default_poster()
    print(f"\n📖 アダプティブ ストーリー投稿中...")
    if poster.post_story(img):
        print(f"✅ 投稿完了 ({trig})")
        return 0
    print(f"❌ 投稿失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
