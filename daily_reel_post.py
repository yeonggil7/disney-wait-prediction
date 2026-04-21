#!/usr/bin/env python3
"""
Instagram Reels 自動投稿スクリプト

「30秒で分かる明日のディズニー混雑予報」リール動画 (mp4) を生成して投稿する。

使い方:
    python daily_reel_post.py --dry-run                          # 動画とキャプション生成のみ
    python daily_reel_post.py --post                             # 翌日分を投稿 (sea+land 2本)
    python daily_reel_post.py --post --park sea
    python daily_reel_post.py --post --date 2026-04-22
    python daily_reel_post.py --post --duration 25
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from generate_reel_video import generate_reel_video
from generate_instagram_heatmap import PARK_THEMES
from generate_x_heatmap import get_day_of_week_ja


# キャプション (Reels向けはやや短めで前半に情報集中)
HASHTAGS_COMMON = [
    '#ディズニー', '#disney', '#tdr', '#tdr_now',
    '#ディズニー混雑', '#ディズニー予測', '#ディズニー旅行',
    '#aiディズニー', '#ディズニー好きな人と繋がりたい',
    '#ディズニーリール', '#リール',
]
HASHTAGS_SEA = [
    '#ディズニーシー', '#tokyodisneysea', '#tds', '#東京ディズニーシー',
    '#ソアリン', '#fantasysprings', '#アナとエルサのフローズンジャーニー',
]
HASHTAGS_LAND = [
    '#ディズニーランド', '#tokyodisneyland', '#tdl', '#東京ディズニーランド',
    '#美女と野獣', '#美女と野獣魔法のものがたり', '#ビッグサンダーマウンテン',
]


def resolve_cover_variant(date_str: str, park: str, mode: str) -> str:
    """
    A/B テスト用にカバーバリアントを決定。

    'auto' のとき:
      doy (年中の日数) と park のオフセットで交互割当。
      → 1日2投稿 (sea+land) のうち必ず1つは old、もう1つは new に割り当てられる。
        週単位でも各パークが ~3-4 ずつのバランスに収束。

    Returns: 'new' or 'old'
    """
    if mode in ('new', 'old'):
        return mode
    try:
        doy = datetime.strptime(date_str, '%Y-%m-%d').timetuple().tm_yday
    except Exception:
        doy = 0
    park_offset = 0 if park == 'sea' else 1
    return ['old', 'new'][(doy + park_offset) % 2]


def _build_caption(park: str, date_str: str,
                    handle: str = '@disney_ai_wait') -> str:
    """Reels キャプション (前半に強いCTA、Reelsは2200文字制限)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = get_day_of_week_ja(date_str)

    if park == 'sea':
        emoji = '🌊'
        park_name = 'ディズニーシー'
        tags = HASHTAGS_SEA + HASHTAGS_COMMON
    else:
        emoji = '🏰'
        park_name = 'ディズニーランド'
        tags = HASHTAGS_LAND + HASHTAGS_COMMON

    lines = [
        f"{emoji} 30秒で分かる！",
        f"{dt.month}/{dt.day}({day}) {park_name} AI混雑予報",
        "",
        "▶ 1日の待ち時間トレンドを完全可視化",
        "▶ 狙い目時間 / ピーク時間 まるわかり",
        "▶ 主要7ライドの時間帯別予測",
        "",
        "💾 保存して旅行プランに",
        "🔁 友達とシェアして賢く回ろう",
        "📲 フォローで毎日アップデート",
        "",
        f"👉 {handle}",
        "",
        "詳しい時間帯別ヒートマップは",
        "プロフィールのフィード投稿をチェック✨",
        "",
        "※AI予測です。実際の待ち時間とは異なる場合があります",
        "",
        ' '.join(tags),
    ]
    cap = '\n'.join(lines)
    if len(cap) > 2200:
        cap = cap[:2197] + '...'
    return cap


def main():
    parser = argparse.ArgumentParser(description='Instagram Reels 自動投稿')
    parser.add_argument('--date', type=str,
                        default=(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                        help='対象日 (デフォルト: 翌日)')
    parser.add_argument('--park', choices=['sea', 'land', 'both'], default='both')
    parser.add_argument('--sea-only', action='store_true')
    parser.add_argument('--land-only', action='store_true')
    parser.add_argument('--duration', type=int, default=20,
                        help='動画長 (秒) 5〜90 / Reels推奨 15〜30')
    parser.add_argument('--no-share-to-feed', action='store_true',
                        help='通常フィードに表示しない (Reelsタブのみ)')
    parser.add_argument('--bgm', type=str, default='auto',
                        help="'auto' (自動生成 / bgm/ 内ファイル優先), 'none' (静音), または音声ファイルパス")
    parser.add_argument('--bgm-volume-db', type=float, default=-8.0,
                        help='BGM 音量 dB (既定 -8dB)')
    parser.add_argument('--cover-variant', choices=['auto', 'new', 'old'],
                        default='auto',
                        help="カバーデザイン. 'auto'=日付×パークで交互割当 (A/Bテスト)")
    parser.add_argument('--post', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.sea_only:
        parks = ['sea']
    elif args.land_only:
        parks = ['land']
    elif args.park == 'both':
        parks = ['sea', 'land']
    else:
        parks = [args.park]

    date = args.date
    print(f"\n🎬 Reels投稿: {date} parks={parks} duration={args.duration}s\n")

    videos = {}      # park -> (mp4, cover)
    captions = {}
    variants = {}    # park -> 'new' | 'old'

    for park in parks:
        variant = resolve_cover_variant(date, park, args.cover_variant)
        variants[park] = variant
        print(f"🧪 {park}: cover_variant = {variant} (mode={args.cover_variant})")
        mp4, cover = generate_reel_video(date, park=park,
                                          duration=args.duration,
                                          bgm=args.bgm,
                                          bgm_volume_db=args.bgm_volume_db,
                                          cover_variant=variant)
        if mp4 is None:
            print(f"⚠️ {park}: 動画生成失敗、スキップ")
            continue
        videos[park] = (mp4, cover)
        captions[park] = _build_caption(park, date)

        print("\n" + "=" * 60)
        print(f"{PARK_THEMES[park]['emoji']} 【{PARK_THEMES[park]['name']}】キャプション:")
        print("-" * 60)
        print(captions[park])
        print("-" * 60)
        print(f"📏 文字数: {len(captions[park])}/2200")
        print(f"🎬 動画: {mp4}")
        print(f"🖼️  カバー: {cover}")

    if not videos:
        print("❌ 投稿対象なし")
        return 1

    if args.post and not args.dry_run:
        from post_via_instagram import (
            _get_default_poster, _select_backend, check_connection,
        )
        backend = _select_backend()
        print(f"\n📡 Instagram バックエンド: {backend}")
        if backend != 'graph':
            print("⚠️ Reels は Graph API バックエンドのみ対応 (INSTAGRAM_API_MODE=graph)")
            return 1
        if not check_connection():
            print("❌ Instagram 接続失敗")
            return 1
        poster = _get_default_poster()

        posted = 0
        for park in parks:
            if park not in videos:
                continue
            mp4, cover = videos[park]
            print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} Reels投稿中... "
                  f"(cover={variants[park]})")
            ok = poster.post_reel(
                mp4, captions[park],
                cover_path=cover,
                share_to_feed=not args.no_share_to_feed,
                extra={
                    "cover_variant": variants[park],
                    "park": park,
                    "target_date": date,
                    "duration": args.duration,
                    "bgm": args.bgm,
                },
            )
            if ok:
                posted += 1
            time.sleep(20)

        print(f"\n✅ {posted}件の Reels 投稿完了")
    elif args.dry_run:
        print(f"\n🔍 ドライラン: {len(videos)}件スキップ")
    else:
        print("\n💡 投稿するには --post を追加")

    return 0


if __name__ == '__main__':
    sys.exit(main())
