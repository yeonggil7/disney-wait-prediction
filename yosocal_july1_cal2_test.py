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

def test_july1_cal2():
    """cal2の7/1要素をテストして28時間帯データを確認"""
    
    print("🚀 7月1日（cal2='7/1'）28時間帯データテスト")
    print("="*50)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        # yosocal.comに移動
        print("📡 yosocal.com に移動中...")
        driver.get("https://yosocal.com/")
        time.sleep(5)
        
        # 東京ディズニーランド選択
        land_radio = driver.find_element(By.ID, "park1")
        if not land_radio.is_selected():
            land_radio.click()
            time.sleep(2)
        
        # cal2要素を確実に取得
        print("📅 cal2 (7/1) 要素検索中...")
        cal2_element = driver.find_element(By.ID, "cal2")
        cal_text = cal2_element.find_element(By.CLASS_NAME, "CAL").text.strip()
        
        print(f"✅ cal2発見: 表示テキスト='{cal_text}'")
        
        if cal_text == "7/1":
            print("🎯 7月1日確認済み、クリック実行...")
            
            # JavaScriptでクリック
            driver.execute_script("arguments[0].click();", cal2_element)
            time.sleep(8)  # 長めの待機
            
            print("✅ 7月1日クリック完了")
            
            # realtime.htmに移動
            print("📊 realtime.htm でデータ確認中...")
            driver.get("https://yosocal.com/realtime.htm")
            time.sleep(8)
            
            # データ抽出
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # jamat div確認
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                print("❌ jamat div が見つかりません")
                return
            
            table = jamat_div.find('table')
            if not table:
                print("❌ jamat テーブルが見つかりません")
                return
            
            # 時間データ抽出
            time_data = []
            rows = table.find_all('tr')
            
            for row in rows:
                # FPM要素
                fpm_cell = row.find('td', class_='FPM')
                if fpm_cell:
                    time_text = fpm_cell.get_text(strip=True)
                    if re.match(r'^\d{2}:\d{2}$', time_text):
                        time_data.append(time_text)
                
                # FPT要素（平均）
                fpt_cell = row.find('td', class_='FPT')
                if fpt_cell:
                    time_text = fpt_cell.get_text(strip=True)
                    if time_text == '平均':
                        time_data.append(time_text)
            
            print(f"📊 7月1日データ結果:")
            print(f"  時間帯数: {len(time_data)}個")
            print(f"  時間帯一覧: {time_data}")
            
            # 28時間帯達成チェック
            if len(time_data) >= 20:
                print(f"🎉 SUCCESS: {len(time_data)}時間帯！28時間帯達成可能性あり")
                
                # 期待される28時間帯
                expected_times = [
                    '08:15', '08:45', '09:15', '09:45', '10:15', '10:45', '11:15', '11:45',
                    '12:15', '12:45', '13:15', '13:45', '14:15', '14:45', '15:15', '15:45',
                    '16:15', '16:45', '17:15', '17:45', '18:15', '18:45', '19:15', '19:45',
                    '20:15', '20:45', '21:15', '21:45'
                ]
                
                found_times = [t for t in time_data if t != '平均']
                missing_times = set(expected_times) - set(found_times)
                
                print(f"✅ 発見時間帯: {len(found_times)}/{len(expected_times)}")
                if missing_times:
                    print(f"⚠️ 未発見時間帯: {sorted(missing_times)}")
                else:
                    print(f"🎉 完全な28時間帯達成！")
                
                # 完全データとして保存を実行
                if len(found_times) >= 15:  # 15時間帯以上なら保存
                    print(f"\n💾 データ保存実行...")
                    save_july1_data(soup, time_data)
                
            else:
                print(f"⚠️ 時間帯不足: {len(time_data)}個のみ")
        
        else:
            print(f"❌ cal2のテキストが期待値と異なります: '{cal_text}'")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ エラー: {e}")

def save_july1_data(soup, time_data):
    """7月1日データをCSVに保存"""
    try:
        all_data = []
        
        # jamat div から完全データ抽出
        jamat_div = soup.find('div', id='jamat')
        table = jamat_div.find('table')
        rows = table.find_all('tr')
        
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
        
        # 各時間帯のデータ抽出
        time_rows = []
        for row in rows:
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
            if fpm_cell:
                time_text = fpm_cell.get_text(strip=True)
                if re.match(r'^\d{2}:\d{2}$', time_text):
                    time_rows.append((time_text, row))
            elif fpt_cell:
                time_text = fpt_cell.get_text(strip=True)
                if time_text == '平均':
                    time_rows.append((time_text, row))
        
        total_records = 0
        valid_data = 0
        
        for time_slot, row in time_rows:
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
                        'date': '7月1日',
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_july1_cal2'
                    }
                    all_data.append(record)
                    total_records += 1
        
        # DataFrame作成とCSV保存
        df = pd.DataFrame(all_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"data/yosocal_2025_07_01_cal2_data_{timestamp}.csv"
        
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"💾 保存完了: {csv_filename}")
        print(f"📊 総レコード数: {total_records}")
        print(f"✅ 有効データ: {valid_data}")
        print(f"⏰ 時間帯数: {df['time'].nunique()}")
        
    except Exception as e:
        print(f"❌ 保存エラー: {e}")

if __name__ == "__main__":
    test_july1_cal2() 