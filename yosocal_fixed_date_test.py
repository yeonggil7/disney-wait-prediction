#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yosocal.com 修正版日付クリックテスト
過去の月でのdiv要素を使った正確な日付クリック方法
"""

import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import json

class YosocalDateSpecificScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（日付指定版）をセットアップ中...")
        
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # 自動化検出回避
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("✅ WebDriverセットアップ完了")
        
    def navigate_to_yosocal(self):
        """yosocal.comに移動"""
        try:
            print("📡 yosocal.com に移動中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(3)
            
            print("✅ yosocal.com 読み込み完了")
            return True
            
        except Exception as e:
            print(f"❌ yosocal.com 移動エラー: {str(e)}")
            return False
    
    def click_july_2nd(self):
        """7月2日をカレンダーでクリック"""
        try:
            print("📅 7月2日をカレンダーでクリック中...")
            
            # 7月2日の要素を探す（cal3）
            july_2nd_element = self.driver.find_element(By.ID, "cal3")
            
            print(f"🎯 7月2日要素発見: {july_2nd_element.get_attribute('outerHTML')[:100]}...")
            
            # JavaScriptでクリック実行
            self.driver.execute_script("arguments[0].click();", july_2nd_element)
            print("✅ 7月2日クリック実行")
            
            # ページ更新待機
            time.sleep(5)
            
            return True
            
        except Exception as e:
            print(f"❌ 7月2日クリックエラー: {str(e)}")
            return False
    
    def extract_complete_data(self):
        """完全な28時間帯データを抽出"""
        try:
            print("📊 28時間帯データ抽出開始...")
            
            # ページソース取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # デバッグ用HTML保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"yosocal_july2_fixed_{timestamp}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"💾 デバッグHTML保存: {debug_file}")
            
            # jamatテーブル検索
            jamat_div = soup.find('div', {'id': 'jamat'})
            if not jamat_div:
                print("❌ jamat divが見つかりません")
                return None
            
            # テーブル抽出
            table = jamat_div.find('table')
            if not table:
                print("❌ jamatテーブルが見つかりません")
                return None
            
            rows = table.find_all('tr')
            print(f"📋 テーブル行数: {len(rows)}")
            
            # データ抽出
            all_data = []
            time_slots = []
            attractions = []
            
            # ヘッダー行から時間帯抽出
            if len(rows) > 0:
                header_row = rows[0]
                time_cells = header_row.find_all('td', class_='FPM')
                for cell in time_cells:
                    time_text = cell.get_text(strip=True)
                    if time_text and time_text != '　':  # 空白でない時間帯のみ
                        time_slots.append(time_text)
                
                # 平均も追加
                avg_cell = header_row.find('td', class_='FPT')
                if avg_cell:
                    time_slots.append(avg_cell.get_text(strip=True))
            
            print(f"⏰ 検出時間帯数: {len(time_slots)}")
            print(f"🕐 時間帯: {time_slots}")
            
            # データ行処理
            for i, row in enumerate(rows[1:], 1):
                # アトラクション名
                attraction_cell = row.find('td', class_='FPh2')
                if not attraction_cell:
                    continue
                    
                attraction_name = attraction_cell.get_text(strip=True)
                attractions.append(attraction_name)
                
                # 待機時間データ
                wait_cells = row.find_all('td', class_=re.compile(r'B[0-8]'))
                
                for j, time_slot in enumerate(time_slots):
                    if j < len(wait_cells):
                        cell = wait_cells[j]
                        wait_time_text = cell.get_text(strip=True)
                        css_classes = cell.get('class', [])
                        
                        # データ解析
                        wait_time = None
                        status = 'no_data'
                        
                        if wait_time_text and wait_time_text != '-':
                            if wait_time_text.isdigit():
                                wait_time = float(wait_time_text)
                                status = 'normal'
                            elif '運休' in wait_time_text or '休止' in wait_time_text:
                                status = 'closed'
                        
                        record = {
                            'date': '7月02日',
                            'time': time_slot,
                            'attraction': attraction_name,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': ' '.join(css_classes),
                            'raw_value': wait_time_text,
                            'data_source': 'jamat div内'
                        }
                        all_data.append(record)
            
            print(f"🎯 アトラクション数: {len(set(attractions))}")
            print(f"📊 総データ数: {len(all_data)}")
            
            # CSV保存
            if all_data:
                df = pd.DataFrame(all_data)
                csv_file = f"yosocal_july2_complete_{timestamp}.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"💾 CSVファイル保存: {csv_file}")
                
                # 統計情報
                valid_data = df[df['status'] == 'normal']
                print(f"✅ 有効データ: {len(valid_data)}件")
                print(f"⏰ 時間帯数: {len(time_slots)}個")
                
                return df
            
            return None
            
        except Exception as e:
            print(f"❌ データ抽出エラー: {str(e)}")
            return None
    
    def run_july_2nd_extraction(self):
        """7月2日データ抽出メイン処理"""
        print("🚀 yosocal.com 7月2日データ抽出システム")
        print("="*60)
        
        try:
            # 1. WebDriverセットアップ
            self.setup_driver()
            
            # 2. yosocal.comに移動
            if not self.navigate_to_yosocal():
                return None
            
            # 3. 7月2日をクリック
            if not self.click_july_2nd():
                return None
            
            # 4. 完全データ抽出
            result = self.extract_complete_data()
            
            return result
            
        except Exception as e:
            print(f"❌ 処理エラー: {str(e)}")
            return None
        
        finally:
            if self.driver:
                print("🔧 WebDriver終了")
                self.driver.quit()

def main():
    """メイン実行"""
    scraper = YosocalDateSpecificScraper()
    result = scraper.run_july_2nd_extraction()
    
    if result is not None:
        print("🎉 7月2日データ抽出成功！")
        print(f"📊 最終結果: {len(result)}件")
        
        # 時間帯統計
        time_counts = result['time'].value_counts()
        print("⏰ 時間帯別データ数:")
        for time_slot, count in time_counts.items():
            print(f"   {time_slot}: {count}件")
            
    else:
        print("❌ データ抽出失敗")

if __name__ == "__main__":
    main() 