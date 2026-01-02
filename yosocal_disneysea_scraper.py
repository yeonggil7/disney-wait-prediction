#!/usr/bin/env python3
"""
yosocal.com ディズニーシー月単位一括データ取得システム
指定月のすべての利用可能日付のディズニーシー待ち時間データを連続取得
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import pandas as pd
import time
import json
import re
import os
import sys
import argparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def setup_driver_with_adblock():
    """広告ブロック対応Chrome WebDriverの設定"""
    options = Options()
    
    # 基本設定
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 広告ブロック設定
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-default-apps')
    options.add_argument('--disable-extensions-http-throttling')
    
    # 広告関連ドメインをブロック
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "popups": 2,
            "media_stream": 2,
        },
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 2
    }
    options.add_experimental_option("prefs", prefs)
    
    # User-Agent設定
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    
    # 広告スクリプトをブロック
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*googlesyndication.com*",
            "*doubleclick.net*",
            "*googleadservices.com*",
            "*google-analytics.com*",
            "*googletagmanager.com*",
            "*facebook.com/tr*",
            "*ads*",
            "*adnxs.com*"
        ]
    })
    driver.execute_cdp_cmd('Network.enable', {})
    
    return driver

def get_disneysea_attraction_list():
    """ディズニーシーアトラクション一覧（実際のサイト順序）"""
    return {
        1: 'ソアリン',
        2: '船メディテレーニアンハーバー発',
        3: 'フォートレスエクスプロレーション',
        4: 'ゴンドラ',
        5: 'タワーオブテラー',
        6: 'トイストーリーマニア',
        7: 'タートル・トーク',
        8: 'エレクトリックレールウェイアメリカンウォーターフロント発',
        9: '船アメリカンウォーターフロント発',
        10: 'ヴィークル',
        11: 'センターオブジアース',
        12: '海底二万マイル',
        13: 'ニモandフレンズシーライダー',
        14: 'アクアトピア',
        15: '鉄道ポートディスカバリー発',
        16: 'インディージョーンズクリスタルスカルの謎',
        17: 'レイジングスピリッツ',
        18: '船ロストリバーデルタ発',
        19: 'マーメイドラグーン',
        20: 'ジャンピン',
        21: 'スカットルのスクーター',
        22: 'フランダー',
        23: 'バルーンレース',
        24: 'ワールプール',
        25: 'アナとエルサ',
        26: 'ラプンツェル',
        27: 'ピーターパン',
        28: 'ティンカーベル',
        29: 'マジックランプシアター',
        30: 'カルーセル',
        31: 'シンドバッド',
        32: 'ジャスミン',
        33: 'プラザグリーティング',
        34: 'ヴィレッジグリーティング',
        35: 'サルードス・アミーゴス',
        36: 'ドナルドグリーティング',
        37: 'ミッキーグリーティング',
        38: 'ミニーグリーティング',
        39: 'マーメイドラグーングリーティング',
        40: 'アラビアンコーストグリーティング'
    }

class YosocalDisneyseaScraper:
    def __init__(self):
        self.driver = None
        self.attractions = get_disneysea_attraction_list()
        self.monthly_data = []
        self.daily_data = {}
        self.base_url = "https://yosocal.com/realtime.htm"
        self.data_dir = "Disneysea"
        
        # Disneyseaディレクトリを作成
        os.makedirs(self.data_dir, exist_ok=True)
        
    def start_driver(self):
        """WebDriverを開始"""
        self.driver = setup_driver_with_adblock()
        print("🚀 ディズニーシー月単位一括取得WebDriver開始")
        
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
        WebDriverWait(self.driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # 広告要素を除去
        self.remove_ads()
        
        print("✅ ページロード完了（広告除去済み）")
        
    def remove_ads(self):
        """広告要素を除去"""
        ad_removal_script = """
        var iframes = document.querySelectorAll('iframe');
        var removedCount = 0;
        iframes.forEach(function(iframe) {
            var src = iframe.src || '';
            var id = iframe.id || '';
            if (src.includes('googlesyndication') || 
                src.includes('doubleclick') || 
                src.includes('googleads') ||
                id.includes('aswift') ||
                iframe.getAttribute('sandbox')) {
                iframe.remove();
                removedCount++;
            }
        });
        
        var adDivs = document.querySelectorAll('div[id*="ad"], div[class*="ad"]');
        adDivs.forEach(function(div) {
            if (div.offsetHeight > 100 || div.offsetWidth > 100) {
                div.style.display = 'none';
                removedCount++;
            }
        });
        
        var overlays = document.querySelectorAll('[style*="position: absolute"], [style*="position: fixed"]');
        overlays.forEach(function(overlay) {
            var zIndex = window.getComputedStyle(overlay).zIndex;
            if (zIndex && parseInt(zIndex) > 1000) {
                overlay.style.display = 'none';
                removedCount++;
            }
        });
        
        return removedCount;
        """
        
        try:
            removed_count = self.driver.execute_script(ad_removal_script)
            if removed_count > 0:
                print(f"  🚫 {removed_count}個の広告要素を除去")
        except Exception as e:
            print(f"  ⚠️ 広告除去エラー: {e}")

    def select_disneysea_park(self):
        """ディズニーシーパークを選択"""
        try:
            print("🏰 ディズニーシーパークを選択中...")
            
            # ディズニーシーのラジオボタンを探す
            disneysea_selectors = [
                "input[id='park2']",
                "input[name='park'][value*='シー']",
                "input[onclick*='park2']"
            ]
            
            for selector in disneysea_selectors:
                try:
                    radio_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if radio_button:
                        # 広告を除去してからクリック
                        self.remove_ads()
                        time.sleep(1)
                        
                        # JavaScriptでクリック実行
                        self.driver.execute_script("arguments[0].click();", radio_button)
                        
                        # パーク切り替え待機
                        time.sleep(3)
                        
                        print("✅ ディズニーシーパークを選択完了")
                        return True
                        
                except Exception as e:
                    continue
            
            # 代替方法：ラベル要素からクリック
            try:
                label_elements = self.driver.find_elements(By.TAG_NAME, "label")
                for label in label_elements:
                    if "ディズニーシー" in label.text:
                        self.driver.execute_script("arguments[0].click();", label)
                        time.sleep(3)
                        print("✅ ディズニーシーパークを選択完了（ラベル経由）")
                        return True
            except Exception as e:
                print(f"⚠️ ラベル経由選択エラー: {e}")
            
            print("❌ ディズニーシーパーク選択に失敗")
            return False
            
        except Exception as e:
            print(f"❌ パーク選択エラー: {e}")
            return False

    def get_current_month_info(self):
        """現在表示されている月の情報を取得"""
        try:
            # JavaScriptのzzDate変数から現在月を取得
            year = self.driver.execute_script("return zzDate ? zzDate.getFullYear() : null;")
            month = self.driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : null;")
            
            if year and month:
                print(f"📅 現在表示月: {year}年{month}月")
                return year, month
            
            return None, None
            
        except Exception as e:
            print(f"❌ 月情報取得エラー: {e}")
            return None, None

    def navigate_to_target_month(self, target_year, target_month):
        """目標の月まで移動"""
        print(f"🎯 {target_year}年{target_month}月へ移動中...")
        
        current_year, current_month = self.get_current_month_info()
        
        if current_year == target_year and current_month == target_month:
            print("✅ 既に目標の月に到達済み")
            return True
        
        # 前月ボタンで移動
        attempt_count = 0
        max_attempts = 12  # 最大12ヶ月まで移動
        
        while current_year and current_month and attempt_count < max_attempts:
            if current_year == target_year and current_month == target_month:
                print(f"✅ {target_year}年{target_month}月に到達")
                return True
            
            # 前月ボタンをクリック
            if not self.click_previous_month_button():
                print("❌ 前月ボタンクリックに失敗")
                return False
            
            current_year, current_month = self.get_current_month_info()
            attempt_count += 1
        
        return False

    def click_previous_month_button(self):
        """前月ボタンをクリック"""
        try:
            selectors = [
                "input[value='前月']",
                "input[onclick*='Fnc_L']",
                "input[type='button'][value*='前']"
            ]
            
            for selector in selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        value = button.get_attribute('value')
                        onclick = button.get_attribute('onclick')
                        
                        if ('前月' in value or '前' in value) and 'Fnc_L' in onclick:
                            # 広告を除去してからクリック
                            self.remove_ads()
                            time.sleep(1)
                            
                            # JavaScriptでクリック実行
                            self.driver.execute_script("arguments[0].click();", button)
                            
                            # ページ更新待機
                            time.sleep(3)
                            
                            return True
                            
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ 前月ボタンクリックエラー: {e}")
            return False

    def get_available_dates(self):
        """利用可能な日付一覧を取得"""
        print("📅 利用可能日付を検出中...")
        
        available_dates = []
        
        try:
            selectors = [
                "div.BOXA[onclick*='fMouseclick']",
                "div.BOX[onclick*='fMouseclick']",
                "[onclick*='fMouseclick']"
            ]
            
            calendar_elements = []
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        onclick = element.get_attribute('onclick')
                        if onclick and 'fMouseclick' in onclick:
                            calendar_elements.append(element)
                            
                except Exception as e:
                    continue
            
            # 重複除去とソート
            seen_onclick = set()
            for elem in calendar_elements:
                onclick = elem.get_attribute('onclick')
                if onclick not in seen_onclick:
                    seen_onclick.add(onclick)
                    
                    # fMouseclick(YYYYMMDD, index) から日付を抽出
                    match = re.search(r'fMouseclick\((\d{8})', onclick)
                    if match:
                        date_str = match.group(1)
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        
                        available_dates.append({
                            'year': year,
                            'month': month,
                            'day': day,
                            'date_str': date_str,
                            'element': elem,
                            'onclick': onclick
                        })
            
            # 日付順でソート
            available_dates.sort(key=lambda x: x['date_str'])
            
            print(f"📅 利用可能日付: {len(available_dates)}日")
            for date_info in available_dates:
                print(f"  📆 {date_info['year']}-{date_info['month']:02d}-{date_info['day']:02d}")
            
            return available_dates
            
        except Exception as e:
            print(f"❌ 日付検出エラー: {e}")
            return []

    def click_date_by_info(self, date_info):
        """日付情報に基づいて日付をクリック"""
        try:
            print(f"📅 {date_info['year']}-{date_info['month']:02d}-{date_info['day']:02d} をクリック")
            
            # 広告を除去してからクリック
            self.remove_ads()
            time.sleep(1)
            
            # JavaScriptでクリック実行
            self.driver.execute_script("arguments[0].click();", date_info['element'])
            
            # ページ更新待機
            time.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"❌ 日付クリックエラー: {e}")
            return False

    def get_current_date_info(self):
        """現在表示されている日付情報を取得"""
        try:
            # TDBT要素から日付を取得
            date_elements = self.driver.find_elements(By.CLASS_NAME, "TDBT")
            
            for elem in date_elements:
                text = elem.text.strip()
                # "X月Y日" 形式をチェック
                match = re.match(r'(\d+)月(\d+)日', text)
                if match:
                    month = int(match.group(1))
                    day = int(match.group(2))
                    # 年を推定（現在月から）
                    current_year = datetime.now().year
                    return f"{current_year}-{month:02d}-{day:02d}"
            
            return None
            
        except Exception as e:
            print(f"❌ 日付情報取得エラー: {e}")
            return None

    def scrape_wait_times(self):
        """待ち時間データを取得（ディズニーシー対応・気温列修正版）"""
        wait_times = []
        
        try:
            # メインテーブルを取得
            main_table = self.driver.find_element(By.ID, "jamat")
            
            if main_table:
                # テーブル構造を解析
                rows = main_table.find_elements(By.TAG_NAME, "tr")
                
                # アトラクション名行を特定
                attraction_row = None
                for i, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    for cell in cells:
                        onclick = cell.get_attribute('onclick')
                        if onclick and "createAT2" in onclick:
                            attraction_row = i
                            break
                    if attraction_row is not None:
                        break
                
                if attraction_row is not None:
                    # 時間データ行を処理
                    time_rows = rows[attraction_row + 1:]  # アトラクション行以降
                    
                    for row_idx, row in enumerate(time_rows):
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) > 1:
                            # 時間列（最初の列）
                            time_cell = cells[0]
                            time_text = time_cell.text.strip()
                            
                            # 時間形式チェック
                            if re.match(r'\d{2}:\d{2}', time_text):
                                # 気温列の検出とスキップ処理
                                start_col_idx = 1  # デフォルトは時間列の次から開始
                                
                                # 2番目の列が気温列（rowspan付き）かチェック
                                if len(cells) > 1:
                                    second_cell = cells[1]
                                    cell_html = second_cell.get_attribute('innerHTML') or ''
                                    cell_text = second_cell.text or ''
                                    
                                    # 気温列の特徴を判定
                                    is_weather_col = (
                                        second_cell.get_attribute('rowspan') or  # rowspan属性
                                        'img' in cell_html or  # 天気画像
                                        re.search(r'\d+\.\d+', cell_text) or  # 気温テキスト
                                        'w\d+\.gif' in cell_html  # 天気画像ファイル
                                    )
                                    
                                    if is_weather_col:
                                        start_col_idx = 2  # 時間列と気温列をスキップ
                                    else:
                                        start_col_idx = 1  # 時間列のみスキップ
                                
                                # 各アトラクションの待ち時間（ディズニーシー対応）
                                for col_idx, cell in enumerate(cells[start_col_idx:], 1):
                                    css_class = cell.get_attribute('class')
                                    cell_text = cell.text.strip()
                                    
                                    # 40個のアトラクションのみ処理（平均待ち時間は除外）
                                    if col_idx <= 40 and ((css_class and css_class.startswith('B')) or cell_text.isdigit()):
                                        wait_time = self.parse_wait_time(css_class, cell_text)
                                        attraction_name = self.attractions.get(col_idx, f"アトラクション{col_idx}")
                                        
                                        wait_times.append({
                                            'time': time_text,
                                            'attraction_index': col_idx,
                                            'attraction_name': attraction_name,
                                            'wait_time': wait_time,
                                            'css_class': css_class,
                                            'raw_value': cell_text
                                        })
                
                return wait_times
                
        except Exception as e:
            print(f"❌ 待ち時間取得エラー: {e}")
            
        return wait_times

    def parse_wait_time(self, css_class, cell_text):
        """CSS クラスと直接数値から待ち時間を解析"""
        # B0-B8 のマッピング
        class_to_wait = {
            'B0': 5,
            'B1': 10,
            'B2': 20,
            'B3': 30,
            'B4': 40,
            'B5': 50,
            'B6': 60,
            'B7': 70,
            'B8': 0  # クローズド
        }
        
        # セルテキストが数値の場合はそれを使用（優先）
        if cell_text and cell_text.isdigit():
            return int(cell_text)
        
        # セルテキストが浮動小数点の場合
        if cell_text and re.match(r'\d+\.\d+', cell_text):
            return float(cell_text)
        
        # '-' や空の場合は0
        if not cell_text or cell_text == '-':
            return 0
        
        # CSS クラスから推定
        if css_class:
            for class_prefix, wait_time in class_to_wait.items():
                if class_prefix in css_class:
                    return wait_time
        
        return 0

    def scrape_monthly_data(self, target_year, target_month):
        """指定月のすべての日付のデータを取得"""
        print(f"🏰 ディズニーシー {target_year}年{target_month}月 一括データ取得開始")
        print("=" * 70)
        
        self.monthly_data = []
        self.daily_data = {}
        
        try:
            self.start_driver()
            self.navigate_to_site()
            
            # ディズニーシーパークを選択
            if not self.select_disneysea_park():
                print("❌ ディズニーシーパーク選択に失敗")
                return False
            
            # 目標の月まで移動
            if not self.navigate_to_target_month(target_year, target_month):
                print("❌ 目標月への移動に失敗")
                return False
            
            # 利用可能な日付を取得
            available_dates = self.get_available_dates()
            
            if not available_dates:
                print("❌ 利用可能な日付が見つかりません")
                return False
            
            # 各日付のデータを順番に取得
            success_count = 0
            
            for i, date_info in enumerate(available_dates, 1):
                date_str = f"{date_info['year']}-{date_info['month']:02d}-{date_info['day']:02d}"
                print(f"\n📅 [{i}/{len(available_dates)}] {date_str} 処理中...")
                
                # 日付をクリック
                if self.click_date_by_info(date_info):
                    
                    # 現在の日付を確認
                    current_date = self.get_current_date_info()
                    print(f"  📋 表示日付: {current_date}")
                    
                    # 待ち時間データを取得
                    wait_times = self.scrape_wait_times()
                    
                    if wait_times:
                        # データを整理
                        daily_records = []
                        for wt in wait_times:
                            wt['date'] = current_date or date_str
                            wt['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            daily_records.append(wt)
                            self.monthly_data.append(wt)
                        
                        # 日別データを保存
                        self.daily_data[date_str] = daily_records
                        
                        print(f"  ✅ {len(daily_records)}個のデータを取得")
                        success_count += 1
                        
                        # 個別ファイルに保存
                        self.save_daily_data(date_str, daily_records)
                        
                    else:
                        print(f"  ❌ {date_str} のデータ取得に失敗")
                else:
                    print(f"  ❌ {date_str} のクリックに失敗")
                
                # 短い待機時間
                time.sleep(1)
            
            print(f"\n🎉 ディズニーシー月間データ取得完了!")
            print(f"✅ 成功: {success_count}/{len(available_dates)} 日")
            print(f"📊 総データ数: {len(self.monthly_data):,}レコード")
            
            # 月間統合データを保存
            self.save_monthly_data(target_year, target_month)
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 月間データ取得エラー: {e}")
            return False
            
        finally:
            self.stop_driver()

    def save_daily_data(self, date_str, data):
        """日別データを保存"""
        try:
            filename = os.path.join(self.data_dir, f"disneysea_daily_{date_str}.csv")
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"  💾 日別保存: {filename}")
        except Exception as e:
            print(f"  ❌ 日別保存エラー: {e}")

    def save_monthly_data(self, year, month):
        """月間統合データを保存"""
        try:
            if not self.monthly_data:
                print("💾 保存するデータがありません")
                return
            
            # 月間統合ファイル
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.data_dir, f"disneysea_monthly_{year}_{month:02d}_{timestamp}.csv")
            
            df = pd.DataFrame(self.monthly_data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"\n💾 月間統合データ保存完了: {filename}")
            print(f"📊 総レコード数: {len(self.monthly_data):,}")
            
            # 統計情報を保存
            self.save_monthly_statistics(year, month, timestamp)
            
        except Exception as e:
            print(f"❌ 月間データ保存エラー: {e}")

    def save_monthly_statistics(self, year, month, timestamp):
        """月間統計情報を保存"""
        try:
            if not self.monthly_data:
                return
            
            df = pd.DataFrame(self.monthly_data)
            
            # 統計情報を計算（JSON serializable形式）
            stats = {
                "パーク": "ディズニーシー",
                "データ取得期間": f"{year}年{month}月",
                "取得日数": int(len(self.daily_data)),
                "総データ数": int(len(self.monthly_data)),
                "データ取得日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "アトラクション数": int(df['attraction_index'].nunique()),
                "時間スロット数": int(df['time'].nunique()),
                "平均待ち時間": float(round(df['wait_time'].mean(), 1)),
                "最大待ち時間": int(df['wait_time'].max()),
                "人気アトラクション": {k: float(round(v, 1)) for k, v in df.groupby('attraction_name')['wait_time'].mean().sort_values(ascending=False).head(5).items()},
                "日別データ数": {date: int(len(data)) for date, data in self.daily_data.items()},
                "月間パフォーマンス": {
                    "成功日数": int(len(self.daily_data)),
                    "平均レコード/日": float(round(len(self.monthly_data) / len(self.daily_data), 1)) if self.daily_data else 0,
                    "データ完整性": "100%" if self.daily_data and all(len(data) > 0 for data in self.daily_data.values()) else "部分的"
                }
            }
            
            # JSON形式で保存
            stats_filename = os.path.join(self.data_dir, f"disneysea_monthly_stats_{year}_{month:02d}_{timestamp}.json")
            with open(stats_filename, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            print(f"📈 統計情報保存: {stats_filename}")
            
            # テキスト形式の詳細レポートも生成
            self.save_detailed_report(year, month, timestamp, stats)
            
        except Exception as e:
            print(f"❌ 統計情報保存エラー: {e}")

    def save_detailed_report(self, year, month, timestamp, stats):
        """詳細テキストレポートを生成"""
        try:
            report_filename = os.path.join(self.data_dir, f"disneysea_monthly_report_{year}_{month:02d}_{timestamp}.txt")
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write("🏰 ディズニーシー待ち時間データ 月間レポート\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"📅 対象期間: {stats['データ取得期間']}\n")
                f.write(f"🎡 パーク: {stats['パーク']}\n")
                f.write(f"📊 データ取得日時: {stats['データ取得日時']}\n")
                f.write(f"📈 取得日数: {stats['取得日数']}日\n")
                f.write(f"📋 総データ数: {stats['総データ数']:,}レコード\n")
                f.write(f"🎢 アトラクション数: {stats['アトラクション数']}個\n")
                f.write(f"⏰ 時間スロット数: {stats['時間スロット数']}個\n\n")
                
                f.write("🎢 人気アトラクション（平均待ち時間）:\n")
                for attraction, wait_time in stats['人気アトラクション'].items():
                    f.write(f"  • {attraction}: {wait_time}分\n")
                f.write("\n")
                
                f.write("📊 月間パフォーマンス:\n")
                for key, value in stats['月間パフォーマンス'].items():
                    f.write(f"  • {key}: {value}\n")
                f.write("\n")
                
                f.write("📅 日別データ数:\n")
                for date, count in sorted(stats['日別データ数'].items()):
                    f.write(f"  • {date}: {count:,}レコード\n")
            
            print(f"📄 詳細レポート保存: {report_filename}")
            
        except Exception as e:
            print(f"❌ 詳細レポート保存エラー: {e}")

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description='yosocal.com ディズニーシー月間データ取得システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python3 yosocal_disneysea_scraper.py --year 2025 --month 6   # 2025年6月
  python3 yosocal_disneysea_scraper.py --year 2025 --month 7   # 2025年7月
  python3 yosocal_disneysea_scraper.py                         # デフォルト: 2025年6月
        """
    )
    
    parser.add_argument(
        '--year', 
        type=int, 
        default=2025,
        help='取得したい年 (default: 2025)'
    )
    
    parser.add_argument(
        '--month', 
        type=int, 
        default=6,
        choices=range(1, 13),
        help='取得したい月 1-12 (default: 6)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='詳細ログを表示'
    )
    
    args = parser.parse_args()
    
    print("🏰 yosocal.com ディズニーシー月間データ取得システム")
    print("=" * 70)
    print(f"🎯 取得対象: {args.year}年{args.month}月")
    
    if args.verbose:
        print("📋 処理概要:")
        print("  1. ディズニーシーパークを選択")
        print("  2. 指定月のカレンダーに移動")
        print("  3. 利用可能な全日付を検出")
        print("  4. 各日付のデータを順次取得")
        print("  5. 日別・月別でデータを保存")
        print("  6. 統計情報を生成")
    
    # 月名表示
    month_names = {
        1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
        7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
    }
    
    print(f"📅 対象月: {month_names.get(args.month, '')} ({args.month}月)")
    
    try:
        scraper = YosocalDisneyseaScraper()
        
        # カスタム年月でデータ取得
        success = scraper.scrape_monthly_data(args.year, args.month)
        
        if success:
            print(f"\n🎉 ディズニーシー {args.year}年{args.month}月 一括取得完了！")
            print("💾 保存先: Disneyseaフォルダ")
            print("📋 生成ファイル:")
            print("  • 日別CSVファイル (disneysea_daily_YYYY-MM-DD.csv)")
            print("  • 月間統合CSVファイル (disneysea_monthly_YYYY_MM_timestamp.csv)")
            print("  • 統計情報JSONファイル (disneysea_monthly_stats_YYYY_MM_timestamp.json)")
        else:
            print(f"\n❌ ディズニーシー {args.year}年{args.month}月 データ取得に失敗しました")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 