import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import random

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

def generate_demo_html():
    """全時間帯のデモHTMLデータを生成"""
    
    # アトラクション名一覧
    attractions = [
        'オムニバス', 'リバー鉄道', 'カリブの海賊', 'ジャングル', 'ツリーハウス', '魅惑のチキルーム',
        'ビッグサンダー', 'Sギャラリー', 'ベア・シアター', 'いかだ', '蒸気船', 'スプラッシュ',
        'カヌー探検', 'スモールワールド', 'ハニーハント', 'ホーンテッド', 'アリス', 'カルーセル',
        'シンデレラ', 'ピノキオ', 'ピーターパン', 'フィルハー', '白雪姫', '空飛ぶダンボ',
        'ゴーコースター', 'グーフィー', 'CDツリーハウス', 'ドナルドのボート', 'ミニーの家', 'カートゥーン',
        'スター・ツアーズ', 'スペース', 'バズライトイヤー', 'モンイン', '美女と野獣', 'ベイマックス',
        'スティッチENC', 'ハウス前', 'ドナルドグリ', 'デイジーグリ', 'ミニーグリ', 'ミート・ミッキー'
    ]
    
    time_slots = generate_expected_times()[:-1]  # 平均を除く
    
    def generate_wait_times(time_str):
        """時間帯に応じた待ち時間を生成"""
        hour = int(time_str.split(':')[0])
        minute = int(time_str.split(':')[1])
        
        # 時間帯による混雑度の変化を模擬
        if 8 <= hour <= 9:  # 開園直後
            base_wait = 5
        elif 10 <= hour <= 11:  # 午前中
            base_wait = 15
        elif 12 <= hour <= 14:  # ランチタイム
            base_wait = 25
        elif 15 <= hour <= 17:  # 午後のピーク
            base_wait = 35
        elif 18 <= hour <= 19:  # 夕方
            base_wait = 30
        else:  # 夜間
            base_wait = 20
        
        wait_times = []
        for attraction in attractions:
            # 人気アトラクションは待ち時間が長い
            if attraction in ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ハニーハント', 'ビッグサンダー']:
                multiplier = random.uniform(1.5, 3.0)
            elif attraction in ['ピーターパン', 'ホーンテッド', 'スペース']:
                multiplier = random.uniform(1.2, 2.0)
            else:
                multiplier = random.uniform(0.3, 1.5)
            
            # 一部のアトラクションは運休
            if random.random() < 0.1:  # 10%の確率で運休
                wait_times.append('-')
            else:
                wait = max(0, int(base_wait * multiplier))
                wait_times.append(str(wait))
        
        return wait_times
    
    def generate_average_times():
        """平均待ち時間を生成"""
        avg_times = []
        for attraction in attractions:
            if attraction in ['美女と野獣', 'ベイマックス']:
                avg = random.randint(40, 60)
            elif attraction in ['スプラッシュ', 'ハニーハント', 'ビッグサンダー']:
                avg = random.randint(25, 40)
            elif attraction in ['ピーターパン', 'ホーンテッド', 'スペース']:
                avg = random.randint(15, 30)
            else:
                if random.random() < 0.1:  # 10%の確率で運休
                    avg_times.append('-')
                    continue
                avg = random.randint(5, 20)
            avg_times.append(str(avg))
        return avg_times
    
    # HTMLヘッダー部分
    html_parts = [
        '<div id="jamat" class="DIVc" style="display: block; background-color: rgb(255, 223, 223); border-color: rgb(208, 65, 95);">',
        '<font color="red" style="font-size:14px"><b>各アトラクション名をクリックでアトラクション毎の日別待ち時間が表示されます</b></font>',
        '<table bgcolor="#999999" border="0" cellspacing="1" cellpadding="0">',
        '<tbody>',
        '<tr><td colspan="45" class="TDBT">7月2日</td></tr>',
        '<tr><td colspan="45">',
        '<table width="100%" class="FXTABLE" bgcolor="#CCCCCC" border="0" cellspacing="4" cellpadding="0">',
        '<tbody>',
        '<tr style="height:25px">',
        '<td class="BUSY6" style="font-size:large;border-radius:4px">S平均</td>',
        '<td class="BUSY3" style="font-size:large;border-radius:4px">A平均</td>',
        '<td class="BUSY2" style="font-size:large;border-radius:4px">B平均</td>',
        '<td class="BUSY1" style="font-size:large;border-radius:4px">C平均</td>',
        '<td class="BUSY4" style="font-size:large;border-radius:4px">G平均</td>',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">混雑指数</td>',
        '</tr>',
        '<tr style="height:25px">',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">24</td>',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">13</td>',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">6</td>',
        '<td class="BUSY1" style="font-size:large;border-radius:4px">5</td>',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">16</td>',
        '<td class="BUSY0" style="font-size:large;border-radius:4px">12</td>',
        '</tr>',
        '</tbody>',
        '</table>',
        '</td></tr>',
        '<tr>',
        '<td class="FPT" rowspan="2">TIME</td>',
        '<td class="FPh" rowspan="2">天<br>気<br>・<br>気<br>温</td>'
    ]
    
    # 混雑レベルヘッダー行
    header_classes = ['B1', 'B2', 'B1', 'B3', 'B0', 'B0', 'B6', 'B1', 'B0', 'B0', 'B1', 'B6', 'B2', 'B2', 'B6', 'B3', 'B1', 'B1', 'B2', 'B2', 'B3', 'B2', 'B2', 'B3', 'B2', 'B1', 'B0', 'B0', 'B1', 'B3', 'B3', 'B6', 'B6', 'B6', 'B6', 'B3', 'B3', 'B4', 'B4', 'B4', 'B4', 'B4']
    header_values = ['C', 'B', 'C', 'A', '-', '-', 'S', 'C', '-', '-', 'C', 'S', 'B', 'B', 'S', 'A', 'C', 'C', 'B', 'B', 'A', 'B', 'B', 'A', 'B', 'C', '-', '-', 'C', 'A', 'A', 'S', 'S', 'S', 'S', 'A', 'A', 'G', 'G', 'G', 'G', 'G']
    
    for i, (cls, val) in enumerate(zip(header_classes, header_values)):
        html_parts.append(f'<td class="{cls}">{val}</td>')
    
    html_parts.append('<td class="FPh" rowspan="2">平<br>均<br>待<br>ち<br>時<br>間</td>')
    html_parts.append('</tr>')
    html_parts.append('<tr>')
    
    # アトラクション名ヘッダー行
    for i, attraction in enumerate(attractions, 1):
        html_parts.append(f'<td class="FPh2" onclick="createAT2({i})" style="cursor:pointer;">{attraction}</td>')
    
    html_parts.append('</tr>')
    
    # 各時間帯のデータ行
    weather_rowspan_count = 0
    for i, time_slot in enumerate(time_slots):
        wait_times = generate_wait_times(time_slot)
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="FPM" height="14px">{time_slot}</td>')
        
        # 天気列は数時間おきにrowspanで表示
        if weather_rowspan_count == 0:
            # 新しい天気セルを追加（次の3-5時間分をカバー）
            rowspan = random.randint(3, 5)
            weather_rowspan_count = rowspan
            html_parts.append(f'<td class="B0" rowspan="{rowspan}"><img width="20" height="14" src="w000.gif" title="天気"><br><font color="orangered">　</font></td>')
        
        weather_rowspan_count -= 1
        
        # 待ち時間データ
        for wait in wait_times:
            if wait == '-':
                html_parts.append('<td class="B8">-</td>')
            else:
                wait_val = int(wait)
                if wait_val == 0:
                    css_class = 'B8'
                elif wait_val <= 5:
                    css_class = 'B0'
                elif wait_val <= 15:
                    css_class = 'B1'
                elif wait_val <= 30:
                    css_class = 'B2'
                elif wait_val <= 45:
                    css_class = 'B3'
                else:
                    css_class = 'B6'
                
                html_parts.append(f'<td class="{css_class}">{wait}</td>')
        
        # 平均列
        avg_wait = random.randint(10, 25)
        html_parts.append(f'<td class="B0">{avg_wait}</td>')
        html_parts.append('</tr>')
    
    # 平均行
    avg_times = generate_average_times()
    html_parts.append('<tr>')
    html_parts.append('<td class="FPT">平均</td>')
    html_parts.append('<td class="FPM"></td>')
    
    for avg in avg_times:
        if avg == '-':
            html_parts.append('<td class="B8">-</td>')
        else:
            avg_val = int(avg)
            if avg_val <= 5:
                css_class = 'B0'
            elif avg_val <= 15:
                css_class = 'B1'
            elif avg_val <= 30:
                css_class = 'B2'
            elif avg_val <= 45:
                css_class = 'B3'
            else:
                css_class = 'B6'
            
            html_parts.append(f'<td class="{css_class}">{avg}</td>')
    
    html_parts.append('<td class="FPM"></td>')
    html_parts.append('</tr>')
    
    # HTMLフッター
    html_parts.extend([
        '</tbody>',
        '</table>',
        '</div>'
    ])
    
    return '\n'.join(html_parts)

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
    
    print(f"\n🎢 yosocal.com 全時間帯待ち時間データ分析（デモ版）")
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

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com 全時間帯スクレイピング（デモ版）")
    print("=" * 80)
    
    expected_times = generate_expected_times()
    print(f"🕐 期待時間帯: {len(expected_times)} 個")
    print(f"   {expected_times[0]} 〜 {expected_times[-2]} + {expected_times[-1]}")
    
    print("\n📝 全時間帯デモHTMLを生成中...")
    demo_html = generate_demo_html()
    
    print("📊 データ解析開始...")
    df = parse_yosocal_complete(demo_html, debug=True)
    
    if not df.empty:
        # CSV出力
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"yosocal_demo_complete_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV出力完了: {filename}")
        
        # 結果分析
        analyze_complete_results(df)
        
        return True
    else:
        print("❌ データ解析に失敗しました")
        return False

if __name__ == "__main__":
    # デモ版で全時間帯データを生成・解析
    success = main()
    
    if success:
        print(f"\n🎉 全時間帯デモスクレイピングが成功しました！")
        print("📊 8:15から21:45まで30分おきの全データが生成されました")
        print("💡 実際のWebサイトと同じ形式で28時間帯 + 平均のデータセットです")
    else:
        print(f"\n❌ デモスクレイピングに失敗しました") 