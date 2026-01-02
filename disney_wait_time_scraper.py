import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import jpholiday
from datetime import datetime

# ===== パラメータ設定 ===== #
parks = ['tdl', 'tds']  # ディズニーランド・シー
date_range = ['20241201', '20241210']  # まず短期間でテスト（YYYYMMDD）
# 注意: 全期間(2023-2025)は約900日分で膨大なデータになります
# 必要に応じて期間を調整してください

# ===== 分類判定関数 ===== #
def classify_item(name: str) -> str:
    """
    アイテム名からカテゴリを判定
    
    Args:
        name (str): アイテム名
    
    Returns:
        str: "greet", "show", "attraction" のいずれか
    """
    if "グリ" in name or "グリーティング" in name:
        return "greet"
    elif any(keyword in name for keyword in ["ショー", "パレード", "シアター"]):
        return "show"
    else:
        return "attraction"

# ===== データ取得関数 ===== #
def fetch_urtrip_all_items(park, date):
    """
    指定されたパークと日付のurtrip.jpから全アイテムデータを取得
    
    Args:
        park (str): 'tdl' または 'tds'
        date (str): 'YYYYMMDD' 形式の日付
    
    Returns:
        pd.DataFrame: アイテムデータ（待ち時間、ショー混雑度など）
    """
    url = f"https://urtrip.jp/{park}-past-info/?rm={date}"
    print(f"📦 Fetching: {url}")
    
    try:
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')

        tables = soup.find_all("table", class_="t_cool")
        if len(tables) < 2:
            print(f"❌ No table for {park} {date}")
            return pd.DataFrame()

        table = tables[1]
        rows = table.find_all("tr")
        
        if len(rows) < 3:
            print(f"❌ Insufficient rows for {park} {date}")
            return pd.DataFrame()

        # ヘッダー（項目名）
        header_cells = rows[0].find_all("th")[1:]  # Row 0から取得し、時間列をスキップ
        item_names = [cell.get_text(strip=True) for cell in header_cells]

        # 本体（時刻 + 各列のデータ）
        data = []
        for row in rows[1:]:  # Row 1から開始（Row 0はヘッダー）
            time_header = row.find("th")
            if not time_header:
                continue
                
            time_text = time_header.get_text(strip=True)
            cols = row.find_all("td")
            
            if not time_text or len(cols) != len(item_names):
                continue
                
            for i, col in enumerate(cols):
                raw_value = col.get_text(strip=True)
                
                # 値の処理：数値変換を試みて、失敗したら文字列のまま
                if raw_value in ["-", "案内終了", "", "休止"]:
                    value = 0
                else:
                    try:
                        # 数値として解析を試行
                        value = int(raw_value.replace("分", "").replace("min", ""))
                    except ValueError:
                        # 数値でない場合は文字列のまま（例："混雑"）
                        value = raw_value
                
                data.append({
                    "datetime": f"{date} {time_text}",
                    "park": "DisneyLand" if park == "tdl" else "DisneySea",
                    "item": item_names[i],
                    "value": value,
                    "type": classify_item(item_names[i])
                })
                
        return pd.DataFrame(data)
        
    except requests.RequestException as e:
        print(f"🌐 Request error for {park} {date}: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"⚠️ Parsing error for {park} {date}: {e}")
        return pd.DataFrame()

# ===== メイン処理 ===== #
def main():
    """メイン処理関数"""
    print("🏰 Disney Urtrip Data Scraper Starting...")
    print(f"🎪 Parks: {', '.join(parks)}")
    print(f"📅 Dates: {', '.join(date_range)}")
    print("-" * 50)
    
    all_df_list = []
    
    for park in parks:
        park_name = "DisneyLand" if park == "tdl" else "DisneySea"
        print(f"\n🎢 Processing {park_name}...")
        
        for date in date_range:
            try:
                df = fetch_urtrip_all_items(park, date)
                if not df.empty:
                    all_df_list.append(df)
                    print(f"  ✅ {date}: {len(df)} records collected")
                else:
                    print(f"  ⚠️ {date}: No data found")
                time.sleep(0.2)  # サーバーにやさしく
            except Exception as e:
                print(f"  ❌ Error on {park}-{date}: {e}")

    # ===== 統合 & 整形 ===== #
    if all_df_list:
        print(f"\n📊 Processing {len(all_df_list)} datasets...")
        
        final_df = pd.concat(all_df_list, ignore_index=True)
        
        # 日時データの変換
        final_df["datetime"] = pd.to_datetime(final_df["datetime"], format="%Y%m%d %H:%M")
        
        # 追加の解析用カラム
        final_df["weekday"] = final_df["datetime"].dt.day_name()
        final_df["is_holiday"] = final_df["datetime"].apply(
            lambda d: jpholiday.is_holiday_name(d.date()) is not None
        )
        
        # データの並び替え
        final_df = final_df.sort_values(["park", "datetime", "item"]).reset_index(drop=True)

        # 出力
        output_filename = "disney_urtrip_parsed.csv"
        final_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ CSV出力完了: {output_filename}")
        print(f"📈 Total records: {len(final_df):,}")
        print(f"🎪 Unique items: {final_df['item'].nunique()}")
        print(f"📅 Date range: {final_df['datetime'].dt.date.min()} to {final_df['datetime'].dt.date.max()}")
        
        # カテゴリ別統計
        print(f"\n📊 Item type breakdown:")
        type_counts = final_df['type'].value_counts()
        for item_type, count in type_counts.items():
            print(f"   {item_type}: {count:,} records")
            
        # パーク別統計
        print(f"\n🏰 Park breakdown:")
        park_counts = final_df['park'].value_counts()
        for park_name, count in park_counts.items():
            print(f"   {park_name}: {count:,} records")
            
        # サンプルデータの表示
        print(f"\n📌 Sample data (first 5 rows):")
        print(final_df.head().to_string(index=False))
        
    else:
        print("❌ データが取得できませんでした。")

if __name__ == "__main__":
    main() 