#!/usr/bin/env python3
"""
yosocal.com カレンダー日付クリック対応スクレイピングシステム
実際のカレンダー機能 (fMouseclick) を使用して特定日のデータを取得
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

class YosocalCalendarScraper:
    def __init__(self):
        self.driver = None
        self.attractions = get_attraction_list()
        self.data = []
        self.base_url = "https://yosocal.com/realtime.htm"
        
    def start_driver(self):
        """WebDriverを開始"""
        self.driver = setup_driver_with_adblock()
        print("🚀 カレンダー対応WebDriver開始")
        
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
        
        # 広告iframe除去
        ad_removal_script = """
        // 広告iframeを除去
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
        
        // 広告div除去
        var adDivs = document.querySelectorAll('div[id*="ad"], div[class*="ad"]');
        adDivs.forEach(function(div) {
            if (div.offsetHeight > 100 || div.offsetWidth > 100) {
                div.style.display = 'none';
                removedCount++;
            }
        });
        
        // 重複要素除去
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

    def find_calendar_elements(self):
        """カレンダー要素を検出"""
        print("📅 カレンダー要素検出中...")
        
        calendar_elements = []
        
        try:
            # カレンダー要素を複数の方法で検索
            selectors = [
                # 日曜日 (BOXA + CALSUN)
                "div.BOXA[onclick*='fMouseclick']",
                # 平日 (BOXA + CAL)  
                "div.BOXA",
                # 土曜日 (BOX + CALSAT)
                "div.BOX[onclick*='fMouseclick']",
                "div.BOX",
                # その他のカレンダー要素
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
            
            # 発見した要素の詳細を表示
            for i, elem in enumerate(unique_elements[:5]):  # 最初の5個のみ表示
                onclick = elem.get_attribute('onclick')
                text = elem.text.strip()
                class_name = elem.get_attribute('class')
                print(f"  [{i+1}] Class: {class_name}, Text: {text}, OnClick: {onclick}")
            
            return unique_elements
            
        except Exception as e:
            print(f"❌ カレンダー要素検出エラー: {e}")
            return []

    def parse_calendar_date(self, onclick_attr):
        """onclickから日付情報を抽出"""
        try:
            # fMouseclick(20250629,0) から 20250629 を抽出
            match = re.search(r'fMouseclick\((\d{8}),\d+\)', onclick_attr)
            if match:
                date_str = match.group(1)
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return year, month, day, f"{year}-{month:02d}-{day:02d}"
        except:
            pass
        return None, None, None, None

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
        """待ち時間データを取得"""
        print("⏱️ 待ち時間データ取得中...")
        
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
                                print(f"⏰ 時間帯: {time_text}")
                                
                                # 気温列の検出とスキップ処理
                                start_col_idx = 2  # 通常は時間列と気温列の後から開始
                                
                                # 2番目の列が気温列（rowspan付き）かチェック
                                has_weather_col = False
                                if len(cells) > 1:
                                    second_cell = cells[1]
                                    # 気温列の特徴：rowspan属性、天気画像、気温テキスト
                                    if (second_cell.get_attribute('rowspan') or 
                                        'img' in second_cell.get_attribute('innerHTML') or '' or
                                        re.search(r'\d+\.\d+', second_cell.text)):
                                        has_weather_col = True
                                        start_col_idx = 2  # 時間列と気温列をスキップ
                                
                                # 下二桁が45の時間帯では気温列がないため調整
                                if time_text.endswith('45'):
                                    start_col_idx = 1  # 時間列のみスキップ
                                
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

    def scrape_specific_date(self, target_year, target_month, target_day):
        """特定日のデータを取得"""
        print(f"🎯 {target_year}-{target_month:02d}-{target_day:02d} のデータ取得開始")
        print("=" * 70)
        
        self.data = []
        
        try:
            self.start_driver()
            self.navigate_to_site()
            
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
            filename = f"yosocal_calendar_data_{timestamp}.csv"
        
        df = pd.DataFrame(self.data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 データ保存完了: {filename}")
        print(f"📊 保存レコード数: {len(self.data)}")

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com カレンダークリック対応スクレイピング")
    print("=" * 70)
    
    scraper = YosocalCalendarScraper()
    
    # 利用可能な日付をテスト（7月1日）
    target_year = 2025
    target_month = 7
    target_day = 1
    
    try:
        print(f"🎯 ターゲット日付: {target_year}年{target_month}月{target_day}日")
        
        success = scraper.scrape_specific_date(target_year, target_month, target_day)
        
        if success:
            scraper.save_data()
            print("✅ スクレイピング完了！")
        else:
            print("❌ データ取得に失敗しました")
            
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main() 