#!/usr/bin/env python3
"""
Instagram Graph API（公式）バックエンド

メリット:
- 公式API/規約準拠 / IPブロックなし / GitHub Actions と相性良
- Business / Creator アカウントが必要

事前にセットアップが必要な環境変数:
- INSTAGRAM_BUSINESS_ACCOUNT_ID  : IGビジネスアカウントID
- INSTAGRAM_ACCESS_TOKEN         : 長期Page Access Token (60日有効)
- FACEBOOK_APP_ID                : 自動更新用 (任意)
- FACEBOOK_APP_SECRET            : 自動更新用 (任意)
- IMGUR_CLIENT_ID                : 画像ホスティング (任意 / 推奨)

セットアップ手順:
    python scripts/ig_graph_setup.py guide

CLI 使い方:
    python post_via_instagram_graph.py --check
    python post_via_instagram_graph.py --photo path.jpg --caption "test"
    python post_via_instagram_graph.py --carousel a.jpg b.jpg --caption "carousel"
    python post_via_instagram_graph.py --story path.jpg
"""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).parent.absolute()

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


GRAPH_API_VERSION = os.environ.get("FACEBOOK_GRAPH_VERSION", "v21.0")
# バックエンド種別: "facebook"(旧/Page経由) or "instagram"(新/Loginログイン直接)
INSTAGRAM_GRAPH_BACKEND = os.environ.get("INSTAGRAM_GRAPH_BACKEND", "facebook").lower()

if INSTAGRAM_GRAPH_BACKEND == "instagram":
    GRAPH_BASE = "https://graph.instagram.com"
else:
    GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET", "")
IMGUR_CLIENT_ID = os.environ.get("IMGUR_CLIENT_ID", "")


def _ensure_graph_jpeg(path: str) -> str:
    """Graph APIに渡す画像をJPEGへ揃える。元画像は変更しない。"""
    p = Path(path)
    if p.suffix.lower() in (".jpg", ".jpeg"):
        return str(p)
    try:
        from PIL import Image
    except ImportError:
        return str(p)

    img = Image.open(p)
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (7, 88, 106))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    out = p.with_suffix(".jpg")
    img.save(out, "JPEG", quality=95, optimize=True)
    return str(out)


# =============================================================================
# 画像公開ホスティング
# =============================================================================
class ImageHost:
    """ローカル画像をMeta APIから到達可能なURLに変換する"""

    def __init__(self, imgur_client_id=None, verbose=True):
        self.imgur_client_id = imgur_client_id or IMGUR_CLIENT_ID
        self.verbose = verbose

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def upload(self, file_path: str) -> str:
        """画像/動画を公開URLにアップロードして返す（複数ホストでフォールバック）"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        ext = os.path.splitext(file_path)[1].lower()
        is_video = ext in {".mp4", ".mov", ".m4v"}

        hosts = []
        if self.imgur_client_id and not is_video:
            # ImgurはAPI種別が異なる/制限が多いので動画ではスキップ
            hosts.append(("Imgur", self._upload_imgur))
        hosts.extend([
            ("catbox.moe (litterbox 1h)", self._upload_litterbox),
            ("0x0.st", self._upload_0x0),
        ])
        if not is_video:
            hosts.append(("tmpfiles.org", self._upload_tmpfiles))
        hosts.append(("catbox.moe", self._upload_catbox))

        last_err = None
        for name, fn in hosts:
            try:
                url = fn(file_path)
                self._log(f"   📤 {name}: {url}")
                return url
            except Exception as e:
                self._log(f"   ⚠️ {name} 失敗: {e}")
                last_err = e

        raise RuntimeError(f"全てのホストでアップロード失敗: {last_err}")

    def _upload_imgur(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            r = requests.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {self.imgur_client_id}"},
                files={"image": f},
                timeout=120,
            )
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"Imgur error: {data}")
        return data["data"]["link"]

    def _upload_litterbox(self, file_path: str) -> str:
        """catbox.moe の一時アップロード版 (最大1時間保存)"""
        with open(file_path, 'rb') as f:
            r = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": f},
                timeout=60,
            )
        r.raise_for_status()
        url = r.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"litterbox 失敗: {url[:200]}")
        return url

    def _upload_0x0(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            r = requests.post(
                "https://0x0.st",
                files={"file": f},
                data={"expires": "24"},
                headers={"User-Agent": "disney-ai-wait/1.0"},
                timeout=60,
            )
        r.raise_for_status()
        url = r.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"0x0.st 失敗: {url[:200]}")
        return url

    def _upload_tmpfiles(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            r = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=60,
            )
        r.raise_for_status()
        data = r.json()
        url = data.get("data", {}).get("url", "")
        if not url:
            raise RuntimeError(f"tmpfiles 失敗: {data}")
        # tmpfiles.org/12345/file.png → tmpfiles.org/dl/12345/file.png (直接ファイル)
        return url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)

    def _upload_catbox(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=120,
            )
        r.raise_for_status()
        url = r.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"catbox.moe 失敗: {url[:200]}")
        return url


# =============================================================================
# Instagram Graph API クライアント
# =============================================================================
POST_LOG_FILE = os.environ.get(
    "INSTAGRAM_POST_LOG",
    str(Path(__file__).parent / "instagram_post_log.csv"),
)


class InstagramGraphPoster:
    def __init__(self, ig_user_id=None, access_token=None,
                 imgur_client_id=None, verbose=True,
                 post_log_file: str = None):
        self.ig_user_id = ig_user_id or INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.access_token = access_token or INSTAGRAM_ACCESS_TOKEN
        self.host = ImageHost(imgur_client_id=imgur_client_id, verbose=verbose)
        self.verbose = verbose
        self.post_log_file = post_log_file or POST_LOG_FILE

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def _record_post(self, media_id: str, post_type: str,
                      image_path: str = "", caption: str = "",
                      extra: dict = None):
        """投稿ログをCSVへ追記。Insights集計および A/B 分析で利用。

        Args:
            extra : dict 形式の任意メタデータ。JSON文字列としてCSVに格納。
                    例: {"cover_variant": "new", "park": "sea", "date": "2026-04-21"}
        """
        try:
            new_file = not os.path.exists(self.post_log_file)
            with open(self.post_log_file, "a", encoding="utf-8") as f:
                if new_file:
                    f.write("posted_at,media_id,post_type,image,caption_preview,extra\n")
                ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                preview = (caption or "").replace("\n", " ").replace(",", " ")[:80]
                # JSON エンコード後にカンマと改行をサニタイズ (CSV破壊回避)
                extra_str = ""
                if extra:
                    try:
                        extra_str = json.dumps(extra, ensure_ascii=False).replace(",", "|").replace("\n", " ")
                    except Exception:
                        extra_str = ""
                f.write(f"{ts},{media_id},{post_type},{image_path},{preview},{extra_str}\n")
        except Exception as e:
            self._log(f"   ⚠️ 投稿ログ書き込み失敗: {e}")

    # -------------------------------------------------------------------------
    def _check_credentials(self) -> bool:
        if not self.ig_user_id:
            print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID が未設定")
            return False
        if not self.access_token:
            print("❌ INSTAGRAM_ACCESS_TOKEN が未設定")
            return False
        return True

    # -------------------------------------------------------------------------
    def check_connection(self) -> bool:
        """アクセストークンとIGアカウントの正当性を確認"""
        if not self._check_credentials():
            return False

        # 新方式 (graph.instagram.com) はフィールド名が一部違う
        if INSTAGRAM_GRAPH_BACKEND == "instagram":
            fields = "id,username,name,account_type,followers_count"
        else:
            fields = "id,username,name,profile_picture_url,followers_count"

        try:
            r = requests.get(
                f"{GRAPH_BASE}/{self.ig_user_id}",
                params={
                    "fields": fields,
                    "access_token": self.access_token,
                },
                timeout=30,
            )
            if not r.ok:
                try:
                    err = r.json().get("error", {})
                    msg = err.get('message', r.text[:200])
                except Exception:
                    msg = r.text[:200]
                print(f"❌ Graph API エラー ({GRAPH_BASE}): {msg}")
                return False
            data = r.json()
            self._log(f"✅ Graph API 接続OK [{INSTAGRAM_GRAPH_BACKEND}]: "
                      f"@{data.get('username')} ({data.get('name', '-')}) "
                      f"- {data.get('followers_count', '?')} followers")
            return True
        except Exception as e:
            print(f"❌ 接続確認エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def _create_container(self, **params) -> str:
        params["access_token"] = self.access_token
        r = requests.post(
            f"{GRAPH_BASE}/{self.ig_user_id}/media",
            data=params,
            timeout=120,
        )
        if not r.ok:
            err = r.json().get("error", {})
            raise RuntimeError(
                f"コンテナ作成失敗: {err.get('message', r.text[:200])}"
            )
        return r.json()["id"]

    def _wait_for_container(self, container_id: str, timeout: int = 180) -> None:
        """コンテナがFINISHEDになるまで待機"""
        deadline = time.time() + timeout
        last_status = None
        while time.time() < deadline:
            r = requests.get(
                f"{GRAPH_BASE}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": self.access_token,
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            status = data.get("status_code", "")
            if status != last_status:
                self._log(f"   ⏳ container {container_id[:10]}... status={status}")
                last_status = status
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(
                    f"コンテナ処理失敗: {data.get('status', status)}"
                )
            time.sleep(3)
        raise TimeoutError(f"コンテナ処理タイムアウト ({timeout}s)")

    def _publish(self, container_id: str) -> str:
        r = requests.post(
            f"{GRAPH_BASE}/{self.ig_user_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": self.access_token,
            },
            timeout=60,
        )
        if not r.ok:
            err = r.json().get("error", {})
            raise RuntimeError(
                f"投稿公開失敗: {err.get('message', r.text[:200])}"
            )
        return r.json()["id"]

    # -------------------------------------------------------------------------
    def post_photo(self, image_path: str, caption: str = "") -> bool:
        if not self._check_credentials():
            return False
        try:
            image_path = _ensure_graph_jpeg(image_path)
            self._log(f"📷 フィード写真投稿: {os.path.basename(image_path)}")
            url = self.host.upload(image_path)
            cid = self._create_container(image_url=url, caption=caption)
            self._log(f"   ✅ コンテナ作成: {cid}")
            self._wait_for_container(cid)
            media_id = self._publish(cid)
            self._log(f"✅ Instagram投稿完了: media_id={media_id}")
            self._record_post(media_id, "photo", image_path, caption)
            return True
        except Exception as e:
            print(f"❌ 投稿エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def post_carousel(self, image_paths: list, caption: str = "",
                       extra: dict = None) -> bool:
        """
        Args:
            extra: 投稿ログに残す任意メタデータ (hook_variant 等、A/B 集計用)
        """
        if not self._check_credentials():
            return False
        if not (2 <= len(image_paths) <= 10):
            print("❌ カルーセルは2〜10枚必要です")
            return False
        try:
            self._log(f"🎠 カルーセル投稿（{len(image_paths)}枚）")
            child_cids = []
            for path in image_paths:
                path = _ensure_graph_jpeg(path)
                self._log(f"   - {os.path.basename(path)}")
                url = self.host.upload(path)
                cid = self._create_container(
                    image_url=url,
                    is_carousel_item="true",
                )
                child_cids.append(cid)

            for cid in child_cids:
                self._wait_for_container(cid)

            carousel_cid = self._create_container(
                media_type="CAROUSEL",
                children=",".join(child_cids),
                caption=caption,
            )
            self._wait_for_container(carousel_cid)
            media_id = self._publish(carousel_cid)
            self._log(f"✅ カルーセル投稿完了: media_id={media_id}")
            self._record_post(media_id, "carousel",
                              ";".join(image_paths), caption, extra=extra)
            return True
        except Exception as e:
            print(f"❌ カルーセル投稿エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def post_reel(self, video_path: str, caption: str = "",
                   cover_path: str = None, share_to_feed: bool = True,
                   extra: dict = None) -> bool:
        """Reels (mp4) 投稿。

        Args:
            video_path:    1080x1920 / H.264 / AAC の mp4
            caption:       キャプション (〜2200文字)
            cover_path:    Reelsタブ用カバー画像 (PNG/JPG)
            share_to_feed: True で通常フィードにも表示
            extra:         投稿ログに残す任意メタデータ (cover_variant 等)

        Notes:
            Reels はコンテナ処理に 30秒〜2分かかる。
            タイムアウトを 5分まで許容する。
        """
        if not self._check_credentials():
            return False
        try:
            self._log(f"🎬 Reels投稿: {os.path.basename(video_path)}")
            video_url = self.host.upload(video_path)

            params = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": "true" if share_to_feed else "false",
            }
            if cover_path and os.path.exists(cover_path):
                cover_url = self.host.upload(cover_path)
                params["cover_url"] = cover_url

            cid = self._create_container(**params)
            self._log(f"   ✅ コンテナ作成: {cid}")
            # Reels は処理に時間がかかる
            self._wait_for_container(cid, timeout=300)
            media_id = self._publish(cid)
            self._log(f"✅ Reels投稿完了: media_id={media_id}")
            extra_with_path = dict(extra or {})
            extra_with_path.setdefault("video_path", video_path)
            self._record_post(media_id, "reel", video_path, caption,
                              extra=extra_with_path)
            return True
        except Exception as e:
            print(f"❌ Reels投稿エラー: {e}")
            return False

    # -------------------------------------------------------------------------
    def post_story(self, image_path: str, caption: str = "") -> bool:
        """ストーリーズ写真投稿"""
        if not self._check_credentials():
            return False
        try:
            image_path = _ensure_graph_jpeg(image_path)
            self._log(f"📖 ストーリーズ投稿: {os.path.basename(image_path)}")
            url = self.host.upload(image_path)
            cid = self._create_container(
                image_url=url,
                media_type="STORIES",
            )
            self._wait_for_container(cid)
            media_id = self._publish(cid)
            self._log(f"✅ ストーリーズ投稿完了: media_id={media_id}")
            self._record_post(media_id, "story", image_path, caption)
            return True
        except Exception as e:
            print(f"❌ ストーリーズ投稿エラー: {e}")
            return False


# =============================================================================
# モジュールレベル API
# =============================================================================
_default_poster = None


def _get_default_poster():
    global _default_poster
    if _default_poster is None:
        _default_poster = InstagramGraphPoster()
    return _default_poster


def post_to_instagram(caption: str, image_paths=None, story=False) -> bool:
    """共通エントリポイント"""
    poster = _get_default_poster()
    if not image_paths:
        print("❌ Instagramはテキストのみ投稿不可。画像を指定してください。")
        return False
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    if story:
        return poster.post_story(image_paths[0], caption)
    if len(image_paths) == 1:
        return poster.post_photo(image_paths[0], caption)
    return poster.post_carousel(image_paths, caption)


def check_connection() -> bool:
    return _get_default_poster().check_connection()


# =============================================================================
# CLI
# =============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Instagram Graph API 投稿テスト")
    parser.add_argument("--check", action="store_true", help="認証確認")
    parser.add_argument("--photo", type=str, help="単一写真フィード投稿")
    parser.add_argument("--carousel", nargs="+", help="カルーセル写真投稿")
    parser.add_argument("--story", type=str, help="ストーリーズ写真投稿")
    parser.add_argument("--reel", type=str, help="Reels 動画投稿 (mp4)")
    parser.add_argument("--cover", type=str, help="Reels カバー画像 (任意)")
    parser.add_argument("--caption", type=str, default="", help="キャプション")
    args = parser.parse_args()

    poster = InstagramGraphPoster()

    if args.check:
        sys.exit(0 if poster.check_connection() else 1)
    if args.photo:
        sys.exit(0 if poster.post_photo(args.photo, args.caption) else 1)
    if args.carousel:
        sys.exit(0 if poster.post_carousel(args.carousel, args.caption) else 1)
    if args.story:
        sys.exit(0 if poster.post_story(args.story, args.caption) else 1)
    if args.reel:
        sys.exit(0 if poster.post_reel(args.reel, args.caption,
                                         cover_path=args.cover) else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
