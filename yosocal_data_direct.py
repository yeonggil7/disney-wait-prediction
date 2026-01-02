import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import json

def extract_js_data():
    """yosocal.comのJavaScriptデータを抽出"""
    
    url = "https://yosocal.com/realtime.htm"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("🌐 yosocal.comからデータを取得中...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 全てのscriptタグを調査
        scripts = soup.find_all('script')
        
        data_arrays = {}
        
        for script in scripts:
            script_text = script.get_text()
            
            # 配列データを抽出（MB, MD, ME, MJ, MF, MP, MR, MG, MW, MT）
            array_patterns = [
                (r'MB=new Array\((.*?)\);', 'MB'),
                (r'MD=new Array\((.*?)\);', 'MD'),
                (r'ME=new Array\((.*?)\);', 'ME'),
                (r'MJ=new Array\((.*?)\);', 'MJ'),
                (r'MF=new Array\((.*?)\);', 'MF'),
                (r'MP=new Array\((.*?)\);', 'MP'),
                (r'MR=new Array\((.*?)\);', 'MR'),
                (r'MG=new Array\((.*?)\);', 'MG'),
                (r'MW=new Array\((.*?)\);', 'MW'),
                (r'MT=new Array\((.*?)\);', 'MT'),
            ]
            
            for pattern, name in array_patterns:
                match = re.search(pattern, script_text, re.DOTALL)
                if match:
                    array_content = match.group(1)
                    print(f"✅ {name} 配列データ発見")
                    data_arrays[name] = array_content
            
            # データファイルの読み込み部分を探す
            if 'fileName' in script_text and 'XMLHttpRequest' in script_text:
                print("🔍 データファイル読み込み部分を発見")
                
                # ファイル名の抽出を試みる
                filename_matches = re.findall(r'fileName\s*=\s*["\']([^"\']+)["\']', script_text)
                for filename in filename_matches:
                    print(f"📁 データファイル候補: {filename}")
        
        # MTデータ（時間データ）を解析
        if 'MT' in data_arrays:
            mt_content = data_arrays['MT']
            # 時間データを抽出
            time_pattern = r'"(\d{2}:\d{2})"'
            times = re.findall(time_pattern, mt_content)
            print(f"⏰ 時間データ: {len(times)}個")
            print(f"   例: {times[:5]}")
        
        return data_arrays
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return {}

def try_data_files():
    """データファイルへの直接アクセスを試みる"""
    
    base_url = "https://yosocal.com/"
    common_files = [
        "data.js",
        "realtime.js", 
        "data.txt",
        "realtime.txt",
        "data.csv",
        f"data{datetime.now().strftime('%Y%m%d')}.js",
        f"rt{datetime.now().strftime('%Y%m%d')}.js",
        f"jam{datetime.now().strftime('%Y%m%d')}.js",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://yosocal.com/realtime.htm'
    }
    
    print(f"\n🔍 データファイルの直接アクセスを試行:")
    
    for file in common_files:
        try:
            url = base_url + file
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {file} - アクセス成功 ({len(response.content)} bytes)")
                
                # 内容を少し表示
                content_preview = response.text[:200].replace('\n', ' ')
                print(f"   内容プレビュー: {content_preview}...")
                
                # CSVまたはJSファイルの場合、保存
                if file.endswith(('.csv', '.js', '.txt')):
                    with open(f"yosocal_{file}", 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"   💾 {file} を保存しました")
                
            else:
                print(f"❌ {file} - {response.status_code}")
                
        except Exception as e:
            print(f"❌ {file} - エラー: {e}")

def analyze_page_network():
    """ページのネットワーク要求を分析"""
    
    url = "https://yosocal.com/realtime.htm"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"\n🔍 ページ分析:")
        response = requests.get(url, headers=headers, timeout=30)
        
        # レスポンスヘッダーを確認
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {response.headers.get('content-length')}")
        
        # HTMLの中から外部リソースのURLを抽出
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # script srcを探す
        external_scripts = [script.get('src') for script in soup.find_all('script') if script.get('src')]
        print(f"📜 外部スクリプト数: {len(external_scripts)}")
        
        for script_url in external_scripts[:5]:  # 最初の5個
            print(f"   {script_url}")
            
        # CSS linkを探す
        css_links = [link.get('href') for link in soup.find_all('link') if link.get('href')]
        print(f"🎨 CSS/リンク数: {len(css_links)}")
        
        # 画像を探す
        images = [img.get('src') for img in soup.find_all('img') if img.get('src')]
        print(f"🖼️ 画像数: {len(images)}")
        
    except Exception as e:
        print(f"❌ ページ分析エラー: {e}")

def main():
    """メイン実行関数"""
    print("🏰 yosocal.com データ直接取得実験")
    print("=" * 80)
    
    # 1. JavaScriptデータの抽出
    js_data = extract_js_data()
    
    # 2. データファイルへの直接アクセス
    try_data_files()
    
    # 3. ページ分析
    analyze_page_network()
    
    print(f"\n📊 結果まとめ:")
    print(f"JavaScript配列データ: {len(js_data)}個")
    
    if js_data:
        print("取得された配列:")
        for name in js_data.keys():
            content_length = len(js_data[name])
            print(f"  {name}: {content_length} 文字")

if __name__ == "__main__":
    main() 