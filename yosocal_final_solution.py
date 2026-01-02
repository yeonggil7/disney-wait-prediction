# -*- coding: utf-8 -*-
"""
yosocal.com完全解決版スクレイピングシステム
正しいrealtime.htmURLを使用した完全動作バージョン
"""

import time
import re
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ WebDriverセットアップ完了")
    return driver

def generate_expected_times():
    """期待される時間リストを生成"""
    times = []
    for hour in range(8, 22):
        for minute in [15, 45]:
            if hour == 21 and minute == 45:
                times.append("21:45")
                break
            times.append(f"{hour:02d}:{minute}")
    times.append("平均")
    return times

def get_attraction_names():
    """42のアトラクション名リスト"""
    return [
        "オムニバス", "リバー鉄道", "カリブの海賊", "ジャングル", "ツリーハウス", "魅惑のチキルーム",
        "ビッグサンダー", "Sギャラリー", "ベア・シアター", "いかだ", "蒸気船", "スプラッシュ",
        "カヌー探検", "スモールワールド", "ハニーハント", "ホーンテッド", "アリス", "カルーセル",
        "シンデレラ", "ピノキオ", "ピーターパン", "フィルハー", "白雪姫", "空飛ぶダンボ",
        "ゴーコースター", "グーフィー", "CDツリーハウス", "ドナルドのボート", "ミニーの家", "カートゥーン",
        "スター・ツアーズ", "スペース", "バズライトイヤー", "モンイン", "美女と野獣", "ベイマックス",
        "スティッチENC", "ハウス前", "ドナルドグリ", "デイジーグリ", "ミニーグリ", "ミート・ミッキー"
    ]

def scrape_realtime_data(driver, target_date=None):
    """realtime.htmページから実際の待機時間データを取得"""
    print("🌐 https://yosocal.com/realtime.htm にアクセス中...")
    
    # 正しいrealtime.htmページにアクセス
    driver.get('https://yosocal.com/realtime.htm')
    time.sleep(5)
    
    # ページソースを取得
    page_source = driver.page_source
    
    # BeautifulSoupで解析
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # jamat divを取得
    jamat_div = soup.find('div', id='jamat')
    if not jamat_div:
        print("❌ jamat divが見つかりません")
        return []
    
    print("✅ jamat divを発見、データ解析中...")
    
    # テーブルを取得
    table = jamat_div.find('table')
    if not table:
        print("❌ jamat div内にテーブルが見つかりません")
        return []
    
    # 解析ロジック実行
    return parse_wait_time_data(table, target_date)

def parse_wait_time_data(table, date_str=None):
    """待機時間データテーブルを解析"""
    print("📊 待機時間データを解析中...")
    
    if date_str is None:
        date_str = datetime.now().strftime("%m月%d日")
    
    rows = table.find_all('tr')
    
    # アトラクション名を取得（FPh2クラス）
    attraction_row = None
    for row in rows:
        fph2_cells = row.find_all('td', class_='FPh2')
        if len(fph2_cells) > 10:  # 十分な数のアトラクション名がある行
            attraction_row = row
            break
    
    if not attraction_row:
        print("❌ アトラクション名行が見つかりません")
        return []
    
    # アトラクション名を抽出
    attraction_cells = attraction_row.find_all('td', class_='FPh2')
    attractions = []
    for cell in attraction_cells:
        text = cell.get_text(strip=True).replace('｜', '')
        if text:
            attractions.append(text)
    
    print(f"📋 {len(attractions)} のアトラクションを発見")
    
    # 時間行を特定してデータを抽出
    data_records = []
    expected_times = generate_expected_times()
    
    for row in rows:
        time_cell = row.find('td', class_='FPM')
        if not time_cell:
            continue
        
        time_text = time_cell.get_text(strip=True)
        if not time_text or time_text == "　":
            continue
        
        # 天気セルが存在するかチェック（rowspanの影響で調整が必要）
        all_cells = row.find_all('td')
        
        # 天気セル（rowspan）の存在を確認
        weather_cell_exists = any(
            cell.find('img') and 'title="天気"' in str(cell) 
            for cell in all_cells
        )
        
        # データセルの開始インデックスを決定
        data_start_index = 2 if weather_cell_exists else 1
        
        # データセルを抽出
        data_cells = all_cells[data_start_index:]
        
        # 各アトラクションのデータを処理
        for i, cell in enumerate(data_cells):
            if i >= len(attractions):
                break
            
            attraction = attractions[i]
            
            # セルのクラスと内容を取得
            css_classes = cell.get('class', [])
            raw_value = cell.get_text(strip=True)
            
            # データの状態と値を判定
            if raw_value == "-" or raw_value == "":
                status = "no_data"
                wait_time = None
            elif raw_value.isdigit():
                status = "normal"
                wait_time = float(raw_value)
            else:
                status = "empty"
                wait_time = None
            
            # レコードを追加
            record = {
                'date': date_str,
                'time': time_text,
                'attraction': attraction,
                'wait_time': wait_time,
                'status': status,
                'css_classes': ' '.join(css_classes),
                'raw_value': raw_value,
                'data_source': 'realtime.htm'
            }
            data_records.append(record)
    
    print(f"✅ {len(data_records)} 件のデータレコードを抽出")
    return data_records

def save_data_to_csv(data_records, filename=None):
    """データをCSVファイルに保存"""
    if not data_records:
        print("❌ 保存するデータがありません")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"yosocal_realtime_data_{timestamp}.csv"
    
    # データディレクトリを作成
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    # CSVに保存
    fieldnames = ['date', 'time', 'attraction', 'wait_time', 'status', 'css_classes', 'raw_value', 'data_source']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_records)
    
    print(f"💾 データを保存: {filepath}")
    return filepath

def analyze_data(data_records):
    """データの分析結果を表示"""
    if not data_records:
        return
    
    df = pd.DataFrame(data_records)
    
    print(f"\n📊 データ分析結果:")
    print(f"   総レコード数: {len(df)}")
    print(f"   アトラクション数: {df['attraction'].nunique()}")
    print(f"   時間スロット数: {df['time'].nunique()}")
    print(f"   有効待機時間データ: {df[df['status'] == 'normal'].shape[0]}")
    
    # 時間スロット一覧
    unique_times = sorted(df['time'].unique())
    print(f"   時間スロット: {unique_times}")
    
    # アトラクション一覧（一部）
    unique_attractions = df['attraction'].unique()
    print(f"   アトラクション例: {list(unique_attractions[:10])}")
    
    # 状態別統計
    status_counts = df['status'].value_counts()
    print(f"   状態別統計: {status_counts.to_dict()}")

def main():
    """メインプロセス"""
    print("🎯 yosocal.com完全解決版スクレイピングシステム")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # 実際のリアルタイム待機時間データを取得
        data_records = scrape_realtime_data(driver)
        
        if data_records:
            # データを保存
            filepath = save_data_to_csv(data_records)
            
            # データ分析
            analyze_data(data_records)
            
            print(f"\n✅ スクレイピング完了！")
            print(f"💾 保存ファイル: {filepath}")
            print(f"🎯 realtime.htmページから正常にデータを取得しました")
        else:
            print("❌ データの取得に失敗しました")
    
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 