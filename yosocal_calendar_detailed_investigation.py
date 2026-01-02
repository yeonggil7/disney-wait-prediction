# -*- coding: utf-8 -*-
"""
yosocal.com カレンダー機能詳細調査
6月のデータ取得のためのカレンダー要素を詳しく分析
"""

import time
import re
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

def find_all_calendar_elements(driver):
    """すべてのカレンダー関連要素を詳しく調査"""
    print("\n🔍 カレンダー要素詳細調査")
    print("=" * 50)
    
    try:
        # 様々な方法でカレンダー要素を検索
        search_methods = [
            ("ID含む 'cal'", "//td[contains(@id, 'cal')]"),
            ("ID含む 'CAL'", "//td[contains(@id, 'CAL')]"),
            ("クラス含む 'cal'", "//td[contains(@class, 'cal')]"),
            ("クラス含む 'CAL'", "//td[contains(@class, 'CAL')]"),
            ("onclick属性", "//td[@onclick]"),
            ("数字のテキスト", "//td[text()>=1 and text()<=31]"),
            ("1-31の数字パターン", "//*[text()>='1' and text()<='31']"),
            ("日付っぽいパターン", "//*[contains(text(), '日') or (text()>='1' and text()<='31' and string-length(text())<=2)]"),
            ("テーブルのセル", "//table//td"),
            ("クリック可能なセル", "//td[@onclick or contains(@style, 'cursor')]")
        ]
        
        for method_name, xpath in search_methods:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                print(f"\n📋 {method_name}: {len(elements)}個")
                
                for i, elem in enumerate(elements[:10]):  # 最初の10個まで表示
                    try:
                        tag = elem.tag_name
                        id_attr = elem.get_attribute('id')
                        class_attr = elem.get_attribute('class')
                        onclick = elem.get_attribute('onclick')
                        text = elem.text.strip()
                        
                        # 数字のみのテキストかチェック
                        is_number = text.isdigit() and 1 <= int(text) <= 31 if text.isdigit() else False
                        
                        print(f"   {i+1:2d}: <{tag}> id='{id_attr}' class='{class_attr}' text='{text}' {'[数字]' if is_number else ''}")
                        if onclick:
                            print(f"        onclick: {onclick[:100]}...")
                            
                    except Exception as e:
                        print(f"   {i+1:2d}: 要素取得エラー: {e}")
                        
            except Exception as e:
                print(f"❌ {method_name} 検索エラー: {e}")
        
        # ページの基本構造も確認
        print(f"\n📊 ページ基本情報:")
        print(f"   URL: {driver.current_url}")
        print(f"   タイトル: {driver.title}")
        
        # JavaScriptが実行される前後での要素数の変化を確認
        time.sleep(3)
        print(f"   3秒待機後の再チェック...")
        
        cal_elements_after = driver.find_elements(By.XPATH, "//td[contains(@id, 'cal') or contains(@id, 'CAL')]")
        print(f"   cal要素（待機後）: {len(cal_elements_after)}個")
        
    except Exception as e:
        print(f"❌ カレンダー要素調査エラー: {e}")

def find_month_navigation(driver):
    """月移動ボタンを見つける"""
    print("\n🔍 月移動ボタン調査")
    print("=" * 50)
    
    try:
        # 月移動に関連する要素を検索
        navigation_methods = [
            ("前月・次月ボタン", "//a[contains(text(), '前') or contains(text(), '次') or contains(text(), '←') or contains(text(), '→')]"),
            ("MHクラス", "//td[@class='MHBT']"),
            ("月表示クラス", "//td[@class='MHDT']"),
            ("年月表示", "//*[contains(text(), '年') and contains(text(), '月')]"),
            ("矢印画像", "//img[contains(@src, 'arrow') or contains(@alt, 'prev') or contains(@alt, 'next')]"),
            ("リンク要素", "//a[@href]")
        ]
        
        for method_name, xpath in navigation_methods:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                print(f"\n📋 {method_name}: {len(elements)}個")
                
                for i, elem in enumerate(elements[:5]):
                    try:
                        tag = elem.tag_name
                        href = elem.get_attribute('href')
                        onclick = elem.get_attribute('onclick')
                        text = elem.text.strip()
                        class_attr = elem.get_attribute('class')
                        
                        print(f"   {i+1}: <{tag}> class='{class_attr}' text='{text}'")
                        if href:
                            print(f"        href: {href}")
                        if onclick:
                            print(f"        onclick: {onclick[:100]}...")
                            
                    except Exception as e:
                        print(f"   {i+1}: 要素詳細取得エラー: {e}")
                        
            except Exception as e:
                print(f"❌ {method_name} 検索エラー: {e}")
                
    except Exception as e:
        print(f"❌ 月移動ボタン調査エラー: {e}")

def try_navigate_to_june(driver):
    """6月への移動を試行"""
    print("\n🔍 6月への移動試行")
    print("=" * 50)
    
    try:
        # 現在の年月を確認
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            current_display = month_elements[0].text
            print(f"   現在表示: {current_display}")
        
        # 前月ボタンを探す
        prev_buttons = driver.find_elements(By.XPATH, "//td[@class='MHBT'][1]//a")
        if prev_buttons:
            print(f"   前月ボタンを発見: {len(prev_buttons)}個")
            
            # 最大5回まで前月に移動して6月を探す
            for attempt in range(5):
                try:
                    # 現在の月を確認
                    month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
                    if month_elements:
                        current_month = month_elements[0].text
                        print(f"   試行 {attempt+1}: {current_month}")
                        
                        if "6月" in current_month or "06月" in current_month:
                            print(f"   ✅ 6月に到達！")
                            return True
                    
                    # 前月ボタンをクリック
                    prev_button = driver.find_element(By.XPATH, "//td[@class='MHBT'][1]//a")
                    prev_button.click()
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"   ❌ 移動試行 {attempt+1} エラー: {e}")
                    break
        
        # 他の方法も試す
        alternative_methods = [
            ("矢印テキスト ←", "//a[contains(text(), '←')]"),
            ("前月テキスト", "//a[contains(text(), '前')]"),
            ("JavaScriptリンク", "//a[contains(@href, 'javascript:')]")
        ]
        
        for method_name, xpath in alternative_methods:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    print(f"   代替方法 {method_name}: {len(elements)}個見つかった")
                    element = elements[0]
                    element.click()
                    time.sleep(2)
                    
                    # 6月になったかチェック
                    month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
                    if month_elements and "6月" in month_elements[0].text:
                        print(f"   ✅ {method_name}で6月に到達！")
                        return True
                        
            except Exception as e:
                print(f"   ❌ {method_name} 試行エラー: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 6月移動試行エラー: {e}")
        return False

def test_date_clicking(driver):
    """日付クリック機能をテスト"""
    print("\n🔍 日付クリック機能テスト")
    print("=" * 50)
    
    try:
        # 現在の月を確認
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            current_month = month_elements[0].text
            print(f"   現在の月: {current_month}")
        
        # すべての数字要素を取得
        number_elements = []
        
        # 様々な方法で数字要素を探す
        search_patterns = [
            "//td[text()>='1' and text()<='31' and string-length(text())<=2]",
            "//td[@onclick and text()>='1' and text()<='31']",
            "//td[contains(@id, 'cal') and text()>='1' and text()<='31']",
            "//*[text()>='1' and text()<='31' and string-length(text())<=2]"
        ]
        
        for pattern in search_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    text = elem.text.strip()
                    if text.isdigit() and 1 <= int(text) <= 31:
                        onclick = elem.get_attribute('onclick')
                        id_attr = elem.get_attribute('id')
                        class_attr = elem.get_attribute('class')
                        
                        number_elements.append({
                            'element': elem,
                            'text': text,
                            'id': id_attr,
                            'class': class_attr,
                            'onclick': onclick,
                            'pattern': pattern
                        })
            except Exception as e:
                print(f"   パターン {pattern} エラー: {e}")
        
        # 重複を削除
        unique_elements = []
        seen_texts = set()
        for elem_info in number_elements:
            if elem_info['text'] not in seen_texts:
                unique_elements.append(elem_info)
                seen_texts.add(elem_info['text'])
        
        print(f"   発見された日付要素: {len(unique_elements)}個")
        
        for elem_info in unique_elements[:10]:
            print(f"   日付 {elem_info['text']}: id='{elem_info['id']}' class='{elem_info['class']}'")
            if elem_info['onclick']:
                print(f"      onclick: {elem_info['onclick'][:50]}...")
        
        # 実際に1つの日付をクリックしてテスト
        if unique_elements:
            test_element = unique_elements[0]
            print(f"\n   🖱️ テスト: 日付 {test_element['text']} をクリック中...")
            
            try:
                # クリック前のページソース長さ
                before_length = len(driver.page_source)
                
                test_element['element'].click()
                time.sleep(3)
                
                # クリック後のページソース長さ
                after_length = len(driver.page_source)
                
                print(f"   ページサイズ変化: {before_length:,} → {after_length:,} 文字")
                
                # 待機時間データが表示されたかチェック
                wait_time_elements = driver.find_elements(By.XPATH, "//td[contains(@class, 'B') and text()>='1']")
                fpm_elements = driver.find_elements(By.XPATH, "//td[@class='FPM']")
                fph2_elements = driver.find_elements(By.XPATH, "//td[@class='FPh2']")
                
                print(f"   クリック後のデータ要素:")
                print(f"     待機時間データ (Bクラス): {len(wait_time_elements)}個")
                print(f"     時間データ (FPM): {len(fpm_elements)}個")
                print(f"     アトラクション名 (FPh2): {len(fph2_elements)}個")
                
                if wait_time_elements or fpm_elements or fph2_elements:
                    print(f"   ✅ 日付クリックでデータテーブルが表示されました！")
                    return True
                else:
                    print(f"   ❌ データテーブルは表示されませんでした")
                    
            except Exception as e:
                print(f"   ❌ 日付クリックエラー: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 日付クリックテストエラー: {e}")
        return False

def main():
    """メイン調査プロセス"""
    print("🔍 yosocal.com カレンダー機能詳細調査")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # メインページにアクセス
        print("🌐 yosocal.comメインページにアクセス中...")
        driver.get('https://yosocal.com/')
        time.sleep(5)  # JavaScriptの読み込みを待つ
        
        # カレンダー要素を詳しく調査
        find_all_calendar_elements(driver)
        
        # 月移動ボタンを調査
        find_month_navigation(driver)
        
        # 6月への移動を試行
        june_reached = try_navigate_to_june(driver)
        
        if june_reached:
            print("\n✅ 6月に移動成功！日付クリックをテスト中...")
            test_date_clicking(driver)
        else:
            print("\n❌ 6月への移動ができませんでした。現在の月で日付クリックをテスト...")
            test_date_clicking(driver)
        
        print("\n✅ カレンダー機能詳細調査完了")
        
    except Exception as e:
        print(f"❌ 調査プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 