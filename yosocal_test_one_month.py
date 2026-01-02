# -*- coding: utf-8 -*-
"""
yosocal.com 1ヶ月テスト版データ取得
長期間システムのテスト用（2024年1月のみ）
"""

import time
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm

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

def generate_expected_times():
    """期待される時間帯リストを生成"""
    times = []
    for hour in range(8, 22):
        if hour == 8:
            # 8時は15分、45分のみ
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
        elif hour == 21:
            # 21時は15分、45分のみ
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
        else:
            # その他は15分、45分
            times.extend([f"{hour:02d}:15", f"{hour:02d}:45"])
    
    # 平均を追加
    times.append("平均")
    
    return times

def navigate_to_month(driver, year, month):
    """指定した年月に移動"""
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # JavaScript関数で月移動
        js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
        driver.execute_script(js_code)
        time.sleep(5)
        
        # 移動確認
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            current_month = month_elements[0].text.strip()
            if str(year) in current_month and str(month) in current_month:
                return True, current_month
        
        return False, "移動失敗"
        
    except Exception as e:
        return False, f"エラー: {e}"

def extract_calendar_dates(driver):
    """カレンダーから利用可能な日付を抽出"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        available_dates = []
        
        # CAL、CALSAT、CALSUNクラスの日付要素を探す
        date_classes = ['CAL', 'CALSAT', 'CALSUN']
        
        for class_name in date_classes:
            date_elements = soup.find_all(class_=class_name)
            for element in date_elements:
                date_text = element.get_text(strip=True)
                if date_text.isdigit():
                    date_num = int(date_text)
                    if 1 <= date_num <= 31:
                        available_dates.append(date_num)
        
        # 重複削除・ソート
        available_dates = sorted(list(set(available_dates)))
        
        return available_dates
        
    except Exception as e:
        print(f"❌ カレンダー日付抽出エラー: {e}")
        return []

def click_date_and_extract_data(driver, date_num, year, month):
    """日付をクリックしてデータを抽出"""
    try:
        # 日付をクリック
        date_xpath = f"//td[@class='CAL' or @class='CALSAT' or @class='CALSUN'][text()='{date_num}']"
        date_elements = driver.find_elements(By.XPATH, date_xpath)
        
        if not date_elements:
            return [], f"日付{date_num}が見つかりません"
        
        # 最初の要素をクリック
        date_elements[0].click()
        time.sleep(3)
        
        # realtime.htmに移動してデータ抽出
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # データ抽出
        data = extract_wait_time_data(driver, year, month, date_num)
        
        return data, "成功"
        
    except Exception as e:
        return [], f"エラー: {e}"

def extract_wait_time_data(driver, year, month, date_num):
    """realtime.htmから待ち時間データを抽出"""
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # jamat divを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return []
        
        # テーブルを探す
        table = jamat_div.find('table')
        if not table:
            return []
        
        rows = table.find_all('tr')
        if len(rows) < 2:  # ヘッダー + データ行が必要
            return []
        
        # 期待される時間帯を取得
        expected_times = generate_expected_times()
        
        # データ抽出
        extracted_data = []
        
        # アトラクション名を抽出（FPh2クラス）
        attractions = []
        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all(['td', 'th'])
            if cells:
                first_cell = cells[0]
                attraction_name = first_cell.get_text(strip=True)
                if attraction_name and attraction_name not in ['時間', 'アトラクション']:
                    attractions.append(attraction_name)
        
        # 各アトラクションの待ち時間データを抽出
        for attraction in attractions:
            # アトラクション行を見つける
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if cells and cells[0].get_text(strip=True) == attraction:
                    # 時間帯ごとのデータを抽出
                    for time_idx, time_slot in enumerate(expected_times, 1):
                        if time_idx < len(cells):
                            cell = cells[time_idx]
                            
                            # 待ち時間の数値を抽出
                            cell_text = cell.get_text(strip=True)
                            css_classes = ' '.join(cell.get('class', []))
                            
                            # ステータス判定
                            if cell_text == '-' or cell_text == '':
                                status = 'no_data'
                                wait_time = None
                            elif cell_text.isdigit():
                                status = 'normal'
                                wait_time = float(cell_text)
                            else:
                                status = 'empty'
                                wait_time = None
                            
                            # データ記録
                            record = {
                                'date': f"{month}月{date_num:02d}日",
                                'year': year,
                                'month': month,
                                'day': date_num,
                                'time': time_slot,
                                'attraction': attraction,
                                'wait_time': wait_time,
                                'status': status,
                                'css_classes': css_classes,
                                'raw_value': cell_text,
                                'data_source': 'jamat div内'
                            }
                            extracted_data.append(record)
                    break
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def main():
    """メイン1ヶ月テストプロセス"""
    print("🧪 yosocal.com 1ヶ月テスト版データ取得")
    print("📅 対象: 2024年1月")
    print("=" * 50)
    
    # テスト対象
    test_year = 2024
    test_month = 1
    
    # 出力ファイル設定
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosocal_test_2024_01_{timestamp}.csv"
    
    driver = None
    all_data = []
    
    try:
        driver = setup_driver()
        
        print(f"\n📅 {test_year}年{test_month}月 テスト開始")
        
        # 月に移動
        success, result = navigate_to_month(driver, test_year, test_month)
        if not success:
            print(f"❌ {test_year}年{test_month}月への移動失敗: {result}")
            return
        
        print(f"✅ {result} に移動完了")
        
        # カレンダー日付抽出
        available_dates = extract_calendar_dates(driver)
        print(f"📋 利用可能日付: {len(available_dates)}日")
        print(f"📋 日付リスト: {available_dates}")
        
        if not available_dates:
            print(f"⚠️ {test_year}年{test_month}月にデータなし")
            return
        
        # 最初の3日だけテスト（フルテストを避ける）
        test_dates = available_dates[:3]
        print(f"🧪 テスト対象日付: {test_dates}")
        
        # 日付ごとの処理
        for date_num in tqdm(test_dates, desc=f"2024/01"):
            try:
                # メインページに戻って月を再設定
                navigate_to_month(driver, test_year, test_month)
                time.sleep(2)
                
                # 日付クリックとデータ抽出
                data, status = click_date_and_extract_data(driver, date_num, test_year, test_month)
                
                if data:
                    all_data.extend(data)
                    print(f"✅ {test_month}月{date_num:02d}日: {len(data)}件")
                else:
                    print(f"❌ {test_month}月{date_num:02d}日: {status}")
                
                # 短い待機
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ {test_month}月{date_num:02d}日処理エラー: {e}")
        
        # データ保存
        if all_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'year', 'month', 'day', 'time', 'attraction', 'wait_time', 
                            'status', 'css_classes', 'raw_value', 'data_source']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_data)
            
            print(f"\n📊 テスト結果:")
            print(f"   📁 出力ファイル: {output_file}")
            print(f"   📈 総データ数: {len(all_data):,}件")
            print(f"   📅 処理日数: {len(test_dates)}日")
            
            # データ統計
            valid_data = [d for d in all_data if d['wait_time'] is not None]
            print(f"   ✅ 有効データ: {len(valid_data):,}件")
            
            if valid_data:
                avg_wait = sum(d['wait_time'] for d in valid_data) / len(valid_data)
                print(f"   ⏱️ 平均待ち時間: {avg_wait:.1f}分")
            
            # アトラクション数
            attractions = set(d['attraction'] for d in all_data)
            print(f"   🎢 アトラクション数: {len(attractions)}個")
            
            # 時間帯数
            time_slots = set(d['time'] for d in all_data)
            print(f"   ⏰ 時間帯数: {len(time_slots)}個")
            
            print(f"\n✅ 1ヶ月テスト完了！長期間システムの動作を確認しました。")
            
        else:
            print(f"❌ データが取得できませんでした")
        
    except Exception as e:
        print(f"❌ テストでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 