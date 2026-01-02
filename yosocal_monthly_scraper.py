# -*- coding: utf-8 -*-
"""
yosocal.com 月ごと保存・高速化対応版スクレイピングシステム
2024年1月1日 - 2025年6月30日 リアルデータ取得
8:45-21:45まで30分おき 全アトラクション対応
月ごとCSV保存・進捗確認・高速化処理
"""

import time
import csv
import json
import os
import requests
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import calendar
import threading
from concurrent.futures import ThreadPoolExecutor

class YosocalMonthlyProgressScraper:
    def __init__(self):
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://yosocal.com/'
        })
        
        # 対象時間帯（8:45-21:45まで30分おき）
        self.target_times = self.generate_target_times()
        
        # データ保存用
        self.all_data = []
        self.current_month_data = []
        self.progress_data = {
            'start_time': None,
            'total_months': 0,
            'completed_months': 0,
            'total_days': 0,
            'completed_days': 0,
            'total_records': 0,
            'valid_records': 0,
            'error_count': 0,
            'monthly_stats': {},
            'daily_stats': {}
        }
        
        # dataディレクトリ確保
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def generate_target_times(self):
        """8:45-21:45まで30分おきの時間帯を生成"""
        times = []
        hour = 8
        minute = 45
        
        while True:
            times.append(f"{hour:02d}:{minute:02d}")
            if hour == 21 and minute == 45:
                break
                
            minute += 30
            if minute >= 60:
                minute = 15 if minute == 90 else 45
                hour += 1
                
        return times

    def setup_driver(self):
        """WebDriverセットアップ（高速化・広告ブロック版）"""
        print("🔧 Chrome WebDriver（高速化版）をセットアップ中...")
        
        chrome_options = Options()
        
        # 高速化設定
        chrome_options.add_argument("--headless")  # ヘッドレスモード
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # 広告・画像・JavaScript無効化（高速化）
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
                "ads": 2
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # 自動化検出回避
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(15)  # タイムアウト短縮
            print("✅ WebDriverセットアップ完了（高速化版）")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def scrape_realtime_data_fast(self, target_date):
        """realtime.htmから高速データ取得"""
        try:
            # 直接realtime.htmにアクセス（高速化）
            realtime_url = "https://yosocal.com/realtime.htm"
            
            # セッション情報設定（日付指定）
            if not self.set_date_session(target_date):
                print(f"   ❌ 日付セッション設定失敗")
                return []
            
            # realtime.htmページ取得
            print(f"   🔄 realtime.htm直接アクセス中...")
            self.driver.get(realtime_url)
            
            # 短時間待機（高速化）
            time.sleep(2)
            
            # ページソース取得・解析
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # データ抽出
            extracted_data = self.extract_data_optimized(soup, target_date)
            
            if extracted_data:
                print(f"   ✅ {len(extracted_data)}件のデータを高速抽出")
                return extracted_data
            else:
                print(f"   ❌ データ抽出失敗")
                return []
                
        except Exception as e:
            print(f"   ❌ 高速スクレイピングエラー: {e}")
            return []

    def set_date_session(self, target_date):
        """日付セッション設定（広告回避版）"""
        try:
            # メインページアクセス
            self.driver.get("https://yosocal.com/")
            time.sleep(1)  # 短縮
            
            # 広告除去JavaScript実行
            self.driver.execute_script("""
                // 広告要素除去
                var ads = document.querySelectorAll('iframe[src*="googleads"], div[id*="ad"], div[class*="ad"]');
                ads.forEach(function(ad) { ad.remove(); });
                
                // オーバーレイ除去
                var overlays = document.querySelectorAll('div[style*="position: fixed"], div[style*="z-index"]');
                overlays.forEach(function(overlay) { 
                    if (overlay.style.zIndex > 100) overlay.remove(); 
                });
            """)
            
            # 日付ナビゲーション（高速版）
            if self.navigate_to_date_fast(target_date):
                return True
            else:
                print(f"   ❌ 日付ナビゲーション失敗")
                return False
                
        except Exception as e:
            print(f"   ❌ セッション設定エラー: {e}")
            return False

    def navigate_to_date_fast(self, target_date):
        """高速日付ナビゲーション"""
        try:
            target_year = target_date.year
            target_month = target_date.month
            target_day = target_date.day
            
            # 現在表示月取得
            current_year, current_month = self.get_current_calendar_date()
            
            # 目標年月まで移動（最小限）
            max_attempts = 24
            attempts = 0
            
            while (current_year, current_month) != (target_year, target_month) and attempts < max_attempts:
                if (target_year, target_month) > (current_year, current_month):
                    # 次月移動
                    next_script = "document.querySelector('input[value*=\"次\"]').click();"
                    try:
                        self.driver.execute_script(next_script)
                    except:
                        break
                else:
                    # 前月移動
                    prev_script = "document.querySelector('input[value*=\"前\"]').click();"
                    try:
                        self.driver.execute_script(prev_script)
                    except:
                        break
                
                time.sleep(0.5)  # 短縮
                current_year, current_month = self.get_current_calendar_date()
                attempts += 1
            
            # 日付クリック（JavaScript経由）
            day_click_script = f"""
                var dayElements = document.querySelectorAll('div.CAL, td.cal, span, a');
                for (var i = 0; i < dayElements.length; i++) {{
                    if (dayElements[i].innerText.trim() === '{target_day}') {{
                        dayElements[i].click();
                        break;
                    }}
                }}
            """
            
            self.driver.execute_script(day_click_script)
            time.sleep(1)  # 短縮
            
            print(f"   ✅ 日付 {target_date} 高速選択完了")
            return True
            
        except Exception as e:
            print(f"   ❌ 高速ナビゲーションエラー: {e}")
            return False

    def get_current_calendar_date(self):
        """現在のカレンダー表示年月を取得（高速版）"""
        try:
            # JavaScript経由で直接取得
            header_script = """
                var headers = document.querySelectorAll('td.CalendarHeader, div.calendar-header, th.month, span.current-month');
                for (var i = 0; i < headers.length; i++) {
                    var text = headers[i].innerText;
                    if (text.includes('年') && text.includes('月')) {
                        return text;
                    }
                }
                return document.title;
            """
            
            header_text = self.driver.execute_script(header_script)
            
            if header_text and '年' in header_text and '月' in header_text:
                year_match = re.search(r'(\d{4})年', header_text)
                month_match = re.search(r'(\d{1,2})月', header_text)
                
                if year_match and month_match:
                    return int(year_match.group(1)), int(month_match.group(1))
            
            # フォールバック
            now = datetime.now()
            return now.year, now.month
            
        except Exception:
            now = datetime.now()
            return now.year, now.month

    def extract_data_optimized(self, soup, target_date):
        """最適化データ抽出"""
        data = []
        
        try:
            # jamatテーブル検索
            jamat_div = soup.find('div', id='jamat')
            if jamat_div:
                data = self.extract_table_data_fast(jamat_div, target_date)
            
            # 代替方法（FPM/FPh2要素）
            if not data:
                data = self.extract_alternative_fast(soup, target_date)
            
            # データ品質確認
            if data:
                valid_count = len([item for item in data if item['wait_time'] is not None])
                print(f"     📊 抽出: {len(data)}件, 有効: {valid_count}件")
            
            return data
            
        except Exception as e:
            print(f"     ❌ 最適化抽出エラー: {e}")
            return []

    def extract_table_data_fast(self, jamat_div, target_date):
        """高速テーブルデータ抽出"""
        data = []
        
        try:
            rows = jamat_div.find_all('tr')
            if len(rows) < 4:
                return data
            
            # 時間行・データ行検出
            time_row = None
            data_rows = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) > 5:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # 時間行検出
                    if any(re.match(r'\d{1,2}:\d{2}', text) for text in cell_texts):
                        time_row = row
                        continue
                    
                    # データ行検出（アトラクション名）
                    if cell_texts and len(cell_texts[0]) > 1:
                        attraction_keywords = ['オムニバス', 'カリブ', '美女', 'ビッグ', 'スプラッシュ', 
                                             'スペース', 'タワー', 'ソアリン', 'ベイマックス', 'プーさん']
                        if any(keyword in cell_texts[0] for keyword in attraction_keywords):
                            data_rows.append(row)
            
            if not time_row or not data_rows:
                return data
            
            # 時間帯抽出
            time_cells = time_row.find_all(['td', 'th'])
            times = []
            
            # 天候列オフセット検出
            weather_offset = 0
            if time_cells and any(keyword in time_cells[0].get_text(strip=True) 
                                for keyword in ['晴', '曇', '雨', '気温', '天気']):
                weather_offset = 1
            
            for cell in time_cells[weather_offset:]:
                time_text = cell.get_text(strip=True)
                if re.match(r'\d{1,2}:\d{2}', time_text):
                    times.append(time_text)
            
            # データ行処理
            for row in data_rows:
                data_cells = row.find_all(['td', 'th'])
                
                if len(data_cells) <= weather_offset:
                    continue
                
                attraction_name = data_cells[weather_offset].get_text(strip=True)
                if not attraction_name or len(attraction_name) < 2:
                    continue
                
                # 各時間帯データ抽出
                for time_idx, time_slot in enumerate(times):
                    if time_slot in self.target_times:
                        cell_idx = weather_offset + 1 + time_idx
                        if cell_idx < len(data_cells):
                            cell = data_cells[cell_idx]
                            cell_text = cell.get_text(strip=True)
                            css_classes = ' '.join(cell.get('class', []))
                            
                            # 待ち時間解析
                            wait_time = None
                            status = "no_data"
                            
                            if cell_text.isdigit() and 1 <= int(cell_text) <= 300:
                                wait_time = int(cell_text)
                                status = "normal"
                            elif cell_text in ['-', '---', '休止', '運休', 'CLOSE']:
                                status = "closed"
                            elif 'B' in css_classes:
                                status = "congestion_level"
                                for cls in cell.get('class', []):
                                    if cls.startswith('B') and cls[1:].isdigit():
                                        level = int(cls[1:])
                                        wait_time = min(level * 10 + 10, 120)
                                        break
                            
                            data.append({
                                'date': target_date.strftime("%m月%d日"),
                                'year': target_date.year,
                                'month': target_date.month,
                                'day': target_date.day,
                                'time': time_slot,
                                'attraction': attraction_name,
                                'wait_time': wait_time,
                                'status': status,
                                'css_classes': css_classes,
                                'raw_value': cell_text,
                                'data_source': 'fast_scraping_yosocal'
                            })
        
        except Exception as e:
            print(f"     ❌ 高速テーブル抽出エラー: {e}")
        
        return data

    def extract_alternative_fast(self, soup, target_date):
        """高速代替データ抽出"""
        data = []
        
        try:
            # FPM、FPh2 クラス要素検索
            fpm_elements = soup.find_all(class_=re.compile(r'FPM'))
            fph2_elements = soup.find_all(class_=re.compile(r'FPh2'))
            b_elements = soup.find_all(class_=re.compile(r'B[0-8]'))
            
            print(f"     📊 FPM: {len(fpm_elements)}, FPh2: {len(fph2_elements)}, B要素: {len(b_elements)}")
            
            if fpm_elements and fph2_elements:
                for i in range(min(len(fpm_elements), len(fph2_elements))):
                    time_text = fpm_elements[i].get_text(strip=True)
                    attraction_text = fph2_elements[i].get_text(strip=True)
                    
                    if re.match(r'\d{1,2}:\d{2}', time_text) and time_text in self.target_times:
                        wait_time = None
                        status = "no_data"
                        css_classes = ""
                        b_text = ""
                        
                        if i < len(b_elements):
                            b_element = b_elements[i]
                            b_text = b_element.get_text(strip=True)
                            css_classes = ' '.join(b_element.get('class', []))
                            
                            if b_text.isdigit():
                                wait_time = int(b_text)
                                status = "normal"
                            elif 'B' in css_classes:
                                for cls in b_element.get('class', []):
                                    if cls.startswith('B') and cls[1:].isdigit():
                                        level = int(cls[1:])
                                        wait_time = min(level * 10 + 10, 120)
                                        status = "congestion_level"
                                        break
                        
                        data.append({
                            'date': target_date.strftime("%m月%d日"),
                            'year': target_date.year,
                            'month': target_date.month,
                            'day': target_date.day,
                            'time': time_text,
                            'attraction': attraction_text,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': css_classes,
                            'raw_value': b_text,
                            'data_source': 'alternative_fast_scraping'
                        })
        
        except Exception as e:
            print(f"     ❌ 高速代替抽出エラー: {e}")
        
        return data

    def save_monthly_data(self, year, month, monthly_data):
        """月ごとデータ保存"""
        if not monthly_data:
            print(f"   📁 {year}年{month}月: データなし、保存スキップ")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(self.data_dir, f"yosocal_{year}_{month:02d}_{timestamp}.csv")
        progress_filename = os.path.join(self.data_dir, f"yosocal_{year}_{month:02d}_progress_{timestamp}.json")
        
        # CSV保存
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 
                        'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in monthly_data:
                writer.writerow(record)
        
        # 月別統計保存
        valid_count = len([item for item in monthly_data if item['wait_time'] is not None])
        monthly_stats = {
            'year': year,
            'month': month,
            'total_records': len(monthly_data),
            'valid_records': valid_count,
            'csv_filename': csv_filename,
            'created_at': timestamp
        }
        
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(monthly_stats, f, ensure_ascii=False, indent=2)
        
        print(f"   💾 {year}年{month}月完了: {len(monthly_data)}件 (有効: {valid_count}件)")
        print(f"       📁 保存先: {csv_filename}")
        
        return csv_filename

    def process_date_range_monthly(self, start_date, end_date):
        """月ごと処理メイン"""
        print(f"🚀 yosocal.com 月ごと保存・高速スクレイピング開始")
        print(f"📅 対象期間: {start_date} - {end_date}")
        print(f"⏰ 時間帯: 8:45-21:45 (30分おき)")
        print(f"📁 保存先: {self.data_dir}ディレクトリ")
        print("=" * 70)
        
        # WebDriverセットアップ
        if not self.setup_driver():
            print("❌ WebDriverセットアップに失敗しました")
            return
        
        try:
            # 月ごと処理
            current_date = start_date
            
            while current_date <= end_date:
                year = current_date.year
                month = current_date.month
                
                print(f"\n📅 {year}年{month}月 処理開始")
                
                # その月の全日付取得
                month_start = date(year, month, 1)
                if month == 12:
                    month_end = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = date(year, month + 1, 1) - timedelta(days=1)
                
                # 処理範囲調整
                actual_start = max(month_start, start_date)
                actual_end = min(month_end, end_date)
                
                # その月の日付リスト生成
                month_dates = []
                process_date = actual_start
                while process_date <= actual_end:
                    month_dates.append(process_date)
                    process_date += timedelta(days=1)
                
                print(f"   📋 対象日数: {len(month_dates)}日")
                
                # 月データ初期化
                monthly_data = []
                
                # 日別処理（プログレスバー付き）
                with tqdm(total=len(month_dates), desc=f"{year}年{month}月", unit="日") as pbar:
                    for day_date in month_dates:
                        try:
                            day_data = self.scrape_realtime_data_fast(day_date)
                            
                            if day_data:
                                monthly_data.extend(day_data)
                                valid_count = len([item for item in day_data if item['wait_time'] is not None])
                                
                                pbar.set_postfix({
                                    'データ': f'{len(day_data)}件',
                                    '有効': f'{valid_count}件'
                                })
                            else:
                                pbar.set_postfix({
                                    'データ': '0件',
                                    'エラー': 'あり'
                                })
                            
                            pbar.update(1)
                            
                            # 連続アクセス回避（短縮）
                            time.sleep(0.5)
                            
                        except Exception as e:
                            print(f"   ❌ {day_date}: 処理エラー: {e}")
                            pbar.update(1)
                            continue
                
                # 月データ保存
                csv_file = self.save_monthly_data(year, month, monthly_data)
                
                if csv_file:
                    self.progress_data['completed_months'] += 1
                    self.progress_data['monthly_stats'][f"{year}-{month:02d}"] = {
                        'csv_file': csv_file,
                        'total_records': len(monthly_data),
                        'valid_records': len([item for item in monthly_data if item['wait_time'] is not None])
                    }
                
                # 次月へ
                if month == 12:
                    current_date = date(year + 1, 1, 1)
                else:
                    current_date = date(year, month + 1, 1)
        
        finally:
            if self.driver:
                print("\n🔧 WebDriver終了")
                self.driver.quit()
        
        # 最終サマリー
        self.print_final_summary()

    def print_final_summary(self):
        """最終サマリー表示"""
        print(f"\n📊 最終処理結果:")
        print(f"   📅 処理月数: {self.progress_data['completed_months']}月")
        print(f"   📁 保存ファイル数: {len(self.progress_data['monthly_stats'])}件")
        print(f"   📂 保存先ディレクトリ: {self.data_dir}")
        
        print(f"\n📈 月別処理統計:")
        for month_key, stats in self.progress_data['monthly_stats'].items():
            print(f"   {month_key}: {stats['total_records']}件 (有効: {stats['valid_records']}件)")
            print(f"      📁 {os.path.basename(stats['csv_file'])}")
        
        print("⚡ 月ごと保存・高速スクレイピング完了！")

def main():
    """メイン実行"""
    scraper = YosocalMonthlyProgressScraper()
    
    # テスト期間設定（1か月分で動作確認）
    start_date = date(2024, 7, 1)  # テスト用
    end_date = date(2024, 7, 31)   # テスト用
    
    print("🧪 プログラム動作確認（2024年7月）")
    print("　　正常動作確認後、期間を拡張してください")
    
    # 月ごと処理実行
    scraper.process_date_range_monthly(start_date, end_date)

if __name__ == "__main__":
    main() 