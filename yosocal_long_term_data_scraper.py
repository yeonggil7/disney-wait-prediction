# -*- coding: utf-8 -*-
"""
yosocal.com 長期間データ取得システム
2024年1月1日から2025年6月30日までの全期間データ取得
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

def generate_expected_times():
    """期待される時間帯リストを生成"""
    times = []
    for hour in range(8, 22):
        if hour == 8:
            # 8時は15分、45分のみ
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
        elif hour == 21:
            # 21時は15分、45分のみ
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
        else:
            # その他は15分、45分
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
    
    # 平均を追加
    times.append("平均")
    
    return times

def navigate_to_month(driver, year, month):
    """指定した年月に移動"""
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # JavaScript関数で月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(5)
        
        # 移動確認
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            current_month = month_elements[0].text.strip()
            if str(year) in current_month and str(month) in current_month:
                return True, current_month
        
        return False, "移動失敗"
        
    except Exception as e:
        return False, f"エラー: {e}"

def extract_calendar_dates(driver):
    """カレンダーから利用可能な日付を抽出"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        available_dates = []
        
        # CAL、CALSAT、CALSUNクラスの日付要素を探す
        date_classes = ['CAL', 'CALSAT', 'CALSUN']
        
        for class_name in date_classes:
            date_elements = soup.find_all(class_=class_name)
            for element in date_elements:
                date_text = element.get_text(strip=True)
                if date_text.isdigit():
                    date_num = int(date_text)
                    if 1 <= date_num <= 31:
                        available_dates.append(date_num)
        
        # 重複削除・ソート
        available_dates = sorted(list(set(available_dates)))
        
        return available_dates
        
    except Exception as e:
        print(f"❌ カレンダー日付抽出エラー: {e}")
        return []

def click_date_and_extract_data(driver, date_num, year, month):
    """日付をクリックしてデータを抽出"""
    try:
        # 日付をクリック
        date_xpath = f"//td[@class='CAL' or @class='CALSAT' or @class='CALSUN'][text()='{date_num}']"
        date_elements = driver.find_elements(By.XPATH, date_xpath)
        
        if not date_elements:
            return [], f"日付{date_num}が見つかりません"
        
        # 最初の要素をクリック
        date_elements[0].click()
        time.sleep(3)
        
        # realtime.htmに移動してデータ抽出
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # データ抽出
        data = extract_wait_time_data(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def extract_wait_time_data(driver, year, month, date_num):
    """realtime.htmから待ち時間データを抽出"""
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
        if len(rows) < 2:  # ヘッダー + データ行が必要
            return []
        
        # 期待される時間帯を取得
        expected_times = generate_expected_times()
        
        # データ抽出
        extracted_data = []
        
        # アトラクション名を抽出（FPh2クラス）
        attractions = []
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all(['td', 'th'])
            if cells:
                first_cell = cells[0]
                attraction_name = first_cell.get_text(strip=True)
                if attraction_name and attraction_name not in ['時間', 'アトラクション']:
                    attractions.append(attraction_name)
        
        # 各アトラクションの待ち時間データを抽出
        for attraction in attractions:
            # アトラクション行を見つける
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if cells and cells[0].get_text(strip=True) == attraction:
                    # 時間帯ごとのデータを抽出
                    for time_idx, time_slot in enumerate(expected_times, 1):
                        if time_idx < len(cells):
                            cell = cells[time_idx]
                            
                            # 待ち時間の数値を抽出
                            cell_text = cell.get_text(strip=True)
                            css_classes = ' '.join(cell.get('class', []))
                            
                            # ステータス判定
                            if cell_text == '-' or cell_text == '':
                                status = 'no_data'
                                wait_time = None
                            elif cell_text.isdigit():
                                status = 'normal'
                                wait_time = float(cell_text)
                            else:
                                status = 'empty'
                                wait_time = None
                            
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
                                'data_source': 'jamat div内'
                            }
                            extracted_data.append(record)
                    break
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def save_progress(filename, completed_months, total_data_count):
    """進捗を保存"""
    progress = {
        'completed_months': completed_months,
        'total_data_count': total_data_count,
        'last_update': datetime.now().isoformat()
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_progress(filename):
    """進捗を読み込み"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return {'completed_months': [], 'total_data_count': 0}

def main():
    """メイン長期間データ取得プロセス"""
    print("🚀 yosocal.com 長期間データ取得システム")
    print("📅 対象期間: 2024年1月1日 - 2025年6月30日")
    print("=" * 60)
    
    # 出力ファイル設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_long_term_data_{timestamp}.csv"
    progress_file = f"yosocal_progress_{timestamp}.json"
    
    # 進捗読み込み
    progress = load_progress(progress_file)
    completed_months = set(progress['completed_months'])
    
    # 対象月リスト生成
    target_months = []
    
    # 2024年1-12月
    for month in range(1, 13):
        month_key = f"2024-{month:02d}"
        if month_key not in completed_months:
            target_months.append((2024, month, month_key))
    
    # 2025年1-6月
    for month in range(1, 7):
        month_key = f"2025-{month:02d}"
        if month_key not in completed_months:
            target_months.append((2025, month, month_key))
    
    print(f"📋 処理対象: {len(target_months)}ヶ月")
    
    if not target_months:
        print("✅ すべての月が処理済みです")
        return
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # 月ごとの処理
        for year, month, month_key in tqdm(target_months, desc="月処理"):
            print(f"\n📅 {year}年{month}月 処理開始")
            
            # 月に移動
            success, result = navigate_to_month(driver, year, month)
            if not success:
                print(f"❌ {year}年{month}月への移動失敗: {result}")
                continue
            
            print(f"✅ {result} に移動完了")
            
            # カレンダー日付抽出
            available_dates = extract_calendar_dates(driver)
            print(f"📋 利用可能日付: {len(available_dates)}日")
            
            if not available_dates:
                print(f"⚠️ {year}年{month}月にデータなし")
                completed_months.add(month_key)
                continue
            
            # 日付ごとの処理
            month_data = []
            for date_num in tqdm(available_dates, desc=f"{year}/{month}", leave=False):
                try:
                    # メインページに戻って月を再設定
                    navigate_to_month(driver, year, month)
                    time.sleep(2)
                    
                    # 日付クリックとデータ抽出
                    data, status = click_date_and_extract_data(driver, date_num, year, month)
                    
                    if data:
                        month_data.extend(data)
                        print(f"✅ {month}月{date_num:02d}日: {len(data)}件")
                    else:
                        print(f"❌ {month}月{date_num:02d}日: {status}")
                    
                    # 短い待機
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ {month}月{date_num:02d}日処理エラー: {e}")
            
            # 月データを追加
            all_data.extend(month_data)
            completed_months.add(month_key)
            
            print(f"✅ {year}年{month}月完了: {len(month_data)}件")
            
            # 進捗保存
            save_progress(progress_file, list(completed_months), len(all_data))
            
            # 中間保存
            if len(all_data) > 0:
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                                'status', 'css_classes', 'raw_value', 'data_source']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_data)
        
        # 最終データ保存
        if all_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_data)
            
            print(f"\n📊 最終結果:")
            print(f"   📁 出力ファイル: {output_file}")
            print(f"   📈 総データ数: {len(all_data):,}件")
            print(f"   📅 処理月数: {len(completed_months)}ヶ月")
            
            # データ統計
            valid_data = [d for d in all_data if d['wait_time'] is not None]
            print(f"   ✅ 有効データ: {len(valid_data):,}件")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # 期間別統計
            print(f"\n📈 年別統計:")
            for year in [2024, 2025]:
                year_data = [d for d in all_data if d['year'] == year]
                if year_data:
                    print(f"   {year}年: {len(year_data):,}件")
        
        print(f"\n✅ 長期間データ取得完了！")
        
    except Exception as e:
        print(f"❌ 長期間データ取得でエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 