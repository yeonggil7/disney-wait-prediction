#!/usr/bin/env python3
"""
Instagram 自動投稿モジュール（バックエンド切替対応のディスパッチャー）

INSTAGRAM_API_MODE 環境変数でバックエンドを切替:
  - "graph"     : 公式 Instagram Graph API（推奨 / IPブロックなし / Business必須）
  - "instagrapi": 非公式 instagrapi（ユーザー名・パスワード方式）
  デフォルト: "graph" を試し、失敗したら "instagrapi" にフォールバック

================================================================
[A] Graph API モード (INSTAGRAM_API_MODE=graph)
================================================================
セットアップ:
    python scripts/ig_graph_setup.py guide

必要な環境変数:
    - INSTAGRAM_BUSINESS_ACCOUNT_ID
    - INSTAGRAM_ACCESS_TOKEN
    - IMGUR_CLIENT_ID  (任意 / 推奨)

================================================================
[B] instagrapi モード (INSTAGRAM_API_MODE=instagrapi)
================================================================
特徴: ユーザー名/パスワードログイン。IP制限の影響を受けやすい。

環境変数:
    - INSTAGRAM_USERNAME
    - INSTAGRAM_PASSWORD
    - INSTAGRAM_TOTP_SECRET (任意 / 2FA Authenticator のシークレット)
    - INSTAGRAM_SESSIONID    (任意 / ブラウザCookieのsessionid値)
    - INSTAGRAM_SESSION_FILE (任意 / デフォルト: .ig_session.json)

ログイン優先順位:
  1. .ig_session.json があればそれを復元
  2. INSTAGRAM_SESSIONID が設定されていればCookie経由ログイン
  3. INSTAGRAM_USERNAME/PASSWORD で通常ログイン

================================================================
CLI 使い方:
    python post_via_instagram.py --check
    python post_via_instagram.py --photo path.jpg --caption "test"
    python post_via_instagram.py --carousel a.jpg b.jpg --caption "carousel"
    python post_via_instagram.py --story path.jpg
"""

import os
import sys
import json
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


INSTAGRAM_API_MODE = os.environ.get('INSTAGRAM_API_MODE', 'graph').lower()

INSTAGRAM_USERNAME = os.environ.get('INSTAGRAM_USERNAME', '')
INSTAGRAM_PASSWORD = os.environ.get('INSTAGRAM_PASSWORD', '')
INSTAGRAM_TOTP_SECRET = os.environ.get('INSTAGRAM_TOTP_SECRET', '')
INSTAGRAM_SESSIONID = os.environ.get('INSTAGRAM_SESSIONID', '')
INSTAGRAM_SESSION_FILE = os.environ.get(
    'INSTAGRAM_SESSION_FILE',
    str(PROJECT_DIR / '.ig_session.json')
)


# -----------------------------------------------------------------------------
# 内部ヘルパー
# -----------------------------------------------------------------------------
def _import_instagrapi():
    try:
        from instagrapi import Client
        from instagrapi.exceptions import (
            LoginRequired, ChallengeRequired, TwoFactorRequired,
        )
        return Client, LoginRequired, ChallengeRequired, TwoFactorRequired
    except ImportError:
        print("❌ instagrapi がインストールされていません。")
        print("   インストール: pip install instagrapi pillow moviepy")
        return None, None, None, None


def _ensure_jpeg(path: str) -> str:
    """Instagram は JPEG が無難。PNG 等は JPEG に変換して返す。"""
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ Pillow がないため画像変換できません")
        return path

    p = Path(path)
    if p.suffix.lower() in ('.jpg', '.jpeg'):
        return str(p)

    img = Image.open(p)
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, (15, 15, 30))  # ダーク背景
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    out = p.with_suffix('.jpg')
    img.save(out, 'JPEG', quality=95, optimize=True)
    return str(out)


def _validate_aspect_for_feed(path: str) -> str:
    """
    Instagram フィードのアスペクト比は 0.8〜1.91。
    範囲外なら 4:5 (0.8) にパディングして整形した画像を返す。
    """
    try:
        from PIL import Image
    except ImportError:
        return path

    img = Image.open(path)
    w, h = img.size
    ratio = w / h
    if 0.8 <= ratio <= 1.91:
        return path

    # 範囲外 → 4:5 にパディング
    target_ratio = 0.8  # 4:5
    if ratio < target_ratio:
        new_w = int(h * target_ratio)
        new_img = Image.new('RGB', (new_w, h), (15, 15, 30))
        new_img.paste(img, ((new_w - w) // 2, 0))
    else:
        new_h = int(w / target_ratio)
        new_img = Image.new('RGB', (w, new_h), (15, 15, 30))
        new_img.paste(img, (0, (new_h - h) // 2))

    out = Path(path).with_name(Path(path).stem + '_padded.jpg')
    new_img.save(out, 'JPEG', quality=95, optimize=True)
    return str(out)


# -----------------------------------------------------------------------------
# クライアント
# -----------------------------------------------------------------------------
class InstagramPoster:
    def __init__(self, username=None, password=None, session_file=None,
                 totp_secret=None, sessionid=None, verbose=True):
        self.username = username or INSTAGRAM_USERNAME
        self.password = password or INSTAGRAM_PASSWORD
        self.session_file = session_file or INSTAGRAM_SESSION_FILE
        self.totp_secret = totp_secret or INSTAGRAM_TOTP_SECRET
        self.sessionid = sessionid or INSTAGRAM_SESSIONID
        self.verbose = verbose
        self._client = None

    # -------------------------------------------------------------------------
    def _log(self, msg):
        if self.verbose:
            print(msg)

    # -------------------------------------------------------------------------
    def _make_client(self):
        """毎回同じデバイス情報でクライアントを作る（不審判定を減らす）"""
        Client, *_ = _import_instagrapi()
        cl = Client()
        cl.delay_range = [3, 6]  # 操作間隔を長めに
        # ユーザー名から決定論的なデバイスIDを生成（同一PCなら毎回同じ値）
        import hashlib
        seed = hashlib.sha256(self.username.encode()).hexdigest()
        cl.set_device({
            "app_version": "269.0.0.18.75",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "480dpi",
            "resolution": "1080x1920",
            "manufacturer": "samsung",
            "device": "SM-G930F",
            "model": "herolte",
            "cpu": "samsungexynos8890",
            "version_code": "314665256",
        })
        cl.set_user_agent()
        cl.set_uuids({
            "phone_id": seed[:32],
            "uuid": seed[32:64] if len(seed) >= 64 else seed[:32],
            "client_session_id": seed[:32],
            "advertising_id": seed[:32],
            "device_id": "android-" + seed[:16],
        })
        return cl

    # -------------------------------------------------------------------------
    def login(self) -> bool:
        Client, LoginRequired, ChallengeRequired, TwoFactorRequired = _import_instagrapi()
        if Client is None:
            return False

        # 1) ローカルセッションファイルを優先
        session_path = Path(self.session_file)
        if session_path.exists():
            try:
                cl = self._make_client()
                cl.load_settings(str(session_path))
                # username/password なしでも復元可能（settings に保持されている）
                if self.username and self.password:
                    cl.login(self.username, self.password)
                cl.get_timeline_feed()
                self._log(f"♻️  セッション復元成功: {session_path.name}")
                self._client = cl
                return True
            except Exception as e:
                self._log(f"⚠️ セッション復元失敗 → 別経路を試行: {e}")

        # 2) ブラウザCookieのsessionidでログイン（IPブロック回避に有効）
        if self.sessionid:
            try:
                cl = self._make_client()
                self._log(f"🍪 sessionid Cookieでログイン中...")
                cl.login_by_sessionid(self.sessionid.strip())
                self._client = cl
                # verification は失敗してもよい（IP制限時は user info 取得が467を返すことがある）
                try:
                    cl.get_timeline_feed()
                    self._log(f"✅ sessionidログイン成功 + verification OK: @{cl.username or self.username}")
                except Exception as ve:
                    self._log(f"⚠️ ログイン後の verification がエラー（IP制限の可能性）: {ve}")
                    self._log(f"   → セッションは保存されました。投稿は実際に試して結果を見ます。")
                # 必ずセッション保存
                try:
                    cl.dump_settings(str(session_path))
                    self._log(f"💾 セッション保存: {session_path.name}")
                except Exception as e:
                    self._log(f"⚠️ セッション保存失敗: {e}")
                return True
            except Exception as e:
                print(f"❌ sessionid ログイン失敗: {e}")
                # フォールスルー → username/password を試みる

        # 3) username/password で通常ログイン
        if not self.username or not self.password:
            print("❌ INSTAGRAM_SESSIONID も INSTAGRAM_USERNAME/PASSWORD も設定されていません")
            return False

        cl = self._make_client()
        try:
            verification_code = ""
            if self.totp_secret:
                verification_code = cl.totp_generate_code(self.totp_secret)
            cl.login(self.username, self.password, verification_code=verification_code)
        except TwoFactorRequired:
            print("❌ 2FAが必要です。INSTAGRAM_TOTP_SECRET を .env に設定してください。")
            return False
        except ChallengeRequired:
            print("❌ Instagramチャレンジ必須。ブラウザで一度ログインしてから再試行してください。")
            return False
        except Exception as e:
            print(f"❌ ログイン失敗: {e}")
            return False

        try:
            cl.dump_settings(str(session_path))
            self._log(f"💾 セッション保存: {session_path.name}")
        except Exception as e:
            self._log(f"⚠️ セッション保存失敗: {e}")

        self._client = cl
        self._log(f"✅ ログイン成功: @{self.username}")
        return True

    # -------------------------------------------------------------------------
    def _client_or_login(self):
        if self._client is None:
            if not self.login():
                return None
        return self._client

    # -------------------------------------------------------------------------
    def post_photo(self, image_path: str, caption: str = "") -> bool:
        """フィードに単一写真を投稿"""
        cl = self._client_or_login()
        if cl is None:
            return False

        path = _ensure_jpeg(image_path)
        path = _validate_aspect_for_feed(path)
        if not os.path.exists(path):
            print(f"❌ 画像が見つかりません: {path}")
            return False

        try:
            self._log(f"📷 フィード投稿中: {os.path.basename(path)}")
            media = cl.photo_upload(path, caption=caption)
            self._log(f"✅ Instagram投稿完了: media_id={media.id}")
            return True
        except Exception as e:
            print(f"❌ Instagram投稿エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def post_carousel(self, image_paths: list, caption: str = "") -> bool:
        """フィードにカルーセル投稿（最大10枚）"""
        cl = self._client_or_login()
        if cl is None:
            return False

        if not image_paths:
            print("❌ 画像がありません")
            return False

        prepared = []
        for p in image_paths[:10]:
            jp = _ensure_jpeg(p)
            jp = _validate_aspect_for_feed(jp)
            if os.path.exists(jp):
                prepared.append(jp)

        if not prepared:
            print("❌ アップロード可能な画像がありません")
            return False

        try:
            self._log(f"🎠 カルーセル投稿中: {len(prepared)}枚")
            media = cl.album_upload(prepared, caption=caption)
            self._log(f"✅ Instagramカルーセル投稿完了: media_id={media.id}")
            return True
        except Exception as e:
            print(f"❌ カルーセル投稿エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def post_story(self, image_path: str, caption: str = "") -> bool:
        """ストーリーズに写真を投稿"""
        cl = self._client_or_login()
        if cl is None:
            return False

        path = _ensure_jpeg(image_path)
        if not os.path.exists(path):
            print(f"❌ 画像が見つかりません: {path}")
            return False

        try:
            self._log(f"📖 ストーリーズ投稿中: {os.path.basename(path)}")
            media = cl.photo_upload_to_story(path, caption=caption)
            self._log(f"✅ ストーリーズ投稿完了: media_id={media.id}")
            return True
        except Exception as e:
            print(f"❌ ストーリーズ投稿エラー: {e}")
            return False


# -----------------------------------------------------------------------------
# モジュールレベルの簡易API（バックエンド切替）
# -----------------------------------------------------------------------------
_default_poster = None
_active_backend = None  # 'graph' or 'instagrapi'


def _instagrapi_poster():
    global _default_poster
    if _default_poster is None or not isinstance(_default_poster, InstagramPoster):
        _default_poster = InstagramPoster()
    return _default_poster


def _graph_poster():
    """Graph API バックエンドを取得（遅延import）"""
    global _default_poster
    if _default_poster is None or not hasattr(_default_poster, 'check_connection'):
        from post_via_instagram_graph import InstagramGraphPoster
        _default_poster = InstagramGraphPoster()
    return _default_poster


def _select_backend():
    """INSTAGRAM_API_MODE に応じてバックエンドを選択"""
    global _active_backend
    if _active_backend:
        return _active_backend

    mode = INSTAGRAM_API_MODE
    if mode == 'graph':
        from post_via_instagram_graph import (
            INSTAGRAM_BUSINESS_ACCOUNT_ID as ig_id,
            INSTAGRAM_ACCESS_TOKEN as ig_token,
        )
        if ig_id and ig_token:
            _active_backend = 'graph'
        else:
            print("⚠️ INSTAGRAM_API_MODE=graph だが認証情報が不足 → instagrapi にフォールバック")
            _active_backend = 'instagrapi'
    elif mode == 'instagrapi':
        _active_backend = 'instagrapi'
    else:
        print(f"⚠️ 不明な INSTAGRAM_API_MODE={mode} → graph として扱います")
        _active_backend = 'graph'
    return _active_backend


def _get_default_poster():
    backend = _select_backend()
    if backend == 'graph':
        return _graph_poster()
    return _instagrapi_poster()


def post_to_instagram(caption: str, image_paths=None, story=False) -> bool:
    """
    汎用エントリポイント
    - image_paths が1枚 → フィード単一写真
    - image_paths が2枚以上 → フィードカルーセル
    - story=True → 1枚目をストーリーズに投稿
    """
    poster = _get_default_poster()
    if not image_paths:
        print("❌ Instagramはテキストのみ投稿はできません。画像を指定してください。")
        return False

    if isinstance(image_paths, str):
        image_paths = [image_paths]

    if story:
        return poster.post_story(image_paths[0], caption)

    if len(image_paths) == 1:
        return poster.post_photo(image_paths[0], caption)
    return poster.post_carousel(image_paths, caption)


def check_connection() -> bool:
    """接続確認（バックエンドに応じて）"""
    backend = _select_backend()
    print(f"📡 Instagram バックエンド: {backend}")
    poster = _get_default_poster()
    if backend == 'graph':
        return poster.check_connection()
    return poster.login()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Instagram投稿テスト（Graph API / instagrapi 切替対応）')
    parser.add_argument('--check', action='store_true', help='ログイン確認')
    parser.add_argument('--photo', type=str, help='単一写真フィード投稿')
    parser.add_argument('--carousel', nargs='+', help='カルーセル写真投稿（複数パス）')
    parser.add_argument('--story', type=str, help='ストーリーズ写真投稿')
    parser.add_argument('--caption', type=str, default='', help='キャプション本文')
    args = parser.parse_args()

    print(f"📡 INSTAGRAM_API_MODE = {INSTAGRAM_API_MODE}")

    if args.check:
        ok = check_connection()
        sys.exit(0 if ok else 1)

    if args.photo:
        ok = post_to_instagram(args.caption, [args.photo])
        sys.exit(0 if ok else 1)

    if args.carousel:
        ok = post_to_instagram(args.caption, args.carousel)
        sys.exit(0 if ok else 1)

    if args.story:
        ok = post_to_instagram(args.caption, [args.story], story=True)
        sys.exit(0 if ok else 1)

    parser.print_help()


if __name__ == '__main__':
    main()
