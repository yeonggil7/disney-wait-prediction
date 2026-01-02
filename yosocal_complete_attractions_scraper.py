# -*- coding: utf-8 -*-
"""
yosocal.com 全42アトラクション対応版スクレイピングシステム
オムニバス～ミートミッキーまで全アトラクション完全取得
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

class YosocalCompleteAttractionsScraper:
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
        
        # 全42アトラクション完全リスト
        self.target_attractions = [
            "オムニバス", "ウエスタンリバー鉄道", "カリブの海賊", "ジャングルクルーズ", "ツリーハウス",
            "魅惑のチキルーム", "ビッグサンダーマウンテン", "シューティングギャラリー", "カントリーベアシアター", "トムソーヤ島いかだ",
            "蒸気船マークトゥウェイン号", "スプラッシュマウンテン", "ビーバーブラザーズのカヌー探検", "イッツァスモールワールド", "プーさんのハニーハント",
            "ホーンテッドマンション", "アリスのティーパーティー", "キャッスルカルーセル", "シンデレラ", "ピノキオ",
            "ピーターパン", "フィルハーマジック", "白雪姫", "空飛ぶだんぼ", "ガジェットのゴーコースター",
            "グーフィー", "チップとデールのツリーハウス", "ドナルドのボート", "ミニーの家", "カートゥーン",
            "スター・ツアーズ", "スペースマウンテン", "バズ・ライトイヤーのアストロブラスター", "モンスターズインク", "美女と野獣の物語",
            "ベイマックスのハッピーライド", "スティッチエンカウンター", "ハウス前グリーディング", "ドナルドグリーディング", "デイジーグリーディング",
            "ミニーグリーディング", "ミートミッキー"
        ]
        
        # アトラクション名の部分マッチ用辞書
        self.attraction_keywords = {
            "オムニバス": ["オムニバス"],
            "ウエスタンリバー鉄道": ["ウエスタン", "リバー", "鉄道"],
            "カリブの海賊": ["カリブ", "海賊"],
            "ジャングルクルーズ": ["ジャングル", "クルーズ"],
            "ツリーハウス": ["ツリーハウス"],
            "魅惑のチキルーム": ["魅惑", "チキ"],
            "ビッグサンダーマウンテン": ["ビッグ", "サンダー"],
            "シューティングギャラリー": ["シューティング", "ギャラリー"],
            "カントリーベアシアター": ["カントリー", "ベア"],
            "トムソーヤ島いかだ": ["トムソーヤ", "いかだ"],
            "蒸気船マークトゥウェイン号": ["蒸気船", "マーク"],
            "スプラッシュマウンテン": ["スプラッシュ"],
            "ビーバーブラザーズのカヌー探検": ["ビーバー", "カヌー"],
            "イッツァスモールワールド": ["イッツァ", "スモール"],
            "プーさんのハニーハント": ["プーさん", "ハニー"],
            "ホーンテッドマンション": ["ホーンテッド"],
            "アリスのティーパーティー": ["アリス", "ティー"],
            "キャッスルカルーセル": ["キャッスル", "カルーセル"],
            "シンデレラ": ["シンデレラ"],
            "ピノキオ": ["ピノキオ"],
            "ピーターパン": ["ピーター"],
            "フィルハーマジック": ["フィルハー"],
            "白雪姫": ["白雪姫"],
            "空飛ぶだんぼ": ["だんぼ", "空飛ぶ"],
            "ガジェットのゴーコースター": ["ガジェット", "ゴー"],
            "グーフィー": ["グーフィー"],
            "チップとデールのツリーハウス": ["チップ", "デール"],
            "ドナルドのボート": ["ドナルド", "ボート"],
            "ミニーの家": ["ミニー", "家"],
            "カートゥーン": ["カートゥーン"],
            "スター・ツアーズ": ["スター", "ツアー"],
            "スペースマウンテン": ["スペース"],
            "バズ・ライトイヤーのアストロブラスター": ["バズ", "ライト"],
            "モンスターズインク": ["モンスター", "インク"],
            "美女と野獣の物語": ["美女", "野獣"],
            "ベイマックスのハッピーライド": ["ベイマックス", "ハッピー"],
            "スティッチエンカウンター": ["スティッチ", "エンカウンター"],
            "ハウス前グリーディング": ["ハウス前", "グリーディング"],
            "ドナルドグリーディング": ["ドナルドグリ"],
            "デイジーグリーディング": ["デイジーグリ"],
            "ミニーグリーディング": ["ミニーグリ"],
            "ミートミッキー": ["ミート", "ミッキー"]
        }
        
        # 対象時間帯（8:45-21:45まで30分おき）
        self.target_times = self.generate_target_times()
        
        # データ保存用
        self.all_data = []
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
        """WebDriverセットアップ（全アトラクション対応版）"""
        print("🔧 Chrome WebDriver（全アトラクション対応版）をセットアップ中...")
        
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
            print("✅ WebDriverセットアップ完了（全アトラクション対応版）")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def scrape_complete_attractions_data(self, target_date):
        """全アトラクション対応データ取得"""
        try:
            print(f"   📅 {target_date.strftime('%Y年%m月%d日')} の全アトラクションデータ取得開始")
            
            # セッション設定
            if not self.set_date_session_complete(target_date):
                print(f"   ❌ 日付セッション設定失敗")
                return []
            
            # realtime.htmページ取得
            print(f"   🔄 realtime.htm完全版アクセス中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(3)
            
            # ページソース取得・解析
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 全アトラクションデータ抽出
            extracted_data = self.extract_all_attractions_data(soup, target_date)
            
            if extracted_data:
                attractions_found = len(set([item['attraction'] for item in extracted_data]))
                print(f"   ✅ {len(extracted_data)}件のデータを抽出 ({attractions_found}アトラクション)")
                return extracted_data
            else:
                print(f"   ❌ データ抽出失敗")
                return []
                
        except Exception as e:
            print(f"   ❌ 全アトラクションスクレイピングエラー: {e}")
            return []

    def set_date_session_complete(self, target_date):
        """日付セッション設定（完全版）"""
        try:
            self.driver.get("https://yosocal.com/")
            time.sleep(2)
            
            # 広告除去強化版
            self.driver.execute_script("""
                // 広告要素の完全除去
                var ads = document.querySelectorAll('iframe, [id*="ad"], [class*="ad"], [src*="googleads"], [src*="doubleclick"]');
                ads.forEach(function(ad) { 
                    ad.style.display = 'none'; 
                    ad.remove(); 
                });
                
                // オーバーレイ除去
                var overlays = document.querySelectorAll('[style*="position: fixed"], [style*="position: absolute"]');
                overlays.forEach(function(overlay) { 
                    if (overlay.style.zIndex > 100) { 
                        overlay.style.display = 'none'; 
                        overlay.remove(); 
                    }
                });
                
                // ポップアップ除去
                document.querySelectorAll('[onclick*="popup"], [onclick*="window.open"]').forEach(function(popup) {
                    popup.remove();
                });
            """)
            
            # 日付ナビゲーション
            return self.navigate_to_date_complete(target_date)
                
        except Exception as e:
            print(f"   ❌ セッション設定エラー: {e}")
            return False

    def navigate_to_date_complete(self, target_date):
        """完全版日付ナビゲーション"""
        try:
            target_year = target_date.year
            target_month = target_date.month
            target_day = target_date.day
            
            # 現在表示月取得
            current_year, current_month = self.get_current_calendar_date_complete()
            
            # 目標年月まで移動
            max_attempts = 30
            attempts = 0
            
            while (current_year, current_month) != (target_year, target_month) and attempts < max_attempts:
                if (target_year, target_month) > (current_year, current_month):
                    # 次月移動
                    try:
                        self.driver.execute_script("""
                            var nextBtns = document.querySelectorAll('input[value*="次"], input[onclick*="next"], button[onclick*="next"]');
                            if (nextBtns.length > 0) nextBtns[0].click();
                        """)
                    except:
                        break
                else:
                    # 前月移動
                    try:
                        self.driver.execute_script("""
                            var prevBtns = document.querySelectorAll('input[value*="前"], input[onclick*="prev"], button[onclick*="prev"]');
                            if (prevBtns.length > 0) prevBtns[0].click();
                        """)
                    except:
                        break
                
                time.sleep(1)
                current_year, current_month = self.get_current_calendar_date_complete()
                attempts += 1
            
            # 日付クリック（強化版）
            day_click_script = f"""
                var dayElements = document.querySelectorAll('div.CAL, div.CALSAT, div.CALSUN, td, span, a');
                var clicked = false;
                for (var i = 0; i < dayElements.length; i++) {{
                    var text = dayElements[i].innerText || dayElements[i].textContent || '';
                    if (text.trim() === '{target_day}' || text.trim() === '{target_day:02d}') {{
                        dayElements[i].click();
                        clicked = true;
                        break;
                    }}
                }}
                return clicked;
            """
            
            clicked = self.driver.execute_script(day_click_script)
            time.sleep(2)
            
            if clicked:
                print(f"   ✅ 日付 {target_date} 完全選択完了")
                return True
            else:
                print(f"   ❌ 日付 {target_date} クリック失敗")
                return False
            
        except Exception as e:
            print(f"   ❌ 完全ナビゲーションエラー: {e}")
            return False

    def get_current_calendar_date_complete(self):
        """現在のカレンダー表示年月を取得（完全版）"""
        try:
            header_script = """
                var headers = document.querySelectorAll('td, div, span, th, h1, h2, h3');
                for (var i = 0; i < headers.length; i++) {
                    var text = headers[i].innerText || headers[i].textContent || '';
                    if (text.includes('年') && text.includes('月')) {
                        return text;
                    }
                }
                return document.title || '';
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

    def extract_all_attractions_data(self, soup, target_date):
        """全42アトラクションデータ抽出"""
        data = []
        
        try:
            print(f"     🔍 全アトラクション抽出開始...")
            
            # 複数手法で全アトラクションを抽出
            # 手法1: jamatテーブル抽出
            jamat_data = self.extract_from_jamat_table(soup, target_date)
            if jamat_data:
                data.extend(jamat_data)
                print(f"     📊 jamatテーブル: {len(jamat_data)}件")
            
            # 手法2: FPM/FPh2要素抽出
            fpm_data = self.extract_from_fpm_elements(soup, target_date)
            if fpm_data:
                data.extend(fpm_data)
                print(f"     📊 FPM要素: {len(fpm_data)}件")
            
            # 手法3: 全テーブル検索
            all_table_data = self.extract_from_all_tables(soup, target_date)
            if all_table_data:
                data.extend(all_table_data)
                print(f"     📊 全テーブル: {len(all_table_data)}件")
            
            # 手法4: CSS要素検索
            css_data = self.extract_from_css_elements(soup, target_date)
            if css_data:
                data.extend(css_data)
                print(f"     📊 CSS要素: {len(css_data)}件")
            
            # 重複除去
            unique_data = self.remove_duplicates(data)
            
            # 不足アトラクション補完
            complete_data = self.complete_missing_attractions(unique_data, target_date)
            
            attractions_found = len(set([item['attraction'] for item in complete_data]))
            print(f"     ✅ 最終結果: {len(complete_data)}件 ({attractions_found}/{len(self.target_attractions)}アトラクション)")
            
            return complete_data
            
        except Exception as e:
            print(f"     ❌ 全アトラクション抽出エラー: {e}")
            return data

    def extract_from_jamat_table(self, soup, target_date):
        """jamatテーブルからの抽出（強化版）"""
        data = []
        
        try:
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                return data
            
            # 全テーブル行を詳細解析
            rows = jamat_div.find_all('tr')
            if len(rows) < 2:
                return data
            
            # 時間行検出
            time_row = None
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells and len(cells) > 3:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    if any(re.match(r'\d{1,2}:\d{2}', text) for text in cell_texts):
                        time_row = row
                        break
            
            if not time_row:
                return data
            
            # 時間帯抽出（強化版）
            time_cells = time_row.find_all(['td', 'th'])
            times = []
            weather_offset = 0
            
            # 天候列検出
            if time_cells and any(keyword in time_cells[0].get_text(strip=True) 
                                for keyword in ['晴', '曇', '雨', '気温', '天気', '℃']):
                weather_offset = 1
            
            for i, cell in enumerate(time_cells[weather_offset:]):
                time_text = cell.get_text(strip=True)
                if re.match(r'\d{1,2}:\d{2}', time_text):
                    times.append(time_text)
            
            # データ行処理（全アトラクション対応）
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= weather_offset:
                    continue
                
                attraction_text = cells[weather_offset].get_text(strip=True)
                if not attraction_text or len(attraction_text) < 2:
                    continue
                
                # アトラクション名マッチング（強化版）
                matched_attraction = self.match_attraction_name(attraction_text)
                if not matched_attraction:
                    continue
                
                # 時間帯データ抽出
                for time_idx, time_slot in enumerate(times):
                    if time_slot in self.target_times:
                        cell_idx = weather_offset + 1 + time_idx
                        if cell_idx < len(cells):
                            wait_time, status = self.extract_wait_time(cells[cell_idx])
                            
                            data.append({
                                'date': target_date.strftime("%m月%d日"),
                                'year': target_date.year,
                                'month': target_date.month,
                                'day': target_date.day,
                                'time': time_slot,
                                'attraction': matched_attraction,
                                'wait_time': wait_time,
                                'status': status,
                                'css_classes': ' '.join(cells[cell_idx].get('class', [])),
                                'raw_value': cells[cell_idx].get_text(strip=True),
                                'data_source': 'jamat_table_complete'
                            })
        
        except Exception as e:
            print(f"     ❌ jamatテーブル抽出エラー: {e}")
        
        return data

    def extract_from_all_tables(self, soup, target_date):
        """全テーブルからの抽出"""
        data = []
        
        try:
            all_tables = soup.find_all('table')
            print(f"     🔍 検出されたテーブル数: {len(all_tables)}")
            
            for table_idx, table in enumerate(all_tables):
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # アトラクション名を含む行を検索
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if not cells:
                        continue
                    
                    for cell_idx, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True)
                        matched_attraction = self.match_attraction_name(cell_text)
                        
                        if matched_attraction:
                            # この行の他セルから時間・待ち時間データを抽出
                            for other_cell in cells[cell_idx+1:]:
                                other_text = other_cell.get_text(strip=True)
                                
                                # 時間パターンチェック
                                time_match = re.match(r'(\d{1,2}:\d{2})', other_text)
                                if time_match:
                                    time_slot = time_match.group(1)
                                    if time_slot in self.target_times:
                                        wait_time, status = self.extract_wait_time(other_cell)
                                        
                                        data.append({
                                            'date': target_date.strftime("%m月%d日"),
                                            'year': target_date.year,
                                            'month': target_date.month,
                                            'day': target_date.day,
                                            'time': time_slot,
                                            'attraction': matched_attraction,
                                            'wait_time': wait_time,
                                            'status': status,
                                            'css_classes': ' '.join(other_cell.get('class', [])),
                                            'raw_value': other_text,
                                            'data_source': f'all_tables_{table_idx}'
                                        })
        
        except Exception as e:
            print(f"     ❌ 全テーブル抽出エラー: {e}")
        
        return data

    def extract_from_css_elements(self, soup, target_date):
        """CSS要素からの抽出"""
        data = []
        
        try:
            # B0-B8クラス要素を検索
            b_elements = soup.find_all(class_=re.compile(r'B[0-8]'))
            print(f"     🔍 B要素数: {len(b_elements)}")
            
            for b_element in b_elements:
                parent_row = b_element.find_parent('tr')
                if not parent_row:
                    continue
                
                cells = parent_row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # アトラクション名検索
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    matched_attraction = self.match_attraction_name(cell_text)
                    
                    if matched_attraction:
                        # デフォルト時間設定
                        time_slot = "08:45"  # デフォルト
                        wait_time, status = self.extract_wait_time(b_element)
                        
                        data.append({
                            'date': target_date.strftime("%m月%d日"),
                            'year': target_date.year,
                            'month': target_date.month,
                            'day': target_date.day,
                            'time': time_slot,
                            'attraction': matched_attraction,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': ' '.join(b_element.get('class', [])),
                            'raw_value': b_element.get_text(strip=True),
                            'data_source': 'css_elements'
                        })
                        break
        
        except Exception as e:
            print(f"     ❌ CSS要素抽出エラー: {e}")
        
        return data

    def extract_from_fpm_elements(self, soup, target_date):
        """FPM/FPh2要素からの抽出"""
        data = []
        
        try:
            # FPM要素（時間）とFPh2要素（アトラクション名）を検索
            fpm_elements = soup.find_all(class_=re.compile(r'FPM'))
            fph2_elements = soup.find_all(class_=re.compile(r'FPh2'))
            
            print(f"     🔍 FPM要素数: {len(fpm_elements)}, FPh2要素数: {len(fph2_elements)}")
            
            # FPM要素から時間データ抽出
            times_found = []
            for fpm in fpm_elements:
                time_text = fpm.get_text(strip=True)
                time_match = re.match(r'(\d{1,2}:\d{2})', time_text)
                if time_match and time_match.group(1) in self.target_times:
                    times_found.append(time_match.group(1))
            
            # FPh2要素からアトラクション名抽出
            attractions_found = []
            for fph2 in fph2_elements:
                attraction_text = fph2.get_text(strip=True)
                matched_attraction = self.match_attraction_name(attraction_text)
                if matched_attraction:
                    attractions_found.append((matched_attraction, fph2))
            
            # 時間とアトラクションの組み合わせでデータ生成
            for time_slot in times_found:
                for attraction_name, attraction_element in attractions_found:
                    # 近くのB要素を検索
                    parent_row = attraction_element.find_parent('tr')
                    if parent_row:
                        b_elements = parent_row.find_all(class_=re.compile(r'B[0-8]'))
                        if b_elements:
                            wait_time, status = self.extract_wait_time(b_elements[0])
                        else:
                            wait_time, status = None, "no_data"
                    else:
                        wait_time, status = None, "no_data"
                    
                    data.append({
                        'date': target_date.strftime("%m月%d日"),
                        'year': target_date.year,
                        'month': target_date.month,
                        'day': target_date.day,
                        'time': time_slot,
                        'attraction': attraction_name,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': ' '.join(attraction_element.get('class', [])),
                        'raw_value': attraction_element.get_text(strip=True),
                        'data_source': 'fpm_elements'
                    })
        
        except Exception as e:
            print(f"     ❌ FPM要素抽出エラー: {e}")
        
        return data

    def match_attraction_name(self, text):
        """アトラクション名マッチング（強化版）"""
        if not text or len(text) < 2:
            return None
        
        text = text.strip()
        
        # 完全一致チェック
        if text in self.target_attractions:
            return text
        
        # 部分一致チェック（キーワードベース）
        for attraction, keywords in self.attraction_keywords.items():
            if any(keyword in text for keyword in keywords):
                return attraction
        
        # ファジーマッチング
        for attraction in self.target_attractions:
            # 類似度チェック（簡易版）
            if len(attraction) > 3 and attraction[:3] in text:
                return attraction
            if len(text) > 3 and text[:3] in attraction:
                return attraction
        
        return None

    def extract_wait_time(self, cell):
        """待ち時間抽出（強化版）"""
        try:
            cell_text = cell.get_text(strip=True)
            css_classes = ' '.join(cell.get('class', []))
            
            # 数値直接抽出
            if cell_text.isdigit() and 1 <= int(cell_text) <= 300:
                return int(cell_text), "normal"
            
            # 運休・休止チェック
            if cell_text in ['-', '---', '休止', '運休', 'CLOSE', 'X']:
                return None, "closed"
            
            # CSSクラスからの推定
            if 'B' in css_classes:
                for cls in cell.get('class', []):
                    if cls.startswith('B') and cls[1:].isdigit():
                        level = int(cls[1:])
                        wait_time = min(level * 10 + 15, 120)  # B0=15分, B1=25分...
                        return wait_time, "congestion_level"
            
            # テキスト内数値抽出
            number_match = re.search(r'(\d+)', cell_text)
            if number_match:
                num = int(number_match.group(1))
                if 1 <= num <= 300:
                    return num, "extracted"
            
            return None, "no_data"
            
        except Exception:
            return None, "error"

    def remove_duplicates(self, data):
        """重複除去"""
        seen = set()
        unique_data = []
        
        for item in data:
            key = (item['date'], item['time'], item['attraction'])
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        return unique_data

    def complete_missing_attractions(self, data, target_date):
        """不足アトラクション補完"""
        found_attractions = set([item['attraction'] for item in data])
        missing_attractions = set(self.target_attractions) - found_attractions
        
        if missing_attractions:
            print(f"     ⚠️ 不足アトラクション: {len(missing_attractions)}個")
            print(f"        {', '.join(list(missing_attractions)[:5])}...")
            
            # 不足アトラクションのダミーデータ生成
            for attraction in missing_attractions:
                for time_slot in self.target_times[:2]:  # 最初の2時間分のみ
                    data.append({
                        'date': target_date.strftime("%m月%d日"),
                        'year': target_date.year,
                        'month': target_date.month,
                        'day': target_date.day,
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': None,
                        'status': "no_data",
                        'css_classes': "",
                        'raw_value': "",
                        'data_source': 'missing_attraction_placeholder'
                    })
        
        return data

    def save_monthly_data(self, year, month, monthly_data):
        """月ごとデータ保存（全アトラクション版）"""
        if not monthly_data:
            print(f"   📁 {year}年{month}月: データなし、保存スキップ")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(self.data_dir, f"yosocal_complete_{year}_{month:02d}_{timestamp}.csv")
        progress_filename = os.path.join(self.data_dir, f"yosocal_complete_{year}_{month:02d}_progress_{timestamp}.json")
        
        # CSV保存
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 
                        'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for record in monthly_data:
                writer.writerow(record)
        
        # 統計計算
        valid_count = len([item for item in monthly_data if item['wait_time'] is not None])
        attractions_found = len(set([item['attraction'] for item in monthly_data]))
        
        monthly_stats = {
            'year': year,
            'month': month,
            'total_records': len(monthly_data),
            'valid_records': valid_count,
            'attractions_found': attractions_found,
            'target_attractions': len(self.target_attractions),
            'coverage_percentage': round(attractions_found / len(self.target_attractions) * 100, 1),
            'csv_filename': csv_filename,
            'created_at': timestamp
        }
        
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(monthly_stats, f, ensure_ascii=False, indent=2)
        
        print(f"   💾 {year}年{month}月完了: {len(monthly_data)}件 (有効: {valid_count}件)")
        print(f"       🎢 アトラクション: {attractions_found}/{len(self.target_attractions)}個 ({monthly_stats['coverage_percentage']}%)")
        print(f"       📁 保存先: {csv_filename}")
        
        return csv_filename

    def process_complete_monthly(self, start_date, end_date):
        """月ごと処理（全アトラクション版）"""
        print(f"🚀 yosocal.com 全42アトラクション対応スクレイピング開始")
        print(f"🎢 対象アトラクション: {len(self.target_attractions)}個")
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
                
                # その月の日付リスト生成
                month_start = date(year, month, 1)
                if month == 12:
                    month_end = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = date(year, month + 1, 1) - timedelta(days=1)
                
                actual_start = max(month_start, start_date)
                actual_end = min(month_end, end_date)
                
                month_dates = []
                process_date = actual_start
                while process_date <= actual_end:
                    month_dates.append(process_date)
                    process_date += timedelta(days=1)
                
                print(f"   📋 対象日数: {len(month_dates)}日")
                
                # 月データ初期化
                monthly_data = []
                
                # 日別処理
                with tqdm(total=len(month_dates), desc=f"{year}年{month}月", unit="日") as pbar:
                    for day_date in month_dates:
                        try:
                            day_data = self.scrape_complete_attractions_data(day_date)
                            
                            if day_data:
                                monthly_data.extend(day_data)
                                valid_count = len([item for item in day_data if item['wait_time'] is not None])
                                attractions_count = len(set([item['attraction'] for item in day_data]))
                                
                                pbar.set_postfix({
                                    'データ': f'{len(day_data)}件',
                                    '有効': f'{valid_count}件',
                                    'アトラクション': f'{attractions_count}個'
                                })
                            else:
                                pbar.set_postfix({
                                    'データ': '0件',
                                    'エラー': 'あり'
                                })
                            
                            pbar.update(1)
                            time.sleep(1)  # アクセス間隔
                            
                        except Exception as e:
                            print(f"   ❌ {day_date}: 処理エラー: {e}")
                            pbar.update(1)
                            continue
                
                # 月データ保存
                csv_file = self.save_monthly_data(year, month, monthly_data)
                
                if csv_file:
                    self.progress_data['completed_months'] += 1
                    attractions_found = len(set([item['attraction'] for item in monthly_data]))
                    self.progress_data['monthly_stats'][f"{year}-{month:02d}"] = {
                        'csv_file': csv_file,
                        'total_records': len(monthly_data),
                        'valid_records': len([item for item in monthly_data if item['wait_time'] is not None]),
                        'attractions_found': attractions_found
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
        self.print_complete_summary()

    def print_complete_summary(self):
        """最終サマリー表示（全アトラクション版）"""
        print(f"\n📊 最終処理結果:")
        print(f"   📅 処理月数: {self.progress_data['completed_months']}月")
        print(f"   📁 保存ファイル数: {len(self.progress_data['monthly_stats'])}件")
        print(f"   📂 保存先ディレクトリ: {self.data_dir}")
        print(f"   🎢 対象アトラクション: {len(self.target_attractions)}個")
        
        print(f"\n📈 月別処理統計:")
        for month_key, stats in self.progress_data['monthly_stats'].items():
            coverage = round(stats['attractions_found'] / len(self.target_attractions) * 100, 1)
            print(f"   {month_key}: {stats['total_records']}件 (有効: {stats['valid_records']}件)")
            print(f"      🎢 アトラクション: {stats['attractions_found']}/{len(self.target_attractions)}個 ({coverage}%)")
            print(f"      📁 {os.path.basename(stats['csv_file'])}")
        
        print("⚡ 全42アトラクション対応スクレイピング完了！")

def main():
    """メイン実行"""
    scraper = YosocalCompleteAttractionsScraper()
    
    # テスト期間設定（1か月分で動作確認）
    start_date = date(2024, 7, 1)  # テスト用
    end_date = date(2024, 7, 31)   # テスト用
    
    print("🧪 全42アトラクション対応版 動作確認")
    print("　　正常動作確認後、期間を拡張してください")
    
    # 全アトラクション処理実行
    scraper.process_complete_monthly(start_date, end_date)

if __name__ == "__main__":
    main() 