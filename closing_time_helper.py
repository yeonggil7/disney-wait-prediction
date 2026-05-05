#!/usr/bin/env python3
"""
閉園前判定ヘルパー

「夜に空く＝乗れる」ではない。
21:00閉園の場合、20:30時点で待ち時間 > 30分のアトラクションは
並んでも閉園までに乗れない可能性が高い。

このモジュールは、予測待ち時間データから「閉園前に乗れる候補」を
抽出し、判定ロジックを各投稿で共有するためのもの。
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_DIR = Path(__file__).parent.absolute()
SCHEDULE_OVERRIDES = PROJECT_DIR / 'chatbot' / 'data' / 'show_schedule_overrides.json'

DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"

# 判定ルール（閉園 21:00 を想定）
EVAL_OFFSET_MIN = 60   # 評価する時刻 = 閉園 - 60分 (= 20:00)
THRESHOLD_MIN = 30     # 評価時刻における待ち時間 ≤ 30分なら「閉園前候補」
LATE_CUTOFF_MIN = 30   # 閉園 - 30分 (= 20:30) 以降の長時間待ちは乗れない可能性


def _safe_load_overrides() -> dict:
    """営業時間オーバーライド設定を読み込む（存在しなければ空 dict）"""
    if not SCHEDULE_OVERRIDES.exists():
        return {}
    try:
        return json.loads(SCHEDULE_OVERRIDES.read_text(encoding='utf-8'))
    except Exception:
        return {}


def get_park_hours(date_str: str, park: str) -> tuple[str, str]:
    """指定日付・パークの開園・閉園時刻を返す。

    現状は overrides JSON にあれば優先、なければデフォルト 09:00–21:00。
    overrides の構造例:
      {
        "tds": {"2026-05-03": {"open": "08:00", "close": "22:00"}},
        "tdl": {"2026-05-03": {"open": "08:00", "close": "22:00"}}
      }
    """
    park_key = 'tds' if park == 'sea' else 'tdl'
    overrides = _safe_load_overrides()
    park_overrides = overrides.get(park_key, {}) if isinstance(overrides, dict) else {}
    if isinstance(park_overrides, dict) and date_str in park_overrides:
        entry = park_overrides[date_str]
        if isinstance(entry, dict):
            return (entry.get('open', DEFAULT_OPEN), entry.get('close', DEFAULT_CLOSE))
    return (DEFAULT_OPEN, DEFAULT_CLOSE)


def _round_up_10(x: float) -> int:
    return int(math.ceil(max(x, 0) / 10) * 10)


def _time_minus(hhmm: str, minutes: int) -> str:
    base = datetime.strptime(hhmm, "%H:%M")
    return (base - timedelta(minutes=minutes)).strftime("%H:%M")


def compute_pre_close_candidates(
    predictions: pd.DataFrame,
    closing_time: str = DEFAULT_CLOSE,
    short_names: dict | None = None,
    excluded: Iterable[str] = (),
    eval_offset_min: int = EVAL_OFFSET_MIN,
    threshold_min: int = THRESHOLD_MIN,
) -> list[tuple[str, int]]:
    """予測 DF から「閉園前候補」を抽出する。

    Parameters
    ----------
    predictions : pd.DataFrame
        予測結果。'time' (HH:MM) と 'attraction_name', 'predicted_wait_time' 必須。
    closing_time : str
        閉園時刻 ('HH:MM')。
    short_names : dict
        attraction_name → 表示用短縮名。
    excluded : Iterable[str]
        除外したい attraction_name の集合（休止中などを除く）。
    eval_offset_min, threshold_min : int
        評価する時刻 (=閉園-eval_offset) と、その時の待ち時間しきい値。

    Returns
    -------
    list[tuple[name, wait_min]]
        閉園前候補のリスト（待ち時間昇順）。空き具合が良いものから並ぶ。
    """
    if predictions is None or predictions.empty:
        return []

    eval_time = _time_minus(closing_time, eval_offset_min)
    short_names = short_names or {}
    excluded = set(excluded)

    target = predictions[predictions['time'] == eval_time]
    if target.empty:
        # 30分単位の time_slots でない場合に備えてフォールバック
        target = predictions.copy()
        target['_diff'] = target['time'].apply(
            lambda t: abs(
                (datetime.strptime(t, '%H:%M') - datetime.strptime(eval_time, '%H:%M'))
                .total_seconds()
            )
        )
        target = target.sort_values('_diff').groupby('attraction_name').head(1)

    candidates = []
    for _, row in target.iterrows():
        attr = row['attraction_name']
        if attr in excluded:
            continue
        wait = _round_up_10(row['predicted_wait_time'])
        if wait <= threshold_min:
            display = short_names.get(attr, attr[:8])
            candidates.append((display, wait))
    candidates.sort(key=lambda x: x[1])
    return candidates


def format_close_judge_block(closing_time: str = DEFAULT_CLOSE) -> str:
    """閉園前判定のルール文（投稿に挿入する短文ブロック）"""
    eval_time = _time_minus(closing_time, EVAL_OFFSET_MIN)
    cutoff_time = _time_minus(closing_time, LATE_CUTOFF_MIN)
    return (
        f"夜の判定({closing_time}閉園):\n"
        f"・{eval_time}時点で30分以下なら候補\n"
        f"・{cutoff_time}以降は乗れない可能性"
    )


def format_close_judge_block_short(closing_time: str = DEFAULT_CLOSE) -> str:
    """閉園前の注意書き（2行）"""
    eval_time = _time_minus(closing_time, EVAL_OFFSET_MIN)
    cutoff_time = _time_minus(closing_time, LATE_CUTOFF_MIN)
    return (
        f"{eval_time}時点で30分以下なら狙い目\n"
        f"※{cutoff_time}以降は乗れない可能性あり"
    )


def format_pre_close_candidates(
    candidates: list[tuple[str, int]],
    closing_time: str = DEFAULT_CLOSE,
    max_n: int = 4,
    fallback: str = "夜は混雑継続予想。閉園前は無理せず短時間施設へ",
) -> str:
    """閉園前候補リストを投稿テキスト形式に整形"""
    eval_time = _time_minus(closing_time, EVAL_OFFSET_MIN)
    if not candidates:
        return fallback
    lines = []
    for name, wait in candidates[:max_n]:
        lines.append(f"・{name} {eval_time}時点 約{wait}分")
    return "\n".join(lines)


__all__ = [
    'DEFAULT_OPEN',
    'DEFAULT_CLOSE',
    'EVAL_OFFSET_MIN',
    'THRESHOLD_MIN',
    'LATE_CUTOFF_MIN',
    'get_park_hours',
    'compute_pre_close_candidates',
    'format_close_judge_block',
    'format_close_judge_block_short',
    'format_pre_close_candidates',
]
