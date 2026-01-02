#!/bin/bash
# 毎朝の自動予測実行をセットアップするスクリプト
# macOS launchdを使用

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.disney.daily-prediction"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
PYTHON_PATH=$(which python3)

# 実行時刻（デフォルト: 毎朝6:00）
HOUR="${1:-6}"
MINUTE="${2:-0}"

echo "🎢 TDR 毎日予測 - 自動実行セットアップ"
echo "=" 
echo "スクリプト: $SCRIPT_DIR/daily_prediction.py"
echo "実行時刻: 毎日 ${HOUR}:${MINUTE}"
echo "Python: $PYTHON_PATH"
echo ""

# LaunchAgentsディレクトリを作成
mkdir -p "$HOME/Library/LaunchAgents"

# plistファイルを作成
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${SCRIPT_DIR}/daily_prediction.py</string>
        <string>--post</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/daily_prediction.log</string>
    
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/daily_prediction_error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>TWITTER_API_KEY</key>
        <string></string>
        <key>TWITTER_API_SECRET</key>
        <string></string>
        <key>TWITTER_ACCESS_TOKEN</key>
        <string></string>
        <key>TWITTER_ACCESS_TOKEN_SECRET</key>
        <string></string>
        <key>TWITTER_BEARER_TOKEN</key>
        <string></string>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# ログディレクトリを作成
mkdir -p "$SCRIPT_DIR/logs"

echo "✅ plistファイルを作成しました: $PLIST_PATH"
echo ""
echo "⚠️ X投稿を有効にするには、plistファイルを編集してAPIキーを設定してください:"
echo "   open $PLIST_PATH"
echo ""

# 既存のジョブをアンロード
launchctl unload "$PLIST_PATH" 2>/dev/null

# 新しいジョブをロード
launchctl load "$PLIST_PATH"

echo "✅ スケジュールを有効化しました"
echo ""
echo "📋 コマンド一覧:"
echo "   確認:   launchctl list | grep disney"
echo "   停止:   launchctl unload $PLIST_PATH"
echo "   再開:   launchctl load $PLIST_PATH"
echo "   手動実行: python3 $SCRIPT_DIR/daily_prediction.py"
echo "   ログ確認: tail -f $SCRIPT_DIR/logs/daily_prediction.log"
echo ""
echo "🎉 セットアップ完了！毎朝 ${HOUR}:${MINUTE} に予測が実行されます"


