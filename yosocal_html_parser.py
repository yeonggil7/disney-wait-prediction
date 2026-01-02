#!/usr/bin/env python3
"""
yosocal HTMLファイル解析ツール
保存されたHTMLからカレンダーとテーブル構造を詳しく分析
"""

from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

def parse_yosocal_html(filename):
    """保存されたHTMLファイルを解析"""
    
    print(f"🔍 HTMLファイル解析開始: {filename}")
    print("=" * 70)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
        # 1. JavaScript関数の詳細解析
        print("🔧 === JavaScript関数解析 ===")
        analyze_javascript_functions(soup)
        
        # 2. カレンダー構造の解析
        print("\n📅 === カレンダー構造解析 ===")
        analyze_calendar_structure(soup)
        
        # 3. 待ち時間テーブルの解析
        print("\n📊 === 待ち時間テーブル解析 ===")
        analyze_wait_time_tables(soup)
    
        # 4. アトラクション一覧の抽出
        print("\n🎢 === アトラクション一覧抽出 ===")
        extract_attractions_list(soup)
    
        # 5. createAT2関数の詳細解析
        print("\n⚙️ === createAT2関数解析 ===")
        analyze_createat2_function(soup)
        
        print("\n✅ HTML解析完了")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")

def analyze_javascript_functions(soup):
    """JavaScript関数の詳細解析"""
    
    scripts = soup.find_all('script')
    print(f"📜 スクリプトタグ数: {len(scripts)}")
    
    all_js = ""
    for script in scripts:
        if script.string:
            all_js += script.string + "\n"
    
    # createAT2関数の検索
    createat2_matches = re.findall(r'function\s+createAT2.*?(?=function|\</script\>)', all_js, re.DOTALL)
    if createat2_matches:
        print(f"🎯 createAT2関数発見")
        print("=" * 50)
        for i, match in enumerate(createat2_matches[:1]):  # 最初のみ表示
            print(match[:500] + "..." if len(match) > 500 else match)
        print("=" * 50)
    
    # その他の重要な関数
    function_patterns = [
        r'function\s+cal\s*\(',
        r'function\s+changeMonth\s*\(',
        r'function\s+setDate\s*\(',
        r'function\s+loadData\s*\(',
        r'onclick\s*=\s*["\']([^"\']*)["\']'
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, all_js, re.IGNORECASE)
        if matches:
            print(f"🔧 パターン '{pattern[:20]}...': {len(matches)}件")
            for match in matches[:3]:  # 最初の3件
                print(f"   {match[:100]}")

def analyze_calendar_structure(soup):
    """カレンダー構造の解析"""
    
    # 前月・次月ボタンの検索
    month_buttons = soup.find_all('input', {'type': 'button', 'value': re.compile(r'前月|次月')})
    print(f"📅 月移動ボタン: {len(month_buttons)}個")
    
    for btn in month_buttons:
        print(f"  ボタン: value='{btn.get('value')}', onclick='{btn.get('onclick')}'")
                    
    # カレンダーテーブルの検索
    calendar_tables = soup.find_all('table')
    
    # 日付らしき要素を含むテーブルを検索
    for i, table in enumerate(calendar_tables):
        cells = table.find_all(['td', 'th'])
        date_cells = [cell for cell in cells if cell.get('onclick') and 'createAT2' in str(cell.get('onclick'))]
        
        if date_cells:
            print(f"\n📊 カレンダーテーブル発見: テーブル{i+1}")
            print(f"   日付セル数: {len(date_cells)}個")
            
            # 最初の数個の日付セルを表示
            for j, cell in enumerate(date_cells[:7]):
                text = cell.get_text(strip=True)
                onclick = cell.get('onclick')
                print(f"   日付{j+1}: '{text}' onclick='{onclick}'")
            
                            break
                        
def analyze_wait_time_tables(soup):
    """待ち時間テーブルの解析"""
    
    tables = soup.find_all('table')
                        
    # 28行のテーブル（時間帯テーブル）を検索
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        
        if len(rows) >= 25:  # 28行前後のテーブル
            print(f"\n📊 大きなテーブル発見: テーブル{i+1} ({len(rows)}行)")
            
            # 最初の行の列数確認
            if rows:
                first_row_cells = rows[0].find_all(['td', 'th'])
                print(f"   列数: {len(first_row_cells)}列")
                
                # ヘッダー行の内容
                header_texts = [cell.get_text(strip=True) for cell in first_row_cells[:10]]
                print(f"   ヘッダー: {' | '.join(header_texts)}")
    
                # 最初の数行の内容
                for j, row in enumerate(rows[1:6]):
                    row_cells = row.find_all(['td', 'th'])
                    if row_cells:
                        row_texts = [cell.get_text(strip=True) for cell in row_cells[:5]]
                        print(f"   行{j+1}: {' | '.join(row_texts)}")
                
                # アトラクション名の検索
                attraction_keywords = ['オムニバス', 'カリブ', 'スペース', 'プーさん', 'ホーンテッド']
                for keyword in attraction_keywords:
                    keyword_cells = table.find_all(['td', 'th'], string=re.compile(keyword))
                    if keyword_cells:
                        print(f"   '{keyword}' 発見: {len(keyword_cells)}個")

def extract_attractions_list(soup):
    """アトラクション一覧の抽出"""
    
    # createAT2を含むセルからアトラクション名を抽出
    onclick_cells = soup.find_all(['td', 'th'], onclick=re.compile(r'createAT2'))
    
    print(f"🎢 createAT2要素: {len(onclick_cells)}個")
    
    attractions = []
    for i, cell in enumerate(onclick_cells[:50]):  # 最初の50個
        text = cell.get_text(strip=True)
        onclick = cell.get('onclick', '')
        
        # createAT2(数字)の数字を抽出
        match = re.search(r'createAT2\((\d+)\)', onclick)
        if match:
            index = int(match.group(1))
            attractions.append({
                'index': index,
                'name': text,
                'onclick': onclick
            })
            
            if i < 20:  # 最初の20個を表示
                print(f"   {index:2d}: {text}")
    
    # インデックス順でソート
    attractions.sort(key=lambda x: x['index'])
    
    print(f"\n📋 アトラクション総数: {len(attractions)}個")
    print("🏆 ソート済みアトラクション一覧（最初の20個）:")
    for attraction in attractions[:20]:
        print(f"   {attraction['index']:2d}: {attraction['name']}")
    
    return attractions

def analyze_createat2_function(soup):
    """createAT2関数の詳細解析"""
    
    scripts = soup.find_all('script')
    
    for script in scripts:
        if script.string and 'createAT2' in script.string:
            print("🎯 createAT2関数が含まれるスクリプト発見")
            
            # 関数定義を抽出
            function_match = re.search(r'function\s+createAT2[^}]*}', script.string, re.DOTALL)
            if function_match:
                print("=" * 50)
                print(function_match.group(0))
                print("=" * 50)
    
            # 変数や配列の抽出
            array_patterns = [
                r'var\s+\w+\s*=\s*\[[^\]]*\]',
                r'var\s+\w+\s*=\s*"[^"]*"',
                r'var\s+\w+\s*=\s*\d+'
            ]
            
            for pattern in array_patterns:
                matches = re.findall(pattern, script.string)
                if matches:
                    print(f"📊 変数パターン '{pattern[:20]}...': {len(matches)}件")
                    for match in matches[:3]:
                        print(f"   {match}")

if __name__ == "__main__":
    # 最新のHTMLファイルを解析
    import glob
    html_files = glob.glob("yosocal_investigation_*.html")
    
    if html_files:
        latest_file = max(html_files)  # 最新のファイル
        parse_yosocal_html(latest_file)
    else:
        print("❌ 解析対象のHTMLファイルが見つかりません") 