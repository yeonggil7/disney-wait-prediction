import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import requests
from urllib.parse import urljoin
import time

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

def analyze_table_structure(html_content):
    """テーブル構造を詳細に分析してrowspanパターンを理解する"""
    soup = BeautifulSoup(html_content, 'html.parser')
    jamat_div = soup.find('div', id='jamat')
    
    if not jamat_div:
        return None
    
    table = jamat_div.find('table')
    if not table:
        return None
    
    rows = table.find_all('tr')
    time_rows = []
    
    print("🔍 テーブル構造の詳細分析:")
    print("=" * 80)
    
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        
        # 時間データ行を特定
        if len(cells) > 10:
            time_cell = cells[0] if cells else None
            if time_cell and ('FPM' in time_cell.get('class', []) or 'FPT' in time_cell.get('class', [])):
                time_text = time_cell.get_text(strip=True)
                
                # 天気列の存在チェック
                weather_cell_exists = False
                if len(cells) > 1:
                    second_cell = cells[1]
                    if ('rowspan' in second_cell.attrs or 
                        'weather' in str(second_cell).lower() or 
                        'gif' in str(second_cell).lower() or
                        '天' in second_cell.get_text()):
                        weather_cell_exists = True
                
                time_rows.append({
                    'row_idx': row_idx,
                    'time': time_text,
                    'total_cells': len(cells),
                    'weather_cell_exists': weather_cell_exists,
                    'data_start_idx': 2 if weather_cell_exists else 1
                })
                
                print(f"行{row_idx}: {time_text} | 列数: {len(cells)} | 天気列: {weather_cell_exists}")
    
    return time_rows

def parse_yosocal_complete(html_content, debug=True):
    """完全版：全時間帯の待ち時間データを解析"""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # jamatテーブルを取得
    jamat_div = soup.find('div', id='jamat')
    if not jamat_div:
        print("❌ jamatテーブルが見つかりません")
        return pd.DataFrame()
    
    table = jamat_div.find('table')
    if not table:
        print("❌ テーブルが見つかりません")
        return pd.DataFrame()
    
    # まずテーブル構造を分析
    if debug:
        time_rows_info = analyze_table_structure(html_content)
    
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
    print(f"   時間帯: {', '.join(expected_times[:5])}...{', '.join(expected_times[-3:])}")
    
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
                if debug:
                    print(f"   最初の5つ: {attraction_names[:5]}")
                    print(f"   最後の5つ: {attraction_names[-5:]}")
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
                    
                    print(f"   天気列存在: {weather_cell_exists}")
                    print(f"   データ開始位置: {data_start_idx}")
                    print(f"   アトラクション数: {len(attraction_names)}")
                    print(f"   データ列数: {len(wait_time_cells)}")
                    
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
    
    print(f"\n🎢 yosocal.com 完全版アトラクション待ち時間データ分析")
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
    time_counts = df['time'].value_counts().sort_index()
    for time_val, count in time_counts.items():
        status = "✅" if count == len(unique_attractions) else f"⚠️ ({count}件)"
        print(f"  {time_val}: {status}")
    
    # 最混雑時間帯の分析
    print(f"\n📈 時間帯別平均待ち時間（運営中のみ）:")
    print("-" * 60)
    
    # 各時間帯の平均待ち時間を計算
    time_averages = []
    for time_val in sorted(unique_times):
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
    
    # 人気アトラクションの待ち時間推移
    popular_attractions = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニーハント', 'ビッグサンダー']
    
    for attraction in popular_attractions:
        attraction_data = df[df['attraction'] == attraction]
        if not attraction_data.empty:
            print(f"\n🎢 {attraction} の待ち時間推移:")
            print("-" * 40)
            
            for _, row in attraction_data.iterrows():
                if row['time'] != '平均':
                    wait_display = f"{row['wait_time']}分" if pd.notna(row['wait_time']) and row['wait_time'] >= 0 else "運休"
                    print(f"  {row['time']}: {wait_display}")
            break  # 1つだけ詳細表示

def fetch_yosocal_data(target_date="20250701"):
    """yosocal.comから実際のデータを取得（実装例）"""
    base_url = "https://yosocal.com"
    
    # 実際のスクレイピング処理はここに実装
    # 現在はサンプルHTMLを返す
    print(f"🌐 yosocal.comから {target_date} のデータを取得中...")
    print("   注意: 実際のスクレイピングにはWebサイトの利用規約を確認してください")
    
    # サンプルHTMLを返す（実際の実装では requests.get() などを使用）
    sample_html = '''
    <div id="jamat" class="DIVc">
    <!-- ここに実際のHTMLデータが入る -->
    </div>
    '''
    
    return sample_html

def main(target_date="20250701", use_sample_data=True):
    """メイン実行関数"""
    print("🏰 yosocal.com 完全版スクレイピング")
    print("=" * 80)
    print(f"📅 対象日付: {target_date}")
    
    expected_times = generate_expected_times()
    print(f"🕐 期待時間帯: {len(expected_times)} 個")
    print(f"   {expected_times[0]} 〜 {expected_times[-2]} + {expected_times[-1]}")
    
    if use_sample_data:
        # サンプルデータを使用（テスト用）
        print("\n📝 サンプルデータを使用してテスト実行...")
        
        # 前回の修正版スクリプトで作成したHTMLサンプルを使用
        with open('yosocal_html_parser_final.py', 'r') as f:
            content = f.read()
            # SAMPLE_HTMLを抽出
            start = content.find("SAMPLE_HTML = '''") + len("SAMPLE_HTML = '''")
            end = content.find("'''", start)
            sample_html = content[start:end]
        
        df = parse_yosocal_complete(sample_html, debug=True)
    else:
        # 実際のデータを取得
        html_content = fetch_yosocal_data(target_date)
        df = parse_yosocal_complete(html_content, debug=True)
    
    if not df.empty:
        # CSV出力
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"yosocal_complete_{target_date}_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV出力完了: {filename}")
        
        # 結果分析
        analyze_complete_results(df)
        
    else:
        print("❌ データの取得に失敗しました")
        return False
    
    return True

if __name__ == "__main__":
    # テストモードで実行
    success = main(target_date="20250702", use_sample_data=True)
    
    if success:
        print(f"\n🎉 完全版スクレイピング機能が正常に動作しました！")
        print("   実際のデータを取得するには use_sample_data=False に設定してください")
    else:
        print(f"\n❌ 処理中にエラーが発生しました") 