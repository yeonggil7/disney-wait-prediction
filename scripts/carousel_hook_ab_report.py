#!/usr/bin/env python3
"""
カルーセル 1枚目フック A/B レポート

cover_ab_report.py の hook 版。
instagram_post_log.csv の post_type=carousel + extra に hook_variant が
記録されているものを対象に、reach / saved / engagement_rate を集計し、
4変種 (V1〜V4) のうちどれが伸びるか可視化する。

使い方:
    python scripts/carousel_hook_ab_report.py
    python scripts/carousel_hook_ab_report.py --days 30
    python scripts/carousel_hook_ab_report.py --dry-run
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
GRAPH_BASE = ("https://graph.instagram.com" if INSTAGRAM_GRAPH_BACKEND == "instagram"
              else f"https://graph.facebook.com/{GRAPH_API_VERSION}")
ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
DEFAULT_LOG = PROJECT_DIR / "instagram_post_log.csv"

VARIANTS = ['V1_curiosity', 'V2_stat', 'V3_warning', 'V4_cta']
METRICS = ["reach", "views", "saved", "likes", "comments", "shares"]


def _api_get(path: str, params: dict = None) -> dict:
    p = dict(params or {})
    p["access_token"] = ACCESS_TOKEN
    r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_insights(media_id: str) -> dict:
    out = {}
    try:
        data = _api_get(f"{media_id}/insights", {"metric": ",".join(METRICS)})
        for m in data.get("data", []):
            v = m.get("values") or []
            if v:
                out[m.get("name")] = v[0].get("value", 0)
        return out
    except Exception:
        pass
    for metric in METRICS:
        try:
            data = _api_get(f"{media_id}/insights", {"metric": metric})
            for m in data.get("data", []):
                v = m.get("values") or []
                if v:
                    out[m.get("name")] = v[0].get("value", 0)
        except Exception:
            continue
    return out


def load_carousel_posts(log_path: Path, since_dt: datetime) -> list:
    if not log_path.exists():
        return []
    rows = []
    with open(log_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get("post_type") != "carousel":
                continue
            try:
                ts = datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < since_dt:
                continue
            extra_raw = (r.get("extra") or "").strip()
            extra = {}
            if extra_raw:
                try:
                    extra = json.loads(extra_raw.replace("|", ","))
                except Exception:
                    extra = {}
            v = extra.get("hook_variant")
            if v not in VARIANTS:
                continue
            rows.append({
                "posted_at": r["posted_at"],
                "media_id": r["media_id"],
                "hook_variant": v,
            })
    return rows


def aggregate(records: list) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r["hook_variant"]].append(r)

    summary = {}
    for v in VARIANTS:
        rs = groups.get(v, [])
        n = len(rs)
        reach = [int(x["insights"].get("reach", 0) or 0) for x in rs]
        saves = [int(x["insights"].get("saved", 0) or 0) for x in rs]
        likes = [int(x["insights"].get("likes", 0) or 0) for x in rs]
        comments = [int(x["insights"].get("comments", 0) or 0) for x in rs]
        shares = [int(x["insights"].get("shares", 0) or 0) for x in rs]
        save_rate = sum(saves) / sum(reach) * 100 if sum(reach) else 0.0
        eng = sum(likes) + sum(comments) + sum(shares)
        eng_rate = eng / sum(reach) * 100 if sum(reach) else 0.0
        summary[v] = {
            "n": n,
            "reach_sum": sum(reach),
            "reach_mean": statistics.mean(reach) if reach else 0,
            "saves_sum": sum(saves),
            "save_rate_pct": save_rate,
            "engagement_sum": eng,
            "engagement_rate_pct": eng_rate,
        }
    return summary


def render_markdown(summary: dict, n_total: int, since_str: str) -> str:
    lines = []
    lines.append("# 🪝 カルーセル 1枚目フック A/B レポート")
    lines.append("")
    lines.append(f"- 集計期間: **{since_str} 以降**")
    lines.append(f"- 対象 カルーセル投稿数: **{n_total}**")
    lines.append("")
    lines.append("| variant | n | reach平均 | save率 | engage率 |")
    lines.append("|---|---:|---:|---:|---:|")
    for v in VARIANTS:
        s = summary.get(v, {})
        lines.append(
            f"| **{v}** | {s.get('n', 0)} "
            f"| {s.get('reach_mean', 0):.0f} "
            f"| {s.get('save_rate_pct', 0):.2f}% "
            f"| {s.get('engagement_rate_pct', 0):.2f}% |"
        )
    lines.append("")

    # 勝者判定 (save_rate でランキング、トップが2位の +20%以上 で確定)
    ranked = sorted(VARIANTS,
                    key=lambda v: summary.get(v, {}).get("save_rate_pct", 0),
                    reverse=True)
    top = ranked[0]
    sec = ranked[1] if len(ranked) > 1 else None
    top_v = summary.get(top, {}).get("save_rate_pct", 0)
    sec_v = summary.get(sec, {}).get("save_rate_pct", 0) if sec else 0
    lines.append("## 🏆 暫定勝者")
    lines.append("")
    if all(summary.get(v, {}).get("n", 0) >= 8 for v in VARIANTS) and sec_v > 0 and top_v >= sec_v * 1.2:
        lines.append(f"### 🎉 **{top}** が確定勝者")
        lines.append(f"- save率 {top_v:.2f}% vs 2位 {sec} {sec_v:.2f}% (+{(top_v - sec_v) / sec_v * 100:.0f}%)")
        lines.append("")
        lines.append("→ resolve_hook_variant が次回以降この variant を返します。")
    else:
        lines.append(f"### ⚖️ 暫定 1位: **{top}** (save率 {top_v:.2f}%)")
        lines.append("- 全 variant n>=8 かつ 2位の +20% を満たすまで待機")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--days", type=int, default=21)
    parser.add_argument("--out", default="reports/carousel_hook_ab.md")
    parser.add_argument("--json", default="reports/carousel_hook_ab.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)
    rows = load_carousel_posts(Path(args.log), since_dt)
    print(f"📥 hook variant タグ付き carousel: {len(rows)}件")

    if args.dry_run or not ACCESS_TOKEN:
        for r in rows:
            r["insights"] = {}
    else:
        for i, r in enumerate(rows, 1):
            print(f"   [{i}/{len(rows)}] {r['media_id']} ({r['hook_variant']})")
            try:
                r["insights"] = fetch_insights(r["media_id"])
            except Exception as e:
                print(f"      ⚠️ {e}")
                r["insights"] = {}

    summary = aggregate(rows)
    md = render_markdown(summary, len(rows), since_dt.date().isoformat())

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    Path(args.out).write_text(md, encoding='utf-8')
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps({
        "since": since_dt.date().isoformat(),
        "n_total": len(rows),
        "summary": summary,
    }, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(f"✅ {args.out}")
    print(f"✅ {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
