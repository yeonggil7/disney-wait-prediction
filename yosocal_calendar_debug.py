#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def debug_yosocal_calendar():
    """yosocal.comカレンダーの利用可能日付を調査"""
    
    print("🔍 yosocal.com カレンダー調査開始")
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
        
        # カレンダー要素を調査
        print("\n📅 カレンダー要素調査:")
        print("-" * 30)
        
        available_dates = []
        
        # cal1-cal31まで調査
        for i in range(1, 32):
            cal_id = f"cal{i}"
            try:
                element = driver.find_element(By.ID, cal_id)
                cal_div = element.find_element(By.CLASS_NAME, "CAL")
                date_text = cal_div.text.strip()
                
                # JAM要素も取得
                jam_info = "なし"
                try:
                    jam_div = element.find_element(By.CLASS_NAME, "JAM0")
                    jam_info = jam_div.text.strip()
                except:
                    try:
                        jam_div = element.find_element(By.CLASS_NAME, "JAM1")
                        jam_info = f"JAM1: {jam_div.text.strip()}"
                    except:
                        pass
                
                print(f"✅ {cal_id}: 日付='{date_text}', 混雑指数={jam_info}")
                available_dates.append({
                    'id': cal_id,
                    'date': date_text,
                    'jam': jam_info,
                    'element': element
                })
                
            except Exception as e:
                print(f"❌ {cal_id}: 要素なし")
        
        print(f"\n📊 発見された日付: {len(available_dates)}個")
        
        # 数字の日付のみ抽出
        numeric_dates = []
        for date_info in available_dates:
            date_text = date_info['date']
            if date_text.isdigit():
                numeric_dates.append({
                    'day': int(date_text),
                    'info': date_info
                })
        
        numeric_dates.sort(key=lambda x: x['day'])
        
        print(f"\n📋 数字日付一覧:")
        for date_info in numeric_dates:
            day = date_info['day']
            info = date_info['info']
            print(f"  7月{day}日 (ID: {info['id']}, 混雑: {info['jam']})")
        
        # 過去日付（昨日まで）を特定
        past_dates = [d for d in numeric_dates if d['day'] <= 2]  # 7月2日まで
        
        if past_dates:
            print(f"\n🎯 過去日付候補:")
            for date_info in past_dates:
                day = date_info['day']
                info = date_info['info']
                print(f"  7月{day}日 (ID: {info['id']}) ← 28時間帯データ候補")
            
            # 最も古い日付をテスト
            oldest_date = past_dates[0]
            test_day = oldest_date['day']
            test_element = oldest_date['info']['element']
            
            print(f"\n🧪 7月{test_day}日でテストクリック:")
            try:
                driver.execute_script("arguments[0].click();", test_element)
                time.sleep(5)
                print(f"✅ 7月{test_day}日クリック成功")
                
                # realtime.htmに移動してデータ確認
                driver.get("https://yosocal.com/realtime.htm")
                time.sleep(5)
                
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # jamat divを確認
                jamat_div = soup.find('div', id='jamat')
                if jamat_div:
                    table = jamat_div.find('table')
                    if table:
                        # 時間データを確認
                        fpm_elements = table.find_all('td', class_='FPM')
                        fpt_elements = table.find_all('td', class_='FPT')
                        
                        times = []
                        for elem in fpm_elements:
                            time_text = elem.get_text(strip=True)
                            if time_text and time_text != '　':
                                times.append(time_text)
                        
                        for elem in fpt_elements:
                            time_text = elem.get_text(strip=True)
                            if time_text == '平均':
                                times.append(time_text)
                        
                        print(f"📊 7月{test_day}日データ:")
                        print(f"  時間帯数: {len(times)}個")
                        print(f"  時間帯一覧: {times}")
                        
                        if len(times) >= 20:
                            print(f"🎉 7月{test_day}日: 大量時間帯データあり！推奨")
                        else:
                            print(f"⚠️ 7月{test_day}日: 時間帯不足")
                
            except Exception as e:
                print(f"❌ 7月{test_day}日テストクリック失敗: {e}")
        else:
            print(f"\n⚠️ 過去日付が見つかりません")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ カレンダー調査エラー: {e}")

if __name__ == "__main__":
    debug_yosocal_calendar() 