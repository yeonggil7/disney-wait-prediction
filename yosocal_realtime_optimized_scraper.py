# -*- coding: utf-8 -*-
"""
yosocal.com realtime.htm起点最適化版長期間データ取得システム
2024年1月1日から2025年6月30日までの全期間データ取得
realtime.htmからの直接カレンダー操作で効率化
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

class YosocalProgressTracker:
    """進捗追跡・表示クラス"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_months = 0
        self.completed_months = 0
        self.total_days = 0
        self.completed_days = 0
        self.successful_days = 0
        self.failed_days = 0
        self.total_records = 0
        self.valid_records = 0
        self.current_year = None
        self.current_month = None
        self.current_day = None
        
    def start_month(self, year, month, available_days):
        """月処理開始"""
        self.current_year = year
        self.current_month = month
        self.total_days += len(available_days)
        print(f"\n📅 {year}年{month}月 処理開始 ({len(available_days)}日)")
        
    def complete_month(self, month_records):
        """月処理完了"""
        self.completed_months += 1
        self.total_records += len(month_records)
        valid_count = len([r for r in month_records if r.get('wait_time') is not None])
        self.valid_records += valid_count
        
        elapsed = datetime.now() - self.start_time
        rate = self.completed_days / elapsed.total_seconds() * 3600 if elapsed.total_seconds() > 0 else 0
        
        print(f"✅ {self.current_year}年{self.current_month}月完了")
        print(f"   📊 月データ: {len(month_records)}件 (有効: {valid_count}件)")
        print(f"   📈 累計: {self.total_records:,}件 (有効: {self.valid_records:,}件)")
        print(f"   ⏱️ 処理速度: {rate:.1f}日/時間")
        print(f"   📋 進捗: 月 {self.completed_months}/{self.total_months}, 日 {self.completed_days}/{self.total_days}")
        
    def process_day(self, day, records, status):
        """日処理結果"""
        self.current_day = day
        self.completed_days += 1
        
        if records:
            self.successful_days += 1
            valid_count = len([r for r in records if r.get('wait_time') is not None])
            print(f"✅ {self.current_month}月{day:02d}日: {len(records)}件 (有効: {valid_count}件)")
        else:
            self.failed_days += 1
            print(f"❌ {self.current_month}月{day:02d}日: {status}")
    
    def get_eta(self):
        """推定残り時間"""
        if self.completed_days == 0:
            return "不明"
        
        elapsed = datetime.now() - self.start_time
        rate = self.completed_days / elapsed.total_seconds()
        remaining_days = self.total_days - self.completed_days
        eta_seconds = remaining_days / rate if rate > 0 else 0
        
        eta = timedelta(seconds=eta_seconds)
        return str(eta).split('.')[0]  # 秒以下切り捨て
    
    def print_summary(self):
        """最終サマリー表示"""
        elapsed = datetime.now() - self.start_time
        success_rate = (self.successful_days / self.completed_days * 100) if self.completed_days > 0 else 0
        
        print(f"\n📊 最終処理結果:")
        print(f"   ⏱️ 総処理時間: {str(elapsed).split('.')[0]}")
        print(f"   📅 処理月数: {self.completed_months}/{self.total_months}")
        print(f"   📅 処理日数: {self.completed_days}/{self.total_days}")
        print(f"   ✅ 成功率: {success_rate:.1f}% ({self.successful_days}/{self.completed_days})")
        print(f"   📈 総データ数: {self.total_records:,}件")
        print(f"   ✅ 有効データ: {self.valid_records:,}件")

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 広告ブロック設定でクリック干渉を回避
    chrome_options.add_argument("--block-new-web-contents")
    chrome_options.add_argument("--disable-popup-blocking")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ WebDriverセットアップ完了")
    return driver

def navigate_to_realtime_month(driver, year, month):
    """realtime.htmから指定年月に移動"""
    try:
        # realtime.htmに直接アクセス
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(3)
        
        # メインページに移動してJavaScript関数で月移動
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        # JavaScript関数で月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        # realtime.htmに戻る
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(3)
        
        return True, f"{year}年{month}月"
        
    except Exception as e:
        return False, f"エラー: {e}"

def extract_calendar_dates_from_main(driver, year, month):
    """メインページから日付を抽出"""
    try:
        # メインページで月移動
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        available_dates = []
        
        # div要素のCAL、CALSAT、CALSUNクラスの日付要素を探す
        date_classes = ['CAL', 'CALSAT', 'CALSUN']
        
        for class_name in date_classes:
            date_elements = soup.find_all('div', class_=class_name)
            for element in date_elements:
                date_text = element.get_text(strip=True)
                if date_text == '1/1':
                    available_dates.append(1)
                elif date_text.isdigit():
                    date_num = int(date_text)
                    if 1 <= date_num <= 31:
                        available_dates.append(date_num)
        
        return sorted(list(set(available_dates)))
        
    except Exception as e:
        print(f"❌ カレンダー日付抽出エラー: {e}")
        return []

def click_date_and_get_realtime_data(driver, date_num, year, month):
    """日付をクリックしてrealtime.htmでデータ抽出"""
    try:
        # メインページで日付クリック
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        # 月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        # 日付クリック（広告要素の干渉を回避）
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
                # 要素が見える位置にスクロール
                driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                time.sleep(1)
                
                # JavaScriptクリックで広告干渉を回避
                driver.execute_script("arguments[0].click();", elements[0])
                date_element = elements[0]
                break
        
        if not date_element:
            return [], f"日付{date_num}が見つかりません"
        
        time.sleep(2)
        
        # realtime.htmに移動してデータ抽出
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(4)
        
        # データ抽出
        data = extract_wait_time_data_optimized(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def extract_wait_time_data_optimized(driver, year, month, date_num):
    """最適化されたデータ抽出"""
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
        if len(rows) < 2:
            return []
        
        # 期待される時間帯を取得
        expected_times = generate_expected_times()
        
        # データ抽出
        extracted_data = []
        
        # 各行のアトラクションデータを抽出
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all(['td', 'th'])
            if cells:
                attraction_name = cells[0].get_text(strip=True)
                if attraction_name and attraction_name not in ['時間', 'アトラクション']:
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
                                'attraction': attraction_name,
                                'wait_time': wait_time,
                                'status': status,
                                'css_classes': css_classes,
                                'raw_value': cell_text,
                                'data_source': 'realtime.htm直接'
                            }
                            extracted_data.append(record)
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def generate_expected_times():
    """期待される時間帯リストを生成"""
    times = []
    for hour in range(8, 22):
        times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
    times.append("平均")
    return times

def save_progress(filename, completed_months, total_data_count, tracker):
    """進捗を保存"""
    progress = {
        'completed_months': completed_months,
        'total_data_count': total_data_count,
        'completed_days': tracker.completed_days,
        'successful_days': tracker.successful_days,
        'failed_days': tracker.failed_days,
        'valid_records': tracker.valid_records,
        'start_time': tracker.start_time.isoformat(),
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
    """メインrealtime.htm起点最適化プロセス"""
    print("🚀 yosocal.com realtime.htm起点最適化版長期間データ取得システム")
    print("📅 対象期間: 2024年1月1日 - 2025年6月30日")
    print("⚡ realtime.htm直接アクセス最適化版")
    print("=" * 60)
    
    # 出力ファイル設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_realtime_optimized_{timestamp}.csv"
    progress_file = f"yosocal_realtime_progress_{timestamp}.json"
    
    # 進捗追跡初期化
    tracker = YosocalProgressTracker()
    
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
    
    tracker.total_months = len(target_months)
    print(f"📋 処理対象: {len(target_months)}ヶ月")
    
    if not target_months:
        print("✅ すべての月が処理済みです")
        return
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        # 月ごとの処理
        for year, month, month_key in tqdm(target_months, desc="月処理", position=0):
            
            try:
                # カレンダー日付抽出
                available_dates = extract_calendar_dates_from_main(driver, year, month)
                if not available_dates:
                    print(f"⚠️ {year}年{month}月にデータなし")
                    completed_months.add(month_key)
                    continue
                
                tracker.start_month(year, month, available_dates)
                
                # 日付ごとの処理
                month_data = []
                
                for date_num in tqdm(available_dates, desc=f"{year}/{month:02d}", leave=False, position=1):
                    try:
                        # 日付クリックとデータ抽出
                        data, status = click_date_and_get_realtime_data(driver, date_num, year, month)
                        
                        month_data.extend(data)
                        tracker.process_day(date_num, data, status)
                        
                        # 短い待機
                        time.sleep(1)
                        
                    except Exception as e:
                        tracker.process_day(date_num, [], f"処理エラー: {e}")
                
                # 月データを追加
                all_data.extend(month_data)
                completed_months.add(month_key)
                tracker.complete_month(month_data)
                
                # 推定残り時間表示
                eta = tracker.get_eta()
                print(f"   ⏰ 推定残り時間: {eta}")
                
                # 進捗保存
                save_progress(progress_file, list(completed_months), len(all_data), tracker)
                
                # 中間保存（3ヶ月ごと）
                if len(completed_months) % 3 == 0 and len(all_data) > 0:
                    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                                    'status', 'css_classes', 'raw_value', 'data_source']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(all_data)
                    print(f"💾 中間保存完了: {len(all_data):,}件")
                
            except Exception as e:
                print(f"❌ {year}年{month}月処理中にエラー: {e}")
                continue
        
        # 最終データ保存
        if all_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_data)
            
            tracker.print_summary()
            print(f"   📁 出力ファイル: {output_file}")
            
            if tracker.valid_records > 0:
                valid_data = [d for d in all_data if d['wait_time'] is not None]
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # 年別統計
            print(f"\n📈 年別統計:")
            for year in [2024, 2025]:
                year_data = [d for d in all_data if d['year'] == year]
                if year_data:
                    print(f"   {year}年: {len(year_data):,}件")
            
            # ファイルサイズ
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"   💾 ファイルサイズ: {file_size:.1f}MB")
        
        print(f"\n⚡ realtime.htm起点最適化版処理完了！")
        
    except Exception as e:
        print(f"❌ 長期間データ取得でエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 