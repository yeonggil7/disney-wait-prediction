#!/usr/bin/env python3
"""
yosocal.com クイックテスト
実際のサイト構造を確認するための小規模テスト
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def quick_test():
    """クイックテスト実行"""
    print("🔍 yosocal.com クイックテスト開始")
    print("=" * 50)
    
    driver = setup_driver()
    
    try:
        # サイトアクセス
        print("🌐 サイトアクセス中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        print("✅ ページロード完了")
        
        # 1. 現在の月を確認
        print("\n📅 === 現在の月確認 ===")
        try:
            current_year = driver.execute_script("return zzDate ? zzDate.getFullYear() : 'undefined';")
            current_month = driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : 'undefined';")
            print(f"現在: {current_year}年{current_month}月")
        except:
            print("❌ zzDate変数にアクセスできません")
        
        # 2. カレンダーの日付要素を確認
        print("\n📅 === カレンダー日付要素確認 ===")
        
        # 複数の方法で日付要素を探す
        search_patterns = [
            "//td[@onclick]",
            "//td[contains(@onclick, 'cal')]",
            "//a[contains(@href, 'cal')]",
            "//td[contains(@class, 'cal')]"
        ]
        
        for pattern in search_patterns:
            elements = driver.find_elements(By.XPATH, pattern)
            print(f"パターン '{pattern}': {len(elements)}個")
            
            if elements and len(elements) > 0:
                # 最初の3個の要素を詳しく調査
                for i, elem in enumerate(elements[:3]):
                    text = elem.text.strip()
                    onclick = elem.get_attribute('onclick')
                    href = elem.get_attribute('href')
                    classes = elem.get_attribute('class')
                    print(f"  要素{i+1}: text='{text}', onclick='{onclick}', class='{classes}'")
        
        # 3. ページソースからカレンダー構造を分析
        print("\n📊 === ページソース分析 ===")
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # テーブル分析
        tables = soup.find_all('table')
        print(f"テーブル総数: {len(tables)}")
        
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 5:  # 大きなテーブルのみ
                cells = table.find_all(['td', 'th'])
                onclick_cells = [cell for cell in cells if cell.get('onclick')]
                
                print(f"  テーブル{i+1}: {len(rows)}行, onclick要素{len(onclick_cells)}個")
                
                # onclick要素の詳細
                for j, cell in enumerate(onclick_cells[:3]):
                    text = cell.get_text(strip=True)
                    onclick = cell.get('onclick')
                    print(f"    onclick{j+1}: '{text}' -> {onclick}")
        
        # 4. 前月・次月ボタンの確認
        print("\n🔄 === 月移動ボタン確認 ===")
        month_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and (@value='前月' or @value='次月')]")
        print(f"月移動ボタン: {len(month_buttons)}個")
        
        for btn in month_buttons:
            value = btn.get_attribute('value')
            onclick = btn.get_attribute('onclick')
            print(f"  ボタン: '{value}' -> {onclick}")
        
        # 5. アトラクション要素の確認
        print("\n🎢 === アトラクション要素確認 ===")
        attraction_elements = driver.find_elements(By.XPATH, "//*[contains(@onclick, 'createAT2')]")
        print(f"createAT2要素: {len(attraction_elements)}個")
        
        for i, elem in enumerate(attraction_elements[:5]):
            text = elem.text.strip()
            onclick = elem.get_attribute('onclick')
            print(f"  アトラクション{i+1}: '{text}' -> {onclick}")
        
        # 6. 実際に日付をクリックしてみる
        print("\n🎯 === 日付クリックテスト ===")
        
        # 最初のクリック可能な要素を見つける
        clickable_elements = driver.find_elements(By.XPATH, "//td[@onclick] | //a[@onclick]")
        
        if clickable_elements:
            first_element = clickable_elements[0]
            text = first_element.text.strip()
            onclick = first_element.get_attribute('onclick')
            
            print(f"テスト対象: '{text}' ({onclick})")
            
            # クリック前のページ状態
            before_source = driver.page_source
            
            # クリック実行
            try:
                driver.execute_script("arguments[0].click();", first_element)
                time.sleep(2)
                
                # クリック後の状態
                after_source = driver.page_source
                
                if before_source != after_source:
                    print("✅ クリックでページが変化しました")
                    
                    # 変化後の新しいテーブルを調査
                    after_soup = BeautifulSoup(after_source, 'html.parser')
                    after_tables = after_soup.find_all('table')
                    
                    print(f"変化後のテーブル数: {len(after_tables)}")
                    
                    # 大きなテーブル（待ち時間データ）を探す
                    for i, table in enumerate(after_tables):
                        rows = table.find_all('tr')
                        if 25 <= len(rows) <= 35:
                            print(f"  待ち時間候補テーブル{i+1}: {len(rows)}行")
                            
                            # 最初の数行をサンプル表示
                            for j, row in enumerate(rows[:3]):
                                cells = row.find_all(['td', 'th'])
                                texts = [cell.get_text(strip=True) for cell in cells[:5]]
                                print(f"    行{j+1}: {' | '.join(texts)}")
                
                else:
                    print("❌ クリックしてもページが変化しませんでした")
                    
            except Exception as e:
                print(f"❌ クリックエラー: {e}")
        
        else:
            print("❌ クリック可能な要素が見つかりません")
        
        print("\n✅ クイックテスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    quick_test() 