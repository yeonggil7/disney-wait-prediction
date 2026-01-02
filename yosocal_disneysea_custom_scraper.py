#!/usr/bin/env python3
"""
yosocal.com ディズニーシー カスタム月間データ取得システム
コマンドラインから任意の年月を指定してディズニーシーのデータを取得
"""

import argparse
import sys
import os
from datetime import datetime
from yosocal_disneysea_scraper import YosocalDisneyseaScraper

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description='🏰 yosocal.com ディズニーシー カスタム月間データ取得システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎢 使用例:
  # 2025年6月のデータを取得
  python3 yosocal_disneysea_custom_scraper.py --year 2025 --month 6
  
  # 2025年7月のデータを詳細ログ付きで取得
  python3 yosocal_disneysea_custom_scraper.py --year 2025 --month 7 --verbose
  
  # 2024年12月のデータを取得
  python3 yosocal_disneysea_custom_scraper.py --year 2024 --month 12
  
  # デフォルト設定（2025年6月）で取得
  python3 yosocal_disneysea_custom_scraper.py

🎯 対象パーク: ディズニーシー
💾 保存先: Disneysea/フォルダ
📋 取得データ: 待ち時間・アトラクション・時間帯別データ
        """
    )
    
    parser.add_argument(
        '--year', 
        type=int, 
        default=2025,
        help='📅 取得したい年 (default: 2025)'
    )
    
    parser.add_argument(
        '--month', 
        type=int, 
        default=6,
        choices=range(1, 13),
        help='📅 取得したい月 1-12 (default: 6)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='📋 詳細ログを表示'
    )
    
    parser.add_argument(
        '--park',
        type=str,
        default='disneysea',
        choices=['disneysea', 'sea'],
        help='🏰 パーク選択 (default: disneysea)'
    )
    
    args = parser.parse_args()
    
    # 和暦月名
    month_names = {
        1: "睦月", 2: "如月", 3: "弥生", 4: "卯月", 5: "皐月", 6: "水無月",
        7: "文月", 8: "葉月", 9: "長月", 10: "神無月", 11: "霜月", 12: "師走"
    }
    
    # 季節の絵文字
    season_emojis = {
        1: "❄️", 2: "❄️", 3: "🌸", 4: "🌸", 5: "🌿", 6: "🌿",
        7: "🌻", 8: "🌻", 9: "🍂", 10: "🍂", 11: "🍁", 12: "⛄"
    }
    
    print("🏰 yosocal.com ディズニーシー カスタム月間データ取得システム")
    print("=" * 80)
    print(f"🎯 取得対象: {args.year}年{args.month}月 ({month_names.get(args.month, '')})")
    print(f"🎢 対象パーク: 🌊 東京ディズニーシー")
    print(f"💾 保存先: Disneysea/フォルダ")
    print(f"{season_emojis.get(args.month, '📅')} 季節: {month_names.get(args.month, '')}")
    
    if args.verbose:
        print("\n📋 処理概要:")
        print("  1. 🌐 yosocal.com にアクセス")
        print("  2. 🏰 ディズニーシーパークを選択")
        print("  3. 📅 指定月のカレンダーに移動")
        print("  4. 🔍 利用可能な全日付を検出")
        print("  5. 🎢 各日付の待ち時間データを順次取得")
        print("  6. 💾 日別・月別でデータを保存")
        print("  7. 📊 統計情報とレポートを生成")
        print("  8. 🎉 完了通知")
    
    # 入力検証
    current_year = datetime.now().year
    if args.year < 2020 or args.year > current_year + 1:
        print(f"❌ エラー: 年は2020から{current_year + 1}の範囲で指定してください")
        sys.exit(1)
    
    try:
        print(f"\n🚀 ディズニーシー {args.year}年{args.month}月 データ取得開始...")
        
        # スクレイピング実行
        scraper = YosocalDisneyseaScraper()
        
        # 詳細ログ設定
        if args.verbose:
            print("📋 詳細ログモード: ON")
        
        # データ取得実行
        success = scraper.scrape_monthly_data(args.year, args.month)
        
        if success:
            print(f"\n🎉 ディズニーシー {args.year}年{args.month}月 データ取得完了！")
            print("=" * 80)
            print("✅ 取得成功")
            print(f"💾 保存先: Disneysea/フォルダ")
            print(f"📋 データ形式: CSV、JSON、TXT")
            print(f"🎢 対象パーク: 🌊 東京ディズニーシー")
            
            print("\n📁 生成ファイル:")
            print("  📄 日別CSVファイル:")
            print("    └── disneysea_daily_YYYY-MM-DD.csv")
            print("  📊 月間統合CSVファイル:")
            print("    └── disneysea_monthly_YYYY_MM_timestamp.csv")
            print("  📈 統計情報JSONファイル:")
            print("    └── disneysea_monthly_stats_YYYY_MM_timestamp.json")
            print("  📄 詳細レポートファイル:")
            print("    └── disneysea_monthly_report_YYYY_MM_timestamp.txt")
            
            print("\n🎯 次のステップ:")
            print("  📊 yosocal_data_analyzer.py でデータ分析")
            print("  📈 統計情報の確認")
            print("  🎢 人気アトラクション分析")
            print("  📅 最適な訪問時間帯の特定")
            
            # 保存先フォルダのファイル数を確認
            disneysea_dir = "Disneysea"
            if os.path.exists(disneysea_dir):
                files = os.listdir(disneysea_dir)
                csv_files = [f for f in files if f.endswith('.csv')]
                json_files = [f for f in files if f.endswith('.json')]
                txt_files = [f for f in files if f.endswith('.txt')]
                
                print(f"\n📂 Disneysea フォルダ内容:")
                print(f"  📄 CSVファイル: {len(csv_files)}個")
                print(f"  📊 JSONファイル: {len(json_files)}個")  
                print(f"  📋 TXTファイル: {len(txt_files)}個")
                print(f"  📁 総ファイル数: {len(files)}個")
            
        else:
            print(f"\n❌ ディズニーシー {args.year}年{args.month}月 データ取得に失敗しました")
            print("🔧 トラブルシューティング:")
            print("  1. インターネット接続を確認")
            print("  2. yosocal.com サイトの稼働状況を確認")
            print("  3. 指定した年月のデータが存在するか確認")
            print("  4. --verbose オプションで詳細ログを確認")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって中断されました")
        print("🔄 再実行する場合は同じコマンドを入力してください")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        print("🔧 トラブルシューティング:")
        print("  1. 必要なパッケージがインストールされているか確認")
        print("  2. Chrome WebDriver が正しくインストールされているか確認")
        print("  3. --verbose オプションで詳細ログを確認")
        if args.verbose:
            import traceback
            print(f"\n📋 詳細エラー情報:")
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 