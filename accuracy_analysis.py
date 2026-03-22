#!/usr/bin/env python3
"""
予測精度分析スクリプト
過去1ヶ月の予測値と実績値を比較し、改善点を特定する
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()


def load_actual_data(park: str) -> pd.DataFrame:
    """実績データを読み込み（最新のCSVから）"""
    if park == 'sea':
        folder = PROJECT_DIR / 'Disneysea'
        prefix = 'disneysea_monthly_2026'
    else:
        folder = PROJECT_DIR / 'Disneyland'
        prefix = 'disneyland_monthly_2026'
    
    csv_files = sorted(glob.glob(str(folder / f'{prefix}*.csv')))
    if not csv_files:
        print(f"❌ {park}の実績データが見つかりません")
        return pd.DataFrame()
    
    # 最新ファイルを使用（最も多くのデータを含む）
    latest_file = csv_files[-1]
    print(f"📂 実績データ: {os.path.basename(latest_file)}")
    
    df = pd.read_csv(latest_file)
    # wait_time を数値変換（'-' は NaN に）
    df['wait_time'] = pd.to_numeric(df['wait_time'], errors='coerce')
    df = df.dropna(subset=['wait_time'])
    df = df[df['wait_time'] > 0]  # 0分は営業時間外
    
    return df


def load_prediction_data(park: str, date: str) -> pd.DataFrame:
    """予測データを読み込み"""
    if park == 'sea':
        folder = PROJECT_DIR / 'predictions_sea' / date
    else:
        folder = PROJECT_DIR / 'predictions_land' / date
    
    csv_file = folder / f'prediction_{date}.csv'
    if not csv_file.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(csv_file)
    df = df[df['predicted_wait_time'] > 0]  # 休止中を除外
    return df


def merge_prediction_and_actual(park: str, dates: list) -> pd.DataFrame:
    """予測と実績をマージ"""
    actual_df = load_actual_data(park)
    if actual_df.empty:
        return pd.DataFrame()
    
    all_merged = []
    
    for date in dates:
        pred_df = load_prediction_data(park, date)
        if pred_df.empty:
            continue
        
        # 実績データからその日のデータを抽出
        actual_day = actual_df[actual_df['date'] == date].copy()
        if actual_day.empty:
            continue
        
        # マージ: アトラクション名 + 時間でジョイン
        merged = pd.merge(
            pred_df[['date', 'time', 'attraction_name', 'predicted_wait_time', 
                     'is_weekend', 'is_holiday', 'hour']],
            actual_day[['date', 'time', 'attraction_name', 'wait_time']],
            on=['date', 'time', 'attraction_name'],
            how='inner'
        )
        
        if not merged.empty:
            merged['error'] = merged['predicted_wait_time'] - merged['wait_time']
            merged['abs_error'] = merged['error'].abs()
            merged['pct_error'] = (merged['abs_error'] / merged['wait_time'].clip(lower=1)) * 100
            merged['park'] = park
            merged['weekday'] = pd.to_datetime(merged['date']).dt.dayofweek
            merged['weekday_name'] = pd.to_datetime(merged['date']).dt.day_name()
            all_merged.append(merged)
    
    if all_merged:
        return pd.concat(all_merged, ignore_index=True)
    return pd.DataFrame()


def main():
    # 分析対象期間: 2026年1月20日〜2月25日 (約1ヶ月)
    start_date = datetime(2026, 1, 20)
    end_date = datetime(2026, 2, 25)
    
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    print("=" * 70)
    print("📊 予測精度分析レポート")
    print(f"📅 分析期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    # 両パークのデータ収集
    sea_data = merge_prediction_and_actual('sea', dates)
    land_data = merge_prediction_and_actual('land', dates)
    
    all_data = pd.concat([sea_data, land_data], ignore_index=True) if not sea_data.empty or not land_data.empty else pd.DataFrame()
    
    if all_data.empty:
        print("❌ マージ可能なデータがありません")
        return
    
    print(f"\n📈 マージされたデータポイント数: {len(all_data):,}")
    matched_dates = sorted(all_data['date'].unique())
    print(f"📅 マッチした日数: {len(matched_dates)}日")
    print(f"   日付一覧: {', '.join(matched_dates)}")
    
    # ============================================================
    # 1. 全体の精度
    # ============================================================
    print("\n" + "=" * 70)
    print("1️⃣  全体精度")
    print("=" * 70)
    
    mae = all_data['abs_error'].mean()
    rmse = np.sqrt((all_data['error'] ** 2).mean())
    mean_bias = all_data['error'].mean()
    median_error = all_data['abs_error'].median()
    
    print(f"   MAE（平均絶対誤差）: {mae:.1f}分")
    print(f"   RMSE（二乗平均平方根誤差）: {rmse:.1f}分")
    print(f"   バイアス（予測 - 実績の平均）: {mean_bias:+.1f}分")
    print(f"   {'→ 全体的に過大予測' if mean_bias > 5 else '→ 全体的に過小予測' if mean_bias < -5 else '→ バイアスは小さい'}")
    print(f"   中央値誤差: {median_error:.1f}分")
    
    # 誤差分布
    print(f"\n   誤差分布:")
    print(f"   |誤差| ≤ 10分: {(all_data['abs_error'] <= 10).mean() * 100:.1f}%")
    print(f"   |誤差| ≤ 20分: {(all_data['abs_error'] <= 20).mean() * 100:.1f}%")
    print(f"   |誤差| ≤ 30分: {(all_data['abs_error'] <= 30).mean() * 100:.1f}%")
    print(f"   |誤差| > 60分: {(all_data['abs_error'] > 60).mean() * 100:.1f}%")
    
    # ============================================================
    # 2. パーク別精度
    # ============================================================
    print("\n" + "=" * 70)
    print("2️⃣  パーク別精度")
    print("=" * 70)
    
    for park_name, park_code in [('ディズニーシー', 'sea'), ('ディズニーランド', 'land')]:
        park_data = all_data[all_data['park'] == park_code]
        if park_data.empty:
            continue
        park_mae = park_data['abs_error'].mean()
        park_bias = park_data['error'].mean()
        print(f"\n   🎡 {park_name}")
        print(f"      MAE: {park_mae:.1f}分 / バイアス: {park_bias:+.1f}分")
        print(f"      データ数: {len(park_data):,}")
    
    # ============================================================
    # 3. 曜日別精度
    # ============================================================
    print("\n" + "=" * 70)
    print("3️⃣  曜日別精度")
    print("=" * 70)
    
    day_names_jp = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}
    weekday_stats = all_data.groupby('weekday').agg(
        MAE=('abs_error', 'mean'),
        Bias=('error', 'mean'),
        Count=('abs_error', 'count')
    ).reset_index()
    
    for _, row in weekday_stats.iterrows():
        wd = int(row['weekday'])
        print(f"   {day_names_jp.get(wd, '?')}曜: MAE {row['MAE']:.1f}分 / バイアス {row['Bias']:+.1f}分 / n={int(row['Count'])}")
    
    # ============================================================
    # 4. 時間帯別精度
    # ============================================================
    print("\n" + "=" * 70)
    print("4️⃣  時間帯別精度")
    print("=" * 70)
    
    hour_stats = all_data.groupby('hour').agg(
        MAE=('abs_error', 'mean'),
        Bias=('error', 'mean'),
        Count=('abs_error', 'count')
    ).reset_index()
    
    for _, row in hour_stats.iterrows():
        h = int(row['hour'])
        bar = '█' * int(row['MAE'] / 3)
        print(f"   {h:2d}時: MAE {row['MAE']:5.1f}分 {bar} (バイアス {row['Bias']:+.1f})")
    
    # ============================================================
    # 5. アトラクション別精度（主要アトラクション）
    # ============================================================
    print("\n" + "=" * 70)
    print("5️⃣  主要アトラクション別精度")
    print("=" * 70)
    
    target_sea = ['ソアリン', 'アナとエルサ', 'センターオブジアース', 'タワーオブテラー',
                  'トイストーリーマニア', 'タートルトーク', 'レイジングスピリッツ']
    target_land = ['美女と野獣の物語', 'ベイマックスのハッピーライド', 'スプラッシュマウンテン',
                   'ビッグサンダーマウンテン', 'プーさんのハニーハント', 'モンスターズインクライド＆ゴーシーク']
    target_all = target_sea + target_land
    
    attr_stats = all_data.groupby('attraction_name').agg(
        MAE=('abs_error', 'mean'),
        Bias=('error', 'mean'),
        Count=('abs_error', 'count'),
        AvgActual=('wait_time', 'mean'),
        AvgPredicted=('predicted_wait_time', 'mean')
    ).reset_index()
    
    # 主要アトラクションのみフィルタ（部分一致）
    print("\n   --- シー ---")
    for target in target_sea:
        matches = attr_stats[attr_stats['attraction_name'].str.contains(target, na=False)]
        for _, row in matches.iterrows():
            direction = "↑過大" if row['Bias'] > 5 else "↓過小" if row['Bias'] < -5 else "≈適正"
            print(f"   {row['attraction_name'][:20]:20s}: MAE {row['MAE']:5.1f}分 / 実績平均 {row['AvgActual']:5.1f}分 / 予測平均 {row['AvgPredicted']:5.1f}分 / {direction}")
    
    print("\n   --- ランド ---")
    for target in target_land:
        matches = attr_stats[attr_stats['attraction_name'].str.contains(target, na=False)]
        for _, row in matches.iterrows():
            direction = "↑過大" if row['Bias'] > 5 else "↓過小" if row['Bias'] < -5 else "≈適正"
            print(f"   {row['attraction_name'][:20]:20s}: MAE {row['MAE']:5.1f}分 / 実績平均 {row['AvgActual']:5.1f}分 / 予測平均 {row['AvgPredicted']:5.1f}分 / {direction}")
    
    # ============================================================
    # 6. 誤差の大きいワースト10（アトラクション別）
    # ============================================================
    print("\n" + "=" * 70)
    print("6️⃣  誤差が大きいアトラクション TOP10")
    print("=" * 70)
    
    worst_attrs = attr_stats.sort_values('MAE', ascending=False).head(10)
    for i, (_, row) in enumerate(worst_attrs.iterrows(), 1):
        print(f"   {i:2d}. {row['attraction_name'][:25]:25s}: MAE {row['MAE']:5.1f}分 (バイアス {row['Bias']:+.1f})")
    
    # ============================================================
    # 7. 日別精度推移
    # ============================================================
    print("\n" + "=" * 70)
    print("7️⃣  日別精度推移")
    print("=" * 70)
    
    daily_stats = all_data.groupby('date').agg(
        MAE=('abs_error', 'mean'),
        Bias=('error', 'mean'),
        Count=('abs_error', 'count')
    ).reset_index()
    daily_stats = daily_stats.sort_values('date')
    
    for _, row in daily_stats.iterrows():
        dt = datetime.strptime(row['date'], '%Y-%m-%d')
        wd = day_names_jp.get(dt.weekday(), '?')
        bar = '█' * int(row['MAE'] / 3)
        quality = "🟢" if row['MAE'] < 15 else "🟡" if row['MAE'] < 25 else "🔴"
        print(f"   {row['date']} ({wd}): {quality} MAE {row['MAE']:5.1f}分 {bar}")
    
    # ============================================================
    # 8. 過大予測 vs 過小予測の分析
    # ============================================================
    print("\n" + "=" * 70)
    print("8️⃣  過大予測 vs 過小予測")
    print("=" * 70)
    
    over = (all_data['error'] > 10).sum()
    under = (all_data['error'] < -10).sum()
    ok = ((all_data['error'] >= -10) & (all_data['error'] <= 10)).sum()
    total = len(all_data)
    
    print(f"   過大予測（10分以上）: {over:,} ({over/total*100:.1f}%)")
    print(f"   適正範囲（±10分以内）: {ok:,} ({ok/total*100:.1f}%)")
    print(f"   過小予測（10分以上）: {under:,} ({under/total*100:.1f}%)")
    
    # 大きな乖離（60分以上）のケース分析
    big_errors = all_data[all_data['abs_error'] > 60].copy()
    if not big_errors.empty:
        print(f"\n   ⚠️ 大きな乖離（60分以上）: {len(big_errors)}件")
        print(f"   内訳:")
        big_by_park = big_errors.groupby('park').size()
        for park, cnt in big_by_park.items():
            print(f"      {park}: {cnt}件")
        big_by_attr = big_errors.groupby('attraction_name').size().sort_values(ascending=False).head(5)
        print(f"   アトラクション内訳TOP5:")
        for attr, cnt in big_by_attr.items():
            print(f"      {attr}: {cnt}件")
    
    # ============================================================
    # 9. 待ち時間帯別の精度
    # ============================================================
    print("\n" + "=" * 70)
    print("9️⃣  実際の待ち時間帯別の精度")
    print("=" * 70)
    
    bins = [0, 15, 30, 60, 90, 120, 180, 999]
    labels = ['0-15分', '15-30分', '30-60分', '60-90分', '90-120分', '120-180分', '180分+']
    all_data['wait_bin'] = pd.cut(all_data['wait_time'], bins=bins, labels=labels)
    
    wait_bin_stats = all_data.groupby('wait_bin', observed=False).agg(
        MAE=('abs_error', 'mean'),
        Bias=('error', 'mean'),
        Count=('abs_error', 'count')
    ).reset_index()
    
    for _, row in wait_bin_stats.iterrows():
        if row['Count'] > 0:
            print(f"   {row['wait_bin']:10s}: MAE {row['MAE']:5.1f}分 / バイアス {row['Bias']:+.1f}分 / n={int(row['Count'])}")
    
    # ============================================================
    # 10. 休日 vs 平日 精度
    # ============================================================
    print("\n" + "=" * 70)
    print("🔟  平日 vs 週末・祝日")
    print("=" * 70)
    
    all_data['is_weekend_holiday'] = (all_data['is_weekend'] == 1) | (all_data['is_holiday'] == 1)
    
    for label, mask in [('平日', ~all_data['is_weekend_holiday']), ('週末・祝日', all_data['is_weekend_holiday'])]:
        subset = all_data[mask]
        if not subset.empty:
            print(f"   {label}: MAE {subset['abs_error'].mean():.1f}分 / バイアス {subset['error'].mean():+.1f}分 / n={len(subset):,}")
    
    print("\n" + "=" * 70)
    print("✅ 分析完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
