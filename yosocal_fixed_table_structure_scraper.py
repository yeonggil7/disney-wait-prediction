# -*- coding: utf-8 -*-
"""
yosocal.com 修正版テーブル構造対応スクレイピングシステム
正しい構造: 行5=アトラクション名(42個), 行6以降=時間データ, 列2以降=待ち時間
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

class YosocalFixedTableStructureScraper:
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
        
        # 対象時間帯（8:15-21:45まで30分おき + 平均）
        self.target_times = self.generate_target_times()
        
        # データ保存用
        self.all_data = []
        
        # dataディレクトリ確保
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def generate_target_times(self):
        """8:15-21:45まで30分おき + 平均"""
        times = []
        hour = 8
        minute = 15
        
        # 8:15から21:45まで
        while True:
            times.append(f"{hour:02d}:{minute:02d}")
            if hour == 21 and minute == 45:
                break
                
            minute += 30
            if minute >= 60:
                minute -= 60
                hour += 1
        
        # 平均も追加
        times.append("平均")
        
        print(f"📋 対象時間帯: {len(times)}個 ({times[0]}～{times[-2]}+{times[-1]})")
        return times

    def setup_driver(self):
        """WebDriverセットアップ（修正版テーブル構造対応）"""
        print("🔧 Chrome WebDriver（修正版テーブル構造対応）をセットアップ中...")
        
        chrome_options = Options()
        
        # 高速化設定
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # 広告ブロック設定
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,
                "plugins": 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
                "media_stream": 2,
                "ads": 2
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
            self.driver.set_page_load_timeout(15)
            print("✅ WebDriverセットアップ完了（修正版テーブル構造対応）")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def scrape_fixed_table_data(self, target_date):
        """修正版テーブル構造データ取得"""
        try:
            print(f"   📅 {target_date.strftime('%Y年%m月%d日')} の修正版テーブル構造データ取得開始")
            
            # セッション設定
            if not self.set_date_session(target_date):
                print(f"   ❌ 日付セッション設定失敗")
                return []
            
            # realtime.htmページ取得
            print(f"   🔄 realtime.htm修正版テーブル構造版アクセス中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(3)
            
            # ページソース取得・解析
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 修正版テーブル構造データ抽出
            extracted_data = self.extract_fixed_table_structure(soup, target_date)
            
            if extracted_data:
                attractions_found = len(set([item['attraction'] for item in extracted_data]))
                valid_data = len([item for item in extracted_data if item['wait_time'] is not None])
                print(f"   ✅ {len(extracted_data)}件のデータを抽出 ({attractions_found}アトラクション, 有効: {valid_data}件)")
                return extracted_data
            else:
                print(f"   ❌ データ抽出失敗")
                return []
                
        except Exception as e:
            print(f"   ❌ 修正版テーブル構造スクレイピングエラー: {e}")
            return []

    def set_date_session(self, target_date):
        """日付セッション設定（簡易版）"""
        try:
            self.driver.get("https://yosocal.com/")
            time.sleep(2)
            
            # 広告除去
            self.driver.execute_script("""
                var ads = document.querySelectorAll('iframe, [id*="ad"], [class*="ad"]');
                ads.forEach(function(ad) { ad.style.display = 'none'; ad.remove(); });
            """)
            
            # 日付クリック（簡易版）
            day_click_script = f"""
                var dayElements = document.querySelectorAll('div.CAL, div.CALSAT, div.CALSUN');
                for (var i = 0; i < dayElements.length; i++) {{
                    var text = dayElements[i].innerText || dayElements[i].textContent || '';
                    if (text.trim() === '{target_date.day}') {{
                        dayElements[i].click();
                        return true;
                    }}
                }}
                return false;
            """
            
            clicked = self.driver.execute_script(day_click_script)
            time.sleep(1)
            
            return True  # 簡易版では常にTrue
                
        except Exception as e:
            print(f"   ❌ セッション設定エラー: {e}")
            return False

    def extract_fixed_table_structure(self, soup, target_date):
        """修正版テーブル構造に基づく抽出"""
        data = []
        
        try:
            print(f"     🔍 修正版テーブル構造抽出開始...")
            
            # jamatテーブル検索
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                print(f"     ❌ jamatテーブルが見つかりません")
                return data
            
            # テーブル取得
            table = jamat_div.find('table')
            if not table:
                print(f"     ❌ テーブルが見つかりません")
                return data
            
            rows = table.find_all('tr')
            if len(rows) < 6:
                print(f"     ❌ テーブル行が不足: {len(rows)}行 (最低6行必要)")
                return data
            
            print(f"     📊 テーブル分析: {len(rows)}行検出")
            
            # 行5: アトラクション名行解析
            attraction_row = rows[5]
            attraction_cells = attraction_row.find_all(['td', 'th'])
            
            print(f"     🎢 アトラクション名行（行5）: {len(attraction_cells)}セル")
            
            # アトラクション名抽出（FPh2クラス）
            attractions_in_table = []
            for i, cell in enumerate(attraction_cells):
                cell_text = cell.get_text(strip=True)
                css_classes = ' '.join(cell.get('class', []))
                
                # FPh2クラスのセルのみ処理
                if 'FPh2' in css_classes and cell_text:
                    # アトラクション名正規化
                    normalized_name = self.normalize_attraction_name(cell_text)
                    attractions_in_table.append((i, normalized_name, cell_text))
            
            print(f"     🎢 検出されたアトラクション: {len(attractions_in_table)}個")
            for idx, (col_idx, attraction, original) in enumerate(attractions_in_table[:10]):
                print(f"         {idx+1}. 列{col_idx}: {attraction} ({original})")
            if len(attractions_in_table) > 10:
                print(f"         ... 他{len(attractions_in_table)-10}個")
            
            # データ行処理（行6以降=時間データ）
            for row_idx in range(6, len(rows)):
                row = rows[row_idx]
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # 時間セル取得（列0, FPMクラス）
                time_cell = cells[0]
                time_text = time_cell.get_text(strip=True)
                css_classes = ' '.join(time_cell.get('class', []))
                
                # FPMクラスかつ有効な時間のみ処理
                if 'FPM' not in css_classes:
                    continue
                
                # 時間パターンマッチング
                matched_time = self.match_time_pattern(time_text)
                if not matched_time:
                    continue
                
                print(f"     ⏰ 処理中: {matched_time} (行{row_idx}, セル数: {len(cells)})")
                
                # 各アトラクション列のデータ抽出
                for col_idx, attraction_name, original_name in attractions_in_table:
                    if col_idx < len(cells):
                        wait_time_cell = cells[col_idx]
                        wait_time, status = self.extract_wait_time(wait_time_cell)
                        
                        data.append({
                            'date': target_date.strftime("%m月%d日"),
                            'year': target_date.year,
                            'month': target_date.month,
                            'day': target_date.day,
                            'time': matched_time,
                            'attraction': attraction_name,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': ' '.join(wait_time_cell.get('class', [])),
                            'raw_value': wait_time_cell.get_text(strip=True),
                            'data_source': 'fixed_table_structure',
                            'table_position': f'行{row_idx}_列{col_idx}',
                            'original_attraction_name': original_name
                        })
                    else:
                        # セル不足の場合
                        data.append({
                            'date': target_date.strftime("%m月%d日"),
                            'year': target_date.year,
                            'month': target_date.month,
                            'day': target_date.day,
                            'time': matched_time,
                            'attraction': attraction_name,
                            'wait_time': None,
                            'status': 'cell_missing',
                            'css_classes': '',
                            'raw_value': '',
                            'data_source': 'fixed_table_structure',
                            'table_position': f'行{row_idx}_列{col_idx}_不足',
                            'original_attraction_name': original_name
                        })
            
            # 結果サマリー
            total_records = len(data)
            valid_records = len([item for item in data if item['wait_time'] is not None])
            unique_attractions = len(set([item['attraction'] for item in data]))
            unique_times = len(set([item['time'] for item in data]))
            
            print(f"     ✅ 抽出完了:")
            print(f"         📊 総レコード: {total_records}件")
            print(f"         ✅ 有効データ: {valid_records}件")
            print(f"         🎢 アトラクション: {unique_attractions}個")
            print(f"         ⏰ 時間帯: {unique_times}個")
            
            return data
            
        except Exception as e:
            print(f"     ❌ 修正版テーブル構造抽出エラー: {e}")
            return data

    def normalize_attraction_name(self, text):
        """アトラクション名正規化"""
        if not text:
            return text
        
        # 特殊文字置換
        replacements = {
            '｜': '',
            'Ｓ': 'S',
            'リバ｜鉄道': 'ウエスタンリバー鉄道',
            'ツリ｜ハウス': 'ツリーハウス',
            '魅惑のチキル｜ム': '魅惑のチキルーム',
            'ビッグサンダ｜': 'ビッグサンダーマウンテン',
            'Ｓギャラリ｜': 'シューティングギャラリー',
            'ベア・シアタ｜': 'カントリーベアシアター',
            'いかだ': 'トムソーヤ島いかだ',
            '蒸気船': '蒸気船マークトゥウェイン号',
            'カヌ｜探検': 'ビーバーブラザーズのカヌー探検',
            'スモ｜ルワ｜ルド': 'イッツァスモールワールド',
            'ハニ｜ハント': 'プーさんのハニーハント'
        }
        
        normalized = text
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized.strip()

    def match_time_pattern(self, text):
        """時間パターンマッチング"""
        if not text:
            return None
        
        text = text.strip()
        
        # 平均チェック
        if text in ['平均', 'AVG', 'Average', '平均値']:
            return '平均'
        
        # 時間パターン（HH:MM）
        time_match = re.match(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            formatted_time = f"{hour:02d}:{minute:02d}"
            
            # 対象時間帯チェック
            if formatted_time in self.target_times:
                return formatted_time
        
        return None

    def extract_wait_time(self, cell):
        """待ち時間抽出（改良版）"""
        try:
            cell_text = cell.get_text(strip=True)
            css_classes = ' '.join(cell.get('class', []))
            
            # 空セルチェック
            if not cell_text:
                return None, "empty"
            
            # 数値直接抽出
            if cell_text.isdigit():
                wait_time = int(cell_text)
                if 1 <= wait_time <= 300:
                    return wait_time, "normal"
            
            # 運休・休止チェック
            if cell_text in ['-', '---', '休止', '運休', 'CLOSE', 'X', '×']:
                return None, "closed"
            
            # レベル文字からの推定
            level_mapping = {
                'S': 80,   # Super busy
                'A': 60,   # Very busy
                'B': 40,   # Busy
                'C': 20,   # Medium
                'D': 10,   # Light
                'E': 5     # Very light
            }
            
            if cell_text in level_mapping:
                return level_mapping[cell_text], "level_estimation"
            
            # CSSクラスからの推定（B0-B8）
            if css_classes:
                for cls in cell.get('class', []):
                    if cls.startswith('B') and len(cls) == 2 and cls[1].isdigit():
                        level = int(cls[1])
                        # B0=5分, B1=15分, B2=25分, ..., B8=85分程度
                        estimated_time = max(5, level * 10 + 5)
                        return estimated_time, "css_estimation"
            
            # テキスト内数値抽出
            numbers = re.findall(r'\d+', cell_text)
            if numbers:
                for num_str in numbers:
                    num = int(num_str)
                    if 1 <= num <= 300:
                        return num, "text_extraction"
            
            return None, "no_data"
            
        except Exception:
            return None, "error"

    def save_fixed_table_data(self, target_date, data):
        """修正版テーブル構造データ保存"""
        if not data:
            print(f"   📁 {target_date}: データなし、保存スキップ")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(self.data_dir, f"yosocal_fixed_table_{target_date.strftime('%Y_%m_%d')}_{timestamp}.csv")
        
        # CSV保存
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 
                        'wait_time', 'status', 'css_classes', 'raw_value', 'data_source',
                        'table_position', 'original_attraction_name']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in data:
                writer.writerow(record)
        
        # 統計計算
        valid_count = len([item for item in data if item['wait_time'] is not None])
        attractions_found = len(set([item['attraction'] for item in data]))
        times_found = len(set([item['time'] for item in data]))
        
        print(f"   💾 保存完了: {len(data)}件 (有効: {valid_count}件)")
        print(f"       🎢 アトラクション: {attractions_found}個")
        print(f"       ⏰ 時間帯: {times_found}個")
        print(f"       📁 保存先: {csv_filename}")
        
        return csv_filename

    def test_fixed_table_structure(self, test_date=None):
        """修正版テーブル構造テスト実行"""
        if test_date is None:
            test_date = date.today()
        
        print(f"🧪 修正版テーブル構造テスト実行")
        print(f"📅 テスト日付: {test_date}")
        print(f"⏰ 対象時間帯: {len(self.target_times)}個")
        print("=" * 70)
        
        # WebDriverセットアップ
        if not self.setup_driver():
            print("❌ WebDriverセットアップに失敗しました")
            return
        
        try:
            # データ取得
            extracted_data = self.scrape_fixed_table_data(test_date)
            
            if extracted_data:
                # データ保存
                csv_file = self.save_fixed_table_data(test_date, extracted_data)
                
                print(f"\n📊 テスト結果サマリー:")
                print(f"   ✅ 成功: {len(extracted_data)}件のデータを取得")
                print(f"   📁 保存ファイル: {os.path.basename(csv_file)}")
                
                # 詳細統計
                attractions = set([item['attraction'] for item in extracted_data])
                times = set([item['time'] for item in extracted_data])
                valid_data = [item for item in extracted_data if item['wait_time'] is not None]
                
                print(f"\n📈 詳細統計:")
                print(f"   🎢 検出アトラクション: {len(attractions)}個")
                print(f"   ⏰ 検出時間帯: {len(times)}個")
                print(f"   ✅ 有効データ: {len(valid_data)}件")
                
                # アトラクション一覧表示
                print(f"\n🎢 検出されたアトラクション:")
                for i, attraction in enumerate(sorted(attractions), 1):
                    print(f"   {i:2d}. {attraction}")
                
                # 時間帯一覧表示
                print(f"\n⏰ 検出された時間帯:")
                sorted_times = sorted([t for t in times if t != '平均']) + (['平均'] if '平均' in times else [])
                for i, time_slot in enumerate(sorted_times, 1):
                    print(f"   {i:2d}. {time_slot}")
                
            else:
                print("❌ データ取得に失敗しました")
        
        finally:
            if self.driver:
                print("\n🔧 WebDriver終了")
                self.driver.quit()

def main():
    """メイン実行"""
    scraper = YosocalFixedTableStructureScraper()
    
    # テスト実行
    print("🔧 修正版テーブル構造対応版 テスト開始")
    scraper.test_fixed_table_structure()

if __name__ == "__main__":
    main() 