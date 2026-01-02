# -*- coding: utf-8 -*-
"""
yosocal.com/realtime.htm 実際のスクレイピングシステム
2024年1月1日 - 2025年6月30日 リアルデータ取得
8:45-21:45まで30分おき 全アトラクション対応
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

class YosocalRealScraper:
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
        self.progress_data = {
            'start_time': None,
            'total_days': 0,
            'completed_days': 0,
            'total_records': 0,
            'valid_records': 0,
            'error_count': 0,
            'daily_stats': {}
        }

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
        """WebDriverセットアップ（実際のスクレイピング用）"""
        print("🔧 Chrome WebDriver（実際のスクレイピング版）をセットアップ中...")
        
        chrome_options = Options()
        # 実際のブラウザ動作に近づける
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 性能最適化
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # 広告ブロック設定
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values": {
                "ads": 2,
                "popups": 2,
                "notifications": 2
            }
        })
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            print("✅ WebDriverセットアップ完了")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def scrape_realtime_data(self, target_date):
        """realtime.htmから実際のデータを取得"""
        try:
            # メインページに移動して日付を設定
            print(f"   📅 {target_date.strftime('%Y年%m月%d日')} のデータ取得開始")
            
            # メインページで日付クリック
            if not self.navigate_to_date(target_date):
                print(f"   ❌ 日付ナビゲーション失敗")
                return []
            
            # realtime.htmに移動
            print(f"   🔄 realtime.htmページに移動中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(5)  # ページロード待機
            
            # ページソース取得
            page_source = self.driver.page_source
            
            # HTMLパース
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # jamatテーブルを検索
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                print(f"   ❌ jamatテーブルが見つかりません")
                return self.try_alternative_extraction(soup, target_date)
                
            # テーブルデータ抽出
            extracted_data = self.extract_table_data(jamat_div, target_date)
            
            if extracted_data:
                print(f"   ✅ {len(extracted_data)}件のデータを抽出")
                return extracted_data
            else:
                print(f"   ❌ データ抽出失敗、代替方法を試行")
                return self.try_alternative_extraction(soup, target_date)
                
        except Exception as e:
            print(f"   ❌ スクレイピングエラー: {e}")
            return []

    def navigate_to_date(self, target_date):
        """指定日付にナビゲート"""
        try:
            # メインページアクセス
            self.driver.get("https://yosocal.com/")
            time.sleep(3)
            
            target_year = target_date.year
            target_month = target_date.month
            
            # 現在表示されている年月を取得
            current_year, current_month = self.get_current_calendar_date()
            
            # 目標年月まで移動
            max_attempts = 24  # 最大2年分
            attempts = 0
            
            while (current_year, current_month) != (target_year, target_month) and attempts < max_attempts:
                if (target_year, target_month) > (current_year, current_month):
                    # 次月ボタン
                    try:
                        next_btn = self.driver.find_element(By.XPATH, "//input[@value='次月' or @value='次の月' or contains(@onclick, 'next')]")
                        self.driver.execute_script("arguments[0].click();", next_btn)
                    except NoSuchElementException:
                        print(f"   ❌ 次月ボタンが見つかりません")
                        break
                else:
                    # 前月ボタン
                    try:
                        prev_btn = self.driver.find_element(By.XPATH, "//input[@value='前月' or @value='前の月' or contains(@onclick, 'prev')]")
                        self.driver.execute_script("arguments[0].click();", prev_btn)
                    except NoSuchElementException:
                        print(f"   ❌ 前月ボタンが見つかりません")
                        break
                
                time.sleep(2)
                current_year, current_month = self.get_current_calendar_date()
                attempts += 1
            
            if attempts >= max_attempts:
                print(f"   ❌ 目標年月への移動に失敗しました")
                return False
            
            # 指定日をクリック
            day_str = str(target_date.day)
            
            # 複数の日付要素パターンを試行
            day_selectors = [
                f"//div[contains(@class, 'CAL') and text()='{day_str}']",
                f"//td[contains(@class, 'cal') and text()='{day_str}']",
                f"//span[text()='{day_str}']",
                f"//a[text()='{day_str}']",
                f"//*[text()='{day_str}' and (contains(@class, 'day') or contains(@class, 'date') or contains(@class, 'cal'))]"
            ]
            
            clicked = False
            for selector in day_selectors:
                try:
                    day_elements = self.driver.find_elements(By.XPATH, selector)
                    if day_elements:
                        # 最初にクリック可能な要素を選択
                        for element in day_elements:
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", element)
                                time.sleep(2)
                                clicked = True
                                break
                            except Exception:
                                continue
                        if clicked:
                            break
                except Exception:
                    continue
            
            if not clicked:
                print(f"   ❌ 日付 {target_date} のクリックに失敗")
                return False
            
            print(f"   ✅ 日付 {target_date} を選択完了")
            return True
                
        except Exception as e:
            print(f"   ❌ 日付ナビゲーションエラー: {e}")
            return False

    def get_current_calendar_date(self):
        """現在のカレンダー表示年月を取得"""
        try:
            # 複数のパターンでヘッダーを検索
            header_selectors = [
                "//td[contains(@class, 'CalendarHeader')]",
                "//div[contains(@class, 'calendar-header')]",
                "//th[contains(@class, 'month')]",
                "//span[contains(@class, 'current-month')]",
                "//*[contains(text(), '年') and contains(text(), '月')]"
            ]
            
            header_text = ""
            for selector in header_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        header_text = elements[0].text
                        break
                except Exception:
                    continue
            
            # "2024年1月" 形式から年月を抽出
            if header_text and '年' in header_text and '月' in header_text:
                year_match = re.search(r'(\d{4})年', header_text)
                month_match = re.search(r'(\d{1,2})月', header_text)
                
                if year_match and month_match:
                    return int(year_match.group(1)), int(month_match.group(1))
            
            # フォールバック：ページタイトルやURLから推測
            title = self.driver.title
            if '年' in title and '月' in title:
                year_match = re.search(r'(\d{4})年', title)
                month_match = re.search(r'(\d{1,2})月', title)
                if year_match and month_match:
                    return int(year_match.group(1)), int(month_match.group(1))
            
            # デフォルト：現在日付
            now = datetime.now()
            return now.year, now.month
            
        except Exception:
            now = datetime.now()
            return now.year, now.month

    def extract_table_data(self, jamat_div, target_date):
        """jamatテーブルからデータを抽出"""
        data = []
        
        try:
            # テーブル行を取得
            rows = jamat_div.find_all('tr')
            if len(rows) < 4:
                print(f"     ❌ 十分な行数がありません: {len(rows)}行")
                return data
            
            print(f"     📊 {len(rows)}行のテーブルを発見")
            
            # 時間帯行とアトラクション行を特定
            time_row = None
            data_rows = []
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) > 5:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # 時間帯行を検出（8:45, 9:15等の時間パターン）
                    if any(re.match(r'\d{1,2}:\d{2}', text) for text in cell_texts):
                        time_row = row
                        print(f"     ✅ 時間帯行を発見: 行{i}")
                        continue
                    
                    # データ行を検出（アトラクション名を含む行）
                    if any(keyword in cell_texts[0] for keyword in ['オムニバス', 'カリブ', '美女', 'ビッグ', 'スプラッシュ', 'スペース', 'タワー', 'ソアリン', 'ベイマックス'] if cell_texts):
                        data_rows.append(row)
                        print(f"     ✅ データ行を発見: 行{i} - {cell_texts[0]}")
            
            if not time_row:
                print(f"     ❌ 時間帯行が見つかりません")
                return data
            
            if not data_rows:
                print(f"     ❌ データ行が見つかりません")
                return data
            
            # 時間帯を抽出
            time_cells = time_row.find_all(['td', 'th'])
            times = []
            
            # 天候列オフセット検出
            weather_offset = 0
            if len(time_cells) > 0:
                first_cell_text = time_cells[0].get_text(strip=True)
                if first_cell_text in ['晴', '曇', '雨', '雪', '天気'] or '気温' in first_cell_text:
                    weather_offset = 1
                    print(f"     📊 天候列オフセット検出: {first_cell_text}")
            
            # 時間帯抽出
            for cell in time_cells[weather_offset:]:
                time_text = cell.get_text(strip=True)
                if re.match(r'\d{1,2}:\d{2}', time_text):
                    times.append(time_text)
            
            print(f"     ⏰ 発見された時間帯: {times}")
            
            # データ行処理
            for row in data_rows:
                data_cells = row.find_all(['td', 'th'])
                
                if len(data_cells) <= weather_offset:
                    continue
                
                attraction_name = data_cells[weather_offset].get_text(strip=True)
                if not attraction_name or len(attraction_name) < 2:
                    continue
                
                print(f"     🎢 処理中: {attraction_name}")
                
                # 各時間帯のデータを抽出
                for time_idx, time_slot in enumerate(times):
                    if time_slot in self.target_times:
                        cell_idx = weather_offset + 1 + time_idx
                        if cell_idx < len(data_cells):
                            cell = data_cells[cell_idx]
                            cell_text = cell.get_text(strip=True)
                            css_classes = ' '.join(cell.get('class', []))
                            
                            # 待ち時間データ解析
                            wait_time = None
                            status = "no_data"
                            
                            if cell_text.isdigit() and 1 <= int(cell_text) <= 300:
                                wait_time = int(cell_text)
                                status = "normal"
                            elif cell_text in ['-', '---', '休止', '運休', 'CLOSE']:
                                status = "closed"
                            elif 'B' in css_classes:
                                status = "congestion_level"
                                # B0-B8 クラスから待ち時間を推定
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
                                'data_source': 'real_scraping_yosocal'
                            })
        
        except Exception as e:
            print(f"     ❌ テーブルデータ抽出エラー: {e}")
        
        return data

    def try_alternative_extraction(self, soup, target_date):
        """代替データ抽出方法"""
        data = []
        
        try:
            print(f"     🔄 代替抽出方法を試行中...")
            
            # FPM、FPh2 クラス要素を検索
            fpm_elements = soup.find_all(class_=re.compile(r'FPM'))
            fph2_elements = soup.find_all(class_=re.compile(r'FPh2'))
            b_elements = soup.find_all(class_=re.compile(r'B[0-8]'))
            
            print(f"     📊 FPM: {len(fpm_elements)}, FPh2: {len(fph2_elements)}, B要素: {len(b_elements)}")
            
            if fpm_elements and fph2_elements:
                # FPM/FPh2ベースの抽出
                for i in range(min(len(fpm_elements), len(fph2_elements))):
                    time_text = fpm_elements[i].get_text(strip=True)
                    attraction_text = fph2_elements[i].get_text(strip=True)
                    
                    if re.match(r'\d{1,2}:\d{2}', time_text) and time_text in self.target_times:
                        # 対応するB要素を検索
                        wait_time = None
                        status = "no_data"
                        css_classes = ""
                        
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
                            'raw_value': b_text if 'b_text' in locals() else "",
                            'data_source': 'alternative_scraping_yosocal'
                        })
            
            print(f"     ✅ 代替方法で{len(data)}件抽出")
            
        except Exception as e:
            print(f"     ❌ 代替抽出エラー: {e}")
        
        return data

    def process_date_range(self, start_date, end_date):
        """指定期間のデータを処理"""
        print(f"🚀 yosocal.com 実際のスクレイピング開始")
        print(f"📅 対象期間: {start_date} - {end_date}")
        print(f"⏰ 時間帯: 8:45-21:45 (30分おき)")
        print("=" * 70)
        
        # 日付リスト生成
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        
        self.progress_data['total_days'] = len(date_list)
        self.progress_data['start_time'] = datetime.now()
        
        print(f"📋 処理対象日数: {len(date_list)}日")
        
        # WebDriverセットアップ
        if not self.setup_driver():
            print("❌ WebDriverセットアップに失敗しました")
            return
        
        try:
            # 日別処理
            with tqdm(total=len(date_list), desc="日別処理", unit="日") as pbar:
                for process_date in date_list:
                    try:
                        day_data = self.scrape_realtime_data(process_date)
                        
                        if day_data:
                            self.all_data.extend(day_data)
                            valid_count = len([item for item in day_data if item['wait_time'] is not None])
                            
                            self.progress_data['completed_days'] += 1
                            self.progress_data['total_records'] += len(day_data)
                            self.progress_data['valid_records'] += valid_count
                            self.progress_data['daily_stats'][process_date.strftime('%Y-%m-%d')] = {
                                'total': len(day_data),
                                'valid': valid_count
                            }
                            
                            pbar.set_postfix({
                                'データ': f'{len(day_data)}件',
                                '有効': f'{valid_count}件'
                            })
                        else:
                            self.progress_data['error_count'] += 1
                            pbar.set_postfix({
                                'データ': '0件',
                                'エラー': 'あり'
                            })
                        
                        pbar.update(1)
                        
                        # 連続アクセス回避
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"❌ {process_date}: 処理エラー: {e}")
                        self.progress_data['error_count'] += 1
                        pbar.update(1)
                        continue
        
        finally:
            if self.driver:
                print("🔧 WebDriver終了")
                self.driver.quit()
        
        # 最終保存
        self.save_final_data()

    def save_final_data(self):
        """最終データ保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"yosocal_real_scraping_{timestamp}.csv"
        progress_filename = f"yosocal_real_scraping_progress_{timestamp}.json"
        
        # CSVファイル保存
        if self.all_data:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 
                            'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for record in self.all_data:
                    writer.writerow(record)
        
        # 進捗ファイル保存
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(self.progress_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 最終統計
        end_time = datetime.now()
        duration = end_time - self.progress_data['start_time']
        
        print(f"\n📊 最終処理結果:")
        print(f"   ⏱️ 総処理時間: {duration}")
        print(f"   📅 処理日数: {self.progress_data['completed_days']}/{self.progress_data['total_days']}")
        print(f"   📈 総データ数: {len(self.all_data):,}件")
        print(f"   ✅ 有効データ: {self.progress_data['valid_records']:,}件")
        print(f"   ❌ エラー数: {self.progress_data['error_count']}件")
        print(f"   📁 出力ファイル: {csv_filename}")
        
        if self.all_data:
            # データ品質レポート
            source_stats = {}
            for record in self.all_data:
                source = record['data_source']
                source_stats[source] = source_stats.get(source, 0) + 1
            
            print(f"📊 データソース別統計:")
            for source, count in source_stats.items():
                percentage = count / len(self.all_data) * 100
                print(f"   {source}: {count:,}件 ({percentage:.1f}%)")
        
        print("⚡ 実際のスクレイピング完了！")
        return csv_filename

def main():
    """メイン実行"""
    scraper = YosocalRealScraper()
    
    # 対象期間設定
    start_date = date(2024, 1, 1)
    end_date = date(2025, 6, 30)
    
    # 実際のスクレイピング実行
    scraper.process_date_range(start_date, end_date)

if __name__ == "__main__":
    main() 