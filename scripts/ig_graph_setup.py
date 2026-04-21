#!/usr/bin/env python3
"""
Instagram Graph API セットアップヘルパー CLI

提供サブコマンド:
  guide          : 全体セットアップ手順を表示
  exchange       : 短期トークン → 長期ユーザートークン変換
  list-pages     : 接続済み Facebook ページ一覧 + Page Access Token
  find-ig        : Page から Instagram Business Account ID を取得
  refresh        : 既存の長期トークンをさらに60日延長
  check          : 現在の認証情報で接続確認
  write-env      : 取得した値を .env に書き込み

使い方例:
  python scripts/ig_graph_setup.py guide
  python scripts/ig_graph_setup.py exchange --token <SHORT_USER_TOKEN>
  python scripts/ig_graph_setup.py list-pages --token <LONG_USER_TOKEN>
  python scripts/ig_graph_setup.py find-ig --page-id <PAGE_ID> --token <PAGE_TOKEN>
  python scripts/ig_graph_setup.py write-env --ig-id <IG_BIZ_ID> --token <PAGE_TOKEN>
  python scripts/ig_graph_setup.py check
  python scripts/ig_graph_setup.py refresh
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

GRAPH_API_VERSION = os.environ.get("FACEBOOK_GRAPH_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
ENV_FILE = PROJECT_DIR / '.env'


# =============================================================================
# サブコマンド: guide
# =============================================================================
GUIDE_TEXT = """
================================================================================
🛠  Instagram Graph API セットアップガイド
================================================================================

このガイドはブラウザでの手動操作と CLI コマンドを組み合わせて、
@disney_ai_wait に Graph API 経由で自動投稿する仕組みを完成させます。

所要時間: 30〜45分（初回のみ）/ 完全無料

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ1️⃣  Instagram を Business / Creator アカウントに変換
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📱 スマホの Instagram 公式アプリで `disney_ai_wait` にログイン
  → プロフィール → メニュー (≡) → 設定とアクティビティ
  → アカウントタイプとツール
  → 「プロアカウントに切り替える」
  → 「クリエイター」または「ビジネス」を選択
  → カテゴリは「個人ブログ」など何でもOK

  🆗 完了の確認方法:
    プロフィール画面に「プロフェッショナルダッシュボード」が出れば成功

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ2️⃣  Facebook ページを作成 & Instagram と連携
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Instagram Graph API は Facebook ページとの連携が必須です。

  (a) Facebook にログイン → https://www.facebook.com/pages/create
      → 「ビジネスまたはブランド」を選択
      → ページ名: 「Disney AI Wait」 など何でもOK
      → カテゴリ: 「個人ブログ」など
      → 作成

  (b) 作成したページに移動 → 設定 → リンク済みアカウント
      → Instagram → 「アカウントを接続」
      → `disney_ai_wait` のログイン情報を入力して連携

  🆗 完了の確認方法:
    Facebook Page の設定で Instagram アカウントが「接続済み」と表示

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ3️⃣  Meta for Developers でアプリ作成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  (a) https://developers.facebook.com/apps/ にアクセス
      → 「アプリを作成」
      → ユースケース: 「その他」 → 次へ
      → タイプ: 「ビジネス」 → 次へ
      → アプリ名: 「Disney AI Wait Bot」 など
      → 連絡先メール: 自分のメール
      → 作成

  (b) ダッシュボード → 「製品を追加」
      → 「Instagram」の「設定」をクリック
      → 「Instagram Graph API」を有効化
      （「Instagram Basic Display」ではなく「Graph API」の方）

  (c) 「アプリの設定」 → 「ベーシック」
      → アプリID(App ID) と app secret(アプリシークレット) をメモ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ4️⃣  ユーザーアクセストークン取得（短期 / 1時間有効）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Graph API Explorer で取得:
  → https://developers.facebook.com/tools/explorer/

  (a) 右上の「Meta App」プルダウンで先ほど作ったアプリを選択
  (b) 「ユーザーまたはページ」 = 「User Token」
  (c) 「Add a Permission」で以下をチェック:
        ✅ instagram_basic
        ✅ instagram_content_publish
        ✅ pages_show_list
        ✅ pages_read_engagement
        ✅ business_management
  (d) 「Generate Access Token」 → Facebookログイン承認
  (e) 表示される `EAAxxxxxx...` という長い文字列をコピー（短期トークン）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ5️⃣  ここから CLI で自動化（短期→長期、Page取得、IG ID取得）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  まず .env に App ID / Secret を保存:
      FACEBOOK_APP_ID=<アプリID>
      FACEBOOK_APP_SECRET=<アプリシークレット>

  (a) 短期トークンを長期(60日)トークンに変換:
      python scripts/ig_graph_setup.py exchange --token <SHORT_USER_TOKEN>

  (b) 接続済みページとPage Access Tokenを取得:
      python scripts/ig_graph_setup.py list-pages --token <LONG_USER_TOKEN>
      → ページIDと page access token が表示される

  (c) Instagram Business Account ID を取得:
      python scripts/ig_graph_setup.py find-ig \\
          --page-id <PAGE_ID> --token <PAGE_TOKEN>

  (d) すべてを .env に書き込み:
      python scripts/ig_graph_setup.py write-env \\
          --ig-id <IG_BIZ_ID> --token <PAGE_TOKEN>

  (e) 動作確認:
      python scripts/ig_graph_setup.py check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ6️⃣  画像ホスティング (Imgur 推奨 / 任意)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Graph API は画像URLが必要なため、ローカル画像を一時ホストします。
  デフォルトで catbox.moe (匿名/無料) を使うので設定不要ですが、
  Imgur を設定するとより安定します。

  (a) https://api.imgur.com/oauth2/addclient にアクセス
  (b) Application name: 「Disney AI Wait」など
  (c) Authorization type: 「Anonymous usage without a user」
  (d) Email: 自分のメール
  (e) reCAPTCHA → submit
  (f) 表示された Client ID を .env に追加:
      IMGUR_CLIENT_ID=<クライアントID>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ステップ7️⃣  GitHub Secrets に登録（GitHub Actions 用）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GitHub リポジトリ → Settings → Secrets and variables → Actions
  以下を登録:
    INSTAGRAM_API_MODE              graph
    INSTAGRAM_BUSINESS_ACCOUNT_ID   <IG_BIZ_ID>
    INSTAGRAM_ACCESS_TOKEN          <PAGE_TOKEN>
    FACEBOOK_APP_ID                 <APP_ID>
    FACEBOOK_APP_SECRET             <APP_SECRET>
    IMGUR_CLIENT_ID                 <任意>

  または gh CLI で一括登録:
    gh secret set INSTAGRAM_API_MODE -b "graph"
    gh secret set INSTAGRAM_BUSINESS_ACCOUNT_ID -b "<IG_BIZ_ID>"
    gh secret set INSTAGRAM_ACCESS_TOKEN -b "<PAGE_TOKEN>"
    ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
完了 🎉  あとは GitHub Actions が毎日 20:05 JST に自動投稿します
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

トークンは60日で期限切れになります。
リフレッシュは月1回程度こちらを実行してください:
    python scripts/ig_graph_setup.py refresh

================================================================================
"""


def cmd_guide(args):
    print(GUIDE_TEXT)


# =============================================================================
# 短期トークン → 長期トークン変換
# =============================================================================
def cmd_exchange(args):
    app_id = args.app_id or os.environ.get("FACEBOOK_APP_ID")
    app_secret = args.app_secret or os.environ.get("FACEBOOK_APP_SECRET")
    if not app_id or not app_secret:
        print("❌ FACEBOOK_APP_ID / FACEBOOK_APP_SECRET が必要です")
        print("   .env に設定するか --app-id / --app-secret で指定してください")
        sys.exit(1)

    print("🔄 短期トークン → 長期トークン (60日有効) に変換中...")
    r = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": args.token,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ エラー: {r.text}")
        sys.exit(1)

    data = r.json()
    long_token = data["access_token"]
    expires = data.get("expires_in", "?")
    print(f"\n✅ 長期トークン取得成功")
    print(f"   有効期間: 約 {expires} 秒 ({int(expires)//86400 if isinstance(expires, int) else '?'} 日)")
    print(f"\n📋 LONG-LIVED USER ACCESS TOKEN:")
    print(f"{long_token}")
    print(f"\n💡 次のステップ:")
    print(f"   python scripts/ig_graph_setup.py list-pages --token {long_token[:30]}...")


# =============================================================================
# 接続済みページ一覧
# =============================================================================
def cmd_list_pages(args):
    print("📄 接続済み Facebook ページを取得中...")
    r = requests.get(
        f"{GRAPH_BASE}/me/accounts",
        params={
            "access_token": args.token,
            "fields": "id,name,access_token,instagram_business_account",
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ エラー: {r.text}")
        sys.exit(1)

    pages = r.json().get("data", [])
    if not pages:
        print("⚠️ 接続済みページが見つかりません。")
        print("   Facebook ページを作成して、ユーザートークンに pages_show_list 権限が")
        print("   付与されていることを確認してください。")
        sys.exit(1)

    print(f"\n✅ {len(pages)} 件のページが見つかりました\n")
    for i, p in enumerate(pages, 1):
        ig = p.get("instagram_business_account", {})
        print(f"━━━ #{i} ━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  ページ名     : {p['name']}")
        print(f"  Page ID      : {p['id']}")
        print(f"  IG Business  : {ig.get('id', '(未連携)')}")
        print(f"  Page Token   : {p['access_token']}")
    print()
    print("💡 Page Access Token は無期限です。これを INSTAGRAM_ACCESS_TOKEN として使います")


# =============================================================================
# Instagram Business Account ID 取得
# =============================================================================
def cmd_find_ig(args):
    print(f"📷 Page {args.page_id} に紐づく Instagram Business Account を取得中...")
    r = requests.get(
        f"{GRAPH_BASE}/{args.page_id}",
        params={
            "fields": "instagram_business_account{id,username,name}",
            "access_token": args.token,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ エラー: {r.text}")
        sys.exit(1)

    data = r.json()
    ig = data.get("instagram_business_account")
    if not ig:
        print("❌ このページに Instagram Business Account が連携されていません")
        print("   Facebook ページの設定 → リンク済みアカウントから Instagram を連携してください")
        sys.exit(1)

    print(f"\n✅ Instagram Business Account 取得")
    print(f"   ID       : {ig['id']}")
    print(f"   Username : @{ig.get('username', '?')}")
    print(f"   Name     : {ig.get('name', '?')}")
    print()
    print(f"💡 これを INSTAGRAM_BUSINESS_ACCOUNT_ID として使います")


# =============================================================================
# トークン更新（60日延長）
# =============================================================================
def cmd_refresh(args):
    app_id = args.app_id or os.environ.get("FACEBOOK_APP_ID")
    app_secret = args.app_secret or os.environ.get("FACEBOOK_APP_SECRET")
    current = args.token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not all([app_id, app_secret, current]):
        print("❌ FACEBOOK_APP_ID / FACEBOOK_APP_SECRET / INSTAGRAM_ACCESS_TOKEN が必要")
        sys.exit(1)

    print("🔄 トークンを60日延長中...")
    r = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": current,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ エラー: {r.text}")
        sys.exit(1)

    data = r.json()
    new_token = data["access_token"]
    print(f"\n✅ 新しいトークン取得")
    print(f"   有効期間: 約 {data.get('expires_in', '?')} 秒")
    print(f"\n{new_token}")

    if args.write:
        _write_env_var("INSTAGRAM_ACCESS_TOKEN", new_token)
        print(f"\n💾 .env を更新しました")


# =============================================================================
# Instagram Login API (新方式 / Facebookページ不要) OAuth フロー
# =============================================================================
IG_OAUTH_AUTHORIZE = "https://www.instagram.com/oauth/authorize"
IG_OAUTH_TOKEN = "https://api.instagram.com/oauth/access_token"
IG_GRAPH_BASE = "https://graph.instagram.com"
IG_DEFAULT_REDIRECT = "https://localhost/"
IG_DEFAULT_SCOPES = "instagram_business_basic,instagram_business_content_publish"


def cmd_ig_login_url(args):
    """OAuth認証URLを生成して表示する"""
    app_id = args.app_id or os.environ.get("FACEBOOK_APP_ID")
    if not app_id:
        print("❌ FACEBOOK_APP_ID (=Disney_aiアプリのID) が必要です")
        sys.exit(1)

    redirect = args.redirect or IG_DEFAULT_REDIRECT
    scopes = args.scopes or IG_DEFAULT_SCOPES

    from urllib.parse import urlencode
    params = {
        "client_id": app_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": scopes,
    }
    url = f"{IG_OAUTH_AUTHORIZE}?{urlencode(params)}"

    print("🌐 ブラウザで以下のURLを開いてください:\n")
    print(url)
    print()
    print("📋 手順:")
    print("  1. URLにアクセス → @disney_ai_wait でログイン")
    print(f"  2. アクセス許可を承認 → {redirect}?code=XXXX に転送される")
    print("     (localhost なのでページは開けないが、URLバーに code= が見える)")
    print("  3. URLバー全体をコピー、もしくは code= の値だけコピー")
    print()
    print("📥 コードを取得したら次のコマンドを実行:")
    print(f"  python scripts/ig_graph_setup.py ig-exchange --code <CODE>")


def cmd_ig_exchange(args):
    """認証コード → 短期トークン → 長期トークン (60日) → .env保存"""
    app_id = args.app_id or os.environ.get("FACEBOOK_APP_ID")
    app_secret = args.app_secret or os.environ.get("FACEBOOK_APP_SECRET")
    redirect = args.redirect or IG_DEFAULT_REDIRECT

    if not app_id or not app_secret:
        print("❌ FACEBOOK_APP_ID / FACEBOOK_APP_SECRET が必要 (.envに設定済みか確認)")
        sys.exit(1)

    code = args.code
    # 「URL全体貼り付け」も許容
    if code.startswith("http"):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(code).query)
        if "code" not in qs:
            print(f"❌ URLから code パラメータを取得できません: {code}")
            sys.exit(1)
        code = qs["code"][0]
    code = code.split("#_")[0]  # Meta は末尾に "#_" を付けるので削除

    # ---- 1) 短期トークン取得 ----
    print("🔄 認証コード → 短期アクセストークン...")
    r = requests.post(
        IG_OAUTH_TOKEN,
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
            "code": code,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ 短期トークン取得失敗: {r.text}")
        sys.exit(1)
    data = r.json()
    short_token = data.get("access_token")
    user_id = data.get("user_id")
    if not short_token:
        print(f"❌ access_tokenが返ってきません: {data}")
        sys.exit(1)
    print(f"   ✅ 短期トークン取得 / user_id={user_id}")

    # ---- 2) 短期 → 長期 (60日) ----
    print("🔄 短期 → 長期 (60日) トークン変換...")
    r = requests.get(
        f"{IG_GRAPH_BASE}/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ 長期トークン変換失敗: {r.text}")
        sys.exit(1)
    data = r.json()
    long_token = data.get("access_token")
    expires = data.get("expires_in")
    print(f"   ✅ 長期トークン取得 (有効期間 {int(expires)//86400 if expires else '?'} 日)")

    # ---- 3) IG ユーザーID 取得 ----
    print("🔄 Instagram User ID を取得...")
    r = requests.get(
        f"{IG_GRAPH_BASE}/me",
        params={
            "fields": "id,username,account_type",
            "access_token": long_token,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"⚠️ ユーザー情報取得失敗 (続行): {r.text}")
        ig_user_id = str(user_id) if user_id else ""
        username = "?"
    else:
        info = r.json()
        ig_user_id = info.get("id", str(user_id) if user_id else "")
        username = info.get("username", "?")
        print(f"   ✅ @{username} (id={ig_user_id}, type={info.get('account_type')})")

    # ---- 4) .env 自動保存 ----
    _write_env_var("INSTAGRAM_API_MODE", "graph")
    _write_env_var("INSTAGRAM_ACCESS_TOKEN", long_token)
    _write_env_var("INSTAGRAM_BUSINESS_ACCOUNT_ID", ig_user_id)
    _write_env_var("INSTAGRAM_GRAPH_BACKEND", "instagram")  # 新方式フラグ

    print()
    print("💾 .env に保存しました:")
    print(f"   INSTAGRAM_API_MODE              = graph")
    print(f"   INSTAGRAM_GRAPH_BACKEND         = instagram (新方式)")
    print(f"   INSTAGRAM_BUSINESS_ACCOUNT_ID   = {ig_user_id}")
    print(f"   INSTAGRAM_ACCESS_TOKEN          = {long_token[:25]}...")
    print()
    print("✅ セットアップ完了！動作確認:")
    print("   python scripts/ig_graph_setup.py check")


def cmd_ig_refresh(args):
    """Instagram Login API の長期トークンを延長 (60日)"""
    current = args.token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not current:
        print("❌ INSTAGRAM_ACCESS_TOKEN が必要")
        sys.exit(1)

    print("🔄 Instagram長期トークンを60日延長中...")
    r = requests.get(
        f"{IG_GRAPH_BASE}/refresh_access_token",
        params={
            "grant_type": "ig_refresh_token",
            "access_token": current,
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ エラー: {r.text}")
        sys.exit(1)

    data = r.json()
    new_token = data["access_token"]
    print(f"\n✅ 新しいトークン取得 (有効期間 {int(data.get('expires_in', 0))//86400} 日)")
    if args.write:
        _write_env_var("INSTAGRAM_ACCESS_TOKEN", new_token)
        print(f"💾 .env を更新しました")
    else:
        print(f"\n{new_token}")


# =============================================================================
# 接続確認
# =============================================================================
def cmd_check(args):
    sys.path.insert(0, str(PROJECT_DIR))
    from post_via_instagram_graph import InstagramGraphPoster
    poster = InstagramGraphPoster()
    ok = poster.check_connection()
    sys.exit(0 if ok else 1)


# =============================================================================
# .env への書き込み
# =============================================================================
def _write_env_var(key: str, value: str):
    """既存の .env を更新（既存キーは上書き、なければ追加）"""
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")

    lines = ENV_FILE.read_text().splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def cmd_write_env(args):
    updates = {
        "INSTAGRAM_API_MODE": "graph",
    }
    if args.ig_id:
        updates["INSTAGRAM_BUSINESS_ACCOUNT_ID"] = args.ig_id
    if args.token:
        updates["INSTAGRAM_ACCESS_TOKEN"] = args.token
    if args.app_id:
        updates["FACEBOOK_APP_ID"] = args.app_id
    if args.app_secret:
        updates["FACEBOOK_APP_SECRET"] = args.app_secret
    if args.imgur_id:
        updates["IMGUR_CLIENT_ID"] = args.imgur_id

    if not updates or len(updates) == 1:
        print("❌ 書き込む値が指定されていません")
        sys.exit(1)

    for k, v in updates.items():
        _write_env_var(k, v)
        print(f"   ✅ {k}=***")
    print(f"\n💾 .env を更新しました ({ENV_FILE})")
    print(f"\n💡 接続確認:")
    print(f"   python scripts/ig_graph_setup.py check")


# =============================================================================
# argparse セットアップ
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Instagram Graph API セットアップヘルパー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("guide", help="セットアップガイドを表示")

    p = sub.add_parser("exchange", help="短期→長期トークン変換")
    p.add_argument("--token", required=True, help="短期ユーザートークン")
    p.add_argument("--app-id", help="(.env のFACEBOOK_APP_IDで自動)")
    p.add_argument("--app-secret", help="(.env のFACEBOOK_APP_SECRETで自動)")

    p = sub.add_parser("list-pages", help="接続済みFacebookページ一覧")
    p.add_argument("--token", required=True, help="長期ユーザートークン")

    p = sub.add_parser("find-ig", help="PageからIGビジネスアカウントID取得")
    p.add_argument("--page-id", required=True)
    p.add_argument("--token", required=True, help="Page Access Token")

    p = sub.add_parser("refresh", help="[旧方式] Facebook Page Tokenを60日延長")
    p.add_argument("--token", help="(.envのINSTAGRAM_ACCESS_TOKENで自動)")
    p.add_argument("--app-id")
    p.add_argument("--app-secret")
    p.add_argument("--write", action="store_true",
                   help=".env のINSTAGRAM_ACCESS_TOKENを更新")

    # --- Instagram Login API (新方式 / FBページ不要) ---
    p = sub.add_parser("ig-login-url",
                       help="[新方式] OAuth認証URL生成 (ブラウザで開く)")
    p.add_argument("--app-id", help="(.env のFACEBOOK_APP_IDで自動)")
    p.add_argument("--redirect", help="OAuth リダイレクトURI (デフォルト https://localhost/)")
    p.add_argument("--scopes", help="権限 (デフォルト instagram_business_basic,instagram_business_content_publish)")

    p = sub.add_parser("ig-exchange",
                       help="[新方式] 認証コード→長期トークン変換+.env保存")
    p.add_argument("--code", required=True,
                   help="認証コード (URL全体貼り付けOK)")
    p.add_argument("--app-id")
    p.add_argument("--app-secret")
    p.add_argument("--redirect", help="ig-login-urlと同じredirect_uri")

    p = sub.add_parser("ig-refresh",
                       help="[新方式] Instagram長期トークンを60日延長")
    p.add_argument("--token")
    p.add_argument("--write", action="store_true")

    sub.add_parser("check", help="現在の認証情報で接続確認")

    p = sub.add_parser("write-env", help="取得した値を .env に保存")
    p.add_argument("--ig-id", help="Instagram Business Account ID")
    p.add_argument("--token", help="Page Access Token")
    p.add_argument("--app-id")
    p.add_argument("--app-secret")
    p.add_argument("--imgur-id", help="Imgur Client ID")

    args = parser.parse_args()

    handlers = {
        "guide": cmd_guide,
        "exchange": cmd_exchange,
        "list-pages": cmd_list_pages,
        "find-ig": cmd_find_ig,
        "refresh": cmd_refresh,
        "ig-login-url": cmd_ig_login_url,
        "ig-exchange": cmd_ig_exchange,
        "ig-refresh": cmd_ig_refresh,
        "check": cmd_check,
        "write-env": cmd_write_env,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
