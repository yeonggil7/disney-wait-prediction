import pandas as pd
import os
from datetime import datetime

def analyze_disney_data():
    """収集されたディズニーデータの統計情報を表示"""
    
    print("🏰 ディズニー待ち時間データ収集プロジェクト 結果サマリー")
    print("=" * 80)
    print(f"📅 分析実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    print("=" * 80)
    
    # 各年のデータを分析
    years = [2022, 2023, 2024]
    total_records = 0
    
    for year in years:
        data_dir = f"disney_monthly_data_{year}"
        annual_file = f"{data_dir}/disney_{year}_annual.csv"
        
        if os.path.exists(annual_file):
            print(f"\n📊 {year}年データ分析:")
            print("-" * 40)
            
            try:
                df = pd.read_csv(annual_file)
                total_records += len(df)
                
                # 基本統計
                print(f"  📈 総レコード数: {len(df):,} 件")
                print(f"  🎪 パーク数: {df['park'].nunique()}")
                print(f"  🎢 アトラクション数: {df['item'].nunique()}")
                
                # 日付範囲
                df['datetime'] = pd.to_datetime(df['datetime'])
                date_min = df['datetime'].min().strftime('%Y-%m-%d')
                date_max = df['datetime'].max().strftime('%Y-%m-%d')
                print(f"  📅 データ期間: {date_min} ～ {date_max}")
                
                # 月別ファイル数
                monthly_files = [f for f in os.listdir(data_dir) if f.startswith(f"disney_{year}_") and f.endswith('.csv') and 'annual' not in f]
                print(f"  📁 月別ファイル数: {len(monthly_files)} ファイル")
                
                # 各パークのデータ
                for park in df['park'].unique():
                    park_data = df[df['park'] == park]
                    print(f"    🏰 {park}: {len(park_data):,} レコード")
                
                # 数値データの待ち時間統計
                numeric_data = df[pd.to_numeric(df['value'], errors='coerce').notna()]
                if not numeric_data.empty:
                    numeric_values = pd.to_numeric(numeric_data['value'])
                    print(f"  ⏰ 数値待ち時間データ: {len(numeric_values):,} 件")
                    print(f"    平均待ち時間: {numeric_values.mean():.1f}分")
                    print(f"    最大待ち時間: {numeric_values.max():.0f}分")
                    print(f"    最小待ち時間: {numeric_values.min():.0f}分")
                
                # 人気アトラクション (数値データのある上位5位)
                if not numeric_data.empty:
                    numeric_data_copy = numeric_data.copy()
                    numeric_data_copy['value_numeric'] = pd.to_numeric(numeric_data_copy['value'])
                    top_attractions = numeric_data_copy.groupby('item')['value_numeric'].mean().sort_values(ascending=False).head(5)
                    print(f"  🎢 平均待ち時間上位5アトラクション:")
                    for idx, (attraction, avg_wait) in enumerate(top_attractions.items(), 1):
                        print(f"    {idx}. {attraction}: {avg_wait:.1f}分")
                
            except Exception as e:
                print(f"  ❌ {year}年データの分析エラー: {e}")
        else:
            print(f"\n❌ {year}年のデータファイルが見つかりません: {annual_file}")
    
    # 全体統計
    print(f"\n🎯 全体統計:")
    print("=" * 40)
    print(f"📊 収集対象年数: {len(years)} 年間")
    print(f"📈 総レコード数: {total_records:,} 件")
    print(f"💾 データサイズ概算: {total_records * 100 / 1024 / 1024:.1f} MB")
    
    # ファイル一覧
    print(f"\n📁 生成されたファイル一覧:")
    print("=" * 40)
    for year in years:
        data_dir = f"disney_monthly_data_{year}"
        if os.path.exists(data_dir):
            files = os.listdir(data_dir)
            csv_files = [f for f in files if f.endswith('.csv')]
            print(f"  {year}年: {len(csv_files)} ファイル")
            for file in sorted(csv_files):
                file_path = os.path.join(data_dir, file)
                file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
                print(f"    - {file} ({file_size:.1f} MB)")
    
    print(f"\n✅ データ収集プロジェクト完了!")
    print("🎉 2022年、2023年、2024年の3年間のディズニー待ち時間データが正常に収集されました！")

if __name__ == "__main__":
    analyze_disney_data() 