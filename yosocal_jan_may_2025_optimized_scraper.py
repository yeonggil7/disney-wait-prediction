#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
2025年1月〜5月全日分データ取得バッチスクリプト（高速版）
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
    """高速化されたWebDriverセットアップ"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')  # 画像読み込み無効
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--page-load-strategy=eager')  # ページ読み込み最適化
    options.add_argument('--disable-logging')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-background-networking')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(15)  # タイムアウト調整
    return driver

def scrape_date_optimized(driver, target_date: str):
    """最適化された日付データ取得"""
    try:
        year = int(target_date[:4])
        month = int(target_date[4:6])
        day = int(target_date[6:8])
        
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
        
        # 月移動（現在の月から対象月へ）
        current_month = datetime.now().month
        months_to_go_back = current_month - month
        if year == 2025 and month < current_month:
            for _ in range(months_to_go_back):
                prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
                driver.execute_script("arguments[0].click();", prev_button)
                time.sleep(0.5)  # 短い待機
        
        # 日付クリック
        date_elements = driver.find_elements(By.CLASS_NAME, "CAL")
        for element in date_elements:
            onclick_attr = element.get_attribute("onclick")
            if onclick_attr and f"fMouseclick({target_date}" in onclick_attr:
                driver.execute_script("arguments[0].click();", element)
                time.sleep(1)  # 最小限の待機
                break
        
        # データ抽出
        soup = BeautifulSoup(driver.page_source, 'html.parser')
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
        
        # データ構築（最小限の処理）
        results = []
        for time_slot, row in time_data_rows:
            all_cells = row.find_all('td')
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            
            # セル数による調整
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
        
    except Exception as e:
        print(f"❌ {target_date}: エラー - {str(e)[:50]}")
        return []

def batch_scrape_optimized():
    """最適化されたバッチ処理"""
    print("🚀 高速版バッチ処理開始")
    print("=" * 40)
    
    months_data = [
        (1, 31), (2, 28), (3, 31), (4, 30), (5, 31)
    ]
    
    # 取得済み確認
    existing_files = []
    total_files = 0
    for month, days in months_data:
        for day in range(1, days + 1):
            total_files += 1
            date_str = f"2025{month:02d}{day:02d}"
            csv_file = f"data/yosocal_{date_str}_fixed.csv"
            if os.path.exists(csv_file):
                existing_files.append(date_str)
    
    remaining_dates = []
    for month, days in months_data:
        for day in range(1, days + 1):
            date_str = f"2025{month:02d}{day:02d}"
            if date_str not in existing_files:
                remaining_dates.append(date_str)
    
    print(f"📁 取得済み: {len(existing_files)}件")
    print(f"🎯 残り: {len(remaining_dates)}件")
    
    if not remaining_dates:
        print("✅ 全データ取得済み！")
        return
    
    # WebDriver起動
    driver = setup_driver()
    
    try:
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(2)
        
        success_count = 0
        error_count = 0
        
        for i, date_str in enumerate(remaining_dates):
            print(f"📅 {i+1}/{len(remaining_dates)}: {date_str}", end=" ... ")
            
            results = scrape_date_optimized(driver, date_str)
            
            if results:
                # CSV保存
                df = pd.DataFrame(results)
                csv_filename = f"yosocal_{date_str}_fixed.csv"
                df.to_csv(csv_filename, index=False, encoding='utf-8')
                
                # dataフォルダに移動
                os.rename(csv_filename, f"data/{csv_filename}")
                
                valid_count = len([r for r in results if r['Status'] == 'normal'])
                print(f"✅ {len(results)}件 (有効: {valid_count}件)")
                success_count += 1
            else:
                print(f"❌ エラー")
                error_count += 1
            
            # 短い待機（最小限）
            if i < len(remaining_dates) - 1:
                time.sleep(2)
        
        print(f"\n🎉 処理完了！")
        print(f"✅ 成功: {success_count}件")
        print(f"❌ エラー: {error_count}件")
        print(f"📈 成功率: {success_count/(success_count+error_count)*100:.1f}%")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    batch_scrape_optimized() 