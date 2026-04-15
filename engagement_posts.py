#!/usr/bin/env python3
"""
フォロワー獲得用エンゲージメント投稿 & 分析スクリプト

投稿タイプごとにカテゴリ分けし、エンゲージメント効果を比較可能にする。
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


def _twitter_len(text):
    count = 0
    for ch in text:
        cp = ord(ch)
        if ch == '\n':
            count += 1
        elif (0x1100 <= cp <= 0x115f) or (0x2e80 <= cp <= 0x303e) or \
             (0x3041 <= cp <= 0x33bf) or (0x3400 <= cp <= 0x4dbf) or \
             (0x4e00 <= cp <= 0xa4cf) or (0xac00 <= cp <= 0xd7ff) or \
             (0xfe30 <= cp <= 0xfe4f) or (0xff00 <= cp <= 0xffef) or \
             cp >= 0x1f000:
            count += 2
        else:
            count += 1
    return count


# ---------------------------------------------------------------------------
# 投稿テンプレート（カテゴリ別）
# ---------------------------------------------------------------------------

POSTS = {
    "question": [
        "【質問】ディズニー行くならどっち派？\n\n"
        "🌊 シー → いいね\n"
        "🏰 ランド → RT\n\n"
        "どっちも好きな人はリプで教えて！\n\n"
        "#ディズニー好きと繋がりたい #TDR",

        "【質問】ディズニーで一番好きなアトラクションは？\n\n"
        "リプで教えてください！\n"
        "AI予測で一番混むのはソアリンですが…\n\n"
        "意外なアトラクションが人気だったりする？🤔\n\n"
        "#ディズニー好きと繋がりたい #TDR",

        "【質問】ディズニーに行く頻度は？\n\n"
        "🔥 年パス勢（月1以上）\n"
        "✨ 年2〜3回\n"
        "🎯 年1回の一大イベント\n"
        "😢 しばらく行けてない\n\n"
        "リプで教えて！\n"
        "#ディズニー好きと繋がりたい",

        "ディズニー行くとき最初に何する？\n\n"
        "① 人気アトラクション直行\n"
        "② まずグッズショップ\n"
        "③ 写真撮影スポットへ\n"
        "④ とりあえずポップコーン買う🍿\n\n"
        "リプで教えて！\n"
        "#ディズニー #TDR",
    ],

    "ranking": [
        "【AI分析】春に混むアトラクション TOP5\n\n"
        "1位 ソアリン\n"
        "2位 アナ雪\n"
        "3位 美女と野獣\n"
        "4位 センター・オブ・ジ・アース\n"
        "5位 ラプンツェル\n\n"
        "午前中に乗るのがおすすめ📊\n"
        "#TDR #ディズニー #待ち時間",

        "【AIデータ】空いてる穴場アトラクション\n\n"
        "🟢 レイジングスピリッツ（平均30分）\n"
        "🟢 マジックランプシアター（平均15分）\n"
        "🟢 海底2万マイル（平均20分）\n"
        "🟢 シンドバッド（平均10分）\n\n"
        "穴場を上手に組み合わせると効率UP\n"
        "#TDS #ディズニーシー",
    ],

    "empathy": [
        "ディズニーあるある\n\n"
        "「今日空いてるかな？」って調べてから行くのに\n"
        "結局めっちゃ混んでるやつ\n\n"
        "→ だからAIで前日に予測してます\n"
        "毎日20時に翌日の予測を投稿中📱\n\n"
        "フォローしておけば前日にチェックできます\n"
        "#ディズニーあるある #TDR",

        "ディズニーあるある\n\n"
        "開園ダッシュしたのに既に大行列で\n"
        "「みんな何時から並んでたの…？」ってなるやつ\n\n"
        "AI予測を見て作戦立ててから行くと心に余裕ができます\n\n"
        "#ディズニーあるある #TDR",

        "ディズニーあるある\n\n"
        "「平日なら空いてるでしょ」と思って行ったら\n"
        "修学旅行シーズンで激混みだったやつ\n\n"
        "AIは修学旅行の時期も学習してます📊\n"
        "#ディズニーあるある #TDR",
    ],

    "tips": [
        "【保存推奨】待ち時間を減らす5つのコツ\n\n"
        "1. 開園15分前には入口に並ぶ\n"
        "2. 人気アトラクションは午前中に\n"
        "3. パレード中は穴場タイム\n"
        "4. 18時以降は全体的に空く\n"
        "5. 火・水曜が最も空いている\n\n"
        "AIデータから導き出した攻略法\n"
        "#ディズニー攻略 #TDR",

        "【保存推奨】効率的な回り方\n\n"
        "朝: 人気アトラクション直行\n"
        "10時: 2つ目のアトラクションへ\n"
        "11時: 早めランチ（混雑回避）\n"
        "13時: ショー・パレード鑑賞\n"
        "15時: アトラクション再開\n"
        "18時: 夕食＆夜のショー\n"
        "20時: 夜の空きタイムを活用\n\n"
        "#ディズニー攻略 #TDR",

        "【知らないと損】シーの裏ワザ\n\n"
        "ソアリンは閉園1時間前が穴場\n"
        "朝120分超え→夜40分以下になることも\n\n"
        "AIの予測で毎日確認できます📊\n"
        "#TDS #ディズニーシー #ソアリン",
    ],

    "behind_scenes": [
        "【開発裏話】待ち時間AIの仕組み\n\n"
        "過去の待ち時間データ数万件を機械学習\n"
        "天気・曜日・イベント・祝日を考慮\n\n"
        "精度は平均誤差30分以内まで改善中\n\n"
        "「こんな機能欲しい」があればリプで🙏\n"
        "#AI #機械学習 #ディズニー",

        "AI開発者のぼやき\n\n"
        "待ち時間予測で一番難しいのは\n"
        "「突発的な機材トラブル」の予測\n\n"
        "止まった瞬間に他のアトラクションも\n"
        "連鎖的に混むので予測精度が下がる\n\n"
        "ここは改善中です…🔧\n"
        "#AI開発 #ディズニー",

        "AIの改良レポート\n\n"
        "先月と今月で予測精度を比較\n"
        "シー: 誤差45分→31分に改善\n"
        "ランド: 誤差31分→27分に改善\n\n"
        "前週の実績データを特徴量に追加したのが効いた\n\n"
        "精度上がったら「いいね」で応援してくれると嬉しい\n"
        "#AI #機械学習",
    ],

    "comparison": [
        "【比較】平日と週末、どれくらい違う？\n\n"
        "🟢 平日（火水）ソアリン → 平均60分\n"
        "🔴 週末（土日）ソアリン → 平均120分\n\n"
        "約2倍の差！\n"
        "有給取ってでも行く価値あり\n"
        "#ディズニー #待ち時間 #TDS",

        "【比較】天気と混雑の関係\n\n"
        "☀️ 晴れの日 → 混雑度100%\n"
        "☁️ 曇りの日 → 混雑度85%\n"
        "🌧 雨の日  → 混雑度60%\n\n"
        "雨ディズニーは実は穴場\n"
        "屋内アトラクションを攻めるのがコツ\n"
        "#ディズニー #TDR",

        "【比較】朝vs昼vs夜の待ち時間\n\n"
        "🌅 9時台: 平均40分（空いてる！）\n"
        "☀️ 13時台: 平均90分（ピーク）\n"
        "🌙 20時台: 平均30分（穴場！）\n\n"
        "朝と夜に人気アトラクを集中させるのが攻略法\n"
        "#ディズニー攻略 #TDR",
    ],

    "interactive": [
        "明日ディズニー行く人🙋\n\n"
        "リプで「シー」か「ランド」か教えて！\n"
        "AIが混雑予測をお届けします📊\n\n"
        "毎日20時に翌日予測を投稿中\n"
        "フォローしておくと便利🎢\n\n"
        "#ディズニー #TDR #TDS #TDL",

        "今週末ディズニー行く予定の人🙋\n\n"
        "いいねで教えて！\n"
        "週末の混雑予測、金曜の夜に投稿します\n\n"
        "#ディズニー #TDR",

        "あなたのディズニーの思い出を教えて！\n\n"
        "最近行った人はリプで感想聞かせてください\n"
        "混み具合はどうでした？\n\n"
        "AIの予測精度向上の参考にします📊\n"
        "#ディズニー好きと繋がりたい",
    ],

    "seasonal_spring": [
        "【4月のTDS】25周年で特別な春！\n\n"
        "スパークリング・ジュビリーで連日大混雑\n"
        "ソアリンは午前中180分超えも\n\n"
        "攻略のカギは午前はソアリン、午後はマーメイドラグーン\n\n"
        "詳細予測は毎晩20時に投稿📊\n"
        "#TDS25周年 #ディズニーシー",

        "🌸 春ディズニーの持ち物チェック\n\n"
        "薄手の上着（夜は冷える）\n"
        "日焼け止め\n"
        "折りたたみ傘\n"
        "モバイルバッテリー\n"
        "レジャーシート\n\n"
        "準備万端で楽しもう！\n"
        "#ディズニー #TDR #春ディズニー",
    ],

    "quiz": [
        "【クイズ】TDSで一番待ち時間が短いのは何曜日？\n\n"
        "答えは…火曜日！\n\n"
        "AIの分析では火曜は土曜の約半分\n"
        "計画的に行くだけで待ち時間が大幅に変わる\n\n"
        "曜日別データ気になる方はフォロー🔔\n"
        "#ディズニー豆知識 #TDS",

        "【クイズ】一番空いてる時間帯は？\n\n"
        "A. 9時台\n"
        "B. 12時台\n"
        "C. 15時台\n"
        "D. 20時台\n\n"
        "正解は…Dの20時台！\n"
        "閉園前は平均待ち時間が半分以下に\n\n"
        "#ディズニー豆知識 #TDR",
    ],
}


def select_post(category=None):
    """投稿を選択。カテゴリ指定可。"""
    if category and category in POSTS:
        pool = POSTS[category]
    else:
        pool = []
        for cat_posts in POSTS.values():
            pool.extend(cat_posts)

    seed = datetime.now().timetuple().tm_yday * 100 + datetime.now().hour
    random.seed(seed)
    return random.choice(pool)


def analyze_engagement():
    """最近の投稿のエンゲージメントを分析"""
    try:
        import tweepy
    except ImportError:
        print("tweepy が必要です")
        return

    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
    )

    me = client.get_me(user_auth=True, user_fields=['public_metrics'])
    pm = me.data.public_metrics
    print(f"=== @{me.data.username} ===")
    print(f"Followers: {pm['followers_count']} | Following: {pm['following_count']} | Tweets: {pm['tweet_count']}")
    print()

    tweets = client.get_users_tweets(
        me.data.id, max_results=30, user_auth=True,
        tweet_fields=['created_at', 'text', 'public_metrics', 'attachments'],
    )

    img_tweets = []
    txt_tweets = []

    for t in tweets.data:
        m = t.public_metrics
        imp = m.get('impression_count', 0)
        eng = m.get('like_count', 0) + m.get('retweet_count', 0) + m.get('reply_count', 0)
        rate = eng / imp * 100 if imp > 0 else 0
        entry = {
            'id': t.id,
            'text': t.text[:60].replace('\n', ' '),
            'imp': imp,
            'likes': m.get('like_count', 0),
            'rts': m.get('retweet_count', 0),
            'replies': m.get('reply_count', 0),
            'eng_rate': rate,
            'has_img': bool(t.attachments),
            'created': str(t.created_at),
        }
        if t.attachments:
            img_tweets.append(entry)
        else:
            txt_tweets.append(entry)

    print("=== Text Posts (by engagement rate) ===")
    for t in sorted(txt_tweets, key=lambda x: x['eng_rate'], reverse=True):
        print(f"  imp={t['imp']:>4} like={t['likes']} rt={t['rts']} reply={t['replies']} eng={t['eng_rate']:.1f}% | {t['text']}")

    print()
    print("=== Image Posts (by engagement rate) ===")
    for t in sorted(img_tweets, key=lambda x: x['eng_rate'], reverse=True):
        print(f"  imp={t['imp']:>4} like={t['likes']} rt={t['rts']} reply={t['replies']} eng={t['eng_rate']:.1f}% | {t['text']}")

    print()
    avg_txt_imp = sum(t['imp'] for t in txt_tweets) / len(txt_tweets) if txt_tweets else 0
    avg_img_imp = sum(t['imp'] for t in img_tweets) / len(img_tweets) if img_tweets else 0
    avg_txt_eng = sum(t['eng_rate'] for t in txt_tweets) / len(txt_tweets) if txt_tweets else 0
    avg_img_eng = sum(t['eng_rate'] for t in img_tweets) / len(img_tweets) if img_tweets else 0

    print(f"--- Summary ---")
    print(f"Text posts ({len(txt_tweets)}): avg imp={avg_txt_imp:.0f}, avg eng={avg_txt_eng:.2f}%")
    print(f"Image posts ({len(img_tweets)}): avg imp={avg_img_imp:.0f}, avg eng={avg_img_eng:.2f}%")


def main():
    parser = argparse.ArgumentParser(description='エンゲージメント投稿 & 分析')
    parser.add_argument('--post', action='store_true', help='投稿する')
    parser.add_argument('--dry-run', action='store_true', help='プレビューのみ')
    parser.add_argument('--category', '-c', type=str, help=f'カテゴリ: {", ".join(POSTS.keys())}')
    parser.add_argument('--analyze', '-a', action='store_true', help='エンゲージメント分析')
    parser.add_argument('--list', '-l', action='store_true', help='全カテゴリと投稿数を表示')
    args = parser.parse_args()

    if args.analyze:
        analyze_engagement()
        return 0

    if args.list:
        print("=== 投稿カテゴリ ===")
        total = 0
        for cat, posts in POSTS.items():
            valid = [p for p in posts if _twitter_len(p) <= 280]
            over = len(posts) - len(valid)
            print(f"  {cat}: {len(posts)} posts" + (f" ({over} over limit)" if over else ""))
            total += len(posts)
        print(f"\n  Total: {total} posts")
        return 0

    tweet = select_post(args.category)

    print("=" * 60)
    print(f"📣 エンゲージメント投稿")
    print("=" * 60)
    print(tweet)
    print("-" * 60)
    tlen = _twitter_len(tweet)
    print(f"📊 文字数: {tlen}/280 {'⚠️ OVER!' if tlen > 280 else 'OK'}")

    if args.post and not args.dry_run:
        if tlen > 280:
            print("❌ 文字数オーバーのため投稿できません")
            return 1
        if not check_connection():
            print("❌ 接続に失敗")
            return 1
        print("\n📤 投稿中...")
        if post_to_twitter(tweet):
            print("✅ 投稿完了！")
        else:
            print("❌ 投稿失敗")
            return 1
    else:
        print("\n💡 --post で投稿、--analyze で分析")

    return 0


if __name__ == "__main__":
    sys.exit(main())
