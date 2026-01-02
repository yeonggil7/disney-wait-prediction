# -*- coding: utf-8 -*-
"""
yosocal.com 2024年1月テスト版データ収集システム
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
import re
from tqdm import tqdm

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriver（1月テスト版）をセットアップ中...")
    
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

def extract_corrected_data(driver, year, month, date_num):
    """修正版データ抽出ロジック"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print(f"   ❌ jamat div が見つかりません")
            return []
        
        # テーブルを探す
        table = jamat_div.find('table')
        if not table:
            print(f"   ❌ テーブルが見つかりません")
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 4:
            print(f"   ❌ 行数不足: {len(rows)}行")
            return []
        
        print(f"   ✅ テーブル検出: {len(rows)}行")
        
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
        
        print(f"   📊 データセル数: {len(data_cells)}")
        print(f"   🎢 アトラクションセル数: {len(attraction_cells)}")
        
        # 実際のデータセル（TIME, 天気・気温を除外）
        actual_data_cells = data_cells[2:]
        actual_attraction_cells = attraction_cells
        
        # アトラクション名を抽出
        attractions = []
        for cell in actual_attraction_cells:
            attraction_name = cell.get_text(strip=True).replace('\n', '').replace('<br>', '')
            if attraction_name:  # 空文字列を除外
                attractions.append(attraction_name)
        
        print(f"   🎯 抽出アトラクション数: {len(attractions)}")
        if len(attractions) > 0:
            print(f"   🎢 アトラクション例: {attractions[:3]}")
        
        extracted_data = []
        
        # データ抽出
        data_index = 0
        valid_count = 0
        
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
                        valid_count += 1
                    elif re.match(r'^\d+分?$', cell_text):
                        status = 'normal'
                        wait_time = float(re.findall(r'\d+', cell_text)[0])
                        valid_count += 1
                    elif cell_text in ['C', 'B', 'A', 'S', 'G']:
                        status = 'congestion_level'
                        congestion_map = {'C': 5, 'B': 15, 'A': 30, 'S': 60, 'G': 90}
                        wait_time = congestion_map.get(cell_text, None)
                        valid_count += 1
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
                        'data_source': 'january_test_corrected'
                    }
                    extracted_data.append(record)
                    
                    data_index += 1
                else:
                    break
            
            if data_index >= len(actual_data_cells):
                break
        
        print(f"   📈 抽出データ: {len(extracted_data)}件 (有効: {valid_count}件)")
        return extracted_data
        
    except Exception as e:
        print(f"   ❌ データ抽出エラー: {e}")
        return []

def click_date_and_get_data(driver, date_num, year, month):
    """日付をクリックしてデータ抽出"""
    try:
        print(f"📅 {year}年{month}月{date_num}日 処理開始")
        
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
                print(f"   ✅ 日付クリック成功: {xpath}")
                break
        
        if not date_element:
            return [], f"日付{date_num}が見つかりません"
        
        time.sleep(2)
        
        # realtime.htmに移動してデータ抽出
        print(f"   🌐 realtime.htmに移動中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(4)
        
        # 修正版データ抽出
        data = extract_corrected_data(driver, year, month, date_num)
        
        print(f"   ✅ {year}年{month}月{date_num}日 完了: {len(data)}件")
        return data, "成功"
        
    except Exception as e:
        print(f"   ❌ {year}年{month}月{date_num}日 エラー: {e}")
        return [], f"エラー: {e}"

def test_january_2024():
    """2024年1月テスト"""
    print("🚀 yosocal.com 2024年1月テスト版データ収集")
    print("🔧 修正版データ抽出ロジック使用")
    print("📅 対象期間: 2024年1月1日 - 1月31日")
    print("=" * 60)
    
    # 出力ファイル設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_january_2024_test_{timestamp}.csv"
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # 1月の日数
        days_in_january = 31
        
        print(f"📋 処理対象: 1ヶ月, {days_in_january}日")
        
        # 日別進捗バー
        day_pbar = tqdm(range(1, days_in_january + 1), desc="2024/01", unit="日")
        
        for day in day_pbar:
            data, status = click_date_and_get_data(driver, day, 2024, 1)
            
            if data:
                all_data.extend(data)
                valid_count = len([d for d in data if d['wait_time'] is not None])
                
                day_pbar.set_postfix({
                    'データ': f"{len(data)}件",
                    '有効': f"{valid_count}件",
                    '累計': f"{len(all_data)}件"
                })
            else:
                day_pbar.set_postfix({'エラー': status[:30]})
            
            # 小休止
            time.sleep(1)
        
        # 結果保存
        if all_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_data)
        
        # 最終結果
        valid_data = [d for d in all_data if d['wait_time'] is not None]
        
        print(f"\n📊 1月テスト結果:")
        print(f"   📅 処理日数: {days_in_january}日")
        print(f"   📈 総データ数: {len(all_data):,}件")
        print(f"   ✅ 有効データ: {len(valid_data):,}件")
        print(f"   📁 出力ファイル: {output_file}")
        
        # 統計情報
        if all_data:
            attractions = set(d['attraction'] for d in all_data)
            time_slots = set(d['time'] for d in all_data)
            
            print(f"\n📊 データ統計:")
            print(f"   🎢 アトラクション数: {len(attractions)}個")
            print(f"   ⏰ 時間帯数: {len(time_slots)}個")
            print(f"   📊 データ完全性: {len(valid_data)/len(all_data)*100:.1f}%")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # ファイルサイズ計算
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            print(f"   💾 ファイルサイズ: {file_size:.2f}MB")
            
            # サンプルデータ表示
            print(f"\n📝 サンプルデータ:")
            for i, record in enumerate(all_data[:5]):
                print(f"   {i+1}. {record['date']} {record['time']} {record['attraction']}: {record['wait_time']}分 ({record['status']})")
        
        print(f"\n⚡ 1月テスト完了！")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    test_january_2024() 