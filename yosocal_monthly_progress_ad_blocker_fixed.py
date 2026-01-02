#!/usr/bin/env python3
"""
yosocal.com 月単位進行スクリプト（広告対策版）- ディズニーランド選択修正版
週末対応 + 月単位処理 + 広告ブロック + ディズニーランド確実選択
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
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
from tqdm import tqdm
import calendar

def setup_chrome_driver():
    """Chrome WebDriverセットアップ（広告ブロック強化版）"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 広告ブロック設定（強化版）
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    # chrome_options.add_argument("--disable-javascript")  # JavaScriptを無効にすると動作しない
    chrome_options.add_argument("--block-new-web-contents")
    chrome_options.add_argument("--disable-popup-blocking")
    
    # 広告関連ドメインブロック
    chrome_options.add_argument("--host-rules=MAP *.doubleclick.net 127.0.0.1")
    chrome_options.add_argument("--host-rules=MAP *.googleadservices.com 127.0.0.1")
    chrome_options.add_argument("--host-rules=MAP *.googlesyndication.com 127.0.0.1")
    chrome_options.add_argument("--host-rules=MAP *.googletagmanager.com 127.0.0.1")
    chrome_options.add_argument("--host-rules=MAP *.google-analytics.com 127.0.0.1")
    
    # プリファレンス設定
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        # WebDriverManagerを使用してバージョン対応
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"❌ WebDriverセットアップ失敗: {e}")
        raise

def remove_ads_javascript(driver):
    """JavaScript実行による広告除去"""
    try:
        # iframeと広告要素を除去
        ad_removal_script = """
        // Google Ads iframes除去
        var iframes = document.querySelectorAll('iframe[src*="doubleclick"], iframe[src*="googleads"], iframe[id*="aswift"]');
        iframes.forEach(function(iframe) {
            iframe.remove();
        });
        
        // 広告divs除去
        var adDivs = document.querySelectorAll('div[id*="google_ads"], div[class*="adsbygoogle"]');
        adDivs.forEach(function(div) {
            div.remove();
        });
        
        // 広告オーバーレイ除去
        var overlays = document.querySelectorAll('div[style*="position: fixed"], div[style*="z-index"]');
        overlays.forEach(function(overlay) {
            if (overlay.offsetHeight > 50 && overlay.offsetWidth > 500) {
                overlay.remove();
            }
        });
        
        return 'ads_removed';
        """
        
        result = driver.execute_script(ad_removal_script)
        if result:
            print("🚫 JavaScript広告除去実行")
        
    except Exception as e:
        print(f"⚠️ JavaScript広告除去エラー: {e}")

def safe_click_with_js(driver, element, description="要素"):
    """JavaScript実行による安全なクリック"""
    try:
        # 広告除去
        remove_ads_javascript(driver)
        
        # JavaScriptでの直接クリック
        driver.execute_script("arguments[0].click();", element)
        print(f"✅ {description}: JavaScript直接クリック成功")
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"❌ {description}: JavaScript クリック失敗: {e}")
        return False

def navigate_to_month(driver, target_year, target_month):
    """指定された年月にカレンダーを移動（広告対策版）"""
    print(f"📅 {target_year}年{target_month}月への移動開始...")
    
    max_attempts = 24  # 最大2年分
    
    for attempt in range(max_attempts):
        try:
            # 広告除去
            remove_ads_javascript(driver)
            time.sleep(1)
            
            # 現在の表示月を取得
            month_element = driver.find_element(By.CLASS_NAME, "CAL_YM")
            current_month_text = month_element.text.strip()
            print(f"📅 現在表示月: {current_month_text}")
            
            # 年月解析
            match = re.search(r'(\d{4})年\s*(\d{1,2})月', current_month_text)
            if not match:
                print(f"⚠️ 月表示解析失敗: {current_month_text}")
                time.sleep(2)
                continue
                
            current_year = int(match.group(1))
            current_month = int(match.group(2))
            
            print(f"🗓️ 現在表示: {current_year}年{current_month}月")
            print(f"🎯 目標: {target_year}年{target_month}月")
            
            # 目標月に到達チェック
            if current_year == target_year and current_month == target_month:
                print("✅ 目標の月に到達しました！")
                return True
            
            # ナビゲーション方向決定
            if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                # 前月ボタン
                print("⬅️ 前月ボタンをクリック...")
                prev_button = driver.find_element(By.CLASS_NAME, "CAL_PREV")
                if not safe_click_with_js(driver, prev_button, "前月ボタン"):
                    time.sleep(3)
                    continue
            else:
                # 次月ボタン
                print("➡️ 次月ボタンをクリック...")
                next_button = driver.find_element(By.CLASS_NAME, "CAL_NEXT")
                if not safe_click_with_js(driver, next_button, "次月ボタン"):
                    time.sleep(3)
                    continue
            
            # 移動完了待機
            time.sleep(3)
            
        except Exception as e:
            print(f"⚠️ 月移動エラー (試行 {attempt+1}): {e}")
            time.sleep(2)
    
    print(f"❌ {target_year}年{target_month}月への移動に失敗しました")
    return False

def click_date_with_retry(driver, date_str):
    """日付クリック（広告対策・リトライ機能付き）"""
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            print(f"📅 日付クリック試行 {attempt+1}/{max_attempts}: {date_str}")
            
            # 広告除去
            remove_ads_javascript(driver)
            
            # ページスクロール（広告回避）
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            
            # 日付要素検索（複数クラス対応）
            date_selectors = [
                f"div.CAL[onclick*='{date_str}']",
                f"div.CALSAT[onclick*='{date_str}']", 
                f"div.CALSUN[onclick*='{date_str}']"
            ]
            
            date_element = None
            for selector in date_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        date_element = elements[0]
                        print(f"✅ 日付要素発見: {selector}")
                        break
                except:
                    continue
            
            if not date_element:
                print(f"❌ 日付要素が見つかりません: {date_str}")
                return False
            
            # JavaScriptによる直接クリック
            if safe_click_with_js(driver, date_element, f"日付{date_str}"):
                time.sleep(5)  # データ読み込み待機
                return True
            
        except ElementClickInterceptedException as e:
            print(f"⚠️ 要素クリック妨害 (試行 {attempt+1}): {str(e)[:100]}...")
            
            # より強力な広告除去
            remove_ads_javascript(driver)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ 日付クリックエラー (試行 {attempt+1}): {e}")
            time.sleep(2)
    
    print(f"❌ 日付クリック最終失敗: {date_str}")
    return False

def extract_table_data(driver, date_str):
    """テーブルデータ抽出（yosocal_monthly_progress_scraper.pyベース）"""
    try:
        # ページソース取得
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # jamatテーブル確認
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamat div未発見")
            return []
        
        table = jamat_div.find('table')
        if not table:
            print("❌ jamat table未発見")
            return []
        
        rows = table.find_all('tr')
        print(f"📊 テーブル行数: {len(rows)}")
        
        # アトラクション名抽出
        attractions = []
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                for cell in fph2_cells:
                    attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                    if attraction_name and attraction_name not in attractions:
                        attractions.append(attraction_name)
                break
        
        print(f"🎯 アトラクション数: {len(attractions)}")
        if len(attractions) == 0:
            print("❌ アトラクション名が取得できませんでした")
            return []
        
        # 時間データ行抽出
        time_data_rows = []
        seen_times = set()
        
        for row in rows:
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
            time_text = None
            if fpm_cell:
                time_text = fpm_cell.get_text(strip=True)
                if re.match(r'^\d{2}:\d{2}$', time_text) and time_text not in seen_times:
                    time_data_rows.append((time_text, row))
                    seen_times.add(time_text)
            elif fpt_cell:
                time_text = fpt_cell.get_text(strip=True)
                if time_text == '平均' and time_text not in seen_times:
                    time_data_rows.append((time_text, row))
                    seen_times.add(time_text)
        
        print(f"⏰ 時間帯数: {len(time_data_rows)}")
        
        # データ抽出
        all_data = []
        total_records = 0
        valid_data = 0
        
        for time_slot, row in time_data_rows:
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    attraction = attractions[i]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    # 待ち時間解析
                    wait_time = None
                    status = "unknown"
                    
                    if cell_text == "-" or cell_text == "" or cell_text == "　":
                        status = "no_data"
                    elif re.match(r'^\d+$', cell_text):
                        wait_time = float(cell_text)
                        status = "normal"
                        valid_data += 1
                    else:
                        status = "other"
                    
                    # データ記録
                    record = {
                        'Attraction': attraction,
                        'WaitTime': wait_time if wait_time is not None else '-',
                        'Status': status,
                        'Time': time_slot,
                        'Date': date_str,
                        'CSSClasses': css_classes,
                        'RawValue': cell_text
                    }
                    all_data.append(record)
                    total_records += 1
        
        print(f"📊 データ抽出結果: {total_records}件 (有効: {valid_data}件)")
        return all_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def process_month(driver, year, month):
    """月単位処理（広告対策版）"""
    print(f"📅 {year}年{month}月 処理開始")
    
    # 対象月に移動
    if not navigate_to_month(driver, year, month):
        return 0, 0
    
    # 月の日数取得
    days_in_month = calendar.monthrange(year, month)[1]
    print(f"📅 {year}年{month}月処理開始 ({days_in_month}日)")
    
    success_count = 0
    error_count = 0
    
    # プログレスバー
    pbar = tqdm(range(1, days_in_month + 1), desc=f"{month:02d}月処理")
    
    for day in pbar:
        date_str = f"{year}{month:02d}{day:02d}"
        output_file = f"data/yosocal_{date_str}_fixed.csv"
        
        # 既存ファイルチェック
        if os.path.exists(output_file):
            pbar.set_postfix_str(f"📁 {month:02d}月{day:02d}日: スキップ済み")
            success_count += 1
            continue
        
        try:
            pbar.set_postfix_str(f"🔄 {month:02d}月{day:02d}日: 処理中...")
            
            # 日付クリック
            if not click_date_with_retry(driver, date_str):
                pbar.set_postfix_str(f"❌ {month:02d}月{day:02d}日: 日付クリック失敗")
                error_count += 1
                continue
            
            # データ抽出
            data = extract_table_data(driver, date_str)
            
            if data:
                # CSV保存
                os.makedirs('data', exist_ok=True)
                df = pd.DataFrame(data)
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                valid_count = len([r for r in data if r['Status'] == 'normal'])
                pbar.set_postfix_str(f"✅ {month:02d}月{day:02d}日: {len(data)}件 (有効: {valid_count}件)")
                success_count += 1
            else:
                pbar.set_postfix_str(f"❌ {month:02d}月{day:02d}日: データなし")
                error_count += 1
            
        except Exception as e:
            pbar.set_postfix_str(f"❌ {month:02d}月{day:02d}日: エラー")
            error_count += 1
            print(f"❌ {date_str}エラー: {e}")
        
        # 短時間待機
        time.sleep(1)
    
    pbar.close()
    print(f"📊 {year}年{month}月完了: 成功{success_count}件, エラー{error_count}件")
    return success_count, error_count

def main():
    """メイン処理"""
    print("🚀 月単位高速バッチ処理開始（ディズニーランド選択修正版）")
    print("="*50)
    
    driver = None
    total_success = 0
    total_error = 0
    
    try:
        # WebDriverセットアップ
        driver = setup_chrome_driver()
        
        # realtime.htmページにアクセス
        print(f"🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(5)
        
        # 🔥 ディズニーランド選択確認（修正箇所）
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # 完全読み込み待機
        time.sleep(5)
        
        # 月別処理（2025年1月〜5月）
        target_months = [
            (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5)
        ]
        
        for year, month in target_months:
            print(f"📅 {year}年{month}月への移動開始...")
            
            if navigate_to_month(driver, year, month):
                print(f"✅ {year}年{month}月に移動完了")
                success, error = process_month(driver, year, month)
                total_success += success
                total_error += error
            else:
                print(f"❌ {year}年{month}月への移動失敗")
                total_error += calendar.monthrange(year, month)[1]
            
            print(f"📈 累計: 成功{total_success}件, エラー{total_error}件")
        
        print("🎉 全処理完了！")
        print(f"✅ 総成功: {total_success}件")
        print(f"❌ 総エラー: {total_error}件")
        print(f"📈 成功率: {total_success/(total_success+total_error)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ メインエラー: {e}")
        
    finally:
        if driver:
            print("🔧 WebDriver終了...")
            driver.quit()

if __name__ == "__main__":
    main() 