import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def fetch_yosocal_realtime():
    url = "https://yosocal.com/realtime.htm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    data = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # liタグ内の各アトラクション情報を取得
    all_rows = soup.select("ul.list_table li")
    for row in all_rows:
        name_tag = row.select_one("span.list_name")
        wait_tag = row.select_one("span.list_time")

        if not name_tag or not wait_tag:
            continue

        name = name_tag.get_text(strip=True)
        wait_text = wait_tag.get_text(strip=True)

        # 待ち時間の数値変換
        if "分待ち" in wait_text:
            wait = int(wait_text.replace("分待ち", "").strip())
        elif "受付終了" in wait_text:
            wait = -1
        elif "中止" in wait_text:
            wait = -2
        elif "休止" in wait_text:
            wait = -3
        elif "未発表" in wait_text:
            wait = None
        else:
            wait = None

        data.append({
            "datetime": now,
            "name": name,
            "wait_time": wait,
            "raw_text": wait_text
        })

    return pd.DataFrame(data)

def display_results(df):
    """結果を詳細表示する関数"""
    print("🎢 ディズニーリアルタイム待ち時間データ")
    print("=" * 60)
    print(f"📅 取得時刻: {df['datetime'].iloc[0] if not df.empty else 'データなし'}")
    print(f"📊 総アトラクション数: {len(df)}")
    print("=" * 60)
    
    if df.empty:
        print("❌ データが取得できませんでした")
        return
    
    # 待ち時間別に分類して表示
    operating = df[df['wait_time'] >= 0].sort_values('wait_time', ascending=False)
    ended = df[df['wait_time'] == -1]
    cancelled = df[df['wait_time'] == -2]
    suspended = df[df['wait_time'] == -3]
    unknown = df[df['wait_time'].isna()]
    
    if not operating.empty:
        print("🎢 運営中アトラクション:")
        for _, row in operating.iterrows():
            print(f"  {row['name']:<30} {row['wait_time']:>3}分待ち")
        print()
    
    if not ended.empty:
        print("🚫 受付終了:")
        for _, row in ended.iterrows():
            print(f"  {row['name']}")
        print()
    
    if not cancelled.empty:
        print("⛔ 中止:")
        for _, row in cancelled.iterrows():
            print(f"  {row['name']}")
        print()
    
    if not suspended.empty:
        print("🔧 休止:")
        for _, row in suspended.iterrows():
            print(f"  {row['name']}")
        print()
    
    if not unknown.empty:
        print("❓ 未発表:")
        for _, row in unknown.iterrows():
            print(f"  {row['name']} ({row['raw_text']})")
        print()
    
    # 統計情報
    if not operating.empty:
        avg_wait = operating['wait_time'].mean()
        max_wait = operating['wait_time'].max()
        max_attraction = operating.loc[operating['wait_time'].idxmax(), 'name']
        
        print("📈 統計情報:")
        print(f"  平均待ち時間: {avg_wait:.1f}分")
        print(f"  最長待ち時間: {max_wait}分 ({max_attraction})")
        print(f"  運営中: {len(operating)}件")
        print(f"  受付終了: {len(ended)}件")
        print(f"  中止/休止: {len(cancelled) + len(suspended)}件")

if __name__ == "__main__":
    print("🏰 yosocal.com リアルタイムデータ取得開始...")
    try:
        df = fetch_yosocal_realtime()
        
        # CSV出力
        output_filename = f"yosocal_realtime_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(output_filename, index=False, encoding="utf-8-sig")
        print(f"✅ CSV出力完了: {output_filename}")
        
        # コンソール表示
        display_results(df)
        
        # DataFrameの先頭も表示
        print("\n📋 データフレーム (先頭10件):")
        print(df.head(10).to_string())
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}") 