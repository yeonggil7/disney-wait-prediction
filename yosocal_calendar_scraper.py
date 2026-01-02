import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import calendar

def generate_expected_times():
    """8:15から21:45まで30分おきの時間リストを生成"""
    times = []
    start_hour, start_minute = 8, 15
    end_hour, end_minute = 21, 45
    
    current_hour, current_minute = start_hour, start_minute
    
    while current_hour < end_hour or (current_hour == end_hour and current_minute <= end_minute):
        times.append(f"{current_hour:02d}:{current_minute:02d}")
        
        # 30分追加
        current_minute += 30
        if current_minute >= 60:
            current_minute -= 60
            current_hour += 1
    
    times.append("平均")  # 平均行も追加
    return times

def ensure_data_directory():
    """dataディレクトリが存在することを確認し、なければ作成"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"📁 {data_dir} ディレクトリを作成しました")
    return data_dir

def setup_driver():
    """Seleniumドライバーをセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # ヘッドレスモード
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    print("✅ WebDriverセットアップ完了")
    return driver

def print_progress_bar(current, total, prefix="進行状況", suffix="完了", length=40):
    """進捗バーを表示"""
    percent = ("{0:.1f}").format(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix} ({current}/{total})', end='', flush=True)

def extract_calendar_dates(driver):
    """カレンダーから利用可能な日付を抽出"""
    print("📅 カレンダーから利用可能な日付を抽出中...")
    
    try:
        # カレンダーテーブルを待機
        wait = WebDriverWait(driver, 10)
        calendar_table = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "FXTABLE"))
        )
        
        # 現在の月年を取得
        month_year_element = driver.find_element(By.CLASS_NAME, "TDBT")
        month_year_text = month_year_element.text  # "2025年 7月" 形式
        
        print(f"📅 現在表示中: {month_year_text}")
        
        # 年と月を抽出
        year_match = re.search(r'(\d{4})年', month_year_text)
        month_match = re.search(r'(\d{1,2})月', month_year_text)
        
        if year_match and month_match:
            year = int(year_match.group(1))
            month = int(month_match.group(1))
        else:
            print("❌ 年月の抽出に失敗")
            return [], year, month
        
        # カレンダーセルを取得
        calendar_cells = driver.find_elements(By.CSS_SELECTOR, "[id^='cal']")
        available_dates = []
        
        print(f"🔍 {len(calendar_cells)} 個のカレンダーセルをチェック中...")
        
        for cell in calendar_cells:
            try:
                # 日付要素を取得
                date_elements = cell.find_elements(By.CSS_SELECTOR, "[class*='CAL']")
                if not date_elements:
                    continue
                
                date_element = date_elements[0]
                date_text = date_element.text.strip()
                
                # 混雑指数を取得
                jam_elements = cell.find_elements(By.CSS_SELECTOR, "[class^='JAM']")
                if jam_elements:
                    jam_value = jam_elements[0].text.strip()
                else:
                    jam_value = "-"
                
                # 日付から年月日を構築
                if date_text and jam_value != "-":
                    # 日付から日を抽出
                    if '/' in date_text:  # "7/1" 形式
                        day_str = date_text.split('/')[-1]
                    else:  # "1" 形式
                        day_str = date_text
                    
                    try:
                        day = int(day_str)
                        # 年月日文字列を構築
                        date_str = f"{year:04d}{month:02d}{day:02d}"
                        
                        available_dates.append({
                            'date_str': date_str,
                            'date_text': date_text,
                            'jam_value': jam_value,
                            'cell_id': cell.get_attribute('id')
                        })
                        print(f"   ✅ {date_text}: 混雑指数 {jam_value} (ID: {cell.get_attribute('id')})")
                    except ValueError:
                        print(f"   ⭕ {date_text}: 日付解析エラー")
                else:
                    print(f"   ⭕ {date_text}: データなし (混雑指数: {jam_value})")
            
            except Exception as e:
                continue
        
        print(f"\n📊 結果: {len(available_dates)} 日分のデータが利用可能")
        return available_dates, year, month
        
    except Exception as e:
        print(f"❌ カレンダー情報の抽出エラー: {e}")
        return [], None, None

def wait_for_data_table(driver, timeout=30):
    """待ち時間データテーブルが読み込まれるまで待機"""
    print("   ⏳ 待ち時間データの読み込みを待機中...")
    
    # 複数の戦略で待ち時間データテーブルを探す
    strategies = [
        # Strategy 1: jamat div
        ("ID", "jamat"),
        # Strategy 2: 時間を含むテーブル（8:15, 8:45などを含む）
        ("XPATH", "//table[.//text()[contains(., '8:15') or contains(., '8:45') or contains(., '9:15')]]"),
        # Strategy 3: アトラクション名を含むテーブル
        ("XPATH", "//table[.//text()[contains(., '美女と野獣') or contains(., 'スプラッシュ') or contains(., 'ビッグサンダー')]]"),
        # Strategy 4: FPh2クラスを含むテーブル（アトラクション名のヘッダー）
        ("XPATH", "//table[.//*[contains(@class, 'FPh2')]]"),
        # Strategy 5: 分を含むテキストがあるテーブル
        ("XPATH", "//table[.//text()[contains(., '分')]]")
    ]
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        print(f"   🔍 検索試行 #{attempt}")
        
        for strategy_name, selector in strategies:
            try:
                if strategy_name == "ID":
                    elements = driver.find_elements(By.ID, selector)
                elif strategy_name == "XPATH":
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    continue
                
                print(f"     {strategy_name} strategy: {len(elements)} 要素発見")
                
                for i, element in enumerate(elements):
                    try:
                        # テーブル内容をチェック
                        table_text = element.text.lower() if element.text else ""
                        table_html = element.get_attribute('outerHTML') or ""
                        rows = element.find_elements(By.TAG_NAME, "tr")
                        
                        print(f"       要素 {i+1}: {len(rows)} 行, テキスト長: {len(table_text)}")
                        
                        # 待ち時間データらしい特徴をチェック
                        features = {
                            'time_8_15': '8:15' in table_text,
                            'time_8_45': '8:45' in table_text,
                            'attraction_beauty': '美女と野獣' in table_text,
                            'attraction_splash': 'スプラッシュ' in table_text,
                            'class_fph2': 'fph2' in table_html.lower(),
                            'id_jamat': 'jamat' in table_html.lower(),
                            'many_rows': len(rows) > 10,
                            'text_minutes': '分' in table_text
                        }
                        
                        print(f"       特徴: {features}")
                        
                        if any(features.values()):
                            print(f"   ✅ 待ち時間データテーブル発見: {strategy_name} strategy")
                            print(f"   📊 テーブル行数: {len(rows)}")
                            # テーブル内容の一部をプレビュー
                            preview_text = table_text[:200] + "..." if len(table_text) > 200 else table_text
                            print(f"   📝 内容プレビュー: {preview_text}")
                            
                            # HTMLを取得してjamat div形式で包む
                            table_html = element.get_attribute('outerHTML')
                            if 'id="jamat"' not in table_html:
                                # BeautifulSoupで包む
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(table_html, 'html.parser')
                                jamat_div = soup.new_tag('div', id='jamat')
                                jamat_div.append(soup)
                                return str(jamat_div)
                            else:
                                return table_html
                            
                    except Exception as e:
                        print(f"       要素チェックエラー: {e}")
                        continue
                        
            except Exception as e:
                print(f"     {strategy_name} strategy エラー: {e}")
                continue
        
        # 全テーブルの概要を表示（初回のみ）
        if attempt == 1:
            try:
                all_tables = driver.find_elements(By.TAG_NAME, "table")
                print(f"   📊 ページ内の全テーブル概要:")
                for i, table in enumerate(all_tables):
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    text_preview = table.text[:50] + "..." if table.text and len(table.text) > 50 else table.text or "空"
                    print(f"     テーブル {i+1}: {len(rows)} 行 - {text_preview}")
            except Exception as e:
                print(f"   ❌ テーブル概要取得エラー: {e}")
        
        elapsed = int(time.time() - start_time)
        print(f"   ⏳ 待機中... ({elapsed}/{timeout}s)")
        time.sleep(3)
    
    print("   ❌ 待ち時間データテーブルが見つかりませんでした")
    return None

def click_date_and_get_data(driver, date_info):
    """日付をクリックして待ち時間データを取得（詳細調査版）"""
    try:
        print(f"   📅 {date_info['date_text']} をクリック中...")
        
        # セルIDで日付要素を取得
        cell_element = driver.find_element(By.ID, date_info['cell_id'])
        
        # JavaScriptでクリック（より確実）
        driver.execute_script("arguments[0].click();", cell_element)
        
        # クリック後の処理待機（長めに設定）
        time.sleep(5)  # 3秒から5秒に延長
        
        print(f"   ⏳ {date_info['date_text']} のデータ読み込み待機中...")
        
        # 段階的にJavaScript読み込み完了を待つ
        for wait_attempt in range(3):
            print(f"   🔄 読み込み確認 #{wait_attempt + 1}/3")
            
            # ページ内の全HTML要素をチェック
            page_source = driver.page_source
            
            # FPMクラスとFPh2クラスの存在確認
            fpm_in_page = 'class="FPM"' in page_source or "class='FPM'" in page_source
            fph2_in_page = 'class="FPh2"' in page_source or "class='FPh2'" in page_source
            
            print(f"     📊 ページ内FPMクラス: {fpm_in_page}")
            print(f"     📊 ページ内FPh2クラス: {fph2_in_page}")
            
            if fpm_in_page and fph2_in_page:
                print("   ✅ 待機時間データが読み込まれました")
                break
            else:
                print(f"   ⏳ 待機時間データ未完了、{3}秒後に再確認...")
                time.sleep(3)
        
        # 詳細HTML調査
        print("   🔍 詳細HTML構造調査開始...")
        
        # 全テーブルの詳細分析
        all_tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"   📊 ページ内テーブル数: {len(all_tables)}")
        
        best_table = None
        best_score = 0
        
        for i, table in enumerate(all_tables):
            try:
                table_html = table.get_attribute('outerHTML')
                table_text = table.text
                
                # 詳細な特徴分析
                features = {
                    'fpm_class': len(re.findall(r'class="FPM"', table_html)),
                    'fph2_class': len(re.findall(r'class="FPh2"', table_html)),
                    'time_08_15': '08:15' in table_text,
                    'time_08_45': '08:45' in table_text,
                    'time_09_15': '09:15' in table_text,
                    'attraction_beauty': '美女と野獣' in table_text,
                    'attraction_splash': 'スプラッシュ' in table_text,
                    'attraction_bigthunder': 'ビッグサンダー' in table_text,
                    'b_classes': len(re.findall(r'class="B[0-8]"', table_html)),
                    'rows': len(table.find_elements(By.TAG_NAME, "tr")),
                    'cells': len(table.find_elements(By.TAG_NAME, "td"))
                }
                
                # スコア計算
                score = (
                    features['fpm_class'] * 10 +
                    features['fph2_class'] * 10 +
                    sum([features['time_08_15'], features['time_08_45'], features['time_09_15']]) * 5 +
                    sum([features['attraction_beauty'], features['attraction_splash'], features['attraction_bigthunder']]) * 5 +
                    min(features['b_classes'], 20) +
                    (1 if features['rows'] > 20 else 0) * 3
                )
                
                print(f"     テーブル {i+1}: スコア {score}")
                print(f"       FPM: {features['fpm_class']}, FPh2: {features['fph2_class']}")
                print(f"       時間: {features['time_08_15']}/{features['time_08_45']}/{features['time_09_15']}")
                print(f"       アトラクション: {features['attraction_beauty']}/{features['attraction_splash']}/{features['attraction_bigthunder']}")
                print(f"       Bクラス: {features['b_classes']}, 行: {features['rows']}")
                
                if score > best_score:
                    best_score = score
                    best_table = table
                    
                # サンプルHTML表示（高スコアテーブルのみ）
                if score > 10:
                    print(f"       🔬 HTML抜粋: {table_html[:200]}...")
                    print(f"       📝 テキスト抜粋: {table_text[:100].replace(chr(10), ' ')}...")
                
            except Exception as e:
                print(f"     テーブル {i+1}: 解析エラー - {e}")
                continue
        
        # 最適なテーブルを選択
        if best_table and best_score > 0:
            print(f"   🎯 最高スコア {best_score} のテーブルを使用")
            table_html = best_table.get_attribute('outerHTML')
            
            # jamat div形式で包む
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(table_html, 'html.parser')
            jamat_div = soup.new_tag('div', id='jamat')
            jamat_div.append(soup)
            return str(jamat_div)
        
        # 基本的なデータテーブル検索（従来の方法）
        data_html = wait_for_data_table(driver, timeout=10)
        
        if data_html:
            print(f"   ✅ {date_info['date_text']} の待ち時間データを発見（従来方式）")
            return data_html
        else:
            print(f"   ❌ {date_info['date_text']} の待ち時間データが見つかりません")
            
            # 最後の手段：現在のページ状況をファイルに保存
            debug_filename = f"debug_page_{date_info['date_text'].replace('/', '_')}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"   💾 デバッグ用にページ全体を {debug_filename} に保存")
            
            return None
            
    except Exception as e:
        print(f"   ❌ {date_info['date_text']} のデータ取得エラー: {e}")
        return None

def navigate_to_month(driver, target_year, target_month):
    """指定した年月に移動"""
    print(f"📅 {target_year}年{target_month}月に移動中...")
    
    max_attempts = 24  # 最大2年分移動
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # 現在表示中の年月を取得
            month_year_element = driver.find_element(By.CLASS_NAME, "TDBT")
            month_year_text = month_year_element.text
            
            year_match = re.search(r'(\d{4})年', month_year_text)
            month_match = re.search(r'(\d{1,2})月', month_year_text)
            
            if year_match and month_match:
                current_year = int(year_match.group(1))
                current_month = int(month_match.group(1))
                
                print(f"   現在: {current_year}年{current_month}月")
                
                if current_year == target_year and current_month == target_month:
                    print(f"   ✅ 目標の {target_year}年{target_month}月に到達")
                    return True
                
                # 前月・次月のどちらに移動するか決定
                current_total = current_year * 12 + current_month
                target_total = target_year * 12 + target_month
                
                if current_total < target_total:
                    # 次月ボタンをクリック
                    next_button = driver.find_element(By.XPATH, "//input[@value='次月']")
                    driver.execute_script("arguments[0].click();", next_button)
                    print("   → 次月に移動")
                else:
                    # 前月ボタンをクリック
                    prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
                    driver.execute_script("arguments[0].click();", prev_button)
                    print("   → 前月に移動")
                
                # ページ更新を待機
                time.sleep(2)
                attempts += 1
            else:
                print("   ❌ 年月の抽出に失敗")
                return False
                
        except Exception as e:
            print(f"   ❌ 月移動エラー: {e}")
            return False
    
    print(f"❌ {max_attempts}回の試行で目標月に到達できませんでした")
    return False

def parse_yosocal_complete(html_content, target_date, debug=False):
    """yosocal.com実際のテーブル構造に対応した解析関数"""
    
    if debug:
        print(f"🔍 データ解析開始 (target_date: {target_date})")
        print(f"📄 HTML長: {len(html_content)} 文字")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 複数の方法で待機時間テーブルを探す
    wait_time_table = None
    detection_method = ""
    
    # 方法1: jamatテーブルを探す
    jamat_div = soup.find('div', id='jamat')
    if jamat_div:
        table = jamat_div.find('table')
        if table:
            wait_time_table = table
            detection_method = "jamat div内"
    
    # 方法2: FPMクラス（時間）とFPh2クラス（アトラクション名）を含むテーブルを探す
    if not wait_time_table:
        all_tables = soup.find_all('table')
        for table in all_tables:
            fpm_elements = table.find_all(class_='FPM')  # 時間
            fph2_elements = table.find_all(class_='FPh2')  # アトラクション名
            
            if len(fpm_elements) > 5 and len(fph2_elements) > 10:  # 十分な数があればyosocalテーブル
                wait_time_table = table
                detection_method = f"FPM/FPh2クラス検出 (時間:{len(fpm_elements)}, アトラクション:{len(fph2_elements)})"
                break
    
    # 方法3: 時間パターンを含むテーブルを探す
    if not wait_time_table:
        for table in all_tables:
            table_text = table.get_text()
            if (re.search(r'08:15|08:45|09:15', table_text) and 
                re.search(r'美女と野獣|スプラッシュ|ビッグサンダー', table_text)):
                wait_time_table = table
                detection_method = "時間＋アトラクション名パターン検出"
                break
    
    if not wait_time_table:
        if debug:
            print("❌ 待機時間テーブルが見つかりません")
            # デバッグ情報を表示
            for i, table in enumerate(all_tables):
                fpm_count = len(table.find_all(class_='FPM'))
                fph2_count = len(table.find_all(class_='FPh2'))
                rows = len(table.find_all('tr'))
                print(f"  テーブル {i+1}: FPM:{fpm_count}, FPh2:{fph2_count}, 行数:{rows}")
        return pd.DataFrame()
    
    if debug:
        print(f"✅ テーブル発見 ({detection_method})")
    
    # データを格納するリスト
    data = []
    
    # 行を取得
    rows = wait_time_table.find_all('tr')
    
    # アトラクション名を最初に抽出
    attraction_names = []
    attraction_row_found = False
    
    for row in rows:
        fph2_cells = row.find_all(class_='FPh2')
        if len(fph2_cells) > 10:  # アトラクション名ヘッダー行
            attraction_names = [cell.get_text(strip=True).replace('｜', 'ー') for cell in fph2_cells]
            attraction_row_found = True
            if debug:
                print(f"🎢 {len(attraction_names)} 個のアトラクション名を取得")
                print(f"   最初の5個: {attraction_names[:5]}")
            break
    
    if not attraction_row_found:
        if debug:
            print("❌ アトラクション名ヘッダーが見つかりません")
        return pd.DataFrame()
    
    # 時間データ行を処理
    date_found = False
    time_data_rows = 0
    current_date = target_date or ""
    
    for row in rows:
        # 日付行をチェック（7月1日 形式）
        if row.find(class_='TDBT'):
            date_cell = row.find(class_='TDBT')
            if date_cell:
                current_date = date_cell.get_text(strip=True)
                date_found = True
                if debug:
                    print(f"📅 日付発見: {current_date}")
                continue
        
        # 時間データ行をチェック（FPMクラスを持つ行）
        time_cell = row.find(class_='FPM')
        if time_cell:
            time_text = time_cell.get_text(strip=True)
            
            # 「平均」または時間形式（08:15など）をチェック
            if time_text == '平均' or re.match(r'\d{1,2}:\d{2}', time_text):
                time_data_rows += 1
                if debug:
                    print(f"⏰ 時間データ行発見: {time_text}")
                
                # 行内の全セルを取得
                all_cells = row.find_all(['td', 'th'])
                
                # 待機時間データのセルを探す（B0-B8クラスを持つセル）
                wait_time_cells = []
                for cell in all_cells:
                    cell_classes = cell.get('class', [])
                    # B0-B8クラスを持つセルを待機時間データとして扱う
                    if any(cls.startswith('B') and len(cls) == 2 and cls[1].isdigit() for cls in cell_classes):
                        wait_time_cells.append(cell)
                
                if debug:
                    print(f"   🔢 {len(wait_time_cells)} 個の待機時間セルを発見")
                
                # 各アトラクションの待ち時間を抽出
                for i, cell in enumerate(wait_time_cells):
                    if i < len(attraction_names):
                        attraction_name = attraction_names[i]
                        cell_text = cell.get_text(strip=True)
                        cell_classes = cell.get('class', [])
                        
                        wait_time, status = parse_wait_time(cell_text, cell_classes)
                        
                        data.append({
                            'date': current_date,
                            'time': time_text,
                            'attraction': attraction_name,
                            'wait_time': wait_time,
                            'status': status,
                            'css_classes': ' '.join(cell_classes),
                            'raw_value': cell_text,
                            'data_source': detection_method
                        })
                
                if debug and len(wait_time_cells) > 0:
                    print(f"   ✅ {time_text}: {min(len(wait_time_cells), len(attraction_names))} 件のデータを抽出")
    
    # 結果の総計
    df = pd.DataFrame(data)
    
    if debug:
        print(f"\n📋 解析結果サマリー:")
        print(f"  - 日付が見つかったか: {date_found}")
        print(f"  - アトラクション名が見つかったか: {attraction_row_found}")
        print(f"  - 時間データ行数: {time_data_rows}")
        print(f"  - 総レコード数: {len(df)}")
        
        if len(df) > 0:
            print(f"✅ データ抽出成功:")
            print(f"  - ユニーク日付数: {df['date'].nunique()}")
            print(f"  - ユニーク時間数: {df['time'].nunique()}")
            print(f"  - ユニークアトラクション数: {df['attraction'].nunique()}")
            print(f"  - 有効な待機時間データ: {df[df['wait_time'].notna()].shape[0]} 件")
            
            # サンプルデータを表示
            print(f"\n📊 サンプルデータ (最初の5件):")
            sample_df = df.head().copy()
            for _, row in sample_df.iterrows():
                print(f"  {row['date']} {row['time']} - {row['attraction']}: {row['wait_time']}分 ({row['status']})")
        else:
            print("❌ データが抽出されませんでした")
    
    return df

def parse_wait_time(text, css_classes):
    """待ち時間テキストを数値とステータスに変換"""
    text = text.strip()
    
    # 空またはダッシュの場合
    if not text or text == '-' or text == '':
        return None, 'no_data'
    
    # 運休・休止の場合
    if text in ['運休', '休止', '点検', 'メンテナンス'] or 'B8' in css_classes:
        return -1, 'closed'
    
    # 数値＋「分」の場合
    if '分' in text:
        match = re.search(r'(\d+)分', text)
        if match:
            return int(match.group(1)), 'normal'
    
    # 数値のみの場合
    if text.isdigit():
        return int(text), 'normal'
    
    # CSSクラスから混雑レベルを推定
    if 'B0' in css_classes:
        return 5, 'empty'      # 空いている
    elif 'B1' in css_classes:
        return 10, 'light'     # 少し混雑
    elif 'B2' in css_classes:
        return 20, 'normal'    # 普通
    elif 'B3' in css_classes:
        return 30, 'busy'      # 混雑
    elif 'B4' in css_classes:
        return 45, 'very_busy' # 非常に混雑
    elif 'B6' in css_classes:
        return 60, 'extreme'   # 激混み
    elif 'B8' in css_classes:
        return -1, 'closed'    # 運休・休止
    
    # その他のテキスト（フリーパスやFPなど）
    if 'FP' in text.upper() or 'ファストパス' in text:
        return 0, 'fastpass'
    elif 'チケット' in text:
        return 0, 'ticket_required'
    
    # 不明な場合はテキストをそのまま返す
    return text, 'unknown'

def scrape_single_month(driver, year, month):
    """単一月のデータを取得"""
    print(f"\n🗓️  {year}年{month}月のデータ取得開始")
    print("=" * 60)
    
    # 指定月に移動
    if not navigate_to_month(driver, year, month):
        print(f"❌ {year}年{month}月への移動に失敗")
        return pd.DataFrame()
    
    # カレンダーから利用可能な日付を取得
    available_dates, current_year, current_month = extract_calendar_dates(driver)
    
    if not available_dates:
        print(f"⚠️ {year}年{month}月にデータが見つかりません")
        return pd.DataFrame()
    
    # 月のデータを格納するリスト
    month_data = []
    
    print(f"\n📊 {len(available_dates)} 日分のデータを取得開始")
    print("-" * 60)
    
    for i, date_info in enumerate(available_dates, 1):
        print(f"\n📅 [{i:2d}/{len(available_dates):2d}] {date_info['date_text']} (混雑度: {date_info['jam_value']})")
        print_progress_bar(i-1, len(available_dates), prefix="全体進捗", suffix="", length=30)
        print()
        
        # 日付をクリックしてデータを取得
        html_content = click_date_and_get_data(driver, date_info)
        
        if html_content:
            print("   📊 データを解析中...")
            # データを解析（デバッグモード有効）
            daily_df = parse_yosocal_complete(html_content, date_info['date_str'], debug=True)
            
            if not daily_df.empty:
                month_data.append(daily_df)
                print(f"   ✅ {len(daily_df)} レコードを取得完了")
            else:
                print(f"   ⚠️ データ解析に失敗")
        else:
            print(f"   ❌ HTMLデータ取得に失敗")
        
        # リクエスト間隔を空ける
        print("   ⏳ 1秒待機中...")
        time.sleep(1)
    
    # 最終進捗表示
    print_progress_bar(len(available_dates), len(available_dates), prefix="全体進捗", suffix="完了", length=30)
    print()
    
    # 月のデータを統合
    if month_data:
        month_df = pd.concat(month_data, ignore_index=True)
        print(f"\n✅ {year}年{month}月: 総 {len(month_df):,} レコードを取得完了")
        return month_df
    else:
        print(f"\n❌ {year}年{month}月: データ取得に失敗")
        return pd.DataFrame()

def scrape_year_2025():
    """2025年全体のデータを取得"""
    print("🏰 yosocal.com 2025年全体スクレイピング開始")
    print("=" * 80)
    
    data_dir = ensure_data_directory()
    driver = setup_driver()
    
    try:
        # yosocal.comにアクセス
        print("🌐 yosocal.comにアクセス中...")
        driver.get("https://yosocal.com/")
        
        # ページ読み込み待機
        time.sleep(5)
        
        # 2025年の全月データを格納するリスト
        year_data = []
        
        # 2025年の各月を順次処理
        for month in range(1, 13):
            print(f"\n" + "="*80)
            print(f"📅 【{month:2d}月 / 12月】 の処理開始")
            print("="*80)
            
            month_df = scrape_single_month(driver, 2025, month)
            
            if not month_df.empty:
                year_data.append(month_df)
                
                # 月ごとにCSV保存
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                month_filename = os.path.join(data_dir, f"yosocal_2025_{month:02d}_{timestamp}.csv")
                month_df.to_csv(month_filename, index=False, encoding='utf-8-sig')
                print(f"💾 月次ファイル保存: {month_filename}")
            
            print(f"📊 {month}月完了: {len(month_df) if not month_df.empty else 0:,} レコード")
            print_progress_bar(month, 12, prefix="年間進捗", suffix=f"({month}/12月)", length=40)
            print()
        
        # 年間データを統合
        if year_data:
            print(f"\n" + "="*80)
            print("📊 2025年全体データの統合中...")
            
            year_df = pd.concat(year_data, ignore_index=True)
            
            # 年間CSVファイル保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            year_filename = os.path.join(data_dir, f"yosocal_2025_complete_{timestamp}.csv")
            year_df.to_csv(year_filename, index=False, encoding='utf-8-sig')
            
            print(f"✅ 2025年全体データ取得完了!")
            print(f"📊 総レコード数: {len(year_df):,}")
            print(f"📁 年間ファイル: {year_filename}")
            
            # 統計情報を表示
            analyze_year_data(year_df)
            
            return year_df
        else:
            print("❌ 2025年のデータ取得に失敗しました")
            return pd.DataFrame()
    
    finally:
        driver.quit()
        print("\n🔚 ブラウザを終了しました")

def analyze_year_data(df):
    """年間データの分析"""
    print(f"\n📈 2025年データ分析")
    print("-" * 50)
    
    unique_dates = df['target_date'].unique()
    unique_months = [date[:6] for date in unique_dates]
    unique_months = list(set(unique_months))
    
    print(f"📅 データ取得日数: {len(unique_dates)} 日")
    print(f"📅 データ取得月数: {len(unique_months)} 月")
    print(f"🎢 アトラクション数: {df['attraction'].nunique()}")
    print(f"⏰ 時間帯数: {df['time'].nunique()}")

def test_june_data():
    """6月のデータが取得できるかテスト"""
    print("🧪 6月データ取得テスト開始")
    print("=" * 50)
    
    data_dir = ensure_data_directory()
    driver = setup_driver()
    
    try:
        # yosocal.comにアクセス
        print("🌐 yosocal.comにアクセス中...")
        driver.get("https://yosocal.com/")
        time.sleep(5)
        
        # 6月に移動してテスト
        month_df = scrape_single_month(driver, 2025, 6)
        
        if not month_df.empty:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = os.path.join(data_dir, f"yosocal_2025_06_test_{timestamp}.csv")
            month_df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 6月テスト完了: {filename}")
            print(f"📊 取得レコード数: {len(month_df):,}")
        else:
            print("\n❌ 6月のデータは現在利用できません")
    
    finally:
        driver.quit()
        print("\n🔚 ブラウザを終了しました")

def main():
    """メイン実行関数"""
    choice = input("""
🏰 yosocal.com カレンダー スクレイピング システム（改良版）
================================================================

実行モードを選択してください:
1. 2025年全体のデータを取得
2. 特定の月のデータを取得
3. 6月データ取得テスト 🧪
4. デモ実行（現在表示中の月のみ）

選択 (1-4): """).strip()
    
    if choice == "1":
        # 2025年全体を取得
        scrape_year_2025()
    
    elif choice == "2":
        # 特定月を取得
        year = int(input("年を入力 (例: 2025): "))
        month = int(input("月を入力 (例: 7): "))
        
        data_dir = ensure_data_directory()
        driver = setup_driver()
        try:
            driver.get("https://yosocal.com/")
            time.sleep(5)
            
            month_df = scrape_single_month(driver, year, month)
            
            if not month_df.empty:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                filename = os.path.join(data_dir, f"yosocal_{year}_{month:02d}_{timestamp}.csv")
                month_df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"\n✅ ファイル保存完了: {filename}")
        finally:
            driver.quit()
    
    elif choice == "3":
        # 6月テスト実行
        test_june_data()
    
    elif choice == "4":
        # デモ実行
        data_dir = ensure_data_directory()
        driver = setup_driver()
        try:
            driver.get("https://yosocal.com/")
            time.sleep(5)
            
            available_dates, year, month = extract_calendar_dates(driver)
            print(f"\n📅 現在表示中: {year}年{month}月")
            print(f"📊 利用可能データ: {len(available_dates)} 日")
            
            if available_dates:
                # 最初の日付のデータを取得してみる
                first_date = available_dates[0]
                html_content = click_date_and_get_data(driver, first_date)
                
                if html_content:
                    df = parse_yosocal_complete(html_content, first_date['date_str'], debug=True)
                    if not df.empty:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                        filename = os.path.join(data_dir, f"yosocal_demo_{first_date['date_str']}_{timestamp}.csv")
                        df.to_csv(filename, index=False, encoding='utf-8-sig')
                        print(f"\n✅ デモファイル保存: {filename}")
        finally:
            driver.quit()
    
    else:
        print("❌ 無効な選択です")

if __name__ == "__main__":
    main() 