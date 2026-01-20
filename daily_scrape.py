#!/usr/bin/env python3
"""
毎日のデータスクレイピングスクリプト

yosocal.comから当月のディズニーシー・ランドの待ち時間データを取得

使用方法:
  python daily_scrape.py              # 当月のデータを取得
  python daily_scrape.py --sea-only   # シーのみ
  python daily_scrape.py --land-only  # ランドのみ
  python daily_scrape.py --year 2026 --month 1  # 特定の月を指定
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
import time

# プロジェクトディレクトリに移動
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

def log(message):
    """タイムスタンプ付きログ"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def scrape_disneysea(year, month):
    """ディズニーシーのデータをスクレイピング"""
    log(f"🌊 ディズニーシー {year}年{month}月 スクレイピング開始...")
    
    try:
        result = subprocess.run(
            ['python3', 'yosocal_disneysea_scraper.py', '--year', str(year), '--month', str(month)],
            capture_output=True,
            text=True,
            timeout=1800,  # 30分タイムアウト
            cwd=PROJECT_DIR
        )
        
        if result.returncode == 0:
            log("✅ シー スクレイピング成功")
            return True
        else:
            log(f"❌ シー スクレイピング失敗: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        log("❌ シー スクレイピング タイムアウト (30分)")
        return False
    except Exception as e:
        log(f"❌ シー スクレイピング エラー: {e}")
        return False

def scrape_disneyland(year, month):
    """ディズニーランドのデータをスクレイピング"""
    log(f"🏰 ディズニーランド {year}年{month}月 スクレイピング開始...")
    
    try:
        result = subprocess.run(
            ['python3', 'yosocal_disneyland_scraper_new.py', '--year', str(year), '--month', str(month)],
            capture_output=True,
            text=True,
            timeout=1800,  # 30分タイムアウト
            cwd=PROJECT_DIR
        )
        
        if result.returncode == 0:
            log("✅ ランド スクレイピング成功")
            return True
        else:
            log(f"❌ ランド スクレイピング失敗: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        log("❌ ランド スクレイピング タイムアウト (30分)")
        return False
    except Exception as e:
        log(f"❌ ランド スクレイピング エラー: {e}")
        return False

def check_data_status():
    """データの状態を確認"""
    log("📊 データ状態確認...")
    
    import glob
    
    # シー
    sea_files = glob.glob("Disneysea/disneysea_daily_*.csv")
    if sea_files:
        latest_sea = max(sea_files)
        log(f"   🌊 シー: {len(sea_files)}ファイル (最新: {os.path.basename(latest_sea)})")
    else:
        log("   🌊 シー: データなし")
    
    # ランド
    land_files = glob.glob("Disneyland/disneyland_daily_*.csv")
    if land_files:
        latest_land = max(land_files)
        log(f"   🏰 ランド: {len(land_files)}ファイル (最新: {os.path.basename(latest_land)})")
    else:
        log("   🏰 ランド: データなし")

def main():
    parser = argparse.ArgumentParser(description='TDR待ち時間データ スクレイピング')
    parser.add_argument('--sea-only', action='store_true', help='シーのみ取得')
    parser.add_argument('--land-only', action='store_true', help='ランドのみ取得')
    parser.add_argument('--year', type=int, default=None, help='対象年 (デフォルト: 当月)')
    parser.add_argument('--month', type=int, default=None, help='対象月 (デフォルト: 当月)')
    parser.add_argument('--status', action='store_true', help='データ状態確認のみ')
    
    args = parser.parse_args()
    
    # デフォルトは当月
    now = datetime.now()
    year = args.year or now.year
    month = args.month or now.month
    
    log("=" * 60)
    log("🎢 TDR待ち時間データ - 毎日スクレイピング")
    log(f"📅 対象: {year}年{month}月")
    log("=" * 60)
    
    if args.status:
        check_data_status()
        return
    
    # スクレイピング実行
    results = []
    
    if not args.land_only:
        sea_success = scrape_disneysea(year, month)
        results.append(('シー', sea_success))
        time.sleep(10)  # サーバー負荷軽減
    
    if not args.sea_only:
        land_success = scrape_disneyland(year, month)
        results.append(('ランド', land_success))
    
    # 結果サマリー
    log("")
    log("=" * 60)
    log("📋 スクレイピング結果サマリー")
    log("=" * 60)
    
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失敗"
        log(f"   {name}: {status}")
    
    check_data_status()
    
    # 全成功なら0、そうでなければ1
    all_success = all(success for _, success in results)
    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
