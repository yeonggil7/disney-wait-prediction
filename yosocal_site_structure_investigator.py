#!/usr/bin/env python3
"""
yosocal.com/realtime.htm サイト構造調査ツール
カレンダー操作とテーブル構造を詳しく分析
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
from datetime import datetime

def setup_driver():
    """Chrome WebDriverの設定"""
    options = Options()
    options.add_argument('--headless')  # ヘッドレスモード
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

def investigate_site_structure():
    """サイト構造の詳細調査"""
    
    print("🔍 yosocal.com サイト構造調査開始")
    print("=" * 70)
    
    driver = setup_driver()
    
    try:
        # サイトにアクセス
        url = "https://yosocal.com/realtime.htm"
        print(f"🌐 アクセス中: {url}")
        driver.get(url)
        
        # ページロード待機
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        print(f"✅ ページロード完了")
        print(f"📋 ページタイトル: {driver.title}")
        
        # 1. カレンダー要素の調査
        print("\n📅 === カレンダー要素調査 ===")
        investigate_calendar_elements(driver)
        
        # 2. テーブル構造の調査
        print("\n📊 === テーブル構造調査 ===")
        investigate_table_structure(driver)
        
        # 3. JavaScript関数の調査
        print("\n🔧 === JavaScript関数調査 ===")
        investigate_javascript_functions(driver)
        
        # 4. フォーム・入力要素の調査
        print("\n📝 === フォーム要素調査 ===")
        investigate_form_elements(driver)
        
        # 5. 実際のカレンダー操作テスト
        print("\n🎯 === カレンダー操作テスト ===")
        test_calendar_interaction(driver)
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_page_source(driver, f"yosocal_investigation_{timestamp}.html")
        
        print("\n✅ サイト構造調査完了")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        
    finally:
        driver.quit()

def investigate_calendar_elements(driver):
    """カレンダー関連要素の調査"""
    
    # 前月・次月ボタン
    month_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '前月') or contains(text(), '次月')]")
    print(f"🗓️ 月移動ボタン: {len(month_buttons)}個")
    
    for i, btn in enumerate(month_buttons):
        print(f"  ボタン{i+1}: '{btn.text}' (tag: {btn.tag_name})")
        if btn.get_attribute('onclick'):
            print(f"    onclick: {btn.get_attribute('onclick')}")
    
    # 日付要素の検索
    date_elements = driver.find_elements(By.XPATH, "//td[contains(@onclick, 'cal') or contains(@onclick, 'date')]")
    print(f"📅 日付クリック要素: {len(date_elements)}個")
    
    if date_elements:
        for i, elem in enumerate(date_elements[:5]):  # 最初の5個
            print(f"  日付{i+1}: '{elem.text}' onclick: {elem.get_attribute('onclick')}")
    
    # カレンダーテーブルの検索
    calendar_tables = driver.find_elements(By.XPATH, "//table[.//td[contains(@onclick, 'cal')]]")
    print(f"📊 カレンダーテーブル: {len(calendar_tables)}個")

def investigate_table_structure(driver):
    """テーブル構造の詳細調査"""
    
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"📊 全テーブル数: {len(tables)}個")
    
    for i, table in enumerate(tables):
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        if len(rows) > 5:  # 大きなテーブルのみ詳細調査
            print(f"\n  📋 テーブル{i+1}: {len(rows)}行")
            
            # 最初の行の列数確認
            if rows:
                first_row_cells = rows[0].find_elements(By.XPATH, ".//td | .//th")
                print(f"    最初の行: {len(first_row_cells)}列")
                
                # セルの内容サンプル
                sample_texts = []
                for cell in first_row_cells[:10]:  # 最初の10列
                    text = cell.text.strip()
                    if text:
                        sample_texts.append(text[:15])
                
                if sample_texts:
                    print(f"    内容サンプル: {' | '.join(sample_texts)}")
            
            # アトラクション名らしきものを検索
            attraction_cells = table.find_elements(By.XPATH, ".//td[contains(text(), 'オムニバス') or contains(text(), 'カリブ') or contains(text(), 'スペース')]")
            if attraction_cells:
                print(f"    アトラクション要素: {len(attraction_cells)}個")

def investigate_javascript_functions(driver):
    """JavaScript関数の調査"""
    
    # cal関数の存在確認
    cal_function_exists = driver.execute_script("return typeof cal === 'function';")
    print(f"🔧 cal()関数: {'存在' if cal_function_exists else '不存在'}")
    
    # その他のカレンダー関連関数
    js_functions = ['setDate', 'changeMonth', 'loadData', 'showData']
    for func in js_functions:
        exists = driver.execute_script(f"return typeof {func} === 'function';")
        print(f"🔧 {func}()関数: {'存在' if exists else '不存在'}")
    
    # グローバル変数の確認
    js_vars = ['currentDate', 'currentMonth', 'selectedDate']
    for var in js_vars:
        try:
            value = driver.execute_script(f"return typeof {var} !== 'undefined' ? {var} : 'undefined';")
            print(f"📊 {var}: {value}")
        except:
            print(f"📊 {var}: 取得失敗")

def investigate_form_elements(driver):
    """フォーム・入力要素の調査"""
    
    forms = driver.find_elements(By.TAG_NAME, "form")
    inputs = driver.find_elements(By.TAG_NAME, "input")
    selects = driver.find_elements(By.TAG_NAME, "select")
    
    print(f"📝 フォーム: {len(forms)}個")
    print(f"📝 入力フィールド: {len(inputs)}個") 
    print(f"📝 セレクトボックス: {len(selects)}個")
    
    # 入力フィールドの詳細
    for i, inp in enumerate(inputs):
        input_type = inp.get_attribute('type')
        input_name = inp.get_attribute('name')
        input_value = inp.get_attribute('value')
        print(f"  入力{i+1}: type={input_type}, name={input_name}, value={input_value}")

def test_calendar_interaction(driver):
    """実際のカレンダー操作テスト"""
    
    try:
        # 日付要素を探す
        date_elements = driver.find_elements(By.XPATH, "//td[@onclick]")
        
        if date_elements:
            print(f"🎯 クリック可能な日付: {len(date_elements)}個")
            
            # 最初の日付をクリックしてみる
            first_date = date_elements[0]
            date_text = first_date.text.strip()
            onclick_attr = first_date.get_attribute('onclick')
            
            print(f"🔍 テスト対象: '{date_text}' (onclick: {onclick_attr})")
            
            # クリック前のページ状態保存
            before_html = driver.page_source
            
            # 日付クリック
            driver.execute_script("arguments[0].click();", first_date)
            time.sleep(2)  # データロード待機
            
            # クリック後の変化確認
            after_html = driver.page_source
            
            if before_html != after_html:
                print("✅ 日付クリックでページ内容が変化")
                
                # 新しく表示されたテーブルの調査
                new_tables = driver.find_elements(By.TAG_NAME, "table")
                for i, table in enumerate(new_tables):
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) == 28:  # 28時間帯のテーブル
                        print(f"🎯 待ち時間テーブル発見: テーブル{i+1} ({len(rows)}行)")
                        
                        # 列数確認
                        if rows:
                            cells = rows[0].find_elements(By.XPATH, ".//td | .//th")
                            print(f"    列数: {len(cells)}")
                            
                            # アトラクション名の確認
                            for j, row in enumerate(rows[1:6]):  # 最初の5行
                                row_cells = row.find_elements(By.XPATH, ".//td | .//th")
                                if len(row_cells) > 1:
                                    print(f"    行{j+1}: {row_cells[0].text} | {row_cells[1].text[:20]}...")
            else:
                print("❌ 日付クリックでページ変化なし")
                
        else:
            print("❌ クリック可能な日付要素が見つかりません")
            
    except Exception as e:
        print(f"❌ カレンダー操作テストエラー: {e}")

def save_page_source(driver, filename):
    """ページソースの保存"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"💾 ページソース保存: {filename}")
    except Exception as e:
        print(f"❌ ページソース保存エラー: {e}")

if __name__ == "__main__":
    investigate_site_structure() 