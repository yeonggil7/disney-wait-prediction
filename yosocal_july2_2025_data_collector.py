#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import os

class YosocalJuly2DataCollector:
    def __init__(self):
        self.driver = None
        self.all_data = []
        
    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（7月2日データ収集版）をセットアップ中...")
        
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            print("✅ WebDriverセットアップ完了")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップ失敗: {e}")
            return False

    def navigate_to_yosocal(self):
        """yosocal.comに移動"""
        try:
            print("📡 yosocal.com に移動中...")
            self.driver.get("https://yosocal.com/")
            time.sleep(3)
            
            # 東京ディズニーランド選択確認
            land_radio = self.driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(2)
                
            print("✅ yosocal.com 移動完了")
            return True
        except Exception as e:
            print(f"❌ yosocal.com 移動失敗: {e}")
            return False

    def click_july2_date(self):
        """7月2日をクリック"""
        try:
            print("📅 7月2日をクリック中...")
            
            # 7月2日の要素を探す（20250702のID）
            july2_element = self.driver.find_element(By.ID, "cal3")
            
            # JavaScriptでクリック
            self.driver.execute_script("arguments[0].click();", july2_element)
            time.sleep(5)  # データ読み込み待機
            
            print("✅ 7月2日クリック完了")
            return True
        except Exception as e:
            print(f"❌ 7月2日クリック失敗: {e}")
            return False

    def navigate_to_realtime(self):
        """realtime.htmに移動してデータ取得"""
        try:
            print("📊 realtime.htm でデータ取得中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(5)
            
            return True
        except Exception as e:
            print(f"❌ realtime.htm移動失敗: {e}")
            return False

    def extract_data_from_page(self):
        """ページからデータを抽出"""
        try:
            print("🔍 28時間帯データ抽出開始...")
            
            # ページソース取得
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # jamat div を検索
            jamat_div = soup.find('div', id='jamat')
            if not jamat_div:
                print("❌ jamat div が見つかりません")
                return 0
            
            # テーブル取得
            table = jamat_div.find('table')
            if not table:
                print("❌ jamat テーブルが見つかりません")
                return 0
            
            # 全行を取得
            rows = table.find_all('tr')
            print(f"📊 テーブル行数: {len(rows)}")
            
            # アトラクション名取得
            attractions = []
            for row in rows:
                fph2_cells = row.find_all('td', class_='FPh2')
                if fph2_cells:
                    for cell in fph2_cells:
                        attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                        attractions.append(attraction_name)
                    break
            
            print(f"🎯 アトラクション数: {len(attractions)}")
            
            # 時間データ行を検索
            time_data_rows = []
            for row in rows:
                fpm_cell = row.find('td', class_='FPM')
                fpt_cell = row.find('td', class_='FPT')
                
                if fpm_cell:
                    time_text = fpm_cell.get_text(strip=True)
                    if re.match(r'^\d{2}:\d{2}$', time_text):
                        time_data_rows.append((time_text, row))
                elif fpt_cell:
                    time_text = fpt_cell.get_text(strip=True)
                    if time_text == '平均':
                        time_data_rows.append((time_text, row))
            
            print(f"⏰ 検出時間帯数: {len(time_data_rows)}")
            
            # 日付抽出
            date_text = "7月2日"
            date_elements = table.find_all('td', class_='TDBT')
            for elem in date_elements:
                text = elem.get_text(strip=True)
                if '月' in text and '日' in text:
                    date_text = text
                    break
            
            print(f"📅 対象日付: {date_text}")
            
            # データ抽出
            total_records = 0
            valid_data = 0
            
            for time_slot, row in time_data_rows:
                data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
                
                for i, cell in enumerate(data_cells):
                    if i < len(attractions):
                        attraction = attractions[i]
                        cell_text = cell.get_text(strip=True)
                        css_classes = ' '.join(cell.get('class', []))
                        
                        # 待ち時間解析
                        wait_time = None
                        status = "unknown"
                        
                        if cell_text == "-" or cell_text == "":
                            status = "no_data"
                        elif re.match(r'^\d+$', cell_text):
                            wait_time = float(cell_text)
                            status = "normal"
                            valid_data += 1
                        else:
                            status = "other"
                        
                        # データ記録
                        record = {
                            'date': date_text,
                            'time': time_slot,
                            'attraction': attraction,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': css_classes,
                            'raw_value': cell_text,
                            'data_source': 'yosocal_realtime'
                        }
                        self.all_data.append(record)
                        total_records += 1
            
            print(f"📊 抽出完了: {total_records}件 (有効: {valid_data}件)")
            return total_records
            
        except Exception as e:
            print(f"❌ データ抽出エラー: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def save_to_csv(self):
        """CSVファイルに保存"""
        try:
            if not self.all_data:
                print("❌ 保存するデータがありません")
                return False
            
            # DataFrame作成
            df = pd.DataFrame(self.all_data)
            
            # 統計出力
            print("\n📊 収集結果サマリー")
            print("="*50)
            print(f"総レコード数: {len(df)}")
            print(f"時間帯数: {df['time'].nunique()}")
            print(f"アトラクション数: {df['attraction'].nunique()}")
            print(f"有効待ち時間データ: {df['wait_time'].notna().sum()}")
            
            # dataディレクトリに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"data/yosocal_2025_07_02_data_{timestamp}.csv"
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 CSVファイル保存: {csv_filename}")
            
            # サンプルデータ表示
            print(f"\n📝 サンプルデータ:")
            sample_data = df[df['wait_time'].notna()].head(10)
            for _, row in sample_data.iterrows():
                print(f"  {row['date']} {row['time']} {row['attraction']}: {row['wait_time']}分")
            
            return True
            
        except Exception as e:
            print(f"❌ CSV保存エラー: {e}")
            return False

    def cleanup(self):
        """WebDriver終了"""
        if self.driver:
            self.driver.quit()
            print("🔧 WebDriver終了")

    def collect_july2_data(self):
        """7月2日データ収集メイン処理"""
        print("🚀 2025年7月2日データ収集開始")
        print("="*60)
        
        try:
            # WebDriverセットアップ
            if not self.setup_driver():
                return False
            
            # yosocal.com移動
            if not self.navigate_to_yosocal():
                return False
            
            # 7月2日クリック
            if not self.click_july2_date():
                return False
            
            # realtime.htmでデータ取得
            if not self.navigate_to_realtime():
                return False
            
            # データ抽出
            total_records = self.extract_data_from_page()
            if total_records == 0:
                print("❌ データ抽出に失敗しました")
                return False
            
            # CSV保存
            if not self.save_to_csv():
                return False
            
            print(f"\n🎉 2025年7月2日データ収集完了！")
            print(f"📈 総データ数: {total_records}件")
            return True
            
        except Exception as e:
            print(f"❌ データ収集エラー: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    collector = YosocalJuly2DataCollector()
    success = collector.collect_july2_data()
    
    if success:
        print("\n✅ データ収集成功")
    else:
        print("\n❌ データ収集失敗") 