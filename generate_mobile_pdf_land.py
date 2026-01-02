#!/usr/bin/env python3
"""
ディズニーランド待ち時間予測 - モバイル向けPDFレポート
パークを回っている時に見やすいコンパクトな形式
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import font_manager

# フォント設定
font_paths = [
    '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
]
for fp in font_paths:
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        prop = font_manager.FontProperties(fname=fp)
        plt.rcParams['font.family'] = prop.get_name()
        break

plt.rcParams['axes.unicode_minus'] = False

# 予測システム
try:
    from disneyland_wait_time_predictor_v3 import DisneyLandWaitTimePredictorV3 as Predictor
except ImportError:
    from disneyland_wait_time_predictor_v2 import DisneySeaWaitTimePredictorV2 as Predictor


def round_up_to_10(value):
    """10分単位で繰り上げ（-1は休止中として維持）"""
    if pd.isna(value):
        return 0
    if value < 0:  # 休止中
        return -1
    if value == 0:
        return 0
    return int(np.ceil(value / 10) * 10)


def get_day_info(date_str):
    """日付情報を取得"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day_names_ja = ['月', '火', '水', '木', '金', '土', '日']
    day_name_ja = day_names_ja[date.weekday()]
    
    month, day = date.month, date.day
    special = ""
    if month == 12 and day == 24:
        special = "🎄 Christmas Eve"
    elif month == 12 and day == 25:
        special = "🎄 Christmas"
    elif month == 12 and 20 <= day <= 27:
        special = "🎄 Holiday Season"
    elif month == 1 and 1 <= day <= 3:
        special = "🎍 New Year"
    elif month == 10 and day == 31:
        special = "🎃 Halloween"
    
    is_weekend = date.weekday() >= 5
    
    return day_name_ja, is_weekend, special


def get_wait_color(wait):
    """待ち時間に応じた色を返す"""
    if pd.isna(wait):
        return '#ffffff'  # 白
    if wait < 0:  # 休止中
        return '#e0e0e0'  # グレー（休止中）
    if wait == 0:
        return '#ffffff'  # 白（データなし）
    elif wait < 15:
        return '#e8f5e9'  # 薄緑（空いている）
    elif wait < 30:
        return '#c8e6c9'  # 緑
    elif wait < 45:
        return '#fff9c4'  # 薄黄色
    elif wait < 60:
        return '#ffe082'  # 黄色
    elif wait < 90:
        return '#ffcc80'  # オレンジ
    elif wait < 120:
        return '#ffab91'  # 薄赤
    else:
        return '#ef9a9a'  # 赤（非常に混雑）


def get_wait_text_color(wait):
    """待ち時間に応じたテキスト色"""
    if wait >= 90:
        return '#b71c1c'  # 濃い赤
    elif wait >= 60:
        return '#e65100'  # 濃いオレンジ
    else:
        return '#212121'  # 黒


# アトラクション短縮名マッピング
ATTRACTION_SHORT_NAMES = {
    'ソアリン': 'ソアリン',
    'アナとエルサ': 'アナエルサ',
    'ラプンツェル': 'ラプンツェル',
    'ピーターパン': 'ピーターパン',
    'ティンカーベル': 'ティンカー',
    'トイストーリーマニア': 'トイマニ',
    'タワーオブテラー': 'タワテラ',
    'センターオブジアース': 'センター',
    'インディージョーンズクリスタルスカルの謎': 'インディ',
    'レイジングスピリッツ': 'レイジング',
    '海底二万マイル': '海底2万',
    'ニモandフレンズシーライダー': 'ニモ',
    'タートル・トーク': 'タートル',
    'マジックランプシアター': 'ランプ',
    'シンドバッド': 'シンドバッド',
    'ゴンドラ': 'ゴンドラ',
    'アクアトピア': 'アクア',
    'ジャスミン': 'ジャスミン',
    'フランダー': 'フランダー',
    'スカットルのスクーター': 'スカットル',
    'ジャンピン': 'ジャンピン',
    'マーメイドラグーン': 'マーメイド',
    'ワールプール': 'ワールプ',
    'カルーセル': 'カルーセル',
    'バルーンレース': 'バルーン',
    'フォートレスエクスプロレーション': 'フォート',
    'ヴィークル': 'ヴィークル',
    '船メディテレーニアンハーバー発': '船メディ',
    '船ロストリバーデルタ発': '船ロスト',
    '船アメリカンウォーターフロント発': '船アメリカ',
    '鉄道ポートディスカバリー発': '鉄道ポート',
    'エレクトリックレールウェイアメリカンウォーターフロント発': '鉄道アメリカ',
    'ミッキーグリーティング': 'ミキグリ',
    'ミニーグリーティング': 'ミニグリ',
    'ドナルドグリーティング': 'ドナグリ',
    'プラザグリーティング': 'プラザグリ',
    'ヴィレッジグリーティング': 'ヴィレグリ',
    'アラビアンコーストグリーティング': 'アラビアグリ',
    'マーメイドラグーングリーティング': 'マメグリ',
    'サルードス・アミーゴス': 'サルードス',
}


def get_short_name(name):
    """アトラクション名を短縮"""
    if name in ATTRACTION_SHORT_NAMES:
        return ATTRACTION_SHORT_NAMES[name]
    # 10文字以上なら短縮
    if len(name) > 8:
        return name[:7] + '..'
    return name


def create_timetable_page(predictions, date_str, output_file):
    """時間×アトラクション表を生成（1ページ目）"""
    
    day_name_ja, is_weekend, special = get_day_info(date_str)
    predictions = predictions.copy()
    
    # 天気情報
    avg_temp = predictions['temperature'].mean() if 'temperature' in predictions.columns else 20
    is_rainy = predictions['is_rainy'].max() if 'is_rainy' in predictions.columns else 0
    weather_icon = "🌧" if is_rainy else "☀"
    
    # ピボットテーブル作成
    pivot = predictions.pivot_table(
        values='predicted_wait_time',
        index='time',
        columns='attraction_name',
        aggfunc='mean'
    )
    
    # 10分単位に繰り上げ
    pivot = pivot.applymap(round_up_to_10)
    
    # アトラクションを平均待ち時間でソート（多い順）
    avg_wait = pivot.mean().sort_values(ascending=False)
    pivot = pivot[avg_wait.index]
    
    # 時間をソート
    pivot = pivot.sort_index()
    
    # 9:00〜21:00の範囲にフィルタリング
    pivot = pivot[pivot.index >= '09:00']
    pivot = pivot[pivot.index <= '21:00']
    
    n_times = len(pivot.index)
    n_attractions = len(pivot.columns)
    
    # 図のサイズ計算（横長で全アトラクション表示）
    fig_width = max(20, n_attractions * 0.55 + 2)
    fig_height = max(14, n_times * 0.38 + 3)
    
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor='white')
    
    # ヘッダー
    ax_header = fig.add_axes([0.02, 0.94, 0.96, 0.05])
    ax_header.axis('off')
    ax_header.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor='#1565c0', 
                                        edgecolor='none', transform=ax_header.transAxes))
    
    title = f"🏰 DisneyLand 待ち時間予測  {date_str} ({day_name_ja}) {weather_icon}{avg_temp:.0f}°C"
    if special:
        title += f"  {special}"
    ax_header.text(0.5, 0.5, title, fontsize=16, fontweight='bold', 
                   ha='center', va='center', color='white')
    
    # メイン表
    ax_table = fig.add_axes([0.08, 0.06, 0.90, 0.86])
    ax_table.axis('off')
    
    # セルサイズ
    cell_width = 0.95 / (n_attractions + 1)  # +1 for time column
    cell_height = 0.95 / (n_times + 2)  # +2 for header rows
    
    # ヘッダー行（アトラクション名を縦書き風に）
    for j, attr_name in enumerate(pivot.columns):
        x = 0.05 + (j + 1) * cell_width
        y = 0.97 - cell_height
        
        # ヘッダー背景
        avg = avg_wait[attr_name]
        header_color = '#e3f2fd' if avg < 30 else '#fff3e0' if avg < 60 else '#ffebee'
        ax_table.add_patch(plt.Rectangle((x, y), cell_width * 0.95, cell_height * 1.8, 
                                          facecolor=header_color, edgecolor='#90a4ae', 
                                          linewidth=0.5, transform=ax_table.transAxes))
        
        # アトラクション名（短縮）
        short_name = get_short_name(attr_name)
        ax_table.text(x + cell_width * 0.45, y + cell_height * 0.9, short_name, 
                     fontsize=7, ha='center', va='center', rotation=60,
                     fontweight='bold', color='#37474f')
    
    # 平均列ヘッダー
    ax_table.add_patch(plt.Rectangle((0.05 + (n_attractions + 1) * cell_width, 0.97 - cell_height), 
                                      cell_width * 0.95, cell_height * 1.8, 
                                      facecolor='#ffeb3b', edgecolor='#90a4ae', 
                                      linewidth=0.5, transform=ax_table.transAxes))
    ax_table.text(0.05 + (n_attractions + 1.45) * cell_width, 0.97 - cell_height * 0.1, 
                 '平均', fontsize=8, ha='center', va='center', fontweight='bold', color='#212121')
    
    # データ行
    for i, time_slot in enumerate(pivot.index):
        y = 0.95 - (i + 2) * cell_height
        
        # 時間列
        ax_table.add_patch(plt.Rectangle((0.01, y), cell_width * 0.9, cell_height * 0.95, 
                                          facecolor='#eceff1', edgecolor='#90a4ae', 
                                          linewidth=0.5, transform=ax_table.transAxes))
        ax_table.text(0.01 + cell_width * 0.45, y + cell_height * 0.45, time_slot, 
                     fontsize=8, ha='center', va='center', fontweight='bold', color='#37474f')
        
        # 待ち時間セル
        row_values = []
        for j, attr_name in enumerate(pivot.columns):
            x = 0.05 + (j + 1) * cell_width
            wait = pivot.loc[time_slot, attr_name]
            row_values.append(wait)
            
            # セル背景色
            bg_color = get_wait_color(wait)
            ax_table.add_patch(plt.Rectangle((x, y), cell_width * 0.95, cell_height * 0.95, 
                                              facecolor=bg_color, edgecolor='#bdbdbd', 
                                              linewidth=0.3, transform=ax_table.transAxes))
            
            # 待ち時間テキスト
            if wait > 0:
                text_color = get_wait_text_color(wait)
                fontsize = 9 if wait < 100 else 8
                ax_table.text(x + cell_width * 0.45, y + cell_height * 0.45, 
                             f'{int(wait)}', fontsize=fontsize, ha='center', va='center',
                             fontweight='bold', color=text_color)
            elif wait < 0:  # 休止中
                ax_table.text(x + cell_width * 0.45, y + cell_height * 0.45, 
                             '-', fontsize=10, ha='center', va='center', color='#757575', fontweight='bold')
            else:
                ax_table.text(x + cell_width * 0.45, y + cell_height * 0.45, 
                             '-', fontsize=8, ha='center', va='center', color='#9e9e9e')
        
        # 行平均
        row_avg = int(np.mean([v for v in row_values if v > 0])) if any(v > 0 for v in row_values) else 0
        x_avg = 0.05 + (n_attractions + 1) * cell_width
        bg_avg = get_wait_color(row_avg)
        ax_table.add_patch(plt.Rectangle((x_avg, y), cell_width * 0.95, cell_height * 0.95, 
                                          facecolor=bg_avg, edgecolor='#90a4ae', 
                                          linewidth=0.5, transform=ax_table.transAxes))
        ax_table.text(x_avg + cell_width * 0.45, y + cell_height * 0.45, 
                     f'{row_avg}', fontsize=9, ha='center', va='center',
                     fontweight='bold', color=get_wait_text_color(row_avg))
    
    # 平均行
    y_avg = 0.95 - (n_times + 2) * cell_height
    ax_table.add_patch(plt.Rectangle((0.01, y_avg), cell_width * 0.9, cell_height * 0.95, 
                                      facecolor='#ffeb3b', edgecolor='#90a4ae', 
                                      linewidth=0.5, transform=ax_table.transAxes))
    ax_table.text(0.01 + cell_width * 0.45, y_avg + cell_height * 0.45, '平均', 
                 fontsize=8, ha='center', va='center', fontweight='bold')
    
    for j, attr_name in enumerate(pivot.columns):
        x = 0.05 + (j + 1) * cell_width
        col_avg = int(avg_wait[attr_name])
        bg_avg = get_wait_color(col_avg)
        ax_table.add_patch(plt.Rectangle((x, y_avg), cell_width * 0.95, cell_height * 0.95, 
                                          facecolor=bg_avg, edgecolor='#90a4ae', 
                                          linewidth=0.5, transform=ax_table.transAxes))
        ax_table.text(x + cell_width * 0.45, y_avg + cell_height * 0.45, 
                     f'{col_avg}', fontsize=9, ha='center', va='center',
                     fontweight='bold', color=get_wait_text_color(col_avg))
    
    # 凡例
    ax_legend = fig.add_axes([0.02, 0.01, 0.96, 0.04])
    ax_legend.axis('off')
    
    legend_items = [
        ('休止', '#e0e0e0'), ('<15分', '#e8f5e9'), ('15-30分', '#c8e6c9'), ('30-45分', '#fff9c4'),
        ('45-60分', '#ffe082'), ('60-90分', '#ffcc80'), ('90-120分', '#ffab91'), ('120分+', '#ef9a9a')
    ]
    
    for i, (label, color) in enumerate(legend_items):
        x = 0.02 + i * 0.12
        ax_legend.add_patch(plt.Rectangle((x, 0.3), 0.03, 0.5, 
                                           facecolor=color, edgecolor='#9e9e9e', 
                                           linewidth=0.5, transform=ax_legend.transAxes))
        ax_legend.text(x + 0.04, 0.55, label, fontsize=8, va='center', color='#424242')
    
    # 保存
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    print(f"📊 時刻表ページ生成: {output_file}")
    return output_file


def create_summary_page(predictions, date_str, output_file):
    """サマリーページを生成（2ページ目）"""
    
    day_name_ja, is_weekend, special = get_day_info(date_str)
    predictions = predictions.copy()
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    
    # 天気情報
    avg_temp = predictions['temperature'].mean() if 'temperature' in predictions.columns else 20
    is_rainy = predictions['is_rainy'].max() if 'is_rainy' in predictions.columns else 0
    weather_icon = "🌧" if is_rainy else "☀"
    
    # 統計計算（休止中を除外）
    active_predictions = predictions[predictions['predicted_wait_time'] >= 0]
    stats = active_predictions.groupby('attraction_name')['predicted_wait_time'].agg(['mean', 'min'])
    stats['mean'] = stats['mean'].apply(round_up_to_10)
    stats['min'] = stats['min'].apply(round_up_to_10)
    stats = stats.sort_values('mean', ascending=False)
    
    # 休止中アトラクションリスト
    closed_attractions = predictions[predictions['predicted_wait_time'] < 0]['attraction_name'].unique().tolist()
    
    # 最短時間（休止中を除外）
    best_times = active_predictions.loc[active_predictions.groupby('attraction_name')['predicted_wait_time'].idxmin()]
    best_times = best_times.set_index('attraction_name')['time']
    
    # 時間帯別平均（休止中を除外）
    hourly_avg = active_predictions.groupby('hour')['predicted_wait_time'].mean().apply(round_up_to_10)
    best_hours = hourly_avg.nsmallest(3).index.tolist()
    
    # スマホ縦向きサイズ
    fig = plt.figure(figsize=(9, 16), facecolor='#f5f5f5')
    
    # ヘッダー
    ax_header = fig.add_axes([0.02, 0.94, 0.96, 0.055])
    ax_header.axis('off')
    ax_header.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor='#1a237e', 
                                        edgecolor='none', transform=ax_header.transAxes))
    
    header_text = f"🏰 DisneyLand Summary"
    ax_header.text(0.5, 0.65, header_text, fontsize=22, fontweight='bold', 
                   ha='center', va='center', color='white')
    
    date_display = f"{date_str} ({day_name_ja}) {weather_icon}{avg_temp:.0f}°C"
    if special:
        date_display += f"  {special}"
    ax_header.text(0.5, 0.15, date_display, fontsize=13, ha='center', va='center', color='#e3f2fd')
    
    # BEST TIME
    ax_best = fig.add_axes([0.02, 0.87, 0.96, 0.065])
    ax_best.axis('off')
    ax_best.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor='#e8f5e9', 
                                      edgecolor='#4caf50', linewidth=3, transform=ax_best.transAxes))
    
    ax_best.text(0.5, 0.75, "🎯 BEST TIME", fontsize=16, fontweight='bold', 
                 ha='center', va='center', color='#2e7d32')
    
    best_text = "  |  ".join([f"{h}時台 ({int(hourly_avg[h])}分)" for h in best_hours])
    ax_best.text(0.5, 0.3, best_text, fontsize=14, fontweight='bold',
                 ha='center', va='center', color='#1b5e20')
    
    # TOP 10
    ax_top = fig.add_axes([0.02, 0.51, 0.96, 0.35])
    ax_top.axis('off')
    
    ax_top.add_patch(plt.Rectangle((0, 0.93), 1, 0.07, facecolor='#1565c0', 
                                    edgecolor='none', transform=ax_top.transAxes))
    ax_top.text(0.5, 0.965, "🏆 TOP 10 混雑アトラクション", fontsize=15, fontweight='bold', 
                ha='center', va='center', color='white')
    
    top_10 = stats.head(10)
    y_step = 0.088
    
    for i, (name, row) in enumerate(top_10.iterrows(), 1):
        y_pos = 0.87 - (i - 1) * y_step
        
        bg_color = get_wait_color(row['mean'])
        ax_top.add_patch(plt.Rectangle((0.01, y_pos - 0.035), 0.98, 0.075, 
                                        facecolor=bg_color, edgecolor='#e0e0e0', 
                                        linewidth=1, transform=ax_top.transAxes))
        
        rank_colors = ['#ffd700', '#c0c0c0', '#cd7f32']
        rank_color = rank_colors[i-1] if i <= 3 else '#424242'
        ax_top.text(0.04, y_pos, f"{i}", fontsize=16, fontweight='bold', 
                   ha='center', va='center', color=rank_color)
        
        short_name = name[:16] + ".." if len(name) > 16 else name
        ax_top.text(0.08, y_pos, short_name, fontsize=12, fontweight='bold', 
                   ha='left', va='center', color='#212121')
        
        wait_color = get_wait_text_color(row['mean'])
        ax_top.text(0.7, y_pos, f"{int(row['mean'])}", fontsize=18, 
                   fontweight='bold', ha='center', va='center', color=wait_color)
        ax_top.text(0.77, y_pos, "分", fontsize=10, ha='left', va='center', color='#616161')
        
        best_time = best_times.get(name, "")
        if best_time:
            ax_top.text(0.92, y_pos, f"Best {best_time}", fontsize=9, 
                       ha='center', va='center', color='#1565c0', fontweight='bold')
    
    # 時間帯別バー
    ax_hourly = fig.add_axes([0.02, 0.38, 0.96, 0.12])
    ax_hourly.axis('off')
    
    ax_hourly.add_patch(plt.Rectangle((0, 0.8), 1, 0.2, facecolor='#7b1fa2', 
                                        edgecolor='none', transform=ax_hourly.transAxes))
    ax_hourly.text(0.5, 0.88, "⏰ 時間帯別 混雑予想", fontsize=14, fontweight='bold', 
                   ha='center', va='center', color='white')
    
    hours = list(range(9, 22))  # 9:00〜21:00
    bar_width = 0.07
    max_wait = max(hourly_avg.values) if len(hourly_avg) > 0 else 60
    
    for i, hour in enumerate(hours):
        wait = hourly_avg.get(hour, 0)
        color = get_wait_color(wait)
        
        x_pos = 0.03 + i * bar_width
        bar_height = min(wait / max_wait, 1.0) * 0.45
        
        ax_hourly.add_patch(plt.Rectangle((x_pos, 0.25), bar_width * 0.85, bar_height, 
                                           facecolor=color, edgecolor='white', 
                                           linewidth=0.5, transform=ax_hourly.transAxes))
        
        ax_hourly.text(x_pos + bar_width * 0.4, 0.15, f"{hour}", fontsize=9, 
                       ha='center', va='top', color='#424242', fontweight='bold')
        
        ax_hourly.text(x_pos + bar_width * 0.4, 0.25 + bar_height + 0.03, f"{int(wait)}", 
                       fontsize=8, ha='center', va='bottom', color='#424242')
    
    # 全アトラクション一覧
    ax_all = fig.add_axes([0.02, 0.01, 0.96, 0.36])
    ax_all.axis('off')
    
    ax_all.add_patch(plt.Rectangle((0, 0.95), 1, 0.05, facecolor='#546e7a', 
                                    edgecolor='none', transform=ax_all.transAxes))
    ax_all.text(0.5, 0.975, "📋 全アトラクション待ち時間（平均）", fontsize=13, fontweight='bold', 
                ha='center', va='center', color='white')
    
    all_attractions = stats.reset_index()
    n_items = len(all_attractions)
    n_per_col = (n_items + 1) // 2
    
    col_width = 0.48
    row_height = 0.043
    
    for idx, row in all_attractions.iterrows():
        col = 0 if idx < n_per_col else 1
        row_idx = idx if col == 0 else idx - n_per_col
        
        x_base = 0.01 + col * 0.5
        y_pos = 0.90 - row_idx * row_height
        
        if y_pos < 0.02:
            break
        
        bg_color = get_wait_color(row['mean'])
        ax_all.add_patch(plt.Rectangle((x_base, y_pos - 0.018), col_width, 0.038, 
                                        facecolor=bg_color, edgecolor='#e0e0e0', 
                                        linewidth=0.5, transform=ax_all.transAxes))
        
        name = row['attraction_name']
        short_name = name[:12] + ".." if len(name) > 12 else name
        ax_all.text(x_base + 0.01, y_pos, short_name, fontsize=9, ha='left', va='center')
        
        wait = int(row['mean'])
        wait_color = get_wait_text_color(wait)
        ax_all.text(x_base + col_width - 0.03, y_pos, f"{wait}分", fontsize=10, 
                   fontweight='bold', ha='right', va='center', color=wait_color)
        
        best_time = best_times.get(name, "")
        if best_time:
            ax_all.text(x_base + col_width - 0.01, y_pos - 0.01, f"({best_time})", 
                       fontsize=6, ha='right', va='top', color='#757575')
    
    plt.savefig(output_file, dpi=180, bbox_inches='tight', facecolor='#f5f5f5')
    plt.close(fig)
    
    print(f"📱 サマリーページ生成: {output_file}")
    return output_file


def create_mobile_report(predictions, date_str, output_file):
    """後方互換用のラッパー"""
    return create_summary_page(predictions, date_str, output_file)


def predict_and_generate_pdf(date_str, output_dir="predictions"):
    """予測を実行してPDFを生成"""
    
    print(f"\n🔮 {date_str} の予測とPDF生成")
    print("=" * 50)
    
    predictor = Predictor()
    if not predictor.load_models():
        print("❌ モデルを読み込めません")
        return None
    
    predictions = predictor.predict(date=date_str)
    
    if predictions is None:
        print(f"❌ {date_str} の予測に失敗しました")
        return None
    
    # 日付ディレクトリを作成
    date_output_dir = os.path.join(output_dir, date_str)
    os.makedirs(date_output_dir, exist_ok=True)
    
    try:
        from PIL import Image
        
        # ページ1: 時刻表
        png1 = os.path.join(date_output_dir, f"temp_table_{date_str}.png")
        create_timetable_page(predictions, date_str, png1)
        
        # ページ2: サマリー
        png2 = os.path.join(date_output_dir, f"temp_summary_{date_str}.png")
        create_summary_page(predictions, date_str, png2)
        
        # 2ページのPDFに結合
        pdf_file = os.path.join(date_output_dir, f"guide_{date_str}.pdf")
        
        img1 = Image.open(png1)
        img2 = Image.open(png2)
        
        if img1.mode == 'RGBA':
            img1 = img1.convert('RGB')
        if img2.mode == 'RGBA':
            img2 = img2.convert('RGB')
        
        img1.save(pdf_file, save_all=True, append_images=[img2], resolution=150)
        
        os.remove(png1)
        os.remove(png2)
        
        print(f"✅ PDF生成完了: {pdf_file} (2ページ)")
        print(f"📁 出力先: {date_output_dir}/")
        
    except ImportError:
        png_file = os.path.join(date_output_dir, f"guide_{date_str}.png")
        create_timetable_page(predictions, date_str, png_file)
        print(f"✅ PNG生成完了: {png_file}")
        return png_file
    
    # サマリー表示
    day_name_ja, is_weekend, special = get_day_info(date_str)
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    hourly_avg = predictions.groupby('hour')['predicted_wait_time'].mean().apply(round_up_to_10)
    best_hours = hourly_avg.nsmallest(3)
    
    print(f"\n📊 {date_str} ({day_name_ja}曜日) サマリー")
    if special:
        print(f"   {special}")
    print(f"\n🎯 おすすめ時間帯:")
    for hour, wait in best_hours.items():
        print(f"   {hour:02d}時台: 平均{int(wait)}分")
    
    stats = predictions.groupby('attraction_name')['predicted_wait_time'].mean().apply(round_up_to_10)
    stats = stats.sort_values(ascending=False)
    print(f"\n🏆 混雑アトラクション TOP 5:")
    for i, (name, wait) in enumerate(stats.head(5).items(), 1):
        print(f"   {i}. {name}: {int(wait)}分")
    
    return pdf_file


def main():
    parser = argparse.ArgumentParser(
        description='ディズニーランド待ち時間予測 モバイルPDF生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python generate_mobile_pdf.py --date 2025-12-25
  python generate_mobile_pdf.py --dates 2025-12-24 2025-12-25 2025-12-26
        """
    )
    
    parser.add_argument('--date', '-d', type=str, help='予測日（単一）')
    parser.add_argument('--dates', nargs='+', type=str, help='予測日（複数）')
    parser.add_argument('--output', '-o', type=str, default='predictions', help='出力ディレクトリ')
    
    args = parser.parse_args()
    
    if args.dates:
        dates = args.dates
    elif args.date:
        dates = [args.date]
    else:
        dates = [datetime.now().strftime("%Y-%m-%d")]
    
    print("🏰 ディズニーランド待ち時間予測 - モバイルPDF生成")
    print("=" * 50)
    
    for date in dates:
        predict_and_generate_pdf(date, args.output)
    
    print(f"\n✅ 完了！PDFは {args.output}/<日付>/ フォルダに保存されました")


if __name__ == "__main__":
    main()
