#!/usr/bin/env python3
"""
休止情報更新スクリプト
公式サイトから休止情報を取得してclosures.jsonを更新

使い方:
  python scripts/update_closures.py

定期実行（cron）:
  0 6 * * * cd /path/to/chatbot && python scripts/update_closures.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# プロジェクトのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("urllib is required")
    sys.exit(1)


# 公式サイトのURL
CLOSURE_URLS = {
    "tdl": "https://www.tokyodisneyresort.jp/tdl/monthly/stop.html",
    "tds": "https://www.tokyodisneyresort.jp/tds/monthly/stop.html",
}

# 出力ファイル
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "closures.json"


def fetch_html(url: str) -> str:
    """URLからHTMLを取得"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_closures(park: str, html: str) -> List[Dict]:
    """HTMLから休止情報をパース（東京ディズニーリゾート公式サイト対応）"""
    closures = []
    
    # アコーディオンブロックを検出
    accordion_pattern = r'<div class="accordionTitle">([^<]+)</div>.*?<div class="accordionDetail">(.*?)</div>\s*<div class="accordionClose">'
    accordion_matches = re.findall(accordion_pattern, html, re.DOTALL)
    
    for category_name, content in accordion_matches:
        # カテゴリを判定
        if "アトラクション" in category_name:
            category = "attraction"
        elif "パレード" in category_name or "ショー" in category_name:
            category = "show"
        elif "レストラン" in category_name:
            category = "restaurant"
        elif "ショップ" in category_name:
            category = "shop"
        else:
            category = "other"
        
        # 各アイテムをパース
        item_pattern = r'<p class="heading3">([^<]+)</p>\s*<p>\s*(\d{4}/\d{1,2}/\d{1,2})\s*(?:-\s*(\d{4}/\d{1,2}/\d{1,2}|未定))?\s*</p>'
        items = re.findall(item_pattern, content, re.DOTALL)
        
        for item in items:
            try:
                name = item[0].strip()
                start_date = convert_date_format(item[1])
                end_date = convert_date_format(item[2]) if item[2] else "未定"
                
                closures.append({
                    "attraction_name": name,
                    "park": park,
                    "start_date": start_date,
                    "end_date": end_date,
                    "reason": "refurbishment" if category in ["attraction", "restaurant", "shop"] else "seasonal",
                    "note": f"カテゴリ: {category_name.strip()}"
                })
            except Exception as e:
                print(f"  パースエラー: {e}")
                continue
    
    # フォールバック
    if not closures:
        simple_pattern = r'<p class="heading3">([^<]+)</p>\s*<p>\s*(\d{4}/\d{1,2}/\d{1,2})\s*-?\s*(\d{4}/\d{1,2}/\d{1,2}|未定)?'
        matches = re.findall(simple_pattern, html, re.DOTALL)
        
        for match in matches:
            try:
                name = match[0].strip()
                start_date = convert_date_format(match[1])
                end_date = convert_date_format(match[2]) if match[2] else "未定"
                
                closures.append({
                    "attraction_name": name,
                    "park": park,
                    "start_date": start_date,
                    "end_date": end_date,
                    "reason": "refurbishment",
                    "note": ""
                })
            except Exception:
                continue
    
    return closures


def convert_date_format(date_str: str) -> str:
    """日付フォーマットを変換（2025/1/6 -> 2025-01-06）"""
    if not date_str or date_str == "未定":
        return "未定"
    
    date_str = date_str.strip()
    
    match = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return date_str


def parse_date(date_str: str) -> str:
    """日付文字列をYYYY-MM-DD形式に変換"""
    date_str = date_str.strip()
    
    # "2025年1月6日" 形式
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # "1月6日" 形式（年なし）
    match = re.search(r'(\d{1,2})月(\d{1,2})日', date_str)
    if match:
        month, day = match.groups()
        year = datetime.now().year
        # 1-3月の場合は翌年の可能性
        if int(month) < datetime.now().month - 6:
            year += 1
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # "1/6" 形式
    match = re.search(r'(\d{1,2})/(\d{1,2})', date_str)
    if match:
        month, day = match.groups()
        year = datetime.now().year
        if int(month) < datetime.now().month - 6:
            year += 1
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    return date_str


def load_existing_closures() -> Dict:
    """既存のclosures.jsonを読み込む"""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"closures": [], "notes": []}


def save_closures(data: Dict):
    """closures.jsonを保存"""
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 保存完了: {OUTPUT_FILE}")


def main():
    print("=" * 60)
    print("🔄 休止情報更新スクリプト")
    print("=" * 60)
    print()
    
    # 既存データを読み込む
    existing_data = load_existing_closures()
    existing_closures = existing_data.get("closures", [])
    existing_names = {c["attraction_name"] for c in existing_closures}
    
    print(f"📦 既存の休止情報: {len(existing_closures)}件")
    
    # 公式サイトから取得
    new_closures = []
    
    for park, url in CLOSURE_URLS.items():
        park_name = "ディズニーランド" if park == "tdl" else "ディズニーシー"
        print(f"\n🔍 {park_name}の休止情報を取得中...")
        print(f"   URL: {url}")
        
        try:
            html = fetch_html(url)
            print(f"   HTML取得成功: {len(html)}文字")
            
            closures = parse_closures(park, html)
            print(f"   パース結果: {len(closures)}件")
            
            for c in closures:
                if c["attraction_name"] not in existing_names:
                    new_closures.append(c)
                    print(f"   ✨ 新規: {c['attraction_name']}")
                else:
                    print(f"   ✓ 既存: {c['attraction_name']}")
                    
        except urllib.error.URLError as e:
            print(f"   ❌ 接続エラー: {e}")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
    
    # 新規休止情報を追加
    if new_closures:
        existing_closures.extend(new_closures)
        print(f"\n✨ 新規追加: {len(new_closures)}件")
    else:
        print("\n📝 新規の休止情報はありません")
    
    # 保存
    existing_data["closures"] = existing_closures
    save_closures(existing_data)
    
    print()
    print("=" * 60)
    print(f"📊 最終結果: {len(existing_closures)}件の休止情報")
    print("=" * 60)


if __name__ == "__main__":
    main()

