#!/usr/bin/env python3
"""
Instagram コメント FAQ 自動返信

定期的に過去 N 日分の自分の投稿を巡回し、
未返信コメントを FAQ ルール に当てはめて自動返信する。

仕組み:
  1. /me/media で直近の投稿を取得
  2. 各投稿の /comments を取得
  3. コメント本文 を FAQ_RULES に正規表現マッチ
  4. マッチしたら、自分が既に返信していないか確認 → 未返信なら reply
  5. 返信済みのコメント ID を logs/auto_reply_done.json に記録 (二重投稿防止)

セキュリティ:
  - INSTAGRAM_AUTO_REPLY_ENABLED=true の場合のみ実投稿
  - スパム/不適切コメントには返信しない (NG_KEYWORDS で除外)
  - 自分のコメント (= 自分の business account ID と同じ) には返信しない
  - 1投稿あたり最大 5件、1巡回あたり最大 30件 のキャップ

使い方:
    python scripts/auto_reply_comments.py --dry-run
    INSTAGRAM_AUTO_REPLY_ENABLED=true python scripts/auto_reply_comments.py
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


GRAPH_API_VERSION = os.environ.get("FACEBOOK_GRAPH_VERSION", "v21.0")
INSTAGRAM_GRAPH_BACKEND = os.environ.get("INSTAGRAM_GRAPH_BACKEND", "facebook").lower()
GRAPH_BASE = ("https://graph.instagram.com" if INSTAGRAM_GRAPH_BACKEND == "instagram"
              else f"https://graph.facebook.com/{GRAPH_API_VERSION}")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
ENABLED = os.environ.get("INSTAGRAM_AUTO_REPLY_ENABLED", "").lower() == "true"

DONE_LOG = PROJECT_DIR / "logs" / "auto_reply_done.json"


# =============================================================================
# FAQ ルール
# =============================================================================
# 正規表現 (大文字小文字無視) → 返信テンプレ
# テンプレ内 {handle} は @disney_ai_wait に置換される
FAQ_RULES = [
    # ── 予測精度系
    (r"(あた|当た)(る|ります|った|るの|るんで)|的中|どれくらい|精度|正確",
     "コメントありがとうございます😊 過去30日の的中率(±15分以内)は約65-75%です！毎日「答え合わせ投稿」で実績公開してます🎯 ハイライト「的中例」もぜひ👀"),

    # ── 何時に投稿か / 更新頻度
    (r"何時|更新|投稿時間|いつ.*投稿|毎日",
     "毎晩20時(JST)に翌日のAI予測、翌日21時に答え合わせを投稿してます📅 通知ONにしておくと旅行プラン作りにすぐ役立ちますよ🔔"),

    # ── データ元 / どうやって?
    (r"どうやって|どのよう|データ.*元|ソース|どこから|モデル",
     "公開待ち時間データ + 天気 + 曜日特性 + 過去傾向を機械学習にかけて予測しています📊 詳しい仕組みはハイライト「仕組み」で公開中！"),

    # ── パスポート/チケット
    (r"パスポート|チケット|何時.*入園|入園時間",
     "パスポート/チケット価格は変動制(デイリー)です🎟️ 公式: tokyodisneyresort.jp で当日の価格をチェックを！"),

    # ── ファストパス / DPA / プレミア
    (r"DPA|プレミアアクセス|ファストパス|スタンバイパス|プライオリティ",
     "DPA は対象アトラクで購入可、当日朝〜売切れまで💎 プレミアアクセスの当日攻略ヒントは IG ストーリーズで毎朝シェアしてます👍"),

    # ── 雨 / 天気
    (r"雨|天気|雷|台風",
     "雨予報の日は屋内アトラク中心の予測が変わります☔ 当日朝のストーリーズで「雨の日攻略ルート」をお届けしてます！"),

    # ── 子供連れ / 親子
    (r"子供|子連れ|赤ちゃん|ベビー|キッズ",
     "ファミリー向けは「身長制限なし」アトラクの待ち時間も別途まとめてます🧸 ハイライト「ファミリー」をご覧ください！"),

    # ── ありがとう / 助かる
    (r"ありがとう|助かり|参考になり|参考に|tnx|thank",
     "こちらこそありがとうございます🙏 旅行プラン作りに役立てたら嬉しいです✨ また見にきてくださいね！"),

    # ── どっちのパーク?
    (r"シー.*ランド|ランド.*シー|どっち.*パーク|どちら",
     "シーは平均待ちが少しランドより短い傾向🌊 ただし日によって逆転します！カルーセル投稿でその日の比較を毎日出してます👀"),

    # ── おすすめ
    (r"おすすめ|オススメ|お勧め",
     "その日の混雑度で変わるので、毎日のAI予測を見てから決めるのがおすすめ💡 ハイライト「攻略テンプレ」に基本ルートまとめてます！"),
]

# 返信しないコメント (スパム/NG)
NG_PATTERNS = [
    r"DM|dm|チェック.*プロフ|稼げ|フォロバ|相互|fxxx|http",
    r"^\s*[👍👏❤️😍🔥]+\s*$",  # 絵文字のみは返信しない
]
NG_REGEX = [re.compile(p, re.IGNORECASE) for p in NG_PATTERNS]
FAQ_REGEX = [(re.compile(p, re.IGNORECASE), tpl) for p, tpl in FAQ_RULES]

HANDLE = "@disney_ai_wait"
PER_POST_LIMIT = 5
PER_RUN_LIMIT = 30


def _api_get(path: str, params: dict = None) -> dict:
    p = dict(params or {})
    p["access_token"] = ACCESS_TOKEN
    r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
    if not r.ok:
        raise RuntimeError(f"GET {path} {r.status_code}: {r.text[:200]}")
    return r.json()


def _api_post(path: str, params: dict = None) -> dict:
    p = dict(params or {})
    p["access_token"] = ACCESS_TOKEN
    r = requests.post(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
    if not r.ok:
        raise RuntimeError(f"POST {path} {r.status_code}: {r.text[:200]}")
    return r.json()


def _load_done() -> set:
    if not DONE_LOG.exists():
        return set()
    try:
        return set(json.loads(DONE_LOG.read_text(encoding='utf-8')))
    except Exception:
        return set()


def _save_done(ids: set):
    DONE_LOG.parent.mkdir(parents=True, exist_ok=True)
    # 直近 5000 件だけ保持
    ids_list = sorted(ids)[-5000:]
    DONE_LOG.write_text(json.dumps(ids_list, ensure_ascii=False, indent=2),
                         encoding='utf-8')


def fetch_recent_media(limit: int = 20) -> list:
    if not (ACCESS_TOKEN and IG_USER_ID):
        return []
    data = _api_get(f"{IG_USER_ID}/media",
                    {"fields": "id,timestamp,caption", "limit": limit})
    return data.get("data", [])


def fetch_comments(media_id: str) -> list:
    try:
        data = _api_get(f"{media_id}/comments",
                         {"fields": "id,text,timestamp,from,user,replies{from,user,text}"})
        return data.get("data", [])
    except Exception as e:
        print(f"   ⚠️ comments 取得失敗: {e}")
        return []


def reply_to_comment(comment_id: str, message: str) -> bool:
    try:
        _api_post(f"{comment_id}/replies", {"message": message[:500]})
        return True
    except Exception as e:
        print(f"   ❌ reply 失敗: {e}")
        return False


def match_faq(text: str) -> str | None:
    """マッチした最初のテンプレを返す。NG にマッチしたら None"""
    if not text or not text.strip():
        return None
    for r in NG_REGEX:
        if r.search(text):
            return None
    for r, tpl in FAQ_REGEX:
        if r.search(text):
            return tpl.replace("{handle}", HANDLE)
    return None


def is_my_reply(replies: list) -> bool:
    """既に自分(または自動返信bot)が返信しているか"""
    if not replies:
        return False
    for rep in replies:
        # IG Graph backend → from.id, FB Graph backend → user.id 両方ケア
        from_id = (rep.get("from") or rep.get("user") or {}).get("id", "")
        if from_id == IG_USER_ID:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="IG コメント FAQ 自動返信")
    parser.add_argument("--dry-run", action="store_true",
                        help="返信せずマッチング結果のみ表示")
    parser.add_argument("--media-limit", type=int, default=20,
                        help="巡回する直近投稿数")
    parser.add_argument("--force", action="store_true",
                        help="INSTAGRAM_AUTO_REPLY_ENABLED が false でも実投稿")
    args = parser.parse_args()

    if not (ACCESS_TOKEN and IG_USER_ID):
        print("❌ INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ACCOUNT_ID 未設定")
        return 1

    will_post = (args.force or ENABLED) and not args.dry_run
    print(f"📡 mode = {'POST (本番)' if will_post else 'DRY-RUN (返信しない)'}")

    media_list = fetch_recent_media(args.media_limit)
    print(f"📥 巡回対象 投稿: {len(media_list)}")
    done = _load_done()

    total_replied = 0
    new_done = set(done)

    for m in media_list:
        if total_replied >= PER_RUN_LIMIT:
            break
        media_id = m["id"]
        comments = fetch_comments(media_id)
        if not comments:
            continue
        per_post = 0
        for c in comments:
            if total_replied >= PER_RUN_LIMIT or per_post >= PER_POST_LIMIT:
                break
            cid = c["id"]
            if cid in done:
                continue
            text = c.get("text", "")
            from_id = (c.get("from") or c.get("user") or {}).get("id", "")
            from_name = (c.get("from") or c.get("user") or {}).get("username", "?")
            if from_id == IG_USER_ID:
                # 自分のコメントはスキップ + done に入れて次回もう見ない
                new_done.add(cid)
                continue
            # 既に自分が返信済みならスキップ
            replies = (c.get("replies") or {}).get("data", []) if isinstance(c.get("replies"), dict) else c.get("replies") or []
            if is_my_reply(replies):
                new_done.add(cid)
                continue
            tpl = match_faq(text)
            if not tpl:
                continue
            print(f"\n   📝 @{from_name}: {text[:60]}")
            print(f"      → 返信案: {tpl[:80]}…")
            if will_post:
                ok = reply_to_comment(cid, tpl)
                if ok:
                    total_replied += 1
                    per_post += 1
                    new_done.add(cid)
                    print(f"      ✅ 返信完了")
                    time.sleep(2)  # rate limit 緩和
            else:
                # dry-run はカウントだけ
                total_replied += 1
                per_post += 1

    print(f"\n✅ {total_replied}件 {'返信' if will_post else 'マッチ (dry-run)'}しました")
    if will_post:
        _save_done(new_done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
