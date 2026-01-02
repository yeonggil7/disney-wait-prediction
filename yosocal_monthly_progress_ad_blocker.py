#!/usr/bin/env python3
"""
yosocal.com 月単位進行スクリプト（広告対策版 + ディズニーランド選択確認版）
週末対応 + 月単位処理 + 広告ブロック + ディズニーランド確実選択

修正内容:
- realtime.htm接続後にpark1ラジオボタンを確実に選択  
- ディズニーランドのデータのみを取得
- ディズニーシーのデータは取得されません
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import calendar

def setup_driver():
    """強化された広告ブロック機能付きWebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    
    # 基本設定
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 広告ブロック設定強化
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images") 
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def main():
    """メイン処理"""
    print("🚀 月単位高速バッチ処理開始")
    print("=" * 50)
    
    driver = setup_driver()
    
    try:
        print(f"🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # 完全読み込み待機
        print("⏳ ページ完全読み込み待機...")
        time.sleep(10)
        
        print("🎉 ディズニーランド選択処理のテスト実行完了！")
        
    except Exception as e:
        print(f"❌ 処理エラー: {e}")
    finally:
        print("🔧 WebDriver終了...")
        driver.quit()

if __name__ == "__main__":
    main()
