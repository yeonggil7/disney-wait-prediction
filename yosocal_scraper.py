import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import time

def scrape_yosocal_table():
    """yosocal.comの詳細アトラクション待ち時間テーブルを取得"""
    
    url = "https://yosocal.com/realtime.htm"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("🌐 yosocal.comからデータを取得中...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # jamatテーブルを探す
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamatテーブルが見つかりません")
            return pd.DataFrame()
        
        print("✅ jamatテーブルを発見")
        
        # テーブル要素を取得
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブル要素が見つかりません")
            return pd.DataFrame()
        
        # 全ての行を取得
        rows = table.find_all('tr')
        print(f"📊 {len(rows)} 行のデータを発見")
        
        data = []
        current_date = ""
        attraction_names = []
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            
            # 日付行を検出（「○月○日」の形式）
            if len(cells) == 1 and '月' in cells[0].get_text() and '日' in cells[0].get_text():
                current_date = cells[0].get_text(strip=True)
                print(f"📅 日付発見: {current_date}")
                continue
            
            # アトラクション名のヘッダー行を検出
            if len(cells) > 40:  # アトラクション数が多い行
                # FPh2クラスを持つセルからアトラクション名を抽出
                attraction_cells = [cell for cell in cells if 'FPh2' in cell.get('class', [])]
                if attraction_cells:
                    attraction_names = [cell.get_text(strip=True).replace('｜', '') for cell in attraction_cells]
                    print(f"🎢 {len(attraction_names)} 個のアトラクション名を取得")
                    continue
            
            # 時間データ行を検出
            if len(cells) > 10 and attraction_names:
                time_cell = cells[0] if cells else None
                if time_cell and 'FPM' in time_cell.get('class', []):
                    time_text = time_cell.get_text(strip=True)
                    
                    # 時間形式かチェック（HH:MM形式）
                    if re.match(r'\d{1,2}:\d{2}', time_text):
                        print(f"⏰ 時間データ行: {time_text}")
                        
                        # 各アトラクションの待ち時間データを抽出
                        wait_time_cells = cells[2:]  # 最初の2列（時間、天気）をスキップ
                        
                        for idx, (attraction_name, cell) in enumerate(zip(attraction_names, wait_time_cells)):
                            if idx >= len(wait_time_cells):
                                break
                            
                            wait_text = cell.get_text(strip=True)
                            class_names = cell.get('class', [])
                            
                            # 待ち時間の数値変換
                            wait_time = parse_wait_time_value(wait_text, class_names)
                            
                            data.append({
                                'date': current_date,
                                'time': time_text,
                                'attraction': attraction_name,
                                'wait_time': wait_time,
                                'raw_value': wait_text,
                                'css_class': ' '.join(class_names),
                                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
            
            # 平均行を検出
            if len(cells) > 10 and any('平均' in cell.get_text() for cell in cells[:2]):
                print("📈 平均データ行を発見")
                
                wait_time_cells = cells[2:]  # 最初の2列をスキップ
                
                for idx, (attraction_name, cell) in enumerate(zip(attraction_names, wait_time_cells)):
                    if idx >= len(wait_time_cells):
                        break
                    
                    wait_text = cell.get_text(strip=True)
                    class_names = cell.get('class', [])
                    
                    wait_time = parse_wait_time_value(wait_text, class_names)
                    
                    data.append({
                        'date': current_date,
                        'time': '平均',
                        'attraction': attraction_name,
                        'wait_time': wait_time,
                        'raw_value': wait_text,
                        'css_class': ' '.join(class_names),
                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        df = pd.DataFrame(data)
        print(f"📋 総 {len(df)} レコードを取得")
        
        return df
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return pd.DataFrame()

def parse_wait_time_value(text, css_classes):
    """待ち時間の値を解析"""
    if not text or text == '-' or text == '':
        return None
    
    # 数値の場合
    if text.isdigit():
        return int(text)
    
    # CSSクラスから待ち時間ランクを推定
    if 'B8' in css_classes:
        return -1  # 運休・休止など
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
    
    # その他のテキスト
    return text

def display_results(df):
    """結果を詳細表示"""
    if df.empty:
        print("❌ データが取得できませんでした")
        return
    
    print("\n🎢 yosocal.com アトラクション待ち時間データ")
    print("=" * 80)
    
    # 基本統計
    unique_dates = df['date'].unique()
    unique_times = df['time'].unique()
    unique_attractions = df['attraction'].unique()
    
    print(f"📅 対象日付: {', '.join(unique_dates)}")
    print(f"⏰ 時間帯数: {len(unique_times)}")
    print(f"🎢 アトラクション数: {len(unique_attractions)}")
    print(f"📊 総レコード数: {len(df)}")
    
    # 平均待ち時間データを表示
    avg_data = df[df['time'] == '平均']
    if not avg_data.empty:
        print(f"\n📈 平均待ち時間データ:")
        print("-" * 60)
        for _, row in avg_data.iterrows():
            if pd.notna(row['wait_time']) and row['wait_time'] != -1:
                print(f"  {row['attraction']:<20}: {row['wait_time']} ({row['raw_value']})")
    
    # 数値データのある待ち時間の統計
    numeric_data = df[pd.to_numeric(df['wait_time'], errors='coerce').notna()]
    numeric_data = numeric_data[numeric_data['wait_time'] >= 0]
    
    if not numeric_data.empty:
        numeric_values = pd.to_numeric(numeric_data['wait_time'])
        print(f"\n📊 数値待ち時間統計:")
        print("-" * 40)
        print(f"  最大待ち時間: {numeric_values.max()}")
        print(f"  最小待ち時間: {numeric_values.min()}")
        print(f"  平均待ち時間: {numeric_values.mean():.1f}")
    
    # 時間帯別データのサンプル表示
    sample_time = [t for t in unique_times if t != '平均'][:1]
    if sample_time:
        sample_data = df[df['time'] == sample_time[0]]
        print(f"\n🕐 {sample_time[0]} の待ち時間:")
        print("-" * 60)
        for _, row in sample_data.head(10).iterrows():
            print(f"  {row['attraction']:<20}: {row['raw_value']}")

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com アトラクション待ち時間スクレイピング開始")
    print("=" * 80)
    
    # データ取得
    df = scrape_yosocal_table()
    
    if not df.empty:
        # CSV出力
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"yosocal_detailed_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ CSV出力完了: {filename}")
        
        # 結果表示
        display_results(df)
        
        # データフレームの先頭を表示
        print(f"\n📋 データサンプル（先頭10件）:")
        print("-" * 80)
        print(df.head(10).to_string())
        
    else:
        print("❌ データ取得に失敗しました")

if __name__ == "__main__":
    main() 