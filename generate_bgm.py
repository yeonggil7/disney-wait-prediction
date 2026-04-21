"""
リール用 BGM 生成モジュール (著作権フリー / 自前生成)

ffmpeg だけだと音楽的に厳しいので numpy で合成し、
標準ライブラリの `wave` で 16bit PCM WAV を書き出す。

設計コンセプト:
- 90BPM・4拍子のチル系
- メイン: 順進行コード (I-V-vi-IV / Am-F-C-G 等) を sine + 微弱倍音で合成
- パッド系: アタックゆっくり / リリース長め
- 軽いキラキラ装飾音 (high sine, 短いエンベロープ) をワンショットで散らす
- ローパス + 軽いソフトクリップで耳触り良く
- 全体に fade in/out (1秒)

パークごとの差分:
- sea : Am (短調寄り) ベース、暗めで落ち着いた雰囲気
- land: C (長調) ベース、明るくポップ

ライセンス: 純粋に numpy で生成した正弦波 → 著作権発生せず
"""

from __future__ import annotations

import math
import os
import wave
import struct
from typing import List, Tuple

import numpy as np


SAMPLE_RATE = 48000


# =============================================================================
# 楽典: コード / 進行
# =============================================================================
# 4 chord progressions (3-4 voicings)
# (root, third, fifth) Hz
_CHORDS = {
    'C':  (261.63, 329.63, 392.00),  # C major
    'G':  (196.00, 246.94, 392.00),  # G major / first inv
    'Am': (220.00, 261.63, 329.63),  # A minor
    'F':  (174.61, 220.00, 261.63),  # F major
    'Em': (164.81, 196.00, 246.94),  # E minor
    'Dm': (146.83, 174.61, 220.00),  # D minor
    'Bb': (233.08, 293.66, 349.23),  # Bb major
}

# pad パッチ: 各パークの 4 コード進行 (合計 4 chords loop)
_PROG = {
    # Land : I-V-vi-IV (王道明るい)
    'land': ['C', 'G', 'Am', 'F'],
    # Sea : vi-IV-I-V (Andante、しっとり)
    'sea':  ['Am', 'F', 'C', 'G'],
}

# 装飾音 (キラキラ) のスケール (Hz) ペンタトニック C
_SPARKLE_SCALE = [
    523.25,   # C5
    587.33,   # D5
    659.25,   # E5
    783.99,   # G5
    880.00,   # A5
    1046.50,  # C6
    1318.51,  # E6
]


# =============================================================================
# シンセサイザ
# =============================================================================
def _adsr(n_samples: int, attack: float, decay: float,
          sustain: float, release: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """ADSR エンベロープ (0-1)"""
    a = max(1, int(attack * sr))
    d = int(decay * sr)
    r = int(release * sr)
    s = max(1, n_samples - a - d - r)
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False),
        np.linspace(1, sustain, d, endpoint=False) if d > 0 else np.array([]),
        np.full(s, sustain),
        np.linspace(sustain, 0, r, endpoint=True) if r > 0 else np.array([]),
    ])
    if len(env) < n_samples:
        env = np.pad(env, (0, n_samples - len(env)))
    return env[:n_samples]


def _voice(freq: float, duration: float, sr: int = SAMPLE_RATE,
           harmonics: Tuple[Tuple[int, float], ...] = ((1, 0.7), (2, 0.18), (3, 0.06)),
           detune_cents: float = 0.0) -> np.ndarray:
    """正弦波 + 倍音 + デチューン (パッド系の柔らかい音)"""
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    detune = 2 ** (detune_cents / 1200.0)
    out = np.zeros(n, dtype=np.float64)
    for mult, amp in harmonics:
        out += amp * np.sin(2 * math.pi * freq * mult * detune * t)
    return out.astype(np.float32)


def _chord_pad(chord_name: str, duration: float,
               sr: int = SAMPLE_RATE) -> np.ndarray:
    """コードパッド: 三和音 + ベース + ゆるやかなエンベロープ"""
    notes = _CHORDS[chord_name]
    n = int(duration * sr)
    out = np.zeros(n, dtype=np.float32)

    # ベース (1オクターブ下)
    bass_freq = notes[0] / 2
    out += _voice(bass_freq, duration,
                  harmonics=((1, 0.55), (2, 0.10))) * 0.35

    # 三和音 (微デチューンで厚みを出す)
    for freq, detune in zip(notes, (-3.0, +0.0, +4.0)):
        out += _voice(freq, duration, detune_cents=detune) * 0.25

    env = _adsr(n, attack=0.30, decay=0.10, sustain=0.85, release=0.40)
    return out * env


def _sparkle(freq: float, start: float, duration: float = 0.45,
             sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """高音のキラッとした装飾音 (start 秒位置から再生)"""
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    # 高めの倍音強め
    wave_arr = (np.sin(2 * math.pi * freq * t) * 0.6 +
                np.sin(2 * math.pi * freq * 2 * t) * 0.25 +
                np.sin(2 * math.pi * freq * 3 * t) * 0.10)
    env = _adsr(n, attack=0.005, decay=0.05, sustain=0.5, release=0.40)
    return (wave_arr * env * 0.18).astype(np.float32), int(start * sr)


def _kick(start: float, sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    """ソフトキック (低域パルス)"""
    duration = 0.18
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    # 周波数ピッチダウン: 80Hz -> 40Hz
    f = 80 - 40 * (t / duration)
    phase = np.cumsum(2 * math.pi * f / sr)
    wave_arr = np.sin(phase)
    env = _adsr(n, attack=0.001, decay=0.06, sustain=0.4, release=0.10)
    return (wave_arr * env * 0.30).astype(np.float32), int(start * sr)


# =============================================================================
# フィルタ / マスタリング
# =============================================================================
def _lowpass(signal: np.ndarray, cutoff_hz: float = 5500.0,
             sr: int = SAMPLE_RATE) -> np.ndarray:
    """1pole IIR low-pass (耳触り柔らかく)"""
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = np.zeros_like(signal)
    prev = 0.0
    for i, x in enumerate(signal):
        prev = prev + alpha * (x - prev)
        out[i] = prev
    return out


def _soft_clip(signal: np.ndarray, drive: float = 0.85) -> np.ndarray:
    """tanh ソフトクリップ (歪まずに -1〜1 に収める)"""
    return np.tanh(signal * drive)


def _fade_in_out(signal: np.ndarray, fade_sec: float = 1.0,
                 sr: int = SAMPLE_RATE) -> np.ndarray:
    f = int(fade_sec * sr)
    f = min(f, len(signal) // 2)
    if f <= 0:
        return signal
    out = signal.copy()
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    return out


# =============================================================================
# 公開API
# =============================================================================
def generate_bgm_wav(output_path: str, duration: float = 20.0,
                     park: str = 'sea',
                     volume: float = 0.78,
                     bpm: float = 92.0,
                     sparkle: bool = True,
                     soft_kick: bool = True,
                     sr: int = SAMPLE_RATE) -> str:
    """
    BGM を WAV (16bit PCM stereo) として書き出す。

    Args:
        output_path : 書き出し先 .wav
        duration    : 秒
        park        : 'sea' or 'land'
        volume      : 0-1 全体音量 (動画にミックス時は ffmpeg 側でも下げる)
        bpm         : テンポ (装飾音の配置位置に使用)
        sparkle     : True で 1拍ごとに高音装飾音
        soft_kick   : True で 1小節頭にキック

    Returns:
        output_path
    """
    progression: List[str] = list(_PROG.get(park, _PROG['land']))
    # 1コード = 2小節 (4拍 × 2 = 8拍)。bpm から尺計算
    beat_sec = 60.0 / bpm
    chord_sec = beat_sec * 8  # 1 chord = 8 beats
    n_chords = max(1, int(math.ceil(duration / chord_sec)))

    n_total = int(duration * sr)
    track = np.zeros(n_total, dtype=np.float32)

    # --- パッド (コード進行ループ) ---
    cursor = 0
    chord_seq = (progression * ((n_chords // len(progression)) + 1))[:n_chords]
    for chord_name in chord_seq:
        chunk = _chord_pad(chord_name, chord_sec, sr=sr)
        end = min(cursor + len(chunk), n_total)
        track[cursor:end] += chunk[:end - cursor]
        cursor += len(chunk)
        if cursor >= n_total:
            break

    # --- 装飾音 (キラッ) を裏拍に少しずつ ---
    if sparkle:
        rng = np.random.default_rng(seed=hash(park + str(int(duration))) & 0xFFFFFFFF)
        # 2拍ごとに 1 装飾音 (拍 0,2,4,...)
        n_beats = int(duration / beat_sec)
        for beat in range(0, n_beats, 2):
            t0 = beat * beat_sec + (rng.random() * 0.04)  # 微妙にずらす
            if t0 >= duration - 0.5:
                break
            # コードに合わせた音域 (ペンタトニック)
            freq = float(rng.choice(_SPARKLE_SCALE))
            chunk, off = _sparkle(freq, start=t0, sr=sr)
            end = min(off + len(chunk), n_total)
            track[off:end] += chunk[:end - off]

    # --- ソフトキック (1小節頭) ---
    if soft_kick:
        # 1小節 = 4拍
        bar_sec = beat_sec * 4
        t = 0.0
        while t < duration - 0.3:
            chunk, off = _kick(t, sr=sr)
            end = min(off + len(chunk), n_total)
            track[off:end] += chunk[:end - off]
            t += bar_sec

    # --- マスタリング ---
    track = _lowpass(track, cutoff_hz=5200.0, sr=sr)
    track = _soft_clip(track, drive=0.85)

    # 全体ノーマライズ
    peak = float(np.max(np.abs(track))) or 1.0
    track = track / peak  # -1..1
    track *= volume

    # フェード
    track = _fade_in_out(track, fade_sec=1.0, sr=sr)

    # ステレオ化 (左右で装飾音の位相を微妙に変える擬似ステレオ)
    # ここではシンプルに同じ信号を両チャネルに
    stereo = np.stack([track, track], axis=1)

    # 16bit 整数化
    stereo_i16 = np.int16(np.clip(stereo, -1.0, 1.0) * 32767)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo_i16.tobytes())

    return output_path


# =============================================================================
# CLI
# =============================================================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="リール BGM 生成 (numpy)")
    parser.add_argument('--out', type=str, default='predictions_x/bgm_test.wav')
    parser.add_argument('--duration', type=float, default=20.0)
    parser.add_argument('--park', choices=['sea', 'land'], default='land')
    parser.add_argument('--bpm', type=float, default=92.0)
    parser.add_argument('--volume', type=float, default=0.42)
    parser.add_argument('--no-sparkle', action='store_true')
    parser.add_argument('--no-kick', action='store_true')
    args = parser.parse_args()

    path = generate_bgm_wav(
        args.out,
        duration=args.duration,
        park=args.park,
        bpm=args.bpm,
        volume=args.volume,
        sparkle=not args.no_sparkle,
        soft_kick=not args.no_kick,
    )
    size_kb = os.path.getsize(path) / 1024
    print(f"✅ BGM 生成: {path} ({size_kb:.1f}KB / {args.duration}s)")
