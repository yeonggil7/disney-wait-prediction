#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

def simple_yosocal_data_collection():
    """シンプルなyosocalデータ収集"""
    
    print("🚀 シンプルyosocalデータ収集開始")
    print("="*50)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        # realtime.htmに直接移動
        print("📡 https://yosocal.com/realtime.htm に移動中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(8)
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
            print("✅ ディズニーランド選択確認")
        except:
            print("⚠️ パーク選択確認スキップ")
        
        # 現在のページソースを取得
        print("📊 現在のページデータ取得中...")
        html_content = driver.page_source
        
        # デバッグHTML保存
        debug_filename = f"yosocal_simple_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📁 デバッグHTML保存: {debug_filename}")
        
        # BeautifulSoupで解析
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # jamat div確認
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamat div が見つかりません")
            driver.quit()
            return
        
        print("✅ jamat div発見")
        
        # テーブル取得
        table = jamat_div.find('table')
        if not table:
            print("❌ jamat テーブルが見つかりません")
            driver.quit()
            return
        
        print("✅ jamat テーブル発見")
        rows = table.find_all('tr')
        print(f"📊 テーブル行数: {len(rows)}")
        
        # アトラクション名取得
        attractions = []
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                for cell in fph2_cells:
                    attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                    if attraction_name:
                        attractions.append(attraction_name)
                break
        
        print(f"🎯 アトラクション数: {len(attractions)}")
        
        # 時間データ行を抽出
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
        
        print(f"⏰ 時間帯数: {len(time_data_rows)}")
        time_list = [t for t, _ in time_data_rows]
        print(f"📋 時間帯一覧: {time_list}")
        
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
                        'date': '7月3日',  # 今日の日付
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_simple_current'
                    }
                    all_data.append(record)
                    total_records += 1
        
        print(f"📊 データ抽出完了: {total_records}件 (有効: {valid_data}件)")
        
        # CSV保存
        if all_data:
            df = pd.DataFrame(all_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"data/yosocal_2025_07_03_simple_current_data_{timestamp}.csv"
            
            # dataディレクトリ作成
            import os
            os.makedirs('data', exist_ok=True)
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"💾 CSVファイル保存: {csv_filename}")
            
            # 統計表示
            print(f"\n📊 収集結果:")
            print(f"  総レコード数: {len(df)}")
            print(f"  時間帯数: {df['time'].nunique()}")
            print(f"  アトラクション数: {df['attraction'].nunique()}")
            print(f"  有効待ち時間: {df['wait_time'].notna().sum()}")
            
            # サンプルデータ表示
            print(f"\n📝 サンプルデータ:")
            sample_data = df[df['wait_time'].notna()].head(5)
            for _, row in sample_data.iterrows():
                print(f"  {row['time']} {row['attraction']}: {row['wait_time']}分")
        
        driver.quit()
        print("\n🎉 シンプルデータ収集完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    simple_yosocal_data_collection() 