#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def investigate_yosocal_specification():
    """yosocal.com の詳細仕様調査"""
    
    print("🔍 yosocal.com サイト仕様詳細調査開始")
    print("="*70)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        # === 1. メインページ調査 ===
        print("📋 1. メインページ (yosocal.com) 調査...")
        driver.get("https://yosocal.com/")
        time.sleep(5)
        
        # カレンダー要素調査
        try:
            calendar_elements = driver.find_elements(By.CLASS_NAME, "BOXA")
            print(f"✅ カレンダー要素数: {len(calendar_elements)}")
            
            if calendar_elements:
                # 最初のカレンダー要素の詳細調査
                first_cal = calendar_elements[0]
                print(f"📊 カレンダー要素の詳細:")
                print(f"  - ID: {first_cal.get_attribute('id')}")
                print(f"  - onclick: {first_cal.get_attribute('onclick')}")
                print(f"  - HTML: {first_cal.get_attribute('outerHTML')[:200]}...")
                
                # 内部要素調査
                cal_divs = first_cal.find_elements(By.TAG_NAME, "div")
                for i, div in enumerate(cal_divs):
                    class_name = div.get_attribute('class')
                    text_content = div.text
                    print(f"    [{i}] class='{class_name}' text='{text_content}'")
        except Exception as e:
            print(f"❌ カレンダー要素調査失敗: {e}")
        
        # === 2. realtime.htm直接アクセス調査 ===
        print(f"\n📋 2. realtime.htm 直接アクセス調査...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(8)
        
        # ディズニーランド選択
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
            print("✅ ディズニーランド選択確認")
        except:
            print("⚠️ パーク選択要素なし")
        
        # 現在のページの時間要素調査
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # FPM/FPT要素数確認
        fpm_elements = soup.find_all('td', class_='FPM')
        fpt_elements = soup.find_all('td', class_='FPT')
        
        print(f"📊 realtime.htm 直接アクセス結果:")
        print(f"  - FPM要素数 (時間): {len(fpm_elements)}")
        print(f"  - FPT要素数 (平均): {len(fpt_elements)}")
        print(f"  - 合計時間要素: {len(fpm_elements) + len(fpt_elements)}")
        
        # 実際の時間データ表示
        time_data = []
        for fpm in fpm_elements:
            time_text = fpm.get_text(strip=True)
            if re.match(r'^\d{2}:\d{2}$', time_text):
                time_data.append(time_text)
        
        for fpt in fpt_elements:
            time_text = fpt.get_text(strip=True)
            if time_text == '平均':
                time_data.append(time_text)
        
        print(f"📋 検出された時間帯: {time_data}")
        
        # === 3. カレンダーからのナビゲーション試行 ===
        print(f"\n📋 3. カレンダーナビゲーション試行...")
        
        # メインページに戻る
        driver.get("https://yosocal.com/")
        time.sleep(5)
        
        # カレンダー要素再取得
        calendar_elements = driver.find_elements(By.CLASS_NAME, "BOXA")
        if calendar_elements:
            # 明日の日付要素を探す
            tomorrow = datetime.now() + timedelta(days=1)
            tomorrow_date = tomorrow.strftime("%Y%m%d")
            
            target_element = None
            for cal_elem in calendar_elements:
                onclick_attr = cal_elem.get_attribute('onclick')
                if onclick_attr and tomorrow_date in onclick_attr:
                    target_element = cal_elem
                    break
            
            if not target_element and calendar_elements:
                # 最初の要素を使用
                target_element = calendar_elements[0]
            
            if target_element:
                print(f"🎯 クリック対象カレンダー要素:")
                print(f"  - onclick: {target_element.get_attribute('onclick')}")
                
                # JavaScriptでクリック
                driver.execute_script("arguments[0].click();", target_element)
                time.sleep(3)
                
                # realtime.htmに移動
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
                
                # カレンダー選択後の時間要素確認
                soup2 = BeautifulSoup(driver.page_source, 'html.parser')
                fpm_elements2 = soup2.find_all('td', class_='FPM')
                fpt_elements2 = soup2.find_all('td', class_='FPT')
                
                print(f"📊 カレンダー選択後結果:")
                print(f"  - FPM要素数 (時間): {len(fpm_elements2)}")
                print(f"  - FPT要素数 (平均): {len(fpt_elements2)}")
                print(f"  - 合計時間要素: {len(fpm_elements2) + len(fpt_elements2)}")
                
                # 時間データ再確認
                time_data2 = []
                for fpm in fpm_elements2:
                    time_text = fpm.get_text(strip=True)
                    if re.match(r'^\d{2}:\d{2}$', time_text):
                        time_data2.append(time_text)
                
                for fpt in fpt_elements2:
                    time_text = fpt.get_text(strip=True)
                    if time_text == '平均':
                        time_data2.append(time_text)
                
                print(f"📋 カレンダー選択後の時間帯: {time_data2}")
        
        # === 4. JavaScript関数調査 ===
        print(f"\n📋 4. JavaScript関数調査...")
        
        # fMouseclick関数の調査
        try:
            # JavaScriptコードを調査
            script_elements = driver.find_elements(By.TAG_NAME, "script")
            for script in script_elements:
                script_content = script.get_attribute('innerHTML')
                if script_content and 'fMouseclick' in script_content:
                    print(f"📜 fMouseclick関数発見:")
                    # 関数の一部を表示
                    lines = script_content.split('\n')
                    for i, line in enumerate(lines):
                        if 'fMouseclick' in line:
                            start = max(0, i-2)
                            end = min(len(lines), i+10)
                            print("```javascript")
                            for j in range(start, end):
                                print(f"{j:3d}: {lines[j]}")
                            print("```")
                            break
                    break
        except Exception as e:
            print(f"⚠️ JavaScript調査失敗: {e}")
        
        # === 5. 期待される28時間帯生成 ===
        print(f"\n📋 5. 期待される28時間帯確認...")
        expected_times = []
        for hour in range(8, 22):  # 8:00-21:00
            expected_times.append(f"{hour:02d}:15")
            expected_times.append(f"{hour:02d}:45")
        expected_times.append("平均")
        
        print(f"🎯 期待される時間帯数: {len(expected_times)}")
        print(f"📋 期待される時間帯: {expected_times}")
        
        # デバッグHTML保存
        debug_filename = f"yosocal_specification_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"📁 デバッグHTML保存: {debug_filename}")
        
        driver.quit()
        
        print(f"\n🎉 yosocal.com 仕様調査完了！")
        
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    investigate_yosocal_specification() 