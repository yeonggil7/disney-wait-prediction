"""
このスクリプトは yosocal.com の待ち時間データを日付指定で取得し、
指定した日付（例: 20250629）の待ち時間一覧をCSV形式で保存します。

仕組み:
1. Seleniumでブラウザを自動操作。
2. 指定日をカレンダーからクリック（onclick="fMouseclick(...) を実行）。
3. 表示された待ち時間テーブルを取得。
4. CSVに書き出し。
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import pandas as pd

def scrape_yosocal_by_date(target_date: str):
    """
    指定された日付のデータをスクレイピングしてCSV出力します。

    Parameters:
        target_date (str): 例 "20250629" のような形式の文字列
    """

    # ヘッドレスモードでブラウザを起動（GUIなし）
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    # サイトを開く
    driver.get("https://yosocal.com/realtime.htm")
    time.sleep(3)  # JavaScriptロード待ち

    # 対象の日付をクリック（onclick に対応する要素を探してクリック）
    calendar_xpath = f'//div[@onclick="fMouseclick({target_date},0)"]'
    calendar_element = driver.find_element(By.XPATH, calendar_xpath)
    calendar_element.click()
    time.sleep(3)  # テーブル読み込み待ち

    # ページ内容を取得して解析
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tables = soup.find_all("table")

    # テーブルからデータを抽出
    results = []
    for table in tables:
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                attraction = cols[0].text.strip()
                wait_time = cols[1].text.strip()
                status = cols[2].text.strip()
                results.append({
                    "Attraction": attraction,
                    "WaitTime": wait_time,
                    "Status": status,
                    "Date": target_date
                })

    # 結果をCSVで保存
    df = pd.DataFrame(results)
    csv_filename = f"yosocal_{target_date}.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"✅ {csv_filename} を出力しました")

    driver.quit()

# 🔧 実行例（2025年6月29日のデータ）
if __name__ == "__main__":
    scrape_yosocal_by_date("20250629")
