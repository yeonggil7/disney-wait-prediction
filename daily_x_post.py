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

# ---------------------------------------------------------------------------
# 予測データ解析
# ---------------------------------------------------------------------------

def _get_prediction_insights(date_str, park='sea'):
    """予測データからインサイトを抽出"""
    try:
        if park == 'sea':
            from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
            predictor = DisneySeaWaitTimePredictorV3()
            targets = SEA_TARGET_ATTRACTIONS
            display = SEA_DISPLAY_NAMES
            closures = get_sea_closures(date_str)
        else:
            from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
            predictor = DisneyLandWaitTimePredictorV3()
            targets = LAND_TARGET_ATTRACTIONS
            display = LAND_DISPLAY_NAMES
            closures = get_land_closures(date_str)

        attractions = [a for a in targets if a not in closures]
        time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]
        predictions = predictor.predict(date=date_str, time_slots=time_slots, attractions=attractions)

        if predictions is None:
            return None

        insights = {}

        # 最混雑アトラクション（日平均）
        avg_by_attr = predictions.groupby('attraction_name')['predicted_wait_time'].mean()
        busiest_attr = avg_by_attr.idxmax()
        insights['busiest_name'] = display.get(busiest_attr, busiest_attr)[:8]
        insights['busiest_wait'] = int(avg_by_attr.max())

        # 穴場アトラクション（日平均最短）
        calmest_attr = avg_by_attr.idxmin()
        insights['calmest_name'] = display.get(calmest_attr, calmest_attr)[:8]
        insights['calmest_wait'] = int(avg_by_attr.min())

        # ピーク時間帯
        avg_by_time = predictions.groupby('time')['predicted_wait_time'].mean()
        peak_time = avg_by_time.idxmax()
        insights['peak_time'] = peak_time
        insights['peak_wait'] = int(avg_by_time.max())

        # 空いてる時間帯
        calm_time = avg_by_time.idxmin()
        insights['calm_time'] = calm_time
        insights['calm_wait'] = int(avg_by_time.min())

        # 全体平均
        insights['avg_wait'] = int(predictions['predicted_wait_time'].mean())

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
    "明日行く方はいいね❤️で教えてね！",
    "保存して当日活用してください📌",
    "参考になったらRT🔄お願いします！",
    "スクショ📱して当日の計画に役立ててね！",
    "どのアトラクション気になる？リプで教えて💬",
    "フォロー✅で毎日予測をお届け！",
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


def create_sea_tweet(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = _get_weekday_ja(date_str)
    closures = get_sea_closures(date_str)
    closed_count = len(closures)
    open_count = len(SEA_TARGET_ATTRACTIONS) - closed_count

    insights = _get_prediction_insights(date_str, 'sea')

    tweet = f"🌊 ディズニーシー AI待ち時間予測\n"
    tweet += f"📅 {dt.month}/{dt.day}({day_name})"

    if insights:
        tweet += f" {insights['congestion_emoji']}{insights['congestion']}予想\n\n"
        tweet += f"🎢 人気{open_count}アトラクション終日予測\n"
        tweet += f"⏱ 平均待ち{insights['avg_wait']}分\n"
        tweet += f"🔥 最混雑: {insights['busiest_name']} 平均{insights['busiest_wait']}分\n"
        tweet += f"✨ 穴場: {insights['calmest_name']} 平均{insights['calmest_wait']}分\n"
        tweet += f"⏰ 空き時間帯: {insights['calm_time']}〜\n"
    else:
        tweet += f"\n\n🎢 人気{open_count}アトラクション終日予測\n"

    if closed_count > 0:
        closed_names = [SEA_DISPLAY_NAMES.get(a, a)[:6] for a in closures.keys()]
        tweet += f"❌ 休止: {', '.join(closed_names)}\n"

    tweet += "\n"

    tip = random.choice(TIPS_SEA)
    tweet += f"{tip}\n\n"

    if _is_weekend(date_str):
        tweet += f"{random.choice(WEEKEND_EXTRAS)}\n\n"

    tweet += random.choice(CTA_VARIATIONS) + "\n\n"
    tweet += "#TDS #ディズニーシー #待ち時間 #TDR_now #ディズニー好きと繋がりたい"

    if len(tweet) > 280:
        tweet = _trim_tweet(tweet)

    return tweet


def create_land_tweet(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = _get_weekday_ja(date_str)
    closures = get_land_closures(date_str)
    closed_count = len(closures)
    open_count = len(LAND_TARGET_ATTRACTIONS) - closed_count

    insights = _get_prediction_insights(date_str, 'land')

    tweet = f"🏰 ディズニーランド AI待ち時間予測\n"
    tweet += f"📅 {dt.month}/{dt.day}({day_name})"

    if insights:
        tweet += f" {insights['congestion_emoji']}{insights['congestion']}予想\n\n"
        tweet += f"🎢 人気{open_count}アトラクション終日予測\n"
        tweet += f"⏱ 平均待ち{insights['avg_wait']}分\n"
        tweet += f"🔥 最混雑: {insights['busiest_name']} 平均{insights['busiest_wait']}分\n"
        tweet += f"✨ 穴場: {insights['calmest_name']} 平均{insights['calmest_wait']}分\n"
        tweet += f"⏰ 空き時間帯: {insights['calm_time']}〜\n"
    else:
        tweet += f"\n\n🎢 人気{open_count}アトラクション終日予測\n"

    if closed_count > 0:
        closed_names = [LAND_DISPLAY_NAMES.get(a, a)[:6] for a in closures.keys()]
        tweet += f"❌ 休止: {', '.join(closed_names)}\n"

    tweet += "\n"

    tip = random.choice(TIPS_LAND)
    tweet += f"{tip}\n\n"

    if _is_weekend(date_str):
        tweet += f"{random.choice(WEEKEND_EXTRAS)}\n\n"

    tweet += random.choice(CTA_VARIATIONS) + "\n\n"
    tweet += "#TDL #ディズニーランド #待ち時間 #TDR_now #ディズニー好きと繋がりたい"

    if len(tweet) > 280:
        tweet = _trim_tweet(tweet)

    return tweet


def _trim_tweet(tweet):
    """280文字以内に収める"""
    lines = tweet.split('\n')
    while len('\n'.join(lines)) > 280 and len(lines) > 5:
        for i, line in enumerate(lines):
            if line.startswith('💡') or line.startswith('🎪'):
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
        print(f"📊 文字数: {len(sea_tweet)}/280")
        if sea_image:
            print(f"🖼️  画像: {sea_image}")

    if land_tweet:
        print("\n" + "=" * 60)
        print("🏰 【ディズニーランド】ツイート内容:")
        print("-" * 60)
        print(land_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(land_tweet)}/280")
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
