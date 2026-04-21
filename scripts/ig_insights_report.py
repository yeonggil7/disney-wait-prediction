#!/usr/bin/env python3
"""
Instagram Insights 取得 & 週次レポート生成

Graph API から最近の投稿のインサイトを取得して以下を出力:
  - per-post: reach / impressions / saved / likes / comments / shares
  - 集計: 平均 / 合計 / 保存率 / シェア率
  - 上位/下位 投稿
  - レポートを Markdown で保存

使い方:
    python scripts/ig_insights_report.py                      # 過去7日
    python scripts/ig_insights_report.py --days 14
    python scripts/ig_insights_report.py --since 2026-04-01
    python scripts/ig_insights_report.py --out instagram_weekly.md
"""

import os
import sys
import json
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
if INSTAGRAM_GRAPH_BACKEND == "instagram":
    GRAPH_BASE = "https://graph.instagram.com"
else:
    GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

IG_USER_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")


# 投稿タイプ別のインサイト指標 (2024〜 Graph API v21+)
# ※ impressions は廃止 → views を使用 (画像投稿でも利用可)
METRICS_FEED = ["reach", "views", "saved", "likes", "comments", "shares", "total_interactions"]
METRICS_REELS = ["reach", "views", "saved", "likes", "comments", "shares", "total_interactions"]
METRICS_STORY = ["reach", "views", "replies", "navigation"]


def _api_get(path: str, params: dict = None) -> dict:
    p = dict(params or {})
    p["access_token"] = ACCESS_TOKEN
    r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
    if not r.ok:
        try:
            err = r.json().get("error", {})
        except Exception:
            err = {"message": r.text[:200]}
        raise RuntimeError(f"API error {r.status_code}: {err.get('message')}")
    return r.json()


def _list_recent_media(since_dt: datetime, limit_pages: int = 5):
    """最近のメディアを取得 (since_dt 以降)"""
    fields = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
    media = []
    next_url = None
    pages = 0
    params = {"fields": fields, "limit": 25}

    while pages < limit_pages:
        if next_url:
            r = requests.get(next_url, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            data = _api_get(f"{IG_USER_ID}/media", params)

        items = data.get("data", [])
        if not items:
            break

        stop = False
        for item in items:
            ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
            if ts < since_dt:
                stop = True
                break
            media.append(item)
        if stop:
            break

        paging = data.get("paging", {})
        next_url = paging.get("next")
        if not next_url:
            break
        pages += 1
    return media


def _fetch_insights(media_id: str, media_type: str, product_type: str = "") -> dict:
    """メディア種別に応じたインサイトを取得（指標が無効でも個別フォールバック）"""
    pt = (product_type or "").upper()
    mt = (media_type or "").upper()
    if pt == "REELS":
        metrics = METRICS_REELS
    elif pt == "STORY":
        metrics = METRICS_STORY
    elif mt == "VIDEO":
        metrics = METRICS_REELS
    else:
        metrics = METRICS_FEED

    out = {}
    # まず一括 → ダメなら個別取得
    try:
        data = _api_get(f"{media_id}/insights",
                        {"metric": ",".join(metrics)})
        for m in data.get("data", []):
            values = m.get("values", [])
            if values:
                out[m.get("name")] = values[0].get("value", 0)
        return out
    except Exception:
        pass

    for metric in metrics:
        try:
            data = _api_get(f"{media_id}/insights", {"metric": metric})
            for m in data.get("data", []):
                values = m.get("values", [])
                if values:
                    out[m.get("name")] = values[0].get("value", 0)
        except Exception:
            continue
    return out


def _summarize(media_with_insights: list) -> dict:
    """全体集計"""
    feed = [m for m in media_with_insights
            if (m.get("media_product_type") or "").upper() != "STORY"]
    total_reach = sum(m["insights"].get("reach", 0) or 0 for m in feed)
    total_views = sum(m["insights"].get("views", 0) or 0 for m in feed)
    total_saves = sum(m["insights"].get("saved", 0) or 0 for m in feed)
    total_likes = sum(m["insights"].get("likes", 0) or 0 for m in feed)
    total_comments = sum(m["insights"].get("comments", 0) or 0 for m in feed)
    total_shares = sum(m["insights"].get("shares", 0) or 0 for m in feed)
    n = len(feed) or 1
    save_rate = (total_saves / total_reach * 100) if total_reach else 0
    share_rate = (total_shares / total_reach * 100) if total_reach else 0
    return {
        "n_posts": len(feed),
        "n_stories": len(media_with_insights) - len(feed),
        "total_reach": total_reach,
        "total_views": total_views,
        "avg_reach": total_reach / n,
        "total_saves": total_saves,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "save_rate_pct": save_rate,
        "share_rate_pct": share_rate,
    }


def _post_label(item: dict) -> str:
    cap = item.get("caption") or ""
    head = cap.split("\n")[0][:50]
    pt = (item.get("media_product_type") or "").upper()
    mt = (item.get("media_type") or "").upper()
    tag = pt or mt or "POST"
    return f"[{tag}] {head}"


def _render_markdown(media_with_insights: list, summary: dict,
                      since_dt: datetime, until_dt: datetime) -> str:
    lines = []
    lines.append("# Instagram 週次インサイトレポート")
    lines.append("")
    lines.append(f"- 期間: **{since_dt.date()} 〜 {until_dt.date()}**")
    lines.append(f"- 集計時刻: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## サマリ (フィード/リール)")
    lines.append("")
    lines.append(f"- 投稿数: **{summary['n_posts']}** 件 (ストーリーズ {summary['n_stories']} 件)")
    lines.append(f"- 合計リーチ: **{summary['total_reach']:,}**  / 表示回数: {summary['total_views']:,}")
    lines.append(f"- 平均リーチ/投稿: {summary['avg_reach']:.0f}")
    lines.append(f"- 保存数 合計: **{summary['total_saves']:,}**  / 保存率: **{summary['save_rate_pct']:.2f}%**")
    lines.append(f"- シェア数 合計: **{summary['total_shares']:,}**  / シェア率: **{summary['share_rate_pct']:.2f}%**")
    lines.append(f"- いいね合計: {summary['total_likes']:,}  / コメント: {summary['total_comments']:,}")
    lines.append("")

    feed = [m for m in media_with_insights
            if (m.get("media_product_type") or "").upper() != "STORY"]
    feed_sorted = sorted(feed,
                         key=lambda m: m["insights"].get("reach", 0) or 0,
                         reverse=True)

    if feed_sorted:
        top = feed_sorted[:3]
        lines.append("## 🏆 リーチTOP3 (フィード)")
        lines.append("")
        for i, m in enumerate(top, 1):
            ins = m["insights"]
            lines.append(
                f"{i}. {_post_label(m)}\n"
                f"   - reach {ins.get('reach', 0):,} / saves {ins.get('saved', 0)} "
                f"/ shares {ins.get('shares', 0)} / likes {ins.get('likes', 0)}\n"
                f"   - {m.get('permalink', '')}"
            )
        lines.append("")

    save_sorted = sorted(feed,
                         key=lambda m: m["insights"].get("saved", 0) or 0,
                         reverse=True)
    if save_sorted:
        lines.append("## 💾 保存数TOP3")
        lines.append("")
        for i, m in enumerate(save_sorted[:3], 1):
            ins = m["insights"]
            lines.append(
                f"{i}. saves={ins.get('saved', 0)} / reach={ins.get('reach', 0):,}  "
                f"{_post_label(m)}\n   {m.get('permalink', '')}"
            )
        lines.append("")

    lines.append("## 全投稿一覧")
    lines.append("")
    lines.append("| 日時 (UTC) | 種別 | reach | saves | shares | likes | URL |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for m in sorted(media_with_insights, key=lambda x: x.get("timestamp", ""), reverse=True):
        ts = m.get("timestamp", "").replace("T", " ").replace("+0000", "")[:16]
        ins = m["insights"]
        pt = (m.get("media_product_type") or m.get("media_type") or "").upper()
        lines.append(
            f"| {ts} | {pt} | {ins.get('reach', '-')} | {ins.get('saved', '-')} | "
            f"{ins.get('shares', '-')} | {ins.get('likes', '-')} | "
            f"[link]({m.get('permalink', '')}) |"
        )
    lines.append("")

    lines.append("## 改善のヒント")
    if summary['save_rate_pct'] < 3:
        lines.append("- 保存率が低めです。**カルーセル化** & **保存推奨CTA** を冒頭で訴求してみましょう。")
    if summary['share_rate_pct'] < 0.5:
        lines.append("- シェア率が低めです。**「友達を誘って行こう」系の文言** や **驚きの統計** を入れて拡散させましょう。")
    if summary['n_posts'] < 5:
        lines.append("- 週の投稿数が少なめです。**リール+ストーリーズ** を組み合わせ週7投稿を目標にしましょう。")
    if not summary.get('total_reach'):
        lines.append("- インサイトが取れていない可能性があります。アクセストークンの権限と Business アカウント設定を確認してください。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7,
                        help='何日前まで遡るか (デフォルト 7)')
    parser.add_argument('--since', type=str, default=None,
                        help='起点日 YYYY-MM-DD (--days より優先)')
    parser.add_argument('--out', type=str, default='instagram_weekly_report.md')
    parser.add_argument('--json-out', type=str, default=None,
                        help='生インサイトを JSON 保存 (任意)')
    args = parser.parse_args()

    if not IG_USER_ID or not ACCESS_TOKEN:
        print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID / INSTAGRAM_ACCESS_TOKEN が未設定")
        return 1

    until_dt = datetime.now(timezone.utc)
    if args.since:
        since_dt = datetime.strptime(args.since, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    else:
        since_dt = until_dt - timedelta(days=args.days)

    print(f"📥 メディア一覧取得 ({since_dt.date()} 〜)")
    media = _list_recent_media(since_dt)
    print(f"   {len(media)} 件取得")

    enriched = []
    for m in media:
        print(f"   - insights取得: {m['id']} ({(m.get('media_product_type') or m.get('media_type'))})")
        ins = _fetch_insights(m["id"],
                              m.get("media_type", ""),
                              m.get("media_product_type", ""))
        m["insights"] = ins
        enriched.append(m)

    summary = _summarize(enriched)
    md = _render_markdown(enriched, summary, since_dt, until_dt)

    out_path = PROJECT_DIR / args.out
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n✅ レポート保存: {out_path}")

    if args.json_out:
        json_path = PROJECT_DIR / args.json_out
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "media": enriched},
                      f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ JSON保存: {json_path}")

    print("\n" + "=" * 60)
    print(f"投稿数: {summary['n_posts']} (story {summary['n_stories']})")
    print(f"合計リーチ: {summary['total_reach']:,}")
    print(f"保存率: {summary['save_rate_pct']:.2f}%  シェア率: {summary['share_rate_pct']:.2f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
