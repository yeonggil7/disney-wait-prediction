#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os
import json

def setup_selenium_driver():
    """Selenium WebDriverのセットアップ"""
    print("🔧 Chrome WebDriver（7月2日分析版）をセットアップ中...")
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        return None

def analyze_july2_data():
    """2025年7月2日のデータを詳細分析"""
    
    print("🎢 yosocal.com 2025年7月2日データ詳細分析")
    print("=" * 70)
    
    driver = setup_selenium_driver()
    if not driver:
        return
    
    try:
        # yosocal.comにアクセス
        print("🌐 yosocal.comにアクセス中...")
        driver.get("https://yosocal.com/")
        time.sleep(5)
        
        # 7月2日をクリック（2025年7月の日付要素を探す）
        print("📅 7月2日の日付要素を探しています...")
        
        # 月が7月かを確認
        try:
            month_element = driver.find_element(By.XPATH, "//td[contains(text(), '7月')]")
            print("✅ 7月カレンダーを確認")
        except:
            print("❌ 7月カレンダーが見つかりません")
        
        # 7月2日の要素を探してクリック
        july2_clicked = False
        possible_selectors = [
            "//div[contains(@class, 'CAL') and contains(text(), '2')]",
            "//td[contains(text(), '2') and contains(@class, 'CAL')]",
            "//div[@class='CAL' and text()='2']",
            "//td[@class='CAL' and text()='2']"
        ]
        
        for selector in possible_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.text.strip() == "2":
                        print(f"📍 7月2日要素発見: {element.text}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(2)
                        
                        # クリック試行
                        try:
                            element.click()
                            print("✅ 7月2日をクリック成功")
                            july2_clicked = True
                            break
                        except Exception as click_error:
                            print(f"⚠️ 直接クリック失敗、JavaScript実行: {click_error}")
                            driver.execute_script("arguments[0].click();", element)
                            print("✅ 7月2日をJavaScriptクリック成功")
                            july2_clicked = True
                            break
                if july2_clicked:
                    break
            except Exception as e:
                continue
        
        if not july2_clicked:
            print("❌ 7月2日のクリックに失敗しました")
            print("📍 現在のページのタイトル:", driver.title)
            # デバッグ情報
            calendar_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'CAL')] | //td[contains(@class, 'CAL')]")
            print(f"📋 カレンダー要素数: {len(calendar_elements)}")
            for i, elem in enumerate(calendar_elements[:10]):
                print(f"   {i+1}: テキスト='{elem.text}', クラス='{elem.get_attribute('class')}'")
        
        # 日付クリック後の待機
        time.sleep(5)
        
        # realtime.htmに移動して待ち時間データ取得
        print("📊 realtime.htmからデータ取得中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(5)
        
        # ページソースを取得してBeautifulSoupで解析
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # デバッグ用HTMLファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"yosocal_july2_debug_{timestamp}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"🔍 デバッグファイル保存: {debug_file}")
        
        # jamat div要素を探す
        jamat_div = soup.find('div', {'id': 'jamat'})
        if not jamat_div:
            print("❌ jamat div要素が見つかりません")
            
            # フォールバック: FPMクラスを直接検索
            fpm_elements = soup.find_all('td', class_='FPM')
            print(f"📍 FPMクラス要素: {len(fpm_elements)}個発見")
            
            # テーブル要素を全探索
            tables = soup.find_all('table')
            print(f"📋 総テーブル数: {len(tables)}")
            
            for i, table in enumerate(tables[:5]):
                rows = table.find_all('tr')
                print(f"   テーブル{i+1}: {len(rows)}行")
                
                # FPMクラスを含む行を探す
                for j, row in enumerate(rows[:10]):
                    fpm_cell = row.find('td', class_='FPM')
                    if fpm_cell:
                        print(f"     行{j}: FPM='{fpm_cell.get_text().strip()}'")
            
            return None
        
        print("✅ jamat div要素を発見")
        
        # テーブル解析
        table = jamat_div.find('table')
        if not table:
            print("❌ jamat内にテーブルが見つかりません")
            return None
        
        rows = table.find_all('tr')
        print(f"📋 テーブル行数: {len(rows)}")
        
        # 時間データ（FPMクラス）を探す
        time_slots = []
        attraction_names = []
        
        # アトラクション名（FPh2クラス）を探す
        for i, row in enumerate(rows):
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells and not attraction_names:
                attraction_names = [cell.get_text().strip() for cell in fph2_cells]
                print(f"🎯 アトラクション名行発見 (行{i}): {len(attraction_names)}個")
                for j, name in enumerate(attraction_names[:10]):
                    print(f"   {j+1:2d}. {name}")
                if len(attraction_names) > 10:
                    print(f"   ... 他{len(attraction_names)-10}個")
                break
        
        # 時間データ（FPMクラス）を探す
        for i, row in enumerate(rows):
            fpm_cell = row.find('td', class_='FPM')
            if fpm_cell:
                time_text = fpm_cell.get_text().strip()
                if time_text and time_text != '　':
                    time_slots.append(time_text)
                    print(f"⏰ 行{i}: 時間データ「{time_text}」")
        
        print(f"\n📊 7月2日データ分析結果:")
        print(f"   ⏰ 時間帯数: {len(time_slots)}")
        print(f"   🎯 アトラクション数: {len(attraction_names)}")
        print(f"   📋 総行数: {len(rows)}")
        
        # 時間帯詳細
        if time_slots:
            print(f"\n⏰ 検出された時間帯:")
            for i, slot in enumerate(time_slots):
                print(f"   {i+1:2d}. {slot}")
        
        # 28時間帯達成チェック
        target_times = generate_expected_28_times()
        print(f"\n🎯 28時間帯達成チェック:")
        print(f"   期待値: {len(target_times)}個")
        print(f"   実際値: {len(time_slots)}個")
        
        if len(time_slots) >= 28:
            print("   ✅ 28時間帯達成！")
        else:
            print(f"   ❌ 不足: {28 - len(time_slots)}個")
            
            # 不足している時間帯を特定
            detected_set = set(time_slots)
            expected_set = set(target_times)
            missing_times = expected_set - detected_set
            
            if missing_times:
                print(f"   📋 不足時間帯:")
                for missing in sorted(missing_times):
                    print(f"     - {missing}")
        
        # データをCSVで保存
        if time_slots and attraction_names:
            save_july2_analysis_data(time_slots, attraction_names, driver.current_url)
        
        return {
            'time_slots': time_slots,
            'attraction_names': attraction_names,
            'total_rows': len(rows),
            'debug_file': debug_file
        }
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        driver.quit()
        print("🔧 WebDriver終了")

def generate_expected_28_times():
    """期待される28個の時間帯を生成"""
    times = []
    
    # 8:15から21:45まで30分間隔
    start_hour = 8
    start_minute = 15
    
    current_hour = start_hour
    current_minute = start_minute
    
    while current_hour < 22 or (current_hour == 21 and current_minute <= 45):
        time_str = f"{current_hour:02d}:{current_minute:02d}"
        times.append(time_str)
        
        # 30分追加
        current_minute += 30
        if current_minute >= 60:
            current_minute -= 60
            current_hour += 1
    
    # 平均も追加
    times.append("平均")
    
    return times

def save_july2_analysis_data(time_slots, attraction_names, source_url):
    """7月2日分析データを保存"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 分析結果をJSONで保存
    analysis_data = {
        'analysis_date': timestamp,
        'target_date': '2025年7月2日',
        'time_slots_count': len(time_slots),
        'time_slots': time_slots,
        'attraction_count': len(attraction_names),
        'attraction_names': attraction_names[:10],  # 最初の10個のみ保存
        'source_url': source_url,
        'target_achieved': len(time_slots) >= 28
    }
    
    json_file = f"yosocal_july2_analysis_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 分析結果保存: {json_file}")
    
    # CSVファイルも作成
    csv_data = []
    for time_slot in time_slots:
        for attraction in attraction_names:
            csv_data.append({
                'date': '7月02日',
                'time': time_slot,
                'attraction': attraction,
                'wait_time': None,
                'status': 'detected_structure',
                'data_source': 'july2_analysis'
            })
    
    if csv_data:
        df = pd.DataFrame(csv_data)
        csv_file = f"yosocal_july2_structure_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"💾 構造データ保存: {csv_file}")

if __name__ == "__main__":
    print("🎢 2025年7月2日 yosocal.com データ分析開始")
    print("📊 28時間帯達成状況を詳細調査")
    print("=" * 70)
    
    result = analyze_july2_data()
    
    if result:
        print(f"\n🎉 7月2日分析完了!")
        print(f"📊 時間帯数: {len(result['time_slots'])}")
        print(f"🎯 アトラクション数: {len(result['attraction_names'])}")
        
        if len(result['time_slots']) >= 28:
            print("✅ 28時間帯目標達成！")
        else:
            print(f"❌ 28時間帯未達成 (不足: {28 - len(result['time_slots'])}個)")
    else:
        print("💥 7月2日分析失敗") 