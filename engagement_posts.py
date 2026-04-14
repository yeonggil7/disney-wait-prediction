#!/usr/bin/env python3
"""
フォロワー獲得用エンゲージメント投稿生成・投稿スクリプト

予測ヒートマップ投稿とは別に、フォロワー増加を加速するための
豆知識・トレンド便乗・アンケート型投稿を自動生成
"""

import os
import sys
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

from post_via_xharness import post_to_twitter, check_connection


# ---------------------------------------------------------------------------
# 投稿テンプレート
# ---------------------------------------------------------------------------

TRIVIA_POSTS = [
    (
        "🎢 ディズニー豆知識\n\n"
        "ソアリンの待ち時間が一番短いのは実は「閉園1時間前」って知ってた？\n\n"
        "朝イチは120分超えも珍しくないけど、19時以降は40分以下になることも🌙\n\n"
        "AIの予測データでも毎日この傾向が出てます📊\n\n"
        "他にも穴場情報知りたい人はフォロー✅\n\n"
        "#ディズニーシー #ソアリン #TDR_now #ディズニー好きと繋がりたい"
    ),
    (
        "🏰 ディズニー豆知識\n\n"
        "美女と野獣の城は「開園ダッシュ」組が集中するから\n"
        "実は10:30〜11:00に一瞬空くことがあるんです👀\n\n"
        "朝イチ組が乗り終わった後、次の波が来るまでの隙間！\n\n"
        "毎日のAI予測で最適な時間帯をチェック📱\n\n"
        "#ディズニーランド #美女と野獣 #TDR_now #ディズニー好きと繋がりたい"
    ),
    (
        "📊 AI混雑予測の裏話\n\n"
        "実は「天気予報が雨→晴れに変わった日」が一番混むんです😱\n\n"
        "理由：雨予報で諦めてた人が急に来るから\n\n"
        "逆に「晴れ→雨」に変わった日は穴場！\n\n"
        "AIはこういう天気変化も学習してます🤖\n\n"
        "#ディズニー #TDR #混雑予測 #ディズニー好きと繋がりたい"
    ),
    (
        "🎢 知ってた？\n\n"
        "ディズニーの待ち時間、曜日別だと\n"
        "📈 一番混む：土曜日\n"
        "📉 一番空く：火・水曜日\n\n"
        "でも祝日や連休が絡むと話は変わります\n"
        "だからAIで毎日予測してるんです📊\n\n"
        "明日の予測は毎晩20時にポスト！\n"
        "フォロー✅で見逃さない！\n\n"
        "#TDR #ディズニー #待ち時間 #ディズニー好きと繋がりたい"
    ),
    (
        "🌊 ディズニーシー攻略\n\n"
        "アナとエルサのフローズンジャーニーは\n"
        "パレード・ショーの時間と被ると空く傾向！\n\n"
        "「ビリーヴ！」開始の19:30前後が穴場の可能性📊\n\n"
        "AIの予測データでも時間帯別の傾向が見えます\n\n"
        "毎日の予測はプロフから✅\n\n"
        "#ディズニーシー #アナ雪 #TDS #TDR_now"
    ),
    (
        "💡 ディズニー初心者向け\n\n"
        "「何時に行くのがベスト？」\n\n"
        "結論：開園30分前！🏃\n\n"
        "理由①：最初の1時間で2〜3個乗れる\n"
        "理由②：午前中は全体的に空いてる\n"
        "理由③：昼からの混雑を避けられる\n\n"
        "毎日の混雑予測を見て計画を立てよう📊\n\n"
        "#ディズニー初心者 #TDR #ディズニー好きと繋がりたい"
    ),
    (
        "🤖 このAI予測の精度は？\n\n"
        "過去データと機械学習で翌日の待ち時間を予測しています\n\n"
        "考慮する要素：\n"
        "📅 曜日・祝日\n"
        "🌤 天気・気温\n"
        "🎪 イベント\n"
        "📊 過去の傾向\n\n"
        "精度改善中なのでフィードバック歓迎💬\n\n"
        "#ディズニー #AI #機械学習 #TDR_now"
    ),
    (
        "🎢 パーク選びで迷ったら\n\n"
        "✅ 絶叫系好き → ランド（スペマン・ビッグサンダー）\n"
        "✅ 世界観重視 → シー（アナ雪・ラプンツェル）\n"
        "✅ 小さい子連れ → ランド（プーさん・バズ）\n"
        "✅ 大人デート → シー（ソアリン・タワテラ）\n\n"
        "どっちも毎日AI予測してます📊\n\n"
        "#TDR #ディズニー好きと繋がりたい #ディズニーデート"
    ),
]

SEASONAL_POSTS = {
    4: [
        (
            "🌸 春ディズニーの持ち物チェック\n\n"
            "☑️ 薄手の上着（夜は冷える！）\n"
            "☑️ 日焼け止め\n"
            "☑️ 折りたたみ傘（春の天気は変わりやすい）\n"
            "☑️ モバイルバッテリー\n"
            "☑️ レジャーシート（パレード用）\n\n"
            "準備万端で楽しもう！\n"
            "毎日の混雑予測もチェック📊\n\n"
            "#ディズニー #TDR #春ディズニー #ディズニー好きと繋がりたい"
        ),
        (
            "🌊 TDS 25周年 スパークリング・ジュビリー開催中！🎉\n\n"
            "25周年の特別な期間、混雑傾向も変わります\n\n"
            "AIが毎日の待ち時間を予測して\n"
            "効率よく回るお手伝いをします📊\n\n"
            "フォロー✅で毎晩20時に予測をお届け！\n\n"
            "#TDS25周年 #スパークリングジュビリー #ディズニーシー #TDR_now"
        ),
    ],
    5: [
        (
            "🎏 GW ディズニー攻略\n\n"
            "GWは年間最大級の混雑！\n\n"
            "対策：\n"
            "① 開園30分前には到着\n"
            "② 人気アトラクは朝イチor閉園前\n"
            "③ ランチは11時前に\n"
            "④ AIの予測で空き時間帯を狙う📊\n\n"
            "GWの予測は毎晩チェック✅\n\n"
            "#GWディズニー #TDR #ディズニー好きと繋がりたい"
        ),
    ],
}


def select_post():
    """今日投稿する内容を選択"""
    month = datetime.now().month
    day_of_year = datetime.now().timetuple().tm_yday

    candidates = list(TRIVIA_POSTS)

    if month in SEASONAL_POSTS:
        candidates.extend(SEASONAL_POSTS[month])

    random.seed(day_of_year)
    return random.choice(candidates)


def main():
    parser = argparse.ArgumentParser(description='エンゲージメント投稿')
    parser.add_argument('--post', action='store_true', help='実際に投稿する')
    parser.add_argument('--dry-run', action='store_true', help='プレビューのみ')
    parser.add_argument('--index', type=int, help='特定の投稿インデックスを指定')
    args = parser.parse_args()

    print("=" * 60)
    print("📣 エンゲージメント投稿")
    print("=" * 60)

    if args.index is not None:
        all_posts = list(TRIVIA_POSTS)
        month = datetime.now().month
        if month in SEASONAL_POSTS:
            all_posts.extend(SEASONAL_POSTS[month])
        if 0 <= args.index < len(all_posts):
            tweet = all_posts[args.index]
        else:
            print(f"❌ インデックスは 0〜{len(all_posts)-1} の範囲で指定してください")
            return 1
    else:
        tweet = select_post()

    print(tweet)
    print("-" * 60)
    print(f"📊 文字数: {len(tweet)}/280")

    if args.post and not args.dry_run:
        if not check_connection():
            print("❌ 接続に失敗しました")
            return 1
        print("\n📤 投稿中...")
        if post_to_twitter(tweet):
            print("✅ 投稿完了！")
        else:
            print("❌ 投稿失敗")
            return 1
    else:
        print("\n💡 --post で実際に投稿できます")

    return 0


if __name__ == "__main__":
    sys.exit(main())
