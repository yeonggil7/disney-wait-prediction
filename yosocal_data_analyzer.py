#!/usr/bin/env python3
"""
yosocal.com データ分析ユーティリティ
取得した待ち時間データの分析・可視化・レポート生成
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import glob
import argparse
from datetime import datetime
import json

# 日本語フォント設定
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Hiragino Sans']
plt.rcParams['axes.unicode_minus'] = False

class YosocalDataAnalyzer:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.monthly_data = None
        self.daily_data = {}
        
    def load_monthly_data(self, filename=None):
        """月間統合データを読み込み"""
        if filename:
            filepath = os.path.join(self.data_dir, filename)
        else:
            # 最新の月間ファイルを自動検出
            pattern = os.path.join(self.data_dir, "yosocal_monthly_*.csv")
            files = glob.glob(pattern)
            if not files:
                raise FileNotFoundError("月間データファイルが見つかりません")
            filepath = max(files, key=os.path.getctime)
        
        print(f"📊 データ読み込み中: {os.path.basename(filepath)}")
        self.monthly_data = pd.read_csv(filepath)
        self.monthly_data['date'] = pd.to_datetime(self.monthly_data['date'])
        self.monthly_data['datetime'] = pd.to_datetime(self.monthly_data['date'].astype(str) + ' ' + self.monthly_data['time'])
        
        print(f"✅ {len(self.monthly_data):,}レコード読み込み完了")
        return self.monthly_data
    
    def load_daily_files(self):
        """日別ファイルを読み込み"""
        pattern = os.path.join(self.data_dir, "yosocal_daily_*.csv")
        files = glob.glob(pattern)
        
        print(f"📁 {len(files)}個の日別ファイルを読み込み中...")
        
        for file in files:
            basename = os.path.basename(file)
            date_str = basename.replace("yosocal_daily_", "").replace(".csv", "")
            try:
                df = pd.read_csv(file)
                self.daily_data[date_str] = df
            except Exception as e:
                print(f"❌ {basename} 読み込みエラー: {e}")
        
        print(f"✅ {len(self.daily_data)}日分のデータ読み込み完了")
        return self.daily_data
    
    def generate_popularity_ranking(self):
        """人気アトラクションランキング生成"""
        if self.monthly_data is None:
            raise ValueError("データが読み込まれていません")
        
        # 平均待ち時間でランキング
        ranking = self.monthly_data.groupby('attraction_name')['wait_time'].agg(['mean', 'max', 'count']).round(1)
        ranking = ranking.sort_values('mean', ascending=False)
        ranking.columns = ['平均待ち時間', '最大待ち時間', 'データ数']
        
        print("\n🎢 アトラクション人気ランキング（平均待ち時間）")
        print("=" * 60)
        for i, (attraction, data) in enumerate(ranking.head(15).iterrows(), 1):
            print(f"{i:2d}. {attraction:<20} {data['平均待ち時間']:>6.1f}分 (最大: {data['最大待ち時間']:>3.0f}分)")
        
        return ranking
    
    def analyze_time_patterns(self):
        """時間帯別パターン分析"""
        if self.monthly_data is None:
            raise ValueError("データが読み込まれていません")
        
        # 時間帯別平均待ち時間
        time_pattern = self.monthly_data.groupby('time')['wait_time'].mean().round(1)
        
        print("\n⏰ 時間帯別平均待ち時間パターン")
        print("=" * 50)
        
        # ピーク時間を特定
        peak_time = time_pattern.idxmax()
        peak_wait = time_pattern.max()
        quiet_time = time_pattern.idxmin()
        quiet_wait = time_pattern.min()
        
        print(f"🔥 最混雑時間: {peak_time} ({peak_wait:.1f}分)")
        print(f"😌 最空いている時間: {quiet_time} ({quiet_wait:.1f}分)")
        
        print("\n時間帯別詳細:")
        for time, wait in time_pattern.items():
            status = "🔥" if wait > 20 else "😐" if wait > 10 else "😌"
            print(f"  {time}: {wait:>5.1f}分 {status}")
        
        return time_pattern
    
    def analyze_daily_trends(self):
        """日別トレンド分析"""
        if self.monthly_data is None:
            raise ValueError("データが読み込まれていません")
        
        daily_avg = self.monthly_data.groupby('date')['wait_time'].mean().round(1)
        
        print("\n📅 日別平均待ち時間トレンド")
        print("=" * 50)
        
        # 曜日別パターン
        daily_avg_with_dow = daily_avg.to_frame('avg_wait')
        daily_avg_with_dow['dayofweek'] = daily_avg_with_dow.index.dayofweek
        daily_avg_with_dow['day_name'] = daily_avg_with_dow.index.strftime('%A')
        
        dow_pattern = daily_avg_with_dow.groupby('day_name')['avg_wait'].mean().round(1)
        
        # 曜日名を日本語化
        dow_jp = {
            'Monday': '月曜日', 'Tuesday': '火曜日', 'Wednesday': '水曜日',
            'Thursday': '木曜日', 'Friday': '金曜日', 'Saturday': '土曜日', 'Sunday': '日曜日'
        }
        
        print("曜日別パターン:")
        for eng_day, avg_wait in dow_pattern.items():
            jp_day = dow_jp.get(eng_day, eng_day)
            status = "📈" if avg_wait > 15 else "📊" if avg_wait > 10 else "📉"
            print(f"  {jp_day}: {avg_wait:>5.1f}分 {status}")
        
        return daily_avg, dow_pattern
    
    def find_best_visit_times(self):
        """おすすめ来園時間を提案"""
        if self.monthly_data is None:
            raise ValueError("データが読み込まれていません")
        
        # 人気アトラクション（待ち時間30分以上）の少ない時間を特定
        popular_attractions = self.monthly_data.groupby('attraction_name')['wait_time'].mean()
        popular_attractions = popular_attractions[popular_attractions > 30].index.tolist()
        
        popular_data = self.monthly_data[self.monthly_data['attraction_name'].isin(popular_attractions)]
        time_congestion = popular_data.groupby('time')['wait_time'].mean()
        
        # 空いている時間トップ5
        best_times = time_congestion.nsmallest(5)
        
        print("\n🎯 おすすめ来園時間（人気アトラクション基準）")
        print("=" * 50)
        for i, (time, avg_wait) in enumerate(best_times.items(), 1):
            print(f"{i}. {time} - 平均待ち時間: {avg_wait:.1f}分")
        
        return best_times
    
    def generate_attraction_heatmap(self, save_path=None):
        """アトラクション×時間帯ヒートマップ生成"""
        if self.monthly_data is None:
            raise ValueError("データが読み込まれていません")
        
        # ピボットテーブル作成（上位15アトラクション）
        top_attractions = self.monthly_data.groupby('attraction_name')['wait_time'].mean().nlargest(15).index
        heatmap_data = self.monthly_data[self.monthly_data['attraction_name'].isin(top_attractions)]
        
        pivot_table = heatmap_data.pivot_table(
            values='wait_time', 
            index='attraction_name', 
            columns='time', 
            aggfunc='mean'
        )
        
        # ヒートマップ作成
        plt.figure(figsize=(16, 10))
        sns.heatmap(pivot_table, annot=True, fmt='.0f', cmap='YlOrRd', cbar_kws={'label': '平均待ち時間（分）'})
        plt.title('🎢 人気アトラクション待ち時間ヒートマップ', fontsize=16, pad=20)
        plt.xlabel('時間帯', fontsize=12)
        plt.ylabel('アトラクション', fontsize=12)
        plt.xticks(rotation=45)
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 ヒートマップ保存: {save_path}")
        
        plt.show()
        return pivot_table
    
    def generate_comprehensive_report(self, output_dir=None):
        """総合分析レポート生成"""
        if output_dir is None:
            output_dir = self.data_dir
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"yosocal_analysis_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("🏰 ディズニーランド待ち時間データ 総合分析レポート\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"📊 分析実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write(f"📋 データ期間: {self.monthly_data['date'].min().strftime('%Y-%m-%d')} ～ {self.monthly_data['date'].max().strftime('%Y-%m-%d')}\n")
            f.write(f"📈 総データ数: {len(self.monthly_data):,}レコード\n")
            f.write(f"📅 分析日数: {self.monthly_data['date'].nunique()}日\n\n")
            
            # 人気ランキング
            ranking = self.generate_popularity_ranking()
            f.write("🎢 人気アトラクションTOP10:\n")
            for i, (attraction, data) in enumerate(ranking.head(10).iterrows(), 1):
                f.write(f"  {i:2d}. {attraction:<20} {data['平均待ち時間']:>6.1f}分\n")
            f.write("\n")
            
            # 時間パターン
            time_pattern = self.analyze_time_patterns()
            f.write("⏰ 時間帯分析:\n")
            peak_time = time_pattern.idxmax()
            quiet_time = time_pattern.idxmin()
            f.write(f"  最混雑時間: {peak_time} ({time_pattern.max():.1f}分)\n")
            f.write(f"  最空いている時間: {quiet_time} ({time_pattern.min():.1f}分)\n\n")
            
            # おすすめ時間
            best_times = self.find_best_visit_times()
            f.write("🎯 おすすめ来園時間TOP3:\n")
            for i, (time, avg_wait) in enumerate(best_times.head(3).items(), 1):
                f.write(f"  {i}. {time} (平均待ち時間: {avg_wait:.1f}分)\n")
            f.write("\n")
            
            # 統計サマリー
            f.write("📊 統計サマリー:\n")
            f.write(f"  全体平均待ち時間: {self.monthly_data['wait_time'].mean():.1f}分\n")
            f.write(f"  最大待ち時間: {self.monthly_data['wait_time'].max()}分\n")
            f.write(f"  待ち時間0分の割合: {(self.monthly_data['wait_time'] == 0).mean() * 100:.1f}%\n")
            f.write(f"  30分以上待ちの割合: {(self.monthly_data['wait_time'] >= 30).mean() * 100:.1f}%\n")
        
        print(f"📄 総合レポート保存: {report_file}")
        return report_file

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='yosocal.com データ分析ツール')
    parser.add_argument('--data-dir', default='data', help='データディレクトリ (default: data)')
    parser.add_argument('--monthly-file', help='月間データファイル名（指定しない場合は最新を自動選択）')
    parser.add_argument('--output-dir', help='出力ディレクトリ（指定しない場合はdata-dirと同じ）')
    parser.add_argument('--heatmap', action='store_true', help='ヒートマップを生成')
    parser.add_argument('--report', action='store_true', help='総合レポートを生成')
    
    args = parser.parse_args()
    
    print("🏰 yosocal.com データ分析ツール")
    print("=" * 50)
    
    try:
        analyzer = YosocalDataAnalyzer(args.data_dir)
        
        # データ読み込み
        analyzer.load_monthly_data(args.monthly_file)
        
        # 基本分析実行
        print("\n📊 基本分析実行中...")
        analyzer.generate_popularity_ranking()
        analyzer.analyze_time_patterns()
        analyzer.analyze_daily_trends()
        analyzer.find_best_visit_times()
        
        # ヒートマップ生成
        if args.heatmap:
            print("\n📊 ヒートマップ生成中...")
            heatmap_path = os.path.join(args.output_dir or args.data_dir, 
                                       f"yosocal_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            analyzer.generate_attraction_heatmap(heatmap_path)
        
        # 総合レポート生成
        if args.report:
            print("\n📄 総合レポート生成中...")
            analyzer.generate_comprehensive_report(args.output_dir)
        
        print("\n✅ 分析完了！")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    main() 