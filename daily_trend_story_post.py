#!/usr/bin/env python3
"""
ディズニートレンド ダイジェストを Instagram ストーリーズに自動投稿。

朝 07:00 JST 実行を想定。
1) 既存の today JSON があれば再利用、無ければ `disney_trend_collector.collect_all()` を実行
2) `render_story_image()` で 1080x1920 のストーリーズ画像を生成
3) `post_via_instagram` 経由で IG Stories に投稿

使い方:
    # ドライラン (画像生成のみ)
    python daily_trend_story_post.py --dry-run

    # 投稿
    python daily_trend_story_post.py --post

    # 既存 JSON を使う (再収集しない)
    python daily_trend_story_post.py --post --reuse

    # 出力先を上書き
    python daily_trend_story_post.py --post --out-image /tmp/story.png
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "scripts"))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


def _load_or_collect(reuse: bool, news_per_query: int) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    json_path = PROJECT_DIR / "reports" / f"disney_trend_{today}.json"

    if reuse and json_path.exists():
        print(f"♻️  既存の収集データを再利用: {json_path}")
        return json.loads(json_path.read_text(encoding='utf-8'))

    print("📡 トレンド収集を実行...")
    from disney_trend_collector import collect_all
    data = collect_all(news_per_query=news_per_query)
    os.makedirs(json_path.parent, exist_ok=True)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                         encoding='utf-8')
    print(f"📁 収集データ保存: {json_path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="ディズニートレンド ストーリーズ自動投稿")
    parser.add_argument("--post", action="store_true",
                        help="実際に Instagram に投稿する")
    parser.add_argument("--dry-run", action="store_true",
                        help="画像生成のみ (投稿しない)")
    parser.add_argument("--reuse", action="store_true",
                        help="今日の JSON があれば再収集せず使う")
    parser.add_argument("--news-per-query", type=int, default=8)
    parser.add_argument("--out-image", type=str, default=None,
                        help="ストーリーズ画像の出力先 (省略時 reports/disney_trend_story_{date}.png)")
    parser.add_argument("--caption", type=str, default="",
                        help="ストーリーズ投稿時のキャプション (任意)")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    out_image = args.out_image or str(
        PROJECT_DIR / "reports" / f"disney_trend_story_{today}.png"
    )

    print(f"\n📖 ディズニートレンド ストーリーズ自動投稿")
    print(f"   date: {today}")
    print(f"   image: {out_image}")
    print(f"   mode: {'POST' if args.post and not args.dry_run else 'DRY-RUN'}")
    print()

    data = _load_or_collect(args.reuse, args.news_per_query)

    from generate_trend_digest import render_story_image
    os.makedirs(os.path.dirname(out_image) or '.', exist_ok=True)
    render_story_image(data, out_image)
    print(f"🖼️  ストーリーズ画像生成: {out_image}")

    if not args.post or args.dry_run:
        print("\n💡 ドライラン完了。投稿するには --post を指定してください")
        return 0

    print("\n📡 Instagram に投稿中...")
    from post_via_instagram import (
        _get_default_poster, _select_backend, check_connection,
    )
    backend = _select_backend()
    print(f"   バックエンド: {backend}")
    if not check_connection():
        print("❌ Instagram 接続失敗")
        return 1

    poster = _get_default_poster()
    if not hasattr(poster, "post_story"):
        print(f"❌ バックエンド {backend} は post_story 未対応 (Graph API のみ)")
        return 1

    ok = poster.post_story(out_image, caption=args.caption)
    if ok:
        print("\n✅ ストーリーズ投稿完了")
        return 0
    print("\n❌ ストーリーズ投稿失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
