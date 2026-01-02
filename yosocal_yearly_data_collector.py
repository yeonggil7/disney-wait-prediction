# -*- coding: utf-8 -*-
"""
yosocal.com 1年分データ収集システム
修正版データ抽出ロジック使用
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

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriver（年間データ収集版）をセットアップ中...")
    
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
    chrome_options.add_argument("--headless")  # バックグラウンド実行
    
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

def extract_corrected_data(driver, year, month, date_num):
    """修正版データ抽出ロジック（ログ出力簡略化）"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return []
        
        # テーブルを探す
        table = jamat_div.find('table')
        if not table:
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 4:
            return []
        
        # 時間帯の定義
        time_slots = [
            "08:15", "08:45", "09:15", "09:45", "10:15", "10:45", "11:15", "11:45",
            "12:15", "12:45", "13:15", "13:45", "14:15", "14:45", "15:15", "15:45",
            "16:15", "16:45", "17:15", "17:45", "18:15", "18:45", "19:15", "19:45",
            "20:15", "20:45", "21:15", "21:45"
        ]
        
        # データ行とアトラクション行
        data_row = rows[2]
        data_cells = data_row.find_all(['td', 'th'])
        
        attraction_row = rows[3]
        attraction_cells = attraction_row.find_all(['td', 'th'])
        
        # 実際のデータセル（TIME, 天気・気温を除外）
        actual_data_cells = data_cells[2:]
        actual_attraction_cells = attraction_cells
        
        # アトラクション名を抽出
        attractions = []
        for cell in actual_attraction_cells:
            attraction_name = cell.get_text(strip=True).replace('\n', '').replace('<br>', '')
            attractions.append(attraction_name)
        
        extracted_data = []
        
        # データ抽出
        data_index = 0
        for time_idx, time_slot in enumerate(time_slots):
            for attr_idx, attraction in enumerate(attractions):
                if data_index < len(actual_data_cells):
                    cell = actual_data_cells[data_index]
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
                        status = 'normal'
                        wait_time = float(re.findall(r'\d+', cell_text)[0])
                    elif cell_text in ['C', 'B', 'A', 'S', 'G']:
                        status = 'congestion_level'
                        congestion_map = {'C': 5, 'B': 15, 'A': 30, 'S': 60, 'G': 90}
                        wait_time = congestion_map.get(cell_text, None)
                    else:
                        status = 'other'
                    
                    # データ記録
                    record = {
                        'date': f"{month}月{date_num:02d}日",
                        'year': year,
                        'month': month,
                        'day': date_num,
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yearly_collector_corrected'
                    }
                    extracted_data.append(record)
                    
                    data_index += 1
                else:
                    break
            
            if data_index >= len(actual_data_cells):
                break
        
        return extracted_data
        
    except Exception as e:
        return []

def click_date_and_get_data(driver, date_num, year, month):
    """日付をクリックしてデータ抽出"""
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
        data = extract_corrected_data(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def collect_yearly_data():
    """2024年1年分データ収集"""
    print("🚀 yosocal.com 2024年1年分データ収集システム")
    print("🔧 修正版データ抽出ロジック使用")
    print("📅 対象期間: 2024年1月1日 - 2024年12月31日")
    print("=" * 70)
    
    # 出力ファイル設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_2024_yearly_data_{timestamp}.csv"
    progress_file = f"yosocal_2024_progress_{timestamp}.json"
    
    # 進捗データの初期化
    progress_data = {
        'start_time': timestamp,
        'total_months': 12,
        'total_days': 0,
        'processed_days': 0,
        'total_records': 0,
        'valid_records': 0,
        'last_processed': None,
        'errors': []
    }
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # 月別処理
        months_data = [
            (1, 31), (2, 29), (3, 31), (4, 30), (5, 31), (6, 30),
            (7, 31), (8, 31), (9, 30), (10, 31), (11, 30), (12, 31)
        ]
        
        # 総日数計算
        total_days = sum(days for _, days in months_data)
        progress_data['total_days'] = total_days
        
        print(f"📋 処理対象: {len(months_data)}ヶ月, {total_days}日")
        
        # 月別進捗バー
        month_pbar = tqdm(months_data, desc="月処理", unit="月")
        
        for month, days_in_month in month_pbar:
            print(f"\n📅 2024年{month}月 処理開始 ({days_in_month}日)")
            
            month_data = []
            month_valid = 0
            
            # 日別進捗バー
            day_pbar = tqdm(range(1, days_in_month + 1), desc=f"2024/{month:02d}", leave=False, unit="日")
            
            for day in day_pbar:
                try:
                    data, status = click_date_and_get_data(driver, day, 2024, month)
                    
                    if data:
                        month_data.extend(data)
                        valid_count = len([d for d in data if d['wait_time'] is not None])
                        month_valid += valid_count
                        
                        day_pbar.set_postfix({
                            'データ': f"{len(data)}件",
                            '有効': f"{valid_count}件"
                        })
                    else:
                        progress_data['errors'].append({
                            'date': f"2024-{month:02d}-{day:02d}",
                            'error': status
                        })
                        day_pbar.set_postfix({'エラー': status[:20]})
                    
                    progress_data['processed_days'] += 1
                    progress_data['last_processed'] = f"2024-{month:02d}-{day:02d}"
                    
                    # 小休止
                    time.sleep(1)
                    
                except Exception as e:
                    error_msg = f"予期しないエラー: {str(e)[:50]}"
                    progress_data['errors'].append({
                        'date': f"2024-{month:02d}-{day:02d}",
                        'error': error_msg
                    })
                    day_pbar.set_postfix({'エラー': error_msg})
                    continue
            
            # 月データを全体に追加
            all_data.extend(month_data)
            progress_data['total_records'] = len(all_data)
            progress_data['valid_records'] = len([d for d in all_data if d['wait_time'] is not None])
            
            print(f"✅ 2024年{month}月完了")
            print(f"   📊 月データ: {len(month_data):,}件 (有効: {month_valid:,}件)")
            print(f"   📈 累計: {len(all_data):,}件 (有効: {progress_data['valid_records']:,}件)")
            
            # 月次進捗保存
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 月次中間保存
            if all_data:
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                                'status', 'css_classes', 'raw_value', 'data_source']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_data)
                print(f"💾 中間保存完了: {len(all_data):,}件")
        
        # 最終結果
        end_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress_data['end_time'] = end_time
        
        print(f"\n📊 最終処理結果:")
        print(f"   📅 処理月数: {len(months_data)}/12")
        print(f"   📅 処理日数: {progress_data['processed_days']}/{total_days}")
        print(f"   ✅ 成功率: {(progress_data['processed_days']-len(progress_data['errors']))/progress_data['processed_days']*100:.1f}%")
        print(f"   📈 総データ数: {len(all_data):,}件")
        print(f"   ✅ 有効データ: {progress_data['valid_records']:,}件")
        print(f"   📁 出力ファイル: {output_file}")
        
        # 統計情報
        if all_data:
            attractions = set(d['attraction'] for d in all_data)
            time_slots = set(d['time'] for d in all_data)
            valid_data = [d for d in all_data if d['wait_time'] is not None]
            
            print(f"\n📊 データ統計:")
            print(f"   🎢 アトラクション数: {len(attractions)}個")
            print(f"   ⏰ 時間帯数: {len(time_slots)}個")
            print(f"   📊 データ完全性: {progress_data['valid_records']/len(all_data)*100:.1f}%")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # ファイルサイズ計算
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   💾 ファイルサイズ: {file_size:.1f}MB")
        
        print(f"\n⚡ 2024年1年分データ収集完了！")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")
        
        # 最終進捗保存
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    collect_yearly_data() 