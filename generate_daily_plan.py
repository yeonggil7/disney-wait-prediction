#!/usr/bin/env python3
"""
TDR 1日おすすめプラン生成スクリプト v2
- AI待ち時間予測に基づいた効率的な回り方を提案
- エリア間の徒歩移動時間を考慮
- 貪欲最適化で回れるアトラクション数を最大化
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3
from generate_x_heatmap import get_sea_closures, get_land_closures


# ========================================
# エリア・位置情報
# ========================================

# --- ディズニーシー ---
SEA_ATTRACTION_AREA = {
    'ソアリン': 'メディテレーニアンハーバー',
    'アナとエルサ': 'ファンタジースプリングス',
    'センターオブジアース': 'ミステリアスアイランド',
    'タワーオブテラー': 'アメリカンウォーターフロント',
    'トイストーリーマニア': 'アメリカンウォーターフロント',
    'ラプンツェル': 'ファンタジースプリングス',
    'ピーターパン': 'ファンタジースプリングス',
    'プラザグリーティング': 'メディテレーニアンハーバー',
    'レイジングスピリッツ': 'ロストリバーデルタ',
    'インディージョーンズクリスタルスカルの謎': 'ロストリバーデルタ',
}

# エリア間の徒歩移動時間（分）- 実測ベース
SEA_WALK_TIME = {
    ('メディテレーニアンハーバー', 'メディテレーニアンハーバー'): 3,
    ('メディテレーニアンハーバー', 'アメリカンウォーターフロント'): 7,
    ('メディテレーニアンハーバー', 'ミステリアスアイランド'): 8,
    ('メディテレーニアンハーバー', 'ロストリバーデルタ'): 12,
    ('メディテレーニアンハーバー', 'アラビアンコースト'): 15,
    ('メディテレーニアンハーバー', 'マーメイドラグーン'): 13,
    ('メディテレーニアンハーバー', 'ファンタジースプリングス'): 15,
    ('アメリカンウォーターフロント', 'アメリカンウォーターフロント'): 3,
    ('アメリカンウォーターフロント', 'ミステリアスアイランド'): 8,
    ('アメリカンウォーターフロント', 'ロストリバーデルタ'): 10,
    ('アメリカンウォーターフロント', 'アラビアンコースト'): 12,
    ('アメリカンウォーターフロント', 'マーメイドラグーン'): 10,
    ('アメリカンウォーターフロント', 'ファンタジースプリングス'): 12,
    ('ミステリアスアイランド', 'ミステリアスアイランド'): 2,
    ('ミステリアスアイランド', 'ロストリバーデルタ'): 7,
    ('ミステリアスアイランド', 'アラビアンコースト'): 10,
    ('ミステリアスアイランド', 'マーメイドラグーン'): 8,
    ('ミステリアスアイランド', 'ファンタジースプリングス'): 10,
    ('ロストリバーデルタ', 'ロストリバーデルタ'): 3,
    ('ロストリバーデルタ', 'アラビアンコースト'): 5,
    ('ロストリバーデルタ', 'マーメイドラグーン'): 5,
    ('ロストリバーデルタ', 'ファンタジースプリングス'): 7,
    ('アラビアンコースト', 'アラビアンコースト'): 3,
    ('アラビアンコースト', 'マーメイドラグーン'): 3,
    ('アラビアンコースト', 'ファンタジースプリングス'): 5,
    ('マーメイドラグーン', 'マーメイドラグーン'): 3,
    ('マーメイドラグーン', 'ファンタジースプリングス'): 5,
    ('ファンタジースプリングス', 'ファンタジースプリングス'): 3,
}

# --- ディズニーランド ---
LAND_ATTRACTION_AREA = {
    '美女と野獣の物語': 'ファンタジーランド',
    'モンスターズ・インク': 'トゥモローランド',
    'ミート・ミッキー': 'トゥーンタウン',
    'プーさんのハニーハント': 'ファンタジーランド',
    'ベイマックスのハッピーライド': 'トゥモローランド',
    'ビッグサンダーマウンテン': 'ウエスタンランド',
    'スプラッシュマウンテン': 'クリッターカントリー',
}

LAND_WALK_TIME = {
    ('ワールドバザール', 'ワールドバザール'): 2,
    ('ワールドバザール', 'アドベンチャーランド'): 5,
    ('ワールドバザール', 'ウエスタンランド'): 7,
    ('ワールドバザール', 'クリッターカントリー'): 10,
    ('ワールドバザール', 'ファンタジーランド'): 7,
    ('ワールドバザール', 'トゥーンタウン'): 10,
    ('ワールドバザール', 'トゥモローランド'): 5,
    ('アドベンチャーランド', 'アドベンチャーランド'): 3,
    ('アドベンチャーランド', 'ウエスタンランド'): 5,
    ('アドベンチャーランド', 'クリッターカントリー'): 8,
    ('アドベンチャーランド', 'ファンタジーランド'): 8,
    ('アドベンチャーランド', 'トゥーンタウン'): 12,
    ('アドベンチャーランド', 'トゥモローランド'): 7,
    ('ウエスタンランド', 'ウエスタンランド'): 3,
    ('ウエスタンランド', 'クリッターカントリー'): 3,
    ('ウエスタンランド', 'ファンタジーランド'): 5,
    ('ウエスタンランド', 'トゥーンタウン'): 8,
    ('ウエスタンランド', 'トゥモローランド'): 10,
    ('クリッターカントリー', 'クリッターカントリー'): 2,
    ('クリッターカントリー', 'ファンタジーランド'): 5,
    ('クリッターカントリー', 'トゥーンタウン'): 7,
    ('クリッターカントリー', 'トゥモローランド'): 12,
    ('ファンタジーランド', 'ファンタジーランド'): 3,
    ('ファンタジーランド', 'トゥーンタウン'): 5,
    ('ファンタジーランド', 'トゥモローランド'): 7,
    ('トゥーンタウン', 'トゥーンタウン'): 3,
    ('トゥーンタウン', 'トゥモローランド'): 7,
    ('トゥモローランド', 'トゥモローランド'): 3,
}

# 対象アトラクション
SEA_TARGET_ATTRACTIONS = [
    'ソアリン', 'アナとエルサ', 'センターオブジアース', 'タワーオブテラー',
    'トイストーリーマニア', 'ラプンツェル', 'ピーターパン', 'プラザグリーティング',
    'レイジングスピリッツ', 'インディージョーンズクリスタルスカルの謎',
]

LAND_TARGET_ATTRACTIONS = [
    '美女と野獣の物語', 'モンスターズ・インク', 'ミート・ミッキー',
    'プーさんのハニーハント', 'ベイマックスのハッピーライド',
    'ビッグサンダーマウンテン', 'スプラッシュマウンテン',
]

# アトラクション乗車時間（分）
RIDE_DURATION = {
    'ソアリン': 5, 'アナとエルサ': 6, 'センターオブジアース': 3,
    'タワーオブテラー': 2, 'トイストーリーマニア': 5, 'ラプンツェル': 6,
    'ピーターパン': 3, 'プラザグリーティング': 3, 'レイジングスピリッツ': 2,
    'インディージョーンズクリスタルスカルの謎': 3,
    '美女と野獣の物語': 8, 'モンスターズ・インク': 4, 'ミート・ミッキー': 3,
    'プーさんのハニーハント': 4, 'ベイマックスのハッピーライド': 2,
    'ビッグサンダーマウンテン': 4, 'スプラッシュマウンテン': 10,
}

# X投稿用短縮名
SEA_SHORT_NAMES = {
    'ソアリン': 'ソアリン', 'アナとエルサ': 'アナ雪',
    'センターオブジアース': 'センター', 'タワーオブテラー': 'タワテラ',
    'トイストーリーマニア': 'トイマニ', 'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーターパン', 'プラザグリーティング': 'プラザグリ',
    'レイジングスピリッツ': 'レイジング',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
}

LAND_SHORT_NAMES = {
    '美女と野獣の物語': '美女と野獣', 'モンスターズ・インク': 'モンスターズ',
    'ミート・ミッキー': 'ミートミッキー', 'プーさんのハニーハント': 'プーさん',
    'ベイマックスのハッピーライド': 'ベイマックス',
    'ビッグサンダーマウンテン': 'ビグサン', 'スプラッシュマウンテン': 'スプラッシュ',
}


# ========================================
# ユーティリティ
# ========================================

def get_walk_time(walk_table, area_from, area_to):
    """エリア間の徒歩時間を取得（双方向対応）"""
    if (area_from, area_to) in walk_table:
        return walk_table[(area_from, area_to)]
    elif (area_to, area_from) in walk_table:
        return walk_table[(area_to, area_from)]
    return 10  # デフォルト


def get_wait_at_time(predictions, attraction, hour):
    """指定時間帯の待ち時間を取得"""
    time_str = f"{hour:02d}:00"
    df = predictions[(predictions['attraction_name'] == attraction) & 
                     (predictions['time'] == time_str)]
    if not df.empty:
        return int(df['predicted_wait_time'].values[0])
    return None


# ========================================
# 予測データ取得
# ========================================

def get_predictions(park: str, date_str: str):
    """予測データを取得"""
    if park == 'sea':
        predictor = DisneySeaWaitTimePredictorV3()
        target = SEA_TARGET_ATTRACTIONS
        closures = get_sea_closures(date_str)
    else:
        predictor = DisneyLandWaitTimePredictorV3()
        target = LAND_TARGET_ATTRACTIONS
        closures = get_land_closures(date_str)

    if not predictor.load_models():
        return None, None, None

    open_attractions = [a for a in target if a not in closures]
    time_slots = [f"{h:02d}:00" for h in range(9, 21)]
    predictions = predictor.predict(date=date_str, time_slots=time_slots, attractions=open_attractions)
    return predictions, open_attractions, closures


# ========================================
# 貪欲最適化プラン生成
# ========================================

def generate_efficient_plan(park: str, date_str: str, open_hour=9, close_hour=21):
    """
    貪欲最適化による1日プラン生成

    各ステップで「(移動時間 + 待ち時間) が最も短い」アトラクションを選ぶ。
    これにより回れるアトラクション数を最大化する。
    ただし開園直後だけは「朝イチ効果が最も大きい」アトラクションを優先。
    """
    print(f"\n📋 {park.upper()} 1日プラン生成中...")

    predictions, open_attractions, closures = get_predictions(park, date_str)
    if predictions is None:
        return None

    if park == 'sea':
        attraction_area = SEA_ATTRACTION_AREA
        walk_table = SEA_WALK_TIME
        entry_area = 'メディテレーニアンハーバー'
    else:
        attraction_area = LAND_ATTRACTION_AREA
        walk_table = LAND_WALK_TIME
        entry_area = 'ワールドバザール'

    # ----- 開園ダッシュ先を決定 -----
    # 「朝(9時)と昼(12-14時ピーク)の待ち時間差」が大きいものを選ぶ
    morning_scores = {}
    for a in open_attractions:
        w9 = get_wait_at_time(predictions, a, 9)
        wpeak = max(
            get_wait_at_time(predictions, a, 12) or 0,
            get_wait_at_time(predictions, a, 13) or 0,
            get_wait_at_time(predictions, a, 14) or 0,
        )
        if w9 is not None:
            # 朝行く効果 = ピークとの差分
            morning_scores[a] = wpeak - w9
    first_attraction = max(morning_scores, key=morning_scores.get) if morning_scores else open_attractions[0]

    # ----- プラン構築 -----
    plan = []
    visited = set()
    current_area = entry_area
    current_time = datetime.strptime(f"{date_str} {open_hour:02d}:00", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(f"{date_str} {close_hour:02d}:00", "%Y-%m-%d %H:%M")

    # (1) 開園ダッシュ
    walk = get_walk_time(walk_table, current_area, attraction_area[first_attraction])
    # 朝一番は並んでいる人が少ないので、予測の30-50%程度
    raw_wait = get_wait_at_time(predictions, first_attraction, 9) or 30
    dash_wait = max(5, int(raw_wait * 0.3))  # 開園ダッシュなら大幅に短縮
    ride = RIDE_DURATION.get(first_attraction, 5)

    plan.append({
        'time': current_time.strftime("%H:%M"),
        'attraction': first_attraction,
        'wait': dash_wait,
        'walk': walk,
        'ride': ride,
        'tag': 'dash',
        'tip': f'開園ダッシュ！徒歩{walk}分',
    })
    visited.add(first_attraction)
    current_time += timedelta(minutes=walk + dash_wait + ride)
    current_area = attraction_area[first_attraction]

    # (2) 2番手 — 同エリアor近隣の人気アトラクション（朝の短い待ちを活かす）
    # 開園直後はまだ空いているので、近くの人気をもう1つ拾う
    second_candidates = []
    for a in open_attractions:
        if a in visited:
            continue
        walk_to = get_walk_time(walk_table, current_area, attraction_area[a])
        w = get_wait_at_time(predictions, a, current_time.hour) or 60
        # 朝補正（10時前なら0.5掛け）
        if current_time.hour < 10:
            w = max(5, int(w * 0.5))
        second_candidates.append((a, walk_to, w))

    if second_candidates:
        # 移動+待ちが短い順
        second_candidates.sort(key=lambda x: x[1] + x[2])
        a2, walk2, wait2 = second_candidates[0]
        ride2 = RIDE_DURATION.get(a2, 5)
        plan.append({
            'time': current_time.strftime("%H:%M"),
            'attraction': a2,
            'wait': wait2,
            'walk': walk2,
            'ride': ride2,
            'tag': 'morning',
            'tip': f'徒歩{walk2}分→朝の空きを活用',
        })
        visited.add(a2)
        current_time += timedelta(minutes=walk2 + wait2 + ride2)
        current_area = attraction_area[a2]

    # (3) 残りを貪欲法で埋める（ランチ込み）
    had_lunch = False

    while current_time < end_time - timedelta(minutes=20):
        remaining = [a for a in open_attractions if a not in visited]
        if not remaining:
            break

        # ランチ挿入（11:30〜13:30 の間で、まだ食べてなければ）
        if not had_lunch and (
            (current_time.hour == 11 and current_time.minute >= 30) or
            current_time.hour == 12
        ):
            plan.append({
                'time': current_time.strftime("%H:%M"),
                'attraction': 'ランチ休憩',
                'wait': 0,
                'walk': 0,
                'ride': 0,
                'tag': 'lunch',
                'tip': '早めのランチで混雑回避',
            })
            current_time += timedelta(minutes=50)
            had_lunch = True
            continue

        # 各候補の「移動 + 待ち」コストを計算
        # ★ 到着時刻ベースで待ち時間を取得する
        candidates = []
        for a in remaining:
            area_to = attraction_area[a]
            walk_to = get_walk_time(walk_table, current_area, area_to)
            arrival_time = current_time + timedelta(minutes=walk_to)
            arrival_hour = min(arrival_time.hour, 20)

            w = get_wait_at_time(predictions, a, arrival_hour)
            if w is None:
                continue

            # 次の1時間後の待ち時間もチェックし、短い方を使う
            # （少し待ってから並んだ方が得なケースに対応）
            w_next = get_wait_at_time(predictions, a, min(arrival_hour + 1, 20))
            if w_next is not None and w_next < w:
                # 次の時間帯まで待つコスト vs 今の待ち時間
                minutes_until_next = 60 - arrival_time.minute
                if w - w_next > minutes_until_next:
                    # 待った方が得
                    w = w_next
                    walk_to += minutes_until_next  # 待機時間を移動に含める

            cost = walk_to + w
            candidates.append((a, walk_to, w, cost))

        if not candidates:
            break

        # コスト最小のアトラクションを選択
        candidates.sort(key=lambda x: x[3])
        best_a, best_walk, best_wait, _ = candidates[0]
        best_ride = RIDE_DURATION.get(best_a, 5)

        # 閉園時間チェック
        total_needed = best_walk + best_wait + best_ride
        if current_time + timedelta(minutes=total_needed) > end_time:
            # まだ他の候補で間に合うものがあるか探す
            found = False
            for a, wlk, wt, _ in candidates[1:]:
                rd = RIDE_DURATION.get(a, 5)
                if current_time + timedelta(minutes=wlk + wt + rd) <= end_time:
                    best_a, best_walk, best_wait, best_ride = a, wlk, wt, rd
                    total_needed = best_walk + best_wait + best_ride
                    found = True
                    break
            if not found:
                break

        # 時間帯に応じたタグ
        if current_time.hour >= 18:
            tag = 'evening'
            tip = f'徒歩{best_walk}分→夜は空いてくる'
        elif current_time.hour >= 15:
            tag = 'afternoon_late'
            tip = f'徒歩{best_walk}分'
        else:
            tag = 'afternoon'
            tip = f'徒歩{best_walk}分'

        plan.append({
            'time': current_time.strftime("%H:%M"),
            'attraction': best_a,
            'wait': best_wait,
            'walk': best_walk,
            'ride': best_ride,
            'tag': tag,
            'tip': tip,
        })
        visited.add(best_a)
        current_time += timedelta(minutes=total_needed)
        current_area = attraction_area[best_a]

    # ランチ入れ忘れ防止
    if not had_lunch:
        for i, item in enumerate(plan):
            t = datetime.strptime(f"{date_str} {item['time']}", "%Y-%m-%d %H:%M")
            if t.hour >= 12 and item['tag'] != 'lunch':
                plan.insert(i, {
                    'time': item['time'],
                    'attraction': 'ランチ休憩',
                    'wait': 0, 'walk': 0, 'ride': 0,
                    'tag': 'lunch',
                    'tip': 'ランチ休憩',
                })
                shift = timedelta(minutes=50)
                for j in range(i + 1, len(plan)):
                    old_t = datetime.strptime(f"{date_str} {plan[j]['time']}", "%Y-%m-%d %H:%M")
                    plan[j]['time'] = (old_t + shift).strftime("%H:%M")
                break

    # --- 統計 ---
    attraction_items = [p for p in plan if p['tag'] not in ('lunch',)]
    total_wait = sum(p['wait'] for p in attraction_items)
    total_walk = sum(p['walk'] for p in attraction_items)
    attractions_count = len(attraction_items)

    return {
        'park': park,
        'date': date_str,
        'plan': plan,
        'total_wait': total_wait,
        'total_walk': total_walk,
        'attractions_count': attractions_count,
        'visited': visited,
        'closures': closures,
    }


# ========================================
# 出力フォーマット
# ========================================

TAG_EMOJI = {
    'dash': '🏃',
    'morning': '☀️',
    'afternoon': '🎢',
    'afternoon_late': '🎡',
    'evening': '🌙',
    'lunch': '🍽️',
}


def format_plan_for_display(result):
    """コンソール表示用"""
    if result is None:
        return "プランを生成できませんでした"

    park_name = "ディズニーシー" if result['park'] == 'sea' else "ディズニーランド"
    park_emoji = "🌊" if result['park'] == 'sea' else "🏰"
    short_names = SEA_SHORT_NAMES if result['park'] == 'sea' else LAND_SHORT_NAMES

    dt = datetime.strptime(result['date'], '%Y-%m-%d')
    days = ['月', '火', '水', '木', '金', '土', '日']

    lines = []
    lines.append(f"{park_emoji} {park_name} おすすめ1日プラン")
    lines.append(f"📅 {dt.month}/{dt.day}({days[dt.weekday()]})")
    lines.append("=" * 44)

    for item in result['plan']:
        emoji = TAG_EMOJI.get(item['tag'], '▶️')
        name = short_names.get(item['attraction'], item['attraction'])

        if item['tag'] == 'lunch':
            lines.append(f"  {item['time']}  {emoji} {name}")
            lines.append(f"          💡 {item['tip']}")
        else:
            wait_str = f"待ち{item['wait']}分" if item['wait'] > 0 else ""
            lines.append(f"  {item['time']}  {emoji} {name}  {wait_str}")
            if item.get('tip'):
                lines.append(f"          💡 {item['tip']}")

    lines.append("=" * 44)
    lines.append(f"🎢 {result['attractions_count']}アトラクション制覇")
    lines.append(f"⏱️  合計待ち時間: 約{result['total_wait']}分")
    lines.append(f"🚶 合計移動時間: 約{result['total_walk']}分")

    if result['closures']:
        closed = ', '.join([short_names.get(n, n[:6]) for n in result['closures']])
        lines.append(f"❌ 休止中: {closed}")

    return "\n".join(lines)


def format_plan_for_x(result):
    """X投稿用コンパクト版"""
    if result is None:
        return None

    park_name = "シー" if result['park'] == 'sea' else "ランド"
    park_emoji = "🌊" if result['park'] == 'sea' else "🏰"
    hashtag = "#TDS" if result['park'] == 'sea' else "#TDL"
    short_names = SEA_SHORT_NAMES if result['park'] == 'sea' else LAND_SHORT_NAMES

    dt = datetime.strptime(result['date'], '%Y-%m-%d')
    days = ['月', '火', '水', '木', '金', '土', '日']

    lines = []
    lines.append(f"{park_emoji} {park_name} 回り方ガイド")
    lines.append(f"📅 {dt.month}/{dt.day}({days[dt.weekday()]}) AIおすすめ")
    lines.append("")

    for item in result['plan']:
        emoji = TAG_EMOJI.get(item['tag'], '▶️')
        name = short_names.get(item['attraction'], item['attraction'])
        if item['tag'] == 'lunch':
            lines.append(f"{emoji}{item['time']} ランチ")
        else:
            lines.append(f"{emoji}{item['time']} {name}({item['wait']}分)")

    lines.append("")
    lines.append(f"🎢{result['attractions_count']}個制覇 ⏱️待ち計{result['total_wait']}分 🚶{result['total_walk']}分")
    lines.append(f"{hashtag} #ディズニー #攻略")

    return "\n".join(lines)


# ========================================
# メイン
# ========================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='TDR 1日おすすめプラン生成 v2')

    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    parser.add_argument('--park', '-p', default='sea', choices=['sea', 'land', 'both'])
    parser.add_argument('--date', '-d', default=tomorrow)
    parser.add_argument('--x-format', '-x', action='store_true')
    args = parser.parse_args()

    print("🎢 TDR 1日おすすめプラン生成 v2")
    print("=" * 50)
    print(f"📅 対象日: {args.date}")

    parks = ['sea', 'land'] if args.park == 'both' else [args.park]

    for park in parks:
        result = generate_efficient_plan(park, args.date)
        if result:
            print("\n" + "=" * 50)
            if args.x_format:
                x_text = format_plan_for_x(result)
                print("📱 X投稿用:")
                print("-" * 50)
                print(x_text)
                print("-" * 50)
                print(f"文字数: {len(x_text)}/280")
            else:
                print(format_plan_for_display(result))

    print("\n✅ 完了!")


if __name__ == "__main__":
    main()
