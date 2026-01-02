# -*- coding: utf-8 -*-
"""
yosocal.com webdriver-manager専用版
Chrome 137対応ChromeDriver自動ダウンロード
"""

import time
import csv
import json
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from tqdm import tqdm

def setup_driver_auto():
    """webdriver-manager自動ChromeDriverダウンロード版"""
    print("🔧 Chrome WebDriver（webdriver-manager版）をセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        # webdriver-managerで最新の互換性のあるChromeDriverを取得
        print("📥 ChromeDriverを自動ダウンロード中...")
        chrome_driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver取得完了: {chrome_driver_path}")
        
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # automation detectionを回避
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 接続テスト
        print("🧪 接続テスト実行中...")
        driver.get('https://www.google.com')
        time.sleep(2)
        
        print("✅ WebDriverセットアップ完了")
        return driver
        
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def test_yosocal_access(driver):
    """yosocal.comアクセステスト"""
    print("🧪 yosocal.comアクセステスト実行中...")
    
    try:
        # メインページアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        page_title = driver.title
        print(f"✅ メインページアクセス成功: {page_title}")
        
        # realtime.htmアクセス
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(3)
        
        # jamatテーブル検索
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        jamat_div = soup.find('div', id='jamat')
        if jamat_div:
            print("✅ jamat div発見")
            
            table = jamat_div.find('table')
            if table:
                rows = table.find_all('tr')
                print(f"✅ テーブル発見: {len(rows)}行")
                
                if len(rows) > 1:
                    # サンプル行を表示
                    sample_row = rows[1]
                    cells = sample_row.find_all(['td', 'th'])
                    if cells:
                        attraction_name = cells[0].get_text(strip=True)
                        print(f"✅ サンプルアトラクション: {attraction_name}")
                        
                        # 時間データを表示
                        for i, cell in enumerate(cells[1:6]):  # 最初の5時間帯
                            cell_text = cell.get_text(strip=True)
                            print(f"   時間{i+1}: {cell_text}")
                
                return True, f"テーブル{len(rows)}行を発見"
            else:
                return False, "jamat div内にテーブルなし"
        else:
            return False, "jamat divが見つかりません"
            
    except Exception as e:
        return False, f"アクセステストエラー: {e}"

def test_calendar_navigation(driver):
    """カレンダーナビゲーションテスト"""
    print("🧪 カレンダーナビゲーションテスト実行中...")
    
    try:
        # メインページアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # 2024年1月に移動
        js_code = "Fnc_L(new Date(2024, 0, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        # カレンダー日付を探す
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        available_dates = []
        date_classes = ['CAL', 'CALSAT', 'CALSUN']
        
        for class_name in date_classes:
            date_elements = soup.find_all('div', class_=class_name)
            for element in date_elements:
                date_text = element.get_text(strip=True)
                if date_text == '1/1':
                    available_dates.append(1)
                elif date_text.isdigit():
                    date_num = int(date_text)
                    if 1 <= date_num <= 31:
                        available_dates.append(date_num)
        
        available_dates = sorted(list(set(available_dates)))
        print(f"✅ 2024年1月利用可能日付: {len(available_dates)}日")
        print(f"   日付: {available_dates[:10]}...")  # 最初の10日を表示
        
        if available_dates:
            # 1日をクリックしてテスト
            test_date = available_dates[0]
            xpath_patterns = [
                f"//div[@class='CAL'][text()='{test_date}']",
                f"//div[@class='CALSAT'][text()='{test_date}']", 
                f"//div[@class='CALSUN'][text()='{test_date}']"
            ]
            
            if test_date == 1:
                xpath_patterns.append("//div[@class='CALSUN'][text()='1/1']")
            
            date_clicked = False
            for xpath in xpath_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", elements[0])
                        date_clicked = True
                        print(f"✅ {test_date}日クリック成功")
                        break
                except:
                    continue
            
            if date_clicked:
                time.sleep(2)
                
                # realtime.htmに移動してデータ確認
                driver.get('https://yosocal.com/realtime.htm')
                time.sleep(4)
                
                # データ抽出テスト
                test_success, test_message = test_yosocal_access(driver)
                
                return test_success, f"カレンダーナビゲーション＋データ抽出: {test_message}"
            else:
                return False, f"{test_date}日をクリックできませんでした"
        else:
            return False, "利用可能日付が見つかりません"
            
    except Exception as e:
        return False, f"カレンダーナビゲーションエラー: {e}"

def main():
    """包括的テスト実行"""
    print("🚀 yosocal.com webdriver-manager版包括的テストシステム")
    print("🧪 Chrome 137対応ChromeDriver自動ダウンロード＋機能テスト")
    print("=" * 60)
    
    driver = None
    
    try:
        # WebDriverセットアップ
        driver = setup_driver_auto()
        
        # テスト1: yosocal.comアクセステスト
        print("\n🧪 テスト1: yosocal.comアクセステスト")
        success1, message1 = test_yosocal_access(driver)
        print(f"結果1: {message1}")
        
        if success1:
            # テスト2: カレンダーナビゲーションテスト
            print("\n🧪 テスト2: カレンダーナビゲーション＋データ抽出テスト")
            success2, message2 = test_calendar_navigation(driver)
            print(f"結果2: {message2}")
            
            if success2:
                print(f"\n✅ 全テスト成功！")
                print(f"📝 システムは完全に動作しています。")
                print(f"🚀 長期間データ取得を開始できます。")
            else:
                print(f"\n⚠️ カレンダーナビゲーションに問題があります: {message2}")
        else:
            print(f"\n❌ yosocal.comアクセスに問題があります: {message1}")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 