#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
月単位高速バッチ処理スクリプト（土日対応修正版）
平日・土日の全てに対応し、正しい日付要素検索を実装
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
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def navigate_to_month(driver, target_year, target_month):
    """指定された年月に移動（動作確認済み方式）"""
    print(f"📅 {target_year}年{target_month}月への移動開始...")
    
    max_month_moves = 12
    month_move_count = 0
    
    while month_move_count < max_month_moves:
        # 現在表示されている月を確認
        try:
            month_element = driver.find_element(By.CLASS_NAME, "TDBT")
            month_text = month_element.text
            print(f"📅 現在表示月: {month_text}")
            
            if "年" in month_text and "月" in month_text:
                # "2025年 7月" のような形式から年月を抽出
                year_match = re.search(r'(\d{4})年', month_text)
                month_match = re.search(r'(\d{1,2})月', month_text)
                
                if year_match and month_match:
                    current_year = int(year_match.group(1))
                    current_month = int(month_match.group(1))
                    
                    print(f"🗓️ 現在表示: {current_year}年{current_month}月")
                    print(f"🎯 目標: {target_year}年{target_month}月")
                    
                    # 目標の月に到達したかチェック
                    if current_year == target_year and current_month == target_month:
                        print("✅ 目標の月に到達しました！")
                        return True
                    
                    # 月移動の方向を決定
                    if (current_year > target_year) or (current_year == target_year and current_month > target_month):
                        # 前月ボタンをクリック
                        print("⬅️ 前月ボタンをクリック...")
                        prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
                        driver.execute_script("arguments[0].click();", prev_button)
                    else:
                        # 次月ボタンをクリック
                        print("➡️ 次月ボタンをクリック...")
                        next_button = driver.find_element(By.XPATH, "//input[@value='次月']")
                        driver.execute_script("arguments[0].click();", next_button)
                    
                    time.sleep(3)  # ページ更新待ち
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
    
    if month_move_count >= max_month_moves:
        print("⚠️ 月移動の最大試行回数に達しました")
    
    return False

def parse_wait_time_data(html_content, date_str):
    """待ち時間データを解析（既存の解析ロジック）"""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = []
    
    # アトラクション名のリスト
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
    
    # 時間帯を作成
    time_slots = []
    for hour in range(8, 22):
        for minute in [15, 45]:
            time_slots.append(f"{hour:02d}:{minute:02d}")
    
    # テーブル行を検索
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 44:  # データ行の基準
            time_text = cells[0].get_text(strip=True)
            if time_text in time_slots:
                # データセルの処理
                data_cells = []
                
                # セル数に応じて気温セルを除外
                if len(cells) == 45:  # 気温セルがある場合
                    data_cells = cells[1:44]  # 最初のセル（気温）を除外
                else:
                    data_cells = cells[1:43]  # 通常のデータセル
                
                # アトラクションごとのデータ抽出
                for i, attraction in enumerate(attractions[:len(data_cells)]):
                    if i < len(data_cells):
                        wait_time = data_cells[i].get_text(strip=True)
                        css_classes = data_cells[i].get('class', [])
                        
                        data.append({
                            'Attraction': attraction,
                            'WaitTime': wait_time if wait_time else '-',
                            'Status': 'no_data' if wait_time == '-' or not wait_time else 'active',
                            'Time': time_text,
                            'Date': date_str,
                            'CSSClasses': ' '.join(css_classes) if css_classes else '',
                            'RawValue': wait_time
                        })
    
    return data

def save_to_csv(data, filename):
    """データをCSVファイルに保存"""
    df = pd.DataFrame(data)
    
    # データディレクトリを作成
    os.makedirs('data', exist_ok=True)
    
    df.to_csv(filename, index=False, encoding='utf-8')

def process_single_month(year, month, days_in_month):
    """1つの月を処理する（土日対応修正版）"""
    driver = setup_driver()
    
    try:
        print(f"🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
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
                # 日付クリック（土日対応修正版）
                date_elements = []
                
                # 平日、土曜、日曜の全クラスを検索
                for class_name in ["CAL", "CALSAT", "CALSUN"]:
                    elements = driver.find_elements(By.CLASS_NAME, class_name)
                    date_elements.extend(elements)
                
                clicked = False
                
                # テキスト内容での検索→親要素のonclick属性をチェック
                for element in date_elements:
                    if element.text.strip() == str(day):
                        # 親要素のonclick属性をチェック
                        parent = element.find_element(By.XPATH, "..")
                        onclick_attr = parent.get_attribute("onclick") 
                        if onclick_attr and f"fMouseclick({date_str}," in onclick_attr:
                            parent.click()
                            clicked = True
                            break
                
                # フォールバック: onclick属性での直接検索
                if not clicked:
                    for element in date_elements:
                        onclick_attr = element.get_attribute("onclick")
                        if onclick_attr and f"fMouseclick({date_str}," in onclick_attr:
                            element.click()
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
                all_data = parse_wait_time_data(html_content, date_str)
                
                if all_data and len(all_data) > 0:
                    save_to_csv(all_data, csv_filename)
                    valid_count = len([d for d in all_data if d['WaitTime'] != '-'])
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
    """月単位バッチ処理メイン関数"""
    print("🚀 月単位高速バッチ処理開始（土日対応版）")
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
        print(f"\\n🗓️ {year}年{month}月 開始...")
        success, error = process_single_month(year, month, days)
        total_success += success
        total_error += error
        print(f"📈 累計: 成功{total_success}件, エラー{total_error}件")
    
    print(f"\\n🎉 全処理完了！")
    print(f"✅ 総成功: {total_success}件")
    print(f"❌ 総エラー: {total_error}件")
    success_rate = (total_success / (total_success + total_error) * 100) if (total_success + total_error) > 0 else 0
    print(f"📈 成功率: {success_rate:.1f}%")

if __name__ == "__main__":
    monthly_batch_scraper() 