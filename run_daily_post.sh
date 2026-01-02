#!/bin/bash
# 毎朝8:00に実行されるディズニー待ち時間予測投稿スクリプト
# 
# 投稿内容:
# - パーク全体×2（シー、ランド）+ 画像
# - 人気アトラクション×2（各パーク1つずつローテーション）
# - 持ち物リスト（月曜日のみ）

# ログファイル
LOG_DIR="/Users/itoshintaro/yeonggil_works/Disney/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_$(date +%Y-%m-%d).log"

echo "========================================" >> "$LOG_FILE"
echo "🎢 TDR待ち時間予測 自動投稿" >> "$LOG_FILE"
echo "実行開始: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# プロジェクトディレクトリに移動
cd /Users/itoshintaro/yeonggil_works/Disney

# .envから環境変数を読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Python実行（パーク全体 + アトラクション個別 + 月曜は持ち物リスト）
/usr/bin/python3 daily_prediction.py --post --attractions >> "$LOG_FILE" 2>&1

echo "" >> "$LOG_FILE"
echo "実行完了: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

