#!/usr/bin/env python3
"""
yosocal.com Selenium スクレイピング実行スクリプト
8:15から21:45まで30分おきの全時間帯データを取得
"""

from yosocal_realtime_complete import main

if __name__ == "__main__":
    print("🚀 Seleniumを使用したyosocal.com全時間帯スクレイピング開始")
    print("=" * 80)
    
    # Seleniumオプション有効でリアルタイムデータを取得
    success = main(target_date="20250702", try_selenium=True)
    
    if success:
        print("\n🎉 Seleniumスクレイピングが成功しました！")
        print("📊 全時間帯（8:15-21:45）のデータが取得できました")
    else:
        print("\n❌ Seleniumスクレイピングに失敗しました")
        print("💡 ブラウザやドライバーの設定を確認してください") 