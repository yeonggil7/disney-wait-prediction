#!/usr/bin/env python3
"""
Instagram自動投稿スクリプト

毎日20:00に翌日のディズニー待ち時間予測を Instagram に投稿
- フィード（縦長 1080x1350 / 4:5）画像 + 長文キャプション + ハッシュタグ
- カルーセル / ストーリーズもオプションで対応

使用例:
  python daily_instagram_post.py --dry-run               # 投稿せず生成のみ
  python daily_instagram_post.py --post                  # 翌日分を投稿
  python daily_instagram_post.py --date 2026-04-20 --post
  python daily_instagram_post.py --post --carousel       # シー+ランドを1投稿のカルーセルに
  python daily_instagram_post.py --post --carousel9             # ランド+シーのカルーセル
  python daily_instagram_post.py --post --carousel9 --sea-only  # シーのみ9枚構成カルーセル
  python daily_instagram_post.py --post --story          # ストーリーズも投稿
  python daily_instagram_post.py --post --sea-only
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

from generate_instagram_heatmap import (
    generate_instagram_image,
    PARK_THEMES,
)
from generate_x_heatmap import (
    SEA_TARGET_ATTRACTIONS, LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES, LAND_DISPLAY_NAMES,
    get_sea_closures, get_land_closures,
)


# ---------------------------------------------------------------------------
# キャプション生成
# ---------------------------------------------------------------------------
SEA_HASHTAGS = [
    '#ディズニーシー', '#tokyodisneysea', '#tds', '#tdr', '#tdr_now',
    '#ディズニー', '#disney', '#東京ディズニーシー',
    '#待ち時間', '#ディズニー待ち時間', '#ディズニー混雑',
    '#ディズニー予測', '#aiディズニー',
    '#ソアリン', '#タワーオブテラー', '#トイストーリーマニア',
    '#アナとエルサのフローズンジャーニー', '#fantasysprings',
    '#ディズニー好きな人と繋がりたい', '#ディズニー旅行',
]

LAND_HASHTAGS = [
    '#ディズニーランド', '#tokyodisneyland', '#tdl', '#tdr', '#tdr_now',
    '#ディズニー', '#disney', '#東京ディズニーランド',
    '#待ち時間', '#ディズニー待ち時間', '#ディズニー混雑',
    '#ディズニー予測', '#aiディズニー',
    '#美女と野獣', '#美女と野獣魔法のものがたり', '#ビッグサンダーマウンテン',
    '#プーさんのハニーハント', '#ベイマックス',
    '#ディズニー好きな人と繋がりたい', '#ディズニー旅行',
]


def _weekday_ja(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]


def _get_target_closures(park, date_str, targets):
    """固定休止情報と公式当日休止情報を統合して返す"""
    if park == 'sea':
        legacy = list(get_sea_closures(date_str).keys())
    else:
        legacy = list(get_land_closures(date_str).keys())

    try:
        from fetch_closed_attractions import get_matched_closed_attractions
        official = get_matched_closed_attractions(
            park=park,
            attraction_list=targets,
            target_date=date_str,
        )
    except Exception:
        official = []

    seen = set()
    closures = []
    for name in legacy + list(official or []):
        if name in targets and name not in seen:
            seen.add(name)
            closures.append(name)
    return closures


def _build_caption(park, date_str, insights=None):
    """Instagram キャプションを生成（〜2200文字制限）"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = _weekday_ja(date_str)

    if park == 'sea':
        emoji = '🌊'
        name = 'ディズニーシー'
        targets = SEA_TARGET_ATTRACTIONS
        closures = _get_target_closures(park, date_str, targets)
        display_names = SEA_DISPLAY_NAMES
        hashtags = SEA_HASHTAGS
    else:
        emoji = '🏰'
        name = 'ディズニーランド'
        targets = LAND_TARGET_ATTRACTIONS
        closures = _get_target_closures(park, date_str, targets)
        display_names = LAND_DISPLAY_NAMES
        hashtags = LAND_HASHTAGS

    # トレンド連動ハッシュタグを先頭に追加
    try:
        sys.path.insert(0, str(PROJECT_DIR / 'scripts'))
        from trend_hashtags import get_trend_hashtags
        trend_tags = get_trend_hashtags(date=date_str, max_n=4, exclude=hashtags)
        if trend_tags:
            hashtags = trend_tags + list(hashtags)
    except Exception:
        pass

    lines = []
    lines.append(f"{emoji} 明日{name}行く人へ")
    lines.append("朝の作戦会議はこの3つだけ見ればOK")
    lines.append("")
    lines.append(f"{emoji} {name} AI待ち時間予測")
    lines.append(f"📅 {dt.month}月{dt.day}日({day}) の混雑予測")
    lines.append("")

    if insights:
        if insights.get('attr_max_list'):
            top_name, top_wait = insights['attr_max_list'][0]
            lines.append(f"1. 最警戒: {top_name} 最大{top_wait}分")
        lines.append(f"2. 空きやすい時間: {insights['calm_time']}頃")
        if insights.get('peak_time'):
            lines.append(f"3. ピーク: {insights['peak_time']}前後")
        lines.append("")
        lines.append(f"{insights['congestion_emoji']} 全体の混雑度: {insights['congestion']}")
        lines.append(f"📊 平均待ち時間: 約{insights['avg_wait']}分")
        lines.append(f"⏰ 比較的空いてる時間: {insights['calm_time']}〜")
        if insights.get('peak_time'):
            lines.append(f"📈 ピーク時間帯: {insights['peak_time']}前後")
        lines.append("")

        if insights.get('attr_max_list'):
            lines.append("【主要アトラクション 最大待ち時間予測】")
            for nm, wait in insights['attr_max_list']:
                lines.append(f"・{nm} 最大{wait}分")
            lines.append("")

    if closures:
        closed_names = [display_names.get(a, a) for a in closures]
        lines.append(f"⚠️ 休止中: {', '.join(closed_names)}")
        lines.append("")

    lines.append("―――――――――――――――")
    lines.append("📲 毎日20時に翌日の予測を投稿中")
    lines.append("💬 朝イチ派 / 夜狙い派、コメントで教えてください")
    lines.append("📩 一緒に行く人に送って作戦会議に使ってください")
    lines.append("💾 保存して当日の回り方に役立てて♪")
    lines.append("👉 フォローはプロフィールから @disney_ai_wait")
    lines.append("")
    lines.append("※AIによる予測のため、実際の待ち時間とは異なる場合があります")
    lines.append("")
    lines.append(' '.join(hashtags))

    caption = '\n'.join(lines)
    # Instagramキャプションは2200文字まで
    if len(caption) > 2200:
        caption = caption[:2197] + '...'
    return caption


# ---------------------------------------------------------------------------
# インサイト取得（daily_x_post.py と同じロジック）
# ---------------------------------------------------------------------------
def _get_insights(date_str, park):
    try:
        from generate_instagram_carousel9 import _prepare, _top_rank

        _pivot, _closures, _predictions, valid, stats, _closed, _short_map = _prepare(date_str, park)
        if valid is None or valid.empty:
            return None

        rank = _top_rank(valid, 10)
        attr_max_list = [(row.short_name, int(row.max_round))
                         for row in rank.itertuples(index=False)]

        avg_wait = int(stats['avg_wait'])
        calm_time = stats['calm_time']
        peak_time = stats['peak_time']

        if avg_wait >= 60:
            cong, emj = '激混み', '🔴'
        elif avg_wait >= 40:
            cong, emj = '混雑', '🟠'
        elif avg_wait >= 25:
            cong, emj = 'やや混雑', '🟡'
        else:
            cong, emj = '快適', '🟢'

        return {
            'attr_max_list': attr_max_list,
            'avg_wait': avg_wait,
            'calm_time': calm_time,
            'peak_time': peak_time,
            'congestion': cong,
            'congestion_emoji': emj,
        }
    except Exception as e:
        print(f"⚠️ インサイト取得失敗 ({park}): {e}")
        return None


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser(
        description='Instagram自動投稿スクリプト（縦長 4:5 フィード）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python daily_instagram_post.py --dry-run
  python daily_instagram_post.py --date 2026-04-20 --post
  python daily_instagram_post.py --post --sea-only
  python daily_instagram_post.py --post --carousel9
  python daily_instagram_post.py --post --carousel
  python daily_instagram_post.py --post --story
        """
    )
    parser.add_argument('--date', '-d', default=tomorrow,
                        help=f'予測日 (default: {tomorrow})')
    parser.add_argument('--post', '-p', action='store_true', help='Instagramに投稿')
    parser.add_argument('--dry-run', action='store_true', help='投稿せず内容を表示')
    parser.add_argument('--sea-only', action='store_true', help='シーのみ')
    parser.add_argument('--land-only', action='store_true', help='ランドのみ')
    parser.add_argument('--carousel', action='store_true',
                        help='シー+ランドを1つのカルーセル投稿にまとめる')
    parser.add_argument('--carousel9', action='store_true',
                        help='参考投稿風の9枚構成カルーセルを生成/投稿')
    parser.add_argument('--hook', choices=['off', 'auto', 'V1_curiosity',
                                            'V2_stat', 'V3_warning', 'V4_cta'],
                        default='auto',
                        help='カルーセル先頭にフック画像を追加 (A/Bテスト)')
    parser.add_argument('--story', action='store_true',
                        help='9:16 ストーリーズも投稿（追加投稿）')
    parser.add_argument('--output', '-o', default='predictions_x',
                        help='出力ディレクトリ')
    parser.add_argument('--handle', default='@disney_ai_wait')

    args = parser.parse_args()
    date = args.date
    output_dir = args.output

    print("=" * 60)
    print("📸 TDR AI待ち時間予測 - Instagram自動投稿")
    print("=" * 60)
    print(f"📅 予測日: {date}")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📐 アスペクト: 4:5 縦長 (1080x1350)" + (" + 9:16 ストーリーズ" if args.story else ""))
    print("=" * 60)

    parks = []
    if not args.land_only:
        parks.append('sea')
    if not args.sea_only:
        parks.append('land')

    # ---------- 画像生成 ----------
    feed_images = {}
    story_images = {}
    carousel9_images = {}
    combined_carousel9 = args.carousel9 and len(parks) > 1

    if combined_carousel9:
        print("\n🎢 ランド+シー カルーセル画像生成中...")
        from generate_instagram_carousel9 import generate_combined_carousel9
        carousel9_images['both'] = generate_combined_carousel9(
            date, output_dir=output_dir, handle=args.handle
        )
        feed_images['both'] = carousel9_images['both'][0] if carousel9_images['both'] else None

    for park in parks:
        if not combined_carousel9:
            print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} 画像生成中...")
        if args.carousel9 and not combined_carousel9:
            from generate_instagram_carousel9 import generate_carousel9
            carousel9_images[park] = generate_carousel9(
                date, park=park, output_dir=output_dir, handle=args.handle
            )
            feed_images[park] = carousel9_images[park][0] if carousel9_images[park] else None
        elif not args.carousel9:
            feed_images[park] = generate_instagram_image(
                date, park, layout='feed', output_dir=output_dir, handle=args.handle
            )
        if args.story:
            story_images[park] = generate_instagram_image(
                date, park, layout='story', output_dir=output_dir, handle=args.handle
            )

    # ---------- キャプション生成 ----------
    captions = {}
    for park in parks:
        insights = _get_insights(date, park)
        captions[park] = _build_caption(park, date, insights)

    # ---------- 表示 ----------
    if combined_carousel9:
        combo_caption = _build_carousel_caption(parks, date, captions)
        print("\n" + "=" * 60)
        print("🎢 【ランド+シー】カルーセル:")
        print("-" * 60)
        print(combo_caption)
        print("-" * 60)
        print(f"📏 文字数: {len(combo_caption)}/2200")
        print(f"🖼️  画像: {feed_images.get('both')}")
        print(f"🎠 カルーセル: {len(carousel9_images.get('both') or [])}枚")
        for p in carousel9_images.get('both') or []:
            print(f"   - {p}")

    for park in parks:
        if combined_carousel9:
            continue
        cap = captions[park]
        img = feed_images.get(park)
        print("\n" + "=" * 60)
        print(f"{PARK_THEMES[park]['emoji']} 【{PARK_THEMES[park]['name']}】キャプション:")
        print("-" * 60)
        print(cap)
        print("-" * 60)
        print(f"📏 文字数: {len(cap)}/2200")
        if img:
            print(f"🖼️  画像: {img}")
        if args.carousel9 and carousel9_images.get(park):
            print(f"🎠 9枚カルーセル: {len(carousel9_images[park])}枚")
            for p in carousel9_images[park]:
                print(f"   - {p}")
        if args.story and story_images.get(park):
            print(f"📖 ストーリーズ: {story_images[park]}")

    # ---------- 投稿 ----------
    if args.post and not args.dry_run:
        # バックエンド (graph / instagrapi) をディスパッチャー経由で選択
        from post_via_instagram import (
            _get_default_poster,
            _select_backend,
            check_connection,
        )
        backend = _select_backend()
        print(f"\n📡 Instagram バックエンド: {backend}")
        if args.carousel9 and combined_carousel9 and backend == 'graph':
            if _already_posted_carousel(date):
                print("\n✅ 既に投稿済みのため、新規投稿は行いません")
                return 0
        if not check_connection():
            print("\n❌ Instagram 接続失敗。.env の認証情報を確認してください。")
            return 1
        poster = _get_default_poster()

        posted = 0

        if args.carousel9:
            if combined_carousel9:
                images = carousel9_images.get('both') or []
                combo_caption = _build_carousel_caption(parks, date, captions)
                print("\n🎠 ランド+シー カルーセル投稿中...")
                ok = poster.post_carousel(images, combo_caption, extra={
                    "carousel": True,
                    "n_slides": len(images),
                    "format": "carousel9",
                    "target_date": date,
                    "park": "both",
                }) if 'extra' in poster.post_carousel.__code__.co_varnames \
                    else poster.post_carousel(images, combo_caption)
                if ok:
                    posted += 1
            else:
                for park in parks:
                    images = carousel9_images.get(park) or []
                    if not images:
                        continue
                    print(f"\n🎠 {PARK_THEMES[park]['name']} 9枚カルーセル投稿中...")
                    ok = poster.post_carousel(images, captions[park], extra={
                        "carousel": True,
                        "n_slides": len(images),
                        "format": "carousel9",
                        "target_date": date,
                        "park": park,
                    }) if 'extra' in poster.post_carousel.__code__.co_varnames \
                        else poster.post_carousel(images, captions[park])
                    if ok:
                        posted += 1
                    time.sleep(15)
        elif args.carousel and len(parks) > 1:
            # シー+ランドを1投稿に
            images = [feed_images[p] for p in parks if feed_images.get(p)]
            hook_variant = None
            if args.hook != 'off':
                try:
                    sys.path.insert(0, str(PROJECT_DIR / 'scripts'))
                    from generate_carousel_hook import (
                        generate_hook_image, resolve_hook_variant,
                    )
                    hook_variant = resolve_hook_variant(date, mode=args.hook)
                    sea_avg = land_avg = None
                    busiest = []
                    for park in parks:
                        ins = _get_insights(date, park)
                        if ins:
                            v = ins.get('avg_wait')
                            if park == 'sea':
                                sea_avg = v
                            else:
                                land_avg = v
                            for nm, _ in (ins.get('attr_max_list') or [])[:3]:
                                busiest.append(nm)
                    hook_img = generate_hook_image(
                        hook_variant, date,
                        sea_avg=sea_avg, land_avg=land_avg,
                        busiest_attractions=busiest,
                    )
                    print(f"   🪝 hook variant = {hook_variant}: {hook_img}")
                    images = [hook_img] + images
                except Exception as e:
                    print(f"   ⚠️ hook 画像生成失敗 (継続): {e}")
            combo_caption = _build_carousel_caption(parks, date, captions)
            print(f"\n🎠 カルーセル投稿中（{len(images)}枚）...")
            extra_meta = {"carousel": True, "n_slides": len(images)}
            if hook_variant:
                extra_meta["hook_variant"] = hook_variant
                extra_meta["target_date"] = date
            ok = poster.post_carousel(images, combo_caption, extra=extra_meta) \
                if 'extra' in poster.post_carousel.__code__.co_varnames \
                else poster.post_carousel(images, combo_caption)
            if ok:
                posted += 1
        else:
            for park in parks:
                img = feed_images.get(park)
                if not img:
                    continue
                print(f"\n{PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} 投稿中...")
                if poster.post_photo(img, captions[park]):
                    posted += 1
                time.sleep(15)

        if args.story:
            for park in parks:
                story_img = story_images.get(park)
                if not story_img:
                    continue
                print(f"\n📖 {PARK_THEMES[park]['name']} ストーリーズ投稿中...")
                if poster.post_story(story_img):
                    posted += 1
                time.sleep(10)

        print(f"\n✅ {posted}件の投稿が完了しました")

    elif args.dry_run:
        total = len(feed_images) + (len(story_images) if args.story else 0)
        print(f"\n🔍 ドライラン: {total}件の投稿がスキップされました")
    else:
        print("\n💡 投稿するには --post オプションを追加してください")

    print("\n📁 生成ファイル:")
    for park, img in feed_images.items():
        if img:
            if park == 'both':
                print(f"   🎢 ランド+シー (カルーセル表紙): {img}")
            else:
                print(f"   {PARK_THEMES[park]['emoji']} {PARK_THEMES[park]['name']} (フィード): {img}")
    for park, img in story_images.items():
        if img:
            print(f"   📖 {PARK_THEMES[park]['name']} (ストーリーズ): {img}")

    print("\n✅ 完了!")
    return 0


def _build_carousel_caption(parks, date_str, captions):
    """カルーセル用に統合キャプションを作る（先頭にサマリー、詳細は省略）"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = _weekday_ja(date_str)

    head = []
    head.append(f"🎢 東京ディズニーリゾート AI待ち時間予測")
    head.append(f"📅 {dt.month}月{dt.day}日({day})")
    head.append("")
    head.append("➡ スワイプでシー＆ランド両方をチェック！")
    head.append("📩 一緒に行く人に送って、朝の作戦会議に使ってください")
    head.append("")

    body_parts = []
    for park in parks:
        cap = captions[park]
        # ハッシュタグ部分を除外して結合
        text = cap.split('―――――――――――――――')[0].strip()
        body_parts.append(text)
        body_parts.append("")

    # ハッシュタグは結合（重複除去）
    seen = set()
    all_tags = []
    for park in parks:
        tag_line = captions[park].split('\n')[-1]
        for tag in tag_line.split():
            if tag.startswith('#') and tag not in seen:
                seen.add(tag)
                all_tags.append(tag)

    footer = []
    footer.append("―――――――――――――――")
    footer.append("📲 毎日20時に翌日の予測を投稿中")
    footer.append("💬 明日行くなら「シー」か「ランド」をコメントで教えてください")
    footer.append("📩 グループLINEに送る用の予報です")
    footer.append("👉 @disney_ai_wait をフォロー")
    footer.append("")
    footer.append(' '.join(all_tags))

    caption = '\n'.join(head + body_parts + footer)
    if len(caption) > 2200:
        caption = caption[:2197] + '...'
    return caption


def _already_posted_carousel(date_str, lookback=20):
    """同じ日付のTDRカルーセルが直近に投稿済みならTrueを返す。"""
    try:
        import requests
        from post_via_instagram_graph import (
            GRAPH_BASE,
            INSTAGRAM_ACCESS_TOKEN,
            INSTAGRAM_BUSINESS_ACCOUNT_ID,
        )
    except Exception:
        return False

    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        return False

    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day = _weekday_ja(date_str)
    date_marker = f"{dt.month}月{dt.day}日({day})"
    title_marker = "東京ディズニーリゾート AI待ち時間予測"

    try:
        res = requests.get(
            f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media",
            params={
                "fields": "id,caption,timestamp",
                "limit": lookback,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=30,
        )
        if not res.ok:
            return False
        for item in res.json().get("data", []):
            caption = item.get("caption") or ""
            if title_marker in caption and date_marker in caption:
                print(f"⏭️  同日カルーセル投稿済みのためスキップ: {date_marker} media_id={item.get('id')}")
                return True
    except Exception as e:
        print(f"⚠️ 重複投稿チェック失敗（継続）: {e}")
    return False


if __name__ == '__main__':
    sys.exit(main())
