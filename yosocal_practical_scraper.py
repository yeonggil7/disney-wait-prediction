#!/usr/bin/env python3
"""
yosocal.com 実用的スクレイピングシステム
実際のサイト構造に基づいて効率的にデータを取得
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    return driver

def get_attraction_list():
    """ディズニーランドアトラクション一覧（42個）"""
    return {
        1: 'オムニバス',
        2: 'ウエスタンリバー鉄道', 
        3: 'カリブの海賊',
        4: 'ジャングルクルーズ',
        5: 'ツリーハウス',
        6: '魅惑のチキルーム',
        7: 'ビッグサンダーマウンテン',
        8: 'シューティングギャラリー',
        9: 'カントリーベアシアター',
        10: 'トムソーヤ島いかだ',
        11: '蒸気船マークトゥウェイン号',
        12: 'スプラッシュマウンテン',
        13: 'ビーバーブラザーズのカヌー探検',
        14: 'イッツ・ア・スモールワールド',
        15: 'プーさんのハニーハント',
        16: 'ホーンテッドマンション',
        17: 'アリスのティーパーティー',
        18: 'キャッスルカルーセル',
        19: 'シンデレラのフェアリーテイル・ホール',
        20: 'ピノキオの冒険旅行',
        21: 'ピーターパン空の旅',
        22: 'ミッキーのフィルハーマジック',
        23: '白雪姫と七人のこびと',
        24: '空飛ぶダンボ',
        25: 'ガジェットのゴーコースター',
        26: 'グーフィーのペイント&プレイハウス',
        27: 'チップとデールのツリーハウス',
        28: 'ドナルドのボート',
        29: 'ミニーの家',
        30: 'カートゥーンスピン',
        31: 'スター・ツアーズ',
        32: 'スペースマウンテン',
        33: 'バズ・ライトイヤーのアストロブラスター',
        34: 'モンスターズ・インク',
        35: '美女と野獣の物語',
        36: 'ベイマックスのハッピーライド',
        37: 'スティッチ・エンカウンター',
        38: 'ハウス前グリーティング',
        39: 'ドナルドグリーティング',
        40: 'デイジーグリーティング',
        41: 'ミニーグリーティング',
        42: 'ミート・ミッキー'
    }

class YosocalPracticalScraper:
    def __init__(self):
        self.driver = None
        self.attractions = get_attraction_list()
        self.data = []
        self.base_url = "https://yosocal.com/realtime.htm"
        
    def start_driver(self):
        """WebDriverを開始"""
        self.driver = setup_driver()
        print("🚀 WebDriver開始")
        
    def stop_driver(self):
        """WebDriverを終了"""
        if self.driver:
            self.driver.quit()
            print("🛑 WebDriver終了")
            
    def navigate_to_site(self):
        """サイトにアクセス"""
        print(f"🌐 アクセス中: {self.base_url}")
        self.driver.get(self.base_url)
        
        # ページロード待機
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ ページロード完了")
        
    def get_current_month_info(self):
        """現在表示されている月の情報を取得"""
        try:
            current_year = self.driver.execute_script("return zzDate ? zzDate.getFullYear() : null;")
            current_month = self.driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : null;")
            
            if current_year and current_month:
                return current_year, current_month
            else:
                return None, None
                
        except Exception as e:
            print(f"❌ 現在月取得エラー: {e}")
            return None, None
            
    def navigate_to_month(self, target_year, target_month):
        """指定月に移動"""
        print(f"📅 {target_year}年{target_month}月に移動中...")
        
        max_attempts = 24  # 最大24回の移動
        
        for attempt in range(max_attempts):
            try:
                current_year, current_month = self.get_current_month_info()
                
                if not current_year or not current_month:
                    print("❌ 現在月の取得に失敗")
                    return False
                
                print(f"  現在: {current_year}年{current_month}月")
                
                if current_year == target_year and current_month == target_month:
                    print(f"✅ 目標月 {target_year}年{target_month}月 に到達")
                    # 月移動後のページ更新を待機
                    print("⏳ ページ更新待機中...")
                    time.sleep(5)  # JavaScript実行とDOM更新を待機
                    return True
                
                # 前月または次月ボタンをクリック
                if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                    # 前月ボタン
                    prev_btn = self.driver.find_element(By.XPATH, "//input[@value='前月']")
                    prev_btn.click()
                    print("  ← 前月へ移動")
                else:
                    # 次月ボタン
                    next_btn = self.driver.find_element(By.XPATH, "//input[@value='次月']")
                    next_btn.click()
                    print("  → 次月へ移動")
                
                time.sleep(5)  # 移動後の待機を長く
                
            except Exception as e:
                print(f"❌ 月移動エラー: {e}")
                return False
                
        print(f"❌ {max_attempts}回試行後も目標月に到達できませんでした")
        return False
        
    def get_current_day_info(self):
        """現在表示されている日の情報を取得"""
        try:
            # 複数の方法で日付を取得
            methods = [
                self._get_date_from_tdbt_elements,
                self._get_date_from_javascript,
                self._get_date_from_page_content
            ]
            
            for method in methods:
                try:
                    date_result = method()
                    if date_result:
                        print(f"📅 日付取得成功: {date_result}")
                        return date_result
                except Exception as e:
                    print(f"  日付取得方法失敗: {e}")
                    continue
            
            # すべて失敗した場合は月情報から推定
            current_year, current_month = self.get_current_month_info()
            if current_year and current_month:
                estimated_date = f"{current_year}-{current_month:02d}-01"
                print(f"📅 日付推定: {estimated_date}")
                return estimated_date
            
            return None
            
        except Exception as e:
            print(f"❌ 現在日取得エラー: {e}")
            return None
    
    def _get_date_from_tdbt_elements(self):
        """TDBT要素から日付を取得"""
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # TDBT クラスの要素を探す
        date_elements = soup.find_all('td', class_='TDBT')
        
        for elem in date_elements:
            text = elem.get_text(strip=True)
            # "X月Y日" 形式をチェック
            match = re.match(r'(\d+)月(\d+)日', text)
            if match:
                month = int(match.group(1))
                day = int(match.group(2))
                
                # 年を取得
                current_year, _ = self.get_current_month_info()
                if current_year:
                    return f"{current_year}-{month:02d}-{day:02d}"
        
        return None
    
    def _get_date_from_javascript(self):
        """JavaScriptから日付を取得"""
        try:
            # zzDate変数から日付を取得
            year = self.driver.execute_script("return zzDate ? zzDate.getFullYear() : null;")
            month = self.driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : null;")
            day = self.driver.execute_script("return zzDate ? zzDate.getDate() : null;")
            
            if year and month and day:
                return f"{year}-{month:02d}-{day:02d}"
        except:
            pass
        
        return None
    
    def _get_date_from_page_content(self):
        """ページコンテンツから日付を取得"""
        page_source = self.driver.page_source
        
        # 日付パターンを正規表現で検索
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})月(\d{1,2})日',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                match = matches[0]
                if len(match) == 3:  # 年月日
                    year, month, day = match
                    return f"{year}-{int(month):02d}-{int(day):02d}"
                elif len(match) == 2:  # 月日のみ
                    month, day = match
                    current_year, _ = self.get_current_month_info()
                    if current_year:
                        return f"{current_year}-{int(month):02d}-{int(day):02d}"
        
        return None
            
    def scrape_main_table_data(self):
        """メインテーブルから待ち時間データを取得"""
        try:
            current_date = self.get_current_day_info()
            
            if not current_date:
                print("❌ 現在の日付情報を取得できませんでした")
                return []
            
            print(f"📊 {current_date} のメインテーブルデータ取得中...")
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 待ち時間テーブルを特定
            wait_time_table = self.find_main_wait_time_table(soup)
            
            if wait_time_table:
                data = self.parse_main_wait_time_table(wait_time_table, current_date)
                print(f"✅ メインテーブル: {len(data)}件のデータを取得")
                return data
            else:
                print("❌ メインテーブルが見つかりません")
                return []
                
        except Exception as e:
            print(f"❌ メインテーブルデータ取得エラー: {e}")
            return []
            
    def find_main_wait_time_table(self, soup):
        """メインの待ち時間テーブルを特定"""
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            # 30行前後で、アトラクション名を含むテーブルを探す
            if 25 <= len(rows) <= 40:
                # アトラクション名のヘッダー行を探す
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > 40:  # 42アトラクション + α
                        # アトラクション名を確認
                        attraction_found = False
                        for cell in cells[2:6]:  # TIME、天気を除く最初の数列
                            text = cell.get_text(strip=True)
                            if any(keyword in text for keyword in ['オムニバス', 'カリブ', 'スペース']):
                                attraction_found = True
                                break
                        
                        if attraction_found:
                            return table
        
        return None
        
    def parse_main_wait_time_table(self, table, date):
        """メインテーブルを解析してデータを抽出"""
        rows = table.find_all('tr')
        data = []
        
        # アトラクション名のヘッダー行を探す
        attraction_names = []
        header_found = False
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > 40 and not header_found:
                # アトラクション名らしきセルを抽出
                potential_attractions = []
                for i, cell in enumerate(cells[2:]):  # TIME、天気列を除く
                    text = cell.get_text(strip=True)
                    if text and len(text) < 25:  # アトラクション名
                        potential_attractions.append(text)
                
                if len(potential_attractions) >= 35:  # アトラクション数の目安
                    attraction_names = potential_attractions[:42]  # 42個に制限
                    header_found = True
                    print(f"🎢 {len(attraction_names)}個のアトラクション名を取得")
                    break
        
        if not attraction_names:
            print("❌ アトラクション名ヘッダーが見つかりません")
            return []
        
        # 時間データ行を解析
        for row in rows:
            cells = row.find_all(['td', 'th'])
            
            if len(cells) >= len(attraction_names) + 2:  # TIME + 天気 + アトラクション
                time_cell = cells[0]
                time_text = time_cell.get_text(strip=True)
                
                # 時間形式をチェック
                if re.match(r'\d{1,2}:\d{2}', time_text):
                    # 待ち時間データを抽出
                    wait_time_cells = cells[2:2+len(attraction_names)]  # TIME, 天気を除く
                    
                    for idx, (attraction_name, cell) in enumerate(zip(attraction_names, wait_time_cells)):
                        wait_text = cell.get_text(strip=True)
                        css_classes = cell.get('class', [])
                        
                        # 待ち時間の数値化
                        wait_time = self.parse_wait_time_value(wait_text, css_classes)
                        
                        data.append({
                            'date': date,
                            'time': time_text,
                            'attraction_index': idx + 1,
                            'attraction_name': attraction_name,
                            'wait_time': wait_time,
                            'raw_value': wait_text,
                            'css_class': ' '.join(css_classes),
                            'data_source': 'main_table',
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
        
        return data
        
    def scrape_attraction_detail_data(self, attraction_index):
        """特定アトラクションの詳細データを取得"""
        try:
            attraction_name = self.attractions.get(attraction_index, f"アトラクション{attraction_index}")
            print(f"🎢 {attraction_name} の詳細データ取得中...")
            
            # 複数の方法でcreateAT2要素を探す
            element_found = False
            search_methods = [
                ("XPath onclick", f"//td[@onclick='createAT2({attraction_index})']"),
                ("XPath contains", f"//td[contains(@onclick, 'createAT2({attraction_index})')]"),
                ("CSS onclick", f"td[onclick='createAT2({attraction_index})']"),
                ("Class FPh2", "td.FPh2")
            ]
            
            for method_name, selector in search_methods:
                try:
                    if "XPath" in method_name:
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    print(f"  {method_name}: {len(elements)}個の要素発見")
                    
                    if method_name == "Class FPh2" and elements:
                        # FPh2クラスの要素から該当するものを探す
                        for elem in elements:
                            onclick = elem.get_attribute('onclick')
                            if onclick and f'createAT2({attraction_index})' in onclick:
                                self.driver.execute_script("arguments[0].click();", elem)
                                element_found = True
                                break
                    elif elements:
                        self.driver.execute_script("arguments[0].click();", elements[0])
                        element_found = True
                        break
                        
                except Exception as e:
                    print(f"    {method_name} 失敗: {str(e)[:100]}")
                    continue
            
            if not element_found:
                print(f"❌ {attraction_name} のcreateAT2要素が見つかりません")
                return []
            
            print(f"✅ {attraction_name} 要素クリック成功")
            time.sleep(2)  # データロード待機
            
            # 変化後のページを解析
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # アトラクション詳細テーブルを解析
            detail_data = self.parse_attraction_detail_table(soup, attraction_index, attraction_name)
            
            print(f"✅ {attraction_name}: {len(detail_data)}件の詳細データを取得")
            return detail_data
            
        except Exception as e:
            print(f"❌ {attraction_name} 詳細データ取得エラー: {e}")
            return []
            
    def parse_attraction_detail_table(self, soup, attraction_index, attraction_name):
        """アトラクション詳細テーブルを解析"""
        tables = soup.find_all('table')
        data = []
        
        # アトラクション名を含むテーブルを探す
        for table in tables:
            rows = table.find_all('tr')
            
            # 30行前後のテーブルを探す
            if 25 <= len(rows) <= 35:
                # 最初の行でアトラクション名を確認
                if rows and attraction_name.replace('｜', '') in str(rows[0]):
                    data = self.parse_time_series_table(table, attraction_index, attraction_name)
                    break
        
        return data
        
    def parse_time_series_table(self, table, attraction_index, attraction_name):
        """時系列テーブルを解析"""
        rows = table.find_all('tr')
        data = []
        
        # ヘッダー行（日付）を取得
        date_headers = []
        if len(rows) > 1:
            header_row = rows[1]
            header_cells = header_row.find_all(['td', 'th'])
            
            for cell in header_cells[1:]:  # TIME列を除く
                date_text = cell.get_text(strip=True)
                # 日付形式を解析（MM月DD日 など）
                match = re.search(r'(\d+)月(\d+)日', date_text)
                if match:
                    month = int(match.group(1))
                    day = int(match.group(2))
                    # 年を取得
                    current_year, _ = self.get_current_month_info()
                    if current_year:
                        formatted_date = f"{current_year}-{month:02d}-{day:02d}"
                        date_headers.append(formatted_date)
        
        print(f"  📅 対象日付: {len(date_headers)}日 - {date_headers}")
        
        # データ行を解析
        for row in rows[2:]:  # ヘッダーを除く
            cells = row.find_all(['td', 'th'])
            
            if cells:
                time_text = cells[0].get_text(strip=True)
                
                # 時間形式をチェック
                if re.match(r'\d{1,2}:\d{2}', time_text):
                    # 各日付の待ち時間を取得
                    for i, date in enumerate(date_headers):
                        if i + 1 < len(cells):  # インデックス確認
                            wait_cell = cells[i + 1]
                            wait_text = wait_cell.get_text(strip=True)
                            css_classes = wait_cell.get('class', [])
                            
                            wait_time = self.parse_wait_time_value(wait_text, css_classes)
                            
                            data.append({
                                'date': date,
                                'time': time_text,
                                'attraction_index': attraction_index,
                                'attraction_name': attraction_name,
                                'wait_time': wait_time,
                                'raw_value': wait_text,
                                'css_class': ' '.join(css_classes),
                                'data_source': 'detail_table',
                                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
        
        return data
        
    def parse_wait_time_value(self, text, css_classes):
        """待ち時間テキストを数値に変換"""
        if not text or text == '-' or text == '':
            return None
        
        # 直接数値の場合
        if text.isdigit():
            return int(text)
        
        # CSSクラスから待ち時間レベルを推定
        class_to_time = {
            'B8': -1,   # 運休・休止
            'B0': 5,    # 空いている（0-14分）
            'B1': 20,   # 少し混雑（15-24分）
            'B2': 27,   # 空いている（25-29分）
            'B3': 35,   # 混雑（30-39分）
            'B4': 45,   # 非常に混雑（40-49分）
            'B5': 55,   # 激混み（50-59分）
            'B6': 65    # 最高レベル（60分以上）
        }
        
        for css_class in css_classes:
            if css_class in class_to_time:
                return class_to_time[css_class]
        
        return text  # パースできない場合は元のテキストを保持
        
    def scrape_multiple_months(self, start_year, start_month, end_year, end_month):
        """複数月のデータを取得"""
        print(f"🎯 期間指定スクレイピング開始")
        print(f"📅 期間: {start_year}年{start_month}月 ～ {end_year}年{end_month}月")
        print("=" * 70)
        
        self.data = []
        
        try:
            self.start_driver()
            self.navigate_to_site()
            
            current_year, current_month = start_year, start_month
            
            while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
                print(f"\n📅 {current_year}年{current_month}月 の処理開始")
                
                # 対象月に移動
                if self.navigate_to_month(current_year, current_month):
                    # メインテーブルデータを取得
                    main_data = self.scrape_main_table_data()
                    self.data.extend(main_data)
                    
                    # 各アトラクションの詳細データを取得（サンプリング）
                    sample_attractions = [1, 3, 12, 15, 16, 32, 35]  # 人気アトラクションのサンプル
                    
                    for attraction_index in sample_attractions:
                        detail_data = self.scrape_attraction_detail_data(attraction_index)
                        self.data.extend(detail_data)
                        time.sleep(1)  # リクエスト間隔
                
                # 次の月へ
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                    
        except Exception as e:
            print(f"❌ スクレイピングエラー: {e}")
            
        finally:
            self.stop_driver()
            
        print(f"\n✅ スクレイピング完了: {len(self.data)}件のデータを取得")
        return self.data
        
    def save_data(self, filename=None):
        """データをCSVファイルに保存"""
        if not self.data:
            print("❌ 保存するデータがありません")
            return
            
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"yosocal_practical_data_{timestamp}.csv"
            
        df = pd.DataFrame(self.data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"💾 データ保存完了: {filename}")
        print(f"📊 保存件数: {len(df)}件")
        print(f"📅 対象期間: {df['date'].min()} ～ {df['date'].max()}")
        print(f"🎢 アトラクション数: {df['attraction_name'].nunique()}個")
        print(f"📋 データソース: {df['data_source'].value_counts().to_dict()}")
        
        return filename

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com 実用的ディズニーランド待ち時間スクレイピング")
    print("=" * 70)
    
    # 対象期間設定（データがある月: 2025年7月）
    start_year, start_month = 2025, 7
    end_year, end_month = 2025, 7
    
    scraper = YosocalPracticalScraper()
    
    try:
        # データ取得
        data = scraper.scrape_multiple_months(start_year, start_month, end_year, end_month)
        
        # データ保存
        if data:
            filename = scraper.save_data()
            
            # 統計表示
            df = pd.DataFrame(data)
            print(f"\n📈 データ統計:")
            print(f"   日付数: {df['date'].nunique()}日")
            print(f"   時間帯数: {df['time'].nunique()}時間帯")
            print(f"   アトラクション: {df['attraction_name'].nunique()}個")
            
            # 平均待ち時間（数値データのみ）
            numeric_data = df[pd.to_numeric(df['wait_time'], errors='coerce').notna()]
            if not numeric_data.empty:
                avg_wait = numeric_data.groupby('attraction_name')['wait_time'].mean().sort_values(ascending=False)
                print(f"\n🏆 平均待ち時間トップ5:")
                for i, (attraction, avg_time) in enumerate(avg_wait.head(5).items()):
                    print(f"   {i+1}. {attraction}: {avg_time:.1f}分")
        
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main() 