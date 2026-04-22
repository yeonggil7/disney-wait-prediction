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
# ※ follows / profile_visits / profile_activity は v22+ で追加 (フォロワー増加要因の特定に重要)
METRICS_FEED = ["reach", "views", "saved", "likes", "comments", "shares",
                "total_interactions", "follows", "profile_visits"]
METRICS_REELS = ["reach", "views", "saved", "likes", "comments", "shares",
                 "total_interactions", "follows", "profile_visits"]
METRICS_STORY = ["reach", "views", "replies", "navigation", "follows", "profile_visits"]


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


# =============================================================================
# フォロワー増加要因 分析
# =============================================================================
def fetch_follower_history(since_dt: datetime, until_dt: datetime) -> dict:
    """
    アカウントレベルの follower_count 推移 (日次) を取得。

    Returns:
        {
            "current": 1234,                # 取得時点
            "delta_in_period": +50,         # 期間中の増加 (= sum of daily delta)
            "daily": [{"date": "2026-04-15", "value": 12}, ...]  # 日次の新規 follow 数
        }
    """
    out = {"current": 0, "delta_in_period": 0, "daily": []}
    if not IG_USER_ID or not ACCESS_TOKEN:
        return out

    # 現在のフォロワー数
    try:
        meta = _api_get(IG_USER_ID, {"fields": "followers_count"})
        out["current"] = int(meta.get("followers_count", 0) or 0)
    except Exception as e:
        print(f"   ⚠️ followers_count 取得失敗: {e}")

    # 日次 follower_count (追加数)
    try:
        # IG insights は max 30 日まで一度に取得可能
        days = min(30, (until_dt - since_dt).days + 1)
        params = {
            "metric": "follower_count",
            "period": "day",
            "since": int((until_dt - timedelta(days=days)).timestamp()),
            "until": int(until_dt.timestamp()),
        }
        data = _api_get(f"{IG_USER_ID}/insights", params)
        for m in data.get("data", []):
            for v in m.get("values", []):
                date = v.get("end_time", "")[:10]
                val = int(v.get("value", 0) or 0)
                out["daily"].append({"date": date, "value": val})
        out["delta_in_period"] = sum(d["value"] for d in out["daily"])
    except Exception as e:
        print(f"   ⚠️ follower_count history 取得失敗: {e}")

    return out


def attribute_followers_to_posts(media_with_insights: list,
                                  follower_history: dict) -> dict:
    """
    各投稿のフォロワー増加への寄与度を推定する。

    優先度:
      1. 投稿レベルの `follows` メトリクスが取れていれば、それを直接使用 (確度高)
      2. 取れていなければ、投稿日と日次 follower_count の相関 (proxy) を計算

    Returns:
        {
          "by_post": [{"post": item, "follows_estimated": int, "method": "direct"|"proxy"}],
          "method": "direct" | "proxy" | "none",
          "top_drivers": [...],  # 上位5件
          "by_post_type": {"FEED": {...}, "REELS": {...}, "STORY": {...}},
        }
    """
    by_post = []
    method = "none"

    # 1. 投稿レベルの follows メトリクスを優先
    direct_total = 0
    for m in media_with_insights:
        f = m["insights"].get("follows", 0) or 0
        if f and isinstance(f, (int, float)) and f > 0:
            direct_total += int(f)
            by_post.append({
                "post": m,
                "follows_estimated": int(f),
                "profile_visits": int(m["insights"].get("profile_visits", 0) or 0),
                "method": "direct",
            })

    if direct_total > 0:
        method = "direct"

    # 2. 取れない場合は proxy: 当日の follower_count delta を投稿のリーチで按分
    if method == "none" and follower_history.get("daily"):
        daily_map = {d["date"]: d["value"] for d in follower_history["daily"]}
        # 同じ日の投稿で reach を按分
        from collections import defaultdict
        posts_by_date = defaultdict(list)
        for m in media_with_insights:
            ts = m.get("timestamp", "")
            if not ts:
                continue
            date_key = ts[:10]
            posts_by_date[date_key].append(m)
        for date_key, posts in posts_by_date.items():
            new_followers = daily_map.get(date_key, 0)
            if new_followers <= 0 or not posts:
                continue
            total_reach = sum(p["insights"].get("reach", 0) or 0 for p in posts) or 1
            for p in posts:
                share = (p["insights"].get("reach", 0) or 0) / total_reach
                est = int(round(new_followers * share))
                if est > 0:
                    by_post.append({
                        "post": p,
                        "follows_estimated": est,
                        "profile_visits": int(p["insights"].get("profile_visits", 0) or 0),
                        "method": "proxy",
                    })
        method = "proxy" if by_post else "none"

    by_post.sort(key=lambda x: x["follows_estimated"], reverse=True)
    top_drivers = by_post[:5]

    # タイプ別集計
    from collections import defaultdict
    by_type = defaultdict(lambda: {"n": 0, "follows": 0, "reach": 0, "profile_visits": 0})
    for entry in by_post:
        m = entry["post"]
        pt = (m.get("media_product_type") or m.get("media_type") or "POST").upper()
        bt = by_type[pt]
        bt["n"] += 1
        bt["follows"] += entry["follows_estimated"]
        bt["reach"] += int(m["insights"].get("reach", 0) or 0)
        bt["profile_visits"] += entry["profile_visits"]

    # 効率指標 (follows per 1k reach)
    by_type_out = {}
    for pt, v in by_type.items():
        eff = (v["follows"] / v["reach"] * 1000) if v["reach"] else 0.0
        pv2f = (v["follows"] / v["profile_visits"] * 100) if v["profile_visits"] else 0.0
        by_type_out[pt] = {
            **v,
            "follows_per_1k_reach": eff,
            "profile_visit_to_follow_pct": pv2f,
        }

    return {
        "by_post": by_post,
        "method": method,
        "top_drivers": top_drivers,
        "by_post_type": by_type_out,
    }


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


def _render_follower_section(follower_hist: dict, attribution: dict,
                              since_dt: datetime, until_dt: datetime) -> list:
    """フォロワー増加要因分析セクションを Markdown 行配列で返す"""
    lines = []
    lines.append("## 👥 フォロワー増加要因 分析")
    lines.append("")

    current = follower_hist.get("current", 0)
    delta = follower_hist.get("delta_in_period", 0)
    days = (until_dt - since_dt).days or 1
    arrow = "🟢" if delta > 0 else ("🔴" if delta < 0 else "⚪")

    lines.append(f"- 現在のフォロワー: **{current:,}**")
    lines.append(f"- 期間中の増減 ({days}日): {arrow} **{delta:+,}** "
                 f"(1日平均 {delta / days:+.1f})")

    if not follower_hist.get("daily"):
        lines.append("")
        lines.append("> ⚠️ follower_count history が取得できませんでした。")
        lines.append("> 権限 (`instagram_manage_insights`) と Business アカウント設定をご確認ください。")
        return lines

    # 日次推移の小型グラフ (テキストスパークライン)
    daily = follower_hist["daily"]
    if daily:
        lines.append("")
        lines.append("### 日次フォロワー増加 (期間内)")
        lines.append("")
        lines.append("| 日付 | 新規 follow | 累積 |")
        lines.append("|---|---:|---:|")
        cum = 0
        for d in daily[-14:]:  # 直近14日まで
            cum += d["value"]
            lines.append(f"| {d['date']} | {d['value']:+d} | {cum:+d} |")
        lines.append("")

    # 投稿レベル要因
    method = attribution.get("method", "none")
    method_note = {
        "direct": "✅ Graph API の `follows` メトリクスから直接計測",
        "proxy":  "📊 投稿日の follower_count delta を投稿リーチで按分した推定値",
        "none":   "⚠️ 投稿×フォロワー増加の対応が取れませんでした",
    }.get(method, "")
    lines.append(f"### 投稿別 寄与度 ({method_note})")
    lines.append("")

    drivers = attribution.get("top_drivers", [])
    if drivers:
        lines.append("**🏆 フォロワー獲得 TOP5 投稿**")
        lines.append("")
        lines.append("| # | 種別 | 推定 follows | reach | プロフィール訪問 | 投稿 |")
        lines.append("|---|---|---:|---:|---:|---|")
        for i, d in enumerate(drivers, 1):
            m = d["post"]
            ins = m["insights"]
            pt = (m.get("media_product_type") or m.get("media_type") or "POST").upper()
            head = (m.get("caption") or "").split("\n")[0][:30]
            link = m.get("permalink", "")
            lines.append(
                f"| {i} | {pt} | **{d['follows_estimated']}** "
                f"| {ins.get('reach', 0):,} | {d.get('profile_visits', 0)} "
                f"| [{head}…]({link}) |"
            )
        lines.append("")
    else:
        lines.append("> 寄与度を分析できる投稿がありませんでした。")
        lines.append("")

    by_type = attribution.get("by_post_type", {})
    if by_type:
        lines.append("**🎯 投稿タイプ別 効率**")
        lines.append("")
        lines.append("| 種別 | 投稿数 | 推定 follows 合計 | follows/1k リーチ | profile→follow率 |")
        lines.append("|---|---:|---:|---:|---:|")
        for pt, v in sorted(by_type.items(), key=lambda kv: kv[1]["follows"], reverse=True):
            lines.append(
                f"| {pt} | {v['n']} | **{v['follows']}** "
                f"| {v['follows_per_1k_reach']:.2f} "
                f"| {v['profile_visit_to_follow_pct']:.2f}% |"
            )
        lines.append("")

        # 自動洞察
        lines.append("**💡 ハイライト**")
        # 最も follows/1k reach が高いタイプ
        best_eff = max(by_type.items(), key=lambda kv: kv[1]["follows_per_1k_reach"], default=None)
        if best_eff and best_eff[1]["follows_per_1k_reach"] > 0:
            pt, v = best_eff
            lines.append(f"- **{pt}** が最もフォロワー獲得効率が高い "
                         f"(リーチ1,000 あたり {v['follows_per_1k_reach']:.1f} follows)")
            lines.append(f"  → このタイプの投稿頻度を増やすと効率的")

        # 最も follows 絶対値が多いタイプ
        best_total = max(by_type.items(), key=lambda kv: kv[1]["follows"], default=None)
        if best_total and best_total[1]["follows"] > 0 and best_total[0] != (best_eff[0] if best_eff else None):
            pt, v = best_total
            lines.append(f"- 絶対数では **{pt}** が最多 ({v['follows']} follows)")

        # 1日あたりに換算
        if delta > 0:
            target_30d = delta / days * 30
            lines.append(f"- このペースだと **30日で +{target_30d:,.0f}** フォロワー予測")
            if target_30d < 100:
                lines.append("  - 目標 (+500/月) には不足。Reels/Story の頻度UP or プロフィール最適化を検討")
            elif target_30d < 300:
                lines.append("  - 順調なペース。トップ要因の投稿タイプを継続")
            else:
                lines.append("  - 強力なペース。bio の CTA を磨いて変換率をさらに上げるチャンス")
        lines.append("")

    return lines


def _render_markdown(media_with_insights: list, summary: dict,
                      since_dt: datetime, until_dt: datetime,
                      follower_hist: dict | None = None,
                      attribution: dict | None = None) -> str:
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

    # ===== フォロワー増加要因 =====
    if follower_hist is not None:
        lines.extend(_render_follower_section(
            follower_hist, attribution or {"by_post": [], "method": "none",
                                           "top_drivers": [], "by_post_type": {}},
            since_dt, until_dt))

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

    # フォロワー増加要因 分析
    print(f"\n📈 フォロワー増加要因を分析中...")
    follower_hist = fetch_follower_history(since_dt, until_dt)
    attribution = attribute_followers_to_posts(enriched, follower_hist)
    print(f"   現在 follower: {follower_hist.get('current', 0):,}  "
          f"期間中 delta: {follower_hist.get('delta_in_period', 0):+,}")
    print(f"   寄与度算出方式: {attribution.get('method')}")

    md = _render_markdown(enriched, summary, since_dt, until_dt,
                          follower_hist=follower_hist,
                          attribution=attribution)

    out_path = PROJECT_DIR / args.out
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n✅ レポート保存: {out_path}")

    if args.json_out:
        json_path = PROJECT_DIR / args.json_out
        # 投稿オブジェクトはそのまま、attribution の by_post に含まれる post 参照は重複なので除去
        attr_serializable = {
            "method": attribution.get("method"),
            "by_post_type": attribution.get("by_post_type", {}),
            "top_drivers": [
                {"follows_estimated": d["follows_estimated"],
                 "profile_visits": d["profile_visits"],
                 "method": d["method"],
                 "media_id": d["post"].get("id"),
                 "permalink": d["post"].get("permalink"),
                 "media_product_type": d["post"].get("media_product_type"),
                 "media_type": d["post"].get("media_type")}
                for d in attribution.get("top_drivers", [])
            ],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": summary,
                "follower_history": follower_hist,
                "attribution": attr_serializable,
                "media": enriched,
            }, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ JSON保存: {json_path}")

    print("\n" + "=" * 60)
    print(f"投稿数: {summary['n_posts']} (story {summary['n_stories']})")
    print(f"合計リーチ: {summary['total_reach']:,}")
    print(f"保存率: {summary['save_rate_pct']:.2f}%  シェア率: {summary['share_rate_pct']:.2f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
