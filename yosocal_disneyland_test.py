#!/usr/bin/env python3
"""
yosocal.com ディズニーランド専用データ取得テストスクリプト
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re

def setup_chrome_driver():
    """Chrome WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # WebDriverManagerで自動的に適切なバージョンを取得
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"❌ WebDriverセットアップ失敗: {e}")
        raise

def main():
    """テスト実行"""
    print("🚀 ディズニーランド選択テスト開始")
    print("="*50)
    
    driver = None
    
    try:
        # WebDriverセットアップ
        driver = setup_chrome_driver()
        
        # realtime.htmページにアクセス
        print(f"🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(5)
        
        # 🔥 ディズニーランド選択確認（重要！）
        try:
            land_radio = driver.find_element(By.ID, "park1")
            print(f"📍 park1ラジオボタン発見: {land_radio.is_selected()}")
            
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
                print("✅ ディズニーランドを選択しました")
            else:
                print("✅ ディズニーランドは既に選択済みです")
                
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # ページ内容確認
        time.sleep(5)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # jamatテーブル確認
        jamat_div = soup.find('div', id='jamat')
        if jamat_div:
            print("✅ jamat div発見")
            
            table = jamat_div.find('table')
            if table:
                print("✅ jamat table発見")
                
                # アトラクション名確認
                fph2_cells = table.find_all('td', class_='FPh2')
                attractions = []
                for cell in fph2_cells[:10]:  # 最初の10個だけ
                    attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                    if attraction_name:
                        attractions.append(attraction_name)
                
                print(f"🎯 発見されたアトラクション例:")
                for i, attraction in enumerate(attractions):
                    print(f"  {i+1}. {attraction}")
                
                # ディズニーランドアトラクション確認
                disneyland_keywords = ['スプラッシュ', 'ビッグサンダー', 'ハニハント', '美女と野獣', 'ベイマックス']
                found_disneyland = []
                
                for keyword in disneyland_keywords:
                    for attraction in attractions:
                        if keyword in attraction:
                            found_disneyland.append(attraction)
                
                if found_disneyland:
                    print(f"✅ ディズニーランドアトラクション確認: {found_disneyland}")
                else:
                    print("⚠️ ディズニーランドアトラクションが見つかりませんでした")
                    print("💡 これはディズニーシーのデータかもしれません")
                
            else:
                print("❌ jamat table未発見")
        else:
            print("❌ jamat div未発見")
        
        print("🎉 テスト完了！")
        
    except Exception as e:
        print(f"❌ メインエラー: {e}")
        
    finally:
        if driver:
            print("🔧 WebDriver終了...")
            driver.quit()

if __name__ == "__main__":
    main()
