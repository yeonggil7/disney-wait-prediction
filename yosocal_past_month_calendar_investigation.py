# -*- coding: utf-8 -*-
"""
yosocal.com 過去の月カレンダー構造詳細調査
2024年1月のカレンダー構造と日付要素を詳しく分析
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

def navigate_to_month(driver, year, month):
    """指定した年月に移動"""
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # JavaScript関数で月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(5)
        
        # 移動確認
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            current_month = month_elements[0].text.strip()
            if str(year) in current_month and str(month) in current_month:
                return True, current_month
        
        return False, "移動失敗"
        
    except Exception as e:
        return False, f"エラー: {e}"

def analyze_calendar_structure(driver):
    """カレンダー構造を詳しく分析"""
    print("\n🔍 カレンダー構造詳細分析")
    print("=" * 50)
    
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 様々な方法で日付要素を検索
        search_methods = [
            ("CAL クラス", soup.find_all(class_='CAL')),
            ("CALSAT クラス", soup.find_all(class_='CALSAT')),
            ("CALSUN クラス", soup.find_all(class_='CALSUN')),
            ("数字のみのテキスト", soup.find_all(text=re.compile(r'^\d{1,2}$'))),
            ("td要素内の数字", soup.find_all('td', text=re.compile(r'^\d{1,2}$'))),
            ("クリック可能な要素", soup.find_all(attrs={"onclick": True})),
            ("JAM関連要素", soup.find_all(class_=re.compile(r'JAM.*'))),
        ]
        
        for method_name, elements in search_methods:
            print(f"\n📋 {method_name}:")
            
            if elements:
                print(f"   発見: {len(elements)}個")
                
                for i, elem in enumerate(elements[:10]):  # 最初の10個まで表示
                    # 要素の詳細を分析
                    tag = elem.name if hasattr(elem, 'name') else 'text'
                    
                    if hasattr(elem, 'get_text'):
                        text = elem.get_text(strip=True)
                        classes = elem.get('class', [])
                        onclick = elem.get('onclick', '')
                        parent = elem.parent.name if elem.parent else 'None'
                        parent_classes = elem.parent.get('class', []) if elem.parent else []
                        
                        print(f"     {i+1}. <{tag} class='{' '.join(classes)}' onclick='{onclick[:50]}...'>{text}</{tag}>")
                        print(f"        親要素: <{parent} class='{' '.join(parent_classes)}'>")
                    else:
                        # テキストノードの場合
                        parent = elem.parent if hasattr(elem, 'parent') else None
                        if parent:
                            parent_classes = parent.get('class', [])
                            parent_onclick = parent.get('onclick', '')
                            print(f"     {i+1}. テキスト: '{elem}' 親: <{parent.name} class='{' '.join(parent_classes)}' onclick='{parent_onclick[:50]}...'>")
                        else:
                            print(f"     {i+1}. テキスト: '{elem}'")
            else:
                print(f"   要素なし")
        
        # 特定の日付を詳しく調査
        print(f"\n🎯 日付 '2' の詳細調査:")
        date_2_elements = []
        
        # テキストが '2' の要素を全て検索
        for elem in soup.find_all(text='2'):
            parent = elem.parent
            if parent:
                date_2_elements.append(parent)
        
        # テキストが '2' のtd/th要素を検索
        for elem in soup.find_all(['td', 'th'], text='2'):
            date_2_elements.append(elem)
        
        print(f"   発見された '2' 要素: {len(date_2_elements)}個")
        
        for i, elem in enumerate(date_2_elements):
            classes = elem.get('class', [])
            onclick = elem.get('onclick', '')
            parent = elem.parent.name if elem.parent else 'None'
            parent_classes = elem.parent.get('class', []) if elem.parent else []
            
            print(f"     {i+1}. <{elem.name} class='{' '.join(classes)}' onclick='{onclick}'>{elem.get_text(strip=True)}</{elem.name}>")
            print(f"        親: <{parent} class='{' '.join(parent_classes)}'>")
            
            # この要素が実際にクリック可能かテスト
            xpath_options = [
                f"//td[text()='2'][{i+1}]",
                f"//td[@class='{' '.join(classes)}'][text()='2']" if classes else None,
                f"//*[text()='2'][{i+1}]",
            ]
            
            for xpath in xpath_options:
                if xpath:
                    try:
                        selenium_elements = driver.find_elements(By.XPATH, xpath)
                        if selenium_elements:
                            print(f"        XPath成功: {xpath} ({len(selenium_elements)}個)")
                        else:
                            print(f"        XPath失敗: {xpath}")
                    except Exception as e:
                        print(f"        XPathエラー: {xpath} - {e}")
    
    except Exception as e:
        print(f"❌ カレンダー構造分析エラー: {e}")

def test_date_clicking_methods(driver):
    """様々な日付クリック方法をテスト"""
    print("\n🖱️ 日付クリック方法テスト")
    print("=" * 50)
    
    # テスト対象の日付
    test_date = '2'
    
    # 様々なXPathパターンをテスト
    xpath_patterns = [
        # 基本パターン
        f"//td[text()='{test_date}']",
        f"//th[text()='{test_date}']",
        f"//*[text()='{test_date}']",
        
        # クラス指定パターン
        f"//td[@class='CAL'][text()='{test_date}']",
        f"//td[@class='CALSAT'][text()='{test_date}']",
        f"//td[@class='CALSUN'][text()='{test_date}']",
        
        # 位置指定パターン
        f"(//td[text()='{test_date}'])[1]",
        f"(//td[text()='{test_date}'])[2]",
        f"(//td[text()='{test_date}'])[3]",
        
        # 親要素指定パターン
        f"//tr//td[text()='{test_date}']",
        f"//table//td[text()='{test_date}']",
        
        # JAM関連パターン
        f"//td[contains(@class, 'JAM')][text()='{test_date}']",
        f"//*[contains(@class, 'JAM') and text()='{test_date}']",
        
        # onclick属性パターン
        f"//td[@onclick][text()='{test_date}']",
        f"//*[@onclick and text()='{test_date}']",
    ]
    
    successful_patterns = []
    
    for i, xpath in enumerate(xpath_patterns):
        try:
            print(f"\n🔧 パターン{i+1}: {xpath}")
            elements = driver.find_elements(By.XPATH, xpath)
            
            if elements:
                print(f"   発見: {len(elements)}個の要素")
                
                for j, elem in enumerate(elements[:3]):  # 最初の3個をテスト
                    try:
                        tag = elem.tag_name
                        text = elem.text.strip()
                        classes = elem.get_attribute('class')
                        onclick = elem.get_attribute('onclick')
                        
                        print(f"     要素{j+1}: <{tag} class='{classes}' onclick='{onclick[:30]}...'>{text}</{tag}>")
                        
                        # クリックテスト
                        print(f"     クリック試行中...")
                        elem.click()
                        time.sleep(2)
                        
                        # クリック後のページ変化をチェック
                        current_url = driver.current_url
                        print(f"     クリック後URL: {current_url}")
                        
                        if 'realtime' in current_url or current_url != 'https://yosocal.com/':
                            print(f"   ✅ パターン成功: {xpath}")
                            successful_patterns.append(xpath)
                            
                            # 元のページに戻る
                            driver.get('https://yosocal.com/')
                            navigate_to_month(driver, 2024, 1)
                            time.sleep(3)
                            break
                        else:
                            print(f"   ❌ クリック効果なし")
                            
                    except Exception as e:
                        print(f"     クリックエラー: {e}")
            else:
                print(f"   要素なし")
                
        except Exception as e:
            print(f"   ❌ XPathエラー: {e}")
    
    print(f"\n📊 成功したXPathパターン:")
    for pattern in successful_patterns:
        print(f"   ✅ {pattern}")
    
    return successful_patterns

def main():
    """メイン過去月カレンダー調査プロセス"""
    print("🔍 yosocal.com 過去月カレンダー構造調査")
    print("📅 対象: 2024年1月")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # 2024年1月に移動
        print("📅 2024年1月に移動中...")
        success, result = navigate_to_month(driver, 2024, 1)
        
        if not success:
            print(f"❌ 2024年1月への移動失敗: {result}")
            return
        
        print(f"✅ {result} に移動完了")
        
        # カレンダー構造分析
        analyze_calendar_structure(driver)
        
        # 日付クリック方法テスト
        successful_patterns = test_date_clicking_methods(driver)
        
        if successful_patterns:
            print(f"\n✅ 過去月での日付クリック方法を発見！")
            print(f"推奨XPath: {successful_patterns[0]}")
        else:
            print(f"\n❌ 過去月での日付クリック方法が見つかりませんでした")
        
        print(f"\n✅ 過去月カレンダー調査完了")
        
    except Exception as e:
        print(f"❌ 調査でエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 