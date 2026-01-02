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

class YosocalJuly1CompleteDataCollector:
    def __init__(self):
        self.driver = None
        self.all_data = []
        
    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（7月1日完全データ収集版）をセットアップ中...")
        
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
            time.sleep(5)  # 初期読み込み待機
            
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

    def find_and_click_july1(self):
        """7月1日を確実に見つけてクリック"""
        try:
            print("📅 7月1日要素を検索中...")
            
            # カレンダー要素が読み込まれるまで待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "CAL"))
            )
            
            # 7月1日の候補要素を検索
            july1_candidates = []
            
            # 方法1: ID検索（cal1, cal2など）
            for cal_id in ["cal1", "cal2", "cal3", "cal4", "cal5"]:
                try:
                    element = self.driver.find_element(By.ID, cal_id)
                    cal_text = element.find_element(By.CLASS_NAME, "CAL").text.strip()
                    if cal_text == "1":
                        july1_candidates.append((cal_id, element, "ID検索"))
                        print(f"✅ 7月1日候補発見: {cal_id} (テキスト: '{cal_text}')")
                except:
                    continue
            
            # 方法2: XPath検索
            try:
                xpath_elements = self.driver.find_elements(By.XPATH, "//div[@class='CAL' and text()='1']")
                for elem in xpath_elements:
                    parent = elem.find_element(By.XPATH, "..")
                    july1_candidates.append(("xpath", parent, "XPath検索"))
                    print(f"✅ 7月1日候補発見: XPath (要素ID: {parent.get_attribute('id')})")
            except:
                pass
            
            if not july1_candidates:
                print("❌ 7月1日要素が見つかりません")
                return False
            
            # 最初の候補をクリック
            cal_id, element, method = july1_candidates[0]
            print(f"📅 7月1日クリック実行: {cal_id} ({method})")
            
            # 複数の方法でクリックを試行
            click_methods = [
                ("通常クリック", lambda: element.click()),
                ("JavaScriptクリック", lambda: self.driver.execute_script("arguments[0].click();", element)),
                ("ActionChainsクリック", lambda: webdriver.ActionChains(self.driver).move_to_element(element).click().perform())
            ]
            
            clicked = False
            for method_name, click_func in click_methods:
                try:
                    print(f"🖱️ {method_name}を試行中...")
                    click_func()
                    time.sleep(3)
                    print(f"✅ {method_name}成功")
                    clicked = True
                    break
                except Exception as e:
                    print(f"❌ {method_name}失敗: {e}")
                    continue
            
            if not clicked:
                print("❌ 全てのクリック方法が失敗")
                return False
            
            # ページ変化を待機
            time.sleep(5)
            print("✅ 7月1日選択完了（ページ更新待機中）")
            return True
            
        except Exception as e:
            print(f"❌ 7月1日クリック失敗: {e}")
            return False

    def navigate_to_realtime_with_date(self):
        """日付選択後realtime.htmに移動してデータ取得"""
        try:
            print("📊 realtime.htm で7月1日データ取得中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(8)  # データ読み込み充分待機
            
            return True
        except Exception as e:
            print(f"❌ realtime.htm移動失敗: {e}")
            return False

    def extract_complete_28times_data(self):
        """完全な28時間帯データを抽出"""
        try:
            print("🔍 28時間帯完全データ抽出開始...")
            
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
            
            # アトラクション名取得（最初のFPh2行から）
            attractions = []
            for row in rows:
                fph2_cells = row.find_all('td', class_='FPh2')
                if fph2_cells:
                    for cell in fph2_cells:
                        attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                        if attraction_name:
                            attractions.append(attraction_name)
                    break
            
            print(f"🎯 アトラクション数: {len(attractions)}")
            
            # 時間データ行を検索（全てのFPM/FPT要素）
            time_data_rows = []
            for row in rows:
                fpm_cell = row.find('td', class_='FPM')
                fpt_cell = row.find('td', class_='FPT')
                
                if fpm_cell:
                    time_text = fpm_cell.get_text(strip=True)
                    # 時刻形式 OR 全角スペースを許可
                    if re.match(r'^\d{2}:\d{2}$', time_text) or time_text == '　':
                        if time_text != '　':  # 空白時間帯はスキップ
                            time_data_rows.append((time_text, row))
                elif fpt_cell:
                    time_text = fpt_cell.get_text(strip=True)
                    if time_text == '平均':
                        time_data_rows.append((time_text, row))
            
            print(f"⏰ 検出時間帯数: {len(time_data_rows)}")
            
            # 期待される28時間帯をチェック
            expected_times = [
                '08:15', '08:45', '09:15', '09:45', '10:15', '10:45', '11:15', '11:45',
                '12:15', '12:45', '13:15', '13:45', '14:15', '14:45', '15:15', '15:45',
                '16:15', '16:45', '17:15', '17:45', '18:15', '18:45', '19:15', '19:45',
                '20:15', '20:45', '21:15', '21:45'
            ]
            
            found_times = [time_slot for time_slot, _ in time_data_rows if time_slot != '平均']
            print(f"📋 期待時間帯: {len(expected_times)}個")
            print(f"📋 発見時間帯: {len(found_times)}個")
            print(f"📋 発見時間帯一覧: {found_times}")
            
            missing_times = set(expected_times) - set(found_times)
            if missing_times:
                print(f"⚠️ 未発見時間帯: {sorted(missing_times)}")
            
            # 日付抽出
            date_text = "7月1日"  # デフォルト
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
                        
                        if cell_text == "-" or cell_text == "" or cell_text == "　":
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
                            'data_source': 'yosocal_july1_complete'
                        }
                        self.all_data.append(record)
                        total_records += 1
            
            print(f"📊 抽出完了: {total_records}件 (有効: {valid_data}件)")
            
            # 28時間帯達成チェック
            extracted_times = len(found_times)
            if extracted_times >= 20:  # 20時間帯以上なら成功とみなす
                print(f"🎉 大量時間帯取得成功: {extracted_times}時間帯")
            else:
                print(f"⚠️ 時間帯不足: {extracted_times}時間帯のみ")
            
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
            
            # 時間帯別統計
            time_stats = df['time'].value_counts().sort_index()
            print(f"\n⏰ 時間帯別データ数:")
            for time_slot, count in time_stats.items():
                print(f"  {time_slot}: {count}件")
            
            # dataディレクトリに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"data/yosocal_2025_07_01_complete_data_{timestamp}.csv"
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 CSVファイル保存: {csv_filename}")
            
            # サンプルデータ表示
            print(f"\n📝 サンプルデータ（有効待ち時間）:")
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

    def collect_july1_complete_data(self):
        """7月1日完全28時間帯データ収集メイン処理"""
        print("🚀 2025年7月1日完全28時間帯データ収集開始")
        print("="*60)
        
        try:
            # WebDriverセットアップ
            if not self.setup_driver():
                return False
            
            # yosocal.com移動
            if not self.navigate_to_yosocal():
                return False
            
            # 7月1日確実クリック
            if not self.find_and_click_july1():
                return False
            
            # realtime.htmで完全データ取得
            if not self.navigate_to_realtime_with_date():
                return False
            
            # 完全28時間帯データ抽出
            total_records = self.extract_complete_28times_data()
            if total_records == 0:
                print("❌ データ抽出に失敗しました")
                return False
            
            # CSV保存
            if not self.save_to_csv():
                return False
            
            print(f"\n🎉 2025年7月1日完全データ収集完了！")
            print(f"📈 総データ数: {total_records}件")
            
            # 28時間帯達成確認
            if len(set([item['time'] for item in self.all_data if item['time'] != '平均'])) >= 20:
                print(f"✅ 28時間帯達成目標: 大幅達成！")
            else:
                print(f"⚠️ 28時間帯達成目標: 未達成")
            
            return True
            
        except Exception as e:
            print(f"❌ データ収集エラー: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    collector = YosocalJuly1CompleteDataCollector()
    success = collector.collect_july1_complete_data()
    
    if success:
        print("\n✅ 7月1日完全データ収集成功")
    else:
        print("\n❌ 7月1日完全データ収集失敗") 