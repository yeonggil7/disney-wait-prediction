#!/usr/bin/env python3
"""
note.com 非公式APIクライアント

Cookie認証を使った記事の作成・更新・公開を行う。
公式APIが存在しないため非公式エンドポイントを利用。
"""

import os
import re
import time
import json
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

BASE_URL = "https://note.com"
EDITOR_URL = "https://editor.note.com"

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Origin": EDITOR_URL,
    "Referer": f"{EDITOR_URL}/",
}

REQUEST_INTERVAL = 2.5


class NoteClient:
    """note.com API client using cookie authentication."""

    def __init__(self, cookies: dict = None):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        if cookies:
            self.session.cookies.update(cookies)
        else:
            self._load_cookies_from_env()

    def _load_cookies_from_env(self):
        cookie_str = os.environ.get("NOTE_COOKIES", "")
        if not cookie_str:
            print("⚠️  NOTE_COOKIES が設定されていません")
            return
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                self.session.cookies.set(k.strip(), v.strip())

    def _reauth(self):
        """メール/パスワードでAPIログインし、Cookie を更新する"""
        email = os.environ.get("NOTE_EMAIL", "")
        password = os.environ.get("NOTE_PASSWORD", "")
        if not email or not password:
            raise RuntimeError(
                "NOTE_EMAIL / NOTE_PASSWORD が未設定のため再認証できません"
            )
        print("   🔄 Cookie 失効 → API再ログイン中...")
        s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        s.get(f"{BASE_URL}/login")
        resp = s.post(
            f"{BASE_URL}/api/v1/sessions/sign_in",
            json={"login": email, "password": password},
        )
        if resp.status_code not in (200, 201) or "error" in resp.json():
            raise RuntimeError(
                f"再ログイン失敗 ({resp.status_code}): {resp.text[:200]}"
            )
        self.session.cookies.update(s.cookies)

        cookie_parts = []
        for c in s.cookies:
            if "session" in c.name.lower():
                cookie_parts.append(f"{c.name}={c.value}")
        if cookie_parts:
            new_cookie_str = "; ".join(cookie_parts)
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                lines = env_path.read_text().strip().split("\n")
                lines = [l for l in lines if not l.startswith("NOTE_COOKIES=")]
                lines.append(f"NOTE_COOKIES={new_cookie_str}")
                env_path.write_text("\n".join(lines) + "\n")
            os.environ["NOTE_COOKIES"] = new_cookie_str
        print("   ✅ 再ログイン成功")

    def _wait(self):
        time.sleep(REQUEST_INTERVAL)

    # ------------------------------------------------------------------
    # User info
    # ------------------------------------------------------------------

    def get_me(self) -> dict:
        """ログイン中ユーザーの情報を取得（失効時は自動再認証）"""
        resp = self.session.get(f"{BASE_URL}/api/v1/current_user")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            name = data.get("nickname", "?")
            urlname = data.get("urlname", "?")
            print(f"✅ note 認証OK ({name} @{urlname})")
            return data
        self._reauth()
        resp = self.session.get(f"{BASE_URL}/api/v1/current_user")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            name = data.get("nickname", "?")
            urlname = data.get("urlname", "?")
            print(f"✅ note 認証OK ({name} @{urlname})")
            return data
        raise RuntimeError(f"認証失敗 ({resp.status_code}): 再ログイン後も認証できません")

    # ------------------------------------------------------------------
    # Image upload
    # ------------------------------------------------------------------

    def upload_image(self, image_path: str) -> dict:
        """画像をアップロードし、key と url を返す"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像が見つかりません: {image_path}")

        headers = {k: v for k, v in DEFAULT_HEADERS.items()
                   if k != "Content-Type"}

        with open(image_path, "rb") as f:
            resp = self.session.post(
                f"{BASE_URL}/api/v1/upload_image",
                headers=headers,
                files={"file": f},
            )

        self._wait()
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            print(f"   📷 画像アップロード完了: {data.get('key', '?')}")
            return data
        raise RuntimeError(f"画像アップロード失敗 ({resp.status_code}): {resp.text[:200]}")

    # ------------------------------------------------------------------
    # Article listing & deletion
    # ------------------------------------------------------------------

    def list_my_articles(self, count: int = 20) -> list[dict]:
        """自分の公開記事一覧を取得"""
        me = self.get_me()
        urlname = me.get("urlname", "")
        resp = self.session.get(
            f"{BASE_URL}/api/v2/creators/{urlname}/contents"
            f"?kind=note&page=1&per_page={count}",
        )
        if resp.status_code == 200:
            notes = resp.json().get("data", {}).get("contents", [])
            return notes
        raise RuntimeError(
            f"記事一覧取得失敗 ({resp.status_code}): {resp.text[:200]}"
        )

    def delete_article(self, note_id: int) -> bool:
        """記事を削除する (数値ID)"""
        resp = self.session.delete(
            f"{BASE_URL}/api/v1/notes/{note_id}",
        )
        self._wait()
        if resp.status_code in (200, 204):
            print(f"   🗑️  削除完了: id={note_id}")
            return True
        raise RuntimeError(
            f"削除失敗 ({resp.status_code}): {resp.text[:200]}"
        )

    # ------------------------------------------------------------------
    # Article CRUD
    # ------------------------------------------------------------------

    def create_article(self, title: str, body_html: str) -> dict:
        """記事を新規作成し、id と key を返す"""
        payload = {
            "name": title,
            "body": body_html,
            "template_key": None,
        }
        resp = self.session.post(
            f"{BASE_URL}/api/v1/text_notes",
            json=payload,
        )
        self._wait()
        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            print(f"   📝 記事作成: id={data.get('id')} key={data.get('key')}")
            return data
        raise RuntimeError(f"記事作成失敗 ({resp.status_code}): {resp.text[:300]}")

    def update_draft(self, article_id: int, title: str, body_html: str,
                     eyecatch_key: str = None, hashtags: list = None) -> bool:
        """記事を下書き保存"""
        payload = {
            "name": title,
            "body": body_html,
            "body_length": len(body_html),
            "index": False,
            "is_lead_form": False,
        }
        if eyecatch_key:
            payload["eyecatch_image_key"] = eyecatch_key
        if hashtags:
            payload["hashtag_notes"] = [
                {"hashtag": {"name": h.lstrip("#")}} for h in hashtags
            ]

        resp = self.session.post(
            f"{BASE_URL}/api/v1/text_notes/draft_save"
            f"?id={article_id}&is_temp_saved=true",
            json=payload,
        )
        self._wait()
        if resp.status_code == 200:
            print(f"   💾 下書き保存完了: id={article_id}")
            return True
        raise RuntimeError(f"下書き保存失敗 ({resp.status_code}): {resp.text[:300]}")

    def _post_via_browser(self, title: str, body_html: str,
                          hashtags: list = None,
                          draft_only: bool = False) -> dict:
        """Seleniumでエディタに記事を入力し、公開(or下書き保存)する"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        import platform

        me_data = self.get_me()
        urlname = me_data.get("urlname", "unknown")
        cookie_str = os.environ.get("NOTE_COOKIES", "")

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1200,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        try:
            driver.get("https://note.com")
            time.sleep(1)
            for pair in cookie_str.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    try:
                        driver.add_cookie({
                            "name": k.strip(),
                            "value": v.strip(),
                            "domain": ".note.com",
                        })
                    except Exception:
                        pass

            driver.get("https://note.com/notes/new")
            time.sleep(6)

            cur_url = driver.current_url
            if "/notes/" in cur_url:
                article_key = cur_url.split("/notes/")[1].split("/")[0]
            else:
                article_key = "unknown"
            print(f"   📝 新規記事: key={article_key} url={cur_url}")

            # Type title
            title_el = driver.find_element(
                By.CSS_SELECTOR,
                'textarea[placeholder*="タイトル"]',
            )
            title_el.click()
            title_el.send_keys(title)
            time.sleep(1)

            # Paste HTML into ProseMirror editor via clipboard API
            editor = driver.find_element(
                By.CSS_SELECTOR,
                '[contenteditable="true"].ProseMirror',
            )
            editor.click()
            time.sleep(0.5)

            # Remove UUID name/id attrs (not needed for paste)
            import re as _re
            clean_html = _re.sub(
                r'\s+(?:name|id)="[^"]*"', "", body_html,
            )

            driver.execute_script("""
                const editor = arguments[0];
                const html = arguments[1];

                editor.focus();

                const dt = new DataTransfer();
                dt.setData('text/html', html);
                dt.setData('text/plain', html.replace(/<[^>]+>/g, ''));

                const pasteEvent = new ClipboardEvent('paste', {
                    bubbles: true,
                    cancelable: true,
                    clipboardData: dt,
                });
                editor.dispatchEvent(pasteEvent);
            """, editor, clean_html)

            time.sleep(3)

            if draft_only:
                driver.execute_script("""
                    let buttons = document.querySelectorAll('button');
                    for (let b of buttons) {
                        if (b.textContent.includes('下書き保存')) {
                            b.click(); break;
                        }
                    }
                """)
                time.sleep(3)
                url = f"https://note.com/{urlname}/n/{article_key}"
                print(f"   📋 下書き保存: {url}")
                return {"key": article_key, "url": url, "status": "draft"}

            # Click 公開に進む
            driver.execute_script("""
                let buttons = document.querySelectorAll('button');
                for (let b of buttons) {
                    if (b.textContent.includes('公開に進む')) {
                        b.click(); break;
                    }
                }
            """)
            time.sleep(5)

            # Add hashtags
            if hashtags:
                try:
                    tag_inputs = driver.find_elements(
                        By.CSS_SELECTOR,
                        'input[placeholder*="ハッシュタグ"], '
                        'input[placeholder*="タグ"]',
                    )
                    if tag_inputs:
                        inp = tag_inputs[0]
                        for tag in hashtags[:5]:
                            inp.clear()
                            inp.send_keys(tag.lstrip("#"))
                            inp.send_keys(Keys.RETURN)
                            time.sleep(0.5)
                except Exception:
                    pass

            time.sleep(2)

            # Click 投稿する
            driver.execute_script("""
                let buttons = document.querySelectorAll('button');
                for (let b of buttons) {
                    let t = b.textContent.trim();
                    if (t === '投稿する') { b.click(); break; }
                }
            """)
            time.sleep(8)

            url = f"https://note.com/{urlname}/n/{article_key}"
            print(f"   ✅ 公開: {url}")
            return {"key": article_key, "url": url, "status": "published"}

        finally:
            driver.quit()

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def upload_images_in_markdown(self, md: str) -> str:
        """Markdown 内の ![alt](ローカルパス) を note URL に置換する"""
        img_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

        def _replace(m):
            alt = m.group(1)
            path = m.group(2)
            if path.startswith("http://") or path.startswith("https://"):
                return m.group(0)
            try:
                data = self.upload_image(path)
                url = data.get("file_url") or data.get("url", "")
                if url:
                    return f"![{alt}]({url})"
            except Exception as e:
                print(f"   ⚠️ 画像アップロード失敗 ({path}): {e}")
            return m.group(0)

        return img_re.sub(_replace, md)

    def post_article(self, title: str, body_html: str,
                     eyecatch_path: str = None,
                     hashtags: list = None,
                     draft_only: bool = False) -> dict:
        """
        Selenium でエディタに記事を入力し、公開(または下書き保存)する。
        Returns: {"key": ..., "url": ..., "status": ...}
        """
        return self._post_via_browser(
            title, body_html, hashtags, draft_only,
        )

    # ------------------------------------------------------------------
    # Markdown → note HTML conversion
    # ------------------------------------------------------------------

    @staticmethod
    def markdown_to_html(md: str) -> str:
        """Markdown テキストを note 向け HTML に変換
        note は各要素に name/id 属性 (UUID) を必要とする。
        """
        import uuid

        def _uid():
            return str(uuid.uuid4())

        def _inline(text):
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            return text

        lines = md.strip().split("\n")
        html_parts = []
        ul_items = []
        ol_items = []

        def _flush_ul():
            nonlocal ul_items
            if ul_items:
                uid = _uid()
                inner = "".join(ul_items)
                html_parts.append(
                    f'<ul name="{uid}" id="{uid}">{inner}</ul>'
                )
                ul_items = []

        def _flush_ol():
            nonlocal ol_items
            if ol_items:
                uid = _uid()
                inner = "".join(ol_items)
                html_parts.append(
                    f'<ol name="{uid}" id="{uid}">{inner}</ol>'
                )
                ol_items = []

        img_re = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")

        for line in lines:
            img_m = img_re.match(line.strip())
            if img_m:
                _flush_ul(); _flush_ol()
                alt = img_m.group(1)
                src = img_m.group(2)
                uid = _uid()
                html_parts.append(
                    f'<figure name="{uid}" id="{uid}">'
                    f'<img src="{src}" alt="{alt}">'
                    f"</figure>"
                )
            elif line.startswith("### "):
                _flush_ul(); _flush_ol()
                uid = _uid()
                content = _inline(line[4:])
                html_parts.append(
                    f'<h3 name="{uid}" id="{uid}">{content}</h3>'
                )
            elif line.startswith("## "):
                _flush_ul(); _flush_ol()
                uid = _uid()
                content = _inline(line[3:])
                html_parts.append(
                    f'<h2 name="{uid}" id="{uid}">{content}</h2>'
                )
            elif line.startswith("# "):
                _flush_ul(); _flush_ol()
                uid = _uid()
                content = _inline(line[2:])
                html_parts.append(
                    f'<h2 name="{uid}" id="{uid}">{content}</h2>'
                )
            elif line.startswith("- ") or line.startswith("* "):
                _flush_ol()
                uid = _uid()
                item = _inline(line[2:])
                ul_items.append(
                    f'<li><p name="{uid}" id="{uid}">{item}</p></li>'
                )
            elif re.match(r"^\d+\.\s", line):
                _flush_ul()
                uid = _uid()
                item = _inline(re.sub(r"^\d+\.\s", "", line))
                ol_items.append(
                    f'<li><p name="{uid}" id="{uid}">{item}</p></li>'
                )
            elif line.strip() == "":
                _flush_ul(); _flush_ol()
            else:
                _flush_ul(); _flush_ol()
                uid = _uid()
                content = _inline(line)
                html_parts.append(
                    f'<p name="{uid}" id="{uid}">{content}</p>'
                )

        _flush_ul(); _flush_ol()
        return "".join(html_parts)


def check_auth() -> bool:
    """NOTE_COOKIES の認証をテスト"""
    try:
        client = NoteClient()
        client.get_me()
        return True
    except Exception as e:
        print(f"❌ note認証エラー: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="note.com クライアントテスト")
    parser.add_argument("--check", action="store_true", help="認証確認")
    parser.add_argument("--test-post", action="store_true",
                        help="テスト記事を下書き保存")
    args = parser.parse_args()

    if args.check:
        check_auth()
    elif args.test_post:
        client = NoteClient()
        client.get_me()
        md = "# テスト記事\n\nこれはAPIからの投稿テストです。\n\n## セクション1\n\n- 項目A\n- 項目B"
        html = NoteClient.markdown_to_html(md)
        result = client.post_article(
            title="APIテスト記事",
            body_html=html,
            draft_only=True,
        )
        print(f"結果: {result}")
    else:
        parser.print_help()
