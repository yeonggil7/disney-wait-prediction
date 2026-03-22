#!/usr/bin/env python3
"""
当日の予測を手動で投稿するスクリプト
自動投稿が失敗した場合にこのスクリプトを実行してください

使い方:
    python3 post_today.py              # 今日の予測を投稿
    python3 post_today.py --tomorrow   # 明日の予測を投稿
    python3 post_today.py --dry-run    # 投稿せず内容確認のみ
    python3 post_today.py --sea-only   # シーのみ投稿
    python3 post_today.py --land-only  # ランドのみ投稿
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='当日の予測を手動で投稿（自動投稿失敗時の救済用）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python3 post_today.py              今日の予測を投稿
  python3 post_today.py --tomorrow   明日の予測を投稿  
  python3 post_today.py --dry-run    投稿内容を確認のみ
  python3 post_today.py --sea-only   シーのみ投稿
        """
    )
    parser.add_argument('--tomorrow', '-t', action='store_true',
                       help='明日の予測を投稿（前日20時に投稿する場合）')
    parser.add_argument('--date', '-d', type=str, default=None,
                       help='特定の日付を指定 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true',
                       help='投稿せずに内容確認のみ')
    parser.add_argument('--sea-only', action='store_true',
                       help='シーのみ投稿')
    parser.add_argument('--land-only', action='store_true',
                       help='ランドのみ投稿')
    parser.add_argument('--no-attractions', action='store_true',
                       help='個別アトラクション投稿をスキップ')
    args = parser.parse_args()
    
    # 日付を決定
    if args.date:
        target_date = args.date
    elif args.tomorrow:
        target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    # 表示
    print("=" * 60)
    print("🎢 手動予測投稿スクリプト")
    print("=" * 60)
    print(f"📅 投稿する日付: {target_date}")
    print(f"⏰ 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🔍 モード: ドライラン（投稿しません）")
    else:
        print("📤 モード: 実際に投稿します")
    
    if args.sea_only:
        print("🌊 対象: シーのみ")
    elif args.land_only:
        print("🏰 対象: ランドのみ")
    else:
        print("🎡 対象: 両パーク")
    
    print("=" * 60)
    
    # 確認
    if not args.dry_run:
        confirm = input("\n投稿を実行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            print("キャンセルしました")
            return
    
    # daily_prediction.py を呼び出し
    cmd = [
        sys.executable,
        str(PROJECT_DIR / 'daily_prediction.py'),
        '--date', target_date,
    ]
    
    if not args.dry_run:
        cmd.append('--post')
    else:
        cmd.append('--dry-run')
    
    if args.sea_only:
        cmd.append('--sea-only')
    elif args.land_only:
        cmd.append('--land-only')
    
    if not args.no_attractions:
        cmd.append('--attractions')
    
    print(f"\n実行コマンド: {' '.join(cmd)}\n")
    
    # 実行
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✅ 処理が完了しました！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ エラーが発生しました")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
