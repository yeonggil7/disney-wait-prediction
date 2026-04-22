#!/usr/bin/env python3
"""
ベスト投稿時間 自動分析

仕組み:
  - instagram_post_log.csv (post_via_instagram_graph が記録) の各メディアについて
    Graph API で reach / saved / likes を取得
  - 投稿時刻 (UTC → JST 変換) を「曜日 × 時間帯バケット (3h)」で集計
  - 各バケットの平均リーチ / 保存 / エンゲージメント率を出して
    `reports/best_time.md` & `reports/best_time.json` を生成

使い方:
    python scripts/best_time_analyzer.py
    python scripts/best_time_analyzer.py --days 60
    python scripts/best_time_analyzer.py --type reel
    python scripts/best_time_analyzer.py --type feed --out reports/best_time_feed.md
"""

from __future__ import annotations

import os
import sys
import csv
import json
import argparse
import statistics
from collections import defaultdict
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

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
DEFAULT_LOG = PROJECT_DIR / "instagram_post_log.csv"

JST = timezone(timedelta(hours=9))
WEEKDAYS_JA = ['月', '火', '水', '木', '金', '土', '日']
# 3時間バケット (00-03, 03-06, ..., 21-24)
TIME_BUCKETS = [
    (0, 3, "00-03"), (3, 6, "03-06"), (6, 9, "06-09"),
    (9, 12, "09-12"), (12, 15, "12-15"), (15, 18, "15-18"),
    (18, 21, "18-21"), (21, 24, "21-24"),
]


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


def fetch_insights(media_id: str, post_type: str) -> dict:
    """投稿のインサイトを取得 (一括 → 個別フォールバック)"""
    if post_type in ("reel", "carousel"):
        metrics = ["reach", "views", "saved", "likes", "comments", "shares"]
    elif post_type == "story":
        metrics = ["reach", "views", "replies"]
    else:
        metrics = ["reach", "saved", "likes", "comments", "shares"]

    out = {}
    try:
        data = _api_get(f"{media_id}/insights", {"metric": ",".join(metrics)})
        for m in data.get("data", []):
            v = m.get("values") or []
            if v:
                out[m.get("name")] = v[0].get("value", 0)
        return out
    except Exception:
        pass
    for metric in metrics:
        try:
            data = _api_get(f"{media_id}/insights", {"metric": metric})
            for m in data.get("data", []):
                v = m.get("values") or []
                if v:
                    out[m.get("name")] = v[0].get("value", 0)
        except Exception:
            continue
    return out


def load_posts(log_path: Path, since_dt: datetime,
               post_type_filter: str | None = None) -> list:
    if not log_path.exists():
        return []
    rows = []
    with open(log_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if post_type_filter and r.get("post_type") != post_type_filter:
                continue
            try:
                ts = datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < since_dt:
                continue
            rows.append({
                "posted_at_utc": ts,
                "posted_at_jst": ts.astimezone(JST),
                "media_id": r.get("media_id", ""),
                "post_type": r.get("post_type", ""),
            })
    return rows


def bucket_of(hour: int) -> str:
    for s, e, label in TIME_BUCKETS:
        if s <= hour < e:
            return label
    return "?"


def aggregate(posts: list) -> dict:
    """{ (weekday_idx, bucket_label): {reach: [...], saves: [...], ...} }"""
    groups = defaultdict(lambda: defaultdict(list))
    for p in posts:
        wd = p["posted_at_jst"].weekday()
        bk = bucket_of(p["posted_at_jst"].hour)
        ins = p.get("insights", {})
        groups[(wd, bk)]["reach"].append(int(ins.get("reach", 0) or 0))
        groups[(wd, bk)]["saved"].append(int(ins.get("saved", 0) or 0))
        groups[(wd, bk)]["likes"].append(int(ins.get("likes", 0) or 0))
        groups[(wd, bk)]["views"].append(int(ins.get("views", 0) or 0))
        groups[(wd, bk)]["comments"].append(int(ins.get("comments", 0) or 0))
        groups[(wd, bk)]["shares"].append(int(ins.get("shares", 0) or 0))
        groups[(wd, bk)]["n"].append(1)
    out = {}
    for (wd, bk), arrs in groups.items():
        n = sum(arrs["n"])
        reach_mean = statistics.mean(arrs["reach"]) if arrs["reach"] else 0
        save_rate = (
            sum(arrs["saved"]) / sum(arrs["reach"]) * 100
            if sum(arrs["reach"]) else 0.0
        )
        eng_rate = (
            (sum(arrs["likes"]) + sum(arrs["comments"]) + sum(arrs["shares"]))
            / sum(arrs["reach"]) * 100
            if sum(arrs["reach"]) else 0.0
        )
        out[(wd, bk)] = {
            "n": n,
            "reach_mean": reach_mean,
            "save_rate_pct": save_rate,
            "engagement_rate_pct": eng_rate,
            "views_mean": statistics.mean(arrs["views"]) if arrs["views"] else 0,
        }
    return out


def render_markdown(stats: dict, post_type: str, n_total: int,
                    since_dt: datetime) -> str:
    lines = []
    lines.append(f"# ⏰ ベスト投稿時間 分析  ({post_type or 'all'})")
    lines.append("")
    lines.append(f"- 集計期間: **{since_dt.date()} 以降**  / 投稿数: **{n_total}**")
    lines.append(f"- 時間は **JST**  / 数値は1投稿あたり 平均")
    lines.append("")

    if not stats:
        lines.append("> ⚠️ サンプルがありません。投稿実績が貯まるまで再実行してください。")
        return "\n".join(lines)

    # ───── 主要表 (曜日 × バケット, リーチ平均) ─────
    lines.append("## 平均リーチ (曜日 × 時間帯)")
    lines.append("")
    header = "| 曜日 \\ 時間帯 | " + " | ".join(b[2] for b in TIME_BUCKETS) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(TIME_BUCKETS) + 1))
    for wd in range(7):
        row = [WEEKDAYS_JA[wd]]
        for s, e, label in TIME_BUCKETS:
            v = stats.get((wd, label))
            if v and v["n"]:
                row.append(f"**{v['reach_mean']:.0f}** (n={v['n']})")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # ───── TOP5 バケット (リーチ) ─────
    bukets = [(k, v) for k, v in stats.items() if v["n"] >= 1]
    bukets.sort(key=lambda kv: kv[1]["reach_mean"], reverse=True)
    lines.append("## 🏆 リーチ TOP5")
    lines.append("")
    lines.append("| # | 曜日 | 時間帯 | n | reach平均 | save率 | エンゲ率 |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for i, ((wd, bk), v) in enumerate(bukets[:5], 1):
        lines.append(
            f"| {i} | {WEEKDAYS_JA[wd]} | {bk} | {v['n']} "
            f"| {v['reach_mean']:.0f} | {v['save_rate_pct']:.2f}% | {v['engagement_rate_pct']:.2f}% |"
        )
    lines.append("")

    # ───── TOP3 (save率) ─────
    sv = sorted(bukets, key=lambda kv: kv[1]["save_rate_pct"], reverse=True)
    lines.append('## 💾 保存率 TOP3 (= 旅行プラン用に「保存」される時間帯)')
    lines.append("")
    for i, ((wd, bk), v) in enumerate(sv[:3], 1):
        lines.append(
            f"{i}. **{WEEKDAYS_JA[wd]} {bk}** — save率 {v['save_rate_pct']:.2f}% "
            f"(n={v['n']}, reach平均 {v['reach_mean']:.0f})"
        )
    lines.append("")

    # ───── 推奨アクション ─────
    if bukets:
        top_wd, top_bk = bukets[0][0]
        s, e, _ = next(b for b in TIME_BUCKETS if b[2] == top_bk)
        lines.append("## 💡 次の打ち手")
        lines.append("")
        lines.append(
            f"- **{WEEKDAYS_JA[top_wd]}曜の {top_bk} 帯** が一番リーチが伸びています。"
            f"その枠の cron を **{(s + e) // 2}:00 JST** にずらしてみる価値あり"
        )
        # JST → UTC
        jst_hour = (s + e) // 2
        utc_hour = (jst_hour - 9) % 24
        lines.append(
            f"  - GitHub Actions の cron 例: "
            f"`'0 {utc_hour} * * {top_wd if top_wd != 6 else 0}'`  "
            f"(UTC, weekday: 0=日 IG準拠だと {top_wd})"
        )
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ベスト投稿時間 分析")
    parser.add_argument("--log", type=str, default=str(DEFAULT_LOG))
    parser.add_argument("--days", type=int, default=30,
                        help="集計期間 (過去N日, デフォルト 30)")
    parser.add_argument("--type", type=str, default=None,
                        choices=[None, "feed", "carousel", "reel", "story"],
                        help="投稿タイプでフィルタ")
    parser.add_argument("--out", type=str, default=None,
                        help="Markdown 出力 (デフォルト reports/best_time_{type}.md)")
    parser.add_argument("--json", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Insights 取得をスキップ (時間帯分布のみ確認)")
    args = parser.parse_args()

    type_label = args.type or 'all'
    out = args.out or str(PROJECT_DIR / "reports" / f"best_time_{type_label}.md")
    out_json = args.json or str(PROJECT_DIR / "reports" / f"best_time_{type_label}.json")

    since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)
    posts = load_posts(Path(args.log), since_dt, post_type_filter=args.type)
    print(f"📥 ログ: {len(posts)}件 (since {since_dt.date()}, type={type_label})")

    if args.dry_run:
        for p in posts:
            p["insights"] = {}
    else:
        if not ACCESS_TOKEN:
            print("⚠️ INSTAGRAM_ACCESS_TOKEN 未設定 — dry-run 相当で進めます")
            for p in posts:
                p["insights"] = {}
        else:
            for i, p in enumerate(posts, 1):
                print(f"   [{i}/{len(posts)}] {p['media_id']} ({p['post_type']})")
                try:
                    p["insights"] = fetch_insights(p["media_id"], p["post_type"])
                except Exception as e:
                    print(f"      ⚠️ insights 失敗: {e}")
                    p["insights"] = {}

    stats = aggregate(posts)
    md = render_markdown(stats, type_label, len(posts), since_dt)

    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    Path(out).write_text(md, encoding='utf-8')
    print(f"✅ Markdown: {out}")

    if out_json:
        os.makedirs(os.path.dirname(out_json) or '.', exist_ok=True)
        Path(out_json).write_text(json.dumps({
            "since": since_dt.isoformat(),
            "type": type_label,
            "n_total": len(posts),
            "stats": [{"weekday": k[0], "bucket": k[1], **v}
                       for k, v in stats.items()],
        }, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print(f"✅ JSON: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
