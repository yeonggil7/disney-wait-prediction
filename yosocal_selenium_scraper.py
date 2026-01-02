import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def fetch_yosocal_selenium():
    """Seleniumを使ってyosocal.comのリアルタイムデータを取得"""
    
    # Chromeオプション設定
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # ヘッドレスモード
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        # Chromeドライバーを起動
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://yosocal.com/realtime.htm")
        
        print("📱 ページを読み込み中...")
        
        # JavaScriptの実行を待つ（最大30秒）
        wait = WebDriverWait(driver, 30)
        
        # データが読み込まれるまで待機（marqueeタグの内容が変わるまで）
        time.sleep(10)  # 初期待機
        
        # ページソースを取得してBeautifulSoupで解析
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # データが表示されている部分を探す
        data_container = soup.find(id="hyo")
        
        if data_container:
            print(f"🔍 データコンテナの内容: {data_container.get_text(strip=True)}")
            
        # テーブル構造を調査
        tables = soup.find_all("table")
        print(f"📊 テーブル数: {len(tables)}")
        
        data = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 各テーブルの内容を確認
        for i, table in enumerate(tables):
            rows = table.find_all("tr")
            if len(rows) > 2:  # ヘッダー + データ行があるテーブル
                print(f"\n📋 テーブル {i+1}: {len(rows)} 行")
                
                # 最初の数行を確認
                for j, row in enumerate(rows[:3]):
                    cells = row.find_all(["td", "th"])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    print(f"  行 {j+1}: {cell_texts}")
                    
                    # アトラクション名と待ち時間らしきデータを探す
                    if len(cells) >= 2:
                        for k, cell in enumerate(cells):
                            text = cell.get_text(strip=True)
                            if any(keyword in text for keyword in ["スプラッシュ", "ビッグサンダー", "ホーンテッド", "プーさん"]):
                                # アトラクション名が見つかった場合
                                wait_time_cell = cells[k+1] if k+1 < len(cells) else None
                                if wait_time_cell:
                                    wait_text = wait_time_cell.get_text(strip=True)
                                    print(f"    🎢 アトラクション発見: {text} -> {wait_text}")
                                    
                                    # 待ち時間の数値変換
                                    wait_time = parse_wait_time(wait_text)
                                    
                                    data.append({
                                        "datetime": now,
                                        "name": text,
                                        "wait_time": wait_time,
                                        "raw_text": wait_text
                                    })
        
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return pd.DataFrame()
    
    finally:
        if driver:
            driver.quit()

def parse_wait_time(wait_text):
    """待ち時間テキストを数値に変換"""
    if not wait_text or wait_text == "-":
        return None
    elif "分" in wait_text:
        try:
            return int(''.join(filter(str.isdigit, wait_text)))
        except ValueError:
            return None
    elif any(keyword in wait_text for keyword in ["終了", "受付終了"]):
        return -1
    elif any(keyword in wait_text for keyword in ["中止", "運休"]):
        return -2
    elif any(keyword in wait_text for keyword in ["休止", "点検"]):
        return -3
    else:
        return None

def display_results(df):
    """結果を詳細表示する関数"""
    print("\n🎢 ディズニーリアルタイム待ち時間データ (Selenium)")
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

if __name__ == "__main__":
    print("🏰 yosocal.com Selenium リアルタイムデータ取得開始...")
    
    # seleniumがインストールされているかチェック
    try:
        import selenium
        print("✅ Seleniumが利用可能です")
    except ImportError:
        print("❌ Seleniumがインストールされていません")
        print("📦 以下のコマンドでインストールしてください:")
        print("pip install selenium")
        print("また、ChromeDriverが必要です")
        exit(1)
    
    try:
        df = fetch_yosocal_selenium()
        
        # CSV出力
        output_filename = f"yosocal_selenium_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(output_filename, index=False, encoding="utf-8-sig")
        print(f"✅ CSV出力完了: {output_filename}")
        
        # コンソール表示
        display_results(df)
        
        # DataFrameの先頭も表示
        if not df.empty:
            print("\n📋 データフレーム:")
            print(df.to_string())
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}") 