#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import os

def correct_calendar_28times_collection():
    """カレンダー選択による正しい28時間帯データ収集"""
    
    print("🚀 カレンダー選択による正しい28時間帯データ収集開始")
    print("="*70)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(15)
        
        # === STEP 1: メインページでカレンダー選択 ===
        print("📅 STEP 1: メインページでカレンダー選択...")
        driver.get("https://yosocal.com/")
        time.sleep(8)
        
        # 明日の日付を取得（確実に28時間帯データがある日付）
        tomorrow = datetime.now() + timedelta(days=1)
        target_date = tomorrow.strftime("%Y%m%d")  # 例: 20250704
        
        print(f"🎯 対象日付: {target_date} ({tomorrow.strftime('%Y年%m月%d日')})")
        
        # カレンダー要素を探索
        calendar_elements = driver.find_elements(By.CLASS_NAME, "BOXA")
        print(f"📊 カレンダー要素数: {len(calendar_elements)}")
        
        target_calendar = None
        for i, cal_elem in enumerate(calendar_elements):
            # 各カレンダー要素の詳細確認
            cal_div = cal_elem.find_element(By.TAG_NAME, "div")
            date_text = cal_div.text
            elem_id = cal_elem.get_attribute('id')
            
            print(f"  📋 カレンダー[{i}]: ID={elem_id}, 日付={date_text}")
            
            # 明日の日付に対応する要素を探す
            if date_text == str(tomorrow.day):  # 日付が一致
                target_calendar = cal_elem
                target_index = i
                print(f"  ✅ 対象カレンダー発見: ID={elem_id}")
                break
        
        if not target_calendar:
            # 最初の要素を使用（テスト用）
            target_calendar = calendar_elements[0] if calendar_elements else None
            target_index = 0
            print("  ⚠️ 対象日付なし、最初の要素を使用")
        
        if target_calendar:
            # === カレンダー選択のJavaScript実行 ===
            print(f"🎯 カレンダー選択実行...")
            
            # 方法1: fMouseclick関数を直接実行
            try:
                driver.execute_script(f"fMouseclick({target_date}, {target_index});")
                print(f"✅ fMouseclick({target_date}, {target_index}) 実行成功")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ fMouseclick実行失敗: {e}")
                
                # 方法2: 要素クリック
                try:
                    driver.execute_script("arguments[0].click();", target_calendar)
                    print("✅ 要素クリック実行")
                    time.sleep(3)
                except Exception as e2:
                    print(f"⚠️ 要素クリック失敗: {e2}")
        
        # === STEP 2: realtime.htmに移動 ===
        print("\n📡 STEP 2: realtime.htmに移動...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(10)
        
        # ディズニーランド選択
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # 完全読み込み待機
        print("⏳ ページ完全読み込み待機...")
        time.sleep(10)
        
        # === STEP 3: 28時間帯データ確認 ===
        print("\n📊 STEP 3: 28時間帯データ確認...")
        
        html_content = driver.page_source
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
        
        # アトラクション名取得（重複除去）
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
        
        # 時間データ行を抽出（重複除去）
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
        
        print(f"⏰ 重複除去後時間帯数: {len(time_data_rows)}")
        time_list = [t for t, _ in time_data_rows]
        print(f"📋 時間帯一覧: {time_list}")
        
        # 期待される28時間帯確認
        expected_times = []
        for hour in range(8, 22):  # 8:00-21:00
            expected_times.append(f"{hour:02d}:15")
            expected_times.append(f"{hour:02d}:45")
        expected_times.append("平均")
        
        print(f"🎯 期待時間帯数: {len(expected_times)}")
        print(f"✅ 期待時間帯: {expected_times[:10]}...{expected_times[-5:]}")
        
        missing_times = set(expected_times) - set(time_list)
        if missing_times:
            print(f"⚠️ 不足時間帯: {sorted(list(missing_times))}")
        else:
            print("🎉 28時間帯完全取得成功！")
        
        # === STEP 4: データ抽出 ===
        print(f"\n📊 STEP 4: データ抽出...")
        
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
                        'date': target_date,
                        'formatted_date': tomorrow.strftime("%m月%d日"),
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_correct_calendar_28times'
                    }
                    all_data.append(record)
                    total_records += 1
        
        print(f"📊 データ抽出完了: {total_records}件 (有効: {valid_data}件)")
        
        # === STEP 5: CSV保存 ===
        if all_data:
            print(f"\n💾 STEP 5: CSV保存...")
            
            df = pd.DataFrame(all_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # dataディレクトリ作成
            os.makedirs('data', exist_ok=True)
            csv_filename = f"data/yosocal_correct_calendar_28times_{timestamp}.csv"
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"💾 CSVファイル保存: {csv_filename}")
            
            # 統計表示
            print(f"\n📊 最終収集結果:")
            print(f"  📅 対象日付: {tomorrow.strftime('%Y年%m月%d日')}")
            print(f"  📈 総レコード数: {len(df)}")
            print(f"  ⏰ 時間帯数: {df['time'].nunique()}")
            print(f"  🎯 アトラクション数: {df['attraction'].nunique()}")
            print(f"  ✅ 有効待ち時間: {df['wait_time'].notna().sum()}")
            print(f"  🎯 期待レコード数: {len(attractions) * len(expected_times)} (42×{len(expected_times)})")
            print(f"  📊 実際レコード数: {len(df)}")
            
            # 時間帯別データ数
            print(f"\n⏰ 時間帯別データ数:")
            time_counts = df['time'].value_counts().sort_index()
            for time_slot, count in time_counts.items():
                print(f"  {time_slot}: {count}件")
            
            # 人気アトラクション待ち時間
            print(f"\n🌟 人気アトラクション待ち時間サンプル:")
            popular_attractions = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニハント', 'スティッチＥＮＣ']
            for attraction in popular_attractions:
                attraction_data = df[(df['attraction'] == attraction) & (df['wait_time'].notna())]
                if not attraction_data.empty:
                    times = []
                    for _, row in attraction_data.head(5).iterrows():
                        times.append(f"{row['time']}:{row['wait_time']:.0f}分")
                    print(f"  {attraction}: {', '.join(times)}")
        
        # デバッグHTML保存
        debug_filename = f"yosocal_correct_calendar_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📁 デバッグHTML保存: {debug_filename}")
        
        driver.quit()
        print(f"\n🎉 カレンダー選択による28時間帯データ収集完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    correct_calendar_28times_collection() 