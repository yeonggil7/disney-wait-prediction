#!/usr/bin/env python3
"""
カルーセル投稿の「1枚目フック画像」を A/B テスト用に生成。

カルーセルの 1枚目 = 投稿の "顔"。
ここを A/B テストして「保存率 / シェア率」が高いパターンを見つけ、
継続的にコンテンツ品質を改善する。

バリアント (V1〜V4):
  V1 curiosity:  「明日の狙い目時間、知ってますか？」  (好奇心ギャップ)
  V2 stat:       「AI予測: 明日の混雑度 ◯%」          (具体数字)
  V3 warning:    「⚠ 明日の激混みアトラク TOP3」      (危機回避)
  V4 cta:        「★ 旅行プラン保存推奨」              (直接CTA)

使い方:
    from scripts.generate_carousel_hook import generate_hook_image, resolve_hook_variant
    variant = resolve_hook_variant(date_str, mode='auto')
    img = generate_hook_image(variant, date_str, sea_avg=45, land_avg=38)
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, Circle

PROJECT_DIR = Path(__file__).parent.parent.absolute()

_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']

# A/B レポートと同じ場所に置いて勝者ロジックを共通化
HOOK_AB_REPORT = PROJECT_DIR / 'reports' / 'carousel_hook_ab.json'
MIN_SAMPLES_PER_VARIANT = 8

VARIANTS = ['V1_curiosity', 'V2_stat', 'V3_warning', 'V4_cta']

# 投稿時刻基準で ローテーション
def resolve_hook_variant(date_str: str, mode: str = 'auto') -> str:
    """
    'auto'  : 日付の DOY % 4 で 4変種ローテ + A/B 勝者があれば固定
    V1〜V4  : そのまま強制
    """
    if mode in VARIANTS:
        return mode
    # 1. 勝者ロジック (n>=8 & トップ1の save 率が他より +20% 以上)
    winner = _load_hook_winner()
    if winner:
        return winner
    # 2. 通常はローテ
    try:
        doy = datetime.strptime(date_str, '%Y-%m-%d').timetuple().tm_yday
    except Exception:
        doy = 0
    return VARIANTS[doy % len(VARIANTS)]


def _load_hook_winner() -> str | None:
    if not HOOK_AB_REPORT.exists():
        return None
    try:
        data = json.loads(HOOK_AB_REPORT.read_text(encoding='utf-8'))
        s = data.get('summary', {})
        # 全 variant の n が最低数を超えているか
        if not all(s.get(v, {}).get('n', 0) >= MIN_SAMPLES_PER_VARIANT for v in VARIANTS):
            return None
        # save_rate でランキング
        ranked = sorted(VARIANTS,
                        key=lambda v: s.get(v, {}).get('save_rate_pct', 0),
                        reverse=True)
        top, second = ranked[0], ranked[1]
        top_v = s.get(top, {}).get('save_rate_pct', 0)
        snd_v = s.get(second, {}).get('save_rate_pct', 0)
        if snd_v > 0 and top_v >= snd_v * 1.2:
            return top
        return None
    except Exception:
        return None


# ───── デザイン定数 ─────
BG_GRADIENT = {
    'V1_curiosity': ('#1A1A2E', '#16213E'),
    'V2_stat':      ('#0F3460', '#16537E'),
    'V3_warning':   ('#3D0000', '#950000'),
    'V4_cta':       ('#0E5C36', '#1F8A5F'),
}
ACCENTS = {
    'V1_curiosity': '#FFD23F',
    'V2_stat':      '#4ECDC4',
    'V3_warning':   '#FFE66D',
    'V4_cta':       '#FFFFFF',
}


def _draw_gradient_bg(fig, c1, c2):
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    cmap = LinearSegmentedColormap.from_list("g", [c1, c2], N=256)
    ax.imshow(grad, aspect='auto', cmap=cmap, extent=[0, 1, 0, 1])
    return ax


def generate_hook_image(variant: str, date_str: str,
                         sea_avg: int | None = None,
                         land_avg: int | None = None,
                         busiest_attractions: list[str] | None = None,
                         out_path: str | None = None) -> str:
    """
    Returns: 出力画像パス (1080x1350)
    """
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant: {variant}")

    out_path = out_path or str(
        PROJECT_DIR / "predictions_x" /
        f"ig_hook_{variant.lower()}_{date_str}.png"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]
    accent = ACCENTS[variant]

    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    c1, c2 = BG_GRADIENT[variant]
    fig.patch.set_facecolor(c1)
    _draw_gradient_bg(fig, c1, c2)

    # ヘッダー (日付・パーク表記)
    h_ax = fig.add_axes([0, 0.86, 1, 0.10])
    h_ax.set_xlim(0, 1); h_ax.set_ylim(0, 1); h_ax.axis('off')
    h_ax.text(0.5, 0.65, f"{dt.month}/{dt.day}({day}) の予測",
              fontsize=28, color='white', ha='center', va='center',
              fontweight='bold', alpha=0.85)
    h_ax.add_patch(FancyBboxPatch(
        (0.34, 0.10), 0.32, 0.30,
        boxstyle="round,pad=0.005,rounding_size=0.04",
        facecolor=accent, edgecolor='none'))
    h_ax.text(0.5, 0.25, "TOKYO DISNEY RESORT",
              fontsize=12, color='black', ha='center', va='center',
              fontweight='bold')

    # メインコピー (バリアント別)
    main_ax = fig.add_axes([0.05, 0.30, 0.90, 0.55])
    main_ax.set_xlim(0, 1); main_ax.set_ylim(0, 1); main_ax.axis('off')

    if variant == 'V1_curiosity':
        main_ax.text(0.5, 0.85, "明日の", fontsize=72, ha='center', va='center',
                     color='white', fontweight='bold')
        main_ax.text(0.5, 0.62, "狙い目 時間、",
                     fontsize=78, ha='center', va='center',
                     color=accent, fontweight='bold')
        main_ax.text(0.5, 0.42, "知ってますか?",
                     fontsize=72, ha='center', va='center',
                     color='white', fontweight='bold')
        main_ax.text(0.5, 0.18, "▶ スワイプして AI予測 をチェック",
                     fontsize=22, ha='center', va='center',
                     color=accent, alpha=0.95)
    elif variant == 'V2_stat':
        main_ax.text(0.5, 0.92, "AI 予測",
                     fontsize=28, ha='center', va='center',
                     color='white', alpha=0.85)
        avg_combined = None
        if sea_avg and land_avg:
            avg_combined = (sea_avg + land_avg) // 2
        if avg_combined:
            main_ax.text(0.5, 0.65, f"明日の平均待ち",
                         fontsize=36, ha='center', va='center',
                         color='white', fontweight='bold')
            main_ax.text(0.5, 0.40, f"{avg_combined}",
                         fontsize=180, ha='center', va='center',
                         color=accent, fontweight='bold')
            main_ax.text(0.78, 0.40, "分",
                         fontsize=48, ha='center', va='center',
                         color='white')
        else:
            main_ax.text(0.5, 0.50, "明日の混雑予測\nスワイプで確認",
                         fontsize=44, ha='center', va='center',
                         color=accent, fontweight='bold', linespacing=1.4)
        main_ax.text(0.5, 0.10, "シー × ランド 両方の混雑予測",
                     fontsize=22, ha='center', va='center',
                     color='white', alpha=0.85)
    elif variant == 'V3_warning':
        main_ax.text(0.5, 0.92, "■ 明日の", fontsize=42,
                     ha='center', va='center', color='white', fontweight='bold')
        main_ax.text(0.5, 0.74, "激混み TOP3",
                     fontsize=78, ha='center', va='center',
                     color=accent, fontweight='bold')
        if busiest_attractions:
            for i, name in enumerate(busiest_attractions[:3]):
                short = name[:14] + ('…' if len(name) > 14 else '')
                main_ax.text(0.5, 0.55 - i * 0.13, f"{i + 1}. {short}",
                             fontsize=30, ha='center', va='center',
                             color='white', fontweight='bold')
        else:
            main_ax.text(0.5, 0.42,
                         "予測値はスワイプ\n→ 詳細をチェック",
                         fontsize=32, ha='center', va='center',
                         color='white', linespacing=1.4)
        main_ax.text(0.5, 0.08, "回避ルートを今のうちに保存",
                     fontsize=22, ha='center', va='center',
                     color=accent, fontweight='bold')
    elif variant == 'V4_cta':
        main_ax.text(0.5, 0.85, "★", fontsize=120,
                     ha='center', va='center', color=accent)
        main_ax.text(0.5, 0.55, "明日のディズニー",
                     fontsize=46, ha='center', va='center',
                     color='white', fontweight='bold')
        main_ax.text(0.5, 0.40, "AI 予測 公開",
                     fontsize=68, ha='center', va='center',
                     color=accent, fontweight='bold')
        main_ax.text(0.5, 0.20, "💾 保存して旅行プランに",
                     fontsize=28, ha='center', va='center',
                     color='white')
        main_ax.text(0.5, 0.08, "▶ スワイプで詳細",
                     fontsize=22, ha='center', va='center',
                     color=accent, alpha=0.85)

    # フッター (ハンドル + variant マーク (デバッグ用、あえて目立たせない))
    f_ax = fig.add_axes([0, 0.04, 1, 0.10])
    f_ax.set_xlim(0, 1); f_ax.set_ylim(0, 1); f_ax.axis('off')
    f_ax.text(0.5, 0.62, "@disney_ai_wait",
              fontsize=26, ha='center', va='center',
              color='white', fontweight='bold')
    f_ax.text(0.5, 0.25, "AI で毎日 予測 × 答え合わせ",
              fontsize=14, ha='center', va='center',
              color='white', alpha=0.7)
    # variant の小さなタグ (右下) — 後で集計時に視覚確認できる
    f_ax.text(0.97, 0.05, variant.replace('_', ' '),
              fontsize=8, ha='right', va='bottom', color='white', alpha=0.35)

    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="カルーセル 1枚目フック画像 を生成")
    parser.add_argument("--variant", choices=['auto'] + VARIANTS, default='auto')
    parser.add_argument("--date", default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument("--sea-avg", type=int, default=None)
    parser.add_argument("--land-avg", type=int, default=None)
    parser.add_argument("--busiest", nargs='*', default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    v = resolve_hook_variant(args.date, mode=args.variant)
    p = generate_hook_image(v, args.date,
                             sea_avg=args.sea_avg, land_avg=args.land_avg,
                             busiest_attractions=args.busiest,
                             out_path=args.out)
    print(f"✅ {v}: {p}")
