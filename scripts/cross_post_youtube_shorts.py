#!/usr/bin/env python3
"""
YouTube Shorts クロスポスト

直近の Reel mp4 を YouTube Shorts として自動アップロード。

セットアップ:
  1. Google Cloud Console で OAuth 2.0 クライアント (Desktop app) を作成
  2. YouTube Data API v3 を有効化
  3. 初回のみ ローカルで `python scripts/cross_post_youtube_shorts.py --auth-init`
     を実行し、refresh token を取得 → .env / GitHub Secret に登録
       YOUTUBE_CLIENT_ID=...
       YOUTUBE_CLIENT_SECRET=...
       YOUTUBE_REFRESH_TOKEN=...
  4. 動画を 60秒以内 / 縦型 9:16 / タイトル末尾に "#Shorts" にすると
     YouTube が自動的に Shorts 棚に表示

使い方:
    python scripts/cross_post_youtube_shorts.py --check
    python scripts/cross_post_youtube_shorts.py --within-min 60
    python scripts/cross_post_youtube_shorts.py --video predictions_x/reel_sea_2026-04-22.mp4 --title "明日のシー予測"
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

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DONE_LOG = PROJECT_DIR / "logs" / "youtube_crosspost_done.json"
IG_LOG = PROJECT_DIR / "instagram_post_log.csv"


def _check_creds() -> bool:
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        print("❌ YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN 未設定")
        print("   --auth-init で初回認可フローを実行してください")
        return False
    return True


def _build_youtube_client():
    """google-api-python-client を使って YouTube API クライアントを構築"""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ google-api-python-client / google-auth が未インストール")
        print("   pip install google-api-python-client google-auth-oauthlib")
        return None
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def auth_init():
    """ローカルで実行: ブラウザで OAuth 認可 → refresh_token を表示"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ pip install google-auth-oauthlib")
        return 1
    if not (CLIENT_ID and CLIENT_SECRET):
        print("❌ YOUTUBE_CLIENT_ID / SECRET を先に .env に登録してください")
        return 1
    cfg = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    creds = flow.run_local_server(port=0)
    print("\n✅ 認可成功")
    print(f"refresh_token = {creds.refresh_token}")
    print("\n→ これを .env / GitHub Secrets に YOUTUBE_REFRESH_TOKEN として保存してください")
    return 0


def upload_short(video_path: str, title: str, description: str = "",
                  tags: list[str] = None, category_id: str = "24") -> str | None:
    """
    YouTube Shorts として動画をアップロード。
    - 60秒以下 + #Shorts ハッシュタグ で Shorts 認定
    - category 24 = Entertainment
    Returns: video_id (string) or None
    """
    if not _check_creds():
        return None
    yt = _build_youtube_client()
    if yt is None:
        return None
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return None

    if "#Shorts" not in title:
        title = (title.strip()[:90] + " #Shorts")[:100]
    description = (description or title) + "\n\n" + " ".join((tags or [])[:8])
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:30],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": "public", "madeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                             mimetype="video/mp4")
    print(f"   📤 YT Shorts アップロード: {os.path.basename(video_path)}")
    try:
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"      {int(status.progress() * 100)}%")
        vid = resp["id"]
        print(f"   ✅ video_id = {vid} → https://youtube.com/shorts/{vid}")
        return vid
    except Exception as e:
        print(f"   ❌ {e}")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth-init", action="store_true",
                        help="OAuth 初回認可")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--within-min", type=int, default=120)
    parser.add_argument("--video", default=None,
                        help="単発アップロード用 (mp4 パス)")
    parser.add_argument("--title", default="")
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    if args.auth_init:
        return auth_init()
    if args.check:
        return 0 if _check_creds() else 1

    if args.video:
        vid = upload_short(args.video,
                           title=args.title or Path(args.video).stem,
                           description=args.description,
                           tags=["disney", "ディズニー", "tdr", "ディズニー予測",
                                  "東京ディズニーシー", "東京ディズニーランド",
                                  "ディズニー混雑", "AI予測"])
        return 0 if vid else 1

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
        # IG ログには image (= cover) しかない場合、動画ファイルパスを別所から拾う
        # 規約上 reel mp4 は predictions_x/reel_{park}_{date}.mp4
        # caption_preview からパーク&日付を推定
        cap = r.get("caption_preview", "")
        # 単純: ログ extra に video_path を入れていれば使う
        extra_raw = (r.get("extra") or "").replace("|", ",")
        video_path = None
        try:
            extra = json.loads(extra_raw) if extra_raw else {}
            video_path = extra.get("video_path")
        except Exception:
            extra = {}
        if not video_path:
            # フォールバック: image (= cover) と同じ stem の mp4 を探す
            img = (r.get("image") or "").split(";")[0]
            if img:
                stem = Path(img).stem.replace("cover_", "reel_").replace("_cover", "")
                cand = Path(img).parent / f"{stem}.mp4"
                if cand.exists():
                    video_path = str(cand)
        if not video_path or not Path(video_path).exists():
            print(f"   ⏭ 動画ファイル見つからず: ig={mid}")
            continue

        title = (cap or "ディズニー AI予測").strip()
        vid = upload_short(video_path, title=title,
                            tags=["disney", "ディズニー", "tdr", "ディズニー予測"])
        if vid:
            posted += 1
            new_done.add(mid)

    _save_done(new_done)
    print(f"\n✅ YT Shorts クロスポスト 完了: {posted}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
