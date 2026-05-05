#!/usr/bin/env python3
"""
X(Twitter)自動投稿スクリプト - エンゲージメント最適化版
毎日20:00に翌日の待ち時間予測を投稿

改善ポイント:
- 予測データから具体的な数値を抽出してツイートに反映
- 曜日・イベントに応じたテンプレートローテーション
- エンゲージメントを誘導するCTA付き
- ハッシュタグ最適化
- 滞在時間を意識した長文ツイート
"""

import os
import sys
import time
import random
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

from post_via_xharness import post_to_twitter, check_connection as check_xharness

from generate_x_heatmap import (
    generate_sea_heatmap,
    generate_land_heatmap,
    get_sea_closures,
    get_land_closures,
    SEA_TARGET_ATTRACTIONS,
    LAND_TARGET_ATTRACTIONS,
    SEA_DISPLAY_NAMES,
    LAND_DISPLAY_NAMES
)

from closing_time_helper import (
    get_park_hours,
    compute_pre_close_candidates,
    format_close_judge_block_short,
    format_pre_close_candidates,
)

# ---------------------------------------------------------------------------
# 予測データ解析
# ---------------------------------------------------------------------------

SEA_SHORT_NAMES = {
    'ソアリン': 'ソアリン',
    'アナとエルサ': 'アナ雪',
    'センターオブジアース': 'センター',
    'タワーオブテラー': 'タワテラ',
    'トイストーリーマニア': 'トイマニ',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーパン',
    'プラザグリーティング': 'プラグリ',
    'レイジングスピリッツ': 'レイジング',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
}

LAND_SHORT_NAMES = {
    '美女と野獣の物語': '美女と野獣',
    'モンスターズ・インク': 'モンスターズ',
    'ミート・ミッキー': 'ミッキー',
    'プーさんのハニーハント': 'プーさん',
    'ベイマックスのハッピーライド': 'ベイマックス',
    'ビッグサンダーマウンテン': 'ビッグサンダー',
    'スプラッシュマウンテン': 'スプラッシュ',
}


def _get_prediction_insights(date_str, park='sea'):
    """予測データからインサイトを抽出（各アトラクションの最大待ち時間含む）"""
    try:
        if park == 'sea':
            from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
            predictor = DisneySeaWaitTimePredictorV3()
            targets = SEA_TARGET_ATTRACTIONS
            display = SEA_DISPLAY_NAMES
            short = SEA_SHORT_NAMES
            closures = get_sea_closures(date_str)
        else:
            from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
            predictor = DisneyLandWaitTimePredictorV3()
            targets = LAND_TARGET_ATTRACTIONS
            display = LAND_DISPLAY_NAMES
            short = LAND_SHORT_NAMES
            closures = get_land_closures(date_str)

        attractions = [a for a in targets if a not in closures]
        time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]
        predictions = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)

        if predictions is None:
            return None

        insights = {}

        # 各アトラクションの最大待ち時間（10分単位で繰り上げ）
        max_by_attr = predictions.groupby('attraction_name')['predicted_wait_time'].max()
        import math
        attr_max_list = []
        for attr_name in targets:
            if attr_name in closures:
                continue
            if attr_name in max_by_attr.index:
                max_wait = int(math.ceil(max_by_attr[attr_name] / 10) * 10)
                sname = short.get(attr_name, attr_name[:6])
                attr_max_list.append((sname, max_wait))
        attr_max_list.sort(key=lambda x: x[1], reverse=True)
        insights['attr_max_list'] = attr_max_list

        # 全体平均
        insights['avg_wait'] = int(predictions['predicted_wait_time'].mean())

        # 空いてる時間帯（参考値・午前/日中の最小）
        # ※ 閉園 1 時間前以降は閉園前判定に切り替えるためここでは集計から除外
        midday = predictions[predictions['time'] < '20:00']
        if not midday.empty:
            avg_by_time = midday.groupby('time')['predicted_wait_time'].mean()
            insights['calm_time'] = avg_by_time.idxmin()
        else:
            insights['calm_time'] = None

        # 閉園前判定用に予測 DF と short_names を保持
        insights['_predictions'] = predictions
        insights['_short_names'] = short
        insights['_excluded'] = list(closures.keys())

        # 混雑度判定
        avg = insights['avg_wait']
        if avg >= 60:
            insights['congestion'] = '激混み'
            insights['congestion_emoji'] = '🔴'
        elif avg >= 40:
            insights['congestion'] = '混雑'
            insights['congestion_emoji'] = '🟠'
        elif avg >= 25:
            insights['congestion'] = 'やや混雑'
            insights['congestion_emoji'] = '🟡'
        else:
            insights['congestion'] = '空いてる'
            insights['congestion_emoji'] = '🟢'

        return insights
    except Exception as e:
        print(f"⚠️ インサイト取得失敗: {e}")
        return None


# ---------------------------------------------------------------------------
# ツイートテンプレート
# ---------------------------------------------------------------------------

TIPS_SEA = [
    "💡 ソアリンは開園直後が狙い目！午前中に乗ると30分以上短い場合も",
    "💡 センター・オブ・ジ・アースは夕方が比較的空きます",
    "💡 トイストーリーマニアは18時以降がおすすめ",
    "💡 雨の日は屋外アトラクションが空く傾向あり",
    "💡 アナ雪エリアは昼過ぎが空きやすい時間帯",
    "💡 タワテラは夜のライトアップも最高！",
    "💡 ラプンツェルは昼と夕方のギャップが大きいので時間選びが重要",
]

TIPS_LAND = [
    "💡 美女と野獣は開園ダッシュが最も効果的！",
    "💡 スペースマウンテンは閉園間際が穴場",
    "💡 ビッグサンダーは夕方以降が空きます",
    "💡 プーさんは平日午前が空いてる傾向あり",
    "💡 バズ・ライトイヤーは夜が狙い目",
    "💡 スプラッシュは気温が低い日ほど空きます",
    "💡 パレード中は多くのアトラクションが空きます！",
]

CTA_VARIATIONS = [
    "明日行く人はリプで「行く」って教えて！",
    "一緒に行く人に送って作戦会議に使ってね",
    "朝イチ派？夜狙い派？リプで教えて！",
    "詳しいヒートマップは画像を保存して使ってね",
]

WEEKEND_EXTRAS = [
    "🎪 週末は混みやすいので早めの行動がカギ！",
    "🎪 週末は開園30分前には並ぶのがおすすめ",
    "🎪 週末のランチは11時前がベスト！混む前に",
]

def _get_weekday_ja(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return ['月', '火', '水', '木', '金', '土', '日'][dt.weekday()]

def _is_weekend(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() >= 4  # 金土日


def _build_tweet(park_emoji, park_name, date_str, insights, closures, display_names, tips, hashtags, park_key, cta_index=0):
    """共通ツイート生成"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = _get_weekday_ja(date_str)

    cta_seed = dt.timetuple().tm_yday + cta_index
    cta = CTA_VARIATIONS[cta_seed % len(CTA_VARIATIONS)]

    _, closing = get_park_hours(date_str, park_key)

    tweet = f"{park_emoji} 明日{park_name}行く人へ\n\n"
    tweet += f"{park_name} AI待ち時間予測\n"
    tweet += f"📅 {dt.month}/{dt.day}({day_name})"

    if insights:
        tweet += f" {insights['congestion_emoji']}{insights['congestion']}予想\n\n"
        for name, wait in insights['attr_max_list']:
            tweet += f"▸ {name} 最大{wait}分\n"
    else:
        tweet += "\n\n"

    closed_count = len(closures)
    if closed_count > 0:
        closed_names = [display_names.get(a, a)[:6] for a in closures.keys()]
        tweet += f"※休止: {', '.join(closed_names)}\n"

    # 閉園前判定（夜の候補）
    if insights and insights.get('_predictions') is not None:
        candidates = compute_pre_close_candidates(
            insights['_predictions'],
            closing_time=closing,
            short_names=insights.get('_short_names', {}),
            excluded=insights.get('_excluded', []),
        )
        if candidates:
            tweet += "\n🌙 夜の候補:\n"
            tweet += format_pre_close_candidates(candidates, closing_time=closing, max_n=2) + "\n"
        tweet += format_close_judge_block_short(closing) + "\n"

    tweet += "\n"
    tweet += cta + "\n"
    tweet += hashtags

    tweet = _trim_tweet(tweet)

    return tweet


def create_sea_tweet(date_str):
    closures = get_sea_closures(date_str)
    insights = _get_prediction_insights(date_str, 'sea')
    return _build_tweet(
        '🌊', 'ディズニーシー', date_str, insights, closures,
        SEA_DISPLAY_NAMES, TIPS_SEA,
        '#TDS #待ち時間 #TDR_now',
        park_key='sea',
        cta_index=0,
    )


def create_land_tweet(date_str):
    closures = get_land_closures(date_str)
    insights = _get_prediction_insights(date_str, 'land')
    return _build_tweet(
        '🏰', 'ディズニーランド', date_str, insights, closures,
        LAND_DISPLAY_NAMES, TIPS_LAND,
        '#TDL #待ち時間 #TDR_now',
        park_key='land',
        cta_index=1,
    )


def _twitter_len(text):
    """Twitter API の weighted character count.

    Twitter text library の仕様: codepoint <= 0x10FF は weight 1,
    それ以外は weight 2（一部例外あり）。
    """
    WEIGHT1_RANGES = [
        (0x0000, 0x10FF),
        (0x2000, 0x200D),
        (0x2010, 0x201F),
        (0x2032, 0x2037),
    ]
    count = 0
    for ch in text:
        cp = ord(ch)
        w = 2
        for lo, hi in WEIGHT1_RANGES:
            if lo <= cp <= hi:
                w = 1
                break
        count += w
    return count


SECTION_HEADERS = ('🌙', '🚀', '⚠️', '📈', '🍱', '⛔')


def _drop_orphaned_headers(lines):
    """直後に詳細行(・/▸)が無い見出しを削除する。"""
    cleaned = []
    for i, line in enumerate(lines):
        if line.startswith(SECTION_HEADERS):
            # 次の非空行が ・ や ▸ で始まらないなら見出しを捨てる
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j >= len(lines) or not lines[j].startswith(('・', '▸')):
                continue
        cleaned.append(line)
    return cleaned


def _trim_tweet(tweet):
    """Twitter weighted count で 280 文字以内に収める

    優先度（残す順）: アトラクション(▸) > 閉園前判定(※) > 閉園前候補(・)
                     > Tips/Weekend > 朝イチ等の見出し
    """
    lines = tweet.split('\n')
    lines = _drop_orphaned_headers(lines)
    # まず Tips/Weekend 行を削除
    while _twitter_len('\n'.join(lines)) > 280 and len(lines) > 5:
        for i, line in enumerate(lines):
            if line.startswith('💡') or line.startswith('🎪'):
                lines.pop(i)
                break
        else:
            break
    # 次に閉園前候補(・)を末尾から削除
    while _twitter_len('\n'.join(lines)) > 280 and len(lines) > 5:
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('・'):
                lines.pop(i)
                break
        else:
            break
    lines = _drop_orphaned_headers(lines)
    # 残り超過分はアトラクション(▸)を末尾から削除（最低でも 2 個は残したい）
    attr_lines = [i for i, l in enumerate(lines) if l.startswith('▸')]
    while _twitter_len('\n'.join(lines)) > 280 and len(attr_lines) > 2:
        idx = attr_lines.pop()
        lines.pop(idx)
        attr_lines = [i for i, l in enumerate(lines) if l.startswith('▸')]
    # それでも超えるならその他の補足見出しから削る
    while _twitter_len('\n'.join(lines)) > 280 and len(lines) > 4:
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith(SECTION_HEADERS):
                lines.pop(i)
                break
        else:
            break
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='X自動投稿スクリプト - エンゲージメント最適化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python daily_x_post.py --post
  python daily_x_post.py --date 2026-04-15 --post
  python daily_x_post.py --date 2026-04-15 --dry-run
  python daily_x_post.py --post --sea-only
        """
    )

    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    parser.add_argument('--date', '-d', type=str, default=tomorrow,
                       help=f'予測日 (デフォルト: {tomorrow})')
    parser.add_argument('--post', '-p', action='store_true',
                       help='Xに投稿する')
    parser.add_argument('--dry-run', action='store_true',
                       help='投稿せずにツイート内容を表示')
    parser.add_argument('--sea-only', action='store_true',
                       help='シーのみ投稿')
    parser.add_argument('--land-only', action='store_true',
                       help='ランドのみ投稿')
    parser.add_argument('--output', '-o', type=str, default='predictions_x',
                       help='出力ディレクトリ (デフォルト: predictions_x)')

    args = parser.parse_args()
    date = args.date
    output_dir = args.output

    print("=" * 60)
    print("🎢 TDR AI待ち時間予測 - X自動投稿")
    print("   （エンゲージメント最適化版）")
    print("=" * 60)
    print(f"📅 予測日: {date}")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.post and not args.dry_run:
        if not check_xharness():
            print("❌ 投稿先への接続に失敗しました。設定を確認してください。")
            return 1

    sea_image = None
    land_image = None

    if not args.land_only:
        print("\n🌊 ディズニーシー ヒートマップ生成中...")
        sea_image = generate_sea_heatmap(date, output_dir)

    if not args.sea_only:
        print("\n🏰 ディズニーランド ヒートマップ生成中...")
        land_image = generate_land_heatmap(date, output_dir)

    sea_tweet = create_sea_tweet(date) if not args.land_only else None
    land_tweet = create_land_tweet(date) if not args.sea_only else None

    if sea_tweet:
        print("\n" + "=" * 60)
        print("🌊 【ディズニーシー】ツイート内容:")
        print("-" * 60)
        print(sea_tweet)
        print("-" * 60)
        print(f"📊 文字数: {_twitter_len(sea_tweet)}/280")
        if sea_image:
            print(f"🖼️  画像: {sea_image}")

    if land_tweet:
        print("\n" + "=" * 60)
        print("🏰 【ディズニーランド】ツイート内容:")
        print("-" * 60)
        print(land_tweet)
        print("-" * 60)
        print(f"📊 文字数: {_twitter_len(land_tweet)}/280")
        if land_image:
            print(f"🖼️  画像: {land_image}")

    if args.post and not args.dry_run:
        posted_count = 0

        if sea_tweet and sea_image:
            print("\n🌊 ディズニーシーを投稿中...")
            if post_to_twitter(sea_tweet, [sea_image]):
                posted_count += 1
            time.sleep(5)

        if land_tweet and land_image:
            print("\n🏰 ディズニーランドを投稿中...")
            if post_to_twitter(land_tweet, [land_image]):
                posted_count += 1

        print(f"\n✅ {posted_count}件の投稿が完了しました")

    elif args.dry_run:
        total = (1 if sea_tweet else 0) + (1 if land_tweet else 0)
        print(f"\n🔍 ドライラン: {total}件の投稿がスキップされました")
    else:
        print("\n💡 投稿するには --post オプションを追加してください")

    print("\n📁 生成ファイル:")
    if sea_image:
        print(f"   🌊 シー: {sea_image}")
    if land_image:
        print(f"   🏰 ランド: {land_image}")

    print("\n✅ 完了!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
