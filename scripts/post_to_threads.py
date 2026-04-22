#!/usr/bin/env python3
"""
Threads (Meta) 自動投稿クライアント

Threads Graph API (2024〜) を使用。
公式ドキュメント: https://developers.facebook.com/docs/threads

セットアップ手順:
  1. Meta for Developers で Threads アプリを作成
  2. Threads ユーザートークンを取得 (Long-lived recommended)
  3. .env or GitHub Secrets に登録:
       THREADS_USER_ID=...
       THREADS_ACCESS_TOKEN=...
  4. (任意) IG と同じ Meta アプリで管理可能

機能:
  - テキストのみ投稿
  - テキスト + 画像 (1枚) 投稿
  - テキスト + 動画 投稿
  - スレッド (返信ツリー) 投稿
  - 投稿ログ → threads_post_log.csv に記録 (IG と同形式)

使い方:
    python scripts/post_to_threads.py --text "明日のディズニー予報を更新しました"
    python scripts/post_to_threads.py --text "..." --image predictions_x/ig_sea_2026-04-22.png
    python scripts/post_to_threads.py --thread "1本目" "2本目" "3本目"
    python scripts/post_to_threads.py --check
"""

from __future__ import annotations

import os
import sys
import csv
import time
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


THREADS_API_BASE = "https://graph.threads.net/v1.0"
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
LOG_PATH = PROJECT_DIR / "threads_post_log.csv"


def _check_credentials() -> bool:
    if not THREADS_USER_ID or not THREADS_ACCESS_TOKEN:
        print("❌ THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定")
        print("   .env または GitHub Secrets に登録してください")
        return False
    return True


def _record_post(media_id: str, post_type: str, text: str,
                 image_path: str = "", extra: dict = None):
    """投稿ログを CSV に追記"""
    new_file = not LOG_PATH.exists()
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        if new_file:
            f.write("posted_at,media_id,post_type,image,text_preview,extra\n")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        text_preview = text[:60].replace(',', ';').replace('\n', ' ')
        extra_json = (json.dumps(extra, ensure_ascii=False).replace(",", "|")
                      if extra else "")
        f.write(f"{ts},{media_id},{post_type},{image_path},{text_preview},{extra_json}\n")


def check_connection() -> bool:
    """Threads アカウントに接続できるか確認"""
    if not _check_credentials():
        return False
    try:
        r = requests.get(
            f"{THREADS_API_BASE}/me",
            params={"fields": "id,username,threads_profile_picture_url",
                    "access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        if r.ok:
            data = r.json()
            print(f"✅ Threads 接続OK: @{data.get('username', '?')} (id={data.get('id')})")
            return True
        print(f"❌ Threads 接続失敗: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"❌ {e}")
    return False


def _create_container(media_type: str, text: str = "",
                       image_url: str = None, video_url: str = None,
                       reply_to_id: str = None,
                       is_carousel_item: bool = False) -> str:
    """投稿コンテナを作成して container ID を返す"""
    params = {"access_token": THREADS_ACCESS_TOKEN, "media_type": media_type}
    if text:
        params["text"] = text
    if image_url:
        params["image_url"] = image_url
    if video_url:
        params["video_url"] = video_url
    if reply_to_id:
        params["reply_to_id"] = reply_to_id
    if is_carousel_item:
        params["is_carousel_item"] = "true"
    r = requests.post(f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads",
                      params=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"create container failed: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def _publish(container_id: str) -> str:
    """コンテナを公開して media ID を返す"""
    r = requests.post(f"{THREADS_API_BASE}/{THREADS_USER_ID}/threads_publish",
                      params={"access_token": THREADS_ACCESS_TOKEN,
                              "creation_id": container_id},
                      timeout=60)
    if not r.ok:
        raise RuntimeError(f"publish failed: {r.status_code} {r.text[:300]}")
    return r.json()["id"]


def _wait_for_container(container_id: str, max_wait: int = 90):
    """コンテナの処理完了を待つ"""
    for _ in range(max_wait):
        r = requests.get(
            f"{THREADS_API_BASE}/{container_id}",
            params={"fields": "status,error_message",
                    "access_token": THREADS_ACCESS_TOKEN},
            timeout=30,
        )
        if r.ok:
            d = r.json()
            status = d.get("status", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"container error: {d.get('error_message')}")
        time.sleep(2)
    raise TimeoutError(f"container {container_id} not finished")


def post_text(text: str, extra: dict = None) -> str | None:
    """テキスト投稿"""
    if not _check_credentials():
        return None
    text = text[:500]  # Threads は 500文字制限
    try:
        cid = _create_container("TEXT", text=text)
        # テキストはすぐ FINISHED になるが念のため
        time.sleep(1)
        media_id = _publish(cid)
        print(f"✅ Threads (text) 投稿: {media_id}")
        _record_post(media_id, "text", text, extra=extra)
        return media_id
    except Exception as e:
        print(f"❌ {e}")
        return None


def post_image(text: str, image_url: str, extra: dict = None) -> str | None:
    """画像 + テキスト 投稿"""
    if not _check_credentials():
        return None
    text = text[:500]
    try:
        cid = _create_container("IMAGE", text=text, image_url=image_url)
        _wait_for_container(cid)
        media_id = _publish(cid)
        print(f"✅ Threads (image) 投稿: {media_id}")
        _record_post(media_id, "image", text, image_url, extra=extra)
        return media_id
    except Exception as e:
        print(f"❌ {e}")
        return None


def post_video(text: str, video_url: str, extra: dict = None) -> str | None:
    """動画 + テキスト 投稿"""
    if not _check_credentials():
        return None
    text = text[:500]
    try:
        cid = _create_container("VIDEO", text=text, video_url=video_url)
        _wait_for_container(cid, max_wait=180)
        media_id = _publish(cid)
        print(f"✅ Threads (video) 投稿: {media_id}")
        _record_post(media_id, "video", text, video_url, extra=extra)
        return media_id
    except Exception as e:
        print(f"❌ {e}")
        return None


def post_thread(texts: list[str], extra: dict = None) -> list[str]:
    """連投 (スレッド) 投稿。1本目を投稿後、それに reply で 2本目以降を続ける"""
    if not _check_credentials() or not texts:
        return []
    posted = []
    parent = None
    for i, t in enumerate(texts):
        try:
            cid = _create_container("TEXT", text=t[:500],
                                     reply_to_id=parent)
            time.sleep(1)
            mid = _publish(cid)
            posted.append(mid)
            parent = mid
            label = f"thread_{i + 1}"
            _record_post(mid, label, t, extra={**(extra or {}),
                                                "thread_index": i + 1,
                                                "thread_total": len(texts),
                                                "parent_id": (posted[0] if i > 0 else None)})
            print(f"   ▶ {label}: {mid}")
            time.sleep(3)
        except Exception as e:
            print(f"   ❌ thread_{i + 1} failed: {e}")
            break
    return posted


# =============================================================================
# IG → Threads 自動クロスポスト ヘルパー
# =============================================================================
def cross_post_from_caption(caption: str, image_url: str = None,
                             video_url: str = None,
                             max_first_post_chars: int = 480,
                             extra: dict = None) -> list[str]:
    """
    IG のキャプションを Threads 流に変換して投稿。

    - ハッシュタグの群れは末尾→1本目に少しだけ残す
    - 500文字を超えるキャプションは分割してスレッド投稿
    - 画像/動画 URL があれば 1本目に添付
    """
    # ハッシュタグを抽出して一旦削除
    import re
    tags = re.findall(r'#\S+', caption)
    body = re.sub(r'#\S+', '', caption).strip()
    body = re.sub(r'\n{3,}', '\n\n', body)

    # 1本目: 本文の前半 + 重要ハッシュタグ 3つ
    first_text = body
    if len(first_text) > max_first_post_chars:
        # 改行で適切に区切る
        cut = first_text.rfind('\n', 0, max_first_post_chars)
        if cut < 100:
            cut = max_first_post_chars
        first_text = body[:cut].rstrip()
        rest = body[cut:].strip()
    else:
        rest = ""
    if tags:
        first_text = first_text.rstrip() + "\n\n" + " ".join(tags[:3])

    if image_url:
        mid = post_image(first_text, image_url, extra={**(extra or {}),
                                                        "source": "ig_crosspost"})
    elif video_url:
        mid = post_video(first_text, video_url, extra={**(extra or {}),
                                                        "source": "ig_crosspost"})
    else:
        mid = post_text(first_text, extra={**(extra or {}),
                                            "source": "ig_crosspost"})

    if not mid:
        return []
    posted = [mid]

    if rest:
        # 残りを reply で繋げる
        chunks = []
        cur = ""
        for line in rest.split("\n"):
            if len(cur) + len(line) + 1 > 480:
                chunks.append(cur)
                cur = line
            else:
                cur = (cur + "\n" + line) if cur else line
        if cur:
            chunks.append(cur)
        for chunk in chunks:
            try:
                cid = _create_container("TEXT", text=chunk[:500], reply_to_id=mid)
                time.sleep(1)
                rid = _publish(cid)
                posted.append(rid)
                _record_post(rid, "thread_reply", chunk,
                              extra={**(extra or {}), "parent_id": mid})
                time.sleep(3)
            except Exception as e:
                print(f"   ⚠️ reply skipped: {e}")
                break
    return posted


def main():
    parser = argparse.ArgumentParser(description="Threads 自動投稿")
    parser.add_argument("--text", type=str, help="単発テキスト投稿")
    parser.add_argument("--image", type=str, help="画像URL (公開URL)")
    parser.add_argument("--video", type=str, help="動画URL (公開URL)")
    parser.add_argument("--thread", nargs='*', help="スレッド (連投)")
    parser.add_argument("--check", action="store_true", help="接続テスト")
    parser.add_argument("--from-ig-caption", type=str,
                        help="IG キャプションを変換して Threads にクロスポスト (テキスト、または '|' で分割画像URL付与)")
    args = parser.parse_args()

    if args.check:
        return 0 if check_connection() else 1
    if args.thread:
        ids = post_thread(args.thread)
        return 0 if ids else 1
    if args.from_ig_caption:
        # text|image_url の形式
        parts = args.from_ig_caption.split("|", 1)
        text = parts[0]
        img = parts[1] if len(parts) > 1 else None
        ids = cross_post_from_caption(text, image_url=img)
        return 0 if ids else 1
    if args.text:
        if args.image:
            mid = post_image(args.text, args.image)
        elif args.video:
            mid = post_video(args.text, args.video)
        else:
            mid = post_text(args.text)
        return 0 if mid else 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
