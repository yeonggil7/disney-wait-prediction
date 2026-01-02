# -*- coding: utf-8 -*-
"""
yosocal.com 2025年6月完全データ取得システム
カレンダークリック機能を使用した6月全日データ収集
"""

import time
import re
import csv
import os
from datetime import datetime
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

def get_all_june_dates(driver):
    """6月の全日付要素を取得"""
    print("\n📅 6月の日付要素を取得中...")
    
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # CAL関連要素を取得
        cal_patterns = [
            ("CALクラス", "//div[@class='CAL']"),
            ("CALSATクラス", "//div[@class='CALSAT']"),
            ("CALSUNクラス", "//div[@class='CALSUN']")
        ]
        
        date_elements = []
        
        for pattern_name, xpath in cal_patterns:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                print(f"   {pattern_name}: {len(elements)}個")
                
                for elem in elements:
                    text = elem.text.strip()
                    # 数字のみの日付を対象（6月の1-30日）
                    if text.isdigit() and 1 <= int(text) <= 30:
                        date_elements.append({
                            'element': elem,
                            'date': int(text),
                            'text': text,
                            'class': elem.get_attribute('class')
                        })
                        
            except Exception as e:
                print(f"   ❌ {pattern_name} 取得エラー: {e}")
        
        # 日付順にソート
        date_elements.sort(key=lambda x: x['date'])
        
        print(f"   ✅ {len(date_elements)}個の日付要素を発見")
        for elem in date_elements:
            print(f"     6月{elem['date']:2d}日 (class: {elem['class']})")
        
        return date_elements
        
    except Exception as e:
        print(f"❌ 日付要素取得エラー: {e}")
        return []

def click_date_and_get_data(driver, date_num):
    """指定日付をクリックして待機時間データを取得"""
    print(f"\n🖱️ 6月{date_num:02d}日のデータ取得中...")
    
    try:
        # メインページに戻る
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        # 日付要素を再取得
        date_elements = []
        cal_patterns = [
            "//div[@class='CAL']",
            "//div[@class='CALSAT']", 
            "//div[@class='CALSUN']"
        ]
        
        for xpath in cal_patterns:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                text = elem.text.strip()
                if text.isdigit() and int(text) == date_num:
                    date_elements.append(elem)
        
        if not date_elements:
            print(f"   ❌ {date_num}日の要素が見つかりません")
            return []
        
        # 最初に見つかった要素をクリック
        target_element = date_elements[0]
        print(f"   📅 6月{date_num:02d}日をクリック中...")
        driver.execute_script("arguments[0].click();", target_element)
        time.sleep(3)
        
        # realtime.htmに移動
        print(f"   📄 realtime.htmページにアクセス中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # データを解析
        data = extract_wait_time_data(driver, f"6月{date_num:02d}日")
        
        if data:
            print(f"   ✅ 6月{date_num:02d}日: {len(data)}件のデータを取得")
            return data
        else:
            print(f"   ❌ 6月{date_num:02d}日: データ取得に失敗")
            return []
            
    except Exception as e:
        print(f"   ❌ 6月{date_num:02d}日クリック・データ取得エラー: {e}")
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
    try:
        rows = table.find_all('tr')
        
        # アトラクション名を取得（FPh2クラス）
        attraction_row = None
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if len(fph2_cells) > 10:  # 十分な数のアトラクション名がある行
                attraction_row = row
                break
        
        if not attraction_row:
            print("     ❌ アトラクション名行が見つかりません")
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
                    'data_source': 'june_calendar_complete'
                }
                data_records.append(record)
        
        return data_records
        
    except Exception as e:
        print(f"     ❌ データ解析エラー: {e}")
        return []

def save_june_complete_data(all_data):
    """6月完全データを保存"""
    if not all_data:
        print("❌ 保存するデータがありません")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"yosocal_june_2025_complete_{timestamp}.csv"
    
    # データディレクトリを作成
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    # CSVに保存
    fieldnames = ['date', 'time', 'attraction', 'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"\n💾 6月完全データを保存: {filepath}")
    return filepath

def analyze_june_complete_data(all_data):
    """6月完全データの分析結果を表示"""
    if not all_data:
        return
    
    df = pd.DataFrame(all_data)
    
    print(f"\n📊 2025年6月完全データ分析結果:")
    print(f"   総レコード数: {len(df)}")
    print(f"   収集日数: {df['date'].nunique()}")
    print(f"   アトラクション数: {df['attraction'].nunique()}")
    print(f"   時間スロット数: {df['time'].nunique()}")
    print(f"   有効待機時間データ: {df[df['status'] == 'normal'].shape[0]}")
    
    # 日付別統計
    date_stats = df.groupby('date').size()
    print(f"\n📅 日付別レコード数:")
    for date, count in date_stats.items():
        print(f"     {date}: {count:,}件")
    
    # 状態別統計
    status_counts = df['status'].value_counts()
    print(f"\n📊 状態別統計: {status_counts.to_dict()}")
    
    # 人気アトラクション分析
    popular_attractions = df[df['status'] == 'normal'].groupby('attraction')['wait_time'].mean().sort_values(ascending=False).head(10)
    print(f"\n🎢 平均待機時間トップ10:")
    for attraction, avg_time in popular_attractions.items():
        print(f"     {attraction}: {avg_time:.1f}分")

def main():
    """メイン処理 - 2025年6月完全データ取得"""
    print("🎯 yosocal.com 2025年6月完全データ取得システム")
    print("=" * 60)
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # 利用可能な日付を確認
        available_dates = get_all_june_dates(driver)
        
        if not available_dates:
            print("❌ 利用可能な日付が見つかりません")
            return
        
        print(f"\n📅 6月の{len(available_dates)}日間のデータ取得を開始...")
        
        # 各日付のデータを取得
        for i, date_info in enumerate(tqdm(available_dates, desc="6月データ取得")):
            date_num = date_info['date']
            print(f"\n進行状況: {i+1}/{len(available_dates)} - 6月{date_num:02d}日")
            
            # 日付データを取得
            date_data = click_date_and_get_data(driver, date_num)
            
            if date_data:
                all_data.extend(date_data)
                print(f"   📊 累計データ数: {len(all_data):,}")
            
            # サーバー負荷軽減のため少し待機
            time.sleep(3)
        
        # データを保存
        if all_data:
            filepath = save_june_complete_data(all_data)
            analyze_june_complete_data(all_data)
            
            print(f"\n✅ 2025年6月完全データ取得完了！")
            print(f"💾 保存ファイル: {filepath}")
            print(f"📊 総データ数: {len(all_data):,}")
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