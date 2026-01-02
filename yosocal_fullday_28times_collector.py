#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import json

def get_yosocal_current_data():
    """現在の時間帯までのyosocalデータを取得"""
    
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.add_argument("--headless")  # バックグラウンド実行
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(8)
        
        # ディズニーランド選択
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
        except:
            pass
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            driver.quit()
            return None, None
        
        table = jamat_div.find('table')
        if not table:
            driver.quit()
            return None, None
        
        rows = table.find_all('tr')
        
        # アトラクション名取得
        attractions = []
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                for cell in fph2_cells:
                    attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                    if attraction_name and attraction_name not in attractions:
                        attractions.append(attraction_name)
                break
        
        # 時間データ抽出
        time_data_rows = []
        for row in rows:
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
            if fpm_cell:
                time_text = fpm_cell.get_text(strip=True)
                if re.match(r'^\d{2}:\d{2}$', time_text):
                    time_data_rows.append((time_text, row))
            elif fpt_cell:
                time_text = fpt_cell.get_text(strip=True)
                if time_text == '平均':
                    time_data_rows.append((time_text, row))
        
        # データ抽出
        all_data = []
        for time_slot, row in time_data_rows:
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    attraction = attractions[i]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    wait_time = None
                    status = "unknown"
                    
                    if cell_text == "-" or cell_text == "" or cell_text == "　":
                        status = "no_data"
                    elif re.match(r'^\d+$', cell_text):
                        wait_time = float(cell_text)
                        status = "normal"
                    else:
                        status = "other"
                    
                    record = {
                        'collection_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'date': datetime.now().strftime("%m月%d日"),
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_fullday_collector'
                    }
                    all_data.append(record)
        
        driver.quit()
        return all_data, time_data_rows
        
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        return None, None

def fullday_28times_collection():
    """一日分28時間帯完全データ収集システム"""
    
    print("🚀 一日分28時間帯完全データ収集システム開始")
    print("="*70)
    
    # データディレクトリ作成
    os.makedirs('data', exist_ok=True)
    
    # 進捗ファイル
    progress_file = f"data/yosocal_fullday_progress_{datetime.now().strftime('%Y%m%d')}.json"
    collected_times = set()
    all_collected_data = []
    
    # 既存の進捗読み込み
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                collected_times = set(progress_data.get('collected_times', []))
                print(f"📊 既存進捗読み込み: {len(collected_times)}時間帯収集済み")
        except:
            print("⚠️ 進捗ファイル読み込み失敗、新規開始")
    
    # 期待時間帯生成
    expected_times = []
    for hour in range(8, 22):
        expected_times.append(f"{hour:02d}:15")
        expected_times.append(f"{hour:02d}:45")
    expected_times.append("平均")
    
    print(f"🎯 目標: {len(expected_times)}時間帯完全収集")
    print(f"📋 既収集: {len(collected_times)}時間帯")
    print(f"📋 残り: {len(expected_times) - len(collected_times)}時間帯")
    
    # 現在の状況でデータ収集
    print(f"\n📡 現在の状況でデータ収集開始...")
    current_data, time_rows = get_yosocal_current_data()
    
    if current_data:
        new_times = []
        for record in current_data:
            time_slot = record['time']
            if time_slot not in collected_times:
                new_times.append(time_slot)
                collected_times.add(time_slot)
        
        all_collected_data.extend(current_data)
        
        print(f"✅ データ収集成功: {len(current_data)}件")
        print(f"🆕 新規時間帯: {len(new_times)}個 - {new_times}")
        print(f"📊 累計時間帯: {len(collected_times)}/{len(expected_times)}")
        
        # 進捗保存
        progress_data = {
            'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'collected_times': list(collected_times),
            'total_records': len(current_data),
            'expected_times': expected_times
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # CSVファイル保存
        df = pd.DataFrame(current_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"data/yosocal_fullday_current_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"💾 現在データ保存: {csv_filename}")
        
        # 統計表示
        print(f"\n📊 現在の収集状況:")
        print(f"  📈 総レコード数: {len(df)}")
        print(f"  ⏰ 時間帯数: {df['time'].nunique()}")
        print(f"  🎯 アトラクション数: {df['attraction'].nunique()}")
        print(f"  ✅ 有効待ち時間: {df['wait_time'].notna().sum()}")
        
        # 時間帯別データ表示
        print(f"\n⏰ 収集済み時間帯:")
        time_counts = df['time'].value_counts().sort_index()
        for time_slot, count in time_counts.items():
            print(f"  {time_slot}: {count}件")
        
        # 人気アトラクション
        print(f"\n🌟 人気アトラクション現在の待ち時間:")
        popular_attractions = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニハント', 'スティッチＥＮＣ']
        for attraction in popular_attractions:
            attraction_data = df[(df['attraction'] == attraction) & (df['wait_time'].notna())]
            if not attraction_data.empty:
                latest_data = attraction_data.iloc[-1]
                print(f"  {attraction}: {latest_data['time']} - {latest_data['wait_time']:.0f}分")
        
    else:
        print("❌ データ収集失敗")
    
    # 自動収集スケジュールの案内
    print(f"\n📅 完全28時間帯データ収集方法:")
    print(f"  1. 現在収集済み: {len(collected_times)}/{len(expected_times)}時間帯")
    print(f"  2. 残り時間帯は時間経過と共に追加収集可能")
    print(f"  3. このスクリプトを定期実行して完全データセット構築")
    print(f"  4. 進捗は {progress_file} に保存")
    
    # 実用的な完全データセット作成
    if len(collected_times) >= 5:  # 最低5時間帯あれば分析可能
        print(f"\n📈 実用可能なデータセット作成:")
        
        # データ分析
        df_analysis = pd.DataFrame(current_data)
        
        # 時間帯別平均待ち時間
        time_avg = df_analysis[df_analysis['wait_time'].notna()].groupby('time')['wait_time'].mean().round(1)
        print(f"⏰ 時間帯別平均待ち時間:")
        for time_slot, avg_wait in time_avg.items():
            print(f"  {time_slot}: {avg_wait}分")
        
        # アトラクション別平均待ち時間（上位10位）
        attraction_avg = df_analysis[df_analysis['wait_time'].notna()].groupby('attraction')['wait_time'].mean().round(1).sort_values(ascending=False).head(10)
        print(f"\n🎯 人気アトラクション（平均待ち時間順）:")
        for attraction, avg_wait in attraction_avg.items():
            print(f"  {attraction}: {avg_wait}分")
    
    print(f"\n🎉 一日分28時間帯収集システム実行完了！")

if __name__ == "__main__":
    fullday_28times_collection() 