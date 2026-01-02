#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
月単位高速バッチ処理スクリプト（広告対策版）
- カレンダー部分：土日対応修正版
- テーブル部分：既存の動作確認済み方式
- 広告対策：JavaScript直接クリック、広告ブロック
"""

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re

def setup_driver():
    """高速WebDriverセットアップ（広告対策版）"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--page-load-strategy=eager')
    
    # 広告ブロック対策
    options.add_argument('--block-new-web-contents')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    
    # プロファイル設定で広告をブロック
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def remove_ads(driver):
    """広告要素を削除"""
    try:
        # Google広告のiframeを削除
        driver.execute_script("""
            var ads = document.querySelectorAll('iframe[src*="googleads"], iframe[src*="doubleclick"]');
            for (var i = 0; i < ads.length; i++) {
                ads[i].style.display = 'none';
                ads[i].remove();
            }
            
            // その他の広告要素も削除
            var adElements = document.querySelectorAll('[id*="ad"], [class*="ad"], [id*="banner"], [class*="banner"]');
            for (var i = 0; i < adElements.length; i++) {
                if (adElements[i].offsetHeight > 50 || adElements[i].offsetWidth > 200) {
                    adElements[i].style.display = 'none';
                }
            }
        """)
        print("🛡️ 広告要素を削除しました")
    except Exception as e:
        print(f"⚠️ 広告削除エラー: {e}")

def navigate_to_month(driver, target_year, target_month):
    """指定された年月に移動（動作確認済み方式）"""
    print(f"📅 {target_year}年{target_month}月への移動開始...")
    
    max_month_moves = 12
    month_move_count = 0
    
    while month_move_count < max_month_moves:
        try:
            month_element = driver.find_element(By.CLASS_NAME, "TDBT")
            month_text = month_element.text
            print(f"📅 現在表示月: {month_text}")
            
            if "年" in month_text and "月" in month_text:
                year_match = re.search(r'(\d{4})年', month_text)
                month_match = re.search(r'(\d{1,2})月', month_text)
                
                if year_match and month_match:
                    current_year = int(year_match.group(1))
                    current_month = int(month_match.group(1))
                    
                    if current_year == target_year and current_month == target_month:
                        print("✅ 目標の月に到達しました！")
                        return True
                    
                    if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                        print("⬅️ 前月ボタンをクリック...")
                        prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
                        driver.execute_script("arguments[0].click();", prev_button)
                    else:
                        print("➡️ 次月ボタンをクリック...")
                        next_button = driver.find_element(By.XPATH, "//input[@value='次月']")
                        driver.execute_script("arguments[0].click();", next_button)
                    
                    time.sleep(3)
                    # 月移動後に広告削除
                    remove_ads(driver)
                    month_move_count += 1
                else:
                    print("⚠️ 月の形式を解析できませんでした")
                    break
            else:
                print("⚠️ 月表示要素が見つかりません")
                break
                
        except Exception as e:
            print(f"⚠️ 月移動処理エラー: {e}")
            break
    
    return False

def get_month_data(driver, soup):
    """月データを取得（既存方式）"""
    try:
        jamat_div = soup.find('div', {'id': 'jamat'})
        if not jamat_div:
            return []
        
        table = jamat_div.find('table')
        if not table:
            return []
        
        rows = table.find_all('tr')
        time_data_rows = []
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                time_cell = cells[0]
                time_text = time_cell.get_text(strip=True)
                if time_text and ':' in time_text:
                    time_data_rows.append((time_text, row))
        
        return time_data_rows
    except Exception as e:
        print(f"❌ データ抽出エラー: {str(e)[:50]}")
        return []

def extract_date_data(time_data_rows, target_date):
    """日付別データ抽出（既存方式）"""
    all_data = []
    
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
    
    for time_slot, row in time_data_rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) > 1:
            data_cells = cells[1:]  # 最初の時間セルを除く
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    cell_text = cell.get_text(strip=True)
                    css_classes = cell.get('class', [])
                    
                    all_data.append({
                        'Attraction': attractions[i],
                        'WaitTime': cell_text if cell_text else '-',
                        'Status': 'no_data' if cell_text == '-' or not cell_text else 'active',
                        'Time': time_slot,
                        'Date': target_date,
                        'CSSClasses': ' '.join(css_classes) if css_classes else '',
                        'RawValue': cell_text
                    })
    
    return all_data

def save_to_csv(data, filename):
    """CSVファイルに保存"""
    df = pd.DataFrame(data)
    os.makedirs('data', exist_ok=True)
    df.to_csv(filename, index=False, encoding='utf-8')

def click_date_js(driver, date_str, day):
    """JavaScript経由での確実な日付クリック（広告対策版）"""
    try:
        # 広告を削除
        remove_ads(driver)
        
        # ページを少し上にスクロールして広告を避ける
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
        time.sleep(1)
        
        # JavaScript直接実行でクリック
        js_click = f"""
            // onclick属性でdateと一致する要素を探す
            var elements = document.querySelectorAll('[onclick*="fMouseclick({date_str},"]');
            if (elements.length > 0) {{
                elements[0].click();
                return true;
            }}
            
            // テキスト内容とonclick属性の組み合わせで検索
            var allDivs = document.querySelectorAll('div');
            for (var i = 0; i < allDivs.length; i++) {{
                var div = allDivs[i];
                if (div.textContent.trim() === '{day}') {{
                    var parent = div.parentElement;
                    if (parent && parent.onclick && parent.onclick.toString().includes('{date_str}')) {{
                        parent.click();
                        return true;
                    }}
                }}
            }}
            return false;
        """
        
        result = driver.execute_script(js_click)
        return result
        
    except Exception as e:
        print(f"⚠️ JSクリックエラー: {e}")
        return False

def process_single_month(year, month, days_in_month):
    """1つの月を処理する（広告対策版）"""
    driver = setup_driver()
    
    try:
        print(f"🌐 realtime.htmに接続中...")
driver.get("https://yosocal.com/realtime.htm")
time.sleep(3)

# ディズニーランド選択確認
try:
    land_radio = driver.find_element(By.ID, "park1")
    if not land_radio.is_selected():
        land_radio.click()
        time.sleep(2)
    print("✅ ディズニーランド選択確認")
except Exception as e:
    print(f"⚠️ パーク選択失敗: {e}")
time.sleep(3)

# ディズニーランド選択確認
try:
    land_radio = driver.find_element(By.ID, "park1")
    if not land_radio.is_selected():
        land_radio.click()
        time.sleep(2)
    print("✅ ディズニーランド選択確認")
except Exception as e:
    print(f"⚠️ パーク選択失敗: {e}")
        time.sleep(3)

        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        time.sleep(3)
        
        # 初期広告削除
        remove_ads(driver)
        
        # 月移動
        if not navigate_to_month(driver, year, month):
            print(f"❌ {year}年{month}月への移動失敗")
            return 0, 0
        
        print(f"📅 {year}年{month}月処理開始 ({days_in_month}日)")
        success_count = 0
        error_count = 0
        
        for day in range(1, days_in_month + 1):
            date_str = f"{year}{month:02d}{day:02d}"
            csv_filename = f"data/yosocal_{date_str}_fixed.csv"
            
            # 既存ファイルチェック
            if os.path.exists(csv_filename):
                print(f"📁 {month:02d}月{day:02d}日: 既存ファイルをスキップ")
                success_count += 1
                continue
            
            print(f"🔄 {month:02d}月{day:02d}日: 処理中...", end=" ")
            
            try:
                # JavaScript経由での確実なクリック
                if click_date_js(driver, date_str, day):
                    # データ読み込み待機
                    time.sleep(2)
                    
                    # データ処理（既存方式）
                    html_content = driver.page_source
                    all_data = extract_date_data(get_month_data(driver, BeautifulSoup(html_content, 'html.parser')), date_str)
                    
                    if all_data and len(all_data) > 0:
                        save_to_csv(all_data, csv_filename)
                        valid_count = len([d for d in all_data if d['WaitTime'] != '-'])
                        print(f"✅ {len(all_data)}件 (有効: {valid_count}件)")
                        success_count += 1
                    else:
                        print("❌ データなし")
                        error_count += 1
                else:
                    print("❌ 日付要素なし")
                    error_count += 1
                
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
                error_count += 1
                
            time.sleep(1)  # 次処理まで短時間待機
        
        print(f"📊 {year}年{month}月完了: 成功{success_count}件, エラー{error_count}件")
        return success_count, error_count
        
    finally:
        driver.quit()

def monthly_batch_scraper():
    """月単位バッチ処理メイン関数（広告対策版）"""
    print("🚀 月単位高速バッチ処理開始（広告対策版）")
    print("=" * 50)
    
    # 処理対象月
    target_months = [
        (2025, 1, 31),   # 1月
        (2025, 2, 28),   # 2月
        (2025, 3, 31),   # 3月
        (2025, 4, 30),   # 4月
        (2025, 5, 31),   # 5月
    ]
    
    total_success = 0
    total_error = 0
    
    for year, month, days in target_months:
        print(f"🗓️ {year}年{month}月 開始...")
        success, error = process_single_month(year, month, days)
        total_success += success
        total_error += error
        print(f"📈 累計: 成功{total_success}件, エラー{total_error}件")
    
    print(f"🎉 全処理完了！")
    print(f"✅ 総成功: {total_success}件")
    print(f"❌ 総エラー: {total_error}件")
    success_rate = (total_success / (total_success + total_error) * 100) if (total_success + total_error) > 0 else 0
    print(f"📈 成功率: {success_rate:.1f}%")

if __name__ == "__main__":
    monthly_batch_scraper() 