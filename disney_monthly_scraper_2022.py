import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import jpholiday
from datetime import datetime, timedelta
import calendar
import os

# ===== 設定 ===== #
parks = ['tdl', 'tds']  # ディズニーランド・シー
year = 2022  # 2022年に変更
output_dir = "disney_monthly_data_2022"  # 2022年専用ディレクトリ

# ===== 分類判定関数 ===== #
def classify_item(name: str) -> str:
    """アイテム名からカテゴリを判定"""
    if "グリ" in name or "グリーティング" in name:
        return "greet"
    elif any(keyword in name for keyword in ["ショー", "パレード", "シアター"]):
        return "show"
    else:
        return "attraction"

# ===== 日付生成関数 ===== #
def generate_date_range(year, month):
    """指定年月の全日付を生成"""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    return dates

# ===== データ取得関数 ===== #
def fetch_urtrip_all_items(park, date):
    """指定されたパークと日付のurtrip.jpから全アイテムデータを取得"""
    url = f"https://urtrip.jp/{park}-past-info/?rm={date}"
    
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')

        tables = soup.find_all("table", class_="t_cool")
        if len(tables) < 2:
            return pd.DataFrame()

        table = tables[1]
        rows = table.find_all("tr")
        
        if len(rows) < 3:
            return pd.DataFrame()

        # ヘッダー（項目名）
        header_cells = rows[0].find_all("th")[1:]
        item_names = [cell.get_text(strip=True) for cell in header_cells]

        # 本体（時刻 + 各列のデータ）
        data = []
        for row in rows[1:]:
            time_header = row.find("th")
            if not time_header:
                continue
                
            time_text = time_header.get_text(strip=True)
            cols = row.find_all("td")
            
            if not time_text or len(cols) != len(item_names):
                continue
                
            for i, col in enumerate(cols):
                raw_value = col.get_text(strip=True)
                
                if raw_value in ["-", "案内終了", "", "休止", "－"]:
                    value = 0
                else:
                    try:
                        value = int(raw_value.replace("分", "").replace("min", ""))
                    except ValueError:
                        value = raw_value
                
                data.append({
                    "datetime": f"{date} {time_text}",
                    "park": "DisneyLand" if park == "tdl" else "DisneySea",
                    "item": item_names[i],
                    "value": value,
                    "type": classify_item(item_names[i])
                })
                
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"    ❌ Error for {park} {date}: {e}")
        return pd.DataFrame()

# ===== 月別処理関数 ===== #
def process_month(year, month):
    """指定年月のデータを処理"""
    month_name = calendar.month_name[month]
    print(f"\n🗓️  Processing {month_name} {year}...")
    print("=" * 60)
    
    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)
    
    # 日付範囲生成
    date_range = generate_date_range(year, month)
    print(f"📅 Date range: {date_range[0]} to {date_range[-1]} ({len(date_range)} days)")
    
    monthly_data = []
    success_count = 0
    error_count = 0
    
    for park in parks:
        park_name = "DisneyLand" if park == "tdl" else "DisneySea"
        print(f"\n🎢 Processing {park_name}...")
        
        for i, date in enumerate(date_range, 1):
            try:
                print(f"  📦 [{i:2d}/{len(date_range):2d}] {date}...", end="")
                
                df = fetch_urtrip_all_items(park, date)
                if not df.empty:
                    monthly_data.append(df)
                    success_count += 1
                    print(f" ✅ {len(df)} records")
                else:
                    error_count += 1
                    print(f" ⚠️ No data")
                
                time.sleep(0.5)  # サーバーにやさしく
                
            except Exception as e:
                error_count += 1
                print(f" ❌ Error: {e}")
    
    # データ統合と保存
    if monthly_data:
        print(f"\n📊 Processing {len(monthly_data)} datasets...")
        
        final_df = pd.concat(monthly_data, ignore_index=True)
        
        # 日時データの変換
        final_df["datetime"] = pd.to_datetime(final_df["datetime"], format="%Y%m%d %H:%M")
        final_df["weekday"] = final_df["datetime"].dt.day_name()
        final_df["is_holiday"] = final_df["datetime"].apply(
            lambda d: jpholiday.is_holiday_name(d.date()) is not None
        )
        
        # データの並び替え
        final_df = final_df.sort_values(["park", "datetime", "item"]).reset_index(drop=True)
        
        # CSV保存
        output_filename = f"{output_dir}/disney_{year}_{month:02d}_{month_name.lower()}.csv"
        final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        print(f"✅ Saved: {output_filename}")
        print(f"📈 Records: {len(final_df):,}")
        print(f"🎪 Items: {final_df['item'].nunique()}")
        print(f"📊 Success: {success_count}, Errors: {error_count}")
        
        return final_df, success_count, error_count
    else:
        print(f"❌ No data collected for {month_name}")
        return None, success_count, error_count

# ===== メイン処理 ===== #
def main():
    """メイン処理関数"""
    print("🏰 Disney Monthly Scraper for 2022")
    print(f"🎪 Parks: {', '.join(parks)}")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 80)
    
    all_monthly_data = []
    total_records = 0
    total_success = 0
    total_errors = 0
    
    # 各月を処理
    for month in range(1, 13):
        try:
            monthly_df, success, errors = process_month(year, month)
            if monthly_df is not None:
                all_monthly_data.append(monthly_df)
                total_records += len(monthly_df)
            total_success += success
            total_errors += errors
            
            print(f"⏱️  Waiting 2 seconds before next month...")
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Failed to process month {month}: {e}")
            total_errors += 1
    
    # 年間データ統合
    if all_monthly_data:
        print("\n" + "=" * 80)
        print("📋 Creating annual consolidated file...")
        
        annual_df = pd.concat(all_monthly_data, ignore_index=True)
        annual_df = annual_df.sort_values(["park", "datetime", "item"]).reset_index(drop=True)
        
        annual_filename = f"{output_dir}/disney_{year}_annual.csv"
        annual_df.to_csv(annual_filename, index=False, encoding='utf-8-sig')
        
        print(f"✅ Annual file saved: {annual_filename}")
        print(f"📊 Total records: {len(annual_df):,}")
        print(f"📅 Date range: {annual_df['datetime'].min()} to {annual_df['datetime'].max()}")
        print(f"🎪 Unique items: {annual_df['item'].nunique()}")
        print(f"🏰 Parks: {annual_df['park'].nunique()}")
    else:
        print("❌ No data was collected for any month")
    
    # 最終統計
    print("\n" + "=" * 80)
    print("📈 FINAL STATISTICS")
    print("=" * 80)
    print(f"✅ Total successful requests: {total_success:,}")
    print(f"❌ Total failed requests: {total_errors:,}")
    print(f"📊 Total records collected: {total_records:,}")
    if total_success + total_errors > 0:
        success_rate = (total_success / (total_success + total_errors)) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
    print("🏰 Scraping completed!")

if __name__ == "__main__":
    main() 