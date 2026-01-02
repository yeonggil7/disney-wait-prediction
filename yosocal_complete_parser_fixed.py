#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os

def parse_yosocal_complete_data(html_file_path):
    """保存されたHTMLから28時間帯の完全データを抽出"""
    
    print("🔧 28時間帯データ完全抽出開始")
    print("="*60)
    
    try:
        # HTMLファイル読み込み
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # jamat div を検索
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            print("❌ jamat div が見つかりません")
            return None
        
        # テーブル取得
        table = jamat_div.find('table')
        if not table:
            print("❌ jamat テーブルが見つかりません")
            return None
        
        print(f"✅ jamat テーブル発見")
        
        # 全行を取得
        rows = table.find_all('tr')
        print(f"📊 総行数: {len(rows)}")
        
        # データ抽出準備
        all_data = []
        time_slots = []
        attractions = []
        
        # アトラクション名取得（2行目のFPh2要素）
        attraction_row = None
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                attraction_row = row
                break
        
        if attraction_row:
            fph2_cells = attraction_row.find_all('td', class_='FPh2')
            for cell in fph2_cells:
                attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                attractions.append(attraction_name)
            print(f"🎯 アトラクション数: {len(attractions)}")
        
        # 時間データ行を検索
        time_data_rows = []
        for row in rows:
            # FPM または FPT クラスを持つセルをチェック
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
            if fpm_cell:
                time_text = fpm_cell.get_text(strip=True)
                if re.match(r'^\d{2}:\d{2}$', time_text):  # HH:MM 形式
                    time_data_rows.append((time_text, row))
                    time_slots.append(time_text)
            elif fpt_cell:
                time_text = fpt_cell.get_text(strip=True)
                if time_text == '平均':
                    time_data_rows.append((time_text, row))
                    time_slots.append(time_text)
        
        print(f"⏰ 検出時間帯数: {len(time_slots)}")
        print(f"📋 時間帯リスト: {time_slots[:5]}...{time_slots[-2:]}")
        
        # 各時間帯のデータ抽出
        for time_slot, row in time_data_rows:
            # データセル取得（B0-B8 クラスまたは数値データ）
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            
            # 日付取得（テーブルのタイトル行から）
            date_text = "7月2日"  # HTMLから抽出された日付
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    attraction = attractions[i]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    # 待ち時間データ解析
                    wait_time = None
                    status = "unknown"
                    
                    if cell_text == "-" or cell_text == "":
                        status = "no_data"
                    elif re.match(r'^\d+$', cell_text):
                        wait_time = float(cell_text)
                        status = "normal"
                    else:
                        status = "other"
                    
                    # データ記録
                    record = {
                        'date': date_text,
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'jamat table'
                    }
                    all_data.append(record)
        
        # DataFrame作成
        df = pd.DataFrame(all_data)
        
        # 統計出力
        print("\n📊 抽出結果サマリー")
        print("="*50)
        print(f"総レコード数: {len(df)}")
        print(f"時間帯数: {df['time'].nunique()}")
        print(f"アトラクション数: {df['attraction'].nunique()}")
        print(f"有効待ち時間データ: {df['wait_time'].notna().sum()}")
        
        # 時間帯別データ数
        print(f"\n⏰ 時間帯別データ数:")
        time_counts = df['time'].value_counts().sort_index()
        for time_slot, count in time_counts.items():
            print(f"  {time_slot}: {count}個")
        
        # サンプルデータ表示
        print(f"\n📝 サンプルデータ:")
        sample_data = df[df['wait_time'].notna()].head(10)
        for _, row in sample_data.iterrows():
            print(f"  {row['date']} {row['time']} {row['attraction']}: {row['wait_time']}分 ({row['status']})")
        
        # CSV保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"yosocal_complete_28times_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 CSVファイル保存: {csv_filename}")
        
        return df
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 保存されたHTMLファイルを解析
    html_file = "yosocal_july2_fixed_20250703_113545.html"
    
    if os.path.exists(html_file):
        print(f"📁 HTMLファイル読み込み: {html_file}")
        result_df = parse_yosocal_complete_data(html_file)
        
        if result_df is not None:
            print(f"\n🎉 解析完了！28時間帯データ抽出成功")
            print(f"最終結果: {len(result_df)} レコード")
        else:
            print(f"\n❌ 解析失敗")
    else:
        print(f"❌ HTMLファイルが見つかりません: {html_file}") 