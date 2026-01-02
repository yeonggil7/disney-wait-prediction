#!/usr/bin/env python3
"""
ディズニーシー待ち時間予測 - コマンドラインインターフェース
任意の日付の待ち時間を予測し、詳細なレポートを生成
モバイル向けPDFガイドも自動生成
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# ================================
# 休止中アトラクション設定
# ================================
# 自動取得を試みる。失敗した場合は手動リストを使用
# 手動で設定する場合: MANUAL_CLOSED_ATTRACTIONS_SEA に追加
MANUAL_CLOSED_ATTRACTIONS_SEA = [
    # 手動で休止中のアトラクションを追加する場合はここに記載
    # 例: 'センターオブジアース',
]

# 公式サイトから休止中アトラクションを自動取得
try:
    from fetch_closed_attractions import get_closed_attractions_sea, normalize_attraction_name
    AUTO_FETCH_CLOSED = True
except ImportError:
    AUTO_FETCH_CLOSED = False
    print("⚠️ fetch_closed_attractions.py が見つかりません。手動リストを使用します。")
    normalize_attraction_name = None


def get_closed_attractions(target_date=None, attraction_list=None):
    """
    休止中アトラクションリストを取得
    
    Args:
        target_date: 対象日付 (YYYY-MM-DD形式)
        attraction_list: 予測システムで使用しているアトラクション名リスト
    
    Returns:
        list: 休止中アトラクション名のリスト（予測システムの名前にマッピング済み）
    """
    if AUTO_FETCH_CLOSED:
        try:
            auto_closed = get_closed_attractions_sea(target_date)
            if auto_closed:
                print(f"📡 公式サイトから休止情報を取得: {len(auto_closed)}件")
                
                # 予測システムの名前にマッピング
                mapped_closed = []
                for name in auto_closed:
                    if attraction_list and normalize_attraction_name:
                        mapped = normalize_attraction_name(name, attraction_list)
                        if mapped:
                            mapped_closed.append(mapped)
                            print(f"   - {name} → {mapped}")
                        else:
                            print(f"   - {name} (マッピングなし)")
                    else:
                        mapped_closed.append(name)
                        print(f"   - {name}")
                
                return mapped_closed
        except Exception as e:
            print(f"⚠️ 自動取得失敗: {e}")
    
    if MANUAL_CLOSED_ATTRACTIONS_SEA:
        print(f"📋 手動リストから休止情報を使用: {len(MANUAL_CLOSED_ATTRACTIONS_SEA)}件")
        return MANUAL_CLOSED_ATTRACTIONS_SEA
    
    return []

# 予測システムをインポート（最新版を優先）
try:
    from disneysea_wait_time_predictor_v3 import DisneySeaWaitTimePredictorV3 as DisneySeaWaitTimePredictor
    WEATHER_INTEGRATED = True
    MODEL_VERSION = "v3"
    MODEL_PATH = "models_v3/wait_time_models.joblib"
except ImportError:
    try:
        from disneysea_wait_time_predictor_v2 import DisneySeaWaitTimePredictorV2 as DisneySeaWaitTimePredictor
        WEATHER_INTEGRATED = True
        MODEL_VERSION = "v2"
        MODEL_PATH = "models_v2/wait_time_models.joblib"
    except ImportError:
        from disneysea_wait_time_predictor import DisneySeaWaitTimePredictor
        WEATHER_INTEGRATED = False
        MODEL_VERSION = "v1"
        MODEL_PATH = "models/wait_time_models.joblib"

# モバイルPDF生成をインポート
try:
    from generate_mobile_pdf import create_timetable_page, create_summary_page, round_up_to_10
    HAS_MOBILE_PDF = True
except ImportError:
    HAS_MOBILE_PDF = False


def mark_closed_attractions(predictions, closed_list):
    """休止中アトラクションをマーク"""
    if not closed_list:
        return predictions
    
    predictions = predictions.copy()
    predictions['is_closed'] = predictions['attraction_name'].isin(closed_list)
    # 休止中のアトラクションは待ち時間を-1に設定（表示時に「-」になる）
    predictions.loc[predictions['is_closed'], 'predicted_wait_time'] = -1
    return predictions

# 可視化ライブラリ
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # GUI不要
    # 日本語フォント設定
    plt.rcParams['font.family'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'sans-serif']
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlibがインストールされていません。グラフ出力は無効です。")

try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


def get_day_of_week_ja(date_str):
    """日本語の曜日を取得"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    days = ['月', '火', '水', '木', '金', '土', '日']
    return days[date.weekday()]


def generate_prediction_report(predictions, date, temperature, is_rainy, output_dir="predictions"):
    """詳細な予測レポートを生成"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    day_name = get_day_of_week_ja(date)
    weather_str = "🌧️ 雨" if is_rainy else "☀️ 晴れ"
    
    report = []
    report.append("=" * 70)
    report.append(f"🏰 ディズニーシー 待ち時間予測レポート")
    report.append("=" * 70)
    report.append(f"📅 日付: {date} ({day_name}曜日)")
    report.append(f"🌡️ 気温: {temperature}℃")
    report.append(f"🌤️ 天気: {weather_str}")
    report.append(f"📊 予測モデル: Gradient Boosting (R²=0.94)")
    report.append("")
    
    # アトラクション別予測
    report.append("-" * 70)
    report.append("📊 アトラクション別 予測待ち時間ランキング")
    report.append("-" * 70)
    
    avg_by_attraction = predictions.groupby('attraction_name').agg({
        'predicted_wait_time': ['mean', 'max', 'min']
    }).round(1)
    avg_by_attraction.columns = ['平均', '最大', '最小']
    avg_by_attraction = avg_by_attraction.sort_values('平均', ascending=False)
    
    report.append(f"{'アトラクション名':<35} {'平均':>8} {'最大':>8} {'最小':>8}")
    report.append("-" * 70)
    
    for name, row in avg_by_attraction.iterrows():
        report.append(f"{name:<35} {row['平均']:>8.1f}分 {row['最大']:>8.1f}分 {row['最小']:>8.1f}分")
    
    # 時間帯別予測
    report.append("")
    report.append("-" * 70)
    report.append("⏰ 時間帯別 平均予測待ち時間")
    report.append("-" * 70)
    
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    avg_by_hour = predictions.groupby('hour')['predicted_wait_time'].mean()
    
    for hour, wait in avg_by_hour.items():
        bar = "█" * int(wait / 5)
        report.append(f"  {hour:02d}時台: {wait:5.1f}分 {bar}")
    
    # おすすめ情報
    report.append("")
    report.append("-" * 70)
    report.append("🎯 おすすめ訪問プラン")
    report.append("-" * 70)
    
    # 空いている時間帯
    best_hours = avg_by_hour.nsmallest(3)
    report.append("\n✅ 空いている時間帯:")
    for hour, wait in best_hours.items():
        report.append(f"   {hour:02d}時台 (平均{wait:.1f}分)")
    
    # 混雑する時間帯
    worst_hours = avg_by_hour.nlargest(3)
    report.append("\n❌ 混雑する時間帯 (避けた方がよい):")
    for hour, wait in worst_hours.items():
        report.append(f"   {hour:02d}時台 (平均{wait:.1f}分)")
    
    # 人気アトラクションの最適時間
    report.append("\n🌟 人気アトラクション攻略:")
    
    top_attractions = ['ソアリン', 'アナとエルサ', 'ラプンツェル', 
                      'トイストーリーマニア', 'センターオブジアース']
    
    for attraction in top_attractions:
        attr_data = predictions[predictions['attraction_name'] == attraction]
        if len(attr_data) > 0:
            best_time = attr_data.loc[attr_data['predicted_wait_time'].idxmin()]
            report.append(f"   {attraction}:")
            report.append(f"     → 最短: {best_time['time']} ({best_time['predicted_wait_time']:.0f}分)")
    
    # エリア別おすすめ順序
    report.append("\n🗺️ エリア別回り方のおすすめ:")
    
    area_mapping = {
        'ファンタジースプリングス': ['アナとエルサ', 'ラプンツェル', 'ピーターパン', 'ティンカーベル'],
        'メディテレーニアンハーバー': ['ソアリン', 'ゴンドラ'],
        'アメリカンウォーターフロント': ['トイストーリーマニア', 'タワーオブテラー', 'タートル・トーク'],
        'ミステリアスアイランド': ['センターオブジアース', '海底二万マイル'],
        'ロストリバーデルタ': ['インディージョーンズクリスタルスカルの謎', 'レイジングスピリッツ']
    }
    
    for area, attractions in area_mapping.items():
        area_data = predictions[predictions['attraction_name'].isin(attractions)]
        if len(area_data) > 0:
            avg_wait = area_data.groupby('hour')['predicted_wait_time'].mean()
            best_hour = avg_wait.idxmin()
            report.append(f"   {area}: {best_hour:02d}時台がおすすめ")
    
    report.append("")
    report.append("=" * 70)
    report.append(f"📝 レポート生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    
    # レポートを保存
    report_text = "\n".join(report)
    report_file = os.path.join(output_dir, f"prediction_report_{date}.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(report_text)
    print(f"\n💾 レポート保存: {report_file}")
    
    return report_text


def generate_heatmap(predictions, date, output_dir="predictions"):
    """待ち時間ヒートマップを生成"""
    
    if not HAS_MATPLOTLIB:
        print("⚠️ matplotlibがないためヒートマップは生成できません")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 9:00〜21:00の時間帯のみにフィルタリング
    predictions_filtered = predictions[
        (predictions['time'] >= '09:00') & 
        (predictions['time'] <= '21:00')
    ].copy()
    
    # ピボットテーブル作成
    pivot = predictions_filtered.pivot_table(
        values='predicted_wait_time',
        index='attraction_name',
        columns='time',
        aggfunc='mean'
    )
    
    # 平均待ち時間でソート
    pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
    
    # ヒートマップ作成
    fig, ax = plt.subplots(figsize=(20, 14))
    
    if HAS_SEABORN:
        sns.heatmap(
            pivot, 
            ax=ax,
            cmap='YlOrRd',
            annot=True,
            fmt='.0f',
            cbar_kws={'label': '予測待ち時間 (分)'},
            linewidths=0.5
        )
    else:
        im = ax.imshow(pivot.values, cmap='YlOrRd', aspect='auto')
        plt.colorbar(im, ax=ax, label='予測待ち時間 (分)')
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
    
    day_name = get_day_of_week_ja(date)
    ax.set_title(f'ディズニーシー 待ち時間予測ヒートマップ\n{date} ({day_name}曜日)', fontsize=16)
    ax.set_xlabel('時刻', fontsize=12)
    ax.set_ylabel('アトラクション', fontsize=12)
    
    plt.tight_layout()
    
    heatmap_file = os.path.join(output_dir, f"prediction_heatmap_{date}.png")
    plt.savefig(heatmap_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📊 ヒートマップ保存: {heatmap_file}")


def generate_hourly_chart(predictions, date, output_dir="predictions"):
    """時間帯別チャートを生成"""
    
    if not HAS_MATPLOTLIB:
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
    
    # 人気アトラクション5つを選択
    top_attractions = predictions.groupby('attraction_name')['predicted_wait_time'].mean()
    top_attractions = top_attractions.nlargest(5).index.tolist()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    for i, attraction in enumerate(top_attractions):
        attr_data = predictions[predictions['attraction_name'] == attraction]
        hourly = attr_data.groupby('hour')['predicted_wait_time'].mean()
        ax.plot(hourly.index, hourly.values, marker='o', linewidth=2.5, 
               label=attraction, color=colors[i])
    
    ax.set_xlabel('時刻', fontsize=12)
    ax.set_ylabel('予測待ち時間 (分)', fontsize=12)
    
    day_name = get_day_of_week_ja(date)
    ax.set_title(f'ディズニーシー 人気アトラクション時間推移予測\n{date} ({day_name}曜日)', fontsize=14)
    
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(8, 22))
    ax.set_xticklabels([f'{h}:00' for h in range(8, 22)], rotation=45)
    
    plt.tight_layout()
    
    chart_file = os.path.join(output_dir, f"prediction_hourly_{date}.png")
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📈 時間推移チャート保存: {chart_file}")


def generate_mobile_pdf(predictions, date, output_dir="predictions"):
    """モバイル向けPDFガイドを生成（2ページ: 時刻表 + サマリー）"""
    
    if not HAS_MOBILE_PDF:
        print("⚠️ モバイルPDF生成モジュールが読み込めません")
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        from PIL import Image
        
        # ページ1: 時刻表
        png1 = os.path.join(output_dir, f"temp_table_{date}.png")
        create_timetable_page(predictions, date, png1)
        
        # ページ2: サマリー
        png2 = os.path.join(output_dir, f"temp_summary_{date}.png")
        create_summary_page(predictions, date, png2)
        
        # 2ページのPDFに結合
        pdf_file = os.path.join(output_dir, f"guide_{date}.pdf")
        
        img1 = Image.open(png1)
        img2 = Image.open(png2)
        
        if img1.mode == 'RGBA':
            img1 = img1.convert('RGB')
        if img2.mode == 'RGBA':
            img2 = img2.convert('RGB')
        
        img1.save(pdf_file, save_all=True, append_images=[img2], resolution=150)
        
        # 一時ファイル削除
        os.remove(png1)
        os.remove(png2)
        
        print(f"📱 モバイルガイドPDF: {pdf_file} (2ページ)")
        return pdf_file
        
    except ImportError:
        # PILがない場合はPNGのみ
        png_file = os.path.join(output_dir, f"guide_{date}.png")
        create_timetable_page(predictions, date, png_file)
        print(f"📱 モバイルガイドPNG: {png_file}")
        return png_file
    except Exception as e:
        print(f"⚠️ モバイルPDF生成エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description='ディズニーシー待ち時間予測システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 明日の予測
  python disneysea_predict_cli.py --date 2025-07-20

  # 特定日の予測（気温・天気指定）
  python disneysea_predict_cli.py --date 2025-08-15 --temperature 32 --rainy

  # 複数日の予測
  python disneysea_predict_cli.py --date 2025-07-20 --days 7

  # グラフなしで予測
  python disneysea_predict_cli.py --date 2025-07-20 --no-charts
        """
    )
    
    parser.add_argument('--date', '-d', type=str, required=True,
                       help='予測日付 (YYYY-MM-DD形式)')
    parser.add_argument('--days', type=int, default=1,
                       help='予測日数（デフォルト: 1日）')
    parser.add_argument('--temperature', '-t', type=float, default=25.0,
                       help='気温（℃）（デフォルト: 25）')
    parser.add_argument('--rainy', action='store_true',
                       help='雨の日として予測')
    parser.add_argument('--no-charts', action='store_true',
                       help='グラフを生成しない')
    parser.add_argument('--pdf', action='store_true',
                       help='モバイル向けPDFガイドを生成（デフォルト: ON）')
    parser.add_argument('--no-pdf', action='store_true',
                       help='PDFガイドを生成しない')
    parser.add_argument('--output', '-o', type=str, default='predictions',
                       help='出力ディレクトリ（デフォルト: predictions）')
    parser.add_argument('--model', '-m', type=str, default='gradient_boosting',
                       choices=['random_forest', 'gradient_boosting', 'lightgbm'],
                       help='使用するモデル（デフォルト: gradient_boosting）')
    parser.add_argument('--train', action='store_true',
                       help='モデルを再訓練する')
    
    args = parser.parse_args()
    
    # 日付のバリデーション
    try:
        start_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ 日付形式が不正です: {args.date}")
        print("   YYYY-MM-DD形式で指定してください（例: 2025-07-20）")
        sys.exit(1)
    
    print("🏰 ディズニーシー待ち時間予測システム")
    print("=" * 60)
    
    # 予測器を初期化
    predictor = DisneySeaWaitTimePredictor()
    
    # モデル訓練（必要な場合）
    print(f"🔧 使用モデル: {MODEL_VERSION}")
    if args.train or not os.path.exists(MODEL_PATH):
        print("\n📚 モデル訓練中...")
        predictor.train()
    else:
        predictor.load_models()
    
    # 予測日のリスト
    dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
             for i in range(args.days)]
    
    for date in dates:
        print(f"\n{'='*60}")
        print(f"🔮 {date} の予測実行中...")
        
        # 日付ディレクトリを作成
        date_output_dir = os.path.join(args.output, date)
        os.makedirs(date_output_dir, exist_ok=True)
        
        # 予測実行（天気統合版とオリジナル版で呼び出し方法が異なる）
        if WEATHER_INTEGRATED:
            predictions = predictor.predict(
                date=date,
                model_name=args.model
            )
            # 天気情報を抽出
            if predictions is not None and 'temperature' in predictions.columns:
                temperature = predictions['temperature'].mean()
                is_rainy = predictions['is_rainy'].max() if 'is_rainy' in predictions.columns else 0
            else:
                temperature = args.temperature
                is_rainy = args.rainy
        else:
            predictions = predictor.predict(
                date=date,
                temperature=args.temperature,
                is_rainy=args.rainy,
                model_name=args.model
            )
            temperature = args.temperature
            is_rainy = args.rainy
        
        if predictions is not None:
            # 予測に含まれるアトラクション名リストを取得
            attraction_list = predictions['attraction_name'].unique().tolist()
            
            # 休止中アトラクションを取得してマーク
            closed_list = get_closed_attractions(target_date=date, attraction_list=attraction_list)
            predictions = mark_closed_attractions(predictions, closed_list)
            
            # レポート生成
            generate_prediction_report(
                predictions, date, 
                temperature, is_rainy,
                date_output_dir
            )
            
            # モバイルPDFガイド生成（デフォルトでON）
            if not args.no_pdf and HAS_MOBILE_PDF:
                generate_mobile_pdf(predictions, date, date_output_dir)
            
            # グラフ生成
            if not args.no_charts and HAS_MATPLOTLIB:
                generate_heatmap(predictions, date, date_output_dir)
                generate_hourly_chart(predictions, date, date_output_dir)
            
            # CSVエクスポート
            csv_file = os.path.join(date_output_dir, f"prediction_{date}.csv")
            predictions.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"💾 CSV保存: {csv_file}")
            
            print(f"📁 出力先: {date_output_dir}/")
    
    print(f"\n✅ 予測完了！結果は {args.output}/<日付>/ フォルダに保存されました。")


if __name__ == "__main__":
    main()

