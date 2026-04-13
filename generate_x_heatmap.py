#!/usr/bin/env python3
"""
X(Twitter)投稿用 待ち時間ヒートマップ生成スクリプト
- 人気アトラクションに絞って出力
- 休止中アトラクションは-1を表示
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import math

# 予測システムをインポート
from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3
from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3

# 可視化ライブラリ
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

# 日本語フォント設定
plt.rcParams['font.family'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'sans-serif']

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


# ========================================
# 対象アトラクション設定
# ========================================

# ディズニーシー - X投稿用アトラクション（内部名）
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

# ディズニーランド - X投稿用アトラクション（内部名）
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
    'アナとエルサ': 'アナとエルサ',
    'センターオブジアース': 'センター・オブ・ジ・アース',
    'タワーオブテラー': 'タワー・オブ・テラー',
    'トイストーリーマニア': 'トイ・ストーリー・マニア！',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーターパン',
    'プラザグリーティング': 'プラザグリーティング',
    'レイジングスピリッツ': 'レイジングスピリッツ',
    'インディージョーンズクリスタルスカルの謎': 'インディ・ジョーンズ',
}

LAND_DISPLAY_NAMES = {
    '美女と野獣の物語': '美女と野獣の物語',
    'モンスターズ・インク': 'モンスターズ・インク',
    'ミート・ミッキー': 'ミート・ミッキー',
    'プーさんのハニーハント': 'プーさんのハニーハント',
    'ベイマックスのハッピーライド': 'ベイマックスのハッピーライド',
    'ビッグサンダーマウンテン': 'ビッグサンダーマウンテン',
    'スプラッシュマウンテン': 'スプラッシュマウンテン',
}


# ========================================
# 休止情報（日付範囲で管理）
# ========================================

def get_sea_closures(date):
    """ディズニーシーの休止アトラクションを取得"""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    closures = {}
    
    # インディ・ジョーンズ: 長期休止中（再開未定）
    closures['インディージョーンズクリスタルスカルの謎'] = '長期休止'
    
    # レイジングスピリッツ: 2026年1月27日～2月20日
    if datetime(2026, 1, 27) <= date <= datetime(2026, 2, 20):
        closures['レイジングスピリッツ'] = 'メンテナンス'
    
    return closures


def get_land_closures(date):
    """ディズニーランドの休止アトラクションを取得"""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    closures = {}
    
    # スプラッシュ・マウンテン: 2026年1月14日～2月12日
    if datetime(2026, 1, 14) <= date <= datetime(2026, 2, 12):
        closures['スプラッシュマウンテン'] = 'メンテナンス'
    
    # 美女と野獣: 2026年2月27日～3月9日
    if datetime(2026, 2, 27) <= date <= datetime(2026, 3, 9):
        closures['美女と野獣の物語'] = 'メンテナンス'
    
    return closures


# ========================================
# ヒートマップ生成
# ========================================

def round_up_to_10(value):
    """10分単位で繰り上げ"""
    if pd.isna(value) or value < 0:
        return value  # -1（休止）はそのまま
    if value <= 0:
        return 5  # 最低5分
    return int(math.ceil(value / 10) * 10)


def get_day_of_week_ja(date_str):
    """日本語の曜日を取得"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    days = ['月', '火', '水', '木', '金', '土', '日']
    return days[date.weekday()]


def generate_sea_heatmap(date_str, output_dir="predictions_x"):
    """ディズニーシーのヒートマップを生成"""
    
    print(f"\n🌊 ディズニーシー ヒートマップ生成: {date_str}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 休止情報を取得
    closures = get_sea_closures(date_str)
    
    # 予測モデルをロード
    predictor = DisneySeaWaitTimePredictorV3()
    if not predictor.load_models():
        print("❌ モデルが見つかりません")
        return None
    
    # 休止中でないアトラクションのみ予測
    attractions_to_predict = [a for a in SEA_TARGET_ATTRACTIONS if a not in closures]
    
    # 9:00〜21:00の時間帯
    time_slots = [f"{h:02d}:15" for h in range(9, 21)] + [f"{h:02d}:45" for h in range(9, 21)]
    time_slots = sorted(time_slots)
    
    # 予測実行
    predictions = predictor.predict(
        date=date_str,
        time_slots=time_slots,
        attractions=attractions_to_predict
    )
    
    if predictions is None:
        return None
    
    # 休止中アトラクションを追加（-1で）
    for attraction in closures:
        for time in time_slots:
            predictions = pd.concat([predictions, pd.DataFrame([{
                'date': date_str,
                'time': time,
                'attraction_name': attraction,
                'predicted_wait_time': -1
            }])], ignore_index=True)
    
    # 対象アトラクションのみにフィルタリング
    predictions = predictions[predictions['attraction_name'].isin(SEA_TARGET_ATTRACTIONS)]
    
    # 表示名に変換
    predictions['display_name'] = predictions['attraction_name'].map(SEA_DISPLAY_NAMES)
    
    # 10分単位で繰り上げ
    predictions['wait_rounded'] = predictions['predicted_wait_time'].apply(round_up_to_10)
    
    # ピボットテーブル作成
    pivot = predictions.pivot_table(
        values='wait_rounded',
        index='display_name',
        columns='time',
        aggfunc='mean'
    )
    
    # 時間を整形（09:15 → 09:15 のまま）
    # アトラクション順序を固定
    ordered_attractions = [SEA_DISPLAY_NAMES[a] for a in SEA_TARGET_ATTRACTIONS if a in SEA_DISPLAY_NAMES]
    pivot = pivot.reindex([a for a in ordered_attractions if a in pivot.index])
    
    # ヒートマップ描画
    _create_heatmap_figure(
        pivot, date_str, 
        title_prefix="🌊 ディズニーシー",
        output_file=os.path.join(output_dir, f"sea_heatmap_{date_str}.png"),
        bg_color='#16213e'  # ダークブルー
    )
    
    print(f"✅ ヒートマップ保存: {output_dir}/sea_heatmap_{date_str}.png")
    return os.path.join(output_dir, f"sea_heatmap_{date_str}.png")


def generate_land_heatmap(date_str, output_dir="predictions_x"):
    """ディズニーランドのヒートマップを生成"""
    
    print(f"\n🏰 ディズニーランド ヒートマップ生成: {date_str}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 休止情報を取得
    closures = get_land_closures(date_str)
    
    # 予測モデルをロード
    predictor = DisneyLandWaitTimePredictorV3()
    if not predictor.load_models():
        print("❌ モデルが見つかりません")
        return None
    
    # 休止中でないアトラクションのみ予測
    attractions_to_predict = [a for a in LAND_TARGET_ATTRACTIONS if a not in closures]
    
    # 9:00〜21:00の時間帯
    time_slots = [f"{h:02d}:15" for h in range(9, 21)] + [f"{h:02d}:45" for h in range(9, 21)]
    time_slots = sorted(time_slots)
    
    # 予測実行
    predictions = predictor.predict(
        date=date_str,
        time_slots=time_slots,
        attractions=attractions_to_predict
    )
    
    if predictions is None:
        return None
    
    # 休止中アトラクションを追加（-1で）
    for attraction in closures:
        for time in time_slots:
            predictions = pd.concat([predictions, pd.DataFrame([{
                'date': date_str,
                'time': time,
                'attraction_name': attraction,
                'predicted_wait_time': -1
            }])], ignore_index=True)
    
    # 対象アトラクションのみにフィルタリング
    predictions = predictions[predictions['attraction_name'].isin(LAND_TARGET_ATTRACTIONS)]
    
    # 表示名に変換
    predictions['display_name'] = predictions['attraction_name'].map(LAND_DISPLAY_NAMES)
    
    # 10分単位で繰り上げ
    predictions['wait_rounded'] = predictions['predicted_wait_time'].apply(round_up_to_10)
    
    # ピボットテーブル作成
    pivot = predictions.pivot_table(
        values='wait_rounded',
        index='display_name',
        columns='time',
        aggfunc='mean'
    )
    
    # アトラクション順序を固定
    ordered_attractions = [LAND_DISPLAY_NAMES[a] for a in LAND_TARGET_ATTRACTIONS if a in LAND_DISPLAY_NAMES]
    pivot = pivot.reindex([a for a in ordered_attractions if a in pivot.index])
    
    # ヒートマップ描画
    _create_heatmap_figure(
        pivot, date_str,
        title_prefix="🏰 ディズニーランド",
        output_file=os.path.join(output_dir, f"land_heatmap_{date_str}.png"),
        bg_color='#1a1a2e'  # ダークパープル
    )
    
    print(f"✅ ヒートマップ保存: {output_dir}/land_heatmap_{date_str}.png")
    return os.path.join(output_dir, f"land_heatmap_{date_str}.png")


def _create_heatmap_figure(pivot, date_str, title_prefix, output_file, bg_color='#1a1a2e'):
    """ヒートマップ図を作成"""
    
    day_name = get_day_of_week_ja(date_str)
    
    # カスタムカラーマップ（緑→黄→赤）
    colors_vibrant = [
        '#2ECC71',  # 緑（空いている）
        '#58D68D',  # 明るい緑
        '#F7DC6F',  # 黄色
        '#F5B041',  # オレンジ
        '#E74C3C',  # 赤
        '#C0392B',  # 濃い赤（激混み）
    ]
    custom_cmap = LinearSegmentedColormap.from_list('disney_vibrant', colors_vibrant, N=256)
    
    # 休止中セル用のマスクを作成
    mask = pivot < 0
    
    # 表示用データ（休止中は0にして色なしに）
    display_data = pivot.copy()
    display_data[mask] = np.nan
    
    # 図のサイズを調整（アトラクション数に応じて）
    n_attractions = len(pivot.index)
    fig_height = max(8, n_attractions * 0.8 + 4)
    
    fig, ax = plt.subplots(figsize=(20, fig_height), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    if HAS_SEABORN:
        sns.heatmap(
            display_data,
            ax=ax,
            cmap=custom_cmap,
            annot=False,  # 後で手動で追加
            cbar_kws={'label': '予測待ち時間 (分)', 'shrink': 0.8},
            linewidths=2,
            linecolor=bg_color,
            vmin=0,
            vmax=180,
            mask=mask
        )
        
        # カラーバーのスタイル
        cbar = ax.collections[0].colorbar
        cbar.ax.yaxis.label.set_color('white')
        cbar.ax.tick_params(colors='white')
    
    # セルに数値を表示（手動で）
    for i, row_name in enumerate(pivot.index):
        for j, col_name in enumerate(pivot.columns):
            value = pivot.loc[row_name, col_name]
            if pd.isna(value):
                continue
            
            if value < 0:
                # 休止中
                text = '-1'
                text_color = '#888888'
                fontweight = 'normal'
            else:
                text = f'{int(value)}'
                text_color = 'white' if value > 60 else 'black'
                fontweight = 'bold'
            
            ax.text(
                j + 0.5, i + 0.5, text,
                ha='center', va='center',
                fontsize=9, fontweight=fontweight,
                color=text_color
            )
    
    # タイトル
    ax.set_title(
        f'{title_prefix} AI待ち時間予測\n📅 {date_str} ({day_name}曜日)',
        fontsize=18,
        fontweight='bold',
        color='white',
        pad=20
    )
    ax.set_xlabel('⏰ 時刻', fontsize=12, color='white', fontweight='bold')
    ax.set_ylabel('', fontsize=12)  # Y軸ラベルなし（アトラクション名で十分）
    
    # 軸ラベルの色とサイズ
    ax.tick_params(axis='x', colors='white', labelsize=9, rotation=45)
    ax.tick_params(axis='y', colors='white', labelsize=11)
    
    # 凡例を追加
    legend_labels = ['〜30分', '30〜60分', '60〜90分', '90〜120分', '120分〜']
    legend_colors = ['#2ECC71', '#58D68D', '#F7DC6F', '#F5B041', '#E74C3C']
    patches = [mpatches.Patch(color=c, label=l) for c, l in zip(legend_colors, legend_labels)]
    legend = ax.legend(
        handles=patches,
        loc='upper left',
        bbox_to_anchor=(1.02, 1),
        facecolor='#2d2d44',
        edgecolor='white',
        fontsize=10
    )
    for text in legend.get_texts():
        text.set_color('white')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor=bg_color)
    plt.close()


# ========================================
# メイン処理
# ========================================

def main():
    """メイン処理"""
    print("🎢 X投稿用 TDRヒートマップ生成")
    print("=" * 60)
    
    # 予測対象日を取得（引数があればそれを使用、なければ明日）
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        tomorrow = datetime.now() + timedelta(days=1)
        target_date = tomorrow.strftime('%Y-%m-%d')
    
    print(f"📅 対象日: {target_date}")
    
    # 出力ディレクトリ
    output_dir = "predictions_x"
    os.makedirs(output_dir, exist_ok=True)
    
    # シー ヒートマップ
    sea_file = generate_sea_heatmap(target_date, output_dir)
    
    # ランド ヒートマップ
    land_file = generate_land_heatmap(target_date, output_dir)
    
    print("\n" + "=" * 60)
    print("📁 生成ファイル:")
    if sea_file:
        print(f"   🌊 シー: {sea_file}")
    if land_file:
        print(f"   🏰 ランド: {land_file}")
    
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
