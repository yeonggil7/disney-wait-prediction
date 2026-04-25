#!/usr/bin/env python3
"""
note.com のログインCookieを取得するスクリプト

Chromeを開いてnote.comにログインし、Cookieを取得して .env に保存する。
"""

import time
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def get_note_cookies() -> str:
    """Chromeでnote.comにログイン（手動）し、Cookieを文字列として返す"""
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,800")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("🌐 Chromeを起動してnote.comのログインページを開きます...")
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    try:
        driver.get("https://note.com/login")
        print()
        print("=" * 60)
        print("📌 ブラウザでnote.comにログインしてください")
        print("   （メール/パスワード、または Google/Twitter ログイン）")
        print("=" * 60)
        print()
        print("ログイン完了を待機中...")

        for i in range(120):
            time.sleep(2)
            try:
                current_url = driver.current_url or ""
            except Exception:
                current_url = ""
            if current_url and "/login" not in current_url and "note.com" in current_url:
                cookies = driver.get_cookies()
                if any(c["name"] == "_note_session_v5" for c in cookies):
                    print(f"✅ ログイン検出！ ({current_url})")
                    break
        else:
            print("❌ タイムアウト: 4分以内にログインが完了しませんでした")
            driver.quit()
            return ""

        time.sleep(2)
        cookies = driver.get_cookies()

        important_names = {"_note_session_v5", "_vid_v1", "_vid_v2",
                           "fp", "_ga", "_gid"}
        cookie_parts = []
        for c in cookies:
            if c["name"] in important_names or "session" in c["name"].lower():
                cookie_parts.append(f"{c['name']}={c['value']}")

        cookie_str = "; ".join(cookie_parts)
        print(f"   🍪 {len(cookie_parts)} cookies 取得")
        return cookie_str

    finally:
        driver.quit()


def save_to_env(cookie_str: str):
    """Cookie文字列を .env に保存"""
    env_path = Path(__file__).parent / ".env"

    if env_path.exists():
        content = env_path.read_text()
        lines = content.strip().split("\n")
        new_lines = [l for l in lines if not l.startswith("NOTE_COOKIES=")]
        new_lines.append(f"NOTE_COOKIES={cookie_str}")
        env_path.write_text("\n".join(new_lines) + "\n")
    else:
        env_path.write_text(f"NOTE_COOKIES={cookie_str}\n")

    print(f"   💾 .env に保存しました")


def main():
    cookie_str = get_note_cookies()
    if not cookie_str:
        print("❌ Cookie取得に失敗しました")
        sys.exit(1)

    save_to_env(cookie_str)

    print()
    print("=" * 60)
    print("✅ 完了！以下のコマンドで認証テストしてください：")
    print("   python note_client.py --check")
    print("=" * 60)


if __name__ == "__main__":
    main()
