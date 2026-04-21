#!/usr/bin/env python3
"""
X(Twitter)投稿用 待ち時間予測生成スクリプト
- 人気アトラクションに絞って出力
- 休止中アトラクションは-1を表示
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 既存の予測モデルをインポート
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3


# ========================================
# 対象アトラクション設定
# ========================================

# ディズニーシー - X投稿用アトラクション
SEA_TARGET_ATTRACTIONS = [
    'ソアリン',
    'アナとエルサ',
    'センターオブジアース',
    'タワーオブテラー',
    'トイストーリーマニア',
    'ラプンツェル',
    'ピーターパン',
    'プラザグリーティング',
    'レイジングスピリッツ',
    'インディージョーンズクリスタルスカルの謎',
]

# ディズニーランド - X投稿用アトラクション
LAND_TARGET_ATTRACTIONS = [
    '美女と野獣の物語',
    'モンスターズ・インク',
    'ミート・ミッキー',
    'プーさんのハニーハント',
    'ベイマックスのハッピーライド',
    'ビッグサンダーマウンテン',
    'スプラッシュマウンテン',
]

# 表示名マッピング（内部名 → 表示名）
SEA_DISPLAY_NAMES = {
    'ソアリン': 'ソアリン',
    'アナとエルサ': 'アナ雪',
    'センターオブジアース': 'センター',
    'タワーオブテラー': 'タワテラ',
    'トイストーリーマニア': 'トイマニ',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーターパン',
    'プラザグリーティング': 'プラザグリ',
    'レイジングスピリッツ': 'レイジング',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
}

LAND_DISPLAY_NAMES = {
    '美女と野獣の物語': '美女野獣',
    'モンスターズ・インク': 'モンスターズ',
    'ミート・ミッキー': 'ミートミッキー',
    'プーさんのハニーハント': 'ハニハン',
    'ベイマックスのハッピーライド': 'ベイマックス',
    'ビッグサンダーマウンテン': 'ビッグサンダー',
    'スプラッシュマウンテン': 'スプラッシュ',
}


# ========================================
# 休止情報（日付範囲で管理）
# ========================================

def get_sea_closures(date):
    """
    ディズニーシーの休止アトラクションを取得
    
    Args:
        date: チェック対象日（datetime or str）
    
    Returns:
        dict: {アトラクション名: 理由} の休止アトラクション
    """
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    closures = {}
    
    # インディ・ジョーンズ: 2025年8月18日～未定（長期休止）
    closures['インディージョーンズクリスタルスカルの謎'] = '長期休止中（再開未定）'
    
    # レイジングスピリッツ: 2026年1月27日～2月20日
    if datetime(2026, 1, 27) <= date <= datetime(2026, 2, 20):
        closures['レイジングスピリッツ'] = 'メンテナンス（～2/20）'
    
    # ディズニーシー・エレクトリックレールウェイ: 2026年1月27日～3月10日
    # (対象アトラクションに含まれていないので不要)
    
    # マジックランプシアター: 2026年2月25日～3月16日
    # (対象アトラクションに含まれていないので不要)
    
    return closures


def get_land_closures(date):
    """
    ディズニーランドの休止アトラクションを取得
    
    Args:
        date: チェック対象日（datetime or str）
    
    Returns:
        dict: {アトラクション名: 理由} の休止アトラクション
    """
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    closures = {}
    
    # スプラッシュ・マウンテン: 2026年1月14日～2月12日
    if datetime(2026, 1, 14) <= date <= datetime(2026, 2, 12):
        closures['スプラッシュマウンテン'] = 'メンテナンス（～2/12）'
    
    # ホーンテッドマンション: 2026年1月13日～2月18日
    # (対象アトラクションに含まれていないので不要)
    
    # 美女と野獣: 2026年2月27日～3月9日
    if datetime(2026, 2, 27) <= date <= datetime(2026, 3, 9):
        closures['美女と野獣の物語'] = 'メンテナンス（～3/9）'
    
    return closures


# ========================================
# 予測生成
# ========================================

def generate_sea_predictions(date_str, time_slots=None):
    """
    ディズニーシーの予測を生成
    
    Args:
        date_str: 予測対象日（YYYY-MM-DD形式）
        time_slots: 予測する時間帯リスト（省略時はデフォルト）
    
    Returns:
        dict: アトラクション別の予測結果
    """
    print(f"\n🌊 ディズニーシー予測: {date_str}")
    print("=" * 50)
    
    # 休止情報を取得
    closures = get_sea_closures(date_str)
    
    # 予測モデルをロード
    predictor = DisneySeaWaitTimePredictorV3()
    
    if not predictor.load_models():
        print("❌ モデルが見つかりません")
        return None
    
    # 休止中でないアトラクションのみ予測
    attractions_to_predict = [a for a in SEA_TARGET_ATTRACTIONS if a not in closures]
    
    if time_slots is None:
        time_slots = [f"{h:02d}:00" for h in range(9, 21)]  # 9時〜20時
    
    # 予測実行
    predictions = predictor.predict(
        date=date_str,
        time_slots=time_slots,
        attractions=attractions_to_predict
    )
    
    if predictions is None:
        return None
    
    # 結果を整形
    results = {}
    
    # 予測結果からアトラクション別平均を計算
    avg_predictions = predictions.groupby('attraction_name')['predicted_wait_time'].mean()
    
    for attraction in SEA_TARGET_ATTRACTIONS:
        display_name = SEA_DISPLAY_NAMES.get(attraction, attraction)
        
        if attraction in closures:
            results[attraction] = {
                'display_name': display_name,
                'wait_time': -1,
                'status': 'closed',
                'reason': closures[attraction]
            }
        elif attraction in avg_predictions.index:
            wait = int(round(avg_predictions[attraction]))
            results[attraction] = {
                'display_name': display_name,
                'wait_time': max(5, wait),  # 最低5分
                'status': 'open',
                'reason': None
            }
        else:
            results[attraction] = {
                'display_name': display_name,
                'wait_time': -1,
                'status': 'unknown',
                'reason': 'データなし'
            }
    
    return results


def generate_land_predictions(date_str, time_slots=None):
    """
    ディズニーランドの予測を生成
    
    Args:
        date_str: 予測対象日（YYYY-MM-DD形式）
        time_slots: 予測する時間帯リスト（省略時はデフォルト）
    
    Returns:
        dict: アトラクション別の予測結果
    """
    print(f"\n🏰 ディズニーランド予測: {date_str}")
    print("=" * 50)
    
    # 休止情報を取得
    closures = get_land_closures(date_str)
    
    # 予測モデルをロード
    predictor = DisneyLandWaitTimePredictorV3()
    
    if not predictor.load_models():
        print("❌ モデルが見つかりません")
        return None
    
    # 休止中でないアトラクションのみ予測
    attractions_to_predict = [a for a in LAND_TARGET_ATTRACTIONS if a not in closures]
    
    if time_slots is None:
        time_slots = [f"{h:02d}:00" for h in range(9, 21)]  # 9時〜20時
    
    # 予測実行
    predictions = predictor.predict(
        date=date_str,
        time_slots=time_slots,
        attractions=attractions_to_predict
    )
    
    if predictions is None:
        return None
    
    # 結果を整形
    results = {}
    
    # 予測結果からアトラクション別平均を計算
    avg_predictions = predictions.groupby('attraction_name')['predicted_wait_time'].mean()
    
    for attraction in LAND_TARGET_ATTRACTIONS:
        display_name = LAND_DISPLAY_NAMES.get(attraction, attraction)
        
        if attraction in closures:
            results[attraction] = {
                'display_name': display_name,
                'wait_time': -1,
                'status': 'closed',
                'reason': closures[attraction]
            }
        elif attraction in avg_predictions.index:
            wait = int(round(avg_predictions[attraction]))
            results[attraction] = {
                'display_name': display_name,
                'wait_time': max(5, wait),  # 最低5分
                'status': 'open',
                'reason': None
            }
        else:
            results[attraction] = {
                'display_name': display_name,
                'wait_time': -1,
                'status': 'unknown',
                'reason': 'データなし'
            }
    
    return results


# ========================================
# X投稿用フォーマット
# ========================================

def format_for_x_sea(results, date_str):
    """
    ディズニーシー予測をX投稿用にフォーマット
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_name = day_names[date.weekday()]
    
    lines = []
    lines.append(f"🌊 シー AI待ち時間予測")
    lines.append(f"📅 {date.month}/{date.day}({day_name})")
    lines.append("")
    
    for attraction in SEA_TARGET_ATTRACTIONS:
        if attraction not in results:
            continue
        
        data = results[attraction]
        display_name = data['display_name']
        wait = data['wait_time']
        
        if wait == -1:
            lines.append(f"❌{display_name}: 休止")
        else:
            lines.append(f"🎢{display_name}: {wait}分")
    
    lines.append("")
    lines.append("#TDR #ディズニーシー #待ち時間予測")
    
    return "\n".join(lines)


def format_for_x_land(results, date_str):
    """
    ディズニーランド予測をX投稿用にフォーマット
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_name = day_names[date.weekday()]
    
    lines = []
    lines.append(f"🏰 ランド AI待ち時間予測")
    lines.append(f"📅 {date.month}/{date.day}({day_name})")
    lines.append("")
    
    for attraction in LAND_TARGET_ATTRACTIONS:
        if attraction not in results:
            continue
        
        data = results[attraction]
        display_name = data['display_name']
        wait = data['wait_time']
        
        if wait == -1:
            lines.append(f"❌{display_name}: 休止")
        else:
            lines.append(f"🎢{display_name}: {wait}分")
    
    lines.append("")
    lines.append("#TDR #ディズニーランド #待ち時間予測")
    
    return "\n".join(lines)


def format_combined_for_x(sea_results, land_results, date_str):
    """
    シーとランドの予測を1つの投稿にまとめる
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_name = day_names[date.weekday()]
    
    lines = []
    lines.append(f"🎢 TDR AI待ち時間予測")
    lines.append(f"📅 {date.month}/{date.day}({day_name})")
    lines.append("")
    
    # シー
    lines.append("🌊【シー】")
    for attraction in SEA_TARGET_ATTRACTIONS:
        if attraction not in sea_results:
            continue
        
        data = sea_results[attraction]
        display_name = data['display_name']
        wait = data['wait_time']
        
        if wait == -1:
            lines.append(f"❌{display_name}")
        else:
            lines.append(f"{display_name}:{wait}分")
    
    lines.append("")
    
    # ランド
    lines.append("🏰【ランド】")
    for attraction in LAND_TARGET_ATTRACTIONS:
        if attraction not in land_results:
            continue
        
        data = land_results[attraction]
        display_name = data['display_name']
        wait = data['wait_time']
        
        if wait == -1:
            lines.append(f"❌{display_name}")
        else:
            lines.append(f"{display_name}:{wait}分")
    
    lines.append("")
    lines.append("#TDR #待ち時間予測")
    
    return "\n".join(lines)


# ========================================
# メイン処理
# ========================================

def main():
    """メイン処理"""
    print("🎢 X投稿用 TDR待ち時間予測生成")
    print("=" * 60)
    
    # 予測対象日を取得（引数があればそれを使用、なければ明日）
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        tomorrow = datetime.now() + timedelta(days=1)
        target_date = tomorrow.strftime('%Y-%m-%d')
    
    print(f"📅 対象日: {target_date}")
    
    # シー予測
    sea_results = generate_sea_predictions(target_date)
    
    if sea_results:
        print("\n" + "=" * 50)
        print("📱 シー X投稿用テキスト:")
        print("-" * 50)
        x_text_sea = format_for_x_sea(sea_results, target_date)
        print(x_text_sea)
        print("-" * 50)
        print(f"文字数: {len(x_text_sea)}")
    
    # ランド予測
    land_results = generate_land_predictions(target_date)
    
    if land_results:
        print("\n" + "=" * 50)
        print("📱 ランド X投稿用テキスト:")
        print("-" * 50)
        x_text_land = format_for_x_land(land_results, target_date)
        print(x_text_land)
        print("-" * 50)
        print(f"文字数: {len(x_text_land)}")
    
    # 統合版（文字数制限に収まる場合）
    if sea_results and land_results:
        print("\n" + "=" * 50)
        print("📱 統合版 X投稿用テキスト:")
        print("-" * 50)
        x_text_combined = format_combined_for_x(sea_results, land_results, target_date)
        print(x_text_combined)
        print("-" * 50)
        print(f"文字数: {len(x_text_combined)}")
        
        if len(x_text_combined) > 280:
            print("⚠️ 280文字を超えています。個別投稿を推奨します。")
    
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
