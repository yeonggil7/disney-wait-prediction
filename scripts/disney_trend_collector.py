#!/usr/bin/env python3
"""
ディズニートレンド収集モジュール

複数の無料ソースを集約し、その日のディズニー周りの動向を JSON で出力する。
全てのソースは graceful fallback (1つコケても他は動く) 設計。

ソース:
  1. Google ニュース RSS (無料・無認証)  ※ 主要ソース
     - "東京ディズニーシー" / "東京ディズニーランド" / "TDR" / "ディズニー" 検索
  2. ニュース系 RSS (Disney 公式 / GIGAZINE 等)
  3. Reddit (任意 / REDDIT_CLIENT_ID/SECRET があれば PRAW で r/Disney 等)
  4. 自社実績データ
     - 直近の混雑トレンド (今週 vs 先週)
     - 昨日の最も混んだ/空いてた アトラクション
     - 予測精度 (MAE)

出力:
  - reports/disney_trend_{date}.json : 構造化データ
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote_plus

import feedparser
import pandas as pd

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass


# =============================================================================
# Google ニュース RSS
# =============================================================================
GOOGLE_NEWS_QUERIES = [
    "東京ディズニーシー",
    "東京ディズニーランド",
    "東京ディズニーリゾート",
    "TDR ディズニー",
]

ADDITIONAL_FEEDS = [
    # GIGAZINE 全カテゴリ (ディズニーの記事もここに流れる)
    {"name": "GIGAZINE", "url": "https://gigazine.net/news/rss_2.0/"},
    # ねとらぼ (おもしろ系の話題)
    {"name": "ねとらぼ", "url": "https://nlab.itmedia.co.jp/rss/2.0/nlab.xml"},
]

DISNEY_KEYWORDS = [
    "ディズニー", "Disney", "TDL", "TDS", "TDR",
    "ミッキー", "ダッフィー", "シェリーメイ",
    "ファンタジースプリングス", "ソアリン", "美女と野獣",
    "ベイマックス", "アナ雪", "アナと雪", "ピーターパン",
    "舞浜", "イクスピアリ",
]


def _fetch_feed(url: str, timeout: int = 20) -> list:
    """RSS を取得して entries を返す。失敗時は空リスト。"""
    try:
        # feedparser には timeout 直接指定が無いので socket レベルで
        import socket
        socket.setdefaulttimeout(timeout)
        d = feedparser.parse(url)
        if d.bozo and not d.entries:
            return []
        return d.entries or []
    except Exception as e:
        print(f"  ⚠️ feed 失敗 {url[:80]}: {e}")
        return []


def fetch_google_news(queries: List[str], max_per_query: int = 8) -> list:
    """Google ニュース RSS から日本語記事を取得"""
    out = []
    seen = set()
    for q in queries:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(q)}&hl=ja&gl=JP&ceid=JP:ja"
        )
        entries = _fetch_feed(url)
        for e in entries[:max_per_query]:
            link = e.get("link", "")
            title = e.get("title", "")
            if not title or link in seen:
                continue
            seen.add(link)

            # 公開日時
            published = ""
            if e.get("published_parsed"):
                published = datetime(*e.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")

            # source は title に "タイトル - 媒体名" の形で入っている
            source = ""
            if " - " in title:
                source = title.rsplit(" - ", 1)[1]
                title = title.rsplit(" - ", 1)[0]

            out.append({
                "query": q,
                "title": title,
                "source": source,
                "link": link,
                "published": published,
            })
    return out


def fetch_extra_feeds(disney_only: bool = True) -> list:
    """汎用 RSS からディズニー関連だけ抽出"""
    out = []
    for feed in ADDITIONAL_FEEDS:
        for e in _fetch_feed(feed["url"]):
            title = e.get("title", "")
            summary = e.get("summary", "")
            blob = f"{title} {summary}"
            if disney_only and not any(k in blob for k in DISNEY_KEYWORDS):
                continue
            published = ""
            if e.get("published_parsed"):
                published = datetime(*e.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
            out.append({
                "source": feed["name"],
                "title": title,
                "link": e.get("link", ""),
                "published": published,
            })
    return out


# =============================================================================
# Reddit (任意)
# =============================================================================
def fetch_reddit_top(limit_per_sub: int = 5) -> list:
    """Reddit の Disney 系 sub から人気投稿を取得 (PRAW)"""
    cid = os.environ.get("REDDIT_CLIENT_ID")
    csecret = os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT", "disney-ai-trend-bot/1.0")

    if not (cid and csecret):
        return []

    try:
        import praw  # type: ignore
    except ImportError:
        print("  ⚠️ praw 未インストール → pip install praw でReddit取得を有効化")
        return []

    try:
        reddit = praw.Reddit(client_id=cid, client_secret=csecret, user_agent=ua,
                             check_for_async=False)
        reddit.read_only = True
    except Exception as e:
        print(f"  ⚠️ Reddit 認証失敗: {e}")
        return []

    subs = ["TokyoDisneyland", "Disneyland", "Disney", "WaltDisneyWorld"]
    out = []
    for sub_name in subs:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.top(time_filter="day", limit=limit_per_sub):
                out.append({
                    "subreddit": sub_name,
                    "title": post.title,
                    "score": post.score,
                    "comments": post.num_comments,
                    "url": f"https://reddit.com{post.permalink}",
                    "created": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
                })
        except Exception as e:
            print(f"  ⚠️ r/{sub_name}: {e}")
    return out


# =============================================================================
# 自社実績データ分析
# =============================================================================
def _load_actual(park: str, date_str: str) -> pd.DataFrame:
    """指定日の actual CSV を読む"""
    base = "Disneysea" if park == "sea" else "Disneyland"
    prefix = "disneysea" if park == "sea" else "disneyland"
    path = PROJECT_DIR / base / f"{prefix}_daily_{date_str}.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df = df[pd.to_numeric(df['wait_time'], errors='coerce').notna()]
        df['wait_time'] = df['wait_time'].astype(int)
        return df[df['wait_time'] >= 0]
    except Exception as e:
        print(f"  ⚠️ {path.name}: {e}")
        return pd.DataFrame()


def analyze_recent_actuals(days: int = 7) -> dict:
    """直近 N 日間の自社データから混雑傾向を抽出"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_week_same_dow = yesterday - timedelta(days=7)

    out = {
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "by_park": {},
        "wow_change": {},  # week-over-week
    }

    for park in ('sea', 'land'):
        df_y = _load_actual(park, yesterday.strftime("%Y-%m-%d"))
        df_w = _load_actual(park, last_week_same_dow.strftime("%Y-%m-%d"))

        park_data = {"avg_wait": None, "busiest": [], "calmest": [], "n_records": len(df_y)}
        if not df_y.empty:
            # 9-19 時のみ集計
            df_y['hour'] = df_y['time'].str.split(':').str[0].astype(int)
            day_df = df_y[(df_y['hour'] >= 9) & (df_y['hour'] < 20)]
            if not day_df.empty:
                park_data["avg_wait"] = round(float(day_df['wait_time'].mean()), 1)
                attr_avg = day_df.groupby('attraction_name')['wait_time'].mean()
                top5 = attr_avg.nlargest(5)
                bot5 = attr_avg[attr_avg > 0].nsmallest(5)
                park_data["busiest"] = [
                    {"name": n, "avg_wait": round(float(v), 1)}
                    for n, v in top5.items()
                ]
                park_data["calmest"] = [
                    {"name": n, "avg_wait": round(float(v), 1)}
                    for n, v in bot5.items()
                ]
                park_data["peak_time"] = str(
                    day_df.groupby('time')['wait_time'].mean().idxmax()
                )

        # 先週同曜日との比較
        wow = None
        if not df_y.empty and not df_w.empty:
            df_y2 = df_y[df_y['wait_time'] > 0]
            df_w2 = df_w[df_w['wait_time'] > 0]
            if not df_y2.empty and not df_w2.empty:
                cur = float(df_y2['wait_time'].mean())
                prev = float(df_w2['wait_time'].mean())
                if prev > 0:
                    wow = {
                        "current_avg": round(cur, 1),
                        "prev_avg": round(prev, 1),
                        "diff_pct": round((cur - prev) / prev * 100, 1),
                    }
        out["by_park"][park] = park_data
        out["wow_change"][park] = wow

    # 一週間の傾向 (各日の混雑度の流れ)
    week = []
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        sea_df = _load_actual('sea', d_str)
        land_df = _load_actual('land', d_str)
        sea_avg = round(float(sea_df[sea_df['wait_time'] > 0]['wait_time'].mean()), 1) if not sea_df.empty and (sea_df['wait_time'] > 0).any() else None
        land_avg = round(float(land_df[land_df['wait_time'] > 0]['wait_time'].mean()), 1) if not land_df.empty and (land_df['wait_time'] > 0).any() else None
        week.append({"date": d_str, "sea": sea_avg, "land": land_avg})
    out["weekly_trend"] = week

    return out


# =============================================================================
# 集約
# =============================================================================
def collect_all(news_per_query: int = 8) -> dict:
    print("📡 トレンド収集開始")

    print("  📰 Google ニュース RSS...")
    google_news = fetch_google_news(GOOGLE_NEWS_QUERIES, max_per_query=news_per_query)
    print(f"     → {len(google_news)} 件")

    print("  📰 追加 RSS フィード (ディズニー関連抽出)...")
    extra = fetch_extra_feeds()
    print(f"     → {len(extra)} 件")

    print("  💬 Reddit (任意)...")
    reddit = fetch_reddit_top()
    print(f"     → {len(reddit)} 件" + (" (creds未設定 → スキップ)" if not reddit and not os.environ.get("REDDIT_CLIENT_ID") else ""))

    print("  📊 自社実績データ分析...")
    actuals = analyze_recent_actuals(days=7)
    print(f"     → 昨日 {actuals['yesterday']} のデータ取り込み済み")

    return {
        "collected_at": datetime.now().isoformat(timespec='seconds'),
        "google_news": google_news,
        "extra_feeds": extra,
        "reddit": reddit,
        "actuals": actuals,
    }


# =============================================================================
# CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="ディズニートレンド 収集")
    parser.add_argument("--out", type=str, default=None,
                        help="JSON 出力パス (デフォルト reports/disney_trend_{date}.json)")
    parser.add_argument("--news-per-query", type=int, default=8)
    args = parser.parse_args()

    out_path = args.out
    if not out_path:
        d = datetime.now().strftime("%Y-%m-%d")
        out_path = str(PROJECT_DIR / "reports" / f"disney_trend_{d}.json")

    data = collect_all(news_per_query=args.news_per_query)

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    Path(out_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f"\n✅ JSON 保存: {out_path}")
    print(f"   ニュース合計: {len(data['google_news']) + len(data['extra_feeds'])} 件")
    return 0


if __name__ == '__main__':
    sys.exit(main())
