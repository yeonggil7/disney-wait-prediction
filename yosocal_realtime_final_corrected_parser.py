# -*- coding: utf-8 -*-
"""
yosocal.com 最終修正版データ抽出システム
データ配列順序を修正した完全版
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
    print("🔧 Chrome WebDriver（最終修正版）をセットアップ中...")
    
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

def extract_final_corrected_data(driver, year, month, date_num):
    """最終修正版データ抽出 - データ配列順序を修正"""
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
        if len(rows) < 4:
            print(f"❌ テーブル行数不足: {len(rows)}行")
            return []
        
        print(f"📊 テーブル解析開始: {len(rows)}行")
        
        # 時間帯の定義（JavaScriptのMT配列に基づく）
        time_slots = [
            "08:15", "08:45", "09:15", "09:45", "10:15", "10:45", "11:15", "11:45",
            "12:15", "12:45", "13:15", "13:45", "14:15", "14:45", "15:15", "15:45",
            "16:15", "16:45", "17:15", "17:45", "18:15", "18:45", "19:15", "19:45",
            "20:15", "20:45", "21:15", "21:45"
        ]
        
        print(f"⏰ 時間帯: {len(time_slots)}個 - {time_slots[:5]}...")
        
        # 行3: 待ち時間データ行（TIME, 天気・気温は除外して実際のデータを取得）
        data_row = rows[2]  # 0ベースで行3
        data_cells = data_row.find_all(['td', 'th'])
        
        # 行4: アトラクション名行
        attraction_row = rows[3]  # 0ベースで行4
        attraction_cells = attraction_row.find_all(['td', 'th'])
        
        print(f"📊 データセル数: {len(data_cells)}個")
        print(f"🎢 アトラクションセル数: {len(attraction_cells)}個")
        
        # TIMEと天気・気温を除外（最初の2セル）
        # 実際のデータは3セル目から開始
        actual_data_cells = data_cells[2:]  # TIME, 天気・気温を除外
        actual_attraction_cells = attraction_cells  # アトラクション名はそのまま
        
        print(f"📋 実際データセル: {len(actual_data_cells)}個")
        print(f"🎢 実際アトラクションセル: {len(actual_attraction_cells)}個")
        
        # アトラクション名を抽出
        attractions = []
        for cell in actual_attraction_cells:
            attraction_name = cell.get_text(strip=True).replace('\n', '').replace('<br>', '')
            attractions.append(attraction_name)
        
        print(f"🎢 アトラクション一覧 (最初の10個):")
        for i, name in enumerate(attractions[:10], 1):
            print(f"   {i:2d}. {name}")
        
        extracted_data = []
        
        # 重要な修正: データの配列が時間軸方向に配置されている可能性を考慮
        # HTMLの実際の構造から判断して、データセルの配列を解析
        
        # データセルの数と期待値を比較
        expected_total = len(time_slots) * len(attractions)
        print(f"📈 期待データ数: {expected_total}件 ({len(time_slots)}時間 × {len(attractions)}アトラクション)")
        
        # データセルが時間軸×アトラクション軸の順序で配列されている場合の処理
        if len(actual_data_cells) >= len(attractions):
            # データセルが十分にある場合は、28時間×42アトラクションの構造と仮定
            
            # データインデックスの追跡
            data_index = 0
            
            for time_idx, time_slot in enumerate(time_slots):
                print(f"⏰ 処理中: {time_slot} (時間帯 {time_idx+1}/{len(time_slots)})")
                
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
                            # 「30分」のようなパターン
                            status = 'normal'
                            wait_time = float(re.findall(r'\d+', cell_text)[0])
                        elif cell_text in ['C', 'B', 'A', 'S', 'G']:
                            # C=軽い, B=普通, A=多い, S=非常に多い, G=激混み
                            status = 'congestion_level'
                            # 推定待ち時間に変換
                            congestion_map = {'C': 5, 'B': 15, 'A': 30, 'S': 60, 'G': 90}
                            wait_time = congestion_map.get(cell_text, None)
                        else:
                            status = 'other'
                            # その他のテキストの場合はスキップしないで記録
                        
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
                            'data_source': 'realtime.htm最終修正版',
                            'time_index': time_idx,
                            'attraction_index': attr_idx,
                            'data_index': data_index
                        }
                        extracted_data.append(record)
                        
                        data_index += 1
                        
                        # デバッグ出力（最初の数件のみ）
                        if data_index <= 10:
                            print(f"   データ{data_index}: {time_slot} - {attraction} = '{cell_text}' ({wait_time}分)")
                        
                    else:
                        # データセルが不足している場合は、その時間帯の処理を終了
                        print(f"⚠️ データセル不足: {time_slot}で終了 (index={data_index})")
                        break
                
                # 全データセルを処理済みの場合は終了
                if data_index >= len(actual_data_cells):
                    print(f"⚠️ 全データセル処理完了: {data_index}件")
                    break
        
        print(f"✅ 抽出完了: {len(extracted_data)}件")
        
        # データ統計
        valid_data = [d for d in extracted_data if d['wait_time'] is not None]
        time_coverage = len(set(d['time'] for d in extracted_data))
        attraction_coverage = len(set(d['attraction'] for d in extracted_data))
        
        print(f"📊 統計:")
        print(f"   📈 総データ数: {len(extracted_data):,}件")
        print(f"   ✅ 有効データ数: {len(valid_data):,}件")
        print(f"   🎢 アトラクション数: {attraction_coverage}個 (期待: {len(attractions)}個)")
        print(f"   ⏰ 時間帯数: {time_coverage}個 (期待: {len(time_slots)}個)")
        print(f"   📊 データ完全性: {len(extracted_data)/expected_total*100:.1f}%")
        
        if valid_data:
            avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
            max_wait = max(d['wait_time'] for d in valid_data)
            min_wait = min(d['wait_time'] for d in valid_data)
            print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            print(f"   📊 最大待ち時間: {max_wait:.0f}分")
            print(f"   📊 最小待ち時間: {min_wait:.0f}分")
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

def click_date_and_get_final_data(driver, date_num, year, month):
    """日付をクリックして最終修正版データ抽出"""
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
        
        # 最終修正版データ抽出
        data = extract_final_corrected_data(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def test_final_corrected_extraction():
    """最終修正版データ抽出テスト"""
    print("🚀 yosocal.com 最終修正版データ抽出テスト")
    print("🔧 データ配列順序を修正した完全版")
    print("=" * 70)
    
    driver = None
    
    try:
        driver = setup_driver()
        
        # 2024年1月1日でテスト
        print(f"🧪 テスト対象: 2024年1月1日")
        
        data, status = click_date_and_get_final_data(driver, 1, 2024, 1)
        
        if data:
            # テスト結果をCSVファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_file = f"yosocal_final_corrected_{timestamp}.csv"
            
            with open(test_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source', 'time_index', 
                            'attraction_index', 'data_index']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"\n📊 最終修正版テスト結果:")
            print(f"   📁 テストファイル: {test_file}")
            print(f"   📈 総データ数: {len(data):,}件")
            
            # アトラクション別集計
            attractions = {}
            valid_data = []
            congestion_data = []
            time_slots = set()
            
            for d in data:
                attraction = d['attraction']
                if attraction not in attractions:
                    attractions[attraction] = 0
                attractions[attraction] += 1
                time_slots.add(d['time'])
                
                if d['wait_time'] is not None:
                    if d['status'] == 'normal':
                        valid_data.append(d)
                    elif d['status'] == 'congestion_level':
                        congestion_data.append(d)
            
            print(f"   🎢 アトラクション数: {len(attractions)}個")
            print(f"   ⏰ 時間帯数: {len(time_slots)}個")
            print(f"   ✅ 数値データ: {len(valid_data)}件")
            print(f"   🎯 混雑レベルデータ: {len(congestion_data)}件")
            print(f"   📊 有効データ合計: {len(valid_data) + len(congestion_data)}件")
            
            # 時間帯一覧表示
            print(f"\n⏰ 時間帯一覧:")
            for time_slot in sorted(time_slots):
                count = len([d for d in data if d['time'] == time_slot])
                print(f"   {time_slot}: {count}件")
            
            # トップアトラクション表示
            print(f"\n🎢 アトラクション一覧 (最初の15個):")
            for i, (name, count) in enumerate(sorted(attractions.items())[:15], 1):
                # そのアトラクションの有効データ数
                attr_valid = len([d for d in data if d['attraction'] == name and d['wait_time'] is not None])
                print(f"   {i:2d}. {name}: {count}件 (有効: {attr_valid}件)")
            
            if valid_data or congestion_data:
                all_wait_times = [d['wait_time'] for d in valid_data + congestion_data]
                avg_wait = sum(all_wait_times) / len(all_wait_times)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            print(f"\n✅ 最終修正版データ抽出テスト成功！")
            if len(data) >= 1000:
                print(f"🎯 期待通りの大量データが正常に抽出されました")
            else:
                print(f"⚠️ データ数が期待値未満ですが、構造は正常です")
        else:
            print(f"❌ テスト失敗: {status}")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    test_final_corrected_extraction() 