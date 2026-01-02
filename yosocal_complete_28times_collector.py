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
from selenium.webdriver.common.action_chains import ActionChains

def complete_28times_yosocal_collection():
    """完全28時間帯yosocalデータ収集"""
    
    print("🚀 28時間帯完全yosocalデータ収集開始")
    print("="*60)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(15)
        
        # realtime.htmに直接移動
        print("📡 https://yosocal.com/realtime.htm に移動中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(10)
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except:
            print("⚠️ パーク選択確認スキップ")
        
        # 追加の読み込み待機
        print("⏳ ページ完全読み込み待機中...")
        time.sleep(15)
        
        # ページをスクロールして全時間帯の読み込みを促進
        print("📜 ページスクロールして28時間帯読み込み...")
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
        
        # jamat要素が完全に読み込まれるまで待機
        print("⏳ jamat要素の完全読み込み待機...")
        max_wait = 30
        wait_count = 0
        
        while wait_count < max_wait:
            try:
                jamat_element = driver.find_element(By.ID, "jamat")
                if jamat_element:
                    # 28時間帯のチェック（FPMとFPTクラス要素数）
                    fpm_elements = driver.find_elements(By.CLASS_NAME, "FPM")
                    fpt_elements = driver.find_elements(By.CLASS_NAME, "FPT")
                    
                    total_time_elements = len(fpm_elements) + len(fpt_elements)
                    print(f"📊 現在の時間要素数: FPM={len(fpm_elements)}, FPT={len(fpt_elements)}, 合計={total_time_elements}")
                    
                    if total_time_elements >= 28:
                        print("✅ 28時間帯読み込み完了！")
                        break
                    elif total_time_elements >= 20:
                        print(f"⏳ {total_time_elements}/28時間帯読み込み中... さらに待機")
                        time.sleep(2)
                    else:
                        print(f"⏳ {total_time_elements}/28時間帯読み込み中...")
                        time.sleep(1)
                        
                wait_count += 1
            except:
                print(f"⏳ jamat要素待機中... ({wait_count}/{max_wait})")
                time.sleep(1)
                wait_count += 1
        
        # 現在のページソースを取得
        print("📊 最終ページデータ取得中...")
        html_content = driver.page_source
        
        # デバッグHTML保存
        debug_filename = f"yosocal_complete_28times_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
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
                    if attraction_name and attraction_name not in attractions:
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
        
        # 期待される28時間帯を生成
        expected_times = []
        for hour in range(8, 22):  # 8時から21時まで
            expected_times.append(f"{hour:02d}:15")
            expected_times.append(f"{hour:02d}:45")
        expected_times.append("平均")  # 29番目
        
        print(f"📝 期待時間帯: {len(expected_times)}個")
        
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
                        'date': '7月3日',
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_complete_28times'
                    }
                    all_data.append(record)
                    total_records += 1
        
        print(f"📊 データ抽出完了: {total_records}件 (有効: {valid_data}件)")
        
        # CSV保存
        if all_data:
            df = pd.DataFrame(all_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"data/yosocal_2025_07_03_complete_28times_data_{timestamp}.csv"
            
            # dataディレクトリ作成
            import os
            os.makedirs('data', exist_ok=True)
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"💾 CSVファイル保存: {csv_filename}")
            
            # 統計表示
            print(f"\n📊 最終収集結果:")
            print(f"  📈 総レコード数: {len(df)}")
            print(f"  ⏰ 時間帯数: {df['time'].nunique()}")
            print(f"  🎯 アトラクション数: {df['attraction'].nunique()}")
            print(f"  ✅ 有効待ち時間: {df['wait_time'].notna().sum()}")
            print(f"  🎯 期待レコード数: {len(attractions) * len(expected_times)} (42×{len(expected_times)})")
            
            # 時間帯別データ数
            print(f"\n⏰ 時間帯別データ数:")
            time_counts = df['time'].value_counts().sort_index()
            for time_slot, count in time_counts.items():
                print(f"  {time_slot}: {count}件")
            
            # 人気アトラクションの待ち時間表示
            print(f"\n🌟 人気アトラクション待ち時間サンプル:")
            popular_attractions = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニハント', 'スティッチＥＮＣ']
            for attraction in popular_attractions:
                attraction_data = df[(df['attraction'] == attraction) & (df['wait_time'].notna())]
                if not attraction_data.empty:
                    times = []
                    for _, row in attraction_data.head(3).iterrows():
                        times.append(f"{row['time']}:{row['wait_time']:.0f}分")
                    print(f"  {attraction}: {', '.join(times)}")
        
        driver.quit()
        print("\n🎉 28時間帯完全データ収集完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    complete_28times_yosocal_collection() 