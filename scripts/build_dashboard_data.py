#!/usr/bin/env python3
"""
公開ダッシュボード用 JSON ビルダー

明日の予測 + ホットトピック + 直近インサイト を 1つの JSON にまとめて
`dashboard/data/latest.json` に書き出す。

このファイルは GitHub Pages で `disney-ai-wait.github.io` に配信される想定。
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

OUT_DIR = PROJECT_DIR / "dashboard" / "data"
OUT_FILE = OUT_DIR / "latest.json"


def _safe_get_predictions(date: str, park: str) -> dict | None:
    """daily_instagram_post の _get_insights を借りる"""
    try:
        from daily_instagram_post import _get_insights
        return _get_insights(date, park)
    except Exception as e:
        print(f"⚠️ predictions fail ({park}): {e}")
        return None


def _safe_get_trends(date: str) -> dict:
    p = PROJECT_DIR / "reports" / f"disney_trend_{date}.json"
    if not p.exists():
        # fallback: latest available
        candidates = sorted(PROJECT_DIR.glob("reports/disney_trend_*.json"))
        if candidates:
            p = candidates[-1]
        else:
            return {"news": []}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        news = []
        for n in (data.get("news") or [])[:8]:
            news.append({
                "title":     n.get("title", ""),
                "url":       n.get("url", ""),
                "source":    n.get("source", ""),
                "topic":     n.get("topic", "📰 その他"),
                "published": n.get("published", ""),
            })
        return {"news": news}
    except Exception as e:
        print(f"⚠️ trends fail: {e}")
        return {"news": []}


def _safe_get_accuracy() -> dict:
    """直近の答え合わせから的中率を読む"""
    candidates = sorted(PROJECT_DIR.glob("reports/recap_*.json"))
    if not candidates:
        return {}
    try:
        data = json.loads(candidates[-1].read_text(encoding='utf-8'))
        return {
            "hit_rate_pct": data.get("hit_rate_pct"),
            "n_samples":    data.get("n_samples"),
            "since":        data.get("since"),
        }
    except Exception:
        return {}


def _safe_get_best_time() -> dict:
    p = PROJECT_DIR / "reports" / "best_time_all.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        stats = data.get("stats", [])
        if not stats:
            return {}
        ranked = sorted(stats, key=lambda s: s.get("reach_mean", 0), reverse=True)[:3]
        WD = ['月', '火', '水', '木', '金', '土', '日']
        return {
            "top": [{
                "weekday": WD[s["weekday"]],
                "bucket":  s["bucket"],
                "reach_mean": s["reach_mean"],
                "save_rate_pct": s["save_rate_pct"],
                "n": s["n"],
            } for s in ranked]
        }
    except Exception:
        return {}


def _safe_get_insights() -> dict:
    """直近の週次インサイトから 3-5本の bullet を取り出す"""
    candidates = sorted(PROJECT_DIR.glob("reports/instagram_weekly_*.json"))
    if not candidates:
        return {"bullets": []}
    try:
        data = json.loads(candidates[-1].read_text(encoding='utf-8'))
        bullets = data.get("bullets") or []
        # フォールバック: トップ投稿リーチを bullet 化
        if not bullets and data.get("top_posts"):
            for p in (data.get("top_posts") or [])[:3]:
                bullets.append(f"🏆 {p.get('post_type', '?')} 直近最高 reach {p.get('reach', 0)}")
        return {"bullets": bullets[:5]}
    except Exception:
        return {"bullets": []}


def build(date: str | None = None) -> dict:
    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    sea_ins = _safe_get_predictions(date, 'sea')
    land_ins = _safe_get_predictions(date, 'land')

    def _pack(ins):
        if not ins:
            return None
        top = []
        for name, w in (ins.get("attr_max_list") or [])[:5]:
            top.append({"name": name, "wait": w})
        return {
            "avg_wait":         ins.get("avg_wait"),
            "congestion":       ins.get("congestion"),
            "calm_time":        ins.get("calm_time"),
            "peak_time":        ins.get("peak_time"),
            "top_attractions":  top,
        }

    out = {
        "target_date":     date,
        "updated_at_jst":  datetime.now().strftime('%Y-%m-%d %H:%M JST'),
        "predictions":     {"sea": _pack(sea_ins), "land": _pack(land_ins)},
        "trends":          _safe_get_trends(date),
        "accuracy":        _safe_get_accuracy(),
        "best_time":       _safe_get_best_time(),
        "insights":        _safe_get_insights(),
    }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--out", default=str(OUT_FILE))
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = build(args.date)
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                          default=str), encoding='utf-8')
    print(f"✅ {args.out}")
    print(json.dumps({
        "target_date": data["target_date"],
        "sea_avg":     data["predictions"]["sea"] and data["predictions"]["sea"]["avg_wait"],
        "land_avg":    data["predictions"]["land"] and data["predictions"]["land"]["avg_wait"],
        "news_n":      len(data["trends"]["news"]),
        "accuracy":    data["accuracy"].get("hit_rate_pct"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
