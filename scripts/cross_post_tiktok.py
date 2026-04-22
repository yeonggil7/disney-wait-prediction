#!/usr/bin/env python3
"""
TikTok クロスポスト

TikTok for Developers の Content Posting API (Direct Post / Inbox Upload) を利用。

セットアップ:
  1. TikTok Developer Portal でアプリを作成
  2. 「Content Posting API」 のアクセス申請 (審査あり: 1〜2週間)
  3. 承認後、 OAuth で access_token を取得
  4. .env / GitHub Secrets に登録:
        TIKTOK_ACCESS_TOKEN=...
        TIKTOK_OPEN_ID=...           # /v2/user/info/ で取得
  5. 公開 URL or アプリにファイルアップロード で動画 URL を渡す

実装方針:
  - **Direct Post** モード = キャプション付きで即時公開 (要追加権限)
  - 標準は **Inbox Upload** = TikTok アプリの下書きに上がるので
    そこから手動で公開 (Disney コンテンツの著作権チェック対応)
  - 動画は IG Reels と同じ mp4 (1080x1920 / H.264) を使い回せる

使い方:
    python scripts/cross_post_tiktok.py --check
    python scripts/cross_post_tiktok.py --within-min 60         # 直近IGリールを送信
    python scripts/cross_post_tiktok.py --video reel.mp4 --caption "..."
"""

from __future__ import annotations

import os
import sys
import csv
import json
import time
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_OPEN_ID = os.environ.get("TIKTOK_OPEN_ID", "")
TIKTOK_DIRECT_POST = os.environ.get("TIKTOK_DIRECT_POST", "").lower() == "true"
API_BASE = "https://open.tiktokapis.com/v2"

DONE_LOG = PROJECT_DIR / "logs" / "tiktok_crosspost_done.json"
IG_LOG = PROJECT_DIR / "instagram_post_log.csv"


def _check_creds() -> bool:
    if not TIKTOK_ACCESS_TOKEN:
        print("❌ TIKTOK_ACCESS_TOKEN が未設定")
        return False
    return True


def _headers() -> dict:
    return {"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json"}


def check_connection() -> bool:
    if not _check_creds():
        return False
    try:
        r = requests.get(f"{API_BASE}/user/info/",
                          params={"fields": "open_id,union_id,display_name,username"},
                          headers={"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}"},
                          timeout=30)
        if r.ok:
            d = r.json().get("data", {}).get("user", {})
            print(f"✅ TikTok 接続OK: @{d.get('username')} ({d.get('display_name')})")
            return True
        print(f"❌ {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"❌ {e}")
    return False


def post_video_inbox(video_url: str) -> str | None:
    """
    Inbox Upload (PULL_FROM_URL): video_url を TikTok 側がダウンロード → ユーザー下書きに格納
    """
    if not _check_creds():
        return None
    body = {
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        }
    }
    try:
        r = requests.post(f"{API_BASE}/post/publish/inbox/video/init/",
                          headers=_headers(), json=body, timeout=60)
        if not r.ok:
            print(f"❌ inbox init failed: {r.status_code} {r.text[:300]}")
            return None
        publish_id = r.json().get("data", {}).get("publish_id")
        print(f"✅ TikTok inbox init: publish_id = {publish_id}")
        return publish_id
    except Exception as e:
        print(f"❌ {e}")
        return None


def post_video_direct(video_url: str, caption: str = "",
                       privacy_level: str = "PUBLIC_TO_EVERYONE") -> str | None:
    """
    Direct Post (要追加申請): キャプション付きで即時公開
    """
    if not _check_creds():
        return None
    body = {
        "post_info": {
            "title": caption[:150],
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
    }
    try:
        r = requests.post(f"{API_BASE}/post/publish/video/init/",
                          headers=_headers(), json=body, timeout=60)
        if not r.ok:
            print(f"❌ direct post init failed: {r.status_code} {r.text[:300]}")
            return None
        publish_id = r.json().get("data", {}).get("publish_id")
        print(f"✅ TikTok direct post init: publish_id = {publish_id}")
        return publish_id
    except Exception as e:
        print(f"❌ {e}")
        return None


def _upload_for_tiktok(local_path: str) -> str | None:
    """TikTok PULL_FROM_URL 用に公開 URL に動画をホストする"""
    try:
        from post_via_instagram_graph import ImageHost
        return ImageHost(verbose=False).upload(local_path)
    except Exception as e:
        print(f"   ⚠️ video hoster 失敗: {e}")
        return None


def _load_done() -> set:
    if not DONE_LOG.exists():
        return set()
    try:
        return set(json.loads(DONE_LOG.read_text(encoding='utf-8')))
    except Exception:
        return set()


def _save_done(ids: set):
    DONE_LOG.parent.mkdir(parents=True, exist_ok=True)
    DONE_LOG.write_text(json.dumps(sorted(ids)[-2000:], ensure_ascii=False, indent=2),
                         encoding='utf-8')


def _recent_reels(within_min: int) -> list:
    if not IG_LOG.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_min)
    rows = []
    with open(IG_LOG, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get("post_type") != "reel":
                continue
            try:
                ts = datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < cutoff:
                continue
            rows.append(r)
    return rows


def _build_caption(ig_caption_preview: str) -> str:
    base = ig_caption_preview or "明日のディズニー AI予測"
    tags = "#ディズニー #tdr #disney #ディズニー混雑予測 #AI予測 #fyp"
    return f"{base}\n\n{tags}"[:150]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--within-min", type=int, default=120)
    parser.add_argument("--video", default=None)
    parser.add_argument("--caption", default="")
    parser.add_argument("--mode", choices=["inbox", "direct"],
                        default=("direct" if TIKTOK_DIRECT_POST else "inbox"),
                        help="inbox=下書き / direct=即時公開")
    args = parser.parse_args()

    if args.check:
        return 0 if check_connection() else 1

    if args.video:
        url = _upload_for_tiktok(args.video)
        if not url:
            return 1
        if args.mode == "direct":
            pid = post_video_direct(url, caption=args.caption or Path(args.video).stem)
        else:
            pid = post_video_inbox(url)
        return 0 if pid else 1

    rows = _recent_reels(args.within_min)
    print(f"📥 直近{args.within_min}分の IG Reels: {len(rows)}件")
    if not rows:
        return 0
    done = _load_done()
    new_done = set(done)
    posted = 0
    for r in rows:
        mid = r.get("media_id", "")
        if not mid or mid in done:
            continue
        extra_raw = (r.get("extra") or "").replace("|", ",")
        video_path = None
        try:
            extra = json.loads(extra_raw) if extra_raw else {}
            video_path = extra.get("video_path")
        except Exception:
            pass
        if not video_path:
            img = (r.get("image") or "").split(";")[0]
            if img:
                stem = Path(img).stem.replace("cover_", "reel_").replace("_cover", "")
                cand = Path(img).parent / f"{stem}.mp4"
                if cand.exists():
                    video_path = str(cand)
        if not video_path or not Path(video_path).exists():
            print(f"   ⏭ 動画見つからず: ig={mid}")
            continue
        url = _upload_for_tiktok(video_path)
        if not url:
            continue
        cap = _build_caption(r.get("caption_preview", ""))
        if args.mode == "direct":
            pid = post_video_direct(url, caption=cap)
        else:
            pid = post_video_inbox(url)
        if pid:
            posted += 1
            new_done.add(mid)
            time.sleep(5)

    _save_done(new_done)
    print(f"\n✅ TikTok クロスポスト 完了: {posted}件 ({args.mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
