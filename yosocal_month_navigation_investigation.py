# -*- coding: utf-8 -*-
"""
yosocal.com 月移動機能詳細調査
2024年1月から2025年6月までの長期間データ取得のための月移動システム
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

def analyze_month_navigation_elements(driver):
    """月移動要素を詳しく分析"""
    print("\n🔍 月移動要素詳細分析")
    print("=" * 50)
    
    try:
        # ページソースを取得してBeautifulSoupで解析
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 現在の年月を確認
        month_displays = soup.find_all(text=re.compile(r'2025年.*月'))
        print(f"📅 現在表示されている年月:")
        for display in month_displays:
            print(f"   {display.strip()}")
        
        # 様々な方法で月移動関連要素を探す
        search_patterns = [
            ("← や 前月", r'[←＜<前]'),
            ("→ や 次月", r'[→＞>次]'),
            ("年月パターン", r'(20\d{2})年\s*(\d{1,2})月'),
            ("リンク href", 'href'),
            ("onclick属性", 'onclick'),
            ("JavaScript呼び出し", r'javascript:'),
            ("フォーム", 'form'),
            ("input hidden", 'input type="hidden"'),
            ("select 年月", 'select')
        ]
        
        print(f"\n🔍 月移動関連要素検索:")
        
        # HTMLから月移動関連の要素を抽出
        for pattern_name, pattern in search_patterns:
            print(f"\n📋 {pattern_name}:")
            
            if pattern_name == "リンク href":
                links = soup.find_all('a', href=True)
                for link in links[:10]:  # 最初の10個まで
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if any(keyword in text for keyword in ['前', '次', '←', '→', '月']):
                        print(f"   <a href='{href}'>{text}</a>")
            
            elif pattern_name == "onclick属性":
                onclick_elements = soup.find_all(attrs={"onclick": True})
                for elem in onclick_elements[:10]:
                    onclick = elem.get('onclick')
                    text = elem.get_text(strip=True)
                    print(f"   <{elem.name} onclick='{onclick}'>{text}</{elem.name}>")
            
            elif pattern_name == "フォーム":
                forms = soup.find_all('form')
                for form in forms:
                    action = form.get('action', '')
                    method = form.get('method', '')
                    print(f"   <form action='{action}' method='{method}'>")
                    inputs = form.find_all('input')
                    for inp in inputs[:5]:
                        name = inp.get('name', '')
                        value = inp.get('value', '')
                        type_attr = inp.get('type', '')
                        print(f"     <input type='{type_attr}' name='{name}' value='{value}'>")
            
            elif pattern_name == "select 年月":
                selects = soup.find_all('select')
                for select in selects:
                    name = select.get('name', '')
                    print(f"   <select name='{name}'>")
                    options = select.find_all('option')
                    for option in options[:10]:
                        value = option.get('value', '')
                        text = option.get_text(strip=True)
                        print(f"     <option value='{value}'>{text}</option>")
            
            else:
                # テキストパターンで検索
                if re.search(pattern, page_source):
                    matches = re.finditer(pattern, page_source)
                    for i, match in enumerate(matches):
                        if i >= 5:  # 最初の5個まで
                            break
                        start = max(0, match.start() - 50)
                        end = min(len(page_source), match.end() + 50)
                        context = page_source[start:end].replace('\n', ' ')
                        print(f"   ...{context}...")
    
    except Exception as e:
        print(f"❌ 月移動要素分析エラー: {e}")

def test_navigation_buttons(driver):
    """実際のナビゲーションボタンをテスト"""
    print("\n🖱️ ナビゲーションボタンテスト")
    print("=" * 50)
    
    # 現在の月を記録
    initial_month = get_current_month(driver)
    print(f"📅 初期月: {initial_month}")
    
    # 様々なナビゲーション方法をテスト
    navigation_methods = [
        # 画像による月移動ボタン
        ("前月画像", "//img[contains(@src, 'prev') or contains(@src, 'left') or contains(@src, 'arrow')]"),
        ("次月画像", "//img[contains(@src, 'next') or contains(@src, 'right') or contains(@src, 'arrow')]"),
        
        # テキストによる月移動リンク
        ("前月テキスト", "//a[contains(text(), '前') or contains(text(), '←')]"),
        ("次月テキスト", "//a[contains(text(), '次') or contains(text(), '→')]"),
        
        # 特定のクラス名
        ("MHBT クラス (前)", "//td[@class='MHBT'][1]//a"),
        ("MHBT クラス (後)", "//td[@class='MHBT'][2]//a"),
        
        # JavaScript リンク
        ("JavaScript href", "//a[contains(@href, 'javascript:')]"),
        
        # フォーム送信
        ("フォーム送信", "//form//input[@type='submit']"),
        ("フォーム画像", "//form//input[@type='image']"),
    ]
    
    for method_name, xpath in navigation_methods:
        try:
            print(f"\n🔧 {method_name} テスト中...")
            elements = driver.find_elements(By.XPATH, xpath)
            
            if elements:
                print(f"   発見: {len(elements)}個の要素")
                
                for i, elem in enumerate(elements[:2]):  # 最初の2個をテスト
                    try:
                        # 要素の詳細を表示
                        tag = elem.tag_name
                        href = elem.get_attribute('href')
                        onclick = elem.get_attribute('onclick')
                        src = elem.get_attribute('src')
                        text = elem.text.strip()
                        
                        print(f"     要素{i+1}: <{tag}> href='{href}' onclick='{onclick}' src='{src}' text='{text}'")
                        
                        # クリックテスト
                        print(f"     クリック試行中...")
                        elem.click()
                        time.sleep(3)
                        
                        # 月が変わったかチェック
                        new_month = get_current_month(driver)
                        print(f"     結果: {initial_month} → {new_month}")
                        
                        if new_month != initial_month:
                            print(f"   ✅ {method_name} で月移動成功！")
                            return method_name, xpath
                        else:
                            print(f"   ❌ {method_name} では月移動せず")
                            
                    except Exception as e:
                        print(f"     クリックエラー: {e}")
            else:
                print(f"   要素なし")
                
        except Exception as e:
            print(f"   ❌ {method_name} 検索エラー: {e}")
    
    return None, None

def get_current_month(driver):
    """現在表示されている年月を取得"""
    try:
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            return month_elements[0].text.strip()
        return "不明"
    except:
        return "不明"

def test_direct_url_navigation(driver):
    """直接URLで過去の月にアクセスできるかテスト"""
    print("\n🌐 直接URL月移動テスト")
    print("=" * 50)
    
    # 様々なURL形式をテスト
    test_urls = [
        # 2024年12月 (6月の前月として近い月)
        ("2024年12月", "https://yosocal.com/?year=2024&month=12"),
        ("2024年12月", "https://yosocal.com/?date=2024-12"),
        ("2024年12月", "https://yosocal.com/index.php?y=2024&m=12"),
        
        # 2024年1月 (目標の開始月)
        ("2024年1月", "https://yosocal.com/?year=2024&month=1"),
        ("2024年1月", "https://yosocal.com/?date=2024-01"),
        ("2024年1月", "https://yosocal.com/index.php?y=2024&m=1"),
        
        # その他の形式
        ("カレンダー形式", "https://yosocal.com/calendar.php?year=2024&month=1"),
        ("cal形式", "https://yosocal.com/cal.php?y=2024&m=1"),
    ]
    
    for target_month, url in test_urls:
        try:
            print(f"\n🔗 {target_month} テスト: {url}")
            driver.get(url)
            time.sleep(3)
            
            current_month = get_current_month(driver)
            print(f"   結果: {current_month}")
            
            if "2024" in current_month and ("1月" in current_month or "12月" in current_month):
                print(f"   ✅ {target_month} アクセス成功！")
                return url
                
        except Exception as e:
            print(f"   ❌ {url} エラー: {e}")
    
    return None

def test_form_based_navigation(driver):
    """フォームベースの月移動をテスト"""
    print("\n📝 フォームベース月移動テスト")
    print("=" * 50)
    
    try:
        # メインページに戻る
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # フォーム要素を取得
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"📋 発見されたフォーム: {len(forms)}個")
        
        for i, form in enumerate(forms):
            try:
                action = form.get_attribute('action')
                method = form.get_attribute('method')
                print(f"\n📄 フォーム{i+1}: action='{action}' method='{method}'")
                
                # フォーム内の入力要素を取得
                inputs = form.find_elements(By.TAG_NAME, "input")
                selects = form.find_elements(By.TAG_NAME, "select")
                
                print(f"   入力要素: {len(inputs)}個, セレクト要素: {len(selects)}個")
                
                # セレクト要素（年月選択）をテスト
                for select in selects:
                    name = select.get_attribute('name')
                    print(f"   📋 セレクト '{name}':")
                    
                    options = select.find_elements(By.TAG_NAME, "option")
                    for option in options[:5]:  # 最初の5個を表示
                        value = option.get_attribute('value')
                        text = option.text
                        print(f"     - {text} (value: {value})")
                    
                    # 2024年のオプションがあるかチェック
                    if any("2024" in option.text for option in options):
                        print(f"   ✅ 2024年のオプションを発見！")
                        
                        # 2024年1月を選択してみる
                        for option in options:
                            if "2024" in option.text and "1" in option.text:
                                print(f"   🎯 2024年1月を選択中: {option.text}")
                                option.click()
                                time.sleep(2)
                                
                                # フォーム送信
                                submit_buttons = form.find_elements(By.XPATH, ".//input[@type='submit'] | .//button[@type='submit']")
                                if submit_buttons:
                                    print(f"   📤 フォーム送信中...")
                                    submit_buttons[0].click()
                                    time.sleep(3)
                                    
                                    current_month = get_current_month(driver)
                                    print(f"   結果: {current_month}")
                                    
                                    if "2024" in current_month and "1月" in current_month:
                                        print(f"   ✅ フォームで2024年1月アクセス成功！")
                                        return True
                                break
                
            except Exception as e:
                print(f"   ❌ フォーム{i+1} テストエラー: {e}")
    
    except Exception as e:
        print(f"❌ フォームベース月移動テストエラー: {e}")
    
    return False

def main():
    """メイン月移動調査プロセス"""
    print("🔍 yosocal.com 月移動機能詳細調査")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # メインページにアクセス
        print("🌐 yosocal.comメインページにアクセス中...")
        driver.get('https://yosocal.com/')
        time.sleep(5)
        
        # 月移動要素を分析
        analyze_month_navigation_elements(driver)
        
        # ナビゲーションボタンをテスト
        successful_method, xpath = test_navigation_buttons(driver)
        
        if successful_method:
            print(f"\n✅ 成功した月移動方法: {successful_method}")
            print(f"XPath: {xpath}")
        else:
            print(f"\n❌ ボタンクリックによる月移動は失敗")
        
        # 直接URLナビゲーションをテスト
        successful_url = test_direct_url_navigation(driver)
        
        if successful_url:
            print(f"\n✅ 成功した直接URL: {successful_url}")
        else:
            print(f"\n❌ 直接URLによる月移動は失敗")
        
        # フォームベースナビゲーションをテスト
        form_success = test_form_based_navigation(driver)
        
        if form_success:
            print(f"\n✅ フォームベース月移動成功")
        else:
            print(f"\n❌ フォームベース月移動失敗")
        
        print("\n📋 月移動調査結果まとめ:")
        print(f"   ボタンクリック: {'✅ 成功' if successful_method else '❌ 失敗'}")
        print(f"   直接URL: {'✅ 成功' if successful_url else '❌ 失敗'}")
        print(f"   フォーム: {'✅ 成功' if form_success else '❌ 失敗'}")
        
        print("\n✅ 月移動機能詳細調査完了")
        
    except Exception as e:
        print(f"❌ 調査プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 