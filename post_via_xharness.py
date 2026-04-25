#!/usr/bin/env python3
"""
X (Twitter) 投稿モジュール — 2つのモードをサポート

- xharness モード (デフォルト): ローカルの X Harness Worker API 経由で投稿
- direct モード: tweepy で直接 X API を叩いて投稿 (CI / GitHub Actions 用)

環境変数 X_POST_MODE で切り替え ("xharness" or "direct")
"""

import os
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

X_POST_MODE = os.environ.get('X_POST_MODE', 'xharness')

# X Harness mode settings
X_HARNESS_API_URL = os.environ.get('X_HARNESS_API_URL', 'http://localhost:8788')
X_HARNESS_API_KEY = os.environ.get('X_HARNESS_API_KEY', 'test-api-key-local')
X_HARNESS_ACCOUNT_ID = os.environ.get('X_HARNESS_ACCOUNT_ID', '')

# Direct mode settings (tweepy)
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')


# ---------------------------------------------------------------------------
# Shared: image resize
# ---------------------------------------------------------------------------

def _resize_for_x(file_path: str) -> str:
    """X API の制限に合わせて画像をリサイズ（最大4096x4096, 5MB以下）"""
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(file_path)
        w, h = img.size
        max_dim = 4096

        if w <= max_dim and h <= max_dim and os.path.getsize(file_path) < 5 * 1024 * 1024:
            return file_path

        print(f"   📐 リサイズ中: {w}x{h} → ", end="")
        ratio = min(max_dim / w, max_dim / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        img = img.resize((new_w, new_h), Image.LANCZOS)
        if img.mode == 'RGBA':
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg

        resized_path = file_path.rsplit('.', 1)[0] + '_x.jpg'
        img.save(resized_path, 'JPEG', quality=92, optimize=True)
        print(f"{new_w}x{new_h} ({os.path.getsize(resized_path) // 1024}KB)")
        return resized_path
    except ImportError:
        print("⚠️ Pillow がインストールされていないためリサイズできません")
        return file_path


# ---------------------------------------------------------------------------
# Direct mode: tweepy
# ---------------------------------------------------------------------------

def _direct_post(text: str, image_paths: list = None, max_retries: int = 3) -> bool:
    """tweepy で直接 X API に投稿（CI / GitHub Actions 用）"""
    try:
        import tweepy
    except ImportError:
        print("❌ tweepy がインストールされていません: pip install tweepy")
        return False

    if not all([TWITTER_API_KEY, TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Twitter API 認証情報が設定されていません (TWITTER_API_KEY 等)")
        return False

    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )

    auth = tweepy.OAuth1UserHandler(
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
    )
    api = tweepy.API(auth)

    for attempt in range(max_retries):
        try:
            media_ids = []
            if image_paths:
                for path in image_paths[:4]:
                    if not os.path.exists(path):
                        continue
                    resized = _resize_for_x(path)
                    try:
                        print(f"   📷 画像アップロード: {os.path.basename(resized)}")
                        media = api.media_upload(resized)
                        media_ids.append(media.media_id)
                    except Exception as upload_err:
                        print(f"⚠️ 画像アップロード失敗: {upload_err}")

                if not media_ids and image_paths:
                    print("⚠️ 画像アップロードに失敗しました。テキストのみで投稿します。")

            if media_ids:
                response = client.create_tweet(text=text, media_ids=media_ids)
            else:
                response = client.create_tweet(text=text)

            tweet_id = response.data['id']
            suffix = "" if media_ids else "（テキストのみ）"
            print(f"✅ Xに投稿しました{suffix}: {tweet_id}")
            return tweet_id

        except tweepy.TooManyRequests:
            wait_time = 15 * 60 * (attempt + 1)
            print(f"⏳ レート制限中 ({attempt + 1}/{max_retries}) - {wait_time // 60}分後にリトライ...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                return False

        except Exception as e:
            print(f"❌ X投稿エラー: {e}")
            return False

    return False


def _direct_thread(tweets: list[dict], max_retries: int = 3):
    """tweepy でスレッド（リプライチェーン）投稿"""
    try:
        import tweepy
    except ImportError:
        print("❌ tweepy がインストールされていません")
        return []

    if not all([TWITTER_API_KEY, TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("❌ Twitter API 認証情報が不足")
        return []

    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )
    auth = tweepy.OAuth1UserHandler(
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
    )
    api = tweepy.API(auth)

    posted_ids = []
    reply_to = None

    for i, item in enumerate(tweets):
        text = item.get("text", "")
        image_paths = item.get("images", [])

        for attempt in range(max_retries):
            try:
                media_ids = []
                for path in (image_paths or [])[:4]:
                    if not os.path.exists(path):
                        continue
                    resized = _resize_for_x(path)
                    try:
                        media = api.media_upload(resized)
                        media_ids.append(media.media_id)
                    except Exception:
                        pass

                kwargs = {"text": text}
                if media_ids:
                    kwargs["media_ids"] = media_ids
                if reply_to:
                    kwargs["in_reply_to_tweet_id"] = reply_to

                response = client.create_tweet(**kwargs)
                tweet_id = response.data["id"]
                posted_ids.append(tweet_id)
                reply_to = tweet_id
                print(f"  ✅ [{i+1}/{len(tweets)}] {tweet_id}")
                time.sleep(2)
                break

            except tweepy.TooManyRequests:
                wait = 15 * 60 * (attempt + 1)
                print(f"  ⏳ レート制限 - {wait//60}分待機...")
                if attempt < max_retries - 1:
                    time.sleep(wait)
                else:
                    print(f"  ❌ [{i+1}] レート制限超過で中断")
                    return posted_ids
            except Exception as e:
                print(f"  ❌ [{i+1}] エラー: {e}")
                return posted_ids

    return posted_ids


# ---------------------------------------------------------------------------
# X Harness mode helpers
# ---------------------------------------------------------------------------

def _api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{X_HARNESS_API_URL}{path}",
        headers={
            'Authorization': f'Bearer {X_HARNESS_API_KEY}',
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _api_post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        f"{X_HARNESS_API_URL}{path}",
        data=body,
        headers={
            'Authorization': f'Bearer {X_HARNESS_API_KEY}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_account_id() -> str:
    """X Harness に登録済みのアカウントIDを取得（キャッシュ付き）"""
    global X_HARNESS_ACCOUNT_ID
    if X_HARNESS_ACCOUNT_ID:
        return X_HARNESS_ACCOUNT_ID

    result = _api_get('/api/x-accounts')
    accounts = result.get('data', [])
    if not accounts:
        raise RuntimeError("X Harness にアカウントが登録されていません")
    X_HARNESS_ACCOUNT_ID = accounts[0]['id']
    return X_HARNESS_ACCOUNT_ID


def _xharness_upload_media(file_path: str) -> str:
    """画像をX Harness経由でアップロードし、media_idを返す"""
    account_id = get_account_id()
    file_path = _resize_for_x(str(file_path))

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    import mimetypes
    content_type = mimetypes.guess_type(file_path)[0] or 'image/png'

    boundary = f'----XHarness{int(time.time() * 1000)}'
    body_parts = []

    body_parts.append(f'--{boundary}\r\n'.encode())
    body_parts.append(b'Content-Disposition: form-data; name="xAccountId"\r\n\r\n')
    body_parts.append(f'{account_id}\r\n'.encode())

    filename = os.path.basename(file_path)
    body_parts.append(f'--{boundary}\r\n'.encode())
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
    with open(file_path, 'rb') as f:
        body_parts.append(f.read())
    body_parts.append(b'\r\n')

    body_parts.append(f'--{boundary}--\r\n'.encode())

    body = b''.join(body_parts)

    req = urllib.request.Request(
        f"{X_HARNESS_API_URL}/api/media/upload",
        data=body,
        headers={
            'Authorization': f'Bearer {X_HARNESS_API_KEY}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())

    if not result.get('success'):
        raise RuntimeError(f"メディアアップロード失敗: {result.get('error', 'unknown')}")

    media_id = result['data']['mediaId']
    print(f"   📷 アップロード完了: {filename} → {media_id}")
    return media_id


def _xharness_post(text: str, image_paths: list = None, max_retries: int = 3) -> bool:
    """X Harness Worker 経由で X に投稿"""
    account_id = get_account_id()

    for attempt in range(max_retries):
        try:
            media_ids = []
            if image_paths:
                for path in image_paths[:4]:
                    if os.path.exists(path):
                        try:
                            media_id = _xharness_upload_media(path)
                            media_ids.append(media_id)
                        except Exception as upload_err:
                            print(f"⚠️ 画像アップロード失敗: {upload_err}")

                if not media_ids and image_paths:
                    print("⚠️ 画像アップロードに失敗しました。テキストのみで投稿します。")

            payload = {
                'xAccountId': account_id,
                'text': text,
            }
            if media_ids:
                payload['mediaIds'] = media_ids

            result = _api_post('/api/posts', payload)

            if result.get('success'):
                tweet_id = result.get('data', {}).get('id', 'unknown')
                suffix = "" if media_ids else "（テキストのみ）"
                print(f"✅ Xに投稿しました{suffix}: {tweet_id}")
                return True
            else:
                error = result.get('error', 'unknown')
                print(f"❌ X投稿エラー: {error}")
                if 'rate' in error.lower() or '429' in str(error):
                    wait_time = 15 * 60 * (attempt + 1)
                    print(f"⏳ レート制限中 ({attempt + 1}/{max_retries}) - {wait_time // 60}分後にリトライ...")
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                return False

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace') if e.fp else ''
            print(f"❌ HTTP {e.code}: {error_body[:200]}")
            if e.code == 429:
                wait_time = 15 * 60 * (attempt + 1)
                print(f"⏳ レート制限中 ({attempt + 1}/{max_retries}) - {wait_time // 60}分後にリトライ...")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
            return False

        except Exception as e:
            print(f"❌ X投稿エラー: {e}")
            return False

    return False


# ---------------------------------------------------------------------------
# Public API — mode dispatch
# ---------------------------------------------------------------------------

def post_to_twitter(text: str, image_paths: list = None, max_retries: int = 3):
    """
    X に投稿（モード自動切替）。成功時は tweet_id を返す（bool True も truthy）。
    """
    if X_POST_MODE == 'direct':
        return _direct_post(text, image_paths, max_retries)
    return _xharness_post(text, image_paths, max_retries)


def post_thread(tweets: list[dict], max_retries: int = 3) -> list:
    """
    スレッド（リプライチェーン）を投稿。
    tweets: [{"text": "...", "images": ["path", ...]}, ...]
    戻り値: 投稿された tweet_id のリスト
    """
    if X_POST_MODE == 'direct':
        return _direct_thread(tweets, max_retries)
    posted = []
    for item in tweets:
        result = _xharness_post(item.get("text", ""), item.get("images"), max_retries)
        if result:
            posted.append(result)
        else:
            break
    return posted


def check_connection() -> bool:
    """接続確認（モードに応じて）"""
    if X_POST_MODE == 'direct':
        if all([TWITTER_API_KEY, TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
            print(f"✅ Direct モード: Twitter API 認証情報あり")
            return True
        print("❌ Direct モード: Twitter API 認証情報が不足しています")
        return False

    try:
        result = _api_get('/api/health')
        if result.get('success'):
            print(f"✅ X Harness 接続OK ({X_HARNESS_API_URL})")
            get_account_id()
            accounts = _api_get('/api/x-accounts')
            for acc in accounts.get('data', []):
                print(f"   📱 @{acc['username']} ({acc.get('displayName', '')})")
            return True
    except Exception as e:
        print(f"❌ X Harness 接続エラー: {e}")
    return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='X 投稿テスト')
    parser.add_argument('--check', action='store_true', help='接続確認')
    parser.add_argument('--post', type=str, help='テスト投稿テキスト')
    parser.add_argument('--image', type=str, help='添付画像パス')
    args = parser.parse_args()

    print(f"📡 モード: {X_POST_MODE}")
    if args.check:
        check_connection()
    elif args.post:
        images = [args.image] if args.image else None
        post_to_twitter(args.post, images)
    else:
        parser.print_help()
