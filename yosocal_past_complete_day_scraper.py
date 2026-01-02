#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import json

class YosocalCompleteDataScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self):
        """WebDriverセットアップ"""
        print("🔧 Chrome WebDriver（完全データ取得版）をセットアップ中...")
        
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
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
                        match = re.search(r'(\d{4})年(\d{1,2})月', text)
                        if match:
                            year = int(match.group(1))
                            month = int(match.group(2))
                            print(f"   📅 現在のカレンダー: {year}年{month}月")
                            return year, month
                except:
                    continue
            
            now = datetime.now()
            print(f"   ⚠️ カレンダー年月検出失敗、現在時刻を使用: {now.year}年{now.month}月")
            return now.year, now.month
            
        except Exception as e:
            print(f"   ❌ カレンダー年月取得エラー: {e}")
            now = datetime.now()
            return now.year, now.month

    def navigate_to_past_date(self, target_date):
        """過去の完全営業日にナビゲート"""
        try:
            print(f"📅 {target_date.strftime('%Y年%m月%d日')} の完全データ取得を開始...")
            
            # メインページアクセス
            self.driver.get("https://yosocal.com/")
            time.sleep(3)
            
            target_year = target_date.year
            target_month = target_date.month
            
            # 現在表示されている年月を取得
            current_year, current_month = self.get_current_calendar_date()
            
            # 目標年月まで移動（過去の日付の場合）
            max_attempts = 12  # 最大1年分
            attempts = 0
            
            while (current_year, current_month) != (target_year, target_month) and attempts < max_attempts:
                if (target_year, target_month) < (current_year, current_month):
                    # 前月ボタン（過去方向）
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
                else:
                    print(f"   ✅ 目標年月に到達: {target_year}年{target_month}月")
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
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(1)
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
                return False
            
            # 日付クリック後の待機
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ 日付ナビゲーションエラー: {e}")
            return False

    def analyze_complete_time_slots(self, target_date):
        """完全な時間帯データを解析"""
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
            debug_file = f"yosocal_complete_{target_date.strftime('%Y%m%d')}_{timestamp}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"🔍 デバッグファイル保存: {debug_file}")
            
            # jamat div要素を探す
            jamat_div = soup.find('div', {'id': 'jamat'})
            if not jamat_div:
                print("❌ jamat div要素が見つかりません")
                return None
            
            print("✅ jamat div要素を発見")
            
            # テーブル解析
            table = jamat_div.find('table')
            if not table:
                print("❌ jamat内にテーブルが見つかりません")
                return None
            
            rows = table.find_all('tr')
            print(f"📋 テーブル行数: {len(rows)}")
            
            # 詳細な時間帯解析
            time_slots = []
            valid_time_slots = []  # 実際にデータがある時間帯
            empty_time_slots = []  # 空白の時間帯
            
            for i, row in enumerate(rows):
                fpm_cell = row.find('td', class_='FPM')
                if fpm_cell:
                    time_text = fpm_cell.get_text().strip()
                    time_slots.append({
                        'row_index': i,
                        'time_text': time_text,
                        'is_valid': time_text not in ['', '　'],
                        'is_time_pattern': bool(re.match(r'\d{1,2}:\d{2}', time_text))
                    })
                    
                    if time_text and time_text not in ['', '　']:
                        if re.match(r'\d{1,2}:\d{2}', time_text):
                            valid_time_slots.append(time_text)
                            print(f"⏰ 行{i}: 有効時間「{time_text}」")
                        else:
                            print(f"📊 行{i}: その他データ「{time_text}」")
                    else:
                        empty_time_slots.append(i)
                        print(f"❌ 行{i}: 空白時間帯")
            
            # アトラクション名の解析
            attraction_names = []
            for i, row in enumerate(rows):
                fph2_cells = row.find_all('td', class_='FPh2')
                if fph2_cells and not attraction_names:
                    attraction_names = [cell.get_text().strip() for cell in fph2_cells]
                    print(f"🎯 アトラクション名行発見 (行{i}): {len(attraction_names)}個")
                    break
            
            # 結果サマリー
            print(f"\n📊 {target_date.strftime('%Y年%m月%d日')} 完全データ分析結果:")
            print(f"   📋 総テーブル行数: {len(rows)}")
            print(f"   🔍 時間帯要素数: {len(time_slots)}")
            print(f"   ✅ 有効時間帯数: {len(valid_time_slots)}")
            print(f"   ❌ 空白時間帯数: {len(empty_time_slots)}")
            print(f"   🎯 アトラクション数: {len(attraction_names)}")
            
            # 28時間帯達成チェック
            print(f"\n🎯 28時間帯達成状況:")
            if len(valid_time_slots) >= 28:
                print(f"   ✅ 28時間帯達成！({len(valid_time_slots)}個)")
                achievement_status = "完全達成"
            elif len(valid_time_slots) >= 20:
                print(f"   🔶 部分達成（{len(valid_time_slots)}/28個）")
                achievement_status = "部分達成"
            else:
                print(f"   ❌ 未達成（{len(valid_time_slots)}/28個）")
                achievement_status = "未達成"
            
            # 有効時間帯詳細表示
            if valid_time_slots:
                print(f"\n⏰ 検出された有効時間帯:")
                for i, slot in enumerate(valid_time_slots[:10]):  # 最初の10個のみ表示
                    print(f"   {i+1:2d}. {slot}")
                if len(valid_time_slots) > 10:
                    print(f"   ... 他{len(valid_time_slots)-10}個")
            
            # 分析結果をJSONで保存
            analysis_data = {
                'analysis_date': timestamp,
                'target_date': target_date.strftime('%Y年%m月%d日'),
                'total_table_rows': len(rows),
                'time_slot_elements': len(time_slots),
                'valid_time_slots_count': len(valid_time_slots),
                'valid_time_slots': valid_time_slots,
                'empty_time_slots_count': len(empty_time_slots),
                'attraction_count': len(attraction_names),
                'achievement_status': achievement_status,
                'target_achieved': len(valid_time_slots) >= 28,
                'debug_file': debug_file
            }
            
            json_file = f"yosocal_complete_analysis_{target_date.strftime('%Y%m%d')}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 完全分析結果保存: {json_file}")
            
            return analysis_data
            
        except Exception as e:
            print(f"❌ 完全データ解析エラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    def test_past_dates(self):
        """複数の過去日付をテストして28時間帯データを探す"""
        print(f"🔍 過去の完全営業日データ検索開始")
        print("=" * 70)
        
        # テスト対象日付（より過去の完全営業日）
        test_dates = [
            date(2025, 6, 28),  # 6月28日（土曜日）
            date(2025, 6, 27),  # 6月27日（金曜日）
            date(2025, 6, 26),  # 6月26日（木曜日）
            date(2025, 6, 25),  # 6月25日（水曜日）
            date(2025, 6, 24),  # 6月24日（火曜日）
        ]
        
        results = []
        
        try:
            # WebDriverセットアップ
            if not self.setup_driver():
                return None
            
            for target_date in test_dates:
                print(f"\n" + "="*70)
                print(f"🎯 {target_date.strftime('%Y年%m月%d日')} テスト開始")
                
                # 過去日付にナビゲート
                if not self.navigate_to_past_date(target_date):
                    print(f"❌ 日付ナビゲーション失敗")
                    continue
                
                # 完全データ解析
                analysis_result = self.analyze_complete_time_slots(target_date)
                
                if analysis_result:
                    results.append(analysis_result)
                    print(f"✅ {target_date.strftime('%Y年%m月%d日')} 解析完了")
                    
                    # 28時間帯達成していれば詳細表示
                    if analysis_result['target_achieved']:
                        print(f"🎉 **28時間帯達成日発見**: {target_date.strftime('%Y年%m月%d日')}")
                        print(f"   ⏰ 時間帯数: {analysis_result['valid_time_slots_count']}")
                        print(f"   🎯 アトラクション数: {analysis_result['attraction_count']}")
                        break  # 最初の完全データが見つかったら終了
                else:
                    print(f"❌ {target_date.strftime('%Y年%m月%d日')} 解析失敗")
                
                # 少し待機してから次の日付へ
                time.sleep(2)
            
            return results
            
        except Exception as e:
            print(f"❌ 過去日付テストエラー: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 WebDriver終了")

def main():
    """メイン処理"""
    print("🎯 yosocal.com 過去完全営業日データ探索")
    print("📅 28時間帯完全データの発見を目指します")
    print("=" * 70)
    
    scraper = YosocalCompleteDataScraper()
    results = scraper.test_past_dates()
    
    if results:
        print(f"\n🎉 過去日付テスト完了サマリー")
        print("=" * 70)
        
        for result in results:
            status_emoji = "✅" if result['target_achieved'] else "🔶" if result['valid_time_slots_count'] >= 20 else "❌"
            print(f"{status_emoji} {result['target_date']}: {result['valid_time_slots_count']}時間帯 "
                  f"({result['achievement_status']})")
        
        # 完全達成があるかチェック
        complete_results = [r for r in results if r['target_achieved']]
        if complete_results:
            print(f"\n🏆 28時間帯完全達成日: {len(complete_results)}日発見！")
            for result in complete_results:
                print(f"   📅 {result['target_date']}: {result['valid_time_slots_count']}時間帯")
        else:
            print(f"\n💭 28時間帯完全達成日は見つかりませんでした")
            print("   💡 より過去の日付や異なる時間帯での取得が必要かもしれません")
    else:
        print(f"\n❌ 過去日付テストに失敗しました")

if __name__ == "__main__":
    main() 