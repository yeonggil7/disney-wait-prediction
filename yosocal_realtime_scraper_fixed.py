#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
このスクリプトは yosocal.com の待ち時間データを日付指定で取得し、
指定した日付（例: 20250629）の待ち時間一覧をCSV形式で保存します。

修正版の仕組み:
1. Seleniumでブラウザを自動操作
2. realtime.htmに直接移動
3. 月移動ボタンで目的の月に移動
4. カレンダー要素をクリック（日付選択）
5. 待ち時間データを取得
6. 実際のテーブル構造（jamat div、FPh2/FPM/B0-B8クラス）に対応
7. CSVに書き出し
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
from datetime import datetime

def scrape_yosocal_by_date(target_date: str):
    """
    指定された日付のデータをスクレイピングしてCSV出力します。

    Parameters:
        target_date (str): 例 "20250629" のような形式の文字列
    """
    
    print(f"🚀 yosocal.com データ取得開始")
    print(f"📅 対象日付: {target_date}")
    print("="*50)
    
    # ブラウザオプション設定
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    # ヘッドレスモードは必要に応じてコメントアウト
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        # WebDriverセットアップ
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        # === STEP 1: realtime.htmに直接移動 ===
        print("📡 STEP 1: realtime.htmに移動...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(8)  # JavaScript読み込み待ち
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except:
            print("⚠️ パーク選択要素なし")
        
        # === STEP 2: 目的の月に移動 ===
        print(f"\n📅 STEP 2: 目的の月（{target_date[:4]}年{target_date[4:6]}月）に移動...")
        
        # 年、月、日を分離
        target_year = int(target_date[:4])
        target_month = int(target_date[4:6])
        target_day = int(target_date[6:8])
        
        print(f"🗓️ 対象: {target_year}年{target_month}月{target_day}日")
        
        # 月移動処理
        max_month_moves = 12  # 最大12回まで月移動を試行
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
                            break
                        
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
        
        # === STEP 3: カレンダー要素でターゲット日付を探してクリック ===
        print(f"\n📅 STEP 3: カレンダーで {target_date} を探してクリック...")
        
        # カレンダー要素を検索
        calendar_found = False
        calendar_elements = driver.find_elements(By.CSS_SELECTOR, "div[onclick*='fMouseclick']")
        print(f"📊 カレンダー要素数: {len(calendar_elements)}")
        
        for i, cal_elem in enumerate(calendar_elements):
            try:
                onclick_attr = cal_elem.get_attribute('onclick')
                if not onclick_attr:
                    continue
                
                # onclick属性から日付を抽出
                # 例: onClick=fMouseclick(20250629,5)
                if target_date in onclick_attr:
                    print(f"✅ 対象日付カレンダー発見: {onclick_attr}")
                    # JavaScriptクリック実行
                    driver.execute_script("arguments[0].click();", cal_elem)
                    calendar_found = True
                    time.sleep(5)  # データ読み込み待ち
                    print("✅ カレンダークリック成功")
                    break
                
                # テキスト内容でも確認
                cal_text = cal_elem.get_text(strip=True)
                if cal_text == str(target_day):
                    print(f"✅ 日付テキスト一致でカレンダー選択: {cal_text}")
                    driver.execute_script("arguments[0].click();", cal_elem)
                    calendar_found = True
                    time.sleep(5)
                    print("✅ カレンダークリック成功")
                    break
                    
            except Exception as e:
                continue
        
        if not calendar_found:
            print("⚠️ 対象カレンダー要素が見つかりません。現在のデータを取得します。")
        
        # === STEP 4: データ抽出 ===
        print("\n📊 STEP 4: データ抽出...")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # デバッグ用: HTMLを保存
        debug_html_filename = f"debug_{target_date}.html"
        with open(debug_html_filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"🔧 デバッグHTML保存: {debug_html_filename}")
        
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
        seen_times = set()
        
        for row in rows:
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
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
        
        print(f"⏰ 時間帯数: {len(time_data_rows)}")
        
        # === STEP 5: データ構築 ===
        print("\n💾 STEP 5: データ構築...")
        
        results = []
        total_records = 0
        valid_wait_times = 0
        
        for time_slot, row in time_data_rows:
            print(f"\n🔍 デバッグ: {time_slot} 時間帯の処理")
            
            # 行内のすべてのセルを確認
            all_cells = row.find_all('td')
            print(f"  📊 行内セル総数: {len(all_cells)}")
            
            # 気温セルの様々なパターンを検索
            temp_cell = None
            temp_colspan = 1
            
            # パターン1: FPh2クラス
            temp_cell = row.find('td', class_='FPh2')
            if temp_cell:
                temp_colspan = int(temp_cell.get('colspan', 1))
                print(f"  🌡️ 気温セル(FPh2) colspan: {temp_colspan}")
            else:
                # パターン2: 気温らしいテキストを含むセル
                for cell in all_cells:
                    cell_text = cell.get_text(strip=True)
                    if re.match(r'^\d+\.\d+$', cell_text):  # 小数点気温パターン
                        temp_cell = cell
                        temp_colspan = int(cell.get('colspan', 1))
                        print(f"  🌡️ 気温セル(数値) colspan: {temp_colspan}, 値: {cell_text}")
                        break
                
                if not temp_cell:
                    # パターン3: セル数の違いから推測
                    if len(all_cells) == 45:  # 下二桁15の場合の想定セル数
                        print(f"  🌡️ セル数から気温セル存在を推測（45セル）")
                        # 最初のB0セルが気温の可能性
                        first_b0 = row.find('td', class_='B0')
                        if first_b0:
                            temp_cell = first_b0
                            temp_colspan = 2  # 推測値
                            print(f"  🌡️ 推測: 最初のB0セルが気温（colspan=2と仮定）")
                    else:
                        print(f"  🌡️ 気温セル見つからず")
            
            # データセルを取得
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            print(f"  📊 B0-B8データセル数: {len(data_cells)}")
            
            # セル数に基づくインデックス調整
            index_offset = 0
            start_index = 0
            
            if len(all_cells) == 45:  # 下二桁15の場合
                # 最初のB0セルは気温データなので除外
                start_index = 1
                print(f"  ⚠️  {time_slot}: セル数45検出 - 最初のB0セル(気温)を除外")
            else:
                print(f"  ✅ {time_slot}: 通常処理（セル数{len(all_cells)}）")
            
            # 処理対象のデータセルを取得（気温セルを除外）
            processed_data_cells = data_cells[start_index:]
            print(f"  📊 処理対象データセル数: {len(processed_data_cells)}")
            
            for i, cell in enumerate(processed_data_cells):
                # アトラクションインデックスは調整不要
                attraction_index = i
                
                if attraction_index < len(attractions):
                    attraction = attractions[attraction_index]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    # 最初の数件をデバッグ表示
                    if i < 5:
                        print(f"    データ{i}: セルインデックス={start_index + i}, アトラクションインデックス={attraction_index}, アトラクション='{attraction}', 値='{cell_text}'")
                    
                    # 待ち時間解析
                    wait_time = None
                    status = "unknown"
                    
                    if cell_text == "-" or cell_text == "" or cell_text == "　":
                        status = "no_data"
                        display_wait = "-"
                    elif re.match(r'^\d+$', cell_text):
                        wait_time = int(cell_text)
                        status = "normal"
                        display_wait = f"{wait_time}分"
                        valid_wait_times += 1
                    else:
                        status = "other"
                        display_wait = cell_text
                    
                    # データ記録（オリジナルの形式に近づける）
                    results.append({
                        "Attraction": attraction,
                        "WaitTime": display_wait,
                        "Status": status,
                        "Time": time_slot,
                        "Date": target_date,
                        "CSSClasses": css_classes,
                        "RawValue": cell_text
                    })
                    total_records += 1
        
        print(f"📊 総レコード数: {total_records}")
        print(f"✅ 有効待ち時間: {valid_wait_times}")
        
        # === STEP 6: CSV保存 ===
        print(f"\n💾 STEP 6: CSV保存...")
        
        if results:
            df = pd.DataFrame(results)
            csv_filename = f"yosocal_{target_date}_fixed.csv"
            df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
            print(f"✅ {csv_filename} を出力しました")
            
            # サンプルデータ表示
            print(f"\n📋 データサンプル:")
            print(df.head(10).to_string(index=False))
            
            # 統計情報
            print(f"\n📊 統計情報:")
            print(f"  時間帯数: {df['Time'].nunique()}")
            print(f"  アトラクション数: {df['Attraction'].nunique()}")
            print(f"  有効待ち時間数: {df[df['Status']=='normal'].shape[0]}")
            
        else:
            print("❌ データが取得できませんでした")
        
        driver.quit()
        print(f"\n🎉 データ取得完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

# 🔧 実行例（2025年6月29日のデータ）
if __name__ == "__main__":
    scrape_yosocal_by_date("20250629") 