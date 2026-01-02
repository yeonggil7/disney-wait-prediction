#!/usr/bin/env python3
"""
yosocal.com カレンダー構造詳細調査
実際の日付クリック機能を特定
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import json

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    # options.add_argument('--headless')  # デバッグのため一時的にヘッドレス無効
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def investigate_calendar():
    """カレンダー構造の詳細調査"""
    print("🔍 yosocal.com カレンダー構造詳細調査")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        # サイトアクセス
        print("🌐 サイトアクセス中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(3)
        
        # ページ全体のHTMLを取得
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 1. カレンダーテーブルの特定
        print("\n📅 === カレンダーテーブル特定 ===")
        find_calendar_table(soup)
        
        # 2. 日付要素の詳細調査
        print("\n📊 === 日付要素詳細調査 ===")
        investigate_date_elements(driver, soup)
        
        # 3. JavaScript関数の詳細調査
        print("\n🔧 === JavaScript関数詳細調査 ===")
        investigate_javascript_functions(driver)
        
        # 4. 隠されたカレンダー要素の調査
        print("\n🔍 === 隠されたカレンダー要素調査 ===")
        investigate_hidden_elements(driver)
        
        # 5. iframe要素の調査
        print("\n🖼️ === iframe要素調査 ===")
        investigate_iframes(driver)
        
        # 6. 動的コンテンツの調査
        print("\n⚡ === 動的コンテンツ調査 ===")
        investigate_dynamic_content(driver)
        
        # 7. CSSセレクターでの日付検索
        print("\n🎨 === CSS セレクター日付検索 ===")
        investigate_css_selectors(driver)
        
        print("\n✅ カレンダー調査完了")
        
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        
    finally:
        driver.quit()

def find_calendar_table(soup):
    """カレンダーテーブルを特定"""
    
    tables = soup.find_all('table')
    print(f"📊 全テーブル数: {len(tables)}")
    
    # カレンダーらしき特徴を持つテーブルを探す
    calendar_candidates = []
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        
        # 7列（曜日）x 数行のテーブルを探す
        if len(rows) >= 4:  # ヘッダー + 最低3週分
            first_row = rows[0] if rows else None
            if first_row:
                cells = first_row.find_all(['td', 'th'])
                if len(cells) == 7:  # 7曜日
                    calendar_candidates.append((i, table, len(rows)))
                    print(f"  カレンダー候補{len(calendar_candidates)}: テーブル{i+1} ({len(rows)}行 x {len(cells)}列)")
    
    # カレンダー候補の詳細調査
    for idx, (table_num, table, row_count) in enumerate(calendar_candidates):
        print(f"\n📋 カレンダー候補{idx+1} 詳細調査:")
        
        rows = table.find_all('tr')
        
        # 最初の行（曜日ヘッダー）
        if rows:
            header_cells = rows[0].find_all(['td', 'th'])
            header_texts = [cell.get_text(strip=True) for cell in header_cells]
            print(f"  ヘッダー: {' | '.join(header_texts)}")
        
        # 日付らしきセルを探す
        date_cells = []
        for row in rows[1:]:  # ヘッダー以外
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                text = cell.get_text(strip=True)
                onclick = cell.get('onclick')
                classes = cell.get('class', [])
                
                # 数字のみ、または日付らしきテキスト
                if text.isdigit() or re.match(r'\d{1,2}[日]?', text):
                    date_cells.append({
                        'text': text,
                        'onclick': onclick,
                        'classes': classes
                    })
        
        print(f"  日付セル数: {len(date_cells)}")
        if date_cells:
            for j, cell_info in enumerate(date_cells[:5]):
                print(f"    日付{j+1}: '{cell_info['text']}' onclick='{cell_info['onclick']}' class='{cell_info['classes']}'")

def investigate_date_elements(driver, soup):
    """日付要素の詳細調査"""
    
    # 複数の方法で日付要素を探す
    search_strategies = [
        ("数字のみ", "//td[text() and string-length(text()) <= 2 and translate(text(), '0123456789', '') = '']"),
        ("日付+日", "//td[contains(text(), '日') and string-length(text()) <= 4]"),
        ("onclick属性", "//td[@onclick]"),
        ("data属性", "//td[@data-date or @data-day]"),
        ("クラス名", "//td[contains(@class, 'date') or contains(@class, 'day') or contains(@class, 'cal')]"),
        ("href属性", "//a[contains(@href, 'date') or contains(@href, 'day')]")
    ]
    
    for strategy_name, xpath in search_strategies:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            print(f"🔍 {strategy_name}: {len(elements)}個")
            
            for i, elem in enumerate(elements[:3]):
                text = elem.text.strip()
                onclick = elem.get_attribute('onclick')
                classes = elem.get_attribute('class')
                href = elem.get_attribute('href')
                
                attributes = []
                if onclick: attributes.append(f"onclick='{onclick[:50]}'")
                if classes: attributes.append(f"class='{classes}'")
                if href: attributes.append(f"href='{href}'")
                
                print(f"  要素{i+1}: '{text}' {' '.join(attributes)}")
                
        except Exception as e:
            print(f"❌ {strategy_name} 検索エラー: {e}")

def investigate_javascript_functions(driver):
    """JavaScript関数の詳細調査"""
    
    # JavaScriptから直接情報を取得
    js_queries = [
        ("zzDate変数", "return typeof zzDate !== 'undefined' ? zzDate.toString() : 'undefined';"),
        ("カレンダー関数", "return [typeof cal, typeof selectDate, typeof clickDate, typeof changeDate].join(',');"),
        ("グローバル変数", "return Object.keys(window).filter(k => k.includes('date') || k.includes('cal')).slice(0, 10);"),
        ("イベントリスナー", "return document.querySelector('td[onclick]') ? 'onclick要素あり' : 'onclick要素なし';")
    ]
    
    for query_name, js_code in js_queries:
        try:
            result = driver.execute_script(js_code)
            print(f"🔧 {query_name}: {result}")
        except Exception as e:
            print(f"❌ {query_name} クエリエラー: {e}")

def investigate_hidden_elements(driver):
    """隠されたカレンダー要素の調査"""
    
    # 非表示要素も含めて調査
    hidden_searches = [
        ("非表示onclick", "//td[@onclick and @style]"),
        ("非表示input", "//input[@type='hidden' and contains(@name, 'date')]"),
        ("非表示div", "//div[contains(@id, 'cal') or contains(@id, 'date')]"),
        ("data属性", "//*[@data-date or @data-day or @data-calendar]")
    ]
    
    for search_name, xpath in hidden_searches:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            print(f"🔍 {search_name}: {len(elements)}個")
            
            for i, elem in enumerate(elements[:2]):
                try:
                    text = elem.text.strip()
                    tag = elem.tag_name
                    style = elem.get_attribute('style')
                    data_attrs = []
                    
                    # data属性をチェック
                    for attr in ['data-date', 'data-day', 'data-calendar']:
                        value = elem.get_attribute(attr)
                        if value:
                            data_attrs.append(f"{attr}='{value}'")
                    
                    print(f"  要素{i+1}: <{tag}> '{text}' style='{style}' {' '.join(data_attrs)}")
                    
                except Exception as e:
                    print(f"  要素{i+1}: 詳細取得エラー - {e}")
                    
        except Exception as e:
            print(f"❌ {search_name} 検索エラー: {e}")

def investigate_iframes(driver):
    """iframe要素の調査"""
    
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"🖼️ iframe数: {len(iframes)}")
    
    for i, iframe in enumerate(iframes):
        src = iframe.get_attribute('src')
        name = iframe.get_attribute('name')
        id_attr = iframe.get_attribute('id')
        
        print(f"  iframe{i+1}: src='{src}' name='{name}' id='{id_attr}'")
        
        # iframe内に切り替えてカレンダーを探す
        try:
            driver.switch_to.frame(iframe)
            
            # iframe内でカレンダー要素を探す
            iframe_date_elements = driver.find_elements(By.XPATH, "//td[@onclick] | //a[contains(@href, 'date')]")
            print(f"    iframe内 クリック可能要素: {len(iframe_date_elements)}個")
            
            driver.switch_to.default_content()  # 元のフレームに戻る
            
        except Exception as e:
            print(f"    iframe調査エラー: {e}")
            driver.switch_to.default_content()

def investigate_dynamic_content(driver):
    """動的コンテンツの調査"""
    
    # ページロード後に動的に生成される要素を探す
    print("⏳ 動的コンテンツロード待機...")
    time.sleep(2)
    
    # スクロールしてコンテンツを表示
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 新しく表示された要素を調査
    new_clickable_elements = driver.find_elements(By.XPATH, "//td[@onclick] | //a[@onclick] | //button[@onclick]")
    print(f"⚡ 動的クリック可能要素: {len(new_clickable_elements)}個")
    
    # JavaScriptでカレンダー関連のイベントを発火
    try:
        result = driver.execute_script("""
            // カレンダー関連の関数を探す
            var calendarFunctions = [];
            for (var prop in window) {
                if (typeof window[prop] === 'function' && prop.toLowerCase().includes('cal')) {
                    calendarFunctions.push(prop);
                }
            }
            return calendarFunctions;
        """)
        print(f"⚡ カレンダー関連関数: {result}")
    except Exception as e:
        print(f"❌ 動的調査エラー: {e}")

def investigate_css_selectors(driver):
    """CSSセレクターでの日付検索"""
    
    css_selectors = [
        ("テーブルセル", "td"),
        ("クリック可能セル", "td[onclick]"),
        ("数字セル", "td:not(:empty)"),
        ("日付クラス", ".date, .day, .calendar"),
        ("カレンダーID", "#calendar, #cal, #date-picker")
    ]
    
    for selector_name, css_selector in css_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
            print(f"🎨 {selector_name} ('{css_selector}'): {len(elements)}個")
            
            # 数字のみのテキストを持つ要素を特別に調査
            if selector_name == "数字セル":
                numeric_elements = []
                for elem in elements:
                    text = elem.text.strip()
                    if text.isdigit() and 1 <= int(text) <= 31:
                        numeric_elements.append(elem)
                
                print(f"  数字(1-31)要素: {len(numeric_elements)}個")
                for i, elem in enumerate(numeric_elements[:5]):
                    text = elem.text.strip()
                    onclick = elem.get_attribute('onclick')
                    print(f"    数字{i+1}: '{text}' onclick='{onclick}'")
                    
        except Exception as e:
            print(f"❌ {selector_name} 検索エラー: {e}")

if __name__ == "__main__":
    investigate_calendar() 