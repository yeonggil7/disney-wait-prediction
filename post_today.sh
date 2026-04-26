#!/bin/bash
# 当日の予測を手動で投稿するスクリプト
# ダブルクリックまたはターミナルで実行可能

cd "$(dirname "$0")"

echo "========================================"
echo "🎢 ディズニー待ち時間 手動投稿"
echo "========================================"
echo ""
echo "どの日付を投稿しますか？"
echo "  1) 今日 ($(date +%Y-%m-%d))"
echo "  2) 明日 ($(date -v+1d +%Y-%m-%d))"
echo "  3) 確認のみ（投稿しない）"
echo "  q) 終了"
echo ""
read -p "選択してください (1/2/3/q): " choice

case $choice in
    1)
        echo ""
        echo "📅 今日の予測を投稿します..."
        /usr/bin/python3 post_today.py
        ;;
    2)
        echo ""
        echo "📅 明日の予測を投稿します..."
        /usr/bin/python3 post_today.py --tomorrow
        ;;
    3)
        echo ""
        echo "🔍 投稿内容を確認します（投稿しません）..."
        /usr/bin/python3 post_today.py --dry-run
        ;;
    q|Q)
        echo "終了します"
        exit 0
        ;;
    *)
        echo "無効な選択です"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "処理が完了しました"
echo "========================================"
read -p "Enterキーで終了..."
