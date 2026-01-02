#!/usr/bin/env python3
"""
yosocal.com カレンダーナビゲーション対応スクレイピングシステム
前月ボタンを使った月移動機能付き（気温列修正版）
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
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os

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

class YosocalNavigationScraper:
    def __init__(self):
        self.driver = None
        self.attractions = get_attraction_list()
        self.data = []
        self.base_url = "https://yosocal.com/realtime.htm"
        
    def start_driver(self):
        """WebDriverを開始"""
        self.driver = setup_driver_with_adblock()
        print("🚀 前月ナビゲーション対応WebDriver開始")
        
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
        print("🚫 広告除去中...")
        
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
            print(f"  ✅ {removed_count}個の広告要素を除去")
        except Exception as e:
            print(f"  ⚠️ 広告除去エラー: {e}")

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

    def click_previous_month_button(self):
        """前月ボタンをクリック"""
        print("◀️ 前月ボタンをクリック中...")
        
        try:
            # 複数の方法で前月ボタンを探す
            selectors = [
                "input[value='前月']",
                "input[onclick*='Fnc_L']",
                "input[type='button'][value*='前']"
            ]
            
            button_found = False
            
            for selector in selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        value = button.get_attribute('value')
                        onclick = button.get_attribute('onclick')
                        
                        if ('前月' in value or '前' in value) and 'Fnc_L' in onclick:
                            print(f"📍 前月ボタン発見: {value}")
                            
                            # 広告を除去してからクリック
                            self.remove_ads()
                            time.sleep(1)
                            
                            # JavaScriptでクリック実行
                            self.driver.execute_script("arguments[0].click();", button)
                            
                            # ページ更新待機
                            time.sleep(5)
                            
                            print("✅ 前月ボタンクリック成功")
                            button_found = True
                            break
                            
                except Exception as e:
                    print(f"  セレクター {selector} エラー: {e}")
                    continue
                
                if button_found:
                    break
            
            if not button_found:
                print("❌ 前月ボタンが見つかりません")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 前月ボタンクリックエラー: {e}")
            return False

    def find_calendar_elements(self):
        """カレンダー要素を検出"""
        print("📅 カレンダー要素検出中...")
        
        calendar_elements = []
        
        try:
            selectors = [
                "div.BOXA[onclick*='fMouseclick']",
                "div.BOXA",
                "div.BOX[onclick*='fMouseclick']",
                "div.BOX",
                "[onclick*='fMouseclick']"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        onclick = element.get_attribute('onclick')
                        if onclick and 'fMouseclick' in onclick:
                            calendar_elements.append(element)
                            
                except Exception as e:
                    print(f"  セレクター {selector} エラー: {e}")
                    continue
            
            # 重複除去
            unique_elements = []
            seen_onclick = set()
            for elem in calendar_elements:
                onclick = elem.get_attribute('onclick')
                if onclick not in seen_onclick:
                    unique_elements.append(elem)
                    seen_onclick.add(onclick)
            
            print(f"📅 カレンダー要素: {len(unique_elements)}個発見")
            
            return unique_elements
            
        except Exception as e:
            print(f"❌ カレンダー要素検出エラー: {e}")
            return []

    def click_specific_date(self, target_year, target_month, target_day):
        """特定の日付をクリック"""
        print(f"🎯 {target_year}-{target_month:02d}-{target_day:02d} をクリック中...")
        
        calendar_elements = self.find_calendar_elements()
        
        if not calendar_elements:
            print("❌ カレンダー要素が見つかりません")
            return False
        
        target_date_str = f"{target_year}{target_month:02d}{target_day:02d}"
        
        for element in calendar_elements:
            onclick = element.get_attribute('onclick')
            if onclick and target_date_str in onclick:
                try:
                    print(f"📅 日付クリック実行: {onclick}")
                    
                    # 広告を除去してからクリック
                    self.remove_ads()
                    time.sleep(1)
                    
                    # JavaScriptでクリック実行
                    self.driver.execute_script("arguments[0].click();", element)
                    
                    # ページ更新待機
                    time.sleep(3)
                    
                    print(f"✅ {target_year}-{target_month:02d}-{target_day:02d} クリック成功")
                    return True
                    
                except Exception as e:
                    print(f"❌ 日付クリックエラー: {e}")
                    continue
        
        print(f"❌ {target_year}-{target_month:02d}-{target_day:02d} が見つかりません")
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
        """待ち時間データを取得（気温列修正版）"""
        print("⏱️ 待ち時間データ取得中（気温列処理対応）...")
        
        wait_times = []
        
        try:
            # メインテーブルを取得
            main_table = self.driver.find_element(By.ID, "jamat")
            
            if main_table:
                # テーブル構造を解析
                rows = main_table.find_elements(By.TAG_NAME, "tr")
                print(f"📊 テーブル行数: {len(rows)}")
                
                # アトラクション名行を特定
                attraction_row = None
                for i, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    for cell in cells:
                        onclick = cell.get_attribute('onclick')
                        if onclick and "createAT2" in onclick:
                            attraction_row = i
                            print(f"🎢 アトラクション行: {i}")
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
                                print(f"⏰ {time_text}", end=" → ")
                                
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
                                        print(f"🌡️ 気温列検出: {cell_text.strip()}")
                                    else:
                                        start_col_idx = 1  # 時間列のみスキップ
                                        print(f"📊 No weather column")
                                
                                # 各アトラクションの待ち時間
                                for col_idx, cell in enumerate(cells[start_col_idx:], 1):
                                    css_class = cell.get_attribute('class')
                                    cell_text = cell.text.strip()
                                    
                                    if css_class and css_class.startswith('B'):
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
                
                print(f"✅ {len(wait_times)}個の待ち時間データを取得")
                return wait_times
                
        except Exception as e:
            print(f"❌ 待ち時間取得エラー: {e}")
            
        return wait_times

    def parse_wait_time(self, css_class, cell_text):
        """CSS クラスから待ち時間を推定"""
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
        
        # セルテキストが数値の場合はそれを使用
        if cell_text.isdigit():
            return int(cell_text)
        
        # CSS クラスから推定
        for class_prefix, wait_time in class_to_wait.items():
            if css_class and class_prefix in css_class:
                return wait_time
        
        return 0

    def scrape_previous_month_date(self, target_year, target_month, target_day):
        """前月の特定日のデータを取得"""
        print(f"🎯 前月データ取得: {target_year}-{target_month:02d}-{target_day:02d}")
        print("=" * 70)
        
        self.data = []
        
        try:
            self.start_driver()
            self.navigate_to_site()
            
            # 現在の月を確認
            current_year, current_month = self.get_current_month_info()
            print(f"📅 初期月: {current_year}年{current_month}月")
            
            # 前月ボタンをクリック
            if self.click_previous_month_button():
                
                # 移動後の月を確認
                new_year, new_month = self.get_current_month_info()
                print(f"📅 移動後の月: {new_year}年{new_month}月")
                
                # 特定の日付をクリック
                if self.click_specific_date(target_year, target_month, target_day):
                    
                    # 現在の日付を確認
                    current_date = self.get_current_date_info()
                    print(f"📅 表示中の日付: {current_date}")
                    
                    # 待ち時間データを取得
                    wait_times = self.scrape_wait_times()
                    
                    if wait_times:
                        # データを整理
                        for wt in wait_times:
                            wt['date'] = current_date or f"{target_year}-{target_month:02d}-{target_day:02d}"
                            wt['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.data.append(wt)
                        
                        print(f"✅ {len(self.data)}個のデータポイントを収集")
                        return True
                    else:
                        print("❌ 待ち時間データが取得できませんでした")
                else:
                    print("❌ 日付クリックに失敗しました")
            else:
                print("❌ 前月ボタンクリックに失敗しました")
                
        except Exception as e:
            print(f"❌ スクレイピングエラー: {e}")
            
        finally:
            self.stop_driver()
            
        return len(self.data) > 0

    def save_data(self, filename=None):
        """データをCSVファイルに保存"""
        if not self.data:
            print("💾 保存するデータがありません")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"yosocal_previous_month_data_{timestamp}.csv"
        
        df = pd.DataFrame(self.data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 データ保存完了: {filename}")
        print(f"📊 保存レコード数: {len(self.data)}")

def main():
    """メイン実行関数 - 6月1日のデータを取得"""
    print("🏰 yosocal.com 前月ナビゲーション対応スクレイピング")
    print("=" * 70)
    
    scraper = YosocalNavigationScraper()
    
    # 6月1日のデータを取得
    target_year = 2025
    target_month = 6
    target_day = 1
    
    try:
        print(f"🎯 ターゲット日付: {target_year}年{target_month}月{target_day}日")
        
        success = scraper.scrape_previous_month_date(target_year, target_month, target_day)
        
        if success:
            scraper.save_data()
            print("✅ 前月データ取得完了！")
        else:
            print("❌ 前月データ取得に失敗しました")
            
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main() 