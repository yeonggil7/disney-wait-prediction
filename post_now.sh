#!/bin/bash
# 確認なしで即座に今日の予測を投稿
# 自動投稿が失敗した時の緊急用

cd "$(dirname "$0")"

DATE=${1:-$(date +%Y-%m-%d)}

echo "🚀 今日（${DATE}）の予測を即座に投稿します..."
echo ""

/usr/bin/python3 daily_prediction.py --date "$DATE" --post

echo ""
echo "✅ 完了"
