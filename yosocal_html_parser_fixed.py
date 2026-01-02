import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re

# 提供されたHTMLサンプル（実際のデータ）
SAMPLE_HTML = '''
<div id="jamat" class="DIVc" style="display: block; background-color: rgb(255, 223, 223); border-color: rgb(208, 65, 95);">
<font color="red" style="font-size:14px"><b>各アトラクション名をクリックでアトラクション毎の日別待ち時間が表示されます</b></font>
<table bgcolor="#999999" border="0" cellspacing="1" cellpadding="0">
<tbody>
<tr><td colspan="45" class="TDBT">7月2日</td></tr>
<tr><td colspan="45">
<table width="100%" class="FXTABLE" bgcolor="#CCCCCC" border="0" cellspacing="4" cellpadding="0">
<tbody>
<tr style="height:25px">
<td class="BUSY6" style="font-size:large;border-radius:4px">S平均</td>
<td class="BUSY3" style="font-size:large;border-radius:4px">A平均</td>
<td class="BUSY2" style="font-size:large;border-radius:4px">B平均</td>
<td class="BUSY1" style="font-size:large;border-radius:4px">C平均</td>
<td class="BUSY4" style="font-size:large;border-radius:4px">G平均</td>
<td class="BUSY0" style="font-size:large;border-radius:4px">混雑指数</td>
</tr>
<tr style="height:25px">
<td class="BUSY0" style="font-size:large;border-radius:4px">24</td>
<td class="BUSY0" style="font-size:large;border-radius:4px">13</td>
<td class="BUSY0" style="font-size:large;border-radius:4px">6</td>
<td class="BUSY1" style="font-size:large;border-radius:4px">5</td>
<td class="BUSY0" style="font-size:large;border-radius:4px">16</td>
<td class="BUSY0" style="font-size:large;border-radius:4px">12</td>
</tr>
</tbody>
</table>
</td></tr>
<tr>
<td class="FPT" rowspan="2">TIME</td>
<td class="FPh" rowspan="2">天<br>気<br>・<br>気<br>温</td>
<td class="B1">C</td><td class="B2">B</td><td class="B1">C</td><td class="B3">A</td><td class="B0">-</td><td class="B0">-</td><td class="B6">S</td><td class="B1">C</td><td class="B0">-</td><td class="B0">-</td><td class="B1">C</td><td class="B6">S</td><td class="B2">B</td><td class="B2">B</td><td class="B6">S</td><td class="B3">A</td><td class="B1">C</td><td class="B1">C</td><td class="B2">B</td><td class="B2">B</td><td class="B3">A</td><td class="B2">B</td><td class="B2">B</td><td class="B3">A</td><td class="B2">B</td><td class="B1">C</td><td class="B0">-</td><td class="B0">-</td><td class="B1">C</td><td class="B3">A</td><td class="B3">A</td><td class="B6">S</td><td class="B6">S</td><td class="B6">S</td><td class="B6">S</td><td class="B3">A</td><td class="B3">A</td><td class="B4">G</td><td class="B4">G</td><td class="B4">G</td><td class="B4">G</td><td class="B4">G</td>
<td class="FPh" rowspan="2">平<br>均<br>待<br>ち<br>時<br>間</td>
</tr>
<tr>
<td class="FPh2" onclick="createAT2(1)" style="cursor:pointer;">オムニバス</td>
<td class="FPh2" onclick="createAT2(2)" style="cursor:pointer;">リバー鉄道</td>
<td class="FPh2" onclick="createAT2(3)" style="cursor:pointer;">カリブの海賊</td>
<td class="FPh2" onclick="createAT2(4)" style="cursor:pointer;">ジャングル</td>
<td class="FPh2" onclick="createAT2(5)" style="cursor:pointer;">ツリーハウス</td>
<td class="FPh2" onclick="createAT2(6)" style="cursor:pointer;">魅惑のチキルーム</td>
<td class="FPh2" onclick="createAT2(7)" style="cursor:pointer;">ビッグサンダー</td>
<td class="FPh2" onclick="createAT2(8)" style="cursor:pointer;">Sギャラリー</td>
<td class="FPh2" onclick="createAT2(9)" style="cursor:pointer;">ベア・シアター</td>
<td class="FPh2" onclick="createAT2(10)" style="cursor:pointer;">いかだ</td>
<td class="FPh2" onclick="createAT2(11)" style="cursor:pointer;">蒸気船</td>
<td class="FPh2" onclick="createAT2(12)" style="cursor:pointer;">スプラッシュ</td>
<td class="FPh2" onclick="createAT2(13)" style="cursor:pointer;">カヌー探検</td>
<td class="FPh2" onclick="createAT2(14)" style="cursor:pointer;">スモールワールド</td>
<td class="FPh2" onclick="createAT2(15)" style="cursor:pointer;">ハニーハント</td>
<td class="FPh2" onclick="createAT2(16)" style="cursor:pointer;">ホーンテッド</td>
<td class="FPh2" onclick="createAT2(17)" style="cursor:pointer;">アリス</td>
<td class="FPh2" onclick="createAT2(18)" style="cursor:pointer;">カルーセル</td>
<td class="FPh2" onclick="createAT2(19)" style="cursor:pointer;">シンデレラ</td>
<td class="FPh2" onclick="createAT2(20)" style="cursor:pointer;">ピノキオ</td>
<td class="FPh2" onclick="createAT2(21)" style="cursor:pointer;">ピーターパン</td>
<td class="FPh2" onclick="createAT2(22)" style="cursor:pointer;">フィルハー</td>
<td class="FPh2" onclick="createAT2(23)" style="cursor:pointer;">白雪姫</td>
<td class="FPh2" onclick="createAT2(24)" style="cursor:pointer;">空飛ぶダンボ</td>
<td class="FPh2" onclick="createAT2(25)" style="cursor:pointer;">ゴーコースター</td>
<td class="FPh2" onclick="createAT2(26)" style="cursor:pointer;">グーフィー</td>
<td class="FPh2" onclick="createAT2(27)" style="cursor:pointer;">CDツリーハウス</td>
<td class="FPh2" onclick="createAT2(28)" style="cursor:pointer;">ドナルドのボート</td>
<td class="FPh2" onclick="createAT2(29)" style="cursor:pointer;">ミニーの家</td>
<td class="FPh2" onclick="createAT2(30)" style="cursor:pointer;">カートゥーン</td>
<td class="FPh2" onclick="createAT2(31)" style="cursor:pointer;">スター・ツアーズ</td>
<td class="FPh2" onclick="createAT2(32)" style="cursor:pointer;">スペース</td>
<td class="FPh2" onclick="createAT2(33)" style="cursor:pointer;">バズライトイヤー</td>
<td class="FPh2" onclick="createAT2(34)" style="cursor:pointer;">モンイン</td>
<td class="FPh2" onclick="createAT2(35)" style="cursor:pointer;">美女と野獣</td>
<td class="FPh2" onclick="createAT2(36)" style="cursor:pointer;">ベイマックス</td>
<td class="FPh2" onclick="createAT2(37)" style="cursor:pointer;">スティッチENC</td>
<td class="FPh2" onclick="createAT2(38)" style="cursor:pointer;">ハウス前</td>
<td class="FPh2" onclick="createAT2(39)" style="cursor:pointer;">ドナルドグリ</td>
<td class="FPh2" onclick="createAT2(40)" style="cursor:pointer;">デイジーグリ</td>
<td class="FPh2" onclick="createAT2(41)" style="cursor:pointer;">ミニーグリ</td>
<td class="FPh2" onclick="createAT2(42)" style="cursor:pointer;">ミート・ミッキー</td>
</tr>
<tr>
<td class="FPM" height="14px">08:15</td>
<td class="B0" rowspan="2"><img width="20" height="14" src="w000.gif" title="天気"><br><font color="orangered">　</font></td>
<td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td>
<td class="B8"></td>
</tr>
<tr>
<td class="FPM" height="14px">09:15</td>
<td class="B8">-</td><td class="B8">-</td><td class="B0">5</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B1">10</td><td class="B0">5</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B1">15</td><td class="B8">-</td><td class="B8">-</td><td class="B0">8</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B8">-</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B8">-</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B3">50</td><td class="B3">60</td><td class="B8">-</td><td class="B8">-</td><td class="B0">5</td><td class="B0">5</td><td class="B1">15</td><td class="B1">10</td>
<td class="B0">10</td>
</tr>
<tr>
<td class="FPT">平均</td>
<td class="FPM"></td>
<td class="B0">9</td><td class="B0">8</td><td class="B0">5</td><td class="B0">5</td><td class="B8">-</td><td class="B1">10</td><td class="B1">14</td><td class="B0">5</td><td class="B1">15</td><td class="B0">5</td><td class="B0">9</td><td class="B2">25</td><td class="B8">-</td><td class="B8">-</td><td class="B2">24</td><td class="B0">7</td><td class="B0">5</td><td class="B0">5</td><td class="B0">6</td><td class="B0">5</td><td class="B1">19</td><td class="B0">5</td><td class="B1">10</td><td class="B1">16</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">5</td><td class="B0">8</td><td class="B0">6</td><td class="B8">-</td><td class="B8">-</td><td class="B8">-</td><td class="B3">35</td><td class="B3">35</td><td class="B1">10</td><td class="B8">-</td><td class="B1">18</td><td class="B1">11</td><td class="B2">20</td><td class="B1">17</td>
<td class="FPM"></td>
</tr>
</tbody>
</table>
</div>
'''

def debug_table_structure(html_content):
    """テーブル構造をデバッグして列位置を確認"""
    soup = BeautifulSoup(html_content, 'html.parser')
    jamat_div = soup.find('div', id='jamat')
    table = jamat_div.find('table')
    rows = table.find_all('tr')
    
    print("🔍 テーブル構造のデバッグ:")
    print("=" * 80)
    
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        print(f"\n行 {row_idx}: {len(cells)} 列")
        
        # 09:15の行を詳しく分析
        if len(cells) > 10:
            time_cell = cells[0] if cells else None
            if time_cell and time_cell.get_text(strip=True) == "09:15":
                print(f"📍 09:15 データ行の詳細分析:")
                for i, cell in enumerate(cells[:10]):  # 最初の10列を分析
                    cell_text = cell.get_text(strip=True)
                    cell_class = cell.get('class', [])
                    print(f"  列{i}: '{cell_text}' (class: {cell_class})")
                
                print(f"\n🎯 アトラクションデータの開始位置確認:")
                print(f"  列0: {cells[0].get_text(strip=True)} (TIME)")
                print(f"  列1: {cells[1].get_text(strip=True)} (天気・rowspan=2)")
                print(f"  列2: {cells[2].get_text(strip=True)} (オムニバス)")
                print(f"  列3: {cells[3].get_text(strip=True)} (リバー鉄道)")
                print(f"  列4: {cells[4].get_text(strip=True)} (カリブの海賊)")

def parse_yosocal_table_fixed(html_content):
    """修正版：天気・気温列を考慮してHTMLテーブルを解析"""
    
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
    
    # データを格納するリスト
    data = []
    
    # 行を取得
    rows = table.find_all('tr')
    
    # 変数の初期化
    current_date = ""
    attraction_names = []
    
    print(f"📊 {len(rows)} 行を解析中...")
    
    for row_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        
        # 日付行を検出
        if len(cells) == 1 and ('月' in cells[0].get_text() and '日' in cells[0].get_text()):
            current_date = cells[0].get_text(strip=True)
            print(f"📅 日付発見: {current_date}")
            continue
        
        # アトラクション名のヘッダー行を検出
        if len(cells) > 30:  # アトラクション名が多い行
            attraction_cells = [cell for cell in cells if 'FPh2' in cell.get('class', [])]
            if attraction_cells:
                attraction_names = [cell.get_text(strip=True) for cell in attraction_cells]
                print(f"🎢 {len(attraction_names)} 個のアトラクション名を取得")
                for i, name in enumerate(attraction_names[:10]):
                    print(f"  {i+1}: {name}")
                continue
        
        # 時間データ行を検出
        if len(cells) > 10 and attraction_names:
            time_cell = cells[0] if cells else None
            if time_cell and 'FPM' in time_cell.get('class', []):
                time_text = time_cell.get_text(strip=True)
                
                # 時間形式かチェック
                if re.match(r'\d{1,2}:\d{2}', time_text) or time_text == '平均':
                    print(f"⏰ 時間データ行: {time_text}")
                    
                    # 修正: アトラクションデータの開始位置
                    # 0: TIME列, 1: 天気・気温列 (rowspanで複数行にまたがる場合がある)
                    # 2: オムニバス (最初のアトラクション)
                    
                    # 天気列がrowspanの場合、09:15行には天気列が含まれない
                    # 構造を確認して適切な開始位置を決定
                    if time_text == "09:15":
                        # 09:15行は天気列が含まれないため、1列目からアトラクションデータ
                        data_start_idx = 1
                    else:
                        # 通常の行（08:15など）は天気列が含まれるため、2列目からアトラクションデータ
                        data_start_idx = 2
                    
                    wait_time_cells = cells[data_start_idx:]
                    
                    # 最後の列（平均列）は除く
                    if len(wait_time_cells) > len(attraction_names):
                        wait_time_cells = wait_time_cells[:-1]
                    
                    print(f"   データ開始位置: {data_start_idx}, アトラクション数: {len(attraction_names)}, データ列数: {len(wait_time_cells)}")
                    
                    for idx, (attraction_name, cell) in enumerate(zip(attraction_names, wait_time_cells)):
                        if idx >= len(wait_time_cells):
                            break
                        
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
    
    df = pd.DataFrame(data)
    print(f"📋 総 {len(df)} レコードを抽出")
    
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

def analyze_results(df):
    """解析結果を表示"""
    if df.empty:
        print("❌ データが取得できませんでした")
        return
    
    print(f"\n🎢 yosocal.com アトラクション待ち時間データ分析（修正版）")
    print("=" * 80)
    
    # 基本統計
    unique_dates = df['date'].unique()
    unique_times = df['time'].unique()
    unique_attractions = df['attraction'].unique()
    
    print(f"📅 対象日付: {', '.join(unique_dates)}")
    print(f"⏰ 時間帯数: {len(unique_times)}")
    print(f"🎢 アトラクション数: {len(unique_attractions)}")
    print(f"📊 総レコード数: {len(df)}")
    
    # 平均待ち時間データ
    avg_data = df[df['time'] == '平均']
    if not avg_data.empty:
        print(f"\n📈 平均待ち時間データ（上位10位）:")
        print("-" * 60)
        
        # 数値データのみでソート
        numeric_avg = avg_data[pd.to_numeric(avg_data['wait_time'], errors='coerce').notna()]
        numeric_avg = numeric_avg[numeric_avg['wait_time'] >= 0]
        
        if not numeric_avg.empty:
            numeric_avg_sorted = numeric_avg.sort_values('wait_time', ascending=False)
            for idx, (_, row) in enumerate(numeric_avg_sorted.head(10).iterrows()):
                print(f"  {idx+1:2}. {row['attraction']:<20}: {row['wait_time']:>3}分 ({row['raw_value']})")
    
    # 9:15の待ち時間データ
    time_915_data = df[df['time'] == '09:15']
    if not time_915_data.empty:
        print(f"\n🕘 09:15 の待ち時間（運営中のみ）:")
        print("-" * 60)
        
        operating_data = time_915_data[pd.to_numeric(time_915_data['wait_time'], errors='coerce').notna()]
        operating_data = operating_data[operating_data['wait_time'] >= 0]
        
        if not operating_data.empty:
            operating_sorted = operating_data.sort_values('wait_time', ascending=False)
            for idx, (_, row) in enumerate(operating_sorted.iterrows()):
                print(f"  {row['attraction']:<20}: {row['wait_time']:>3}分")

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com HTMLテーブル解析（修正版）")
    print("=" * 80)
    
    # まずテーブル構造をデバッグ
    debug_table_structure(SAMPLE_HTML)
    
    # 修正版で解析
    df = parse_yosocal_table_fixed(SAMPLE_HTML)
    
    if not df.empty:
        # CSV出力
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"yosocal_fixed_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ CSV出力完了: {filename}")
        
        # 結果分析
        analyze_results(df)
        
        # データサンプル表示
        print(f"\n📋 データサンプル（09:15の先頭10件）:")
        print("-" * 80)
        sample_915 = df[df['time'] == '09:15'].head(10)
        print(sample_915.to_string())
        
    else:
        print("❌ HTMLの解析に失敗しました")

if __name__ == "__main__":
    main() 