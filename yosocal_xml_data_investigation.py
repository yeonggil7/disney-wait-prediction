# -*- coding: utf-8 -*-
"""
yosocal.com XMLファイル直接アクセス調査システム
時間帯データの直接取得テスト
"""

import requests
import time
from datetime import datetime
import csv
import re

def test_xml_access():
    """XMLファイル直接アクセステスト"""
    print("🔍 yosocal.com XMLファイル直接アクセス調査")
    print("=" * 70)
    
    # XMLファイル候補
    xml_files = [
        'date.xml',
        'cal.xml', 
        'logat.xml',
        'logwh.xml',
        'date2024.xml',
        'cal2024.xml',
        'logat2024.xml',
        'logwh2024.xml'
    ]
    
    base_url = 'https://yosocal.com/'
    
    # セッション作成
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/xml,text/xml,*/*',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Referer': 'https://yosocal.com/realtime.htm'
    })
    
    successful_files = []
    
    for xml_file in xml_files:
        try:
            print(f"\n📂 {xml_file} アクセステスト:")
            
            # タイムスタンプ付きでアクセス
            timestamp = int(time.time() * 1000)
            url = f"{base_url}{xml_file}?time={timestamp}"
            
            print(f"   🌐 URL: {url}")
            
            # XMLファイル取得
            response = session.get(url, timeout=10)
            
            print(f"   📊 ステータス: {response.status_code}")
            print(f"   📦 サイズ: {len(response.content)} bytes")
            print(f"   📋 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200 and len(response.content) > 0:
                print(f"   ✅ アクセス成功！")
                
                # レスポンス内容を保存
                content = response.text
                print(f"   📝 内容プレビュー:")
                print(f"      先頭100文字: {content[:100]}")
                print(f"      末尾100文字: {content[-100:]}")
                
                # ファイル保存
                output_file = f"yosocal_{xml_file.replace('.xml', '')}_data.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"   💾 保存: {output_file}")
                
                # データ構造分析
                analyze_xml_content(content, xml_file)
                
                successful_files.append(xml_file)
                
            else:
                print(f"   ❌ アクセス失敗")
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
        
        time.sleep(1)  # レート制限対策
    
    print(f"\n📊 結果サマリー:")
    print(f"   ✅ 成功ファイル: {len(successful_files)}個")
    for file in successful_files:
        print(f"      - {file}")
    
    print(f"\n⚡ XMLファイル調査完了！")

def analyze_xml_content(content, filename):
    """XML内容分析"""
    print(f"   🔍 {filename} 構造分析:")
    
    # データの行数
    lines = content.split('\n')
    print(f"      行数: {len(lines)}行")
    
    # バックスラッシュ区切りの可能性
    backslash_parts = content.split('\\')
    print(f"      \\ 区切り: {len(backslash_parts)}個")
    
    # カンマ区切りデータの可能性
    comma_parts = content.split(',')
    print(f"      , 区切り: {len(comma_parts)}個")
    
    # 時間パターンの検索
    time_patterns = re.findall(r'\d{1,2}:\d{2}', content)
    if time_patterns:
        unique_times = list(set(time_patterns))
        print(f"      時間パターン: {len(unique_times)}個")
        print(f"      例: {unique_times[:5]}")
    
    # 数値パターンの検索
    numbers = re.findall(r'\b\d+\b', content)
    if numbers:
        print(f"      数値: {len(numbers)}個")
        print(f"      例: {numbers[:10]}")
    
    # 日本語文字の検索
    japanese = re.findall(r'[ひらがなカタカナ漢字]+', content)
    if japanese:
        unique_japanese = list(set(japanese))
        print(f"      日本語: {len(unique_japanese)}個")
        print(f"      例: {unique_japanese[:5]}")

def parse_xml_data(xml_content, data_type):
    """XMLデータパース（予想される形式）"""
    try:
        # バックスラッシュ区切りでデータを分割
        records = xml_content.split('\\')
        parsed_data = []
        
        for record in records:
            if record.strip():
                # カンマ区切りでフィールド分割
                fields = record.split(',')
                if len(fields) > 1:
                    parsed_data.append(fields)
        
        return parsed_data
        
    except Exception as e:
        print(f"   ❌ パースエラー: {e}")
        return []

if __name__ == "__main__":
    test_xml_access() 