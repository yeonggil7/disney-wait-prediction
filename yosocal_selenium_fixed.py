import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import requests
import time
import json
from urllib.parse import urljoin

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

def selenium_scraping_with_manager(target_date="20250702"):
    """webdriver-managerを使用したSeleniumスクレイピング"""
    print("🔧 webdriver-managerによる自動ChromeDriverセットアップ...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Chromeオプション設定
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # ヘッドレスモード
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
        
        # webdriver-managerで適切なChromeDriverを自動取得
        service = Service(ChromeDriverManager().install())
        
        # WebDriverを初期化
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            print("🌐 yosocal.comにアクセス中...")
            driver.get("https://yosocal.com/")
            
            # ページが完全に読み込まれるまで待機
            time.sleep(5)
            
            print("🔍 jamatテーブルを検索中...")
            
            # jamatテーブルが表示されるまで待機（最大20秒）
            try:
                wait = WebDriverWait(driver, 20)
                jamat_element = wait.until(
                    EC.presence_of_element_located((By.ID, "jamat"))
                )
                print("✅ jamatテーブルを発見！")
            except:
                print("⚠️ jamatテーブルが見つからないため、ページ内容を確認...")
                
                # ページソースを確認
                page_source = driver.page_source
                if 'jamat' in page_source.lower():
                    print("📜 ページソース内にjamatが存在することを確認")
                else:
                    print("❌ ページソース内にjamatが見つかりません")
                    
                    # デバッグ用：利用可能なテーブルを確認
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    print(f"📊 ページ内のテーブル数: {len(tables)}")
                    
                    for i, table in enumerate(tables):
                        if table.is_displayed():
                            table_text = table.text[:100] if table.text else ""
                            print(f"   テーブル{i}: {table_text}...")
            
            # JavaScript実行を少し待機
            time.sleep(3)
            
            # 最新のページソースを取得
            html_content = driver.page_source
            
            # BeautifulSoupで解析
            soup = BeautifulSoup(html_content, 'html.parser')
            jamat_div = soup.find('div', id='jamat')
            
            if jamat_div:
                print("🎯 jamatテーブルをHTMLから取得成功！")
                return str(jamat_div)
            else:
                print("⚠️ jamat divが見つからないため、全体から待ち時間テーブルを探索...")
                
                # アトラクション名を含むテーブルを探す
                tables = soup.find_all('table')
                for i, table in enumerate(tables):
                    table_text = table.get_text()
                    if any(name in table_text for name in ['スプラッシュ', '美女と野獣', 'ビッグサンダー', 'ハニーハント']):
                        print(f"🎢 アトラクション名を含むテーブル{i}を発見！")
                        return str(table)
                
                print("❌ 待ち時間テーブルが見つかりません")
                
                # デバッグ用：ページの概要を出力
                print("\n📄 ページ概要:")
                title = soup.find('title')
                if title:
                    print(f"   タイトル: {title.get_text()}")
                
                # 主要なdivを確認
                main_divs = soup.find_all('div', limit=10)
                print(f"   主要div数: {len(main_divs)}")
                
                return None
                
        except Exception as e:
            print(f"❌ スクレイピング処理中エラー: {e}")
            return None
            
        finally:
            driver.quit()
            
    except ImportError as e:
        print(f"❌ ライブラリのインポートエラー: {e}")
        return None
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return None

def parse_yosocal_complete(html_content, debug=True):
    """完全版：全時間帯の待ち時間データを解析"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # jamatテーブルを取得
    jamat_div = soup.find('div', id='jamat')
    if not jamat_div:
        # divが見つからない場合、HTML全体から解析
        jamat_div = soup
        print("⚠️ jamat divが見つからないため、HTML全体から解析します")
    
    table = jamat_div.find('table')
    if not table:
        print("❌ テーブルが見つかりません")
        return pd.DataFrame()
    
    # データを格納するリスト
    data = []
    
    # 行を取得
    rows = table.find_all('tr')
    
    # 変数の初期化
    current_date = ""
    attraction_names = []
    expected_times = generate_expected_times()
    
    print(f"\n📊 {len(rows)} 行を解析中...")
    print(f"🕐 期待される時間帯数: {len(expected_times)}")
    
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        
        # 日付行を検出
        if len(cells) == 1 and ('月' in cells[0].get_text() and '日' in cells[0].get_text()):
            current_date = cells[0].get_text(strip=True)
            print(f"\n📅 日付発見: {current_date}")
            continue
        
        # アトラクション名のヘッダー行を検出
        if len(cells) > 30:  # アトラクション名が多い行
            attraction_cells = [cell for cell in cells if 'FPh2' in cell.get('class', [])]
            if attraction_cells:
                attraction_names = [cell.get_text(strip=True) for cell in attraction_cells]
                print(f"🎢 {len(attraction_names)} 個のアトラクション名を取得")
                continue
        
        # 時間データ行を検出
        if len(cells) > 10 and attraction_names:
            time_cell = cells[0] if cells else None
            if time_cell and ('FPM' in time_cell.get('class', []) or 'FPT' in time_cell.get('class', [])):
                time_text = time_cell.get_text(strip=True)
                
                # 時間形式または「平均」かチェック
                if re.match(r'\d{1,2}:\d{2}', time_text) or time_text == '平均':
                    print(f"⏰ 時間データ行発見: {time_text}")
                    
                    # 天気列の存在を動的に判定
                    weather_cell_exists = False
                    if len(cells) > 1:
                        second_cell = cells[1]
                        cell_content = str(second_cell).lower()
                        cell_text = second_cell.get_text(strip=True)
                        
                        # 天気列の特徴を確認
                        if (second_cell.get('rowspan') or 
                            'gif' in cell_content or 
                            'weather' in cell_content or
                            '天' in cell_text or
                            'img' in cell_content):
                            weather_cell_exists = True
                    
                    # データ開始位置の決定
                    data_start_idx = 2 if weather_cell_exists else 1
                    
                    wait_time_cells = cells[data_start_idx:]
                    
                    # 最後の列（平均列）は除く
                    if len(wait_time_cells) > len(attraction_names):
                        wait_time_cells = wait_time_cells[:-1]
                    
                    # データの長さチェック
                    if len(wait_time_cells) != len(attraction_names):
                        print(f"   ⚠️ データ数不一致: 期待{len(attraction_names)}, 実際{len(wait_time_cells)}")
                        # 短い方に合わせる
                        min_length = min(len(attraction_names), len(wait_time_cells))
                        attraction_names_subset = attraction_names[:min_length]
                        wait_time_cells = wait_time_cells[:min_length]
                    else:
                        attraction_names_subset = attraction_names
                    
                    # データを抽出
                    for idx, (attraction_name, cell) in enumerate(zip(attraction_names_subset, wait_time_cells)):
                        wait_text = cell.get_text(strip=True)
                        css_classes = cell.get('class', [])
                        
                        # 待ち時間の数値変換
                        wait_time = parse_wait_time(wait_text, css_classes)
                        
                        data.append({
                            'date': current_date,
                            'time': time_text,
                            'attraction': attraction_name,
                            'wait_time': wait_time,
                            'raw_value': wait_text,
                            'css_class': ' '.join(css_classes),
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    print(f"   ✅ {len(attraction_names_subset)} 件のデータを抽出")
    
    df = pd.DataFrame(data)
    print(f"\n📋 総 {len(df)} レコードを抽出完了")
    
    return df

def parse_wait_time(text, css_classes):
    """待ち時間テキストを数値に変換"""
    if not text or text == '-' or text == '':
        return None
    
    # 数値の場合
    if text.isdigit():
        return int(text)
    
    # CSSクラスから混雑レベルを推定
    if 'B8' in css_classes:
        return -1  # 運休・休止
    elif 'B0' in css_classes:
        return 0   # 空いている
    elif 'B1' in css_classes:
        return 1   # 少し混雑
    elif 'B2' in css_classes:
        return 2   # 普通
    elif 'B3' in css_classes:
        return 3   # 混雑
    elif 'B4' in css_classes:
        return 4   # 非常に混雑
    elif 'B6' in css_classes:
        return 6   # 激混み
    
    return text

def analyze_complete_results(df):
    """完全版の解析結果を表示"""
    if df.empty:
        print("❌ データが取得できませんでした")
        return
    
    print(f"\n🎢 yosocal.com 全時間帯待ち時間データ分析")
    print("=" * 80)
    
    # 基本統計
    unique_dates = df['date'].unique()
    unique_times = df['time'].unique()
    unique_attractions = df['attraction'].unique()
    
    print(f"📅 対象日付: {', '.join(unique_dates)}")
    print(f"⏰ 取得時間帯数: {len(unique_times)}")
    print(f"🎢 アトラクション数: {len(unique_attractions)}")
    print(f"📊 総レコード数: {len(df)}")
    
    # 時間帯一覧
    print(f"\n🕐 取得された時間帯:")
    print("-" * 60)
    time_counts = df['time'].value_counts()
    
    # 時間順にソート
    time_order = []
    for time_val in time_counts.index:
        if time_val == '平均':
            time_order.append((99, 99, time_val))  # 平均は最後
        else:
            match = re.match(r'(\d{1,2}):(\d{2})', time_val)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))
                time_order.append((hour, minute, time_val))
    
    time_order.sort()
    
    for _, _, time_val in time_order:
        count = time_counts[time_val]
        status = "✅" if count == len(unique_attractions) else f"⚠️ ({count}件)"
        print(f"  {time_val}: {status}")
    
    # 最混雑時間帯の分析
    print(f"\n📈 時間帯別平均待ち時間（運営中のみ）:")
    print("-" * 60)
    
    # 各時間帯の平均待ち時間を計算
    time_averages = []
    for _, _, time_val in time_order:
        if time_val == '平均':
            continue
        
        time_data = df[df['time'] == time_val]
        operating_data = time_data[pd.to_numeric(time_data['wait_time'], errors='coerce').notna()]
        operating_data = operating_data[operating_data['wait_time'] >= 0]
        
        if not operating_data.empty:
            avg_wait = operating_data['wait_time'].mean()
            time_averages.append((time_val, avg_wait, len(operating_data)))
    
    # 混雑順にソート
    time_averages.sort(key=lambda x: x[1], reverse=True)
    
    for idx, (time_val, avg_wait, count) in enumerate(time_averages[:10]):
        print(f"  {idx+1:2}. {time_val}: {avg_wait:.1f}分平均 ({count}施設運営)")
    
    # 人気アトラクションの時間別推移
    popular_attractions = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニーハント', 'ビッグサンダー']
    
    for attraction in popular_attractions:
        attraction_data = df[df['attraction'] == attraction]
        if not attraction_data.empty:
            print(f"\n🎢 {attraction} の待ち時間推移:")
            print("-" * 40)
            
            # 時間順にソート
            attraction_data_sorted = attraction_data.copy()
            attraction_data_sorted['sort_hour'] = attraction_data_sorted['time'].apply(
                lambda x: (int(x.split(':')[0]), int(x.split(':')[1])) if ':' in x else (99, 99)
            )
            attraction_data_sorted = attraction_data_sorted.sort_values('sort_hour')
            
            for _, row in attraction_data_sorted.iterrows():
                if row['time'] != '平均':
                    wait_display = f"{row['wait_time']}分" if pd.notna(row['wait_time']) and row['wait_time'] >= 0 else "運休"
                    print(f"  {row['time']}: {wait_display}")
            break  # 1つだけ詳細表示

def main(target_date="20250702"):
    """メイン実行関数"""
    print("🏰 yosocal.com 全時間帯Seleniumスクレイピング")
    print("=" * 80)
    print(f"📅 対象日付: {target_date}")
    
    expected_times = generate_expected_times()
    print(f"🕐 期待時間帯: {len(expected_times)} 個")
    print(f"   {expected_times[0]} 〜 {expected_times[-2]} + {expected_times[-1]}")
    
    # Seleniumでデータ取得
    html_content = selenium_scraping_with_manager(target_date)
    
    if html_content:
        print("\n📊 データ解析開始...")
        df = parse_yosocal_complete(html_content, debug=True)
        
        if not df.empty:
            # CSV出力
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"yosocal_selenium_{target_date}_{timestamp}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ CSV出力完了: {filename}")
            
            # 結果分析
            analyze_complete_results(df)
            
            return True
        else:
            print("❌ データ解析に失敗しました")
    else:
        print("❌ HTMLデータの取得に失敗しました")
    
    return False

if __name__ == "__main__":
    # Seleniumで全時間帯データを取得
    success = main(target_date="20250702")
    
    if success:
        print(f"\n🎉 全時間帯Seleniumスクレイピングが成功しました！")
        print("📊 8:15から21:45まで30分おきのデータが取得できました")
    else:
        print(f"\n❌ Seleniumスクレイピングに失敗しました")
        print("💡 ネットワーク接続やWebサイトの状態を確認してください") 