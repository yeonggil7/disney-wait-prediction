# -*- coding: utf-8 -*-
"""
yosocal.com 利用可能データ確認システム
現在利用可能な日付とデータを調査
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

def check_main_page_structure(driver):
    """メインページの構造を確認"""
    print("\n🔍 メインページ構造確認")
    print("=" * 40)
    
    try:
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # ページサイズ
        page_source = driver.page_source
        print(f"📏 ページサイズ: {len(page_source):,} 文字")
        
        # カレンダー関連要素を検索
        print("\n📅 カレンダー関連要素:")
        calendar_elements = driver.find_elements(By.XPATH, "//td[contains(@class, 'MH')]")
        print(f"   MHクラスの要素: {len(calendar_elements)}")
        
        for i, elem in enumerate(calendar_elements[:5]):
            class_attr = elem.get_attribute('class')
            text = elem.text.strip()
            print(f"   要素 {i+1}: class='{class_attr}', text='{text}'")
        
        # cal IDを持つ要素を検索
        cal_elements = driver.find_elements(By.XPATH, "//td[contains(@id, 'cal')]")
        print(f"\n📋 cal IDの要素: {len(cal_elements)}")
        
        for i, elem in enumerate(cal_elements[:10]):
            id_attr = elem.get_attribute('id')
            text = elem.text.strip()
            onclick = elem.get_attribute('onclick')
            print(f"   要素 {i+1}: id='{id_attr}', text='{text}', onclick='{onclick[:50] if onclick else 'None'}...'")
        
        # 年月表示を検索
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        print(f"\n📆 年月表示要素: {len(month_elements)}")
        
        for i, elem in enumerate(month_elements[:3]):
            text = elem.text.strip()
            tag_name = elem.tag_name
            class_attr = elem.get_attribute('class')
            print(f"   要素 {i+1}: {tag_name}, class='{class_attr}', text='{text}'")
        
        # テーブル構造を確認
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\n📋 テーブル数: {len(tables)}")
        
        for i, table in enumerate(tables[:3]):
            rows = table.find_elements(By.TAG_NAME, "tr")
            cells = table.find_elements(By.TAG_NAME, "td")
            print(f"   テーブル {i+1}: {len(rows)}行, {len(cells)}セル")
        
    except Exception as e:
        print(f"❌ メインページ構造確認エラー: {e}")

def check_realtime_page_dates(driver):
    """realtime.htmページで利用可能な日付を確認"""
    print("\n🔍 realtime.htmページ日付確認")
    print("=" * 40)
    
    try:
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # ページサイズ
        page_source = driver.page_source
        print(f"📏 ページサイズ: {len(page_source):,} 文字")
        
        # BeautifulSoupで解析
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを確認
        jamat_div = soup.find('div', id='jamat')
        if jamat_div:
            print("✅ jamat divを発見")
            
            # テーブルを取得
            table = jamat_div.find('table')
            if table:
                print("✅ jamat内テーブルを発見")
                
                # 日付に関連する情報を検索
                all_text = jamat_div.get_text()
                
                # 日付パターンを検索
                date_patterns = re.findall(r'\d{1,2}月\d{1,2}日', all_text)
                if date_patterns:
                    unique_dates = list(set(date_patterns))
                    unique_dates.sort()
                    print(f"📅 発見された日付: {unique_dates}")
                else:
                    print("❌ 日付パターンが見つかりません")
                
                # 年の情報を検索
                year_patterns = re.findall(r'20\d{2}年', all_text)
                if year_patterns:
                    unique_years = list(set(year_patterns))
                    print(f"📅 発見された年: {unique_years}")
                
                # 現在のデータの日付を特定
                print("\n📊 データ分析:")
                rows = table.find_all('tr')
                
                # FPMクラス（時間）を含む行を検索
                fpm_rows = [row for row in rows if row.find('td', class_='FPM')]
                print(f"   時間データ行数: {len(fpm_rows)}")
                
                if fpm_rows:
                    first_time = fpm_rows[0].find('td', class_='FPM').get_text(strip=True)
                    last_time = fpm_rows[-1].find('td', class_='FPM').get_text(strip=True)
                    print(f"   時間範囲: {first_time} ～ {last_time}")
                
                # FPh2クラス（アトラクション名）を含む行を検索
                attraction_rows = [row for row in rows if row.find('td', class_='FPh2')]
                print(f"   アトラクション行数: {len(attraction_rows)}")
                
                if attraction_rows:
                    attractions = [cell.get_text(strip=True).replace('｜', '') 
                                 for cell in attraction_rows[0].find_all('td', class_='FPh2')]
                    print(f"   アトラクション数: {len(attractions)}")
                    print(f"   アトラクション例: {attractions[:5]}")
            else:
                print("❌ jamat内にテーブルが見つかりません")
        else:
            print("❌ jamat divが見つかりません")
        
        # カレンダー関連要素があるかチェック
        cal_elements = driver.find_elements(By.XPATH, "//td[contains(@id, 'cal')]")
        print(f"\n📋 realtime.htmページ内 cal要素: {len(cal_elements)}")
        
        # 日付選択可能な要素があるかチェック
        clickable_dates = driver.find_elements(By.XPATH, "//*[@onclick and contains(text(), '日')]")
        print(f"📋 クリック可能日付要素: {len(clickable_dates)}")
        
    except Exception as e:
        print(f"❌ realtime.htmページ確認エラー: {e}")

def check_alternative_calendar_access(driver):
    """代替カレンダーアクセス方法を確認"""
    print("\n🔍 代替カレンダーアクセス方法確認")
    print("=" * 40)
    
    try:
        # メインページに戻る
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # realtime.htmへのリンクを探す
        realtime_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'realtime')]")
        print(f"📋 realtime.htmリンク: {len(realtime_links)}")
        
        for i, link in enumerate(realtime_links[:3]):
            href = link.get_attribute('href')
            text = link.text.strip()
            print(f"   リンク {i+1}: href='{href}', text='{text}'")
        
        # 混雑予想カレンダーの他の形式を探す
        calendar_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'カレンダー') or contains(text(), '混雑')]")
        print(f"\n📋 カレンダー関連リンク: {len(calendar_links)}")
        
        for i, link in enumerate(calendar_links[:5]):
            href = link.get_attribute('href')
            text = link.text.strip()
            print(f"   リンク {i+1}: href='{href}', text='{text}'")
        
        # フォーム要素をチェック（日付選択フォームがあるかもしれない）
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"\n📋 フォーム数: {len(forms)}")
        
        for i, form in enumerate(forms[:3]):
            action = form.get_attribute('action')
            method = form.get_attribute('method')
            inputs = form.find_elements(By.TAG_NAME, "input")
            selects = form.find_elements(By.TAG_NAME, "select")
            print(f"   フォーム {i+1}: action='{action}', method='{method}', inputs={len(inputs)}, selects={len(selects)}")
        
    except Exception as e:
        print(f"❌ 代替アクセス方法確認エラー: {e}")

def main():
    """メイン確認プロセス"""
    print("🔍 yosocal.com 利用可能データ確認システム")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # メインページ構造確認
        check_main_page_structure(driver)
        
        # realtime.htmページ日付確認
        check_realtime_page_dates(driver)
        
        # 代替アクセス方法確認
        check_alternative_calendar_access(driver)
        
        print("\n✅ 利用可能データ確認完了")
        
    except Exception as e:
        print(f"❌ 確認プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 