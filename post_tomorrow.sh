#!/bin/bash
# 確認なしで即座に明日の予測を投稿
# 通常は20:00に自動実行されますが、失敗した場合の緊急用

cd "$(dirname "$0")"

DATE=$(date -v+1d +%Y-%m-%d)

echo "🚀 明日（${DATE}）の予測を即座に投稿します..."
echo ""

/usr/bin/python3 daily_prediction.py --date "$DATE" --post

echo ""
echo "✅ 完了"
