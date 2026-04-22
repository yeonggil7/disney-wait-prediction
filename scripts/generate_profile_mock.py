#!/usr/bin/env python3
"""
@disney_ai_wait プロフィール改善案を視覚化したモック画像を生成。

出力: reports/profile_mock_{date}.png  (1080x1920)
スマホで実際にどう見えるかを画像化し、bio / ハイライト / アクションボタン
の改善提案を視覚的に確認できるようにする。

使い方:
    python scripts/generate_profile_mock.py
    python scripts/generate_profile_mock.py --out reports/profile_mock.png
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, Circle

_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']

BG = '#FAFBFC'
TEXT = '#262626'
MUTE = '#8E8E8E'
ACCENT = '#FF5E62'
LINK = '#00376B'
DIVIDER = '#DBDBDB'


def render_profile_mock(out_path: str):
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor(BG)

    # ───── ヘッダー帯 (アプリ風) ─────
    head = fig.add_axes([0, 0.95, 1, 0.05])
    head.set_xlim(0, 1); head.set_ylim(0, 1); head.axis('off')
    head.text(0.04, 0.5, "@disney_ai_wait", fontsize=22, fontweight='bold',
              color=TEXT, va='center')
    head.text(0.96, 0.5, "≡", fontsize=28, color=TEXT, ha='right', va='center')

    # ───── 上段: アイコン + 数値 ─────
    top = fig.add_axes([0.04, 0.78, 0.92, 0.16])
    top.set_xlim(0, 1); top.set_ylim(0, 1); top.axis('off')
    top.add_patch(Circle((0.13, 0.55), 0.11, facecolor=ACCENT, edgecolor='white', linewidth=2.5))
    top.text(0.13, 0.55, "AI", fontsize=28, fontweight='bold',
             color='white', ha='center', va='center')
    top.text(0.13, 0.18, "リアル感あるアイコン推奨\n(AIロボ + ディズニー城のシルエット)",
             fontsize=8, color=MUTE, ha='center', va='top', linespacing=1.4)

    for i, (label, val) in enumerate([("投稿", "300+"), ("フォロワー", "0→5K"), ("フォロー中", "120")]):
        x = 0.34 + i * 0.21
        top.text(x, 0.65, val, fontsize=20, fontweight='bold',
                 color=TEXT, ha='center', va='center')
        top.text(x, 0.40, label, fontsize=12, color=TEXT, ha='center', va='center')

    # ───── 名前 + bio エリア ─────
    bio = fig.add_axes([0.04, 0.58, 0.92, 0.20])
    bio.set_xlim(0, 1); bio.set_ylim(0, 1); bio.axis('off')

    # 名前 (太字、Bold が検索されやすい)
    bio.text(0.0, 0.95, "AI ディズニー待ち時間予報",
             fontsize=20, fontweight='bold', color=TEXT, va='top')
    bio.text(0.0, 0.83, "▼ クリエイター / ニュースサイト",
             fontsize=11, color=MUTE, va='top')

    # bio 本文 (改善版)
    bio_lines = [
        "🎢 シー・ランド の 待ち時間 を AI が毎日予測",
        "📊 翌日予報・的中レポ・週間ランキング を自動投稿",
        "⏰ 毎朝7時 / 毎晩20時 に新着",
        "💾 旅行プランに「保存」して使ってください",
        "👇 過去の的中例 / 使い方 はハイライトから",
    ]
    for j, line in enumerate(bio_lines):
        bio.text(0.0, 0.66 - j * 0.115, line,
                 fontsize=13, color=TEXT, va='top', linespacing=1.5)

    bio.text(0.0, 0.06, "🔗 disney-ai-wait.com",
             fontsize=13, color=LINK, va='top', fontweight='bold')

    # ───── プロフィール改善ポイント注釈 ─────
    note = fig.add_axes([0.04, 0.52, 0.92, 0.05])
    note.set_xlim(0, 1); note.set_ylim(0, 1); note.axis('off')
    note.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.05",
        facecolor='#FFF3CD', edgecolor='#FCC85A', linewidth=1.5))
    note.text(0.02, 0.55,
              "💡 ポイント: 1行目は「何を提供するか」、最終行に「次のアクション(ハイライト誘導)」を入れる",
              fontsize=10, color='#856404', va='center', fontweight='bold')

    # ───── アクションボタン ─────
    btn = fig.add_axes([0.04, 0.46, 0.92, 0.05])
    btn.set_xlim(0, 1); btn.set_ylim(0, 1); btn.axis('off')
    for i, label in enumerate(["フォロー", "メッセージ", "メールを送信"]):
        x = i * 0.34
        btn.add_patch(FancyBboxPatch(
            (x + 0.005, 0.10), 0.32, 0.80,
            boxstyle="round,pad=0.005,rounding_size=0.05",
            facecolor='#0095F6' if i == 0 else 'white',
            edgecolor='#DBDBDB' if i > 0 else 'none', linewidth=1))
        btn.text(x + 0.165, 0.50, label,
                 fontsize=12, fontweight='bold' if i == 0 else 'normal',
                 color='white' if i == 0 else TEXT,
                 ha='center', va='center')

    # ───── ハイライト案 ─────
    high_label = fig.add_axes([0.04, 0.43, 0.92, 0.025])
    high_label.set_xlim(0, 1); high_label.set_ylim(0, 1); high_label.axis('off')
    high_label.text(0.0, 0.5, "ハイライト (5枚に整理)",
                    fontsize=11, color=MUTE, va='center', fontweight='bold')

    high = fig.add_axes([0.04, 0.34, 0.92, 0.09])
    high.set_xlim(0, 1); high.set_ylim(0, 1); high.axis('off')
    highlights = [
        ("📖", "使い方", "#7B68EE"),
        ("🏆", "的中例", "#FCC85A"),
        ("🎯", "狙い目DAY", "#4ECDC4"),
        ("💡", "FAQ", "#FF9966"),
        ("🤝", "コラボ", "#FF6B9D"),
    ]
    for i, (emoji, label, color) in enumerate(highlights):
        x = 0.04 + i * 0.19
        high.add_patch(Circle((x + 0.07, 0.65), 0.07,
                              facecolor='white', edgecolor=color, linewidth=3.5))
        high.text(x + 0.07, 0.65, emoji, fontsize=20, ha='center', va='center')
        high.text(x + 0.07, 0.18, label, fontsize=11,
                  color=TEXT, ha='center', va='center', fontweight='bold')

    # ───── ハイライト改善提案 ─────
    note2 = fig.add_axes([0.04, 0.28, 0.92, 0.05])
    note2.set_xlim(0, 1); note2.set_ylim(0, 1); note2.axis('off')
    note2.add_patch(FancyBboxPatch(
        (0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.05",
        facecolor='#D1ECF1', edgecolor='#17A2B8', linewidth=1.5))
    note2.text(0.02, 0.55,
               "💡 ポイント: 「的中例」が信頼の証拠。フォロー前に必ず見られる場所に配置",
               fontsize=10, color='#0C5460', va='center', fontweight='bold')

    # ───── タブアイコン ─────
    tab = fig.add_axes([0.04, 0.23, 0.92, 0.05])
    tab.set_xlim(0, 1); tab.set_ylim(0, 1); tab.axis('off')
    tab.plot([0, 1], [0.95, 0.95], color=DIVIDER, linewidth=1)
    for i, sym in enumerate(["▣", "▶", "■"]):
        x = 0.165 + i * 0.34
        tab.text(x, 0.45, sym, fontsize=20, color=TEXT if i == 0 else MUTE,
                 ha='center', va='center')
    tab.plot([0.04, 0.30], [0.05, 0.05], color=TEXT, linewidth=2.5)

    # ───── グリッド (3x3 サムネ) ─────
    grid = fig.add_axes([0.04, 0.04, 0.92, 0.18])
    grid.set_xlim(0, 1); grid.set_ylim(0, 1); grid.axis('off')
    grid_colors = [
        '#1F8FBE', '#D63384', '#FCC85A',
        '#7B68EE', '#FF6B9D', '#4ECDC4',
        '#FF5E62', '#1F8FBE', '#D63384',
    ]
    grid_labels = [
        'シー予報', 'ランド予報', '答え合わせ',
        'リール', '週間RK', 'シー予報',
        'ホット速報', 'シー予報', 'ランド予報',
    ]
    cell = 0.32
    for i in range(3):
        for j in range(3):
            idx = i * 3 + j
            x = j * 0.333
            y = 1 - (i + 1) * 0.333
            grid.add_patch(FancyBboxPatch(
                (x + 0.005, y + 0.005), cell, cell,
                boxstyle="round,pad=0.005,rounding_size=0.01",
                facecolor=grid_colors[idx], edgecolor='white', linewidth=1.5))
            grid.text(x + cell / 2, y + cell / 2, grid_labels[idx],
                      fontsize=10, color='white', ha='center', va='center',
                      fontweight='bold')

    # ───── タイトル (画像のヘッダー) ─────
    title = fig.add_axes([0, 0.0, 1, 0.04])
    title.set_xlim(0, 1); title.set_ylim(0, 1); title.axis('off')
    title.text(0.5, 0.5,
               f"@disney_ai_wait プロフィール 改善モック  /  {datetime.now().strftime('%Y-%m-%d')}",
               fontsize=12, color=MUTE, ha='center', va='center')

    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor(),
                bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="プロフィール改善モック生成")
    parser.add_argument("--out", type=str, default=None,
                        help="出力パス (デフォルト reports/profile_mock_{date}.png)")
    args = parser.parse_args()
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = args.out or str(PROJECT_DIR / "reports" / f"profile_mock_{today}.png")
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    render_profile_mock(out_path)
    print(f"✅ プロフィールモック: {out_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
