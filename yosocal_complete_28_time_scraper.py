#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re

def extract_yosocal_complete_data():
    """yosocal.comから完全な28時間帯データを取得"""
    
    print("🚀 yosocal.com 完全28時間帯データ取得開始")
    print("="*60)
    
    try:
        # realtime.htmから最新データを取得
        url = "https://yosocal.com/realtime.htm"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"📡 {url} からデータ取得中...")
        response = requests.get(url, headers=headers)
        response.encoding = 'shift_jis'
        
        if response.status_code != 200:
            print(f"❌ HTTP エラー: {response.status_code}")
            return None
            
        # BeautifulSoupでパース
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # jamat div要素を探す
        jamat_div = soup.find('div', {'id': 'jamat'})
        if not jamat_div:
            print("❌ jamat div要素が見つかりません")
            return None
            
        print("✅ jamat div要素を発見")
        
        # テーブルを取得
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブルが見つかりません")
            return None
            
        # すべての行を取得
        rows = table.find_all('tr')
        print(f"📋 総行数: {len(rows)}")
        
        # FPMクラス（時間データ）を含む行を特定
        time_rows = []
        attraction_names = []
        
        # アトラクション名の行を特定
        for i, row in enumerate(rows):
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                print(f"📍 行{i}: アトラクション名行発見 - {len(fph2_cells)}個")
                attraction_names = [cell.get_text().strip() for cell in fph2_cells]
                break
        
        print(f"🎯 アトラクション数: {len(attraction_names)}")
        
        # 時間データ行を探す
        for i, row in enumerate(rows):
            fpm_cell = row.find('td', class_='FPM')
            if fpm_cell:
                time_text = fpm_cell.get_text().strip()
                print(f"📍 行{i}: 時間データ「{time_text}」")
                
                # 空白や無効データをスキップ
                if time_text and time_text != '　' and time_text != '':
                    # 時間パターンチェック（HH:MM形式）
                    if re.match(r'\d{1,2}:\d{2}', time_text) or time_text == '平均':
                        time_rows.append((i, time_text, row))
                        
        print(f"⏰ 有効時間帯数: {len(time_rows)}")
        
        # すべての時間データを表示
        print("\n📊 検出された時間帯:")
        for i, (row_idx, time_text, row) in enumerate(time_rows):
            print(f"  {i+1:2d}. {time_text}")
            
        # データ抽出処理
        all_data = []
        current_date = datetime.now().strftime('%m月%d日')
        
        for time_idx, (row_idx, time_text, row) in enumerate(time_rows):
            print(f"\n⏰ 処理中: {time_text}")
            
            # 各セルのデータを取得
            cells = row.find_all('td')
            data_start_idx = 1  # TIME列の次から開始
            
            # 天気列があるかチェック（rowspan属性）
            for cell in cells[1:3]:  # 最初の数列をチェック
                if cell.get('rowspan'):
                    data_start_idx = 2
                    print(f"  🌤️  天気列検出 - データ開始位置: {data_start_idx}")
                    break
            
            # アトラクションデータを抽出
            valid_data_count = 0
            for attraction_idx, attraction_name in enumerate(attraction_names):
                cell_idx = data_start_idx + attraction_idx
                
                if cell_idx < len(cells):
                    cell = cells[cell_idx]
                    wait_time_text = cell.get_text().strip()
                    css_classes = ' '.join(cell.get('class', []))
                    
                    # 待ち時間の解析
                    wait_time = None
                    status = 'no_data'
                    
                    if wait_time_text == '-':
                        status = 'no_data'
                    elif wait_time_text == '':
                        status = 'empty'
                    elif wait_time_text.isdigit():
                        wait_time = float(wait_time_text)
                        status = 'normal'
                        valid_data_count += 1
                    else:
                        status = 'unknown'
                    
                    # データレコード作成
                    record = {
                        'date': current_date,
                        'time': time_text,
                        'attraction': attraction_name,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': wait_time_text,
                        'data_source': 'realtime.htm完全版'
                    }
                    all_data.append(record)
            
            print(f"  ✅ 有効データ: {valid_data_count}件")
        
        # 結果をDataFrameに変換
        df = pd.DataFrame(all_data)
        
        # ファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'yosocal_complete_28times_{timestamp}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        # 統計情報
        print(f"\n📊 最終結果:")
        print(f"   ⏰ 時間帯数: {len(time_rows)}")
        print(f"   🎯 アトラクション数: {len(attraction_names)}")
        print(f"   📈 総レコード数: {len(df)}")
        print(f"   ✅ 有効データ数: {len(df[df['status'] == 'normal'])}")
        print(f"   💾 保存ファイル: {filename}")
        
        # 時間帯の詳細分析
        time_summary = df.groupby('time').agg({
            'attraction': 'count',
            'wait_time': lambda x: x.notna().sum()
        }).rename(columns={'attraction': '総データ', 'wait_time': '有効データ'})
        
        print(f"\n📋 時間帯別統計:")
        for time_slot, stats in time_summary.iterrows():
            print(f"   {time_slot}: {stats['有効データ']}/{stats['総データ']} 件")
            
        return df
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = extract_yosocal_complete_data()
    if result is not None:
        print("\n🎉 完全データ取得成功！")
    else:
        print("\n💥 データ取得失敗") 