#!/usr/bin/env python3
"""
トレンド連動 BGM 自動選択

Instagram Graph API は Business Account 経由で「トレンド楽曲」を直接取得できないため、
当アカウントでは「トレンド連動 ムード切替」 で代替する:

  - Hot Topic / 天気 / 曜日 / イベント に応じて
    BGM の キー(key) ・ 拍(bpm) ・ 装飾(sparkle) ・ キック(soft_kick) を切り替える
  - 5種類のムード ↓ を持ち、generate_bgm.py のパラメータに変換して生成
       * upbeat       : 新規発表・周年・GW など 盛り上がりトピック
       * gentle       : 雨の日・通常平日
       * dramatic     : 混雑警報・ハロウィン
       * mystery      : 夜・ナイトショー・新エリア発表
       * heroic       : 25周年・スペシャルイベント

オプション (上級):
  - YouTube Audio Library / Pixabay Music の URL リスト (JSON) を
    `data/bgm_library.json` に置けば、優先的にダウンロードして使用 (※要 yt-dlp)

使い方:
    python scripts/trending_bgm_selector.py --date 2026-04-22 --park sea --duration 20
    python scripts/trending_bgm_selector.py --date 2026-04-22 --explain
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ムード定義 → generate_bgm パラメータ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MOODS = {
    'upbeat': {
        'bpm': 110, 'sparkle': True, 'soft_kick': True, 'volume': 0.78,
        'key_hint': 'major',
        'desc': '🎉 アップビート (新発表・周年・GW)',
    },
    'gentle': {
        'bpm': 82, 'sparkle': True, 'soft_kick': False, 'volume': 0.70,
        'key_hint': 'minor',
        'desc': '🌧 ジェントル (雨・落ち着き)',
    },
    'dramatic': {
        'bpm': 96, 'sparkle': False, 'soft_kick': True, 'volume': 0.82,
        'key_hint': 'minor',
        'desc': '⚠ ドラマティック (混雑警報・ハロウィン)',
    },
    'mystery': {
        'bpm': 88, 'sparkle': True, 'soft_kick': False, 'volume': 0.75,
        'key_hint': 'minor',
        'desc': '🌙 ミステリー (新エリア・夜)',
    },
    'heroic': {
        'bpm': 102, 'sparkle': True, 'soft_kick': True, 'volume': 0.80,
        'key_hint': 'major',
        'desc': '✨ ヒロイック (周年・特別イベント)',
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# トリガー → ムード マッピング
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC_TO_MOOD = {
    "🎉 25周年・記念":      'heroic',
    "🆕 新エリア・新アトラク": 'mystery',
    "🎃 ハロウィン":         'dramatic',
    "🎄 クリスマス":         'upbeat',
    "🌸 春・桜":            'gentle',
    "☀️ サマー":            'upbeat',
    "🛡 トラブル・運休":     'dramatic',
    "📰 その他":            'gentle',
}


def _load_trend_data(date_str: str) -> dict | None:
    p = PROJECT_DIR / "reports" / f"disney_trend_{date_str}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def _select_hot_topic(data: dict) -> str | None:
    """Hot Topic からカテゴリラベル を返す"""
    try:
        from scripts.generate_trend_digest import select_hot_topic
        ht = select_hot_topic(data)
        return ht.get("topic") if ht else None
    except Exception:
        return None


def _is_weekend(date_str: str) -> bool:
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').weekday() >= 5
    except Exception:
        return False


def select_mood(date_str: str,
                 weather: dict | None = None,
                 event: tuple | None = None) -> tuple[str, str]:
    """
    Returns: (mood_key, reason_text)
    """
    # 1. イベント (祝日/特別日) > Hot Topic > 天気 > 平日デフォ の優先順位
    if event:
        label, desc = event
        if "ハロウィン" in desc:
            return 'dramatic', f"event: {desc}"
        if "クリスマス" in desc:
            return 'upbeat', f"event: {desc}"
        if "周年" in desc or "TDR" in desc:
            return 'heroic', f"event: {desc}"
        return 'upbeat', f"event: {desc}"

    data = _load_trend_data(date_str)
    if data:
        topic = _select_hot_topic(data)
        if topic and topic in TOPIC_TO_MOOD:
            return TOPIC_TO_MOOD[topic], f"hot topic: {topic}"

    if weather:
        if weather.get("rain_pop", 0) >= 60 or weather.get("rain_mm", 0) >= 5:
            return 'gentle', f"rain forecast {weather.get('rain_pop', '?')}%"
        if weather.get("t_max", 0) >= 30:
            return 'upbeat', f"hot day {weather.get('t_max', '?')}℃"

    if _is_weekend(date_str):
        return 'upbeat', "weekend"
    return 'gentle', "weekday default"


def _key_to_park(mood_key: str, park: str) -> str:
    """
    minor mood なら sea (短調進行 Am-F-C-G), major なら land (C-G-Am-F)
    """
    mood = MOODS.get(mood_key, MOODS['gentle'])
    if mood['key_hint'] == 'minor':
        return 'sea'
    return 'land'


def generate_trending_bgm(date_str: str, park: str = 'sea',
                          duration: float = 20.0,
                          out_path: str | None = None,
                          weather: dict = None,
                          event: tuple = None) -> dict:
    """
    Returns: {mood, reason, bgm_path, params}
    """
    mood_key, reason = select_mood(date_str, weather=weather, event=event)
    mood = MOODS[mood_key]
    # park は元の指定をベースにしつつ、ムード由来の bgm_park を合成
    bgm_park = _key_to_park(mood_key, park)

    out_path = out_path or str(
        PROJECT_DIR / "predictions_x" /
        f"trending_bgm_{mood_key}_{park}_{date_str}.wav"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    from generate_bgm import generate_bgm_wav
    generate_bgm_wav(
        output_path=out_path,
        duration=duration,
        park=bgm_park,
        bpm=mood['bpm'],
        sparkle=mood['sparkle'],
        soft_kick=mood['soft_kick'],
        volume=mood['volume'],
    )
    return {
        "mood": mood_key,
        "mood_desc": mood['desc'],
        "reason": reason,
        "bgm_path": out_path,
        "bgm_park": bgm_park,
        "params": {k: v for k, v in mood.items() if k != 'desc'},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument("--park", choices=['sea', 'land'], default='sea')
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--out", default=None)
    parser.add_argument("--explain", action="store_true",
                        help="ムード判定だけ表示 (BGM生成しない)")
    parser.add_argument("--with-weather", action="store_true",
                        help="天候も加味")
    args = parser.parse_args()

    weather = None
    event = None
    if args.with_weather:
        try:
            from scripts.weather_adaptive import fetch_weather, detect_event
            weather = fetch_weather(args.date)
            event = detect_event(args.date)
        except Exception as e:
            print(f"⚠️ weather取得失敗: {e}")

    if args.explain:
        m, r = select_mood(args.date, weather=weather, event=event)
        print(f"📅 {args.date}")
        print(f"🎵 mood = {m}  ({MOODS[m]['desc']})")
        print(f"📝 reason: {r}")
        return 0

    result = generate_trending_bgm(
        args.date, park=args.park, duration=args.duration,
        out_path=args.out, weather=weather, event=event,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
