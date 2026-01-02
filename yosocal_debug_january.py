#!/usr/bin/env python3
"""
yosocal.com January Debug Script
1月到達時のページ構造を詳細分析
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    # options.add_argument('--headless')  # デバッグのためヘッドレス無効
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def navigate_to_january(driver):
    """1月に移動"""
    print("📅 2025年1月に移動中...")
    
    # サイトアクセス
    driver.get("https://yosocal.com/realtime.htm")
    time.sleep(3)
    
    # 1月まで移動
    max_attempts = 12
    
    for attempt in range(max_attempts):
        try:
            current_year = driver.execute_script("return zzDate ? zzDate.getFullYear() : null;")
            current_month = driver.execute_script("return zzDate ? zzDate.getMonth() + 1 : null;")
            
            print(f"  現在: {current_year}年{current_month}月")
            
            if current_year == 2025 and current_month == 1:
                print("✅ 2025年1月に到達")
                time.sleep(5)  # ページ更新待機
                return True
            
            # 前月ボタンをクリック
            prev_btn = driver.find_element(By.XPATH, "//input[@value='前月']")
            prev_btn.click()
            print("  ← 前月へ移動")
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ 月移動エラー: {e}")
            return False
    
    return False

def analyze_january_page(driver):
    """1月ページの詳細分析"""
    print("\n🔍 1月ページ分析開始")
    print("=" * 60)
    
    # 1. HTML保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_filename = f"january_debug_{timestamp}.html"
    
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"💾 HTML保存: {html_filename}")
    
    # 2. BeautifulSoupで解析
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # 3. テーブル分析
    analyze_tables(soup)
    
    # 4. createAT2要素分析
    analyze_createat2_elements(driver, soup)
    
    # 5. JavaScript変数分析
    analyze_javascript_variables(driver)
    
    # 6. 日付要素分析
    analyze_date_elements(soup)

def analyze_tables(soup):
    """テーブル分析"""
    print("\n📊 === テーブル分析 ===")
    
    tables = soup.find_all('table')
    print(f"📋 テーブル総数: {len(tables)}")
    
    # 各テーブルの詳細
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) >= 10:  # 10行以上のテーブルのみ
            print(f"\n  テーブル{i+1}: {len(rows)}行")
            
            # 最初の数行を確認
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                if cells:
                    cell_count = len(cells)
                    first_cell = cells[0].get_text(strip=True)[:20]
                    print(f"    行{j+1}: {cell_count}セル, 最初=\"{first_cell}\"")
                    
                    # セル数が多い行（アトラクション候補）
                    if cell_count > 30:
                        print(f"      🎢 アトラクション候補行: {cell_count}セル")
                        
                        # 既知のアトラクション名をチェック
                        cell_texts = [cell.get_text(strip=True) for cell in cells[:10]]
                        known_attractions = ['オムニバス', 'カリブ', 'スプラッシュ', 'スペース', 'プーさん']
                        found = [text for text in cell_texts if any(att in text for att in known_attractions)]
                        if found:
                            print(f"        発見アトラクション: {found}")

def analyze_createat2_elements(driver, soup):
    """createAT2要素分析"""
    print("\n🎢 === createAT2要素分析 ===")
    
    # 1. Seleniumで要素検索
    search_methods = [
        ("XPath onclick", "//td[@onclick]"),
        ("XPath createAT2", "//td[contains(@onclick, 'createAT2')]"),
        ("CSS onclick", "td[onclick]"),
        ("Class FPh2", "td.FPh2"),
        ("任意onclick", "//*[@onclick]")
    ]
    
    for method_name, selector in search_methods:
        try:
            if "XPath" in method_name or method_name == "任意onclick":
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            print(f"  {method_name}: {len(elements)}個")
            
            # 最初の数個を詳細確認
            for i, elem in enumerate(elements[:3]):
                onclick = elem.get_attribute('onclick')
                text = elem.text.strip()[:15]
                class_attr = elem.get_attribute('class')
                print(f"    要素{i+1}: onclick=\"{onclick}\", text=\"{text}\", class=\"{class_attr}\"")
                
        except Exception as e:
            print(f"  {method_name}: エラー - {e}")
    
    # 2. BeautifulSoupでonclick検索
    print("\n  BeautifulSoup分析:")
    onclick_elements = soup.find_all(attrs={"onclick": True})
    print(f"  onclick属性要素: {len(onclick_elements)}個")
    
    createat2_elements = soup.find_all(attrs={"onclick": re.compile(r"createAT2")})
    print(f"  createAT2要素: {len(createat2_elements)}個")
    
    if createat2_elements:
        print("  createAT2要素詳細:")
        for i, elem in enumerate(createat2_elements[:5]):
            onclick = elem.get('onclick')
            text = elem.get_text(strip=True)[:15]
            print(f"    {i+1}. onclick=\"{onclick}\", text=\"{text}\"")

def analyze_javascript_variables(driver):
    """JavaScript変数分析"""
    print("\n🔧 === JavaScript変数分析 ===")
    
    js_queries = [
        ("zzDate", "return zzDate ? zzDate.toString() : 'undefined';"),
        ("createAT2 function", "return typeof createAT2;"),
        ("document.readyState", "return document.readyState;"),
        ("Global variables", "return Object.keys(window).filter(k => k.includes('AT') || k.includes('Date')).slice(0, 10);")
    ]
    
    for query_name, js_code in js_queries:
        try:
            result = driver.execute_script(js_code)
            print(f"  {query_name}: {result}")
        except Exception as e:
            print(f"  {query_name}: エラー - {e}")

def analyze_date_elements(soup):
    """日付要素分析"""
    print("\n📅 === 日付要素分析 ===")
    
    # TDBT要素
    tdbt_elements = soup.find_all('td', class_='TDBT')
    print(f"  TDBT要素: {len(tdbt_elements)}個")
    
    for i, elem in enumerate(tdbt_elements[:5]):
        text = elem.get_text(strip=True)
        print(f"    {i+1}. \"{text}\"")
    
    # 日付パターン検索
    date_patterns = [
        r'(\d+)月(\d+)日',
        r'(\d{4})年(\d+)月(\d+)日',
        r'2025.*1.*'
    ]
    
    page_text = soup.get_text()
    
    for pattern in date_patterns:
        matches = re.findall(pattern, page_text)
        if matches:
            print(f"  パターン {pattern}: {len(matches)}件")
            for match in matches[:3]:
                print(f"    {match}")

def main():
    """メイン実行"""
    print("🔍 yosocal.com January Debug Analysis")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        # 1月に移動
        if navigate_to_january(driver):
            # 詳細分析
            analyze_january_page(driver)
        else:
            print("❌ 1月への移動に失敗")
            
    except Exception as e:
        print(f"❌ 分析エラー: {e}")
        
    finally:
        input("\n⏸️ Enterキーを押すとブラウザを閉じます...")
        driver.quit()

if __name__ == "__main__":
    main() 