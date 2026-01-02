#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta, date
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
import json

class YosocalPastDataScraper:
    def __init__(self):
        self.driver = None
        self.target_times = self.generate_28_times()
        
    def generate_28_times(self):
        """28個の時間帯を生成（8:15-21:45 + 平均）"""
        times = []
        hour = 8
        minute = 15
        
        # 8:15から21:45まで30分間隔
        while hour < 22 or (hour == 21 and minute <= 45):
            times.append(f"{hour:02d}:{minute:02d}")
            minute += 30
            if minute >= 60:
                minute -= 60
                hour += 1
        
        # 平均も追加
        times.append("平均")
        
        print(f"🎯 目標時間帯数: {len(times)}個")
        print(f"   範囲: {times[0]} - {times[-2]} + {times[-1]}")
        
        return times

    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（28時間帯取得版）をセットアップ中...")
        
        options = Options()
        # 実際のブラウザ動作に近づける
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 広告ブロック設定
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values": {
                "ads": 2,
                "popups": 2,
                "notifications": 2
            }
        })
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            print("✅ WebDriverセットアップ完了")
            return True
        except Exception as e:
            print(f"❌ WebDriverセットアップエラー: {e}")
            return False

    def get_current_calendar_date(self):
        """現在表示されているカレンダーの年月を取得"""
        try:
            # 年月表示を探す（複数パターン）
            year_month_selectors = [
                "//table//td[contains(text(), '年') and contains(text(), '月')]",
                "//div[contains(text(), '年') and contains(text(), '月')]",
                "//span[contains(text(), '年') and contains(text(), '月')]"
            ]
            
            for selector in year_month_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # "2025年7月" パターンをパース
                        match = re.search(r'(\d{4})年(\d{1,2})月', text)
                        if match:
                            year = int(match.group(1))
                            month = int(match.group(2))
                            print(f"   📅 現在のカレンダー: {year}年{month}月")
                            return year, month
                except:
                    continue
            
            # フォールバック: 現在日時を使用
            now = datetime.now()
            print(f"   ⚠️ カレンダー年月検出失敗、現在時刻を使用: {now.year}年{now.month}月")
            return now.year, now.month
            
        except Exception as e:
            print(f"   ❌ カレンダー年月取得エラー: {e}")
            now = datetime.now()
            return now.year, now.month

    def navigate_to_date(self, target_date):
        """指定日付にナビゲート（yosocal_real_scraping_system.pyのロジック参考）"""
        try:
            print(f"📅 {target_date.strftime('%Y年%m月%d日')} に移動中...")
            
            # メインページアクセス
            self.driver.get("https://yosocal.com/")
            time.sleep(3)
            
            target_year = target_date.year
            target_month = target_date.month
            
            # 現在表示されている年月を取得
            current_year, current_month = self.get_current_calendar_date()
            
            # 目標年月まで移動
            max_attempts = 24  # 最大2年分
            attempts = 0
            
            while (current_year, current_month) != (target_year, target_month) and attempts < max_attempts:
                if (target_year, target_month) > (current_year, current_month):
                    # 次月ボタン
                    try:
                        next_selectors = [
                            "//input[@value='次月' or @value='次の月' or contains(@onclick, 'next')]",
                            "//button[contains(text(), '次') or contains(text(), '→')]",
                            "//a[contains(@onclick, 'next') or contains(@href, 'next')]"
                        ]
                        
                        clicked = False
                        for selector in next_selectors:
                            try:
                                next_btn = self.driver.find_element(By.XPATH, selector)
                                self.driver.execute_script("arguments[0].click();", next_btn)
                                clicked = True
                                break
                            except:
                                continue
                        
                        if not clicked:
                            print(f"   ❌ 次月ボタンが見つかりません")
                            break
                            
                    except Exception as e:
                        print(f"   ❌ 次月ボタンクリックエラー: {e}")
                        break
                else:
                    # 前月ボタン
                    try:
                        prev_selectors = [
                            "//input[@value='前月' or @value='前の月' or contains(@onclick, 'prev')]",
                            "//button[contains(text(), '前') or contains(text(), '←')]",
                            "//a[contains(@onclick, 'prev') or contains(@href, 'prev')]"
                        ]
                        
                        clicked = False
                        for selector in prev_selectors:
                            try:
                                prev_btn = self.driver.find_element(By.XPATH, selector)
                                self.driver.execute_script("arguments[0].click();", prev_btn)
                                clicked = True
                                break
                            except:
                                continue
                        
                        if not clicked:
                            print(f"   ❌ 前月ボタンが見つかりません")
                            break
                            
                    except Exception as e:
                        print(f"   ❌ 前月ボタンクリックエラー: {e}")
                        break
                
                time.sleep(2)
                current_year, current_month = self.get_current_calendar_date()
                attempts += 1
                print(f"   🔄 移動試行 {attempts}/{max_attempts}: {current_year}年{current_month}月")
            
            if attempts >= max_attempts:
                print(f"   ❌ 目標年月への移動に失敗")
                return False
            
            # 指定日をクリック
            day_str = str(target_date.day)
            print(f"   📍 {day_str}日をクリック中...")
            
            # 複数の日付要素パターンを試行
            day_selectors = [
                f"//div[contains(@class, 'CAL') and text()='{day_str}']",
                f"//td[contains(@class, 'cal') and text()='{day_str}']",
                f"//span[contains(@class, 'day') and text()='{day_str}']",
                f"//a[text()='{day_str}']",
                f"//*[contains(@class, 'date') and text()='{day_str}']"
            ]
            
            clicked = False
            for selector in day_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.text.strip() == day_str and element.is_displayed():
                            try:
                                # 要素が見える位置にスクロール
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(1)
                                
                                # 広告などが被っている場合のため、JavaScriptでクリック
                                self.driver.execute_script("arguments[0].click();", element)
                                print(f"   ✅ {day_str}日をクリック成功")
                                clicked = True
                                break
                            except Exception as click_error:
                                print(f"   ⚠️ クリック失敗: {click_error}")
                                continue
                    
                    if clicked:
                        break
                        
                except Exception as e:
                    continue
            
            if not clicked:
                print(f"   ❌ 日付 {day_str} のクリックに失敗")
                
                # デバッグ: 利用可能な日付要素を表示
                try:
                    all_date_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'CAL')] | //td[contains(@class, 'cal')]")
                    print(f"   📋 利用可能な日付要素: {len(all_date_elements)}個")
                    for i, elem in enumerate(all_date_elements[:10]):
                        try:
                            print(f"     {i+1}: '{elem.text}' (class='{elem.get_attribute('class')}')")
                        except:
                            print(f"     {i+1}: (テキスト取得失敗)")
                except:
                    pass
                
                return False
            
            # 日付クリック後の待機
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ 日付ナビゲーションエラー: {e}")
            return False

    def extract_28_times_data(self, target_date):
        """28時間帯データを抽出（yosocal_real_scraping_system.pyのロジック参考）"""
        try:
            # realtime.htmに移動
            print(f"🔄 realtime.htmページに移動中...")
            self.driver.get("https://yosocal.com/realtime.htm")
            time.sleep(5)
            
            # ページソース取得
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # デバッグ用HTMLファイル保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"yosocal_28times_{target_date.strftime('%Y%m%d')}_{timestamp}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"🔍 デバッグファイル保存: {debug_file}")
            
            # jamat div要素を探す
            jamat_div = soup.find('div', {'id': 'jamat'})
            if not jamat_div:
                print("❌ jamat div要素が見つかりません")
                return []
            
            print("✅ jamat div要素を発見")
            
            # テーブル解析
            table = jamat_div.find('table')
            if not table:
                print("❌ jamat内にテーブルが見つかりません")
                return []
            
            rows = table.find_all('tr')
            print(f"📋 テーブル行数: {len(rows)}")
            
            # 時間帯とアトラクション名の抽出
            time_slots = []
            attraction_names = []
            data_rows = []
            
            # アトラクション名行（FPh2クラス）を探す
            for i, row in enumerate(rows):
                fph2_cells = row.find_all('td', class_='FPh2')
                if fph2_cells and not attraction_names:
                    attraction_names = [cell.get_text().strip() for cell in fph2_cells]
                    print(f"🎯 アトラクション名行発見 (行{i}): {len(attraction_names)}個")
                    for j, name in enumerate(attraction_names[:10]):
                        print(f"   {j+1:2d}. {name}")
                    if len(attraction_names) > 10:
                        print(f"   ... 他{len(attraction_names)-10}個")
            
            # 時間データ（FPMクラス）を含む行を探す
            for i, row in enumerate(rows):
                fpm_cell = row.find('td', class_='FPM')
                if fpm_cell:
                    time_text = fpm_cell.get_text().strip()
                    if time_text and time_text not in ['　', '']:
                        time_slots.append(time_text)
                        data_rows.append(row)
                        print(f"⏰ 行{i}: 時間データ「{time_text}」")
            
            print(f"\n📊 {target_date.strftime('%Y年%m月%d日')} データ分析結果:")
            print(f"   ⏰ 時間帯数: {len(time_slots)}")
            print(f"   🎯 アトラクション数: {len(attraction_names)}")
            print(f"   📋 データ行数: {len(data_rows)}")
            
            # 28時間帯達成チェック
            print(f"\n🎯 28時間帯達成チェック:")
            print(f"   期待値: {len(self.target_times)}個")
            print(f"   実際値: {len(time_slots)}個")
            
            if len(time_slots) >= 28:
                print("   ✅ 28時間帯達成！")
            else:
                print(f"   ❌ 不足: {28 - len(time_slots)}個")
            
            # 時間帯詳細表示
            if time_slots:
                print(f"\n⏰ 検出された時間帯:")
                for i, slot in enumerate(time_slots):
                    print(f"   {i+1:2d}. {slot}")
            
            # データ構造化
            extracted_data = []
            for time_slot in time_slots:
                for attraction in attraction_names:
                    extracted_data.append({
                        'date': target_date.strftime("%m月%d日"),
                        'year': target_date.year,
                        'month': target_date.month,
                        'day': target_date.day,
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': None,  # 実際の待ち時間は追加処理で取得
                        'status': 'structure_detected',
                        'data_source': '28times_scraper'
                    })
            
            # 分析結果をJSONで保存
            analysis_data = {
                'analysis_date': timestamp,
                'target_date': target_date.strftime('%Y年%m月%d日'),
                'time_slots_count': len(time_slots),
                'time_slots': time_slots,
                'attraction_count': len(attraction_names),
                'attraction_names': attraction_names[:10],  # 最初の10個のみ保存
                'target_achieved': len(time_slots) >= 28,
                'debug_file': debug_file
            }
            
            json_file = f"yosocal_28times_analysis_{target_date.strftime('%Y%m%d')}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 分析結果保存: {json_file}")
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ データ抽出エラー: {e}")
            import traceback
            traceback.print_exc()
            return []

    def scrape_past_date(self, target_date):
        """過去の指定日付のデータを取得"""
        print(f"🎢 {target_date.strftime('%Y年%m月%d日')} の28時間帯データ取得開始")
        print("=" * 70)
        
        try:
            # WebDriverセットアップ
            if not self.setup_driver():
                return None
            
            # 指定日付にナビゲート
            if not self.navigate_to_date(target_date):
                print(f"❌ 日付ナビゲーション失敗")
                return None
            
            # 28時間帯データ抽出
            extracted_data = self.extract_28_times_data(target_date)
            
            if extracted_data:
                print(f"\n🎉 {target_date.strftime('%Y年%m月%d日')} データ取得完了!")
                print(f"📊 構造データ: {len(extracted_data)}件")
                
                # CSVファイル保存
                df = pd.DataFrame(extracted_data)
                csv_file = f"yosocal_28times_{target_date.strftime('%Y%m%d')}.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"💾 CSVファイル保存: {csv_file}")
                
                return extracted_data
            else:
                print(f"💥 データ取得失敗")
                return None
                
        except Exception as e:
            print(f"❌ スクレイピングエラー: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 WebDriver終了")

def main():
    """メイン処理"""
    print("🎢 yosocal.com 28時間帯データ取得システム")
    print("📅 過去の完全営業日データを取得")
    print("=" * 70)
    
    scraper = YosocalPastDataScraper()
    
    # テスト対象日付（過去の完全営業日）
    test_dates = [
        date(2025, 7, 1),   # 7月1日（火曜日）
        date(2025, 6, 30),  # 6月30日（月曜日）
        date(2025, 6, 29),  # 6月29日（日曜日）
    ]
    
    results = []
    
    for target_date in test_dates:
        print(f"\n" + "="*70)
        result = scraper.scrape_past_date(target_date)
        if result:
            results.append({
                'date': target_date,
                'data_count': len(result),
                'time_slots': len(set([item['time'] for item in result])),
                'attractions': len(set([item['attraction'] for item in result]))
            })
    
    # 最終サマリー
    print(f"\n🎉 28時間帯データ取得完了サマリー")
    print("=" * 70)
    for result in results:
        print(f"📅 {result['date']}: {result['data_count']}件 "
              f"(時間帯: {result['time_slots']}, アトラクション: {result['attractions']})")
    
    if any(r['time_slots'] >= 28 for r in results):
        print("✅ 28時間帯データ取得に成功！")
    else:
        print("❌ 28時間帯データの取得に失敗")

if __name__ == "__main__":
    main() 