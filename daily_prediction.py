#!/usr/bin/env python3
"""
毎日自動実行される予測スクリプト
- 当日の予測を両パークで実行
- PDF/レポートを生成
- X（Twitter）に投稿（オプション）
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# プロジェクトのルートディレクトリ
PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass  # python-dotenvがない場合は環境変数のみ使用

# X投稿機能（tweepyがインストールされている場合）
try:
    import tweepy
    HAS_TWEEPY = True
except ImportError:
    HAS_TWEEPY = False

# 環境変数からTwitter API認証情報を取得
TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY', '')
TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET', '')
TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN', '')


def run_prediction(park: str, date: str, output_dir: str) -> bool:
    """
    予測を実行
    
    Args:
        park: 'sea' または 'land'
        date: 日付 (YYYY-MM-DD)
        output_dir: 出力ディレクトリ
    
    Returns:
        bool: 成功したかどうか
    """
    if park == 'sea':
        script = 'disneysea_predict_cli.py'
    else:
        script = 'disneyland_predict_cli.py'
    
    cmd = [
        sys.executable,
        str(PROJECT_DIR / script),
        '--date', date,
        '--output', output_dir
    ]
    
    print(f"🔮 {park.upper()} 予測実行中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {park.upper()} 予測完了")
        return True
    else:
        print(f"❌ {park.upper()} 予測失敗: {result.stderr}")
        return False


def get_prediction_summary(park: str, date: str, output_dir: str) -> dict:
    """
    予測レポートからサマリーを抽出
    """
    report_file = PROJECT_DIR / output_dir / date / f"prediction_report_{date}.txt"
    
    if not report_file.exists():
        return None
    
    summary = {
        'park': 'ディズニーシー' if park == 'sea' else 'ディズニーランド',
        'date': date,
        'top_attractions': [],
        'best_hours': [],
        'worst_hours': []
    }
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # トップアトラクションを抽出
    lines = content.split('\n')
    in_ranking = False
    count = 0
    
    for line in lines:
        if 'アトラクション別 予測待ち時間ランキング' in line:
            in_ranking = True
            continue
        if in_ranking and '---' in line:
            continue
        if in_ranking and 'アトラクション名' in line:
            continue
        if in_ranking and line.strip() and count < 3:
            parts = line.split()
            if parts and '分' in line:
                name = parts[0]
                # 待ち時間を抽出
                for p in parts:
                    if '分' in p:
                        wait = p.replace('分', '')
                        summary['top_attractions'].append((name, wait))
                        count += 1
                        break
        if '時間帯別' in line:
            in_ranking = False
        
        # 空いている時間帯
        if '空いている時間帯' in line:
            in_best = True
            continue
        if '混雑する時間帯' in line:
            in_best = False
            continue
    
    return summary


def create_tweet_text(sea_summary: dict, land_summary: dict, date: str) -> str:
    """
    ツイート用テキストを生成（両パーク統合版 - 未使用）
    """
    dt = datetime.strptime(date, '%Y-%m-%d')
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[dt.weekday()]
    
    tweet = f"🎢 {dt.month}/{dt.day}({weekday}) TDR待ち時間予測\n\n"
    
    # シー
    tweet += "🌊【シー】\n"
    if sea_summary and sea_summary['top_attractions']:
        for name, wait in sea_summary['top_attractions'][:3]:
            tweet += f"・{name[:6]}: {wait}分\n"
    
    # ランド
    tweet += "\n🏰【ランド】\n"
    if land_summary and land_summary['top_attractions']:
        for name, wait in land_summary['top_attractions'][:3]:
            tweet += f"・{name[:6]}: {wait}分\n"
    
    tweet += "\n⏰ おすすめ: 開園直後 or 19時以降"
    tweet += "\n#TDR #ディズニー #待ち時間"
    
    return tweet


from tdr_event_calendar import get_current_event, get_special_day, get_smart_tips, is_packing_day, create_packing_tweet


def create_park_tweet(park: str, summary: dict, date: str) -> str:
    """
    パーク別のツイートを生成（明日ディズニーに行く人向け・予習スタイル）
    """
    import math
    
    dt = datetime.strptime(date, '%Y-%m-%d')
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[dt.weekday()]
    
    if park == 'sea':
        emoji = "🌊"
        park_name = "ディズニーシー"
        short_name = "シー"
        base_hashtag = "#TDS"
    else:
        emoji = "🏰"
        park_name = "ディズニーランド"
        short_name = "ランド"
        base_hashtag = "#TDL"
    
    # イベント情報
    event = get_current_event(date, park)
    special = get_special_day(date)
    
    # 平均待ち時間を計算
    avg_wait = 60
    if summary and summary['top_attractions']:
        waits = [float(w) for _, w in summary['top_attractions'][:3]]
        avg_wait = sum(waits) / len(waits)
    
    # スマートTips取得
    tips = get_smart_tips(date, park, avg_wait)
    
    # ===== ツイート構築 =====
    # キャッチーな導入
    tweet = f"📢 明日{short_name}行く人！\n"
    tweet += f"🎓 AI予習しとこ👇\n\n"
    
    tweet += f"{emoji} {dt.month}/{dt.day}({weekday}) {park_name}\n"
    
    # イベント情報（初日は大々的に！）
    if event:
        if event['is_first_day']:
            tweet += f"🎉 {event['name']}初日！\n"
        else:
            tweet += f"{event['emoji']} {event['name']}開催中\n"
    
    tweet += "━━━━━━━━━━━━━━\n"
    
    # 混雑度に応じたキャッチ
    if avg_wait >= 100:
        tweet += "😱 覚悟して！激混み予想\n"
    elif avg_wait >= 70:
        tweet += "📈 そこそこ混む予想\n"
    elif avg_wait >= 40:
        tweet += "✨ 狙い目な1日！\n"
    else:
        tweet += "🌟 穴場日の予感！\n"
    
    # 最も混むアトラクション
    if summary and summary['top_attractions']:
        top_name, top_wait = summary['top_attractions'][0]
        top_wait_int = int(math.ceil(float(top_wait) / 10) * 10)
        short_attr = top_name[:6] if len(top_name) > 6 else top_name
        tweet += f"🔥 {short_attr}は{top_wait_int}分待ち\n"
    
    # スマートTip（1つだけ）
    if tips:
        tweet += f"💡 {tips[0]}\n"
    
    tweet += "\n📱 時間別予想は画像で確認↓\n\n"
    
    # ハッシュタグ
    tweet += "※AI予測/閉園時間で並べない場合あり\n"
    if event:
        tweet += f"{base_hashtag} {event['hashtag']}"
    else:
        tweet += f"{base_hashtag} #ディズニー"
    
    return tweet


def create_attraction_tweet(park: str, attraction_name: str, hourly_data: dict, date: str) -> str:
    """
    個別アトラクションのツイートを生成
    
    Args:
        park: 'sea' または 'land'
        attraction_name: アトラクション名
        hourly_data: 時間帯別待ち時間 {'09:00': 60, '10:00': 80, ...}
        date: 日付
    """
    import math
    
    dt = datetime.strptime(date, '%Y-%m-%d')
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[dt.weekday()]
    
    if park == 'sea':
        emoji = "🌊"
        park_short = "TDS"
    else:
        emoji = "🏰"
        park_short = "TDL"
    
    # アトラクション名を短くする
    short_name = attraction_name[:10] if len(attraction_name) > 10 else attraction_name
    
    tweet = f"{emoji} {short_name}\n"
    tweet += f"📅 {dt.month}/{dt.day}({weekday}) 🤖AI予測\n"
    tweet += "━━━━━━━━━━━━\n"
    
    # 全時間帯の待ち時間（9時〜19時）- ラインカット考慮
    display_hours = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', 
                     '15:00', '16:00', '17:00', '18:00', '19:00']
    
    for hour in display_hours:
        if hour in hourly_data:
            wait = hourly_data[hour]
            if wait < 0:
                wait_int = 0
                bar = "休止"
            else:
                wait_int = int(math.ceil(float(wait) / 10) * 10)
                # 待ち時間に応じたバー表示
                if wait_int < 30:
                    bar = "🟢"
                elif wait_int < 60:
                    bar = "🟡"
                elif wait_int < 90:
                    bar = "🟠"
                else:
                    bar = "🔴"
            
            hour_num = int(hour[:2])
            if wait_int > 0:
                tweet += f"{hour_num}時 {bar} {wait_int}分\n"
            else:
                tweet += f"{hour_num}時 ⬜ {bar}\n"
    
    tweet += "━━━━━━━━━━━━\n"
    
    # 最短時間を見つける（19時までのみ対象 - ラインカット考慮）
    valid_waits = {k: v for k, v in hourly_data.items() 
                   if v > 0 and k <= '19:00'}
    if valid_waits:
        best_hour = min(valid_waits, key=valid_waits.get)
        best_wait = int(math.ceil(valid_waits[best_hour] / 10) * 10)
        tweet += f"一番空いてる時間はこちら↓\n"
        tweet += f"▶︎ {best_hour[:2]}時台 約{best_wait}分\n\n"
    
    tweet += f"#{park_short} #{short_name.replace(' ', '')}"
    
    return tweet


# 人気アトラクションリスト（ランダム選択用）
POPULAR_ATTRACTIONS_SEA = [
    "ソアリン",
    "アナとエルサ",  
    "タワーオブテラー",
]

POPULAR_ATTRACTIONS_LAND = [
    "美女と野獣の物語",
    "ベイマックスのハッピーライド",
    "スプラッシュマウンテン",
]


def get_random_attraction(park: str, date: str) -> str:
    """
    日付に基づいてアトラクションをローテーション選択
    3日周期で全アトラクションが順番に登場
    """
    from datetime import datetime
    
    if park == 'sea':
        attractions = POPULAR_ATTRACTIONS_SEA
    else:
        attractions = POPULAR_ATTRACTIONS_LAND
    
    # 日付から通算日数を計算してローテーション
    dt = datetime.strptime(date, '%Y-%m-%d')
    day_of_year = dt.timetuple().tm_yday
    
    # パークによってオフセットを変えて、同じアトラクションが被らないように
    offset = 0 if park == 'sea' else 1
    
    index = (day_of_year + offset) % len(attractions)
    return attractions[index]


def get_attraction_hourly_data(predictions_df, attraction_name: str) -> dict:
    """
    予測データから特定アトラクションの時間帯別データを取得
    """
    df = predictions_df[predictions_df['attraction_name'] == attraction_name]
    if df.empty:
        # 部分一致で探す
        df = predictions_df[predictions_df['attraction_name'].str.contains(attraction_name[:5], na=False)]
    
    if df.empty:
        return {}
    
    hourly = {}
    for _, row in df.iterrows():
        time = row['time']
        wait = row['predicted_wait_time']
        # 時間を正規化（09:15 -> 09:00）
        hour = time[:2] + ":00"
        if hour not in hourly or wait > hourly[hour]:
            hourly[hour] = wait
    
    return hourly


def post_to_twitter(text: str, image_paths: list = None, max_retries: int = 3) -> bool:
    """
    Xに投稿（レート制限時は自動リトライ）
    """
    import time
    
    if not HAS_TWEEPY:
        print("⚠️ tweepyがインストールされていません")
        print("   pip install tweepy でインストールしてください")
        return False
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, 
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        print("⚠️ Twitter API認証情報が設定されていません")
        print("   環境変数を設定してください:")
        print("   - TWITTER_API_KEY")
        print("   - TWITTER_API_SECRET")
        print("   - TWITTER_ACCESS_TOKEN")
        print("   - TWITTER_ACCESS_TOKEN_SECRET")
        return False
    
    # Twitter API v2 クライアント
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    
    # 画像アップロード用のv1.1 API
    auth = None
    api = None
    if image_paths:
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET
        )
        api = tweepy.API(auth)
    
    for attempt in range(max_retries):
        try:
            media_ids = []
            if image_paths and api:
                for path in image_paths[:4]:  # 最大4枚
                    if os.path.exists(path):
                        media = api.media_upload(path)
                        media_ids.append(media.media_id)
            
            if media_ids:
                response = client.create_tweet(text=text, media_ids=media_ids)
            else:
                response = client.create_tweet(text=text)
            
            print(f"✅ Xに投稿しました: {response.data['id']}")
            return True
            
        except tweepy.TooManyRequests as e:
            wait_time = 15 * 60 * (attempt + 1)  # 15分、30分、45分
            print(f"⏳ レート制限中 ({attempt + 1}/{max_retries}) - {wait_time // 60}分後にリトライ...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                print(f"❌ レート制限: {max_retries}回リトライしましたが失敗しました")
                print("   翌日に再試行してください")
                return False
                
        except Exception as e:
            print(f"❌ X投稿エラー: {e}")
            return False
    
    return False


def main():
    """メイン処理"""
    import argparse
    import time
    import pandas as pd
    
    parser = argparse.ArgumentParser(description='毎日の予測実行スクリプト')
    parser.add_argument('--date', '-d', type=str, 
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='予測日 (デフォルト: 今日)')
    parser.add_argument('--post', '-p', action='store_true',
                       help='Xに投稿する')
    parser.add_argument('--dry-run', action='store_true',
                       help='投稿せずにツイート内容を表示')
    parser.add_argument('--sea-only', action='store_true',
                       help='シーのみ投稿')
    parser.add_argument('--land-only', action='store_true',
                       help='ランドのみ投稿')
    parser.add_argument('--attractions', '-a', action='store_true',
                       help='人気アトラクションも個別投稿（各パーク1つをランダム選択）')
    parser.add_argument('--attractions-only', action='store_true',
                       help='人気アトラクションのみ投稿（パーク全体は投稿しない）')
    args = parser.parse_args()
    
    date = args.date
    
    print("=" * 60)
    print(f"🎢 TDR 待ち時間予測 - 自動実行")
    print(f"📅 日付: {date}")
    print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 予測実行
    sea_success = run_prediction('sea', date, 'predictions_sea')
    land_success = run_prediction('land', date, 'predictions_land')
    
    if not (sea_success and land_success):
        print("❌ 予測に失敗しました")
        sys.exit(1)
    
    # サマリー取得
    sea_summary = get_prediction_summary('sea', date, 'predictions_sea')
    land_summary = get_prediction_summary('land', date, 'predictions_land')
    
    # パーク別ツイート作成
    sea_tweet = create_park_tweet('sea', sea_summary, date)
    land_tweet = create_park_tweet('land', land_summary, date)
    
    # ヒートマップ画像のパス
    sea_image = str(PROJECT_DIR / 'predictions_sea' / date / f'prediction_heatmap_{date}.png')
    land_image = str(PROJECT_DIR / 'predictions_land' / date / f'prediction_heatmap_{date}.png')
    
    # CSVから予測データを読み込み（個別アトラクション投稿用）
    sea_csv = PROJECT_DIR / 'predictions_sea' / date / f'prediction_{date}.csv'
    land_csv = PROJECT_DIR / 'predictions_land' / date / f'prediction_{date}.csv'
    
    sea_predictions = pd.read_csv(sea_csv) if sea_csv.exists() else None
    land_predictions = pd.read_csv(land_csv) if land_csv.exists() else None
    
    # 個別アトラクションツイート作成（各パーク1つをランダム選択）
    attraction_tweets = []
    
    if args.attractions or args.attractions_only:
        # シーの人気アトラクション（ランダムに1つ）
        if not args.land_only and sea_predictions is not None:
            attr = get_random_attraction('sea', date)
            hourly = get_attraction_hourly_data(sea_predictions, attr)
            if hourly:
                tweet = create_attraction_tweet('sea', attr, hourly, date)
                attraction_tweets.append(('sea', attr, tweet))
                print(f"🎲 シー: 本日は「{attr}」を投稿")
        
        # ランドの人気アトラクション（ランダムに1つ）
        if not args.sea_only and land_predictions is not None:
            attr = get_random_attraction('land', date)
            hourly = get_attraction_hourly_data(land_predictions, attr)
            if hourly:
                tweet = create_attraction_tweet('land', attr, hourly, date)
                attraction_tweets.append(('land', attr, tweet))
                print(f"🎲 ランド: 本日は「{attr}」を投稿")
    
    # 表示
    if not args.attractions_only:
        print("\n" + "=" * 60)
        print("🌊 【ディズニーシー】ツイート内容:")
        print("-" * 60)
        print(sea_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(sea_tweet)}/280")
        print(f"🖼️  画像: {sea_image}")
        
        print("\n" + "=" * 60)
        print("🏰 【ディズニーランド】ツイート内容:")
        print("-" * 60)
        print(land_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(land_tweet)}/280")
        print(f"🖼️  画像: {land_image}")
    
    # 個別アトラクションツイート表示
    if attraction_tweets:
        print("\n" + "=" * 60)
        print("🎢 【人気アトラクション個別】ツイート内容:")
        for park, attr, tweet in attraction_tweets:
            emoji = "🌊" if park == 'sea' else "🏰"
            print("-" * 60)
            print(f"{emoji} {attr}")
            print("-" * 60)
            print(tweet)
            print(f"📊 文字数: {len(tweet)}/280")
    
    # 持ち物リスト（月曜日のみ）
    packing_tweet = None
    if is_packing_day(date):
        packing_tweet = create_packing_tweet(date)
        print("\n" + "=" * 60)
        print("🎒 【週間持ち物リスト】ツイート内容:")
        print("-" * 60)
        print(packing_tweet)
        print("-" * 60)
        print(f"📊 文字数: {len(packing_tweet)}/280")
    
    # X投稿
    if args.post and not args.dry_run:
        posted_count = 0
        
        # パーク全体の投稿
        if not args.attractions_only:
            # シー投稿
            if not args.land_only:
                print("\n🌊 ディズニーシーを投稿中...")
                if post_to_twitter(sea_tweet, [sea_image]):
                    posted_count += 1
                time.sleep(3)  # API制限対策で少し待機
            
            # ランド投稿
            if not args.sea_only:
                print("\n🏰 ディズニーランドを投稿中...")
                if post_to_twitter(land_tweet, [land_image]):
                    posted_count += 1
                time.sleep(3)
        
        # 個別アトラクション投稿（レート制限対策で60秒間隔）
        if attraction_tweets:
            print("\n🎢 人気アトラクションを投稿中...")
            print("   ⚠️ レート制限対策のため60秒間隔で投稿します")
            for i, (park, attr, tweet) in enumerate(attraction_tweets):
                emoji = "🌊" if park == 'sea' else "🏰"
                print(f"   {emoji} {attr}...")
                if post_to_twitter(tweet):
                    posted_count += 1
                if i < len(attraction_tweets) - 1:  # 最後以外は待機
                    print(f"   ⏳ 次の投稿まで60秒待機...")
                    time.sleep(60)  # API制限対策で60秒待機
        
        # 持ち物リスト投稿（月曜日のみ）
        if packing_tweet:
            print("\n🎒 持ち物リストを投稿中...")
            time.sleep(60)  # 前の投稿から60秒待機
            if post_to_twitter(packing_tweet):
                posted_count += 1
        
        print(f"\n✅ {posted_count}件の投稿が完了しました")
        
    elif args.dry_run:
        total_tweets = (0 if args.attractions_only else 2) + len(attraction_tweets)
        if packing_tweet:
            total_tweets += 1
        print(f"\n🔍 ドライラン: {total_tweets}件の投稿がスキップされました")
    
    # 出力ファイルの場所
    print("\n📁 生成ファイル:")
    print(f"   シー: predictions_sea/{date}/")
    print(f"   ランド: predictions_land/{date}/")
    
    print("\n✅ 完了!")


if __name__ == "__main__":
    main()

