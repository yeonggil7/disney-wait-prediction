#!/usr/bin/env python3
"""
yosocal.com Past Month Test
過去月（データがある月）でテスト
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def navigate_to_month(driver, target_year, target_month):
    """指定月に移動"""
    print(f"📅 {target_year}年{target_month}月に移動中...")
    
    # サイトアクセス
    driver.get("https://yosocal.com/realtime.htm")
    time.sleep(3)
    
    max_attempts = 12
    
    for attempt in range(max_attempts):
        try:
            current_year = driver.execute_script("return zzDate ? zzDate.getFullYear() : null;")
            current_month = driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : null;")
            
            print(f"  現在: {current_year}年{current_month}月")
            
            if current_year == target_year and current_month == target_month:
                print(f"✅ {target_year}年{target_month}月に到達")
                time.sleep(5)  # ページ更新待機
                return True
            
            # 前月または次月に移動
            if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                prev_btn = driver.find_element(By.XPATH, "//input[@value='前月']")
                prev_btn.click()
                print("  ← 前月へ移動")
            else:
                next_btn = driver.find_element(By.XPATH, "//input[@value='次月']")
                next_btn.click()
                print("  → 次月へ移動")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 月移動エラー: {e}")
            return False
    
    return False

def quick_test_month(driver, year, month):
    """月のデータ有無を簡単テスト"""
    print(f"\n🧪 === {year}年{month}月 テスト ===")
    
    if navigate_to_month(driver, year, month):
        # createAT2要素をチェック
        createat2_elements = driver.find_elements(By.XPATH, "//td[contains(@onclick, 'createAT2')]")
        print(f"  🎢 createAT2要素: {len(createat2_elements)}個")
        
        # テーブルをチェック
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tables = soup.find_all('table')
        large_tables = [t for t in tables if len(t.find_all('tr')) > 20]
        print(f"  📊 大型テーブル: {len(large_tables)}個")
        
        # アトラクション名をチェック
        page_text = driver.page_source
        attractions_found = []
        test_attractions = ['オムニバス', 'カリブの海賊', 'スプラッシュマウンテン', 'スペースマウンテン']
        
        for attraction in test_attractions:
            if attraction in page_text:
                attractions_found.append(attraction)
        
        print(f"  🎯 発見アトラクション: {len(attractions_found)}個 - {attractions_found}")
        
        # 日付情報
        date_elements = soup.find_all('td', class_='TDBT')
        dates_found = []
        for elem in date_elements:
            text = elem.get_text(strip=True)
            if re.search(r'\d+月\d+日', text):
                dates_found.append(text)
        
        print(f"  📅 発見日付: {dates_found}")
        
        return len(createat2_elements) > 0 and len(large_tables) > 0
    
    return False

def main():
    """メイン実行"""
    print("🧪 yosocal.com Past Month Data Test")
    print("複数の月をテストしてデータがある月を特定")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        # 複数の月をテスト
        test_months = [
            (2024, 12),  # 2024年12月
            (2024, 11),  # 2024年11月
            (2024, 10),  # 2024年10月
            (2025, 7),   # 2025年7月（現在月周辺）
            (2025, 6),   # 2025年6月
        ]
        
        working_months = []
        
        for year, month in test_months:
            has_data = quick_test_month(driver, year, month)
            
            if has_data:
                print(f"  ✅ データあり！")
                working_months.append((year, month))
            else:
                print(f"  ❌ データなし")
            
            time.sleep(2)
        
        print(f"\n📊 === テスト結果 ===")
        print(f"データがある月: {working_months}")
        
        if working_months:
            print(f"\n🎯 推奨：以下の月でスクレイピングを実行してください")
            for year, month in working_months:
                print(f"  - {year}年{month}月")
        else:
            print(f"\n❌ テストした月すべてでデータが見つかりませんでした")
            print(f"   より最近の月を試すか、サイトの仕様を再確認してください")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 