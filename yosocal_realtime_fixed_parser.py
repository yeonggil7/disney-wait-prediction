# -*- coding: utf-8 -*-
"""
yosocal.com テーブル構造修正版データ抽出システム
CSVファイル分析結果に基づく正確なデータ抽出
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

def setup_driver_fixed():
    """修正版WebDriverセットアップ"""
    print("🔧 Chrome WebDriver（修正版）をセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        print("📥 ChromeDriverを自動ダウンロード中...")
        chrome_driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver取得完了: {chrome_driver_path}")
        
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ WebDriverセットアップ完了")
        return driver
        
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def extract_wait_time_data_corrected(driver, year, month, date_num):
    """修正版データ抽出 - テーブル構造を正しく解析"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamat div未発見")
            return []
        
        # テーブルを探す
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブル未発見")
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 2:
            print(f"❌ テーブル行数不足: {len(rows)}行")
            return []
        
        print(f"📊 テーブル解析開始: {len(rows)}行")
        
        # ヘッダー行から時間帯を抽出
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        
        # 時間帯のパターンを抽出
        time_slots = []
        for i, cell in enumerate(header_cells):
            cell_text = cell.get_text(strip=True)
            # 時間帯のパターンをチェック（8:15, 8:45, ..., 21:45, 平均）
            if re.match(r'^\d{1,2}:\d{2}$', cell_text) or cell_text == '平均':
                time_slots.append((i, cell_text))
        
        print(f"⏰ 時間帯: {len(time_slots)}個 - {[t[1] for t in time_slots[:5]]}...")
        
        extracted_data = []
        
        # データ行を処理
        for row_idx, row in enumerate(rows[1:], 1):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            # アトラクション名を取得（最初のセル）
            attraction_name = cells[0].get_text(strip=True)
            
            # アトラクション名のフィルタリング
            skip_names = ['TIME', '時間', 'アトラクション', '平均', '', '天気・気温']
            if attraction_name in skip_names:
                continue
            
            print(f"🎢 アトラクション: {attraction_name}")
            
            # 各時間帯のデータを抽出
            for time_idx, time_slot in time_slots:
                if time_idx < len(cells):
                    cell = cells[time_idx]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    # 待ち時間データの判定
                    wait_time = None
                    status = 'unknown'
                    
                    if cell_text == '-' or cell_text == '':
                        status = 'no_data'
                    elif cell_text.isdigit():
                        status = 'normal'
                        wait_time = float(cell_text)
                    elif re.match(r'^\d+分?$', cell_text):
                        # 「30分」のようなパターン
                        status = 'normal'
                        wait_time = float(re.findall(r'\d+', cell_text)[0])
                    else:
                        # A, B, C, S などの記号
                        status = 'symbol'
                    
                    # データ記録
                    record = {
                        'date': f"{month}月{date_num:02d}日",
                        'year': year,
                        'month': month,
                        'day': date_num,
                        'time': time_slot,
                        'attraction': attraction_name,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'realtime.htm修正版'
                    }
                    extracted_data.append(record)
        
        print(f"✅ 抽出完了: {len(extracted_data)}件")
        return extracted_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def click_date_and_get_corrected_data(driver, date_num, year, month):
    """日付をクリックして修正版データ抽出"""
    try:
        # メインページで日付クリック
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        # 月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        # 日付クリック
        xpath_patterns = [
            f"//div[@class='CAL'][text()='{date_num}']",
            f"//div[@class='CALSAT'][text()='{date_num}']", 
            f"//div[@class='CALSUN'][text()='{date_num}']"
        ]
        
        if date_num == 1:
            xpath_patterns.append("//div[@class='CALSUN'][text()='1/1']")
        
        date_element = None
        for xpath in xpath_patterns:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", elements[0])
                date_element = elements[0]
                break
        
        if not date_element:
            return [], f"日付{date_num}が見つかりません"
        
        time.sleep(2)
        
        # realtime.htmに移動してデータ抽出
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(4)
        
        # 修正版データ抽出
        data = extract_wait_time_data_corrected(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def test_corrected_extraction():
    """修正版データ抽出テスト"""
    print("🚀 yosocal.com テーブル構造修正版データ抽出テスト")
    print("🔧 CSVファイル分析結果に基づく正確なデータ抽出")
    print("=" * 60)
    
    driver = None
    
    try:
        driver = setup_driver_fixed()
        
        # 2024年1月1日でテスト
        print(f"🧪 テスト対象: 2024年1月1日")
        
        data, status = click_date_and_get_corrected_data(driver, 1, 2024, 1)
        
        if data:
            # テスト結果をCSVファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_file = f"yosocal_corrected_test_{timestamp}.csv"
            
            with open(test_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"\n📊 修正版テスト結果:")
            print(f"   📁 テストファイル: {test_file}")
            print(f"   📈 総データ数: {len(data):,}件")
            
            # アトラクション別集計
            attractions = {}
            valid_data = []
            for d in data:
                attraction = d['attraction']
                if attraction not in attractions:
                    attractions[attraction] = 0
                attractions[attraction] += 1
                
                if d['wait_time'] is not None:
                    valid_data.append(d)
            
            print(f"   🎢 アトラクション数: {len(attractions)}個")
            print(f"   ✅ 有効データ: {len(valid_data)}件")
            
            # トップアトラクション表示
            print(f"\n🎢 アトラクション一覧:")
            for i, (name, count) in enumerate(sorted(attractions.items())[:10], 1):
                print(f"   {i:2d}. {name}: {count}件")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            print(f"\n✅ 修正版データ抽出テスト成功！")
        else:
            print(f"❌ テスト失敗: {status}")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    test_corrected_extraction() 