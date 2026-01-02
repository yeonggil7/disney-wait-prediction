#!/usr/bin/env python3
"""
東京ディズニーリゾート イベントカレンダー
公式サイトの年間スケジュールに基づく
"""

from datetime import datetime, date
from typing import Optional, Tuple, List

# 2025-2026年のイベントスケジュール
TDR_EVENTS = {
    # ランド
    'land': [
        {
            'name': 'ディズニー・クリスマス',
            'start': (11, 8),
            'end': (12, 25),
            'emoji': '🎄',
            'hashtag': '#ディズニークリスマス',
            'highlight': 'エレクトリカルパレードがクリスマスver.に！',
        },
        {
            'name': 'お正月プログラム',
            'start': (1, 1),
            'end': (1, 13),
            'emoji': '🎍',
            'hashtag': '#ディズニー正月',
            'highlight': '和装ミッキーに会える！',
        },
        {
            'name': 'ディズニー・パルパルーザ',
            'start': (1, 15),
            'end': (3, 31),
            'emoji': '🎪',
            'hashtag': '#パルパルーザ',
            'highlight': 'ドナルドvsチップとデールのお祭り騒ぎ！',
        },
        {
            'name': 'ディズニー・イースター',
            'start': (4, 1),
            'end': (6, 30),
            'emoji': '🐰',
            'hashtag': '#ディズニーイースター',
            'highlight': 'うさたまが大暴走！',
        },
        {
            'name': 'ディズニー・サマーフェスティバル',
            'start': (7, 1),
            'end': (8, 31),
            'emoji': '🌴',
            'hashtag': '#ディズニー夏',
            'highlight': '水しぶき全開のびしょ濡れパレード！',
        },
        {
            'name': 'ディズニー・ハロウィーン',
            'start': (9, 10),
            'end': (10, 31),
            'emoji': '🎃',
            'hashtag': '#ディズニーハロウィン',
            'highlight': 'フル仮装でインパできる！',
        },
    ],
    # シー
    'sea': [
        {
            'name': 'ディズニー・クリスマス',
            'start': (11, 8),
            'end': (12, 25),
            'emoji': '🎄',
            'hashtag': '#ディズニークリスマス',
            'highlight': 'ハーバーショーがクリスマス仕様に！',
        },
        {
            'name': 'お正月プログラム',
            'start': (1, 1),
            'end': (1, 13),
            'emoji': '🎍',
            'hashtag': '#ディズニー正月',
            'highlight': '和装ダッフィーフレンズに会える！',
        },
        {
            'name': 'ダッフィー＆フレンズ',
            'start': (1, 15),
            'end': (3, 19),
            'emoji': '🧸',
            'hashtag': '#ダッフィー',
            'highlight': 'リーナベルの新グッズ要チェック！',
        },
        {
            'name': 'ディズニー・イースター',
            'start': (4, 1),
            'end': (6, 30),
            'emoji': '🐰',
            'hashtag': '#ディズニーイースター',
            'highlight': '春らしいパステルカラーの装飾！',
        },
        {
            'name': 'ディズニー・サマーフェスティバル',
            'start': (7, 1),
            'end': (8, 31),
            'emoji': '🌴',
            'hashtag': '#ディズニー夏',
            'highlight': 'ハーバーで水かけ祭り！',
        },
        {
            'name': 'ディズニー・ハロウィーン',
            'start': (9, 10),
            'end': (10, 31),
            'emoji': '🎃',
            'hashtag': '#ディズニーハロウィン',
            'highlight': 'ヴィランズが主役に！',
        },
    ],
}

# 特別な日
SPECIAL_DAYS = {
    (2, 14): ('バレンタインデー', '💕', 'カップルで激混み注意！'),
    (3, 14): ('ホワイトデー', '🤍', 'お返しディズニーが人気！'),
    (10, 31): ('ハロウィン当日', '👻', '仮装ゲストで大盛り上がり！'),
    (12, 24): ('クリスマスイブ', '🎅', '年間最混雑日の一つ！'),
    (12, 25): ('クリスマス', '🎄', 'ラストクリスマス、激混み！'),
    (12, 31): ('大晦日', '🎆', 'カウントダウン！特別な夜！'),
    (1, 1): ('元日', '🌅', '新年ディズニー！限定グッズ争奪戦！'),
}


def get_current_event(target_date: str, park: str) -> Optional[dict]:
    """
    指定日に開催中のイベントを取得
    
    Returns:
        dict: {name, emoji, hashtag, highlight, is_first_day, days_until_end}
    """
    dt = datetime.strptime(target_date, '%Y-%m-%d')
    month, day = dt.month, dt.day
    
    events = TDR_EVENTS.get(park, [])
    
    for event in events:
        start_month, start_day = event['start']
        end_month, end_day = event['end']
        
        # 年をまたぐイベント対応
        start_date = date(dt.year, start_month, start_day)
        if end_month < start_month:  # 年をまたぐ
            if month >= start_month:
                end_date = date(dt.year + 1, end_month, end_day)
            else:
                start_date = date(dt.year - 1, start_month, start_day)
                end_date = date(dt.year, end_month, end_day)
        else:
            end_date = date(dt.year, end_month, end_day)
        
        current = date(dt.year, month, day)
        
        if start_date <= current <= end_date:
            is_first_day = (current == start_date)
            days_until_end = (end_date - current).days
            
            return {
                'name': event['name'],
                'emoji': event['emoji'],
                'hashtag': event['hashtag'],
                'highlight': event['highlight'],
                'is_first_day': is_first_day,
                'days_until_end': days_until_end,
            }
    
    return None


def get_special_day(target_date: str) -> Optional[dict]:
    """特別な日かどうかをチェック"""
    dt = datetime.strptime(target_date, '%Y-%m-%d')
    key = (dt.month, dt.day)
    
    if key in SPECIAL_DAYS:
        name, emoji, comment = SPECIAL_DAYS[key]
        return {
            'name': name,
            'emoji': emoji,
            'comment': comment,
        }
    
    return None


def get_smart_tips(target_date: str, park: str, avg_wait: float) -> List[str]:
    """
    日付と混雑度に応じた賢いTipsを生成
    """
    dt = datetime.strptime(target_date, '%Y-%m-%d')
    weekday = dt.weekday()
    month, day = dt.month, dt.day
    
    tips = []
    
    # 曜日別Tips
    if weekday == 0:  # 月曜
        tips.append("月曜は穴場！週末の疲れでゲスト少なめ")
    elif weekday == 4:  # 金曜
        tips.append("金曜夜は空く傾向あり！仕事終わりにどうぞ")
    elif weekday >= 5:  # 土日
        tips.append("土日は開園1時間前には到着を！")
    
    # 季節別Tips
    if month in [7, 8]:
        tips.append("暑さ対策必須！休憩を多めに")
        tips.append("屋内アトラクションが狙い目")
    elif month in [12, 1, 2]:
        tips.append("防寒対策をしっかり！夜は極寒")
    
    # 混雑度別Tips
    if avg_wait >= 100:
        tips.append("プレミアアクセス活用がおすすめ")
        tips.append("ショー・パレード場所取りは1時間前から")
    elif avg_wait >= 60:
        tips.append("人気アトラクションは午前中に！")
        tips.append("レストラン予約が取れればラッキー")
    else:
        tips.append("今日はスタンバイで回れそう！")
        tips.append("ゆっくりグリーティングも楽しめる")
    
    # パーク別Tips
    if park == 'sea':
        tips.append("ソアリンはDPA即売り切れ注意")
    else:
        tips.append("美女と野獣はDPA朝イチで確保を")
    
    return tips[:3]  # 最大3つ


# 季節別持ち物リスト
PACKING_LISTS = {
    'spring': {  # 3-5月
        'title': '春ディズニーの持ち物',
        'emoji': '🌸',
        'items': [
            '☑️ 薄手の上着（朝晩は冷える）',
            '☑️ 折りたたみ傘（春雨対策）',
            '☑️ 花粉症の薬',
            '☑️ モバイルバッテリー',
            '☑️ レジャーシート',
        ],
        'tip': '気温差が激しい季節！重ね着がおすすめ',
    },
    'summer': {  # 6-8月
        'title': '夏ディズニーの持ち物',
        'emoji': '🌴',
        'items': [
            '☑️ 日焼け止め（こまめに塗り直し）',
            '☑️ 帽子・サングラス',
            '☑️ ハンディファン',
            '☑️ 冷感タオル',
            '☑️ 水分（ペットボトル凍らせて）',
            '☑️ 着替え（びしょ濡れイベント用）',
        ],
        'tip': '熱中症対策が命！休憩多めに',
    },
    'autumn': {  # 9-11月
        'title': '秋ディズニーの持ち物',
        'emoji': '🍂',
        'items': [
            '☑️ 羽織れる上着',
            '☑️ ブランケット（パレード待ち用）',
            '☑️ モバイルバッテリー',
            '☑️ レジャーシート',
            '☑️ 仮装グッズ（ハロウィン期間）',
        ],
        'tip': '夜は冷え込むので防寒具必須！',
    },
    'winter': {  # 12-2月
        'title': '冬ディズニーの持ち物',
        'emoji': '❄️',
        'items': [
            '☑️ ダウンジャケット',
            '☑️ マフラー・手袋・ニット帽',
            '☑️ カイロ（貼るタイプも）',
            '☑️ ブランケット',
            '☑️ 温かい飲み物用タンブラー',
            '☑️ モバイルバッテリー（寒さで減る）',
        ],
        'tip': '海風で体感-5℃！完全防寒で！',
    },
}


def get_season(target_date: str) -> str:
    """季節を取得"""
    dt = datetime.strptime(target_date, '%Y-%m-%d')
    month = dt.month
    
    if month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    elif month in [9, 10, 11]:
        return 'autumn'
    else:
        return 'winter'


def is_packing_day(target_date: str) -> bool:
    """持ち物リストを投稿する日かどうか（毎週月曜日）"""
    dt = datetime.strptime(target_date, '%Y-%m-%d')
    return dt.weekday() == 0  # 月曜日


def create_packing_tweet(target_date: str) -> str:
    """持ち物リストツイートを生成"""
    season = get_season(target_date)
    packing = PACKING_LISTS[season]
    
    tweet = f"{packing['emoji']} {packing['title']}\n"
    tweet += "━━━━━━━━━━━━━━\n\n"
    
    for item in packing['items']:
        tweet += f"{item}\n"
    
    tweet += f"\n💡 {packing['tip']}\n\n"
    tweet += "#ディズニー持ち物 #TDR準備"
    
    return tweet


if __name__ == "__main__":
    # テスト
    test_dates = ['2026-01-01', '2026-12-24', '2026-10-31', '2026-04-01']
    
    for d in test_dates:
        print(f"\n📅 {d}")
        
        event = get_current_event(d, 'sea')
        if event:
            if event['is_first_day']:
                print(f"  🎉 本日スタート！ {event['emoji']} {event['name']}")
            else:
                print(f"  {event['emoji']} {event['name']} (残り{event['days_until_end']}日)")
            print(f"     {event['highlight']}")
        
        special = get_special_day(d)
        if special:
            print(f"  {special['emoji']} {special['name']}: {special['comment']}")
        
        tips = get_smart_tips(d, 'sea', 80)
        print(f"  💡 Tips: {tips[0]}")
    
    # 持ち物リストテスト
    print("\n\n=== 持ち物リスト ===")
    for season in ['spring', 'summer', 'autumn', 'winter']:
        print(f"\n{PACKING_LISTS[season]['emoji']} {PACKING_LISTS[season]['title']}")

