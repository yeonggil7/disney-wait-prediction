# -*- coding: utf-8 -*-
"""
yosocal.com 効率化版長期間データ取得システム
処理時間を大幅に短縮した高速版
"""

import time
import csv
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm

def setup_driver():
    """高速WebDriverセットアップ"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # ヘッドレスで高速化
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-images")  # 画像読み込み無効で高速化
    chrome_options.add_argument("--disable-javascript")  # JavaScript無効（必要な場合のみ有効化）
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(5)  # 暗黙的待機を短縮
    
    return driver

def navigate_to_month_fast(driver, year, month):
    """高速月移動"""
    try:
        driver.get('https://yosocal.com/')
        time.sleep(1)  # 待機時間短縮
        
        # JavaScript有効化してから月移動
        driver.execute_script("return true")  # JavaScript動作確認
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(2)  # 待機時間短縮
        
        return True, f"{year}年{month}月"
        
    except Exception as e:
        return False, str(e)

def extract_dates_fast(driver):
    """高速日付抽出"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        dates = []
        for class_name in ['CAL', 'CALSAT', 'CALSUN']:
            elements = soup.find_all('div', class_=class_name)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text == '1/1':
                    dates.append(1)
                elif text.isdigit() and 1 <= int(text) <= 31:
                    dates.append(int(text))
        
        return sorted(list(set(dates)))
        
    except:
        return []

def click_and_extract_fast(driver, date_num, year, month):
    """高速クリック&データ抽出"""
    try:
        # 高速日付クリック
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
                date_element = elements[0]
                break
        
        if not date_element:
            return []
        
        date_element.click()
        time.sleep(1)  # 待機時間短縮
        
        # realtime.htmへ高速移動
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(2)  # 待機時間短縮
        
        # 高速データ抽出
        return extract_data_fast(driver, year, month, date_num)
        
    except:
        return []

def extract_data_fast(driver, year, month, date_num):
    """高速データ抽出（簡易版）"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return []
        
        table = jamat_div.find('table')
        if not table:
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 2:
            return []
        
        data = []
        
        # 最初の10アトラクションのみ処理（高速化）
        for row_idx, row in enumerate(rows[1:11]):
            cells = row.find_all(['td', 'th'])
            if cells:
                attraction = cells[0].get_text(strip=True)
                if attraction and attraction not in ['時間', 'アトラクション']:
                    # 最初の5時間帯のみ処理（高速化）
                    for cell_idx in range(1, min(6, len(cells))):
                        cell = cells[cell_idx]
                        wait_time_text = cell.get_text(strip=True)
                        
                        record = {
                            'date': f"{month}月{date_num:02d}日",
                            'year': year,
                            'month': month,
                            'day': date_num,
                            'time': f"time_{cell_idx}",
                            'attraction': attraction,
                            'wait_time': float(wait_time_text) if wait_time_text.isdigit() else None,
                            'raw_value': wait_time_text
                        }
                        data.append(record)
        
        return data
        
    except:
        return []

def save_data_fast(filename, data):
    """高速データ保存"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 'raw_value']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return True
    except:
        return False

def main():
    """効率化版メインプロセス"""
    print("⚡ yosocal.com 効率化版長期間データ取得")
    print("📅 対象: 2024年1月-2025年6月 (高速処理)")
    print("=" * 50)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_optimized_{timestamp}.csv"
    
    # 対象月リスト
    target_months = []
    for year in [2024, 2025]:
        end_month = 12 if year == 2024 else 6
        for month in range(1, end_month + 1):
            target_months.append((year, month))
    
    print(f"📋 処理対象: {len(target_months)}ヶ月")
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        print("✅ 高速WebDriver準備完了")
        
        # 高速月別処理
        for year, month in tqdm(target_months, desc="月別処理"):
            
            # 月移動
            success, result = navigate_to_month_fast(driver, year, month)
            if not success:
                continue
            
            # 日付抽出
            dates = extract_dates_fast(driver)
            if not dates:
                continue
            
            # 高速日別処理（最初の5日のみ）
            month_data = []
            for date_num in dates[:5]:  # 高速化のため最初の5日のみ
                try:
                    navigate_to_month_fast(driver, year, month)
                    data = click_and_extract_fast(driver, date_num, year, month)
                    if data:
                        month_data.extend(data)
                except:
                    continue
            
            all_data.extend(month_data)
            
            # 5ヶ月ごとに中間保存
            if len(all_data) > 0 and (year * 100 + month) % 500 == 0:
                save_data_fast(output_file, all_data)
        
        # 最終保存
        if all_data:
            save_data_fast(output_file, all_data)
            
            print(f"\n📊 効率化版結果:")
            print(f"   📁 ファイル: {output_file}")
            print(f"   📈 データ数: {len(all_data):,}件")
            
            valid_data = [d for d in all_data if d['wait_time'] is not None]
            print(f"   ✅ 有効データ: {len(valid_data):,}件")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # 年別統計
            for year in [2024, 2025]:
                year_data = [d for d in all_data if d['year'] == year]
                if year_data:
                    print(f"   {year}年: {len(year_data):,}件")
        
        print("\n⚡ 効率化版処理完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main() 