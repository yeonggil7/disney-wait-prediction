#!/usr/bin/env python3
"""
ディズニーシー待ち時間予測 - PDF レポート生成
縦軸：時間、横軸：アトラクションの表形式
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import subprocess

# PDF生成
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# 日本語フォントの設定（macOS用）
from matplotlib import font_manager
# macOSの日本語フォントを探す
font_paths = [
    '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
]
for fp in font_paths:
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        prop = font_manager.FontProperties(fname=fp)
        plt.rcParams['font.family'] = prop.get_name()
        break
else:
    # フォントが見つからない場合
    plt.rcParams['font.family'] = 'sans-serif'

plt.rcParams['axes.unicode_minus'] = False

# 予測システム
try:
    from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3 as Predictor
    MODEL_VERSION = "v3"
except ImportError:
    try:
        from disneysea_wait_time_predictor_v2 import DisneySeaWaitTimePredictorV2 as Predictor
        MODEL_VERSION = "v2"
    except ImportError:
        from disneysea_wait_time_predictor import DisneySeaWaitTimePredictor as Predictor
        MODEL_VERSION = "v1"


def get_day_info(date_str):
    """日付情報を取得"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_name = day_names[date.weekday()]
    
    # 特別日判定
    month, day = date.month, date.day
    special = ""
    if month == 12 and day == 24:
        special = "🎄 クリスマスイブ"
    elif month == 12 and day == 25:
        special = "🎄 クリスマス"
    elif month == 12 and 20 <= day <= 27:
        special = "🎄 クリスマスシーズン"
    elif month == 1 and 1 <= day <= 3:
        special = "🎍 お正月"
    elif month == 10 and day == 31:
        special = "🎃 ハロウィン"
    
    is_weekend = date.weekday() >= 5
    
    return day_name, is_weekend, special


def round_up_to_10(value):
    """10分単位で繰り上げ（例: 23→30, 45→50, 10→10）"""
    if pd.isna(value) or value <= 0:
        return 0
    return int(np.ceil(value / 10) * 10)


def create_wait_time_heatmap(predictions, date_str, ax, title_prefix=""):
    """待ち時間のヒートマップを作成"""
    
    # ピボットテーブル作成（時間×アトラクション）
    pivot = predictions.pivot_table(
        values='predicted_wait_time',
        index='time',
        columns='attraction_name',
        aggfunc='mean'
    )
    
    # 10分単位で繰り上げ
    pivot = pivot.applymap(round_up_to_10)
    
    # アトラクションを平均待ち時間でソート
    col_order = pivot.mean().sort_values(ascending=False).index
    pivot = pivot[col_order]
    
    # カラーマップ
    cmap = plt.cm.YlOrRd
    norm = mcolors.Normalize(vmin=0, vmax=max(150, pivot.max().max()))
    
    # ヒートマップ描画
    im = ax.imshow(pivot.values, cmap=cmap, norm=norm, aspect='auto')
    
    # 軸ラベル
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=90, fontsize=7, ha='center')
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    
    # 数値を表示
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.iloc[i, j]
            if not np.isnan(value):
                text_color = 'white' if value > 75 else 'black'
                ax.text(j, i, f'{value:.0f}', ha='center', va='center', 
                       fontsize=5, color=text_color)
    
    # 日付情報
    day_name, is_weekend, special = get_day_info(date_str)
    
    title = f"{title_prefix}{date_str} ({day_name}曜日)"
    if is_weekend:
        title += " 📅週末"
    if special:
        title += f" {special}"
    
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.set_ylabel('時刻', fontsize=10)
    
    return im, pivot


def create_summary_table(predictions, date_str, ax):
    """サマリーテーブルを作成"""
    
    day_name, is_weekend, special = get_day_info(date_str)
    
    # アトラクション別統計
    stats = predictions.groupby('attraction_name')['predicted_wait_time'].agg(['mean', 'max', 'min'])
    stats = stats.sort_values('mean', ascending=False)
    
    # 10分単位で繰り上げ
    stats['mean'] = stats['mean'].apply(round_up_to_10)
    stats['max'] = stats['max'].apply(round_up_to_10)
    stats['min'] = stats['min'].apply(round_up_to_10)
    
    # 上位15アトラクション
    top_15 = stats.head(15)
    
    ax.axis('off')
    
    # テーブル作成
    cell_text = []
    for name, row in top_15.iterrows():
        # アトラクション名を短縮
        short_name = name[:20] + "..." if len(name) > 20 else name
        cell_text.append([short_name, f"{row['mean']}分", f"{row['max']}分", f"{row['min']}分"])
    
    table = ax.table(
        cellText=cell_text,
        colLabels=['アトラクション', '平均', '最大', '最小'],
        loc='center',
        cellLoc='center',
        colWidths=[0.5, 0.15, 0.15, 0.15]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.5)
    
    # ヘッダーのスタイル
    for i in range(4):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    # 交互の背景色
    for i in range(1, len(cell_text) + 1):
        if i % 2 == 0:
            for j in range(4):
                table[(i, j)].set_facecolor('#E8F0FE')
    
    title = f"人気アトラクション Top 15\n{date_str} ({day_name}曜日)"
    if special:
        title += f" {special}"
    ax.set_title(title, fontsize=11, fontweight='bold', pad=5)


def create_hourly_chart(predictions, date_str, ax):
    """時間帯別チャート"""
    
    predictions = predictions.copy()
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    
    hourly_avg = predictions.groupby('hour')['predicted_wait_time'].mean()
    
    # 10分単位で繰り上げ
    hourly_avg = hourly_avg.apply(round_up_to_10)
    
    colors = ['#2ECC71' if v < 20 else '#F39C12' if v < 40 else '#E74C3C' 
              for v in hourly_avg.values]
    
    bars = ax.bar(hourly_avg.index, hourly_avg.values, color=colors, edgecolor='black', linewidth=0.5)
    
    ax.set_xlabel('Time', fontsize=10)
    ax.set_ylabel('Average Wait Time (min)', fontsize=10)
    ax.set_title('Hourly Average Wait Time', fontsize=11, fontweight='bold')
    ax.set_xticks(range(8, 22))
    ax.set_xticklabels([f'{h}:00' for h in range(8, 22)], rotation=45, fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    
    # 値を表示
    for bar, val in zip(bars, hourly_avg.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
               f'{int(val)}', ha='center', va='bottom', fontsize=7)
    
    # 凡例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ECC71', label='空いている (<20分)'),
        Patch(facecolor='#F39C12', label='普通 (20-35分)'),
        Patch(facecolor='#E74C3C', label='混雑 (>35分)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=7)


def create_recommendations(predictions, date_str, ax):
    """おすすめ情報"""
    
    predictions = predictions.copy()
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    
    day_name, is_weekend, special = get_day_info(date_str)
    
    # 時間帯別平均（10分単位で繰り上げ）
    hourly_avg = predictions.groupby('hour')['predicted_wait_time'].mean().apply(round_up_to_10)
    best_hours = hourly_avg.nsmallest(3)
    worst_hours = hourly_avg.nlargest(3)
    
    # 人気アトラクションの最短時間
    top_attractions = ['ソアリン', 'アナとエルサ', 'ラプンツェル', 
                      'トイストーリーマニア', 'センターオブジアース']
    
    ax.axis('off')
    
    text_lines = []
    text_lines.append(f"{date_str} ({day_name}) Guide")
    if special:
        text_lines.append(f"   {special}")
    text_lines.append("")
    
    text_lines.append("Best Time Slots (Less Crowded):")
    for hour, wait in best_hours.items():
        text_lines.append(f"   {hour:02d}:00 - Avg {int(wait)} min")
    
    text_lines.append("")
    text_lines.append("Avoid (Crowded):")
    for hour, wait in worst_hours.items():
        text_lines.append(f"   {hour:02d}:00 - Avg {int(wait)} min")
    
    text_lines.append("")
    text_lines.append("Popular Attractions - Best Time:")
    for attraction in top_attractions:
        attr_data = predictions[predictions['attraction_name'] == attraction]
        if len(attr_data) > 0:
            best_row = attr_data.loc[attr_data['predicted_wait_time'].idxmin()]
            wait_rounded = round_up_to_10(best_row['predicted_wait_time'])
            text_lines.append(f"   {attraction}:")
            text_lines.append(f"      -> {best_row['time']} ({int(wait_rounded)} min)")
    
    # 天気情報
    if 'temperature' in predictions.columns:
        avg_temp = predictions['temperature'].mean()
        is_rainy = predictions['is_rainy'].max() if 'is_rainy' in predictions.columns else 0
        weather_str = "Rain" if is_rainy else "Sunny"
        text_lines.append("")
        text_lines.append(f"Weather: {avg_temp:.0f}C | {weather_str}")
    
    text = "\n".join(text_lines)
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))


def generate_pdf_report(dates, output_file="predictions/wait_time_report.pdf"):
    """PDFレポートを生成（PNG経由）"""
    
    print(f"📄 PDFレポート生成中...")
    print(f"   対象日: {', '.join(dates)}")
    
    # 予測器を初期化
    predictor = Predictor()
    if not predictor.load_models():
        print("❌ モデルを読み込めません。先にモデルを訓練してください。")
        return None
    
    output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else 'predictions'
    os.makedirs(output_dir, exist_ok=True)
    
    png_files = []
    
    for date in dates:
        print(f"   📅 {date} を処理中...")
        
        # 予測実行
        predictions = predictor.predict(date=date)
        
        if predictions is None:
            print(f"   ⚠️ {date} の予測に失敗しました")
            continue
        
        # ページ1: ヒートマップ（メイン）
        fig = plt.figure(figsize=(20, 12))
        
        # ヒートマップ
        ax1 = fig.add_subplot(111)
        im, pivot = create_wait_time_heatmap(predictions, date, ax1, 
                                              title_prefix="DisneySea Wait Time Prediction ")
        
        # カラーバー
        cbar = fig.colorbar(im, ax=ax1, shrink=0.8, pad=0.02)
        cbar.set_label('Wait Time (min)', fontsize=10)
        
        plt.tight_layout()
        png1 = os.path.join(output_dir, f"temp_heatmap_{date}.png")
        plt.savefig(png1, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        png_files.append(png1)
        
        # ページ2: サマリーと推奨
        fig = plt.figure(figsize=(20, 12))
        
        # サマリーテーブル（左上）
        ax2 = fig.add_subplot(221)
        create_summary_table(predictions, date, ax2)
        
        # 時間帯別チャート（右上）
        ax3 = fig.add_subplot(222)
        create_hourly_chart(predictions, date, ax3)
        
        # おすすめ情報（下半分）
        ax4 = fig.add_subplot(212)
        create_recommendations(predictions, date, ax4)
        
        plt.tight_layout()
        png2 = os.path.join(output_dir, f"temp_summary_{date}.png")
        plt.savefig(png2, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        png_files.append(png2)
    
    # PNGをPDFに結合
    if png_files:
        try:
            from PIL import Image
            
            images = []
            for png_file in png_files:
                img = Image.open(png_file)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                images.append(img)
            
            if images:
                images[0].save(
                    output_file,
                    save_all=True,
                    append_images=images[1:],
                    resolution=150
                )
                print(f"✅ PDFレポート生成完了: {output_file}")
            
            # 一時ファイルを削除
            for png_file in png_files:
                try:
                    os.remove(png_file)
                except:
                    pass
                    
        except ImportError:
            print("⚠️ PILがインストールされていません。PNGファイルのみ生成しました。")
            print(f"   pip install Pillow でインストールしてください")
            return png_files
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='ディズニーシー待ち時間予測PDFレポート生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 1日分のPDFを生成
  python generate_prediction_pdf.py --date 2025-12-25

  # 複数日のPDFを生成
  python generate_prediction_pdf.py --dates 2025-12-24 2025-12-25 2025-12-26

  # 出力ファイル名を指定
  python generate_prediction_pdf.py --date 2025-12-25 --output christmas.pdf
        """
    )
    
    parser.add_argument('--date', '-d', type=str, 
                       help='予測日（単一）')
    parser.add_argument('--dates', nargs='+', type=str,
                       help='予測日（複数）')
    parser.add_argument('--output', '-o', type=str, 
                       default='predictions/wait_time_report.pdf',
                       help='出力PDFファイル名')
    
    args = parser.parse_args()
    
    # 日付リストを構築
    if args.dates:
        dates = args.dates
    elif args.date:
        dates = [args.date]
    else:
        # デフォルト: 今日から1週間
        from datetime import timedelta
        today = datetime.now()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    print("🏰 ディズニーシー待ち時間予測 PDFレポート生成")
    print("=" * 60)
    
    generate_pdf_report(dates, args.output)


if __name__ == "__main__":
    main()

