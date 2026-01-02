# -*- coding: utf-8 -*-
"""
yosocal.com realtime.htm起点安定版長期間データ取得システム
ChromeDriverの互換性問題解決版
"""

import time
import csv
import json
import os
import subprocess
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
        return str(eta).split('.')[0]
    
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

def find_chromedriver_path():
    """ChromeDriverのパスを自動検出"""
    possible_paths = [
        "/usr/local/bin/chromedriver",
        "/opt/homebrew/bin/chromedriver",
        "/usr/bin/chromedriver",
        "./chromedriver",
        os.path.expanduser("~/chromedriver")
    ]
    
    # システムPATHで検索
    try:
        result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.exists(path):
                return path
    except:
        pass
    
    # 手動パス検索
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    return None

def setup_driver_stable():
    """安定版WebDriverセットアップ"""
    print("🔧 Chrome WebDriver（安定版）をセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # ChromeDriverの自動検出
    chromedriver_path = find_chromedriver_path()
    
    if chromedriver_path:
        print(f"✅ ChromeDriver発見: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        print("⚠️ システムChromeDriverが見つかりません")
        print("🔧 webdriver-managerを使用...")
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            print(f"❌ webdriver-manager失敗: {e}")
            raise Exception("ChromeDriverのセットアップに失敗しました")
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # automation detectionを回避
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 接続テスト
        driver.get('https://www.google.com')
        time.sleep(2)
        
        print("✅ WebDriverセットアップ完了")
        return driver
        
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def test_single_date_extraction(driver, year=2024, month=1, date_num=1):
    """単一日付でのデータ抽出テスト"""
    print(f"🧪 テスト: {year}年{month}月{date_num}日のデータ抽出")
    
    try:
        # メインページで日付クリック
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
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
        
        date_clicked = False
        for xpath in xpath_patterns:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    driver.execute_script("arguments[0].scrollIntoView(true);", elements[0])
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", elements[0])
                    date_clicked = True
                    break
            except:
                continue
        
        if not date_clicked:
            return [], f"日付{date_num}をクリックできませんでした"
        
        time.sleep(2)
        
        # realtime.htmに移動
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(4)
        
        # データ抽出テスト
        data = extract_wait_time_data_optimized(driver, year, month, date_num)
        
        if data:
            print(f"✅ テスト成功: {len(data)}件のデータを抽出")
            # サンプルデータ表示
            for i, record in enumerate(data[:5]):
                print(f"   {record['attraction']}: {record['time']} = {record['wait_time']}分")
            if len(data) > 5:
                print(f"   ... 他{len(data)-5}件")
        else:
            print("❌ テスト失敗: データが抽出できませんでした")
        
        return data, "テスト完了"
        
    except Exception as e:
        return [], f"テストエラー: {e}"

def extract_calendar_dates_from_main(driver, year, month):
    """メインページから日付を抽出"""
    try:
        driver.get('https://yosocal.com/')
        time.sleep(2)
        
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(3)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        available_dates = []
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
                                'data_source': 'realtime.htm安定版'
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

def main():
    """メイン処理（テスト版）"""
    print("🚀 yosocal.com realtime.htm起点安定版データ取得システム")
    print("🧪 ChromeDriver互換性問題解決＋単発テスト版")
    print("=" * 60)
    
    driver = None
    
    try:
        # WebDriverセットアップ
        driver = setup_driver_stable()
        
        # 単一日付でのテスト実行
        test_data, test_status = test_single_date_extraction(driver, 2024, 1, 1)
        
        if test_data:
            # テスト成功の場合、CSVファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_file = f"yosocal_stable_test_{timestamp}.csv"
            
            with open(test_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(test_data)
            
            print(f"\n📊 テスト結果:")
            print(f"   📁 テストファイル: {test_file}")
            print(f"   📈 総データ数: {len(test_data):,}件")
            
            valid_data = [d for d in test_data if d['wait_time'] is not None]
            print(f"   ✅ 有効データ: {len(valid_data)}件")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            print(f"\n✅ システムは正常に動作しています！")
            print(f"📝 実際の長期間データ取得を開始する場合は、")
            print(f"   main()関数内でテスト部分を実際の処理ループに変更してください")
        else:
            print(f"❌ テスト失敗: {test_status}")
            print(f"💡 ChromeDriverまたはサイトアクセスに問題があります")
        
    except Exception as e:
        print(f"❌ システムエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 