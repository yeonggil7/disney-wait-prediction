# -*- coding: utf-8 -*-
"""
yosocal.com 日付クリック→realtime.htm アプローチテスト
カレンダーで日付選択後にrealtime.htmでデータ取得
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

def get_cal_date_elements(driver):
    """CALクラスの日付要素を取得"""
    print("\n📅 CALクラス日付要素を取得中...")
    
    try:
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
                    # 数字のみの日付を対象
                    if text.isdigit() and 1 <= int(text) <= 31:
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
        for elem in date_elements[:10]:
            print(f"     {elem['date']:2d}日 (class: {elem['class']})")
        
        return date_elements
        
    except Exception as e:
        print(f"❌ 日付要素取得エラー: {e}")
        return []

def click_date_and_check_realtime(driver, date_element):
    """日付をクリックしてrealtime.htmでデータを確認"""
    date_num = date_element['date']
    print(f"\n🖱️ {date_num}日をクリックしてrealtime.htmチェック中...")
    
    try:
        # クリック前のURLを記録
        before_url = driver.current_url
        
        # 日付をクリック
        print(f"   📅 {date_num}日をクリック中...")
        driver.execute_script("arguments[0].click();", date_element['element'])
        time.sleep(3)
        
        # URLの変化を確認
        after_url = driver.current_url
        print(f"   URL変化: {before_url} → {after_url}")
        
        # realtime.htmに移動
        print(f"   📄 realtime.htmページにアクセス中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # データを解析
        data = extract_wait_time_data(driver, f"6月{date_num:02d}日")
        
        if data:
            print(f"   ✅ {date_num}日: {len(data)}件のデータを取得")
            return data
        else:
            print(f"   ❌ {date_num}日: データ取得に失敗")
            return []
            
    except Exception as e:
        print(f"   ❌ {date_num}日クリック・データ取得エラー: {e}")
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
        
        print(f"     📊 {len(attractions)}個のアトラクションを発見")
        
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
                    'data_source': 'calendar_click_realtime'
                }
                data_records.append(record)
        
        return data_records
        
    except Exception as e:
        print(f"     ❌ データ解析エラー: {e}")
        return []

def try_direct_url_approach(driver):
    """URLパラメータで直接6月を指定するアプローチをテスト"""
    print("\n🔍 URLパラメータでの6月アクセステスト")
    print("=" * 50)
    
    # 可能性のあるURLパターンをテスト
    url_patterns = [
        "https://yosocal.com/?month=6",
        "https://yosocal.com/?month=2025-06",
        "https://yosocal.com/?year=2025&month=6",
        "https://yosocal.com/index.htm?month=6",
        "https://yosocal.com/?m=6",
        "https://yosocal.com/?date=2025-06",
        "https://yosocal.com/calendar.htm?month=6"
    ]
    
    for url in url_patterns:
        try:
            print(f"   🌐 テスト: {url}")
            driver.get(url)
            time.sleep(3)
            
            # 6月になったかチェック
            month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2025年') and contains(text(), '月')]")
            if month_elements:
                current_month = month_elements[0].text
                print(f"     結果: {current_month}")
                
                if "6月" in current_month:
                    print(f"   ✅ {url} で6月に到達！")
                    return True
            else:
                print(f"     年月表示が見つかりません")
                
        except Exception as e:
            print(f"   ❌ {url} テストエラー: {e}")
    
    return False

def test_june_data_collection(driver):
    """6月のデータ収集をテスト"""
    print("\n🎯 6月データ収集テスト")
    print("=" * 50)
    
    all_data = []
    
    try:
        # メインページに戻る
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # URLパラメータで6月を試行
        june_accessed = try_direct_url_approach(driver)
        
        if not june_accessed:
            print("   URLパラメータでの6月アクセスに失敗、現在の月でテスト中...")
            driver.get('https://yosocal.com/')
            time.sleep(3)
        
        # 日付要素を取得
        date_elements = get_cal_date_elements(driver)
        
        if not date_elements:
            print("   ❌ 日付要素が見つかりません")
            return []
        
        # 最初の3つの日付でテスト
        test_dates = date_elements[:3]
        print(f"\n   📅 {len(test_dates)}個の日付でテスト実行...")
        
        for i, date_element in enumerate(test_dates):
            print(f"\n   進行状況: {i+1}/{len(test_dates)}")
            
            # メインページに戻る
            driver.get('https://yosocal.com/')
            time.sleep(2)
            
            # 同じ日付要素を再取得（ページ再読み込み後）
            fresh_date_elements = get_cal_date_elements(driver)
            matching_element = next((elem for elem in fresh_date_elements if elem['date'] == date_element['date']), None)
            
            if matching_element:
                # 日付をクリックしてデータ取得
                date_data = click_date_and_check_realtime(driver, matching_element)
                
                if date_data:
                    all_data.extend(date_data)
                    print(f"     📊 累計データ数: {len(all_data)}")
            
            # サーバー負荷軽減のため少し待機
            time.sleep(2)
        
        return all_data
        
    except Exception as e:
        print(f"❌ 6月データ収集テストエラー: {e}")
        return []

def save_test_data(all_data):
    """テストデータを保存"""
    if not all_data:
        print("❌ 保存するデータがありません")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"yosocal_calendar_test_data_{timestamp}.csv"
    
    # データディレクトリを作成
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    # CSVに保存
    fieldnames = ['date', 'time', 'attraction', 'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"💾 テストデータを保存: {filepath}")
    print(f"📊 総データ数: {len(all_data)}")

def main():
    """メインテストプロセス"""
    print("🎯 yosocal.com 日付クリック→realtime.htm アプローチテスト")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # 6月データ収集をテスト
        test_data = test_june_data_collection(driver)
        
        # データを保存
        save_test_data(test_data)
        
        if test_data:
            print(f"\n✅ テスト成功！{len(test_data)}件のデータを取得")
        else:
            print(f"\n❌ テスト失敗：データを取得できませんでした")
        
        print("\n✅ 日付クリック→realtime.htmアプローチテスト完了")
        
    except Exception as e:
        print(f"❌ テストプロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 