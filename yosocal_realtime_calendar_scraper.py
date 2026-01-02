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

class YosocalRealtimeCalendarScraper:
    def __init__(self):
        self.driver = None
        self.all_data = []
        
    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（realtime.htmカレンダー版）をセットアップ中...")
        
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

    def navigate_to_realtime(self):
        """realtime.htmに直接移動"""
        try:
            print("📡 realtime.htm に直接移動中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(8)  # 十分な読み込み時間
            
            # 東京ディズニーランド選択確認
            try:
                land_radio = self.driver.find_element(By.ID, "park1")
                if not land_radio.is_selected():
                    land_radio.click()
                    time.sleep(2)
                print("✅ ディズニーランド選択確認")
            except:
                print("⚠️ パーク選択ボタンが見つかりません（既に選択済みの可能性）")
                
            print("✅ realtime.htm 移動完了")
            return True
        except Exception as e:
            print(f"❌ realtime.htm 移動失敗: {e}")
            return False

    def find_and_analyze_calendar(self):
        """カレンダー要素を分析して過去日付を特定"""
        try:
            print("📅 realtime.htmカレンダー分析中...")
            
            # カレンダー要素が読み込まれるまで待機
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "CAL"))
            )
            
            available_dates = []
            
            # cal1-cal31まで調査
            for i in range(1, 32):
                cal_id = f"cal{i}"
                try:
                    element = self.driver.find_element(By.ID, cal_id)
                    cal_div = element.find_element(By.CLASS_NAME, "CAL")
                    date_text = cal_div.text.strip()
                    
                    # onclick属性を取得
                    onclick_attr = element.get_attribute("onclick")
                    
                    print(f"✅ {cal_id}: 日付='{date_text}', onclick='{onclick_attr}'")
                    
                    # 数値の日付のみを候補とする
                    if date_text.isdigit():
                        day = int(date_text)
                        # 過去日付（今日より前）を特定
                        if day <= 2:  # 7月2日まで
                            available_dates.append({
                                'id': cal_id,
                                'day': day,
                                'element': element,
                                'onclick': onclick_attr,
                                'date_text': date_text
                            })
                    elif "/" in date_text:  # "7/1"形式
                        available_dates.append({
                            'id': cal_id,
                            'day': 1,
                            'element': element,
                            'onclick': onclick_attr,
                            'date_text': date_text
                        })
                        
                except Exception as e:
                    continue
            
            print(f"\n📊 過去日付候補: {len(available_dates)}個")
            for date_info in available_dates:
                print(f"  {date_info['id']}: 7月{date_info['day']}日 (onclick: {date_info['onclick']})")
            
            return available_dates
            
        except Exception as e:
            print(f"❌ カレンダー分析失敗: {e}")
            return []

    def click_date_and_extract_data(self, date_info):
        """指定された日付をクリックして28時間帯データを抽出"""
        try:
            cal_id = date_info['id']
            day = date_info['day']
            element = date_info['element']
            
            print(f"\n📅 7月{day}日 (ID: {cal_id}) クリック実行...")
            
            # JavaScriptでクリック実行
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(10)  # データ更新を十分待機
            
            print(f"✅ 7月{day}日クリック完了、データ抽出開始...")
            
            # ページが更新されたことを確認
            # jamat divの存在確認
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "jamat"))
                )
                print("✅ jamat div確認完了")
            except:
                print("⚠️ jamat div待機タイムアウト")
            
            # データ抽出
            return self.extract_28times_data(day)
            
        except Exception as e:
            print(f"❌ 7月{day}日データ抽出エラー: {e}")
            return 0

    def extract_28times_data(self, target_day):
        """28時間帯データを抽出"""
        try:
            print(f"🔍 7月{target_day}日 28時間帯データ抽出開始...")
            
            # ページソース取得
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # デバッグ用HTMLファイル保存
            debug_filename = f"yosocal_realtime_july{target_day}_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"📁 デバッグHTML保存: {debug_filename}")
            
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
                    # 時刻形式チェック
                    if re.match(r'^\d{2}:\d{2}$', time_text):
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
            else:
                print(f"🎉 完全な28時間帯達成！")
            
            # 日付抽出
            date_text = f"7月{target_day}日"
            
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
                            'data_source': 'yosocal_realtime_calendar'
                        }
                        self.all_data.append(record)
                        total_records += 1
            
            print(f"📊 7月{target_day}日抽出完了: {total_records}件 (有効: {valid_data}件)")
            
            # 28時間帯達成判定
            extracted_times = len(found_times)
            if extracted_times >= 20:
                print(f"🎉 大量時間帯取得成功: {extracted_times}時間帯")
                return total_records
            else:
                print(f"⚠️ 時間帯不足: {extracted_times}時間帯のみ")
                return total_records
            
        except Exception as e:
            print(f"❌ データ抽出エラー: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def save_to_csv(self, target_day):
        """CSVファイルに保存"""
        try:
            if not self.all_data:
                print("❌ 保存するデータがありません")
                return False
            
            # DataFrame作成
            df = pd.DataFrame(self.all_data)
            
            # 統計出力
            print(f"\n📊 7月{target_day}日データ収集結果")
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
            csv_filename = f"data/yosocal_2025_07_{target_day:02d}_realtime_calendar_data_{timestamp}.csv"
            
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 CSVファイル保存: {csv_filename}")
            
            # サンプルデータ表示
            print(f"\n📝 サンプルデータ（有効待ち時間）:")
            sample_data = df[df['wait_time'].notna()].head(10)
            for _, row in sample_data.iterrows():
                print(f"  {row['date']} {row['time']} {row['attraction']}: {row['wait_time']}分")
            
            return csv_filename
            
        except Exception as e:
            print(f"❌ CSV保存エラー: {e}")
            return False

    def cleanup(self):
        """WebDriver終了"""
        if self.driver:
            self.driver.quit()
            print("🔧 WebDriver終了")

    def collect_realtime_calendar_data(self):
        """realtime.htmカレンダー経由28時間帯データ収集メイン処理"""
        print("🚀 realtime.htmカレンダー経由28時間帯データ収集開始")
        print("="*60)
        
        try:
            # WebDriverセットアップ
            if not self.setup_driver():
                return False
            
            # realtime.htm直接移動
            if not self.navigate_to_realtime():
                return False
            
            # カレンダー分析
            available_dates = self.find_and_analyze_calendar()
            if not available_dates:
                print("❌ 過去日付が見つかりません")
                return False
            
            # 最も古い日付を選択（通常は7月1日または7月2日）
            target_date = min(available_dates, key=lambda x: x['day'])
            target_day = target_date['day']
            
            print(f"\n🎯 対象日決定: 7月{target_day}日")
            
            # 日付クリック & データ抽出
            total_records = self.click_date_and_extract_data(target_date)
            if total_records == 0:
                print("❌ データ抽出に失敗しました")
                return False
            
            # CSV保存
            csv_filename = self.save_to_csv(target_day)
            if not csv_filename:
                return False
            
            print(f"\n🎉 realtime.htmカレンダー経由データ収集完了！")
            print(f"📈 総データ数: {total_records}件")
            print(f"💾 保存ファイル: {csv_filename}")
            
            # 28時間帯達成確認
            unique_times = len(set([item['time'] for item in self.all_data if item['time'] != '平均']))
            if unique_times >= 20:
                print(f"✅ 大量時間帯達成: {unique_times}時間帯")
            else:
                print(f"⚠️ 時間帯不足: {unique_times}時間帯")
            
            return True
            
        except Exception as e:
            print(f"❌ データ収集エラー: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    scraper = YosocalRealtimeCalendarScraper()
    success = scraper.collect_realtime_calendar_data()
    
    if success:
        print("\n✅ realtime.htmカレンダー経由データ収集成功")
    else:
        print("\n❌ realtime.htmカレンダー経由データ収集失敗") 