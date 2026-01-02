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

def url_parameter_28times_collection():
    """URLパラメータによる28時間帯完全データ収集"""
    
    print("🚀 URLパラメータによる28時間帯完全データ収集開始")
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
        
        # === 複数の日付とURL方式を試行 ===
        test_dates = []
        
        # 1. 今日
        today = datetime.now()
        test_dates.append((today, "今日"))
        
        # 2. 明日
        tomorrow = today + timedelta(days=1)
        test_dates.append((tomorrow, "明日"))
        
        # 3. 明後日
        day_after_tomorrow = today + timedelta(days=2)
        test_dates.append((day_after_tomorrow, "明後日"))
        
        # 4. 来週の同じ曜日
        next_week = today + timedelta(days=7)
        test_dates.append((next_week, "来週"))
        
        best_result = None
        max_time_slots = 0
        
        for date_obj, date_label in test_dates:
            print(f"\n📅 【{date_label}】 {date_obj.strftime('%Y年%m月%d日')} の検証...")
            
            # === 方式1: realtime.htmに直接アクセス ===
            print("🔍 方式1: realtime.htm 直接アクセス...")
            
            try:
                driver.get("https://yosocal.com/realtime.htm")
                time.sleep(8)
                
                # ディズニーランド選択
                try:
                    land_radio = driver.find_element(By.ID, "park1")
                    if not land_radio.is_selected():
                        land_radio.click()
                        time.sleep(3)
                except:
                    pass
                
                # データ分析
                result = analyze_page_data(driver, date_obj, f"{date_label}_realtime")
                if result and result['time_slots'] > max_time_slots:
                    max_time_slots = result['time_slots']
                    best_result = result
                    print(f"✅ 新記録: {result['time_slots']}時間帯")
                
            except Exception as e:
                print(f"❌ 方式1失敗: {e}")
            
            # === 方式2: メインページ経由 ===
            print("🔍 方式2: メインページ経由...")
            
            try:
                # セッション情報クリア
                driver.delete_all_cookies()
                
                # メインページアクセス
                driver.get("https://yosocal.com/")
                time.sleep(5)
                
                # JavaScriptで日付設定を試行
                date_string = date_obj.strftime("%Y%m%d")
                
                # 複数のJavaScript実行方式を試行
                js_commands = [
                    f"if(typeof setDate === 'function') setDate('{date_string}');",
                    f"if(typeof fSetDate === 'function') fSetDate('{date_string}');",
                    f"if(typeof selectDate === 'function') selectDate('{date_string}');",
                    f"if(typeof window.selectedDate !== 'undefined') window.selectedDate = '{date_string}';",
                    f"localStorage.setItem('selectedDate', '{date_string}');",
                    f"sessionStorage.setItem('selectedDate', '{date_string}');"
                ]
                
                for js_cmd in js_commands:
                    try:
                        driver.execute_script(js_cmd)
                        time.sleep(1)
                    except:
                        pass
                
                # realtime.htmに移動
                driver.get("https://yosocal.com/realtime.htm")
                time.sleep(8)
                
                # ディズニーランド選択
                try:
                    land_radio = driver.find_element(By.ID, "park1")
                    if not land_radio.is_selected():
                        land_radio.click()
                        time.sleep(3)
                except:
                    pass
                
                # データ分析
                result = analyze_page_data(driver, date_obj, f"{date_label}_mainpage")
                if result and result['time_slots'] > max_time_slots:
                    max_time_slots = result['time_slots']
                    best_result = result
                    print(f"✅ 新記録: {result['time_slots']}時間帯")
                
            except Exception as e:
                print(f"❌ 方式2失敗: {e}")
            
            # === 方式3: URLパラメータ試行 ===
            print("🔍 方式3: URLパラメータ...")
            
            date_params = [
                f"?date={date_obj.strftime('%Y%m%d')}",
                f"?d={date_obj.strftime('%Y%m%d')}",
                f"?target={date_obj.strftime('%Y%m%d')}",
                f"?day={date_obj.strftime('%Y%m%d')}",
                f"#{date_obj.strftime('%Y%m%d')}"
            ]
            
            for param in date_params:
                try:
                    url = f"https://yosocal.com/realtime.htm{param}"
                    driver.get(url)
                    time.sleep(5)
                    
                    # ディズニーランド選択
                    try:
                        land_radio = driver.find_element(By.ID, "park1")
                        if not land_radio.is_selected():
                            land_radio.click()
                            time.sleep(2)
                    except:
                        pass
                    
                    # データ分析
                    result = analyze_page_data(driver, date_obj, f"{date_label}_param_{param[1:]}")
                    if result and result['time_slots'] > max_time_slots:
                        max_time_slots = result['time_slots']
                        best_result = result
                        print(f"✅ 新記録: {result['time_slots']}時間帯 (パラメータ: {param})")
                    
                except Exception as e:
                    continue
        
        # === 最良結果での最終データ収集 ===
        if best_result and best_result['time_slots'] >= 20:
            print(f"\n🎉 最良結果で最終データ収集実行...")
            print(f"📊 最良結果: {best_result['time_slots']}時間帯 ({best_result['source']})")
            
            final_data = extract_final_data(driver, best_result)
            
            if final_data:
                save_final_csv(final_data, best_result['date'])
        else:
            print(f"\n⚠️ 十分な時間帯データが取得できませんでした")
            print(f"📊 最大取得: {max_time_slots}時間帯")
            
            # 現在の最良結果でもCSV保存
            if best_result:
                final_data = extract_final_data(driver, best_result)
                if final_data:
                    save_final_csv(final_data, best_result['date'], partial=True)
        
        driver.quit()
        print(f"\n🎉 URLパラメータ方式による収集完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

def analyze_page_data(driver, date_obj, source):
    """ページデータの分析"""
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # jamat div確認
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return None
        
        # 時間データ抽出
        time_data_rows = []
        seen_times = set()
        
        fpm_elements = soup.find_all('td', class_='FPM')
        fpt_elements = soup.find_all('td', class_='FPT')
        
        for fpm in fpm_elements:
            time_text = fpm.get_text(strip=True)
            if re.match(r'^\d{2}:\d{2}$', time_text) and time_text not in seen_times:
                time_data_rows.append(time_text)
                seen_times.add(time_text)
        
        for fpt in fpt_elements:
            time_text = fpt.get_text(strip=True)
            if time_text == '平均' and time_text not in seen_times:
                time_data_rows.append(time_text)
                seen_times.add(time_text)
        
        print(f"  📊 時間帯数: {len(time_data_rows)}")
        print(f"  📋 時間帯: {time_data_rows}")
        
        return {
            'time_slots': len(time_data_rows),
            'time_list': time_data_rows,
            'date': date_obj,
            'source': source,
            'soup': soup
        }
        
    except Exception as e:
        print(f"  ❌ 分析失敗: {e}")
        return None

def extract_final_data(driver, result):
    """最終データ抽出"""
    try:
        soup = result['soup']
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
                    if attraction_name and attraction_name not in attractions:
                        attractions.append(attraction_name)
                break
        
        # データ抽出
        all_data = []
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
                        'date': result['date'].strftime("%Y%m%d"),
                        'formatted_date': result['date'].strftime("%m月%d日"),
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': f'yosocal_url_parameter_{result["source"]}'
                    }
                    all_data.append(record)
        
        return all_data
        
    except Exception as e:
        print(f"❌ 最終データ抽出失敗: {e}")
        return None

def save_final_csv(data, date_obj, partial=False):
    """最終CSV保存"""
    try:
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        prefix = "partial_" if partial else "complete_"
        csv_filename = f"data/yosocal_{prefix}url_parameter_28times_{timestamp}.csv"
        
        os.makedirs('data', exist_ok=True)
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"💾 CSV保存: {csv_filename}")
        print(f"📊 総レコード数: {len(df)}")
        print(f"⏰ 時間帯数: {df['time'].nunique()}")
        print(f"🎯 アトラクション数: {df['attraction'].nunique()}")
        print(f"✅ 有効待ち時間: {df['wait_time'].notna().sum()}")
        
        # 時間帯一覧表示
        time_list = sorted(df['time'].unique().tolist(), key=lambda x: x if x != '平均' else 'ZZ')
        print(f"📋 時間帯一覧: {time_list}")
        
    except Exception as e:
        print(f"❌ CSV保存失敗: {e}")

if __name__ == "__main__":
    url_parameter_28times_collection() 