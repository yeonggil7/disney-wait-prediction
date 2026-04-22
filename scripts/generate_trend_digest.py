#!/usr/bin/env python3
"""
ディズニートレンド 日次ダイジェスト生成

`disney_trend_collector.py` の出力 JSON を読んで
  (1) Markdown ダイジェスト    (毎朝のチェック用)
  (2) 1080x1350 画像           (個人参照 / 必要なら IG 投稿に転用可)
を生成する。

使い方:
    # 収集 → ダイジェスト まで一気に
    python scripts/generate_trend_digest.py --collect

    # 既存 JSON から
    python scripts/generate_trend_digest.py --input reports/disney_trend_2026-04-20.json

    # Markdown のみ (画像は重いので)
    python scripts/generate_trend_digest.py --collect --no-image
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

# 日本語フォント
_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']


# =============================================================================
# トピック抽出 (簡易NLP)
# =============================================================================
TOPIC_KEYWORDS = {
    "🎉 25周年・記念": ["25周年", "アニバーサリー", "ジュビリー"],
    "🏰 新エリア・新アトラク": ["ファンタジースプリングス", "新アトラク", "オープン", "新エリア", "リニューアル"],
    "🎁 グッズ・フード": ["グッズ", "メニュー", "フード", "限定", "発売"],
    "🎪 イベント・期間限定": ["イベント", "ハロウィン", "クリスマス", "イースター", "期間限定", "コラボ"],
    "💰 料金・チケット": ["料金", "値上げ", "改定", "値段", "チケット", "パスポート"],
    "👨‍👩‍👧 ファミリー・体験": ["体験", "感想", "ブログ", "レポ"],
    "🌟 著名人・トレンド": ["インスタ", "話題", "バズ", "公式", "発表"],
    "⚠️ トラブル・運休": ["休止", "中止", "運休", "故障", "トラブル", "事故"],
}


def categorize_news(news_items: list) -> dict:
    """ニュースをトピック別に分類"""
    out = {topic: [] for topic in TOPIC_KEYWORDS}
    out["📰 その他"] = []
    seen = set()
    for n in news_items:
        title = n.get("title", "")
        if not title or title in seen:
            continue
        seen.add(title)
        matched = False
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(k in title for k in keywords):
                out[topic].append(n)
                matched = True
                break
        if not matched:
            out["📰 その他"].append(n)
    # 空のトピックは削除
    return {t: items for t, items in out.items() if items}


# =============================================================================
# Markdown レンダリング
# =============================================================================
def render_markdown(data: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d (%a)")
    lines = []
    lines.append(f"# 🎢 ディズニートレンド ダイジェスト  {today}")
    lines.append("")
    lines.append(f"*収集時刻: {data.get('collected_at', '')}*")
    lines.append("")

    actuals = data.get("actuals", {})
    yest = actuals.get("yesterday", "")

    # ===== 1. 昨日の混雑サマリ =====
    lines.append(f"## 📊 昨日 ({yest}) の実績")
    lines.append("")
    lines.append("| パーク | 平均待ち | ピーク時間 | 一番混んだアトラクション |")
    lines.append("|---|---:|---|---|")
    for park in ('sea', 'land'):
        p = actuals.get("by_park", {}).get(park, {})
        if not p:
            continue
        park_label = "ディズニーシー" if park == "sea" else "ディズニーランド"
        avg = p.get("avg_wait")
        peak = p.get("peak_time", "—")
        bs = p.get("busiest", [])
        bs_str = f"{bs[0]['name']} ({bs[0]['avg_wait']}分)" if bs else "—"
        lines.append(f"| {park_label} | {avg if avg is not None else '—'}分 | {peak} | {bs_str} |")
    lines.append("")

    # ===== 2. 先週同曜日との比較 =====
    wow = actuals.get("wow_change", {})
    if wow:
        lines.append("### 📈 先週同曜日との比較")
        lines.append("")
        for park in ('sea', 'land'):
            w = wow.get(park)
            if not w:
                continue
            park_label = "シー" if park == "sea" else "ランド"
            arrow = "🔺" if w["diff_pct"] > 5 else ("🔻" if w["diff_pct"] < -5 else "➖")
            lines.append(f"- **{park_label}**: {w['current_avg']}分 vs 先週 {w['prev_avg']}分 → {arrow} **{w['diff_pct']:+.1f}%**")
        lines.append("")

    # ===== 3. 過去7日間の混雑トレンド =====
    weekly = actuals.get("weekly_trend", [])
    if weekly:
        lines.append("### 📅 過去7日間の混雑トレンド (1日平均待ち時間 / 分)")
        lines.append("")
        lines.append("| 日付 | シー | ランド |")
        lines.append("|---|---:|---:|")
        for d in weekly:
            sea = f"{d['sea']}" if d['sea'] is not None else "—"
            land = f"{d['land']}" if d['land'] is not None else "—"
            lines.append(f"| {d['date']} | {sea} | {land} |")
        lines.append("")

    # ===== 4. 昨日の最も空いてた・混んでた =====
    lines.append("### 🎯 昨日の狙い目 / 激混みアトラクション")
    lines.append("")
    for park in ('sea', 'land'):
        p = actuals.get("by_park", {}).get(park, {})
        if not p:
            continue
        park_label = "🌊 ディズニーシー" if park == "sea" else "🏰 ディズニーランド"
        lines.append(f"#### {park_label}")
        if p.get("calmest"):
            lines.append("- **狙い目** (待ち少ないライド top5):")
            for i, c in enumerate(p["calmest"][:5], 1):
                lines.append(f"  {i}. {c['name']} — 平均 {c['avg_wait']}分")
        if p.get("busiest"):
            lines.append("- **激混み** (待ち長いライド top5):")
            for i, b in enumerate(p["busiest"][:5], 1):
                lines.append(f"  {i}. {b['name']} — 平均 {b['avg_wait']}分")
        lines.append("")

    # ===== 5. ニュース・話題 =====
    google_news = data.get("google_news", [])
    extra = data.get("extra_feeds", [])
    all_news = google_news + extra

    lines.append("## 📰 今日のディズニー話題 (世間で何が起きてる？)")
    lines.append("")

    if all_news:
        cat = categorize_news(all_news)
        for topic, items in cat.items():
            if not items:
                continue
            lines.append(f"### {topic}  ({len(items)}件)")
            lines.append("")
            for n in items[:5]:
                src = n.get("source", "")
                pub = n.get("published", "")
                link = n.get("link", "")
                title = n.get("title", "")
                meta = []
                if src:
                    meta.append(src)
                if pub:
                    meta.append(pub)
                meta_str = " / ".join(meta) if meta else ""
                if link:
                    lines.append(f"- [{title}]({link})  *{meta_str}*")
                else:
                    lines.append(f"- {title}  *{meta_str}*")
            lines.append("")
    else:
        lines.append("> ニュース取得失敗 (RSS が一時的に応答無し等)")
        lines.append("")

    # ===== 6. Reddit (海外の反応) =====
    reddit = data.get("reddit", [])
    if reddit:
        lines.append("## 💬 Reddit 海外コミュニティで人気")
        lines.append("")
        lines.append("| Sub | Score | Comments | Title |")
        lines.append("|---|---:|---:|---|")
        for r in sorted(reddit, key=lambda x: x.get("score", 0), reverse=True)[:10]:
            lines.append(
                f"| r/{r['subreddit']} | {r['score']} | {r['comments']} | "
                f"[{r['title'][:80]}]({r['url']}) |"
            )
        lines.append("")

    # ===== 7. 投稿のヒント =====
    lines.append("## 💡 今日の投稿ヒント (運用補助)")
    lines.append("")
    cat = categorize_news(all_news) if all_news else {}
    tips = []
    if "🎉 25周年・記念" in cat:
        tips.append("**25周年関連がトレンド** — 「ジュビリー」関連ハッシュタグを今日の投稿に追加")
    if "🏰 新エリア・新アトラク" in cat:
        tips.append("**新エリア・新アトラク関連がホット** — ファンタジースプリングス系のアトラクを Reels で前面に")
    if "💰 料金・チケット" in cat:
        tips.append("**料金関連がバズり中** — 「コスパ良く回るルート」系の保存価値高い投稿を作るチャンス")
    if "⚠️ トラブル・運休" in cat:
        tips.append("**運休情報あり** — 該当アトラクが含まれる場合は予測から除外できているか確認")
    if not tips:
        tips.append("特に大きな話題なし — いつもの「翌日予報」「狙い目時間」テンプレで OK")

    # 自社データから派生する Tip
    for park in ('sea', 'land'):
        w = wow.get(park)
        if not w:
            continue
        park_label = "シー" if park == "sea" else "ランド"
        if w["diff_pct"] >= 15:
            tips.append(f"**{park_label}の混雑度が先週比 +{w['diff_pct']:.0f}%** → 「最近混んでる！」系の警告投稿を検討")
        elif w["diff_pct"] <= -15:
            tips.append(f"**{park_label}が先週比 {w['diff_pct']:.0f}%** → 「今は狙い目」系のポジティブ投稿のチャンス")

    for t in tips:
        lines.append(f"- {t}")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M JST')}*")
    return "\n".join(lines)


# =============================================================================
# 1080x1350 ダイジェスト画像
# =============================================================================
LIGHT_BG = '#FFF9F0'
TEXT_PRIMARY = '#2A2A2A'
TEXT_SECONDARY = '#666666'
ACCENT_SEA = '#1F8FBE'
ACCENT_LAND = '#D63384'


def render_image(data: dict, output_path: str):
    """1080x1350 のダイジェスト画像 (個人ダッシュボード用)"""
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    fig.patch.set_facecolor(LIGHT_BG)

    today = datetime.now().strftime("%Y-%m-%d (%a)")
    actuals = data.get("actuals", {})
    yest = actuals.get("yesterday", "")
    by_park = actuals.get("by_park", {})
    wow = actuals.get("wow_change", {})
    weekly = actuals.get("weekly_trend", [])

    # ヘッダー
    h_ax = fig.add_axes([0, 0.92, 1, 0.08])
    h_ax.set_xlim(0, 1); h_ax.set_ylim(0, 1); h_ax.axis('off')
    h_ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor='#2A2A2A'))
    h_ax.text(0.04, 0.55, "★ ディズニートレンド ダイジェスト",
              fontsize=24, ha='left', va='center',
              color='white', fontweight='bold')
    h_ax.text(0.96, 0.55, today,
              fontsize=18, ha='right', va='center', color='#FCC85A')

    # ===== 1. パーク別 KPI カード (上) =====
    for i, (park, accent) in enumerate([('sea', ACCENT_SEA), ('land', ACCENT_LAND)]):
        x_left = 0.04 + i * 0.48
        ax = fig.add_axes([x_left, 0.74, 0.44, 0.16])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0.01,rounding_size=0.04",
            facecolor='white', edgecolor=accent, linewidth=3,
        ))
        park_label = "ディズニーシー" if park == 'sea' else "ディズニーランド"
        ax.text(0.5, 0.85, park_label,
                fontsize=20, ha='center', va='center',
                color=accent, fontweight='bold')

        p = by_park.get(park, {})
        avg = p.get("avg_wait")
        ax.text(0.5, 0.55, f"{avg}分" if avg is not None else "—",
                fontsize=42, ha='center', va='center',
                color=TEXT_PRIMARY, fontweight='bold')
        ax.text(0.5, 0.34, f"昨日({yest}) の平均待ち",
                fontsize=12, ha='center', va='center',
                color=TEXT_SECONDARY)

        # WoW
        w = wow.get(park)
        if w:
            arrow = "▲" if w["diff_pct"] > 5 else ("▼" if w["diff_pct"] < -5 else "→")
            color = '#E84C5C' if w["diff_pct"] > 5 else ('#2BB673' if w["diff_pct"] < -5 else TEXT_SECONDARY)
            ax.text(0.5, 0.13,
                    f"先週比 {arrow} {w['diff_pct']:+.1f}%",
                    fontsize=13, ha='center', va='center',
                    color=color, fontweight='bold')

    # ===== 2. 過去7日間トレンド =====
    if weekly:
        ax = fig.add_axes([0.06, 0.46, 0.88, 0.22])
        ax.set_facecolor('white')
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')

        days = [d['date'][-5:] for d in weekly]
        seas = [d['sea'] if d['sea'] is not None else 0 for d in weekly]
        lands = [d['land'] if d['land'] is not None else 0 for d in weekly]
        x = list(range(len(days)))

        ax.plot(x, seas, marker='o', linewidth=2.5, color=ACCENT_SEA,
                markersize=8, label='シー', markerfacecolor='white',
                markeredgewidth=2.5)
        ax.plot(x, lands, marker='s', linewidth=2.5, color=ACCENT_LAND,
                markersize=8, label='ランド', markerfacecolor='white',
                markeredgewidth=2.5)

        ax.set_xticks(x)
        ax.set_xticklabels(days, fontsize=11, color=TEXT_SECONDARY)
        ax.set_ylabel("平均待ち時間 (分)", fontsize=11, color=TEXT_SECONDARY)
        ax.tick_params(axis='y', labelsize=10, colors=TEXT_SECONDARY)
        ax.legend(loc='upper left', fontsize=11, frameon=False)
        ax.grid(True, axis='y', linestyle=':', alpha=0.4)
        ax.set_title("● 過去7日間の混雑トレンド",
                     fontsize=15, color=TEXT_PRIMARY, fontweight='bold',
                     loc='left', pad=10)

    # ===== 3. 昨日のトップアトラクション (busiest sea / land) =====
    for i, (park, accent) in enumerate([('sea', ACCENT_SEA), ('land', ACCENT_LAND)]):
        x_left = 0.04 + i * 0.48
        ax = fig.add_axes([x_left, 0.22, 0.44, 0.21])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

        park_label = "シー 昨日 TOP5 混雑" if park == 'sea' else "ランド 昨日 TOP5 混雑"
        ax.text(0.04, 0.94, park_label,
                fontsize=14, ha='left', va='top',
                color=accent, fontweight='bold')

        p = by_park.get(park, {})
        bs = p.get("busiest", [])[:5]
        if not bs:
            ax.text(0.5, 0.5, "データなし",
                    fontsize=12, ha='center', va='center',
                    color=TEXT_SECONDARY)
            continue
        max_wait = max(b['avg_wait'] for b in bs) or 1
        for j, b in enumerate(bs):
            y = 0.78 - j * 0.16
            bar_w = (b['avg_wait'] / max_wait) * 0.55
            ax.add_patch(plt.Rectangle((0.42, y - 0.05), bar_w, 0.10,
                                       facecolor=accent, alpha=0.85))
            short = b['name'][:10] + ("…" if len(b['name']) > 10 else "")
            ax.text(0.40, y, short,
                    fontsize=11, ha='right', va='center',
                    color=TEXT_PRIMARY, fontweight='bold')
            ax.text(0.42 + bar_w + 0.01, y, f"{b['avg_wait']:.0f}分",
                    fontsize=11, ha='left', va='center',
                    color=accent, fontweight='bold')

    # ===== 4. 今日のニュースヘッドライン (3件) =====
    google_news = data.get("google_news", [])
    extra = data.get("extra_feeds", [])
    all_news = google_news + extra
    cat = categorize_news(all_news) if all_news else {}

    # 最初に見つかった3件のヘッドライン (重複排除しつつトピック横断)
    headlines = []
    seen_titles = set()
    for topic, items in cat.items():
        for n in items:
            t = n.get("title", "")
            if t and t not in seen_titles:
                seen_titles.add(t)
                headlines.append((topic, n))
                if len(headlines) >= 3:
                    break
        if len(headlines) >= 3:
            break

    ax = fig.add_axes([0.04, 0.04, 0.92, 0.16])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.02",
        facecolor='white', edgecolor='#FCC85A', linewidth=2,
    ))
    ax.text(0.02, 0.92, "■ 今日のディズニー話題",
            fontsize=14, ha='left', va='top',
            color=TEXT_PRIMARY, fontweight='bold')

    if headlines:
        for j, (topic, n) in enumerate(headlines):
            y = 0.70 - j * 0.22
            title = n.get("title", "")
            src = n.get("source", "")
            display_title = title[:42] + ("…" if len(title) > 42 else "")
            ax.text(0.03, y, "▶", fontsize=14,
                    ha='left', va='center', color='#FCC85A',
                    fontweight='bold')
            ax.text(0.07, y, display_title, fontsize=12,
                    ha='left', va='center', color=TEXT_PRIMARY,
                    fontweight='bold')
            if src:
                ax.text(0.97, y, f"— {src[:14]}", fontsize=10,
                        ha='right', va='center', color=TEXT_SECONDARY)
    else:
        ax.text(0.5, 0.45, "ニュース取得失敗",
                fontsize=12, ha='center', va='center',
                color=TEXT_SECONDARY)

    fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


# =============================================================================
# 1080x1920 ストーリーズ画像 (Instagram Stories)
# =============================================================================
STORY_BG = '#0F1B2D'          # ネイビー
STORY_CARD = '#FFFFFF'
STORY_ACCENT = '#FCC85A'      # ゴールド
STORY_TEXT_LIGHT = '#FFFFFF'
STORY_TEXT_MUTE = '#B7C2D4'


def _build_posting_hint(data: dict) -> str:
    """投稿ヒントを1〜2文で要約 (ストーリーズ用)"""
    actuals = data.get("actuals", {})
    wow = actuals.get("wow_change", {})
    google_news = data.get("google_news", [])
    extra = data.get("extra_feeds", [])
    cat = categorize_news(google_news + extra) if (google_news or extra) else {}

    if "🎉 25周年・記念" in cat:
        return "今日は25周年関連が話題！ #ジュビリー で投稿伸びそう"
    if "💰 料金・チケット" in cat:
        return "料金関連がバズり中。コスパ系の保存投稿チャンス"
    if "🏰 新エリア・新アトラク" in cat:
        return "新エリア系がホット。Reels で前面に出すのが◎"

    for park in ('sea', 'land'):
        w = wow.get(park)
        if not w:
            continue
        label = "シー" if park == 'sea' else "ランド"
        if w["diff_pct"] >= 15:
            return f"{label}が先週比 +{w['diff_pct']:.0f}%。混雑警告系が刺さる日"
        if w["diff_pct"] <= -15:
            return f"{label}が先週比 {w['diff_pct']:.0f}%。狙い目アピールのチャンス"

    return "通常運用日。狙い目時間 / 翌日予報の定番テンプレで OK"


def render_story_image(data: dict, output_path: str):
    """1080x1920 のストーリーズ用ダイジェスト画像 (フォロワー向け『今朝の速報』)"""
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor(STORY_BG)

    today = datetime.now().strftime("%Y年%-m月%-d日 (%a)")
    actuals = data.get("actuals", {})
    yest = actuals.get("yesterday", "")
    by_park = actuals.get("by_park", {})
    wow = actuals.get("wow_change", {})
    weekly = actuals.get("weekly_trend", [])

    google_news = data.get("google_news", [])
    extra = data.get("extra_feeds", [])
    all_news = google_news + extra
    cat = categorize_news(all_news) if all_news else {}

    # ───── ヘッダー (上部の余白＋タイトル) ─────
    h_ax = fig.add_axes([0, 0.91, 1, 0.09])
    h_ax.set_xlim(0, 1); h_ax.set_ylim(0, 1); h_ax.axis('off')
    h_ax.text(0.5, 0.70, "今朝のディズニー速報",
              fontsize=44, ha='center', va='center',
              color=STORY_TEXT_LIGHT, fontweight='bold')
    h_ax.text(0.5, 0.30, today,
              fontsize=22, ha='center', va='center', color=STORY_ACCENT)
    h_ax.plot([0.30, 0.70], [0.08, 0.08], color=STORY_ACCENT, linewidth=3)

    # ───── パーク別 KPI (上下に2枚) ─────
    for i, (park, accent) in enumerate([('sea', ACCENT_SEA), ('land', ACCENT_LAND)]):
        # 0.79 → 0.66 / 0.65 → 0.52
        y_top = 0.89 - i * 0.13
        ax = fig.add_axes([0.06, y_top - 0.11, 0.88, 0.11])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0.01,rounding_size=0.05",
            facecolor=STORY_CARD, edgecolor=accent, linewidth=4,
        ))
        park_label = "ディズニーシー" if park == 'sea' else "ディズニーランド"
        ax.text(0.05, 0.74, park_label,
                fontsize=22, ha='left', va='center',
                color=accent, fontweight='bold')
        ax.text(0.05, 0.32, f"昨日({yest}) の平均待ち",
                fontsize=13, ha='left', va='center',
                color=TEXT_SECONDARY)

        p = by_park.get(park, {})
        avg = p.get("avg_wait")
        ax.text(0.95, 0.65, f"{avg}" if avg is not None else "—",
                fontsize=58, ha='right', va='center',
                color=TEXT_PRIMARY, fontweight='bold')
        ax.text(0.97, 0.30, "分", fontsize=18,
                ha='right', va='center', color=TEXT_SECONDARY)

        # WoW
        w = wow.get(park)
        if w:
            arrow = "▲" if w["diff_pct"] > 5 else ("▼" if w["diff_pct"] < -5 else "→")
            color = '#E84C5C' if w["diff_pct"] > 5 else ('#2BB673' if w["diff_pct"] < -5 else TEXT_SECONDARY)
            ax.text(0.55, 0.30,
                    f"先週比 {arrow} {w['diff_pct']:+.1f}%",
                    fontsize=14, ha='left', va='center',
                    color=color, fontweight='bold')

    # ───── 7日間トレンド (折れ線) ─────
    if weekly:
        ax = fig.add_axes([0.10, 0.41, 0.84, 0.16])
        ax.set_facecolor(STORY_CARD)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')

        days = [d['date'][-5:] for d in weekly]
        seas = [d['sea'] if d['sea'] is not None else 0 for d in weekly]
        lands = [d['land'] if d['land'] is not None else 0 for d in weekly]
        x = list(range(len(days)))

        ax.plot(x, seas, marker='o', linewidth=3, color=ACCENT_SEA,
                markersize=10, label='シー', markerfacecolor='white',
                markeredgewidth=3)
        ax.plot(x, lands, marker='s', linewidth=3, color=ACCENT_LAND,
                markersize=10, label='ランド', markerfacecolor='white',
                markeredgewidth=3)

        ax.set_xticks(x)
        ax.set_xticklabels(days, fontsize=13, color=TEXT_SECONDARY)
        ax.set_ylabel("平均待ち (分)", fontsize=13, color=TEXT_SECONDARY)
        ax.tick_params(axis='y', labelsize=12, colors=TEXT_SECONDARY)
        ax.legend(loc='upper left', fontsize=13, frameon=False)
        ax.grid(True, axis='y', linestyle=':', alpha=0.4)
        ax.set_title("過去7日間の混雑トレンド",
                     fontsize=18, color=TEXT_PRIMARY, fontweight='bold',
                     loc='left', pad=10)

        bg_ax = fig.add_axes([0.04, 0.39, 0.92, 0.21], zorder=-1)
        bg_ax.set_xlim(0, 1); bg_ax.set_ylim(0, 1); bg_ax.axis('off')
        bg_ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.03",
            facecolor=STORY_CARD, edgecolor='none',
        ))

    # ───── 今日のニュースヘッドライン (最大3件) ─────
    headlines = []
    seen = set()
    for topic, items in cat.items():
        for n in items:
            t = n.get("title", "")
            if t and t not in seen:
                seen.add(t)
                headlines.append((topic, n))
                if len(headlines) >= 3:
                    break
        if len(headlines) >= 3:
            break

    ax = fig.add_axes([0.04, 0.18, 0.92, 0.18])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.03",
        facecolor=STORY_CARD, edgecolor=STORY_ACCENT, linewidth=3,
    ))
    ax.text(0.04, 0.92, "今日のディズニー話題",
            fontsize=18, ha='left', va='top',
            color=TEXT_PRIMARY, fontweight='bold')

    if headlines:
        for j, (topic, n) in enumerate(headlines):
            y = 0.68 - j * 0.22
            title = n.get("title", "")
            display_title = title[:34] + ("…" if len(title) > 34 else "")
            ax.text(0.05, y, "▶", fontsize=18,
                    ha='left', va='center', color=STORY_ACCENT,
                    fontweight='bold')
            ax.text(0.10, y, display_title, fontsize=15,
                    ha='left', va='center', color=TEXT_PRIMARY,
                    fontweight='bold')
    else:
        ax.text(0.5, 0.45, "ニュース取得失敗",
                fontsize=14, ha='center', va='center',
                color=TEXT_SECONDARY)

    # ───── 投稿ヒント / 一言 ─────
    hint = _build_posting_hint(data)
    ax = fig.add_axes([0.04, 0.10, 0.92, 0.06])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.5, 0.5, "★ " + hint,
            fontsize=16, ha='center', va='center',
            color=STORY_ACCENT, fontweight='bold')

    # ───── フッター (CTA) ─────
    f_ax = fig.add_axes([0, 0, 1, 0.08])
    f_ax.set_xlim(0, 1); f_ax.set_ylim(0, 1); f_ax.axis('off')
    f_ax.text(0.5, 0.62, "@disney_ai_wait で毎日チェック",
              fontsize=20, ha='center', va='center',
              color=STORY_TEXT_LIGHT, fontweight='bold')
    f_ax.text(0.5, 0.25, "AI予測 × 実測データで賢く回ろう",
              fontsize=13, ha='center', va='center',
              color=STORY_TEXT_MUTE)

    fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


# =============================================================================
# 1080x1920 「今日のホットトピック」ストーリーズ画像
# (フィードでは固定情報、ストーリーズでは "今この瞬間" のトレンド一点突破)
# =============================================================================
HOT_BG = '#0A1628'
HOT_ACCENT = '#FF5E62'        # 燃える赤 (HOT 訴求)
HOT_ACCENT_2 = '#FF9966'      # オレンジグラデ用
HOT_GOLD = '#FCC85A'

# トピック → カラー / メッセージ
TOPIC_STYLES = {
    "🎉 25周年・記念":       {"label": "25周年トピック", "color": '#FCC85A',
                              "cta": "ジュビリー の最新動向"},
    "🏰 新エリア・新アトラク": {"label": "新エリア",       "color": '#7B68EE',
                              "cta": "新アトラク 速報"},
    "🎁 グッズ・フード":      {"label": "グッズ/フード",   "color": '#FF6B9D',
                              "cta": "限定アイテム情報"},
    "🎪 イベント・期間限定":   {"label": "イベント",       "color": '#4ECDC4',
                              "cta": "期間限定の見逃し厳禁"},
    "💰 料金・チケット":      {"label": "料金/チケット",   "color": '#FFA500',
                              "cta": "コスパ系の保存推奨"},
    "👨‍👩‍👧 ファミリー・体験":  {"label": "体験レポ",       "color": '#95E1D3',
                              "cta": "リアルな声をチェック"},
    "🌟 著名人・トレンド":    {"label": "話題",           "color": '#F38181',
                              "cta": "今 SNS で話題"},
    "⚠️ トラブル・運休":     {"label": "運休/注意",      "color": '#E94560',
                              "cta": "行く前に必読"},
    "📰 その他":              {"label": "ディズニー速報",  "color": HOT_GOLD,
                              "cta": "気になるディズニーニュース"},
}


def select_hot_topic(data: dict) -> dict | None:
    """
    最も注目度が高いトピック+ヘッドラインを選ぶ。
      優先度 (高い順):
        1. ⚠️ トラブル・運休 (フォロワー価値が最高)
        2. 🎉 25周年・記念
        3. 🏰 新エリア・新アトラク
        4. 🎪 イベント・期間限定
        5. 💰 料金・チケット
        6. 🎁 グッズ・フード
        7. その他
      件数 2件以上のトピックを優先。
    """
    google_news = data.get("google_news", []) or []
    extra = data.get("extra_feeds", []) or []
    all_news = google_news + extra
    if not all_news:
        return None
    cat = categorize_news(all_news)

    priority = [
        "⚠️ トラブル・運休",
        "🎉 25周年・記念",
        "🏰 新エリア・新アトラク",
        "🎪 イベント・期間限定",
        "💰 料金・チケット",
        "🎁 グッズ・フード",
        "👨‍👩‍👧 ファミリー・体験",
        "🌟 著名人・トレンド",
        "📰 その他",
    ]

    # まず件数2件以上 + 優先度の高いトピック
    for t in priority:
        if t in cat and len(cat[t]) >= 2:
            return {"topic": t, "items": cat[t]}
    # 次に1件でもあるもの
    for t in priority:
        if t in cat:
            return {"topic": t, "items": cat[t]}
    return None


def render_hot_topic_story_image(data: dict, output_path: str) -> bool:
    """
    1080x1920 の「今日のホットトピック」ストーリーズ画像を生成。
      - 1トピックに絞り込んだ大きな見出し+3件のヘッドライン
      - 強いビジュアル (HOT バッジ・グラデ背景)
      - 下部 CTA: "詳しくはフィードへ" / "@disney_ai_wait"

    トピックが拾えなかったら False を返して呼び出し側で投稿スキップ。
    """
    hot = select_hot_topic(data)
    if not hot:
        return False

    topic = hot["topic"]
    items = hot["items"]
    style = TOPIC_STYLES.get(topic, TOPIC_STYLES["📰 その他"])
    accent = style["color"]
    cta = style["cta"]

    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor(HOT_BG)

    today_jp = datetime.now().strftime("%-m月%-d日")
    today_dow = ["月", "火", "水", "木", "金", "土", "日"][datetime.now().weekday()]

    # ───── 上部グラデーション帯 (アテンション) ─────
    grad_ax = fig.add_axes([0, 0.85, 1, 0.15])
    grad_ax.set_xlim(0, 1); grad_ax.set_ylim(0, 1); grad_ax.axis('off')
    import numpy as np
    grad = np.linspace(0, 1, 256).reshape(1, -1)
    grad = np.vstack([grad] * 16)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "hot", [HOT_ACCENT, HOT_ACCENT_2, accent], N=256)
    grad_ax.imshow(grad, aspect='auto', cmap=cmap, extent=[0, 1, 0, 1], alpha=0.92)
    # HOT バッジ
    grad_ax.add_patch(FancyBboxPatch(
        (0.04, 0.18), 0.20, 0.55,
        boxstyle="round,pad=0.01,rounding_size=0.04",
        facecolor='#FFFFFF', edgecolor='none'))
    grad_ax.text(0.14, 0.45, "HOT", fontsize=42, fontweight='bold',
                 color=HOT_ACCENT, ha='center', va='center')
    grad_ax.text(0.97, 0.55, f"{today_jp}({today_dow})",
                 fontsize=22, color='white', ha='right', va='center',
                 fontweight='bold')
    grad_ax.text(0.97, 0.22, "今日のディズニー速報",
                 fontsize=14, color='white', ha='right', va='center',
                 alpha=0.92)

    # ───── トピックラベル + 見出し ─────
    title_ax = fig.add_axes([0.06, 0.66, 0.88, 0.18])
    title_ax.set_xlim(0, 1); title_ax.set_ylim(0, 1); title_ax.axis('off')
    title_ax.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.01,rounding_size=0.05",
        facecolor='#FFFFFF', edgecolor=accent, linewidth=5))

    # トピックバッジ (パーク名のような扱い)
    title_ax.add_patch(FancyBboxPatch(
        (0.04, 0.72), 0.55, 0.22,
        boxstyle="round,pad=0.005,rounding_size=0.04",
        facecolor=accent, edgecolor='none'))
    title_ax.text(0.315, 0.83, style["label"],
                  fontsize=22, fontweight='bold',
                  color='white', ha='center', va='center')

    # メインヘッドライン (1件目を大きく)
    main = items[0]
    main_title = main.get("title", "")
    # 自然な改行: 30文字程度で折り返し
    def _wrap(s, n=22):
        out, line = [], ""
        for ch in s:
            line += ch
            if len(line) >= n and ch in "、。！？・ 　":
                out.append(line); line = ""
        if line:
            out.append(line)
        return "\n".join(out[:3]) + ("…" if len(out) > 3 else "")

    title_ax.text(0.04, 0.55, _wrap(main_title, 22),
                  fontsize=28, fontweight='bold',
                  color=TEXT_PRIMARY, ha='left', va='top')

    # ───── サブヘッドライン (2-3件) ─────
    sub_ax = fig.add_axes([0.06, 0.30, 0.88, 0.34])
    sub_ax.set_xlim(0, 1); sub_ax.set_ylim(0, 1); sub_ax.axis('off')
    sub_ax.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.03",
        facecolor='#FFFFFF', alpha=0.08, edgecolor=accent, linewidth=2))
    sub_ax.text(0.04, 0.94, f"■ 関連ニュース ({len(items)}件)",
                fontsize=18, fontweight='bold',
                color='white', ha='left', va='top')

    related = items[1:4] if len(items) > 1 else []
    if related:
        for j, n in enumerate(related):
            y = 0.78 - j * 0.26
            t = n.get("title", "")
            src = n.get("source", "")
            display = t[:46] + ("…" if len(t) > 46 else "")
            sub_ax.add_patch(plt.Rectangle((0.03, y - 0.10), 0.005, 0.18,
                                           facecolor=accent))
            sub_ax.text(0.06, y + 0.05, display,
                        fontsize=15, ha='left', va='top',
                        color='white', fontweight='bold')
            if src:
                sub_ax.text(0.06, y - 0.07, f"— {src}",
                            fontsize=11, ha='left', va='center',
                            color=STORY_TEXT_MUTE)
    else:
        sub_ax.text(0.5, 0.45,
                    "1件のヘッドラインのみ。\nメインを保存して回りましょう。",
                    fontsize=14, ha='center', va='center',
                    color=STORY_TEXT_MUTE, linespacing=1.6)

    # ───── 下部 CTA ─────
    cta_ax = fig.add_axes([0.06, 0.16, 0.88, 0.12])
    cta_ax.set_xlim(0, 1); cta_ax.set_ylim(0, 1); cta_ax.axis('off')
    cta_ax.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.01,rounding_size=0.05",
        facecolor=accent, edgecolor='none', alpha=0.92))
    cta_ax.text(0.5, 0.68, f"★ {cta} ★",
                fontsize=22, ha='center', va='center',
                color='white', fontweight='bold')
    cta_ax.text(0.5, 0.28, "詳しくは @disney_ai_wait のフィード →",
                fontsize=15, ha='center', va='center',
                color='white')

    # ───── フッター (ハンドル + サイン) ─────
    f_ax = fig.add_axes([0, 0.04, 1, 0.10])
    f_ax.set_xlim(0, 1); f_ax.set_ylim(0, 1); f_ax.axis('off')
    f_ax.text(0.5, 0.70, "@disney_ai_wait",
              fontsize=26, ha='center', va='center',
              color=HOT_GOLD, fontweight='bold')
    f_ax.text(0.5, 0.30, "AI で予測 × 毎日アップデート",
              fontsize=13, ha='center', va='center',
              color=STORY_TEXT_MUTE)

    fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return True


# =============================================================================
# CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="ディズニートレンド 日次ダイジェスト")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--collect", action="store_true",
                     help="その場で disney_trend_collector を呼んで集める")
    src.add_argument("--input", type=str,
                     help="既存の trend JSON ファイル")
    parser.add_argument("--out-md", type=str, default=None,
                        help="Markdown 出力 (デフォルト reports/disney_trend_digest_{date}.md)")
    parser.add_argument("--out-image", type=str, default=None,
                        help="画像出力 (デフォルト reports/disney_trend_digest_{date}.png)")
    parser.add_argument("--out-story", type=str, default=None,
                        help="ストーリーズ画像 (1080x1920) 出力 (デフォルト reports/disney_trend_story_{date}.png)")
    parser.add_argument("--no-image", action="store_true",
                        help="1080x1350 画像生成をスキップ")
    parser.add_argument("--story-image", action="store_true",
                        help="1080x1920 ストーリーズ画像も生成")
    parser.add_argument("--no-md", action="store_true",
                        help="Markdown 生成をスキップ")
    parser.add_argument("--news-per-query", type=int, default=8)
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")

    if args.collect:
        from disney_trend_collector import collect_all
        data = collect_all(news_per_query=args.news_per_query)
        # 元 JSON も保存
        json_path = PROJECT_DIR / "reports" / f"disney_trend_{today}.json"
        os.makedirs(json_path.parent, exist_ok=True)
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding='utf-8')
        print(f"📁 元 JSON: {json_path}")
    else:
        data = json.loads(Path(args.input).read_text(encoding='utf-8'))

    out_md = args.out_md or str(PROJECT_DIR / "reports" / f"disney_trend_digest_{today}.md")
    out_img = args.out_image or str(PROJECT_DIR / "reports" / f"disney_trend_digest_{today}.png")
    out_story = args.out_story or str(PROJECT_DIR / "reports" / f"disney_trend_story_{today}.png")

    if not args.no_md:
        md = render_markdown(data)
        os.makedirs(os.path.dirname(out_md) or '.', exist_ok=True)
        Path(out_md).write_text(md, encoding='utf-8')
        print(f"✅ Markdown: {out_md}")

    if not args.no_image:
        os.makedirs(os.path.dirname(out_img) or '.', exist_ok=True)
        try:
            render_image(data, out_img)
            print(f"✅ 画像: {out_img}")
        except Exception as e:
            print(f"⚠️ 画像生成失敗: {e}")

    if args.story_image:
        os.makedirs(os.path.dirname(out_story) or '.', exist_ok=True)
        try:
            render_story_image(data, out_story)
            print(f"✅ ストーリーズ画像: {out_story}")
        except Exception as e:
            print(f"⚠️ ストーリーズ画像生成失敗: {e}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
