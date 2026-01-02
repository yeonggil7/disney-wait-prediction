#!/usr/bin/env python3
"""
yosocal.com 広告ブロック対応スクレイピングシステム
広告をブロックして安定した動作を実現
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

class YosocalAdBlockScraper:
    def __init__(self):
        self.driver = None
        self.attractions = get_attraction_list()
        self.data = []
        self.base_url = "https://yosocal.com/realtime.htm"
        
    def start_driver(self):
        """WebDriverを開始"""
        self.driver = setup_driver_with_adblock()
        print("🚀 広告ブロック対応WebDriver開始")
        
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
            print(f"  ⚠️ 広告除去でエラー: {e}")
        
        time.sleep(2)  # DOM安定化待機
        
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
            
    def safe_click_navigation_button(self, button_text, max_retries=3):
        """安全な月移動ボタンクリック"""
        for retry in range(max_retries):
            try:
                # 広告を再度除去
                if retry > 0:
                    self.remove_ads()
                    time.sleep(2)
                
                # ボタンを探す
                button = self.driver.find_element(By.XPATH, f"//input[@value='{button_text}']")
                
                # ボタンが見える位置にスクロール
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(1)
                
                # クリック実行（JavaScript使用）
                self.driver.execute_script("arguments[0].click();", button)
                print(f"  ✅ {button_text}ボタンクリック成功")
                return True
                
            except ElementClickInterceptedException:
                print(f"  ⚠️ {button_text}ボタンクリック妨害 (試行{retry+1}/{max_retries})")
                if retry < max_retries - 1:
                    # 妨害要素を除去して再試行
                    self.remove_ads()
                    time.sleep(3)
                continue
            except Exception as e:
                print(f"  ❌ {button_text}ボタンクリックエラー: {e}")
                if retry < max_retries - 1:
                    time.sleep(2)
                continue
        
        return False
            
    def navigate_to_month(self, target_year, target_month):
        """指定月に移動（広告対応版）"""
        print(f"📅 {target_year}年{target_month}月に移動中...")
        
        max_attempts = 12
        
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
                    time.sleep(5)
                    # 到達後も広告を除去
                    self.remove_ads()
                    return True
                
                # 前月または次月ボタンをクリック
                if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                    success = self.safe_click_navigation_button("前月")
                    if success:
                        print("  ← 前月へ移動")
                    else:
                        print("  ❌ 前月ボタンクリック失敗")
                        return False
                else:
                    success = self.safe_click_navigation_button("次月")
                    if success:
                        print("  → 次月へ移動")
                    else:
                        print("  ❌ 次月ボタンクリック失敗")
                        return False
                
                time.sleep(5)  # 移動後の待機
                
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
        
    def scrape_single_month(self, target_year, target_month):
        """単一月のデータを取得"""
        print(f"🎯 広告対応版スクレイピング開始")
        print(f"📅 対象: {target_year}年{target_month}月")
        print("=" * 70)
        
        self.data = []
        
        try:
            self.start_driver()
            self.navigate_to_site()
            
            # 対象月に移動
            if self.navigate_to_month(target_year, target_month):
                
                # 現在の日付を取得
                current_date = self.get_current_day_info()
                
                if current_date:
                    print(f"📊 {current_date} のデータ取得開始...")
                    
                    # createAT2要素の存在確認
                    createat2_elements = self.driver.find_elements(By.XPATH, "//td[contains(@onclick, 'createAT2')]")
                    print(f"🎢 createAT2要素: {len(createat2_elements)}個発見")
                    
                    if len(createat2_elements) > 0:
                        print(f"✅ {target_year}年{target_month}月にはデータが存在します！")
                        
                        # 簡単なサンプル取得（最初の3つのアトラクション）
                        sample_attractions = [1, 3, 15]
                        
                        for attraction_index in sample_attractions:
                            try:
                                attraction_name = self.attractions.get(attraction_index, f"アトラクション{attraction_index}")
                                print(f"🎢 {attraction_name} のテストクリック中...")
                                
                                # 広告を再度除去してからクリック
                                self.remove_ads()
                                time.sleep(1)
                                
                                attraction_element = self.driver.find_element(
                                    By.XPATH, f"//td[@onclick='createAT2({attraction_index})']"
                                )
                                
                                self.driver.execute_script("arguments[0].click();", attraction_element)
                                print(f"  ✅ {attraction_name} クリック成功")
                                time.sleep(2)
                                
                            except Exception as e:
                                print(f"  ❌ {attraction_name} クリックエラー: {str(e)[:100]}")
                                continue
                                
                    else:
                        print(f"❌ {target_year}年{target_month}月にはデータがありません")
                        
                else:
                    print("❌ 日付情報を取得できませんでした")
                    
            else:
                print(f"❌ {target_year}年{target_month}月への移動に失敗")
                
        except Exception as e:
            print(f"❌ スクレイピングエラー: {e}")
            
        finally:
            self.stop_driver()
            
        return len(createat2_elements) > 0 if 'createat2_elements' in locals() else False

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com 広告ブロック対応スクレイピング")
    print("=" * 70)
    
    scraper = YosocalAdBlockScraper()
    
    # 複数の月をテスト
    test_months = [
        (2025, 1),   # 1月
        (2025, 7),   # 7月（データありの確認）
        (2024, 12),  # 12月
    ]
    
    try:
        for year, month in test_months:
            print(f"\n📅 === {year}年{month}月 テスト ===")
            has_data = scraper.scrape_single_month(year, month)
            
            if has_data:
                print(f"✅ {year}年{month}月: データあり")
            else:
                print(f"❌ {year}年{month}月: データなし")
                
            time.sleep(3)  # 次のテストまで待機
        
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main() 