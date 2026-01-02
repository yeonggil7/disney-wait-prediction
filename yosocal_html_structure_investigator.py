# -*- coding: utf-8 -*-
"""
yosocal.com 実際のHTMLテーブル構造詳細調査
時間帯データ配置解析版
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriver（HTML構造調査版）をセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        chrome_driver_path = ChromeDriverManager().install()
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ WebDriverセットアップ完了")
        return driver
        
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def investigate_detailed_structure():
    """詳細HTML構造調査"""
    print("🔍 yosocal.com realtime.htm 詳細HTML構造調査")
    print("=" * 70)
    
    driver = None
    
    try:
        driver = setup_driver()
        
        # realtime.htmに直接アクセス
        print("🌐 realtime.htmに移動中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamat div が見つかりません")
            return
        
        print("✅ jamat div 発見")
        
        # テーブルを探す
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブルが見つかりません")
            return
        
        print("✅ テーブル発見")
        
        # 全行を取得
        rows = table.find_all('tr')
        print(f"📊 総行数: {len(rows)}行")
        
        # 各行の詳細分析
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            print(f"\n📋 行 {i+1}: {len(cells)}セル")
            
            # 最初の10セルの内容を表示
            for j, cell in enumerate(cells[:15]):
                cell_text = cell.get_text(strip=True)
                css_classes = ' '.join(cell.get('class', []))
                rowspan = cell.get('rowspan', '1')
                colspan = cell.get('colspan', '1')
                
                print(f"   セル{j+1}: '{cell_text}' (class: {css_classes}, rowspan: {rowspan}, colspan: {colspan})")
            
            if len(cells) > 15:
                print(f"   ... 他 {len(cells)-15}セル")
        
        # 時間関連テキストの検索
        print(f"\n🕐 時間関連テキスト検索:")
        time_patterns = [
            r'\d{2}:\d{2}',  # 08:15形式
            r'\d{1,2}:\d{2}',  # 8:15形式
            r'平均'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, page_source)
            unique_matches = list(set(matches))
            print(f"   パターン '{pattern}': {len(unique_matches)}個 -> {unique_matches[:10]}")
        
        # FPMクラス要素の検索
        print(f"\n⏰ FPMクラス要素検索:")
        fpm_elements = soup.find_all(class_=re.compile(r'FPM'))
        print(f"   FPM要素数: {len(fpm_elements)}")
        
        if fpm_elements:
            print("   FPM要素サンプル:")
            for i, elem in enumerate(fpm_elements[:10]):
                print(f"   {i+1}. class: {elem.get('class')}, text: '{elem.get_text(strip=True)}'")
        
        # B0-B8クラス要素の検索
        print(f"\n🎯 B0-B8クラス要素検索:")
        for b_class in ['B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8']:
            b_elements = soup.find_all(class_=b_class)
            print(f"   {b_class}: {len(b_elements)}個")
            
            if b_elements and len(b_elements) <= 5:
                for elem in b_elements:
                    print(f"      text: '{elem.get_text(strip=True)}'")
        
        # テーブル構造の推測
        print(f"\n🔍 テーブル構造推測:")
        if len(rows) >= 4:
            # 1行目: 日付・タイトル行
            first_row = rows[0]
            first_cells = first_row.find_all(['td', 'th'])
            print(f"   1行目: {len(first_cells)}セル (タイトル行)")
            
            # 2行目: 時間帯行
            if len(rows) >= 2:
                time_row = rows[1]
                time_cells = time_row.find_all(['td', 'th'])
                print(f"   2行目: {len(time_cells)}セル (時間帯行)")
                print("   時間帯テキスト:")
                for j, cell in enumerate(time_cells[:20]):
                    cell_text = cell.get_text(strip=True)
                    if cell_text:
                        print(f"      セル{j+1}: '{cell_text}'")
            
            # 3行目: データ行
            if len(rows) >= 3:
                data_row = rows[2]
                data_cells = data_row.find_all(['td', 'th'])
                print(f"   3行目: {len(data_cells)}セル (データ行)")
                
            # 4行目: アトラクション行
            if len(rows) >= 4:
                attr_row = rows[3]
                attr_cells = attr_row.find_all(['td', 'th'])
                print(f"   4行目: {len(attr_cells)}セル (アトラクション行)")
                print("   アトラクション名:")
                for j, cell in enumerate(attr_cells[:10]):
                    cell_text = cell.get_text(strip=True)
                    if cell_text:
                        print(f"      セル{j+1}: '{cell_text}'")
        
        # デバッグ用HTMLファイル保存
        debug_file = "yosocal_html_structure_debug.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"\n💾 デバッグ用HTMLファイル保存: {debug_file}")
        
        print(f"\n⚡ HTML構造調査完了！")
        
    except Exception as e:
        print(f"❌ 調査エラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    investigate_detailed_structure() 