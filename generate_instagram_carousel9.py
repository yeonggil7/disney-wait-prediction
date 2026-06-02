#!/usr/bin/env python3
"""
Instagram 9枚カルーセル用 待ち時間予想画像生成

1. 表紙
2. 今日の結論
3. 最警戒ランキング
4. 狙い目タイム
5. 朝の攻略
6. 昼〜夕方の攻略
7. 夜の攻略
8. 詳細ヒートマップ
9. 保存CTA
"""

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

from generate_instagram_heatmap import (
    INSTAGRAM_CMAP,
    LAND_SHORT_DISPLAY,
    PARK_THEMES,
    SEA_SHORT_DISPLAY,
    _build_pivot,
    _summary_stats,
)
from generate_x_heatmap import get_day_of_week_ja, round_up_to_10


PROJECT_DIR = Path(__file__).parent.absolute()
W, H = 10.8, 13.5
TEXT = '#162033'
MUTED = '#64748B'
WHITE = '#FFFFFF'
INK_BLUE = '#0F3B68'
PINK = '#F45C9D'
GOLD = '#F7C948'
GREEN = '#159957'
RED = '#E84C5C'

_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro', 'Yu Gothic',
             'Meiryo', 'Noto Sans CJK JP', 'Noto Sans CJK', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']


def _gradient(ax, colors, horizontal=False):
    grad = np.linspace(0, 1, 512)
    grad = np.vstack([grad, grad]) if horizontal else np.vstack([grad, grad]).T
    cmap = LinearSegmentedColormap.from_list('carousel_grad', colors)
    ax.imshow(grad, aspect='auto', cmap=cmap, extent=[0, 1, 0, 1], origin='lower')


def _text(ax, x, y, s, **kwargs):
    shadow = kwargs.pop('shadow', False)
    t = ax.text(x, y, s, **kwargs)
    if shadow:
        t.set_path_effects([
            path_effects.withStroke(linewidth=4, foreground='black', alpha=0.18),
        ])
    return t


def _new_fig(theme):
    fig = plt.figure(figsize=(W, H), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    colors = ['#E6F7FF', '#FFF7E8', '#FFF9FB'] if theme == 'sea' else ['#FFF0F7', '#FFF7E8', '#F4FBFF']
    _gradient(ax, colors)
    return fig, ax


def _card(ax, x, y, w, h, fc=WHITE, ec='none', alpha=0.96, radius=0.035):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=1.5, alpha=alpha,
    )
    ax.add_patch(patch)
    return patch


def _pill(ax, x, y, w, h, text, fc, color=TEXT, fs=15):
    _card(ax, x, y, w, h, fc=fc, alpha=1.0, radius=0.025)
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha='center', va='center',
            color=color, fontweight='bold')


def _slide_title(ax, no, title, subtitle, accent):
    _pill(ax, 0.065, 0.90, 0.12, 0.045, f"{no}/9", accent, WHITE, 13)
    ax.text(0.065, 0.855, title, fontsize=34, ha='left', va='center',
            color=TEXT, fontweight='bold')
    if subtitle:
        ax.text(0.067, 0.818, subtitle, fontsize=15, ha='left', va='center',
                color=MUTED, fontweight='bold')


def _footer(ax, handle):
    ax.text(0.5, 0.035, f"保存して当日の作戦会議に  /  {handle}",
            fontsize=12, ha='center', va='center', color=MUTED, fontweight='bold')


def _prepare(date_str, park):
    pivot, closures, predictions = _build_pivot(date_str, park)
    if pivot is None:
        raise RuntimeError("予測データを作成できませんでした")
    stats = _summary_stats(predictions)
    valid = predictions[predictions['predicted_wait_time'] >= 0].copy()
    valid['hour'] = valid['time'].str.slice(0, 2).astype(int)
    valid['wait_rounded'] = valid['predicted_wait_time'].apply(round_up_to_10)
    closed = sorted(predictions.loc[predictions['predicted_wait_time'] < 0, 'short_name'].dropna().unique())
    short_map = SEA_SHORT_DISPLAY if park == 'sea' else LAND_SHORT_DISPLAY
    return pivot, closures, predictions, valid, stats, closed, short_map


def _top_rank(valid, n=5):
    rows = valid.groupby('short_name')['predicted_wait_time'].agg(['max', 'mean']).reset_index()
    rows['max_round'] = rows['max'].apply(round_up_to_10).astype(int)
    rows['mean_round'] = rows['mean'].apply(round_up_to_10).astype(int)
    return rows.sort_values(['max_round', 'mean_round'], ascending=False).head(n)


def _best_times(valid):
    rows = []
    window = valid[(valid['time'] >= '09:30') & (valid['time'] < '19:00')]
    for name, grp in window.groupby('short_name'):
        best = grp.sort_values(['predicted_wait_time', 'time']).iloc[0]
        rows.append((name, best['time'], int(round_up_to_10(best['predicted_wait_time']))))
    return sorted(rows, key=lambda x: (x[2], x[1]))


def _hourly(valid):
    data = valid.groupby('hour')['predicted_wait_time'].mean().apply(round_up_to_10)
    return data.astype(int)


def _draw_cover(date_str, park, stats, out, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _gradient(ax, [theme['accent'], '#6D5DF6', '#FF6FB1'], horizontal=True)
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = get_day_of_week_ja(date_str)

    for x, y, s in [(0.13, 0.86, '✦'), (0.80, 0.82, '✧'), (0.90, 0.28, '✦'), (0.18, 0.20, '✧')]:
        ax.text(x, y, s, fontsize=34, color=WHITE, alpha=0.42, ha='center', va='center')

    _text(ax, 0.07, 0.80, f"{dt.month}/{dt.day}({day})", fontsize=70,
          ha='left', va='center', color=WHITE, fontweight='bold', shadow=True)
    _text(ax, 0.07, 0.67, theme['name'], fontsize=34,
          ha='left', va='center', color=WHITE, fontweight='bold', shadow=True)
    _text(ax, 0.07, 0.55, "AI待ち時間予想", fontsize=60,
          ha='left', va='center', color=WHITE, fontweight='bold', shadow=True)

    _card(ax, 0.07, 0.31, 0.86, 0.17, fc=WHITE, alpha=0.94)
    cols = [(0.13, "平均待ち", f"{stats['avg_wait']}分", stats['congestion_color']),
            (0.40, "狙い目", stats['calm_time'], GREEN),
            (0.67, "混雑度", stats['congestion'], RED)]
    for x, label, value, color in cols:
        ax.add_patch(Rectangle((x, 0.445), 0.19, 0.012, color=color, transform=ax.transAxes))
        ax.text(x + 0.095, 0.395, value, fontsize=24, ha='center', va='center',
                color=TEXT, fontweight='bold')
        ax.text(x + 0.095, 0.355, label, fontsize=13, ha='center', va='center',
                color=MUTED, fontweight='bold')

    ax.text(0.5, 0.22, "1分で作戦会議できる9枚", fontsize=24, ha='center',
            va='center', color=WHITE, fontweight='bold')
    ax.text(0.5, 0.14, "スワイプして、回る順番を決めよう", fontsize=18, ha='center',
            va='center', color=WHITE, fontweight='bold', alpha=0.9)
    ax.text(0.5, 0.055, handle, fontsize=20, ha='center', va='center',
            color=WHITE, fontweight='bold')
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_summary(date_str, park, stats, closed, out, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _slide_title(ax, 2, "今日の結論", "まずはここだけ見ればOK", theme['accent'])
    cards = [
        ("平均待ち", f"{stats['avg_wait']}分", stats['congestion_color']),
        ("ピーク", stats['peak_time'], RED),
        ("狙い目", stats['calm_time'], GREEN),
        ("休止", f"{len(closed)}施設", '#94A3B8'),
    ]
    for i, (label, value, color) in enumerate(cards):
        x = 0.07 + (i % 2) * 0.45
        y = 0.62 - (i // 2) * 0.20
        _card(ax, x, y, 0.39, 0.15)
        ax.add_patch(Rectangle((x + 0.03, y + 0.12), 0.33, 0.012, color=color))
        ax.text(x + 0.195, y + 0.085, value, fontsize=30, ha='center', va='center',
                color=TEXT, fontweight='bold')
        ax.text(x + 0.195, y + 0.040, label, fontsize=14, ha='center', va='center',
                color=MUTED, fontweight='bold')

    _card(ax, 0.07, 0.19, 0.86, 0.20, fc='#FFF7ED')
    msg = "人気施設の休止がある日は、近いジャンルの施設へ待ち時間が流れやすい日。"
    ax.text(0.10, 0.31, "攻略メモ", fontsize=18, ha='left', va='center',
            color=TEXT, fontweight='bold')
    ax.text(0.10, 0.255, msg, fontsize=17, ha='left', va='center',
            color=TEXT, fontweight='bold')
    ax.text(0.10, 0.215, "青枠の時間帯は、各施設の相対的な狙い目です。", fontsize=14,
            ha='left', va='center', color=MUTED, fontweight='bold')
    _footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_rank(valid, out, park, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _slide_title(ax, 3, "最警戒ランキング", "最大待ち時間が高い順", theme['accent'])
    rank = _top_rank(valid, 5)
    max_wait = max(rank['max_round'].max(), 1)
    for i, row in enumerate(rank.itertuples(index=False), 1):
        y = 0.72 - (i - 1) * 0.125
        _card(ax, 0.07, y, 0.86, 0.092)
        ax.text(0.105, y + 0.046, f"{i}", fontsize=20, ha='center', va='center',
                color=RED, fontweight='bold')
        ax.text(0.16, y + 0.046, row.short_name, fontsize=19, ha='left', va='center',
                color=TEXT, fontweight='bold')
        bar_w = 0.34 * (row.max_round / max_wait)
        ax.add_patch(FancyBboxPatch((0.44, y + 0.033), bar_w, 0.026,
                                    boxstyle="round,pad=0.002,rounding_size=0.013",
                                    facecolor=RED if i == 1 else '#FF9F70', edgecolor='none'))
        ax.text(0.86, y + 0.046, f"最大 {row.max_round}分", fontsize=18,
                ha='right', va='center', color=TEXT, fontweight='bold')
    _footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_best(valid, out, park, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _slide_title(ax, 4, "狙い目タイム", "9:30〜19:00の中で拾いやすい時間", theme['accent'])
    rows = _best_times(valid)[:10]
    for i, (name, time, wait) in enumerate(rows):
        col = i // 5
        row = i % 5
        x = 0.07 + col * 0.45
        y = 0.70 - row * 0.115
        _card(ax, x, y, 0.39, 0.085)
        ax.text(x + 0.035, y + 0.043, name, fontsize=15, ha='left',
                va='center', color=TEXT, fontweight='bold')
        ax.text(x + 0.35, y + 0.053, time, fontsize=20, ha='right',
                va='center', color=GREEN, fontweight='bold')
        ax.text(x + 0.35, y + 0.025, f"約{wait}分", fontsize=11, ha='right',
                va='center', color=MUTED, fontweight='bold')
    _footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_time_strategy(valid, out, park, handle, slide_no, title, subtitle, start, end, accent):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _slide_title(ax, slide_no, title, subtitle, theme['accent'])
    block = valid[(valid['time'] >= start) & (valid['time'] <= end)].copy()
    avg_by_attr = block.groupby('short_name')['predicted_wait_time'].mean().apply(round_up_to_10).sort_values()
    easy = avg_by_attr.head(3)
    hard = avg_by_attr.tail(3).sort_values(ascending=False)

    _card(ax, 0.07, 0.55, 0.86, 0.25)
    ax.text(0.11, 0.745, "狙いやすい", fontsize=18, color=GREEN, fontweight='bold')
    for i, (name, wait) in enumerate(easy.items()):
        ax.text(0.12, 0.695 - i * 0.055, f"{name}", fontsize=18, color=TEXT, fontweight='bold')
        ax.text(0.84, 0.695 - i * 0.055, f"約{int(wait)}分", fontsize=18,
                ha='right', color=GREEN, fontweight='bold')

    _card(ax, 0.07, 0.25, 0.86, 0.23, fc='#FFF1F2')
    ax.text(0.11, 0.425, "後回し候補", fontsize=18, color=RED, fontweight='bold')
    for i, (name, wait) in enumerate(hard.items()):
        ax.text(0.12, 0.375 - i * 0.055, f"{name}", fontsize=18, color=TEXT, fontweight='bold')
        ax.text(0.84, 0.375 - i * 0.055, f"約{int(wait)}分", fontsize=18,
                ha='right', color=RED, fontweight='bold')

    hourly = _hourly(block)
    if not hourly.empty:
        best_hour = hourly.idxmin()
        ax.text(0.5, 0.17, f"この時間帯の狙い目: {best_hour}時台",
                fontsize=22, ha='center', va='center', color=accent, fontweight='bold')
    _footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_heatmap(pivot, stats, out, park, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _slide_title(ax, 8, "詳細ヒートマップ", "濃い赤ほど待ち時間が長い予想", theme['accent'])
    _card(ax, 0.055, 0.11, 0.89, 0.72)
    hm = fig.add_axes([0.10, 0.18, 0.85, 0.58])
    data = pivot.copy().astype(float)
    mask = data < 0
    data[mask] = np.nan
    hm.imshow(data.values, aspect='auto', cmap=INSTAGRAM_CMAP, vmin=0, vmax=150)
    n_rows, n_cols = data.shape
    for i in range(n_rows):
        for j in range(n_cols):
            v = pivot.iloc[i, j]
            if pd.isna(v):
                continue
            if v < 0:
                hm.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor='#F1F5F9', edgecolor='none'))
                hm.text(j, i, '休止', ha='center', va='center', fontsize=9, color=MUTED)
            else:
                hm.text(j, i, f"{int(v)}", ha='center', va='center',
                        fontsize=10, color='#111827', fontweight='bold')
    time_to_idx = {t: i for i, t in enumerate(pivot.index)}
    for j, attr in enumerate(pivot.columns):
        t = stats.get('per_attraction_calm', {}).get(attr)
        if t in time_to_idx:
            i = time_to_idx[t]
            hm.add_patch(Rectangle((j - 0.48, i - 0.48), 0.96, 0.96,
                                   fill=False, edgecolor=INK_BLUE, linewidth=2.2))
    hm.set_xticks(range(n_cols))
    hm.set_xticklabels(list(pivot.columns), rotation=30, ha='right', fontsize=10, fontweight='bold')
    hm.set_yticks(range(n_rows))
    hm.set_yticklabels(pivot.index, fontsize=9, color=MUTED)
    hm.tick_params(axis='both', length=0)
    for spine in hm.spines.values():
        spine.set_visible(False)
    _footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_cta(date_str, park, stats, out, handle):
    theme = PARK_THEMES[park]
    fig, ax = _new_fig(park)
    _gradient(ax, [theme['accent'], '#6D5DF6', '#FF6FB1'], horizontal=True)
    ax.text(0.5, 0.76, "行く前に保存", fontsize=58, ha='center', va='center',
            color=WHITE, fontweight='bold')
    ax.text(0.5, 0.63, "当日はこの順番でチェック", fontsize=28, ha='center',
            va='center', color=WHITE, fontweight='bold')
    _card(ax, 0.10, 0.36, 0.80, 0.20, fc=WHITE, alpha=0.94)
    ax.text(0.50, 0.50, "1. 最警戒TOPを見る\n2. 狙い目タイムを決める\n3. ヒートマップで時間をずらす",
            fontsize=23, ha='center', va='center', color=TEXT, fontweight='bold', linespacing=1.7)
    ax.text(0.5, 0.25, "友だちに送って、朝の作戦会議に", fontsize=24,
            ha='center', va='center', color=WHITE, fontweight='bold')
    ax.text(0.5, 0.13, "※AI予測のため実際の待ち時間と異なる場合があります", fontsize=14,
            ha='center', va='center', color=WHITE, fontweight='bold', alpha=0.85)
    ax.text(0.5, 0.06, handle, fontsize=22, ha='center', va='center',
            color=WHITE, fontweight='bold')
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------------------
# DisneyColors風: 正方形・濃青緑・黄色日付丸・表メイン
# ---------------------------------------------------------------------------
DC_BG = '#07586A'
DC_BG2 = '#064A5B'
DC_YELLOW = '#F6F36A'
DC_GOLD = '#F4D56B'
DC_PINK = '#FF5DA2'
DC_CYAN = '#4ED5D0'
DC_LIME = '#8EF07A'
DC_TABLE = '#F7F7EC'
DC_GRID = '#0A5665'
COVER_ASSETS = [
    PROJECT_DIR / 'assets' / 'instagram_cover' / 'frozen.jpg',
    PROJECT_DIR / 'assets' / 'instagram_cover' / 'aqua_sphere.webp',
    PROJECT_DIR / 'assets' / 'instagram_cover' / 'fantasy_springs_castle.jpg',
    PROJECT_DIR / 'assets' / 'instagram_cover' / 'cinderella_castle.jpeg',
]


def _dc_fig():
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100, facecolor=DC_BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    _gradient(ax, [DC_BG, DC_BG2])
    return fig, ax


def _cover_image_array(path, aspect=1.0):
    """写真を指定アスペクトで中央クロップしてnumpy配列にする"""
    img = Image.open(path).convert('RGB')
    w, h = img.size
    current = w / h
    if current > aspect:
        new_w = int(h * aspect)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif current < aspect:
        new_h = int(w / aspect)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    return np.asarray(img)


def _draw_photo_panel(ax, path, x, y, w, h):
    arr = _cover_image_array(path, aspect=w / h)
    ax.imshow(arr, extent=[x, x + w, y, y + h], zorder=0)
    ax.add_patch(Rectangle((x, y), w, h, facecolor='black', edgecolor='none',
                           alpha=0.14, zorder=1))


def _outline(ax, x, y, s, fontsize, color, stroke='white', lw=5, **kwargs):
    t = ax.text(x, y, s, fontsize=fontsize, color=color, fontweight='bold', **kwargs)
    t.set_path_effects([path_effects.withStroke(linewidth=lw, foreground=stroke)])
    return t


def _dc_date(ax, date_str, x=0.14, y=0.87, r=0.085):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.weekday()]
    ax.add_patch(plt.Circle((x, y), r, facecolor=DC_YELLOW, edgecolor='none', alpha=0.98))
    ax.text(x, y + 0.035, str(dt.year), fontsize=12, ha='center', va='center',
            color='black', fontweight='bold')
    ax.text(x, y - 0.005, f"{dt.month}.{dt.day}", fontsize=30, ha='center', va='center',
            color='black', fontweight='bold')
    ax.text(x, y - 0.050, day, fontsize=15, ha='center', va='center',
            color='black', fontweight='bold')


def _dc_footer(ax, handle):
    ax.text(0.5, 0.035, handle, fontsize=14, ha='center', va='center',
            color='white', fontweight='bold', alpha=0.9)


def _dc_title(ax, date_str, title, subtitle=None):
    _dc_date(ax, date_str)
    ax.text(0.52, 0.91, title, fontsize=28, ha='center', va='center',
            color=DC_GOLD, fontweight='bold')
    if subtitle:
        ax.text(0.52, 0.865, subtitle, fontsize=13, ha='center', va='center',
                color='white', fontweight='bold', alpha=0.9)


def _dc_wait_color(wait):
    if pd.isna(wait) or wait < 0:
        return '#E7E7E7'
    if wait >= 120:
        return '#FF5B70'
    if wait >= 90:
        return '#FF9D4D'
    if wait >= 60:
        return '#FFE45E'
    if wait >= 30:
        return '#83E972'
    return '#5CD0F0'


def _dc_attraction_dots(ax, names, y=0.74):
    xs = np.linspace(0.25, 0.82, len(names))
    colors = ['#FF88B6', '#CFA5FF', '#67D9FF', '#A9F47A', '#FFD166', '#FF9F80']
    for i, (x, name) in enumerate(zip(xs, names)):
        ax.add_patch(plt.Circle((x, y), 0.045, facecolor=colors[i % len(colors)],
                                edgecolor='white', linewidth=2))
        ax.text(x, y, name[:1], fontsize=20, ha='center', va='center',
                color='white', fontweight='bold')
        ax.text(x, y - 0.065, name[:6], fontsize=9, ha='center', va='center',
                color='white', fontweight='bold')


def _dc_table(ax, df, x, y, w, h, col_widths=None, font=10):
    nrows, ncols = df.shape
    col_widths = col_widths or [1 / ncols] * ncols
    row_h = h / (nrows + 1)
    cx = x
    for j, col in enumerate(df.columns):
        cw = w * col_widths[j]
        ax.add_patch(Rectangle((cx, y + h - row_h), cw, row_h,
                               facecolor=DC_GOLD, edgecolor=DC_GRID, linewidth=1.4))
        ax.text(cx + cw / 2, y + h - row_h / 2, str(col), fontsize=font,
                ha='center', va='center', color='black', fontweight='bold')
        cx += cw
    for i in range(nrows):
        cx = x
        for j, col in enumerate(df.columns):
            cw = w * col_widths[j]
            val = df.iloc[i, j]
            face = _dc_wait_color(val) if isinstance(val, (int, float, np.integer, np.floating)) else DC_TABLE
            display_val = _dc_display_value(val)
            ax.add_patch(Rectangle((cx, y + h - row_h * (i + 2)), cw, row_h,
                                   facecolor=face, edgecolor=DC_GRID, linewidth=1.1))
            ax.text(cx + cw / 2, y + h - row_h * (i + 1.5), display_val,
                    fontsize=font, ha='center', va='center', color='black',
                    fontweight='bold')
            cx += cw


def _dc_display_value(value):
    """表内表示用。待ち時間の小数点を出さない。"""
    if isinstance(value, (int, float, np.integer, np.floating)) and not pd.isna(value):
        if value < 0:
            return '休止'
        return str(int(round(value)))
    return str(value)


def _dc_top_names(valid, n=5):
    rank = _top_rank(valid, n)
    return rank['short_name'].tolist()


def _draw_dc_cover(date_str, park, stats, valid, out, handle, stats_line=None):
    fig, ax = _dc_fig()
    # 写真4分割コラージュ
    panels = [
        (0.04, 0.52, 0.46, 0.44, COVER_ASSETS[0]),
        (0.50, 0.52, 0.46, 0.44, COVER_ASSETS[1]),
        (0.04, 0.06, 0.46, 0.46, COVER_ASSETS[2]),
        (0.50, 0.06, 0.46, 0.46, COVER_ASSETS[3]),
    ]
    for x, y, w, h, path in panels:
        if path.exists():
            _draw_photo_panel(ax, path, x, y, w, h)
        else:
            ax.add_patch(Rectangle((x, y), w, h, facecolor='#7EC8E3', edgecolor='none'))

    ax.add_patch(Rectangle((0.04, 0.06), 0.92, 0.90, facecolor='black',
                           edgecolor='none', alpha=0.18, zorder=2))
    ax.add_patch(Rectangle((0.04, 0.06), 0.92, 0.90, facecolor='none',
                           edgecolor='white', linewidth=3, alpha=0.75, zorder=3))

    _outline(ax, 0.5, 0.80, "ディズニーランド", 35, DC_PINK, stroke='white',
             lw=5, ha='center', va='center', zorder=5)
    _outline(ax, 0.5, 0.70, "ディズニーシー", 35, DC_CYAN, stroke='white',
             lw=5, ha='center', va='center', zorder=5)
    _outline(ax, 0.5, 0.58, "AI 待ち時間予想", 42, DC_YELLOW, stroke='black',
             lw=6, ha='center', va='center', zorder=5)
    _dc_date(ax, date_str, x=0.50, y=0.31, r=0.13)
    stats_line = stats_line or f"平均待ち時間 {stats['avg_wait']}分"
    ax.text(0.5, 0.17, stats_line,
            fontsize=19, ha='center', va='center', color='white', fontweight='bold',
            zorder=5)
    ax.text(0.5, 0.10, handle, fontsize=18, ha='center', va='center',
            color='white', fontweight='bold', zorder=5)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_dc_status(date_str, park, stats, valid, closed, out, handle):
    fig, ax = _dc_fig()
    park_label = "シー" if park == 'sea' else "ランド"
    _dc_title(ax, date_str, f"{park_label} 人気アトラクション", "予測待ち時間と休止を一覧で確認")
    names = _dc_top_names(valid, 5)
    _dc_attraction_dots(ax, names, y=0.74)
    rank = _top_rank(valid, 6)
    rows = []
    for r in rank.itertuples(index=False):
        rows.append([r.short_name, f"最大{r.max_round}分", f"平均{r.mean_round}分"])
    for name in closed[:2]:
        rows.append([name, "休止", "-"])
    df = pd.DataFrame(rows, columns=['施設', '最大', '平均'])
    _dc_table(ax, df, 0.13, 0.23, 0.74, 0.42, col_widths=[0.45, 0.28, 0.27], font=13)
    ax.text(0.5, 0.16, f"ピーク {stats['peak_time']} / 狙い目 {stats['calm_time']}",
            fontsize=20, ha='center', va='center', color=DC_YELLOW, fontweight='bold')
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _dc_pivot_subset(pivot, names, every=2):
    times = list(pivot.index)[::every]
    cols = [n for n in names if n in pivot.columns]
    data = pivot.loc[times, cols].copy()
    data.insert(0, '時刻', times)
    return data


def _draw_dc_wait_table(date_str, park, pivot, valid, out, handle, slide_no=3,
                        title="AI待ち時間予測", every=1):
    fig, ax = _dc_fig()
    park_label = "シー" if park == 'sea' else "ランド"
    interval = "30分おき" if every == 1 else "1時間おき"
    _dc_title(ax, date_str, f"{park_label} {title}", f"{interval} / 色つきセルほど待ち時間が長い予想")
    names = _dc_top_names(valid, 5)
    if every != 1:
        _dc_attraction_dots(ax, names, y=0.72)
        table_y, table_h, font = 0.10, 0.52, 9
    else:
        table_y, table_h, font = 0.075, 0.70, 7
    df = _dc_pivot_subset(pivot, names, every=every)
    _dc_table(ax, df, 0.07, table_y, 0.86, table_h,
              col_widths=[0.14] + [0.86 / max(len(df.columns) - 1, 1)] * (len(df.columns) - 1),
              font=font)
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_dc_rank(date_str, park, valid, out, handle):
    fig, ax = _dc_fig()
    park_label = "シー" if park == 'sea' else "ランド"
    _dc_title(ax, date_str, f"{park_label} 最大待ち時間", "今日の最警戒TOP5")
    rank = _top_rank(valid, 5)
    max_wait = max(rank['max_round'].max(), 1)
    for i, row in enumerate(rank.itertuples(index=False), 1):
        y = 0.72 - (i - 1) * 0.115
        ax.add_patch(Rectangle((0.12, y), 0.76, 0.078, facecolor=DC_TABLE,
                               edgecolor=DC_GOLD, linewidth=2))
        ax.text(0.16, y + 0.039, str(i), fontsize=22, ha='center', va='center',
                color=DC_PINK, fontweight='bold')
        ax.text(0.24, y + 0.039, row.short_name, fontsize=17, ha='left',
                va='center', color='black', fontweight='bold')
        bw = 0.22 * row.max_round / max_wait
        ax.add_patch(Rectangle((0.55, y + 0.025), bw, 0.028,
                               facecolor=_dc_wait_color(row.max_round), edgecolor='none'))
        ax.text(0.84, y + 0.039, f"{row.max_round}分", fontsize=18,
                ha='right', va='center', color='black', fontweight='bold')
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_dc_best(date_str, park, valid, out, handle):
    fig, ax = _dc_fig()
    _dc_title(ax, date_str, "狙い目タイム", "短い待ち時間で拾いやすい時間")
    rows = _best_times(valid)[:8]
    df = pd.DataFrame([[n, t, f"{w}分"] for n, t, w in rows], columns=['施設', '時間', '予測'])
    _dc_table(ax, df, 0.12, 0.17, 0.76, 0.58, col_widths=[0.46, 0.28, 0.26], font=13)
    ax.text(0.5, 0.10, "青枠より、表の時間を先に狙うと動きやすいです",
            fontsize=14, ha='center', va='center', color=DC_YELLOW, fontweight='bold')
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_dc_segment(date_str, park, valid, out, handle, title, start, end, note):
    fig, ax = _dc_fig()
    _dc_title(ax, date_str, title, note)
    block = valid[(valid['time'] >= start) & (valid['time'] <= end)]
    avg = block.groupby('short_name')['predicted_wait_time'].mean().apply(round_up_to_10).sort_values()
    easy = avg.head(4)
    hard = avg.tail(4).sort_values(ascending=False)
    easy_df = pd.DataFrame([[n, f"{int(w)}分"] for n, w in easy.items()], columns=['狙いやすい', '平均'])
    hard_df = pd.DataFrame([[n, f"{int(w)}分"] for n, w in hard.items()], columns=['後回し候補', '平均'])
    _dc_table(ax, easy_df, 0.13, 0.48, 0.74, 0.26, col_widths=[0.65, 0.35], font=14)
    _dc_table(ax, hard_df, 0.13, 0.17, 0.74, 0.26, col_widths=[0.65, 0.35], font=14)
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _draw_dc_cta(date_str, park, stats, out, handle):
    fig, ax = _dc_fig()
    _dc_date(ax, date_str, x=0.5, y=0.76, r=0.13)
    _outline(ax, 0.5, 0.56, "保存して", 44, DC_YELLOW, stroke='black',
             lw=5, ha='center', va='center')
    _outline(ax, 0.5, 0.45, "朝の作戦会議に", 38, DC_PINK, stroke='white',
             lw=5, ha='center', va='center')
    ax.add_patch(Rectangle((0.15, 0.20), 0.70, 0.16, facecolor=DC_TABLE,
                           edgecolor=DC_GOLD, linewidth=3))
    ax.text(0.5, 0.28, "1. ランキングを見る\n2. 狙い目タイムを決める\n3. 表で時間をずらす",
            fontsize=18, ha='center', va='center', color='black',
            fontweight='bold', linespacing=1.22)
    ax.text(0.5, 0.11, "※AI予測のため実際の待ち時間と異なる場合があります",
            fontsize=11, ha='center', va='center', color='white', fontweight='bold')
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _park_label(park):
    return "シー" if park == 'sea' else "ランド"


def _draw_dc_dual_summary(date_str, sea_pack, land_pack, out, handle):
    fig, ax = _dc_fig()
    _dc_title(ax, date_str, "今日の結論", "ランド・シーをまとめて確認")
    packs = [('シー', sea_pack, DC_CYAN), ('ランド', land_pack, DC_PINK)]
    for i, (label, pack, accent) in enumerate(packs):
        x = 0.09 + i * 0.43
        stats = pack['stats']
        closed = pack['closed']
        rank = _top_rank(pack['valid'], 3)
        ax.add_patch(Rectangle((x, 0.22), 0.38, 0.54, facecolor=DC_TABLE,
                               edgecolor=accent, linewidth=3))
        ax.text(x + 0.19, 0.70, label, fontsize=25, ha='center', va='center',
                color=accent, fontweight='bold')
        ax.text(x + 0.19, 0.625, f"平均 {stats['avg_wait']}分", fontsize=19,
                ha='center', va='center', color='black', fontweight='bold')
        ax.text(x + 0.19, 0.570, f"ピーク {stats['peak_time']}", fontsize=16,
                ha='center', va='center', color='black', fontweight='bold')
        ax.text(x + 0.19, 0.515, f"休止 {len(closed)}施設", fontsize=16,
                ha='center', va='center', color='black', fontweight='bold')
        for j, row in enumerate(rank.itertuples(index=False), 1):
            y = 0.435 - (j - 1) * 0.075
            ax.text(x + 0.035, y, f"{j}. {row.short_name}", fontsize=13,
                    ha='left', va='center', color='black', fontweight='bold')
            ax.text(x + 0.35, y, f"{row.max_round}分", fontsize=14,
                    ha='right', va='center', color='black', fontweight='bold')
    ax.text(0.5, 0.13, "まずは平均と最警戒TOPを見て、行く順番を決めよう",
            fontsize=16, ha='center', va='center', color=DC_YELLOW, fontweight='bold')
    _dc_footer(ax, handle)
    fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _prepare_pack(date_str, park):
    pivot, closures, predictions, valid, stats, closed, short_map = _prepare(date_str, park)
    return {
        'park': park,
        'pivot': pivot,
        'closures': closures,
        'predictions': predictions,
        'valid': valid,
        'stats': stats,
        'closed': closed,
        'short_map': short_map,
    }


def generate_combined_carousel9(date_str, output_dir='predictions_x', handle='@disney_ai_wait'):
    output = Path(output_dir) / date_str / "ig_both_carousel9"
    output.mkdir(parents=True, exist_ok=True)
    for old in output.glob("*.png"):
        old.unlink()
    sea = _prepare_pack(date_str, 'sea')
    land = _prepare_pack(date_str, 'land')
    stats_line = f"平均待ち時間 シー{sea['stats']['avg_wait']}分 / ランド{land['stats']['avg_wait']}分"

    paths = []
    writers = [
        lambda p: _draw_dc_cover(date_str, 'both', sea['stats'], sea['valid'], p, handle, stats_line),
        lambda p: _draw_dc_wait_table(date_str, 'sea', sea['pivot'], sea['valid'], p, handle, 2, "AI待ち時間予測", every=1),
        lambda p: _draw_dc_wait_table(date_str, 'land', land['pivot'], land['valid'], p, handle, 3, "AI待ち時間予測", every=1),
        lambda p: _draw_dc_rank(date_str, 'sea', sea['valid'], p, handle),
        lambda p: _draw_dc_rank(date_str, 'land', land['valid'], p, handle),
        lambda p: _draw_dc_dual_summary(date_str, sea, land, p, handle),
        lambda p: _draw_dc_cta(date_str, 'both', sea['stats'], p, handle),
    ]
    for i, writer in enumerate(writers, 1):
        path = output / f"{i:02d}.png"
        writer(str(path))
        paths.append(str(path))
    manifest = output / "manifest.txt"
    manifest.write_text("\n".join(paths) + "\n", encoding='utf-8')
    return paths


def generate_carousel9(date_str, park='sea', output_dir='predictions_x', handle='@disney_ai_wait'):
    if park in ('both', 'all'):
        return generate_combined_carousel9(date_str, output_dir=output_dir, handle=handle)
    output = Path(output_dir) / date_str / f"ig_{park}_carousel9"
    output.mkdir(parents=True, exist_ok=True)
    for old in output.glob("*.png"):
        old.unlink()
    pivot, closures, predictions, valid, stats, closed, _ = _prepare(date_str, park)

    paths = []
    writers = [
        lambda p: _draw_dc_cover(date_str, park, stats, valid, p, handle),
        lambda p: _draw_dc_status(date_str, park, stats, valid, closed, p, handle),
        lambda p: _draw_dc_wait_table(date_str, park, pivot, valid, p, handle, 3, "AI待ち時間予測", every=1),
        lambda p: _draw_dc_rank(date_str, park, valid, p, handle),
        lambda p: _draw_dc_best(date_str, park, valid, p, handle),
        lambda p: _draw_dc_segment(date_str, park, valid, p, handle, "朝の攻略", "09:15", "11:45", "9:15〜11:45"),
        lambda p: _draw_dc_segment(date_str, park, valid, p, handle, "昼〜夕方の攻略", "12:15", "16:45", "12:15〜16:45"),
        lambda p: _draw_dc_wait_table(date_str, park, pivot, valid, p, handle, 8, "時間別詳細表", every=1),
        lambda p: _draw_dc_cta(date_str, park, stats, p, handle),
    ]
    for i, writer in enumerate(writers, 1):
        path = output / f"{i:02d}.png"
        writer(str(path))
        paths.append(str(path))
    manifest = output / "manifest.txt"
    manifest.write_text("\n".join(paths) + "\n", encoding='utf-8')
    return paths


def main():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    parser = argparse.ArgumentParser(description='Instagram 9枚カルーセル画像生成')
    parser.add_argument('--date', '-d', default=tomorrow)
    parser.add_argument('--park', '-p', choices=['sea', 'land', 'both', 'all'], default='both')
    parser.add_argument('--output', '-o', default='predictions_x')
    parser.add_argument('--handle', default='@disney_ai_wait')
    args = parser.parse_args()

    os.chdir(PROJECT_DIR)
    paths = generate_carousel9(args.date, args.park, args.output, args.handle)
    print("\n📁 生成ファイル:")
    for path in paths:
        print(f"   - {path}")


if __name__ == '__main__':
    main()
