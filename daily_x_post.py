#!/usr/bin/env python3
"""
X(Twitter)自動投稿スクリプト - 人気アトラクション絞り込み版
毎日20:00に翌日の待ち時間予測を投稿

機能:
- 人気アトラクションのみのヒートマップ生成
- 休止中アトラクションは-1表示
- シー・ランド両方を自動投稿
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトのルートディレクトリ
PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

# X投稿機能 — X Harness 経由（フォールバック: tweepy直接）
from post_via_xharness import post_to_twitter, check_connection as check_xharness

# ヒートマップ生成モジュール
from generate_x_heatmap import (
    generate_sea_heatmap, 
    generate_land_heatmap,
    get_sea_closures,
    get_land_closures,
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES
)


def get_day_of_week_ja(date_str):
    """日本語の曜日を取得"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    days = ['月', '火', '水', '木', '金', '土', '日']
    return days[date.weekday()]


def create_sea_tweet(date_str):
    """シー用ツイートテキストを生成"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = get_day_of_week_ja(date_str)
    
    # 休止情報
    closures = get_sea_closures(date_str)
    closed_count = len(closures)
    
    tweet = f"🌊 ディズニーシー AI待ち時間予測\n"
    tweet += f"📅 {dt.month}/{dt.day}({day_name})\n\n"
    
    # アトラクション数
    open_count = len(SEA_TARGET_ATTRACTIONS) - closed_count
    tweet += f"🎢 人気{open_count}アトラクションの終日予測\n"
    
    if closed_count > 0:
        closed_names = [SEA_DISPLAY_NAMES.get(a, a)[:6] for a in closures.keys()]
        tweet += f"❌ 休止: {', '.join(closed_names)}\n"
    
    tweet += "\n⏰ 緑=空いてる 赤=混んでる\n"
    tweet += "📱 スクショして活用してね！\n\n"
    tweet += "#TDS #ディズニーシー #待ち時間"
    
    return tweet


def create_land_tweet(date_str):
    """ランド用ツイートテキストを生成"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = get_day_of_week_ja(date_str)
    
    # 休止情報
    closures = get_land_closures(date_str)
    closed_count = len(closures)
    
    tweet = f"🏰 ディズニーランド AI待ち時間予測\n"
    tweet += f"📅 {dt.month}/{dt.day}({day_name})\n\n"
    
    # アトラクション数
    open_count = len(LAND_TARGET_ATTRACTIONS) - closed_count
    tweet += f"🎢 人気{open_count}アトラクションの終日予測\n"
    
    if closed_count > 0:
        closed_names = [LAND_DISPLAY_NAMES.get(a, a)[:6] for a in closures.keys()]
        tweet += f"❌ 休止: {', '.join(closed_names)}\n"
    
    tweet += "\n⏰ 緑=空いてる 赤=混んでる\n"
    tweet += "📱 スクショして活用してね！\n\n"
    tweet += "#TDL #ディズニーランド #待ち時間"
    
    return tweet


## post_to_twitter は post_via_xharness から import 済み


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='X自動投稿スクリプト - 人気アトラクション絞り込み版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 翌日の予測を投稿
  python daily_x_post.py --post
  
  # 特定日の予測を投稿
  python daily_x_post.py --date 2026-02-04 --post
  
  # ドライラン（投稿せずに確認）
  python daily_x_post.py --date 2026-02-04 --dry-run
  
  # シーのみ投稿
  python daily_x_post.py --post --sea-only
        """
    )
    
    # 翌日の日付をデフォルトに
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    parser.add_argument('--date', '-d', type=str, default=tomorrow,
                       help=f'予測日 (デフォルト: {tomorrow})')
    parser.add_argument('--post', '-p', action='store_true',
                       help='Xに投稿する')
    parser.add_argument('--dry-run', action='store_true',
                       help='投稿せずにツイート内容を表示')
    parser.add_argument('--sea-only', action='store_true',
                       help='シーのみ投稿')
    parser.add_argument('--land-only', action='store_true',
                       help='ランドのみ投稿')
    parser.add_argument('--output', '-o', type=str, default='predictions_x',
                       help='出力ディレクトリ (デフォルト: predictions_x)')
    
    args = parser.parse_args()
    date = args.date
    output_dir = args.output
    
    print("=" * 60)
    print("🎢 TDR AI待ち時間予測 - X自動投稿")
    print("   （人気アトラクション絞り込み版 / X Harness版）")
    print("=" * 60)
    print(f"📅 予測日: {date}")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if args.post and not args.dry_run:
        if not check_xharness():
            print("❌ 投稿先への接続に失敗しました。設定を確認してください。")
            return 1
    
    # ヒートマップ生成
    sea_image = None
    land_image = None
    
    if not args.land_only:
        print("\n🌊 ディズニーシー ヒートマップ生成中...")
        sea_image = generate_sea_heatmap(date, output_dir)
    
    if not args.sea_only:
        print("\n🏰 ディズニーランド ヒートマップ生成中...")
        land_image = generate_land_heatmap(date, output_dir)
    
    # ツイート作成
    sea_tweet = create_sea_tweet(date) if not args.land_only else None
    land_tweet = create_land_tweet(date) if not args.sea_only else None
    
    # ツイート内容表示
    if sea_tweet:
        print("\n" + "=" * 60)
        print("🌊 【ディズニーシー】ツイート内容:")
        print("-" * 60)
        print(sea_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(sea_tweet)}/280")
        if sea_image:
            print(f"🖼️  画像: {sea_image}")
    
    if land_tweet:
        print("\n" + "=" * 60)
        print("🏰 【ディズニーランド】ツイート内容:")
        print("-" * 60)
        print(land_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(land_tweet)}/280")
        if land_image:
            print(f"🖼️  画像: {land_image}")
    
    # X投稿
    if args.post and not args.dry_run:
        posted_count = 0
        
        # シー投稿
        if sea_tweet and sea_image:
            print("\n🌊 ディズニーシーを投稿中...")
            if post_to_twitter(sea_tweet, [sea_image]):
                posted_count += 1
            time.sleep(5)  # API制限対策
        
        # ランド投稿
        if land_tweet and land_image:
            print("\n🏰 ディズニーランドを投稿中...")
            if post_to_twitter(land_tweet, [land_image]):
                posted_count += 1
        
        print(f"\n✅ {posted_count}件の投稿が完了しました")
        
    elif args.dry_run:
        total = (1 if sea_tweet else 0) + (1 if land_tweet else 0)
        print(f"\n🔍 ドライラン: {total}件の投稿がスキップされました")
    else:
        print("\n💡 投稿するには --post オプションを追加してください")
    
    # 出力ファイル
    print("\n📁 生成ファイル:")
    if sea_image:
        print(f"   🌊 シー: {sea_image}")
    if land_image:
        print(f"   🏰 ランド: {land_image}")
    
    print("\n✅ 完了!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
