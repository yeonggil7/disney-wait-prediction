#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
月単位高速バッチ処理スクリプト（月ごとWebDriver再起動版）
各月ごとにWebDriverを再起動して確実な処理を実現
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
    """高速WebDriverセットアップ"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--page-load-strategy=eager')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-notifications')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(15)
    return driver

def navigate_to_month(driver, year, month):
    """指定された年月に移動"""
    print(f"📅 {year}年{month}月への移動開始...")
    
    # realtime.htmに移動
    driver.get("https://yosocal.com/realtime.htm")
    time.sleep(3)
    
    # 現在の月を取得（現在は7月と仮定）
    current_month = 7  # 2025年7月
    target_month = month
    
    # 目標月まで前月ボタンをクリック
    months_to_go_back = current_month - target_month
    
    if months_to_go_back > 0:
        for _ in range(months_to_go_back):
            try:
                prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
                driver.execute_script("arguments[0].click();", prev_button)
                time.sleep(1)
            except Exception as e:
                print(f"❌ 月移動エラー: {e}")
                return False
    
    print(f"✅ {year}年{month}月に移動完了")
    return True

def get_month_data(driver, soup):
    """現在表示されているページからデータを抽出"""
    try:
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return []
        
        table = jamat_div.find('table')
        if not table:
            return []
        
        rows = table.find_all('tr')
        time_data_rows = []
        
        for row in rows:
            time_cell = row.find('td', class_='FPM')
            if time_cell:
                time_text = time_cell.get_text(strip=True)
                if ':' in time_text:
                    time_data_rows.append((time_text, row))
        
        return time_data_rows
    except Exception as e:
        print(f"❌ データ抽出エラー: {str(e)[:50]}")
        return []

def extract_date_data(time_data_rows, target_date):
    """時間帯データからCSV用データを構築"""
    # アトラクション名（固定）
    attractions = [
        'オムニバス', 'リバ鉄道', 'カリブの海賊', 'ジャングル', 'ツリハウス',
        '魅惑のチキルム', 'ビッグサンダ', 'Ｓギャラリ', 'ベア・シアタ', 'いかだ',
        'スプラッシュ', 'カヌ探検', 'ビーバー', 'ウエスタンランド', 'シューティング',
        'ワンマンズ', 'ホンテッド', 'イッツ', 'ピノキオ', 'ホワイト',
        'ピーター', 'ミッキー', 'プーさん', 'ハニハント', '蒸気船',
        'ガジェット', 'グーフィー', 'ドナルド', 'トゥーン', 'ロジャー',
        'シンデレラ', 'アリス', 'スタージェット', 'ダンボ', 'ティー',
        'メリー', 'モンスターズ', 'バズ', 'ペニー', 'ナイトメア',
        'ベイマックス', 'ミニー'
    ]
    
    results = []
    for time_slot, row in time_data_rows:
        all_cells = row.find_all('td')
        data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
        
        # セル数による調整（気温セル対応）
        start_index = 1 if len(all_cells) == 45 else 0
        processed_cells = data_cells[start_index:]
        
        for i, cell in enumerate(processed_cells):
            if i < len(attractions):
                cell_text = cell.get_text(strip=True)
                wait_time = cell_text if cell_text and cell_text != '-' else '-'
                status = 'normal' if wait_time != '-' else 'no_data'
                
                results.append({
                    'Attraction': attractions[i],
                    'WaitTime': wait_time,
                    'Status': status,
                    'Time': time_slot,
                    'Date': target_date,
                    'CSSClasses': cell.get('class', [''])[0] if cell.get('class') else '',
                    'RawValue': cell_text
                })
    
    return results

def process_single_month(year, month, days_in_month):
    """1つの月を処理する"""
    driver = setup_driver()
    
    try:
        print(f"🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        # 月移動
        navigate_to_month(driver, year, month)
        
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
                # 日付クリック（修正版：平日・土日対応）
                date_elements = []
                
                # 平日、土曜、日曜の全クラスを検索
                for class_name in ["CAL", "CALSAT", "CALSUN"]:
                    elements = driver.find_elements(By.CLASS_NAME, class_name)
                    date_elements.extend(elements)
                
                clicked = False
                
                # onclick属性での検索
                for element in date_elements:
                    onclick_attr = element.get_attribute("onclick")
                    if onclick_attr and f"fMouseclick({date_str}," in onclick_attr:
                        element.click()
                        clicked = True
                        break
                
                # 代替検索：要素のテキスト内容
                if not clicked:
                    for element in date_elements:
                        if element.text.strip() == str(day):
                            # 親要素のonclick属性をチェック
                            parent = element.find_element(By.XPATH, "..")
                            onclick_attr = parent.get_attribute("onclick") 
                            if onclick_attr and f"fMouseclick({date_str}," in onclick_attr:
                                parent.click()
                                clicked = True
                                break
                
                if not clicked:
                    print("❌ 日付要素なし")
                    error_count += 1
                    continue
                
                # データ読み込み待機
                time.sleep(2)
                
                # データ処理
                html_content = driver.page_source
                all_data = extract_date_data(get_month_data(driver, BeautifulSoup(html_content, 'html.parser')), date_str)
                
                if all_data and len(all_data) > 0:
                    df = pd.DataFrame(all_data)
                    df.to_csv(csv_filename, index=False, encoding='utf-8')
                    valid_count = len([d for d in all_data if d['Status'] == 'normal'])
                    print(f"✅ {len(all_data)}件 (有効: {valid_count}件)")
                    success_count += 1
                else:
                    print("❌ データなし")
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
    """月単位高速バッチ処理メイン（月ごとWebDriver再起動版）"""
    print("🚀 月単位高速バッチ処理開始（月ごとWebDriver再起動版）")
    print("=" * 60)
    
    # 処理対象月の定義
    months_data = [
        (2025, 1, 31), (2025, 2, 28), (2025, 3, 31), 
        (2025, 4, 30), (2025, 5, 31)
    ]
    
    total_success = 0
    total_error = 0
    
    try:
        for year, month, days_in_month in months_data:
            # 各月を独立したWebDriverセッションで処理
            month_success, month_error = process_single_month(year, month, days_in_month)
            total_success += month_success
            total_error += month_error
            
            # 進捗表示
            print(f"📈 累計: 成功{total_success}件, エラー{total_error}件")
            
            # 月間処理間隔（WebDriver再起動の準備時間）
            if month < 5:  # 最後の月でなければ
                print("⏳ 次の月の準備のため3秒待機...")
                time.sleep(3)
        
        print(f"\n🎉 全処理完了！")
        print(f"✅ 総成功: {total_success}件")
        print(f"❌ 総エラー: {total_error}件")
        if total_success + total_error > 0:
            print(f"📈 成功率: {total_success/(total_success+total_error)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ 致命的エラー: {e}")

if __name__ == "__main__":
    monthly_batch_scraper() 