#!/usr/bin/env python3
"""
Reels カバー画像 A/B テスト 自動計測 & レポート

仕組み:
  - daily_reel_post.py が `cover_variant` を `instagram_post_log.csv` の
    extra (JSON) カラムに記録している。
  - 本スクリプトはそのログから Reels 投稿を抽出し、Graph API で
    各メディアの insights (reach / views / saved / likes / comments / shares /
    total_interactions) を取得する。
  - variant (new / old) でグループ集計し、リフト率と勝者を提示する。

使い方:
    python scripts/cover_ab_report.py
    python scripts/cover_ab_report.py --days 21
    python scripts/cover_ab_report.py --since 2026-04-15
    python scripts/cover_ab_report.py --out reports/cover_ab.md --json reports/cover_ab.json

注意:
  - 公開直後 (24h 以内) は数値が伸びている途中なので、一定期間置いたほうがフェアな比較になる。
  - サンプルが小さい (n<10) 段階では「効果サイズ」のみ参考に。p値は出さない。
"""

from __future__ import annotations

import os
import sys
import csv
import json
import math
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

# Reels で取得するメトリクス
METRICS_REELS = ["reach", "views", "saved", "likes", "comments",
                 "shares", "total_interactions"]


# =============================================================================
# 投稿ログ読み込み (extra JSON を含む新スキーマ + 旧スキーマ後方互換)
# =============================================================================
def load_post_log(path: Path):
    """instagram_post_log.csv を読んで Reels 投稿のみを返す"""
    if not path.exists():
        return []
    rows = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("post_type") != "reel":
                continue
            extra_raw = (r.get("extra") or "").strip()
            extra = {}
            if extra_raw:
                try:
                    # 書き込み時に "," → "|" でサニタイズしているので戻す
                    extra = json.loads(extra_raw.replace("|", ","))
                except Exception:
                    extra = {}
            rows.append({
                "posted_at": r.get("posted_at", ""),
                "media_id": r.get("media_id", ""),
                "image": r.get("image", ""),
                "caption_preview": r.get("caption_preview", ""),
                "extra": extra,
            })
    return rows


def filter_by_date(rows, since_dt):
    out = []
    for r in rows:
        try:
            ts = datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if ts >= since_dt:
            out.append(r)
    return out


# =============================================================================
# Graph API
# =============================================================================
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


def fetch_insights(media_id: str) -> dict:
    """1 メディアのインサイトを取得 (一括 → 失敗時 個別フォールバック)"""
    out = {}
    try:
        data = _api_get(f"{media_id}/insights",
                        {"metric": ",".join(METRICS_REELS)})
        for m in data.get("data", []):
            v = m.get("values") or []
            if v:
                out[m.get("name")] = v[0].get("value", 0)
        return out
    except Exception:
        pass

    for metric in METRICS_REELS:
        try:
            data = _api_get(f"{media_id}/insights", {"metric": metric})
            for m in data.get("data", []):
                v = m.get("values") or []
                if v:
                    out[m.get("name")] = v[0].get("value", 0)
        except Exception:
            continue
    return out


def fetch_media_meta(media_id: str) -> dict:
    """permalink, タイムスタンプ等"""
    fields = "id,permalink,timestamp,media_product_type,like_count,comments_count"
    try:
        return _api_get(media_id, {"fields": fields})
    except Exception:
        return {}


# =============================================================================
# 集計
# =============================================================================
def aggregate(records: list) -> dict:
    """
    records: [{variant, park, insights{...}}]
    variant ごとに集計して dict を返す。
    """
    groups = defaultdict(list)
    for r in records:
        variant = r.get("variant", "unknown")
        groups[variant].append(r)

    summary = {}
    for variant, rs in groups.items():
        n = len(rs)
        reach = [int(x["insights"].get("reach", 0) or 0) for x in rs]
        views = [int(x["insights"].get("views", 0) or 0) for x in rs]
        saves = [int(x["insights"].get("saved", 0) or 0) for x in rs]
        likes = [int(x["insights"].get("likes", 0) or 0) for x in rs]
        comments = [int(x["insights"].get("comments", 0) or 0) for x in rs]
        shares = [int(x["insights"].get("shares", 0) or 0) for x in rs]
        interactions = [int(x["insights"].get("total_interactions", 0) or 0) for x in rs]

        # CTR proxy: 動画再生 / リーチ (高い = サムネが効いてる)
        ctr_per_post = []
        for v, r_ in zip(views, reach):
            if r_ > 0:
                ctr_per_post.append(v / r_ * 100)

        # save rate
        save_rate_per_post = []
        for s, r_ in zip(saves, reach):
            if r_ > 0:
                save_rate_per_post.append(s / r_ * 100)

        summary[variant] = {
            "n": n,
            "reach":      _stats(reach),
            "views":      _stats(views),
            "saved":      _stats(saves),
            "likes":      _stats(likes),
            "comments":   _stats(comments),
            "shares":     _stats(shares),
            "interactions": _stats(interactions),
            "ctr_pct":    _stats(ctr_per_post),       # views / reach
            "save_rate":  _stats(save_rate_per_post), # saves / reach
            "by_park": _by_park(rs),
        }
    return summary


def _stats(arr):
    if not arr:
        return {"n": 0, "sum": 0, "mean": 0.0, "median": 0.0, "max": 0}
    return {
        "n": len(arr),
        "sum": int(sum(arr)) if all(isinstance(x, (int, float)) for x in arr) else sum(arr),
        "mean": float(statistics.mean(arr)),
        "median": float(statistics.median(arr)),
        "max": int(max(arr)) if all(isinstance(x, (int, float)) for x in arr) else max(arr),
    }


def _by_park(records):
    parks = defaultdict(list)
    for r in records:
        parks[r.get("park", "unknown")].append(r)
    out = {}
    for p, rs in parks.items():
        out[p] = {
            "n": len(rs),
            "avg_reach": _avg(int(x["insights"].get("reach", 0) or 0) for x in rs),
            "avg_views": _avg(int(x["insights"].get("views", 0) or 0) for x in rs),
            "avg_saves": _avg(int(x["insights"].get("saved", 0) or 0) for x in rs),
        }
    return out


def _avg(it):
    arr = list(it)
    return float(statistics.mean(arr)) if arr else 0.0


def lift(new_val: float, old_val: float) -> float:
    """new vs old の相対リフト (%). old=0 のときは inf 防止で 0"""
    if old_val == 0:
        return 0.0
    return (new_val - old_val) / old_val * 100.0


# =============================================================================
# Markdown レンダリング
# =============================================================================
def render_markdown(summary: dict, n_total: int, since_str: str,
                    records: list) -> str:
    new = summary.get("new", {})
    old = summary.get("old", {})

    lines = []
    lines.append(f"# 🧪 Reels カバー A/B テスト レポート")
    lines.append("")
    lines.append(f"- 集計期間: **{since_str}** 以降")
    lines.append(f"- 対象 Reels 投稿数: **{n_total}**")
    lines.append(f"  - new (専用デザイン): **{new.get('n', 0)}**")
    lines.append(f"  - old (1フレーム目): **{old.get('n', 0)}**")
    lines.append("")

    if not (new and old):
        lines.append("> ⚠️ どちらか一方の variant データがありません。両方の投稿が蓄積されてから再実行してください。")
        return "\n".join(lines)

    if min(new.get('n', 0), old.get('n', 0)) < 3:
        lines.append("> ⚠️ サンプル数が少ないため (n<3 のグループあり)、参考値としてご覧ください。")
        lines.append("")

    # ===== 主要指標比較 =====
    lines.append("## 主要指標 (1投稿あたり 平均)")
    lines.append("")
    lines.append("| 指標 | new (新カバー) | old (旧カバー) | リフト (new vs old) | 勝者 |")
    lines.append("|---|---:|---:|---:|:---:|")

    KEY_METRICS = [
        ("リーチ",         "reach",        "{:.1f}",  False),
        ("再生数 (views)", "views",        "{:.1f}",  False),
        ("**CTR** (views/reach)", "ctr_pct", "{:.2f}%", True),
        ("保存",           "saved",        "{:.2f}",  False),
        ("**保存率**",      "save_rate",    "{:.2f}%", True),
        ("いいね",         "likes",        "{:.2f}",  False),
        ("コメント",       "comments",     "{:.2f}",  False),
        ("シェア",         "shares",       "{:.2f}",  False),
        ("総インタラクション", "interactions", "{:.2f}", False),
    ]

    for label, key, fmt, is_pct in KEY_METRICS:
        nv = new.get(key, {}).get("mean", 0)
        ov = old.get(key, {}).get("mean", 0)
        lf = lift(nv, ov)
        winner = "🆕" if nv > ov else ("🅾️" if ov > nv else "—")
        lf_str = f"{lf:+.1f}%" if ov > 0 else "—"
        lines.append(f"| {label} | {fmt.format(nv)} | {fmt.format(ov)} | {lf_str} | {winner} |")

    lines.append("")

    # ===== 累計 =====
    lines.append("## 累計 (合計値)")
    lines.append("")
    lines.append("| 指標 | new | old |")
    lines.append("|---|---:|---:|")
    for label, key in [("リーチ", "reach"), ("再生数", "views"),
                        ("保存", "saved"), ("いいね", "likes"),
                        ("コメント", "comments"), ("シェア", "shares")]:
        lines.append(f"| {label} | {new.get(key, {}).get('sum', 0)} | {old.get(key, {}).get('sum', 0)} |")
    lines.append("")

    # ===== Park 別 =====
    lines.append("## パーク別 内訳 (平均)")
    lines.append("")
    lines.append("| パーク | variant | n | リーチ | 再生 | 保存 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for variant in ('new', 'old'):
        bp = summary.get(variant, {}).get("by_park", {})
        for park in ('sea', 'land'):
            v = bp.get(park, {})
            if not v:
                continue
            lines.append(f"| {park} | {variant} | {v['n']} | "
                         f"{v['avg_reach']:.1f} | {v['avg_views']:.1f} | {v['avg_saves']:.1f} |")
    lines.append("")

    # ===== 勝者判定 (CTR と保存率の two-of-three majority) =====
    new_ctr = new.get("ctr_pct", {}).get("mean", 0)
    old_ctr = old.get("ctr_pct", {}).get("mean", 0)
    new_save = new.get("save_rate", {}).get("mean", 0)
    old_save = old.get("save_rate", {}).get("mean", 0)
    new_views = new.get("views", {}).get("mean", 0)
    old_views = old.get("views", {}).get("mean", 0)

    n_wins = sum([new_ctr > old_ctr, new_save > old_save, new_views > old_views])
    o_wins = sum([new_ctr < old_ctr, new_save < old_save, new_views < old_views])

    lines.append("## 🏆 暫定 勝者")
    lines.append("")
    if n_wins > o_wins:
        lines.append(f"### 🆕 **新カバー (専用デザイン)** が優勢 ({n_wins} / 3 指標)")
        if new_ctr > 0 and old_ctr > 0:
            lines.append(f"- CTR: **{new_ctr:.2f}%** vs {old_ctr:.2f}% (リフト {lift(new_ctr, old_ctr):+.1f}%)")
        if new_save > 0 and old_save > 0:
            lines.append(f"- 保存率: **{new_save:.2f}%** vs {old_save:.2f}% (リフト {lift(new_save, old_save):+.1f}%)")
    elif o_wins > n_wins:
        lines.append(f"### 🅾️ **旧カバー (1フレーム目)** が優勢 ({o_wins} / 3 指標)")
    else:
        lines.append("### ⚖️ 引き分け — もう少し蓄積が必要です")
    lines.append("")

    # ===== 個別投稿一覧 (直近10件) =====
    lines.append("## 個別投稿 (直近10件)")
    lines.append("")
    lines.append("| 投稿日時 (UTC) | パーク | variant | リーチ | 再生 | 保存 | likes | リンク |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")
    sorted_records = sorted(records, key=lambda r: r.get("posted_at", ""), reverse=True)[:10]
    for r in sorted_records:
        ins = r.get("insights", {})
        lines.append(
            f"| {r.get('posted_at', '')} "
            f"| {r.get('park', '')} "
            f"| {r.get('variant', '')} "
            f"| {ins.get('reach', 0)} "
            f"| {ins.get('views', 0)} "
            f"| {ins.get('saved', 0)} "
            f"| {ins.get('likes', 0)} "
            f"| {('[link](' + r.get('permalink', '') + ')') if r.get('permalink') else ''} |"
        )
    lines.append("")

    # ===== 改善Tips =====
    lines.append("## 次の打ち手")
    lines.append("")
    if n_wins > o_wins:
        lines.append("- ✅ **新カバーで全リールを統一**してOK。")
        lines.append("- 📌 次は新カバーの中で更なる細かいA/B (色 / コピー / KPIサイズ) を試す。")
    elif o_wins > n_wins:
        lines.append("- ⚠️ 新カバーが旧より弱い → 何が原因か仮説検証する。")
        lines.append("  - 文字情報過多？ → KPI減らす / 装飾を整理")
        lines.append("  - 動きがある旧カバーの方がアテンション取れている可能性 → 動きあるカバー(GIF風)を試す")
    else:
        lines.append("- 引き分け中。2週間 (28本) ほど蓄積後に再評価。")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}*")
    return "\n".join(lines)


# =============================================================================
# メイン
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Reels カバー A/B レポート生成")
    parser.add_argument("--log", type=str, default=str(DEFAULT_LOG),
                        help="instagram_post_log.csv パス")
    parser.add_argument("--days", type=int, default=14,
                        help="集計期間 (過去N日)")
    parser.add_argument("--since", type=str, default=None,
                        help="集計開始日 YYYY-MM-DD (--days より優先)")
    parser.add_argument("--out", type=str, default="reports/cover_ab.md",
                        help="Markdown出力パス")
    parser.add_argument("--json", type=str, default="reports/cover_ab.json",
                        help="JSON出力パス")
    parser.add_argument("--dry-run", action="store_true",
                        help="API呼ばずローカルログだけで集計 (insightsは0)")
    args = parser.parse_args()

    log_path = Path(args.log)
    rows = load_post_log(log_path)
    print(f"📥 ログ読み込み: {log_path} → 全Reels {len(rows)}件")

    if args.since:
        since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)
    since_str = since_dt.strftime("%Y-%m-%d")

    rows = filter_by_date(rows, since_dt)
    print(f"📅 期間フィルタ ({since_str}〜): {len(rows)}件")

    # variant 抽出
    target_rows = []
    for r in rows:
        ext = r.get("extra") or {}
        v = ext.get("cover_variant")
        if v not in ("new", "old"):
            # variant が記録されていない (旧スキーマ) は対象外
            continue
        target_rows.append({
            "posted_at": r["posted_at"],
            "media_id": r["media_id"],
            "park": ext.get("park", ""),
            "variant": v,
        })

    print(f"🧪 variant タグ付き: {len(target_rows)}件")
    if not target_rows:
        print("⚠️ variant タグ付き Reels がありません。daily_reel_post.py で投稿を蓄積してください。")
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        Path(args.out).write_text(
            f"# Reels カバー A/B レポート\n\n"
            f"対象データなし ({since_str} 以降の variant タグ付き Reels が0件)。\n",
            encoding='utf-8')
        return 0

    # Insights 取得
    if args.dry_run:
        print("🔍 ドライラン: Insights API は呼ばず 0 で集計")
        for r in target_rows:
            r["insights"] = {}
            r["permalink"] = ""
    else:
        if not ACCESS_TOKEN:
            print("❌ INSTAGRAM_ACCESS_TOKEN が未設定です")
            return 1
        for i, r in enumerate(target_rows, 1):
            print(f"  📊 [{i}/{len(target_rows)}] {r['media_id']} ({r['variant']}/{r['park']})")
            try:
                r["insights"] = fetch_insights(r["media_id"])
            except Exception as e:
                print(f"     ⚠️ insights 失敗: {e}")
                r["insights"] = {}
            try:
                meta = fetch_media_meta(r["media_id"])
                r["permalink"] = meta.get("permalink", "")
            except Exception:
                r["permalink"] = ""

    # 集計 & 出力
    summary = aggregate(target_rows)

    md = render_markdown(summary, n_total=len(target_rows),
                         since_str=since_str, records=target_rows)

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    Path(args.out).write_text(md, encoding='utf-8')
    print(f"\n✅ Markdown: {args.out}")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or '.', exist_ok=True)
        Path(args.json).write_text(
            json.dumps({
                "since": since_str,
                "n_total": len(target_rows),
                "summary": summary,
                "records": [
                    {k: v for k, v in r.items() if k != 'insights'} | {"insights": r.get("insights", {})}
                    for r in target_rows
                ],
            }, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8')
        print(f"✅ JSON: {args.json}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
