# -*- coding: utf-8 -*-
"""
yosocal.com テーブル構造詳細調査ツール
実際のjamatテーブルのHTML構造を分析
"""

import time
import os
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class YosocalTableStructureInvestigator:
    def __init__(self):
        self.driver = None

    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriverをセットアップ中...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(15)
            print("✅ WebDriverセットアップ完了")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def investigate_table_structure(self):
        """テーブル構造詳細調査"""
        try:
            print("🔍 yosocal.com/realtime.htm アクセス中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(3)
            
            # ページソース取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # jamatテーブル検索
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                print("❌ jamatテーブルが見つかりません")
                return
                
            table = jamat_div.find('table')
            if not table:
                print("❌ テーブルが見つかりません")
                return
            
            rows = table.find_all('tr')
            print(f"📊 テーブル分析結果:")
            print(f"   総行数: {len(rows)}行")
            
            # 各行の詳細分析
            for row_idx, row in enumerate(rows[:10]):  # 最初の10行のみ
                cells = row.find_all(['td', 'th'])
                print(f"\n🔍 行{row_idx}: {len(cells)}セル")
                
                # 各セルの詳細
                for cell_idx, cell in enumerate(cells[:15]):  # 最初の15セルのみ
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    if cell_text:
                        print(f"   セル{cell_idx}: '{cell_text}' (CSS: {css_classes})")
            
            # 特定行の完全分析
            print(f"\n🎯 ヘッダー行（行0）の完全分析:")
            if rows:
                header_row = rows[0]
                header_cells = header_row.find_all(['td', 'th'])
                print(f"   ヘッダーセル数: {len(header_cells)}個")
                
                for i, cell in enumerate(header_cells):
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    if cell_text:
                        print(f"   列{i}: '{cell_text}' (CSS: {css_classes})")
            
            # データ行サンプル分析
            print(f"\n🎯 データ行サンプル（行1-3）:")
            for row_idx in range(1, min(4, len(rows))):
                if row_idx < len(rows):
                    row = rows[row_idx]
                    cells = row.find_all(['td', 'th'])
                    print(f"   行{row_idx}: {len(cells)}セル")
                    
                    # 最初の15セルの内容
                    for cell_idx in range(min(15, len(cells))):
                        cell = cells[cell_idx]
                        cell_text = cell.get_text(strip=True)
                        css_classes = ' '.join(cell.get('class', []))
                        if cell_text:
                            print(f"      セル{cell_idx}: '{cell_text}' (CSS: {css_classes})")
            
            # HTML保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"yosocal_table_structure_debug_{timestamp}.html"
            
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(str(jamat_div))
            
            print(f"\n💾 HTML保存完了: {html_filename}")
            
            # 重要パターン検索
            print(f"\n🔍 重要要素検索:")
            
            # FPh2 (アトラクション名) 要素
            fph2_elements = soup.find_all(class_='FPh2')
            print(f"   FPh2要素: {len(fph2_elements)}個")
            for i, elem in enumerate(fph2_elements[:10]):
                print(f"      {i+1}. '{elem.get_text(strip=True)}'")
            
            # FPM (時間) 要素
            fpm_elements = soup.find_all(class_='FPM')
            print(f"   FPM要素: {len(fpm_elements)}個")
            for i, elem in enumerate(fpm_elements[:10]):
                print(f"      {i+1}. '{elem.get_text(strip=True)}'")
            
            # B要素 (待ち時間)
            b_elements = soup.find_all(class_=lambda x: x and x.startswith('B') and len(x) == 2 and x[1].isdigit())
            print(f"   B要素: {len(b_elements)}個")
            for i, elem in enumerate(b_elements[:10]):
                print(f"      {i+1}. '{elem.get_text(strip=True)}' (CSS: {' '.join(elem.get('class', []))})")
                
        except Exception as e:
            print(f"❌ テーブル構造調査エラー: {e}")

    def run_investigation(self):
        """調査実行"""
        print("🚀 yosocal.com テーブル構造詳細調査開始")
        print("=" * 70)
        
        if not self.setup_driver():
            return
        
        try:
            self.investigate_table_structure()
        finally:
            if self.driver:
                print("\n🔧 WebDriver終了")
                self.driver.quit()

def main():
    investigator = YosocalTableStructureInvestigator()
    investigator.run_investigation()

if __name__ == "__main__":
    main() 