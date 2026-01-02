#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
2025年1月〜5月全日分データ取得バッチスクリプト
修正版スクレイパーを使用して各月の全データを取得
"""

import os
import time
from datetime import datetime
from yosocal_realtime_scraper_fixed import scrape_yosocal_by_date

def batch_scrape_jan_may_2025():
    """
    2025年1月〜5月の全日分データを順次取得
    """
    print("🚀 2025年1月〜5月全日分データ取得開始")
    print("=" * 60)
    
    # 各月の日数定義
    months_data = [
        (1, 31),  # 1月: 31日
        (2, 28),  # 2月: 28日（2025年は平年）
        (3, 31),  # 3月: 31日
        (4, 30),  # 4月: 30日
        (5, 31),  # 5月: 31日
    ]
    
    # 取得済み確認
    already_exists = []
    total_target_days = 0
    
    for month, days in months_data:
        for day in range(1, days + 1):
            total_target_days += 1
            date_str = f"2025{month:02d}{day:02d}"
            csv_file = f"data/yosocal_{date_str}_fixed.csv"
            if os.path.exists(csv_file):
                already_exists.append((month, day))
    
    print(f"📊 総対象日数: {total_target_days}日")
    
    if already_exists:
        print(f"📁 取得済みファイル: {len(already_exists)}件")
        for month, day in already_exists[:10]:  # 最初の10件のみ表示
            print(f"  ✅ {month}月{day:02d}日")
        if len(already_exists) > 10:
            print(f"  ... 他{len(already_exists)-10}件")
        print()
    
    # 未取得日のみ処理
    remaining_days = []
    for month, days in months_data:
        for day in range(1, days + 1):
            if (month, day) not in already_exists:
                remaining_days.append((month, day))
    
    if not remaining_days:
        print("🎉 すべてのデータが既に取得済みです！")
        return
    
    print(f"📋 取得対象: {len(remaining_days)}日")
    print(f"📅 対象期間: 2025年1月〜5月（未取得分）")
    print()
    
    # データ取得開始
    success_count = 0
    error_count = 0
    current_month = None
    
    for i, (month, day) in enumerate(remaining_days, 1):
        # 月が変わったら表示
        if current_month != month:
            if current_month is not None:
                print(f"\n{'='*40}")
            current_month = month
            month_names = ["", "1月", "2月", "3月", "4月", "5月"]
            print(f"📅 {month_names[month]}処理開始")
            print(f"{'='*40}")
        
        date_str = f"2025{month:02d}{day:02d}"
        print(f"📅 進捗 {i}/{len(remaining_days)}: 2025年{month}月{day:02d}日 ({date_str})")
        
        try:
            # データ取得
            scrape_yosocal_by_date(date_str)
            
            # ファイル移動
            source_file = f"yosocal_{date_str}_fixed.csv"
            target_file = f"data/yosocal_{date_str}_fixed.csv"
            
            if os.path.exists(source_file):
                os.rename(source_file, target_file)
                print(f"✅ {month}月{day:02d}日: データ取得・移動完了")
                success_count += 1
            else:
                print(f"⚠️ {month}月{day:02d}日: CSVファイルが見つかりません")
                error_count += 1
            
        except Exception as e:
            print(f"❌ {month}月{day:02d}日: エラー - {e}")
            error_count += 1
        
        # 次の処理前に少し待機（サーバー負荷軽減）
        if i < len(remaining_days):
            print(f"⏳ 次の処理まで10秒待機...")
            time.sleep(10)
        
        print("-" * 30)
        
        # 10日ごとに進捗報告
        if i % 10 == 0 or i == len(remaining_days):
            print(f"\n📊 中間進捗報告 ({i}/{len(remaining_days)})")
            print(f"✅ 成功: {success_count}日")
            print(f"❌ エラー: {error_count}日")
            print(f"📈 成功率: {success_count/(success_count+error_count)*100:.1f}%")
            print()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 1月〜5月データ取得完了サマリー")
    print("=" * 60)
    print(f"✅ 成功: {success_count}日")
    print(f"❌ エラー: {error_count}日")
    print(f"📈 成功率: {success_count/(success_count+error_count)*100:.1f}%")
    
    # dataフォルダ内のファイル確認（月別）
    print(f"\n📁 dataフォルダ内のファイル確認:")
    total_files = 0
    
    for month, _ in months_data:
        month_files = []
        if os.path.exists("data"):
            pattern = f"yosocal_2025{month:02d}"
            for filename in sorted(os.listdir("data")):
                if filename.startswith(pattern) and filename.endswith("_fixed.csv"):
                    month_files.append(filename)
                    total_files += 1
        
        month_names = ["", "1月", "2月", "3月", "4月", "5月"]
        print(f"  📅 {month_names[month]}: {len(month_files)}ファイル")
    
    print(f"\n🎉 2025年1月〜5月: 合計{total_files}ファイル取得完了！")

if __name__ == "__main__":
    batch_scrape_jan_may_2025() 