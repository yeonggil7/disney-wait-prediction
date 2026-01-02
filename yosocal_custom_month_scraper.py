#!/usr/bin/env python3
"""
yosocal.com カスタム月間データ取得システム
任意の年月を指定してディズニーランド待ち時間データを一括取得
"""

import sys
import argparse
from yosocal_monthly_batch_scraper import YosocalMonthlyBatchScraper

def main():
    """メイン実行関数 - カスタム年月指定対応"""
    parser = argparse.ArgumentParser(
        description='yosocal.com カスタム月間データ取得システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python3 yosocal_custom_month_scraper.py --year 2025 --month 6   # 2025年6月
  python3 yosocal_custom_month_scraper.py --year 2025 --month 7   # 2025年7月
  python3 yosocal_custom_month_scraper.py                         # デフォルト: 2025年6月
        """
    )
    
    parser.add_argument(
        '--year', 
        type=int, 
        default=2025,
        help='取得したい年 (default: 2025)'
    )
    
    parser.add_argument(
        '--month', 
        type=int, 
        default=6,
        choices=range(1, 13),
        help='取得したい月 1-12 (default: 6)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='詳細ログを表示'
    )
    
    args = parser.parse_args()
    
    print("🏰 yosocal.com カスタム月間データ取得システム")
    print("=" * 70)
    print(f"🎯 取得対象: {args.year}年{args.month}月")
    
    if args.verbose:
        print("📋 処理概要:")
        print("  1. 指定月のカレンダーに移動")
        print("  2. 利用可能な全日付を検出")
        print("  3. 各日付のデータを順次取得")
        print("  4. 日別・月別でデータを保存")
        print("  5. 統計情報を生成")
    
    # 月名表示
    month_names = {
        1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
        7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
    }
    
    print(f"📅 対象月: {month_names.get(args.month, '')} ({args.month}月)")
    
    try:
        scraper = YosocalMonthlyBatchScraper()
        
        # カスタム年月でデータ取得
        success = scraper.scrape_monthly_data(args.year, args.month)
        
        if success:
            print(f"\n🎉 {args.year}年{args.month}月 一括取得完了！")
            print("💾 保存先: dataフォルダ")
            print("📋 生成ファイル:")
            print("  • 日別CSVファイル (yosocal_daily_YYYY-MM-DD.csv)")
            print("  • 月間統合CSVファイル (yosocal_monthly_YYYY_MM_timestamp.csv)")
            print("  • 統計情報JSONファイル (yosocal_monthly_stats_YYYY_MM_timestamp.json)")
        else:
            print(f"\n❌ {args.year}年{args.month}月 データ取得に失敗しました")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 