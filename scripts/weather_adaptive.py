#!/usr/bin/env python3
"""
天候・特別日 アダプティブ コンテンツ生成

- Open-Meteo (無料・無認証) で TDR (浦安) の天気予報を取得
- 国民の祝日 (内閣府 CSV) と TDR 特別イベント日 (内蔵カレンダー) を加味
- 「明日の天候」に応じた特別ストーリー画像 を生成
  - 雨予報 → 「雨の日攻略ストーリー」 (屋内アトラク TOP5)
  - 30度以上 → 「猛暑日対策ストーリー」 (冷えるアトラク + クールスポット)
  - 祝日/イベント → 「混雑警報ストーリー」 (混雑予測強調)
  - その他 → 何も生成しない (None を返す)

使い方:
    python scripts/weather_adaptive.py --date 2026-04-22 --out story.png
    python scripts/weather_adaptive.py --check  # 天気だけ表示
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

# 浦安・TDR の座標 (Open-Meteo は座標で問い合わせ)
TDR_LAT, TDR_LON = 35.6329, 139.8804

_jp_fonts = ['Hiragino Sans', 'Hiragino Maru Gothic Pro',
             'Yu Gothic', 'Meiryo', 'Noto Sans CJK JP', 'sans-serif']
_available = {f.name for f in fm.fontManager.ttflist}
plt.rcParams['font.family'] = [f for f in _jp_fonts if f in _available] or ['sans-serif']

# ───────────────────── データ定義 ─────────────────────
INDOOR_ATTRACTIONS_LAND = [
    "プーさんのハニーハント", "美女と野獣", "ホーンテッドマンション",
    "ピーターパン空の旅", "イッツ・ア・スモールワールド",
]
INDOOR_ATTRACTIONS_SEA = [
    "ソアリン", "タワー・オブ・テラー", "トイ・ストーリー・マニア!",
    "海底2万マイル", "シンドバッド・ストーリーブック・ヴォヤッジ",
]
COOL_INDOOR = [
    "アリエルのプレイグラウンド (シー)", "魅惑のチキルーム (ランド)",
    "シアター系: マジックランプシアター (シー)", "プーさんのハニーハント (ランド)",
]
HEAT_TIPS = [
    "💧 こまめな水分補給 (持込ペット可)",
    "🧢 帽子・首元クール推奨",
    "📍 シー: マーメイドラグーン地下は涼しい",
    "📍 ランド: ハニーハント+魅惑チキルームをセットで",
]
RAIN_TIPS = [
    "☂️ 透明傘 = キャストが目印にしやすい",
    "👟 防水シューズ or サンダル+靴下が快適",
    "🎡 屋内アトラク中心で回ると待ち↓ 体感↑",
    "📸 雨の日限定 写真スポット = タワテラ前",
]


# ───────────────────── 祝日 / イベント ─────────────────────
# 簡易内蔵 (内閣府 CSV の代替・年間20日前後)
JP_HOLIDAYS_2026 = {
    "2026-01-01": "元日", "2026-01-12": "成人の日",
    "2026-02-11": "建国記念の日", "2026-02-23": "天皇誕生日",
    "2026-03-20": "春分の日", "2026-04-29": "昭和の日",
    "2026-05-03": "憲法記念日", "2026-05-04": "みどりの日",
    "2026-05-05": "こどもの日", "2026-05-06": "振替休日",
    "2026-07-20": "海の日", "2026-08-11": "山の日",
    "2026-09-21": "敬老の日", "2026-09-22": "国民の休日",
    "2026-09-23": "秋分の日", "2026-10-12": "スポーツの日",
    "2026-11-03": "文化の日", "2026-11-23": "勤労感謝の日",
}

# TDR 公式イベント (代表的なもの。本番運用時は更新可能)
TDR_EVENTS_2026 = {
    "2026-04-15": "TDR春のイベント開幕",
    "2026-07-01": "夏のイベント開幕",
    "2026-10-01": "ハロウィーン開幕",
    "2026-11-08": "クリスマス開幕",
}


def fetch_weather(date_str: str) -> dict | None:
    """
    Open-Meteo 無料 API で TDR の指定日の天気予報を取得
    Returns: {date, t_max, t_min, rain_mm, weather_code, summary}
    """
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": TDR_LAT, "longitude": TDR_LON,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "timezone": "Asia/Tokyo",
            "start_date": date_str, "end_date": date_str,
        }, timeout=30)
        r.raise_for_status()
        d = r.json().get("daily", {})
        if not d.get("time"):
            return None
        wc = d["weather_code"][0]
        return {
            "date": date_str,
            "t_max": d["temperature_2m_max"][0],
            "t_min": d["temperature_2m_min"][0],
            "rain_mm": d["precipitation_sum"][0],
            "rain_pop": d["precipitation_probability_max"][0],
            "weather_code": wc,
            "summary": _wc_summary(wc),
        }
    except Exception as e:
        print(f"⚠️ 天気取得失敗: {e}")
        return None


def _wc_summary(code: int) -> str:
    if code in (0, 1):
        return "☀️ 晴れ"
    if code in (2, 3):
        return "⛅ 曇り"
    if code in (45, 48):
        return "🌫 霧"
    if 51 <= code <= 67:
        return "🌧 雨"
    if 71 <= code <= 77:
        return "❄️ 雪"
    if 80 <= code <= 82:
        return "☔ にわか雨"
    if 95 <= code <= 99:
        return "⛈ 雷雨"
    return f"WMO {code}"


def detect_event(date_str: str) -> tuple[str, str] | None:
    """
    Returns: (label, description) or None
    """
    if date_str in JP_HOLIDAYS_2026:
        return ("祝日", f"🎌 {JP_HOLIDAYS_2026[date_str]} (混雑予想 ↑)")
    if date_str in TDR_EVENTS_2026:
        return ("TDRイベント", f"🎉 {TDR_EVENTS_2026[date_str]}")
    # 連休判定 (前後が祝日 or 週末で 3日以上連続)
    return None


# ───────────────────── ストーリー画像生成 ─────────────────────
def _gradient_bg(fig, c1, c2):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    cmap = LinearSegmentedColormap.from_list("g", [c1, c2], N=256)
    ax.imshow(grad, aspect='auto', cmap=cmap, extent=[0, 1, 0, 1])
    return ax


def render_rain_story(weather: dict, date_str: str, out_path: str) -> str:
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    fig.patch.set_facecolor('#0F1F3A')
    _gradient_bg(fig, '#0F1F3A', '#2B5876')
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]

    h = fig.add_axes([0, 0.88, 1, 0.10]); h.set_xlim(0, 1); h.set_ylim(0, 1); h.axis('off')
    h.text(0.5, 0.65, "☔ 雨の日 攻略ガイド", fontsize=44, ha='center', va='center',
           color='white', fontweight='bold')
    h.text(0.5, 0.30, f"{dt.month}/{dt.day}({day})  降水確率 {weather.get('rain_pop', '?')}%",
           fontsize=24, ha='center', va='center', color='#A3D8FF')

    # 屋内 アトラク TOP5
    a = fig.add_axes([0.05, 0.50, 0.90, 0.35]); a.set_xlim(0, 1); a.set_ylim(0, 1); a.axis('off')
    a.text(0.02, 0.95, "🎡 屋内中心 おすすめ ルート", fontsize=28, color='#FFD23F',
           fontweight='bold', va='top')
    a.text(0.02, 0.85, "🌊 ディズニーシー", fontsize=22, color='white', va='top', fontweight='bold')
    for i, n in enumerate(INDOOR_ATTRACTIONS_SEA[:5]):
        a.text(0.04, 0.78 - i * 0.07, f"  {i + 1}. {n}", fontsize=18, color='white')
    a.text(0.52, 0.85, "🏰 ディズニーランド", fontsize=22, color='white', va='top', fontweight='bold')
    for i, n in enumerate(INDOOR_ATTRACTIONS_LAND[:5]):
        a.text(0.54, 0.78 - i * 0.07, f"  {i + 1}. {n}", fontsize=18, color='white')

    # Tips
    t = fig.add_axes([0.05, 0.20, 0.90, 0.28]); t.set_xlim(0, 1); t.set_ylim(0, 1); t.axis('off')
    t.text(0.02, 0.95, "💡 雨の日 Tips", fontsize=26, color='#FFD23F', fontweight='bold', va='top')
    for i, tip in enumerate(RAIN_TIPS):
        t.text(0.02, 0.80 - i * 0.18, tip, fontsize=20, color='white', va='top')

    f = fig.add_axes([0, 0.04, 1, 0.10]); f.set_xlim(0, 1); f.set_ylim(0, 1); f.axis('off')
    f.text(0.5, 0.60, "@disney_ai_wait", fontsize=26, ha='center', va='center',
           color='white', fontweight='bold')
    f.text(0.5, 0.20, "🔔 通知ONで明日の予測も毎晩20時にお届け", fontsize=16,
           ha='center', va='center', color='white', alpha=0.85)

    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def render_heat_story(weather: dict, date_str: str, out_path: str) -> str:
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    _gradient_bg(fig, '#FF6B35', '#A8123F')
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]

    h = fig.add_axes([0, 0.88, 1, 0.10]); h.set_xlim(0, 1); h.set_ylim(0, 1); h.axis('off')
    h.text(0.5, 0.65, "🌡 猛暑日 サバイバル", fontsize=44, ha='center', va='center',
           color='white', fontweight='bold')
    h.text(0.5, 0.30, f"{dt.month}/{dt.day}({day})  最高 {weather.get('t_max', '?')}℃",
           fontsize=26, ha='center', va='center', color='#FFE66D')

    a = fig.add_axes([0.05, 0.50, 0.90, 0.35]); a.set_xlim(0, 1); a.set_ylim(0, 1); a.axis('off')
    a.text(0.02, 0.95, "❄️ 冷えるアトラク・スポット", fontsize=28, color='#FFE66D',
           fontweight='bold', va='top')
    for i, n in enumerate(COOL_INDOOR):
        a.text(0.04, 0.83 - i * 0.18, f"  {i + 1}. {n}", fontsize=20, color='white', va='top')

    t = fig.add_axes([0.05, 0.20, 0.90, 0.28]); t.set_xlim(0, 1); t.set_ylim(0, 1); t.axis('off')
    t.text(0.02, 0.95, "💡 熱中症対策", fontsize=26, color='#FFE66D', fontweight='bold', va='top')
    for i, tip in enumerate(HEAT_TIPS):
        t.text(0.02, 0.80 - i * 0.18, tip, fontsize=20, color='white', va='top')

    f = fig.add_axes([0, 0.04, 1, 0.10]); f.set_xlim(0, 1); f.set_ylim(0, 1); f.axis('off')
    f.text(0.5, 0.60, "@disney_ai_wait", fontsize=26, ha='center', va='center',
           color='white', fontweight='bold')
    f.text(0.5, 0.20, "🔔 当日朝に最新の混雑予測も配信", fontsize=16,
           ha='center', va='center', color='white', alpha=0.85)

    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def render_event_story(event_label: str, event_desc: str,
                        weather: dict | None, date_str: str,
                        out_path: str) -> str:
    fig = plt.figure(figsize=(10.8, 19.2), dpi=100)
    _gradient_bg(fig, '#7B2CBF', '#3A0CA3')
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]

    h = fig.add_axes([0, 0.85, 1, 0.13]); h.set_xlim(0, 1); h.set_ylim(0, 1); h.axis('off')
    h.text(0.5, 0.70, "⚠ 混雑警報", fontsize=46, ha='center', va='center',
           color='#FFD23F', fontweight='bold')
    h.text(0.5, 0.35, f"{dt.month}/{dt.day}({day})  {event_label}",
           fontsize=24, ha='center', va='center', color='white')

    a = fig.add_axes([0.05, 0.45, 0.90, 0.38]); a.set_xlim(0, 1); a.set_ylim(0, 1); a.axis('off')
    a.text(0.5, 0.92, event_desc, fontsize=28, ha='center', va='top',
           color='white', wrap=True, fontweight='bold')
    a.text(0.5, 0.70, "通常より +30〜50% の混雑が予想されます",
           fontsize=20, ha='center', va='top', color='#FFD23F')
    a.text(0.5, 0.55, "💡 攻略の優先順位",
           fontsize=22, ha='center', va='top', color='white', fontweight='bold')
    tips = [
        "1. 開園 30分前 入園待ち",
        "2. 人気アトラクは DPA 即購入",
        "3. ランチ 11:00 / ディナー 17:00 ずらし",
        "4. ナイトショー 1時間前 場所取り",
    ]
    for i, t in enumerate(tips):
        a.text(0.5, 0.42 - i * 0.10, t, fontsize=20, ha='center', va='top', color='white')

    if weather:
        w = fig.add_axes([0.05, 0.20, 0.90, 0.20]); w.set_xlim(0, 1); w.set_ylim(0, 1); w.axis('off')
        w.text(0.5, 0.85, f"☁ 当日の天気", fontsize=22, ha='center', color='#FFD23F',
                fontweight='bold')
        w.text(0.5, 0.55, f"{weather['summary']}  {weather['t_min']:.0f}〜{weather['t_max']:.0f}℃",
                fontsize=24, ha='center', color='white')
        w.text(0.5, 0.30, f"降水確率 {weather.get('rain_pop', '?')}%  / 降水量 {weather.get('rain_mm', 0)}mm",
                fontsize=18, ha='center', color='white', alpha=0.85)

    f = fig.add_axes([0, 0.04, 1, 0.10]); f.set_xlim(0, 1); f.set_ylim(0, 1); f.axis('off')
    f.text(0.5, 0.60, "@disney_ai_wait", fontsize=26, ha='center', va='center',
           color='white', fontweight='bold')
    f.text(0.5, 0.20, "AI 予測 × 当日攻略を毎日配信", fontsize=16,
           ha='center', va='center', color='white', alpha=0.85)

    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


# ───────────────────── ディスパッチ ─────────────────────
def generate_adaptive_story(date_str: str, out_dir: str = "predictions_x") -> dict:
    """
    Returns: {trigger, image_path} or {trigger: 'none', image_path: None}
    """
    weather = fetch_weather(date_str)
    event = detect_event(date_str)

    out_dir_p = Path(out_dir); out_dir_p.mkdir(parents=True, exist_ok=True)

    triggers = []

    # 雨予報 (降水確率 60% 以上 または 5mm 以上)
    if weather and (weather["rain_pop"] >= 60 or weather["rain_mm"] >= 5):
        out = str(out_dir_p / f"adaptive_rain_{date_str}.png")
        render_rain_story(weather, date_str, out)
        triggers.append({"trigger": "rain", "image_path": out, "weather": weather})

    # 猛暑日 (最高気温 30度 以上 — 雨予報と並列に出してもOK)
    if weather and weather["t_max"] >= 30:
        out = str(out_dir_p / f"adaptive_heat_{date_str}.png")
        render_heat_story(weather, date_str, out)
        triggers.append({"trigger": "heat", "image_path": out, "weather": weather})

    # 祝日 / TDR イベント
    if event:
        out = str(out_dir_p / f"adaptive_event_{date_str}.png")
        render_event_story(event[0], event[1], weather, date_str, out)
        triggers.append({"trigger": "event", "image_path": out,
                          "weather": weather, "event": event})

    if not triggers:
        return {"trigger": "none", "image_path": None, "weather": weather}
    # 複数トリガーがあれば最重要の 1つを返す。優先度: event > rain > heat
    priority = {"event": 3, "rain": 2, "heat": 1}
    triggers.sort(key=lambda t: priority.get(t["trigger"], 0), reverse=True)
    return triggers[0]


def main():
    parser = argparse.ArgumentParser(description="天候・特別日 アダプティブ ストーリー")
    parser.add_argument("--date", default=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                        help="対象日 (default: 翌日)")
    parser.add_argument("--out-dir", default="predictions_x")
    parser.add_argument("--check", action="store_true", help="天気と判定だけ表示")
    args = parser.parse_args()

    if args.check:
        w = fetch_weather(args.date)
        print(f"📅 {args.date}")
        print(f"   weather: {w}")
        print(f"   event:   {detect_event(args.date)}")
        return 0

    result = generate_adaptive_story(args.date, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["trigger"] != "none" else 0


if __name__ == "__main__":
    sys.exit(main())
