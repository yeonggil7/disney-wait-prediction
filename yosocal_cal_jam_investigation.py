# -*- coding: utf-8 -*-
"""
yosocal.com CAL/JAMクラス要素詳細調査
実際のカレンダー機能を見つけて6月データを取得
"""

import time
import re
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ WebDriverセットアップ完了")
    return driver

def investigate_cal_jam_elements(driver):
    """CAL/JAMクラス要素を詳しく調査"""
    print("\n🔍 CAL/JAMクラス要素詳細調査")
    print("=" * 50)
    
    try:
        # CAL関連要素を詳しく調査
        cal_patterns = [
            ("CALクラス", "//div[@class='CAL']"),
            ("CALSUNクラス", "//div[@class='CALSUN']"),
            ("CAL含むクラス", "//*[contains(@class, 'CAL')]"),
            ("JAMクラス", "//div[contains(@class, 'JAM')]"),
            ("JAM1クラス", "//div[@class='JAM1']"),
            ("JAM2クラス", "//div[@class='JAM2']"),
            ("JAM3クラス", "//div[@class='JAM3']"),
            ("JAM4クラス", "//div[@class='JAM4']"),
            ("JAM5クラス", "//div[@class='JAM5']")
        ]
        
        cal_elements = []
        
        for pattern_name, xpath in cal_patterns:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                print(f"\n📋 {pattern_name}: {len(elements)}個")
                
                for i, elem in enumerate(elements[:10]):
                    try:
                        text = elem.text.strip()
                        class_attr = elem.get_attribute('class')
                        id_attr = elem.get_attribute('id')
                        onclick = elem.get_attribute('onclick')
                        parent_onclick = elem.find_element(By.XPATH, "..").get_attribute('onclick') if elem.find_element(By.XPATH, "..") else None
                        
                        print(f"   {i+1:2d}: class='{class_attr}' text='{text}' id='{id_attr}'")
                        if onclick:
                            print(f"        onclick: {onclick}")
                        if parent_onclick:
                            print(f"        parent onclick: {parent_onclick[:50]}...")
                        
                        # 数字の場合は後でクリックテスト用に保存
                        if text.isdigit() and 1 <= int(text) <= 31:
                            cal_elements.append({
                                'element': elem,
                                'text': text,
                                'class': class_attr,
                                'id': id_attr,
                                'onclick': onclick,
                                'parent_onclick': parent_onclick
                            })
                            
                    except Exception as e:
                        print(f"   {i+1:2d}: 要素詳細取得エラー: {e}")
                        
            except Exception as e:
                print(f"❌ {pattern_name} 検索エラー: {e}")
        
        return cal_elements
        
    except Exception as e:
        print(f"❌ CAL/JAM要素調査エラー: {e}")
        return []

def test_javascript_events(driver, cal_elements):
    """JavaScript経由での要素クリックをテスト"""
    print("\n🔍 JavaScript経由クリックテスト")
    print("=" * 50)
    
    if not cal_elements:
        print("❌ テスト対象の要素がありません")
        return False
    
    # 最初の数字要素でテスト
    test_element = cal_elements[0]
    print(f"📅 テスト対象: {test_element['text']}日 (class: {test_element['class']})")
    
    try:
        # クリック前の状態を記録
        before_url = driver.current_url
        before_source_length = len(driver.page_source)
        
        # 様々な方法でクリックを試行
        click_methods = [
            ("通常クリック", lambda elem: elem.click()),
            ("JavaScriptクリック", lambda elem: driver.execute_script("arguments[0].click();", elem)),
            ("マウスイベント", lambda elem: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", elem)),
            ("親要素クリック", lambda elem: driver.execute_script("arguments[0].parentElement.click();", elem))
        ]
        
        for method_name, click_func in click_methods:
            try:
                print(f"\n   🖱️ {method_name}を試行中...")
                
                click_func(test_element['element'])
                time.sleep(3)
                
                # 変化をチェック
                after_url = driver.current_url
                after_source_length = len(driver.page_source)
                
                print(f"      URL変化: {before_url == after_url}")
                print(f"      ページサイズ: {before_source_length:,} → {after_source_length:,}")
                
                # データテーブル要素をチェック
                fpm_elements = driver.find_elements(By.XPATH, "//td[@class='FPM']")
                fph2_elements = driver.find_elements(By.XPATH, "//td[@class='FPh2']")
                b_class_elements = driver.find_elements(By.XPATH, "//td[contains(@class, 'B') and (text()>='1' or text()='-')]")
                jamat_div = driver.find_elements(By.ID, "jamat")
                
                print(f"      FPM要素: {len(fpm_elements)}個")
                print(f"      FPh2要素: {len(fph2_elements)}個")
                print(f"      Bクラス要素: {len(b_class_elements)}個")
                print(f"      jamat div: {len(jamat_div)}個")
                
                if fpm_elements and fph2_elements and b_class_elements:
                    print(f"   ✅ {method_name}で待機時間データテーブルが表示されました！")
                    return True
                elif jamat_div:
                    print(f"   ⚠️ {method_name}でjamat divが見つかりましたが、データは不完全です")
                else:
                    print(f"   ❌ {method_name}では待機時間データは表示されませんでした")
                
            except Exception as e:
                print(f"   ❌ {method_name}エラー: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ JavaScriptクリックテストエラー: {e}")
        return False

def check_hidden_calendar_functionality(driver):
    """隠された(hidden)カレンダー機能をチェック"""
    print("\n🔍 隠されたカレンダー機能チェック")
    print("=" * 50)
    
    try:
        # JavaScript関数の確認
        js_functions = [
            "if(typeof cal !== 'undefined') console.log('cal function exists'); else console.log('cal function not found');",
            "if(typeof calendar !== 'undefined') console.log('calendar function exists'); else console.log('calendar function not found');",
            "if(typeof selectDate !== 'undefined') console.log('selectDate function exists'); else console.log('selectDate function not found');",
            "console.log('Available global functions:', Object.getOwnPropertyNames(window).filter(item => typeof window[item] === 'function'));"
        ]
        
        for js in js_functions:
            try:
                result = driver.execute_script(js)
                print(f"   JS実行結果: {result}")
            except Exception as e:
                print(f"   JS実行エラー: {e}")
        
        # イベントリスナーの確認
        check_listeners_js = """
        var elements = document.querySelectorAll('div[class*="CAL"], div[class*="JAM"]');
        var results = [];
        elements.forEach(function(elem, index) {
            var listeners = getEventListeners ? getEventListeners(elem) : 'getEventListeners not available';
            results.push({
                index: index,
                class: elem.className,
                text: elem.textContent.trim(),
                hasClickListener: listeners.click ? listeners.click.length : 0
            });
        });
        return results;
        """
        
        try:
            listener_results = driver.execute_script(check_listeners_js)
            print(f"   イベントリスナー調査結果: {listener_results}")
        except Exception as e:
            print(f"   イベントリスナー調査エラー: {e}")
        
        # 手動でのJavaScript関数実行テスト
        test_functions = [
            ("cal(1)", "cal(1);"),
            ("cal('1')", "cal('1');"),
            ("calendar(1)", "calendar(1);"),
            ("selectDate(1)", "selectDate(1);"),
            ("clickDate(1)", "clickDate(1);"),
        ]
        
        for func_name, js_code in test_functions:
            try:
                print(f"   🔧 {func_name}を試行中...")
                driver.execute_script(js_code)
                time.sleep(2)
                
                # データが表示されたかチェック
                fpm_elements = driver.find_elements(By.XPATH, "//td[@class='FPM']")
                if fpm_elements:
                    print(f"   ✅ {func_name}で待機時間データが表示されました！")
                    return True
                else:
                    print(f"   ❌ {func_name}では効果なし")
                    
            except Exception as e:
                print(f"   ❌ {func_name}エラー: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 隠されたカレンダー機能チェックエラー: {e}")
        return False

def try_month_navigation(driver):
    """月移動を様々な方法で試行"""
    print("\n🔍 月移動機能試行")
    print("=" * 50)
    
    try:
        # 現在の年月を確認
        current_month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2025年') and contains(text(), '月')]")
        if current_month_elements:
            current_month = current_month_elements[0].text
            print(f"   現在の月: {current_month}")
        
        # 様々な月移動方法を試行
        navigation_methods = [
            ("prev()", "prev();"),
            ("next()", "next();"),
            ("goPrevMonth()", "goPrevMonth();"),
            ("goNextMonth()", "goNextMonth();"),
            ("changeMonth(-1)", "changeMonth(-1);"),
            ("changeMonth(6)", "changeMonth(6);"),  # 6月に直接移動
            ("setMonth(6)", "setMonth(6);"),
            ("showMonth(2025, 6)", "showMonth(2025, 6);"),
        ]
        
        for method_name, js_code in navigation_methods:
            try:
                print(f"   🔧 {method_name}を試行中...")
                driver.execute_script(js_code)
                time.sleep(2)
                
                # 月が変わったかチェック
                new_month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2025年') and contains(text(), '月')]")
                if new_month_elements:
                    new_month = new_month_elements[0].text
                    print(f"      結果: {new_month}")
                    
                    if "6月" in new_month:
                        print(f"   ✅ {method_name}で6月に移動成功！")
                        return True
                        
            except Exception as e:
                print(f"   ❌ {method_name}エラー: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 月移動機能試行エラー: {e}")
        return False

def main():
    """メイン調査プロセス"""
    print("🔍 yosocal.com CAL/JAMクラス詳細調査")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # メインページにアクセス
        print("🌐 yosocal.comメインページにアクセス中...")
        driver.get('https://yosocal.com/')
        time.sleep(5)
        
        # CAL/JAM要素を詳しく調査
        cal_elements = investigate_cal_jam_elements(driver)
        
        # JavaScript経由でのクリックテスト
        click_success = test_javascript_events(driver, cal_elements)
        
        # 隠されたカレンダー機能をチェック
        if not click_success:
            hidden_success = check_hidden_calendar_functionality(driver)
        
        # 月移動機能を試行
        june_success = try_month_navigation(driver)
        
        if june_success:
            print("\n✅ 6月への移動成功！日付クリックを再テスト...")
            cal_elements_june = investigate_cal_jam_elements(driver)
            test_javascript_events(driver, cal_elements_june)
        
        print("\n✅ CAL/JAMクラス詳細調査完了")
        
    except Exception as e:
        print(f"❌ 調査プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 