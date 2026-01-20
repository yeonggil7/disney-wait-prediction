#!/usr/bin/env python3
"""
毎日のモデル再学習スクリプト

機能:
1. 最新データでシー・ランドのモデルを再学習
2. モデルを保存
3. ログを出力

使用方法:
  python daily_train.py              # 両パーク再学習
  python daily_train.py --sea-only   # シーのみ
  python daily_train.py --land-only  # ランドのみ
  python daily_train.py --skip-scrape # スクレイピングをスキップ
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import subprocess

# プロジェクトディレクトリに移動
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

def log(message):
    """タイムスタンプ付きログ"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def scrape_latest_data():
    """
    最新データをスクレイピング（オプション）
    yosocal.comから昨日までのデータを取得
    """
    log("📥 最新データをスクレイピング中...")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # シー用スクレイパー
    try:
        log("🌊 ディズニーシーのデータ取得中...")
        # ここではスクレイピングは複雑なので、手動で実行することを推奨
        # subprocess.run(['python3', 'yosocal_disneysea_scraper.py', '--date', yesterday], check=True)
        log("   → スクレイピングは手動で実行してください")
    except Exception as e:
        log(f"   ⚠️ シースクレイピングエラー: {e}")
    
    # ランド用スクレイパー
    try:
        log("🏰 ディズニーランドのデータ取得中...")
        # subprocess.run(['python3', 'yosocal_disneyland_scraper.py', '--date', yesterday], check=True)
        log("   → スクレイピングは手動で実行してください")
    except Exception as e:
        log(f"   ⚠️ ランドスクレイピングエラー: {e}")

def train_sea_model():
    """ディズニーシーモデルを再学習"""
    log("🌊 ディズニーシーモデル再学習開始...")
    
    try:
        from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
        
        predictor = DisneySeaWaitTimePredictorV3()
        
        # データ読み込み
        df = predictor.load_data()
        if df is None:
            log("❌ シーのデータがありません")
            return False
        
        log(f"   📊 データ件数: {len(df):,}件")
        
        # 学習実行
        success = predictor.train(df)
        
        if success:
            log("✅ シーモデル再学習完了")
            return True
        else:
            log("❌ シーモデル再学習失敗")
            return False
            
    except Exception as e:
        log(f"❌ シーモデルエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def train_land_model():
    """ディズニーランドモデルを再学習"""
    log("🏰 ディズニーランドモデル再学習開始...")
    
    try:
        from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
        
        predictor = DisneyLandWaitTimePredictorV3()
        
        # データ読み込み
        df = predictor.load_data()
        if df is None:
            log("❌ ランドのデータがありません")
            return False
        
        log(f"   📊 データ件数: {len(df):,}件")
        
        # 学習実行
        success = predictor.train(df)
        
        if success:
            log("✅ ランドモデル再学習完了")
            return True
        else:
            log("❌ ランドモデル再学習失敗")
            return False
            
    except Exception as e:
        log(f"❌ ランドモデルエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_model_info():
    """モデル情報を表示"""
    log("📊 モデル情報:")
    
    import joblib
    
    # シー
    try:
        config = joblib.load('models_v3/model_config.joblib')
        latest_date = config.get('latest_training_date', 'unknown')
        if hasattr(latest_date, 'strftime'):
            latest_date = latest_date.strftime('%Y-%m-%d')
        log(f"   🌊 シー: 最終学習日 {latest_date}")
    except:
        log("   🌊 シー: 情報取得失敗")
    
    # ランド
    try:
        config = joblib.load('models_land_v3/model_config.joblib')
        latest_date = config.get('latest_training_date', 'unknown')
        if hasattr(latest_date, 'strftime'):
            latest_date = latest_date.strftime('%Y-%m-%d')
        log(f"   🏰 ランド: 最終学習日 {latest_date}")
    except:
        log("   🏰 ランド: 情報取得失敗")

def main():
    parser = argparse.ArgumentParser(description='TDR待ち時間予測モデル再学習')
    parser.add_argument('--sea-only', action='store_true', help='シーのみ再学習')
    parser.add_argument('--land-only', action='store_true', help='ランドのみ再学習')
    parser.add_argument('--skip-scrape', action='store_true', help='スクレイピングをスキップ')
    parser.add_argument('--info', action='store_true', help='モデル情報のみ表示')
    
    args = parser.parse_args()
    
    log("=" * 60)
    log("🎢 TDR待ち時間予測モデル - 毎日再学習")
    log("=" * 60)
    
    if args.info:
        get_model_info()
        return
    
    # スクレイピング（オプション）
    if not args.skip_scrape:
        scrape_latest_data()
    
    # 再学習
    results = []
    
    if not args.land_only:
        sea_success = train_sea_model()
        results.append(('シー', sea_success))
    
    if not args.sea_only:
        land_success = train_land_model()
        results.append(('ランド', land_success))
    
    # 結果サマリー
    log("")
    log("=" * 60)
    log("📋 再学習結果サマリー")
    log("=" * 60)
    
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失敗"
        log(f"   {name}: {status}")
    
    get_model_info()
    
    # 全成功なら0、そうでなければ1
    all_success = all(success for _, success in results)
    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
