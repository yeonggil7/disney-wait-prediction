# -*- coding: utf-8 -*-
"""
yosocal.com 2025年6月データ取得システム
カレンダー機能を使用して6月の全日データを収集
"""

import time
import re
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ WebDriverセットアップ完了")
    return driver

def navigate_to_month(driver, year, month):
    """指定の年月に移動"""
    print(f"📅 {year}年{month}月に移動中...")
    
    max_attempts = 12
    for attempt in range(max_attempts):
        try:
            # 現在表示されている年月を確認
            month_element = driver.find_element(By.XPATH, "//td[@class='MHDT']")
            current_display = month_element.text
            
            target_text = f"{year}年{month:02d}月"
            print(f"   現在表示: {current_display}, 目標: {target_text}")
            
            if target_text in current_display or f"{year}年{month}月" in current_display:
                print(f"   ✅ 目標の {target_text} に到達")
                return True
            
            # 現在の年月を解析
            current_match = re.search(r'(\d{4})年(\d{1,2})月', current_display)
            if current_match:
                current_year = int(current_match.group(1))
                current_month = int(current_match.group(2))
                
                # 目標より前か後かを判定
                if (current_year, current_month) > (year, month):
                    # 前月に移動
                    prev_button = driver.find_element(By.XPATH, "//td[@class='MHBT'][1]/a")
                    prev_button.click()
                    print(f"   ← 前月に移動")
                else:
                    # 次月に移動
                    next_button = driver.find_element(By.XPATH, "//td[@class='MHBT'][2]/a")
                    next_button.click()
                    print(f"   → 次月に移動")
                
                time.sleep(2)
            else:
                print(f"   ❌ 現在の年月を解析できません: {current_display}")
                break
        
        except Exception as e:
            print(f"   ❌ 月移動エラー: {e}")
            break
    
    print(f"   ❌ {max_attempts}回試行後も目標月に到達できませんでした")
    return False

def get_available_dates(driver):
    """利用可能な日付を取得"""
    print("📋 利用可能な日付を取得中...")
    
    try:
        # cal + 数字のIDを持つ要素を取得
        date_elements = driver.find_elements(By.XPATH, "//td[starts-with(@id, 'cal') and string-length(@id) > 3]")
        
        available_dates = []
        for element in date_elements:
            date_id = element.get_attribute('id')
            date_text = element.text.strip()
            
            # 数字のみの日付をフィルタ
            if date_text.isdigit():
                available_dates.append({
                    'id': date_id,
                    'date': int(date_text),
                    'element': element
                })
        
        available_dates.sort(key=lambda x: x['date'])
        print(f"   ✅ {len(available_dates)} 個の日付を発見")
        
        return available_dates
    
    except Exception as e:
        print(f"   ❌ 日付取得エラー: {e}")
        return []

def click_date_and_get_data(driver, date_info, target_month=6):
    """日付をクリックして待機時間データを取得"""
    date_id = date_info['id']
    date_num = date_info['date']
    date_str = f"6月{date_num:02d}日"
    
    print(f"🖱️ {date_str} ({date_id}) をクリック中...")
    
    try:
        # 日付をクリック
        element = date_info['element']
        driver.execute_script("arguments[0].click();", element)
        time.sleep(3)
        
        # クリック後にrealtime.htmページにアクセス
        print(f"   📄 realtime.htmページにアクセス中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # データを取得
        data_records = extract_wait_time_data(driver, date_str)
        
        if data_records:
            print(f"   ✅ {date_str}: {len(data_records)} 件のデータを取得")
        else:
            print(f"   ❌ {date_str}: データの取得に失敗")
        
        # メインページに戻る
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        # 2025年6月に再移動
        navigate_to_month(driver, 2025, 6)
        time.sleep(1)
        
        return data_records
    
    except Exception as e:
        print(f"   ❌ {date_str} データ取得エラー: {e}")
        return []

def extract_wait_time_data(driver, date_str):
    """realtime.htmページから待機時間データを抽出"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを取得
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("     ❌ jamat divが見つかりません")
            return []
        
        # テーブルを取得
        table = jamat_div.find('table')
        if not table:
            print("     ❌ jamat div内にテーブルが見つかりません")
            return []
        
        return parse_wait_time_data(table, date_str)
    
    except Exception as e:
        print(f"     ❌ データ抽出エラー: {e}")
        return []

def parse_wait_time_data(table, date_str):
    """待機時間データテーブルを解析"""
    rows = table.find_all('tr')
    
    # アトラクション名を取得（FPh2クラス）
    attraction_row = None
    for row in rows:
        fph2_cells = row.find_all('td', class_='FPh2')
        if len(fph2_cells) > 10:  # 十分な数のアトラクション名がある行
            attraction_row = row
            break
    
    if not attraction_row:
        return []
    
    # アトラクション名を抽出
    attraction_cells = attraction_row.find_all('td', class_='FPh2')
    attractions = []
    for cell in attraction_cells:
        text = cell.get_text(strip=True).replace('｜', '')
        if text:
            attractions.append(text)
    
    # 時間行を特定してデータを抽出
    data_records = []
    
    for row in rows:
        time_cell = row.find('td', class_='FPM')
        if not time_cell:
            continue
        
        time_text = time_cell.get_text(strip=True)
        if not time_text or time_text == "　":
            continue
        
        # 天気セルが存在するかチェック（rowspanの影響で調整が必要）
        all_cells = row.find_all('td')
        
        # 天気セル（rowspan）の存在を確認
        weather_cell_exists = any(
            cell.find('img') and 'title="天気"' in str(cell) 
            for cell in all_cells
        )
        
        # データセルの開始インデックスを決定
        data_start_index = 2 if weather_cell_exists else 1
        
        # データセルを抽出
        data_cells = all_cells[data_start_index:]
        
        # 各アトラクションのデータを処理
        for i, cell in enumerate(data_cells):
            if i >= len(attractions):
                break
            
            attraction = attractions[i]
            
            # セルのクラスと内容を取得
            css_classes = cell.get('class', [])
            raw_value = cell.get_text(strip=True)
            
            # データの状態と値を判定
            if raw_value == "-" or raw_value == "":
                status = "no_data"
                wait_time = None
            elif raw_value.isdigit():
                status = "normal"
                wait_time = float(raw_value)
            else:
                status = "empty"
                wait_time = None
            
            # レコードを追加
            record = {
                'date': date_str,
                'time': time_text,
                'attraction': attraction,
                'wait_time': wait_time,
                'status': status,
                'css_classes': ' '.join(css_classes),
                'raw_value': raw_value,
                'data_source': 'calendar_realtime'
            }
            data_records.append(record)
    
    return data_records

def save_june_data(all_data, filename=None):
    """6月のデータをCSVファイルに保存"""
    if not all_data:
        print("❌ 保存するデータがありません")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"yosocal_june_2025_data_{timestamp}.csv"
    
    # データディレクトリを作成
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    # CSVに保存
    fieldnames = ['date', 'time', 'attraction', 'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"💾 6月データを保存: {filepath}")
    return filepath

def analyze_june_data(all_data):
    """6月データの分析結果を表示"""
    if not all_data:
        return
    
    df = pd.DataFrame(all_data)
    
    print(f"\n📊 2025年6月データ分析結果:")
    print(f"   総レコード数: {len(df)}")
    print(f"   収集日数: {df['date'].nunique()}")
    print(f"   アトラクション数: {df['attraction'].nunique()}")
    print(f"   時間スロット数: {df['time'].nunique()}")
    print(f"   有効待機時間データ: {df[df['status'] == 'normal'].shape[0]}")
    
    # 日付別統計
    date_stats = df.groupby('date').size()
    print(f"   日付別レコード数: {date_stats.to_dict()}")
    
    # 状態別統計
    status_counts = df['status'].value_counts()
    print(f"   状態別統計: {status_counts.to_dict()}")

def main():
    """メイン処理 - 2025年6月データ取得"""
    print("🎯 yosocal.com 2025年6月データ取得システム")
    print("=" * 60)
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # メインページにアクセス
        print("🌐 yosocal.comメインページにアクセス中...")
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # 2025年6月に移動
        if not navigate_to_month(driver, 2025, 6):
            print("❌ 2025年6月への移動に失敗しました")
            return
        
        # 利用可能な日付を取得
        available_dates = get_available_dates(driver)
        if not available_dates:
            print("❌ 利用可能な日付が見つかりません")
            return
        
        print(f"📅 2025年6月の{len(available_dates)}日間のデータを取得開始...")
        
        # 各日付のデータを取得
        for i, date_info in enumerate(tqdm(available_dates, desc="日付データ取得")):
            print(f"\n進行状況: {i+1}/{len(available_dates)}")
            
            # 日付データを取得
            date_data = click_date_and_get_data(driver, date_info)
            
            if date_data:
                all_data.extend(date_data)
                print(f"   📊 累計データ数: {len(all_data)}")
            
            # 少し待機（サーバー負荷軽減）
            time.sleep(2)
        
        # データを保存
        if all_data:
            filepath = save_june_data(all_data)
            analyze_june_data(all_data)
            
            print(f"\n✅ 2025年6月データ取得完了！")
            print(f"💾 保存ファイル: {filepath}")
            print(f"📊 総データ数: {len(all_data)}")
        else:
            print("\n❌ 取得できたデータがありません")
    
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 