#!/bin/bash
# .ig_session.json を base64 化して GitHub Secret に登録するためのヘルパー
#
# 使い方:
#   1. ローカルで一度ログイン（セッション生成）:
#        .venv/bin/python post_via_instagram.py --check
#   2. このスクリプトで base64 を生成:
#        ./scripts/encode_ig_session.sh
#   3. 表示された値を GitHub の Secrets > Repository secrets に
#      INSTAGRAM_SESSION_B64 として保存
#   4. （任意）gh CLI が入っていれば自動アップロードも可能:
#        ./scripts/encode_ig_session.sh --upload

set -e

cd "$(dirname "$0")/.."

SESSION_FILE=".ig_session.json"

if [ ! -f "$SESSION_FILE" ]; then
    echo "❌ $SESSION_FILE が見つかりません。"
    echo "   先に: .venv/bin/python post_via_instagram.py --check"
    exit 1
fi

ENCODED=$(base64 < "$SESSION_FILE" | tr -d '\n')

case "$1" in
    --upload)
        if ! command -v gh &> /dev/null; then
            echo "❌ gh CLI が見つかりません。https://cli.github.com/ からインストール"
            exit 1
        fi
        echo "📤 INSTAGRAM_SESSION_B64 を GitHub Secret に登録中..."
        echo "$ENCODED" | gh secret set INSTAGRAM_SESSION_B64
        echo "✅ 登録完了"
        ;;
    *)
        echo "==================================================="
        echo "GitHub Secret 用 base64 (INSTAGRAM_SESSION_B64):"
        echo "==================================================="
        echo "$ENCODED"
        echo "==================================================="
        echo ""
        echo "💡 上記をコピーして以下に貼り付けてください:"
        echo "   GitHub → Settings → Secrets and variables → Actions"
        echo "   → New repository secret"
        echo "   Name : INSTAGRAM_SESSION_B64"
        echo "   Value: <上記の base64 文字列>"
        echo ""
        echo "💡 gh CLI 経由で自動登録する場合:"
        echo "   ./scripts/encode_ig_session.sh --upload"
        ;;
esac
