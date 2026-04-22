#!/usr/bin/env python3
"""
直近の IG 投稿を Threads に自動クロスポスト。

instagram_post_log.csv の最新行を読み、
ファイル(画像) → 公開URL (Imgur 等のホスター) にアップロード → Threads 投稿。

使い方:
    # 直近1件をクロスポスト
    python scripts/cross_post_threads_from_ig.py
    # 過去1時間以内に投稿されたもの全部
    python scripts/cross_post_threads_from_ig.py --within-min 60
    # キャプションだけ (画像なし) でテキスト投稿
    python scripts/cross_post_threads_from_ig.py --text-only
"""

from __future__ import annotations

import os
import sys
import csv
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from scripts.post_to_threads import (
    cross_post_from_caption, post_text, check_connection,
)

LOG_PATH = PROJECT_DIR / "instagram_post_log.csv"
THREADS_DEDUP_LOG = PROJECT_DIR / "logs" / "threads_crosspost_done.json"


def _load_dedup() -> set:
    if not THREADS_DEDUP_LOG.exists():
        return set()
    try:
        return set(json.loads(THREADS_DEDUP_LOG.read_text(encoding='utf-8')))
    except Exception:
        return set()


def _save_dedup(media_ids: set):
    THREADS_DEDUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    THREADS_DEDUP_LOG.write_text(
        json.dumps(sorted(media_ids), ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _load_recent_posts(within_min: int) -> list:
    if not LOG_PATH.exists():
        return []
    rows = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_min)
    with open(LOG_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                ts = datetime.strptime(r["posted_at"],
                                        "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < cutoff:
                continue
            rows.append(r)
    return rows


def _upload_image_for_threads(local_path: str) -> str | None:
    """Threads 用に画像を公開 URL にアップロードする (IG 用 ImageHost を再利用)"""
    try:
        from post_via_instagram_graph import ImageHost
        return ImageHost(verbose=False).upload(local_path)
    except Exception as e:
        print(f"   ⚠️ image hoster 失敗: {e}")
        return None


def _build_threads_text(row: dict) -> str:
    """投稿ログから Threads 用の本文を生成"""
    pt = row.get("post_type", "")
    cap = row.get("caption_preview", "")  # 60文字 preview のみ
    today = datetime.now().strftime('%-m/%-d')
    if pt in ("feed", "carousel"):
        head = "🎢 明日のディズニー AI予測、Instagram で公開しました\n\n"
        body = f"{cap}…\n\n👀 詳細は IG @disney_ai_wait のプロフィールから\n\n"
        tags = "#tdr_now #ディズニー #Disney"
        return head + body + tags
    elif pt == "reel":
        head = "🎬 Reels 公開: 明日のディズニーAI予測\n\n"
        return head + cap + "\n\n#tdr_now #ディズニー"
    elif pt == "story":
        return "📖 IG Stories 更新: 今日のディズニー混雑速報\n👀 IG @disney_ai_wait をチェック"
    return cap or "ディズニー予測を更新しました"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--within-min", type=int, default=60)
    parser.add_argument("--text-only", action="store_true",
                        help="画像をクロスポストせず、誘導テキストのみ投稿")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        return 0 if check_connection() else 1

    rows = _load_recent_posts(args.within_min)
    print(f"📥 直近{args.within_min}分の IG 投稿: {len(rows)}件")
    if not rows:
        return 0

    done = _load_dedup()
    new_done = set(done)
    posted = 0
    for r in rows:
        mid = r.get("media_id", "")
        if not mid or mid in done:
            continue
        text = _build_threads_text(r)
        image_url = None
        if not args.text_only:
            # 画像パスがあればホストして添付
            img_paths = (r.get("image") or "").split(";")
            for p in img_paths:
                p = p.strip()
                if p and Path(p).exists():
                    image_url = _upload_image_for_threads(p)
                    if image_url:
                        break

        print(f"\n▶ Threads クロスポスト: ig_media={mid}")
        try:
            ids = cross_post_from_caption(
                text, image_url=image_url,
                extra={"ig_media_id": mid, "ig_post_type": r.get("post_type")},
            )
            if ids:
                posted += 1
                new_done.add(mid)
                print(f"   ✅ Threads ids: {ids}")
        except Exception as e:
            print(f"   ❌ {e}")

    _save_dedup(new_done)
    print(f"\n✅ Threads クロスポスト 完了: {posted}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
