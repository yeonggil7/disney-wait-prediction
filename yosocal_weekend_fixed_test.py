#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
土日対応テスト用スクリプト（修正版）
動作確認済み方式を使用
"""

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re

def setup_driver():
    """高速WebDriverセットアップ"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')
    options.add_argument('--disable-extensions')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def navigate_to_month(driver, target_year, target_month):
    """指定の年月に移動（動作確認済み方式）"""
    print(f"📅 {target_year}年{target_month:02d}月への移動開始...")
    
    max_month_moves = 12
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
                        return True
                    
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
    
    return False

def test_date_element_detection(driver, test_dates):
    """日付要素検出のテスト"""
    print("🔍 日付要素検出テスト開始")
    
    for date_info in test_dates:
        date_str = date_info['date']
        day = date_info['day']
        day_type = date_info['type']
        
        print(f"\\n📅 テスト対象: {date_str} ({day}日, {day_type})")
        
        # 全ての日付クラスを検索
        date_elements = []
        class_counts = {}
        
        for class_name in ["CAL", "CALSAT", "CALSUN"]:
            elements = driver.find_elements(By.CLASS_NAME, class_name)
            class_counts[class_name] = len(elements)
            date_elements.extend(elements)
        
        print(f"📊 検出クラス数: CAL={class_counts['CAL']}, CALSAT={class_counts['CALSAT']}, CALSUN={class_counts['CALSUN']}")
        print(f"📊 総日付要素数: {len(date_elements)}")
        
        # onclick属性での検索
        found_by_onclick = False
        for element in date_elements:
            onclick_attr = element.get_attribute("onclick")
            if onclick_attr and f"fMouseclick({date_str}," in onclick_attr:
                element_class = element.get_attribute("class")
                print(f"✅ onclick検索成功: クラス={element_class}, onclick={onclick_attr}")
                found_by_onclick = True
                # 実際にクリックしてテスト
                element.click()
                time.sleep(2)
                print(f"📱 {day_type}クリック成功")
                break
        
        if not found_by_onclick:
            print("❌ onclick検索失敗")
        
        # テキスト内容での検索
        found_by_text = False
        for element in date_elements:
            if element.text.strip() == str(day):
                element_class = element.get_attribute("class")
                parent = element.find_element(By.XPATH, "..")
                parent_onclick = parent.get_attribute("onclick")
                print(f"📝 テキスト検索結果: クラス={element_class}, テキスト='{element.text}', 親onclick={parent_onclick}")
                if parent_onclick and f"fMouseclick({date_str}," in parent_onclick:
                    print(f"✅ テキスト検索成功: 親要素にonclick発見")
                    found_by_text = True
                break
        
        if not found_by_text:
            print("❌ テキスト検索失敗")

def main():
    print("🚀 土日対応日付検出テスト（修正版）")
    print("=" * 50)
    
    # テスト対象日付（平日・土日混合）
    test_dates = [
        {'date': '20250102', 'day': 2, 'type': '平日'},
        {'date': '20250104', 'day': 4, 'type': '土曜'},
        {'date': '20250105', 'day': 5, 'type': '日曜'},
        {'date': '20250106', 'day': 6, 'type': '平日'},
    ]
    
    driver = setup_driver()
    
    try:
        print("🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        # 2025年1月に移動
        if navigate_to_month(driver, 2025, 1):
            # 日付要素検出テスト
            test_date_element_detection(driver, test_dates)
        else:
            print("❌ 月移動失敗")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    finally:
        driver.quit()
        print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 