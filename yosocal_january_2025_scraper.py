#!/usr/bin/env python3
"""
yosocal.com 2025年1月専用データ取得スクリプト
ディズニーランド選択確認 + 完全データ抽出機能
"""

import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import re
import calendar

def setup_driver():
    """Chrome WebDriverセットアップ（シンプル版）"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    
    # 広告ブロック設定
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    
    # プロファイル設定
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        # ChromeDriverManagerを使用
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"⚠️ WebDriverManager失敗: {e}")
        
        # 直接Chromeを使用
        try:
            driver = webdriver.Chrome(options=options)
            print("✅ 直接Chrome接続成功")
            return driver
        except Exception as e2:
            print(f"❌ WebDriverセットアップエラー: {e2}")
            raise

def remove_ads_and_overlays(driver):
    """広告とオーバーレイ要素の削除"""
    try:
        driver.execute_script("""
            // 広告要素を削除
            const adSelectors = [
                'iframe[src*="doubleclick"]',
                'iframe[src*="googleadservices"]', 
                'iframe[src*="googlesyndication"]',
                'div[id*="google_ads"]',
                'div[class*="ad-"]',
                '.ad-container',
                '.banner-ad'
            ];
            
            adSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
            
            // オーバーレイ要素を削除
            document.querySelectorAll('div').forEach(el => {
                if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                    if (el.style.zIndex > 1000) {
                        el.remove();
                    }
                }
            });
        """)
        print("🚫 広告・オーバーレイ削除実行")
    except Exception as e:
        print(f"⚠️ 広告削除失敗: {e}")

def navigate_to_january_2025(driver):
    """2025年1月に移動"""
    print("📅 2025年1月への移動開始...")
    
    max_attempts = 15
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # 現在の表示月を確認
            month_element = driver.find_element(By.CLASS_NAME, "TDBT")
            month_text = month_element.text
            print(f"📅 現在表示月: {month_text}")
            
            # 2025年1月かチェック
            if "2025年" in month_text and "1月" in month_text:
                print("✅ 2025年1月に到達しました！")
                return True
            
            # 前月ボタンをクリック
            print("⬅️ 前月ボタンをクリック...")
            prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
            driver.execute_script("arguments[0].click();", prev_button)
            time.sleep(3)
            
            # 広告削除
            remove_ads_and_overlays(driver)
            attempts += 1
            
        except Exception as e:
            print(f"⚠️ 月移動エラー: {e}")
            attempts += 1
            time.sleep(2)
    
    print("❌ 2025年1月への移動に失敗しました")
    return False

def safe_click_date(driver, date_str, day):
    """安全な日付クリック（JavaScript使用）"""
    try:
        # 広告削除
        remove_ads_and_overlays(driver)
        time.sleep(1)
        
        # ページスクロール調整
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.4);")
        time.sleep(1)
        
        # 複数の方法で日付要素を検索してクリック
        click_scripts = [
            f"""
            // onclick属性でdateと一致する要素を探す
            var elements = document.querySelectorAll('[onclick*="fMouseclick({date_str},"]');
            if (elements.length > 0) {{
                elements[0].click();
                return true;
            }}
            return false;
            """,
            f"""
            // 日付テキストとCSSクラスで検索
            var dayElements = document.querySelectorAll('.CAL, .CALSAT, .CALSUN');
            for (var i = 0; i < dayElements.length; i++) {{
                if (dayElements[i].textContent.trim() === '{day}') {{
                    dayElements[i].click();
                    return true;
                }}
            }}
            return false;
            """,
            f"""
            // div要素を全て検索
            var allDivs = document.querySelectorAll('div');
            for (var i = 0; i < allDivs.length; i++) {{
                var div = allDivs[i];
                if (div.textContent.trim() === '{day}') {{
                    if (div.onclick && div.onclick.toString().includes('{date_str}')) {{
                        div.click();
                        return true;
                    }}
                }}
            }}
            return false;
            """
        ]
        
        for script in click_scripts:
            try:
                result = driver.execute_script(script)
                if result:
                    print(f"✅ 日付{day}をクリック成功")
                    return True
            except:
                continue
        
        print(f"❌ 日付{day}のクリックに失敗")
        return False
        
    except Exception as e:
        print(f"❌ 日付クリックエラー: {e}")
        return False

def extract_table_data(driver, target_date):
    """テーブルデータの抽出"""
    try:
        # データ読み込み待機
        time.sleep(3)
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # jamatテーブルを探す
        jamat_div = soup.find('div', {'id': 'jamat'})
        if not jamat_div:
            print("❌ jamatテーブルが見つかりません")
            return []
        
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブルが見つかりません")
            return []
        
        rows = table.find_all('tr')
        
        # ディズニーランドアトラクション名
        attractions = [
            'オムニバス', 'リバ鉄道', 'カリブの海賊', 'ジャングル', 'ツリハウス',
            '魅惑のチキルム', 'ビッグサンダ', 'Ｓギャラリ', 'ベア・シアタ', 'いかだ',
            'スプラッシュ', 'イッツ・ア・ス', 'ホーンテッド', 'プーさん', 'ホール・オ・',
            'スペマン', 'バズ', 'モンスタ', 'スタージェ', 'ニモ',
            'インディ', 'レイジング', 'タワ・オブ・テ', 'ＪニーＣ', 'アクアト',
            'ビッグバンド', 'トイマニ', 'ニモ＆フレンズ', 'タートル', 'マメマン',
            'アリエル', 'フランダ', 'ブロホ', 'マジック', 'Ｓア',
            'エレクト', 'ディズニー', 'インクマン', 'Ｆファン', 'ゴー',
            'アブーズ', 'ジャスミン'
        ]
        
        all_data = []
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= 1:
                continue
            
            # 時間セル
            time_cell = cells[0]
            time_text = time_cell.get_text(strip=True)
            
            # 時間形式のチェック
            if not time_text or ':' not in time_text:
                continue
            
            print(f"🕐 時間帯: {time_text}")
            
            # データセル（時間セルを除く）
            data_cells = cells[1:]
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    cell_text = cell.get_text(strip=True)
                    css_classes = cell.get('class', [])
                    
                    wait_time = cell_text if cell_text and cell_text != '-' else '-'
                    status = 'active' if wait_time != '-' and wait_time.isdigit() else 'no_data'
                    
                    all_data.append({
                        'Attraction': attractions[i],
                        'WaitTime': wait_time,
                        'Status': status,
                        'Time': time_text,
                        'Date': target_date,
                        'CSSClasses': ' '.join(css_classes) if css_classes else '',
                        'RawValue': cell_text
                    })
        
        print(f"📊 抽出データ数: {len(all_data)}件")
        valid_count = len([d for d in all_data if d['WaitTime'] != '-'])
        print(f"✅ 有効待ち時間: {valid_count}件")
        
        return all_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def save_data_to_csv(data, filename):
    """CSVファイルに保存"""
    try:
        # dataディレクトリを作成
        os.makedirs('data', exist_ok=True)
        
        df = pd.DataFrame(data)
        filepath = os.path.join('data', filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"💾 {filepath} に保存完了")
        print(f"📋 データサンプル:")
        print(df.head(10).to_string(index=False))
        
        return True
    except Exception as e:
        print(f"❌ CSV保存エラー: {e}")
        return False

def scrape_january_2025():
    """2025年1月データ取得メイン処理"""
    print("🚀 2025年1月ディズニーランドデータ取得開始")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        # realtime.htmに接続
        print("🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # 初期読み込み待機と広告削除
        time.sleep(5)
        remove_ads_and_overlays(driver)
        
        # 2025年1月に移動
        if not navigate_to_january_2025(driver):
            print("❌ 2025年1月への移動に失敗しました")
            return
        
        # 1月の日数を取得
        days_in_january = calendar.monthrange(2025, 1)[1]  # 31日
        print(f"📅 2025年1月処理開始 ({days_in_january}日)")
        
        success_count = 0
        error_count = 0
        
        for day in range(1, days_in_january + 1):
            date_str = f"2025{1:02d}{day:02d}"
            filename = f"yosocal_{date_str}_fixed.csv"
            filepath = os.path.join('data', filename)
            
            # 既存ファイルチェック
            if os.path.exists(filepath):
                print(f"📁 1月{day:02d}日: 既存ファイルをスキップ")
                success_count += 1
                continue
            
            print(f"🔄 1月{day:02d}日: 処理中...")
            
            # 日付をクリック
            if safe_click_date(driver, date_str, str(day)):
                # データ抽出
                data = extract_table_data(driver, date_str)
                
                if data and len(data) > 0:
                    # CSV保存
                    if save_data_to_csv(data, filename):
                        valid_count = len([d for d in data if d['WaitTime'] != '-'])
                        print(f"✅ 1月{day:02d}日: {len(data)}件 (有効: {valid_count}件)")
                        success_count += 1
                    else:
                        print(f"❌ 1月{day:02d}日: 保存失敗")
                        error_count += 1
                else:
                    print(f"❌ 1月{day:02d}日: データなし")
                    error_count += 1
            else:
                print(f"❌ 1月{day:02d}日: 日付クリック失敗")
                error_count += 1
            
            # 次の処理まで待機
            time.sleep(2)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print(f"🎉 2025年1月処理完了！")
        print(f"✅ 成功: {success_count}日")
        print(f"❌ エラー: {error_count}日")
        total_days = success_count + error_count
        success_rate = (success_count / total_days * 100) if total_days > 0 else 0
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"📁 保存場所: ./data/ フォルダ")
        
    except Exception as e:
        print(f"❌ 処理エラー: {e}")
    finally:
        print("🔧 WebDriver終了...")
        driver.quit()

if __name__ == "__main__":
    scrape_january_2025() 