# -*- coding: utf-8 -*-
"""
yosocal.com/realtime.htm ページ専用調査スクリプト
実際のリアルタイム待機時間データページの構造を詳細に分析
"""

import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_realtime_driver():
    """リアルタイムページ調査用WebDriverセットアップ"""
    print("🔧 realtime.htm調査用Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ realtime.htm調査用WebDriverセットアップ完了")
    return driver

def investigate_realtime_page(driver):
    """realtime.htmページの詳細調査"""
    print(f"\n🔍 realtime.htmページ詳細調査開始")
    print("=" * 60)
    
    try:
        # realtime.htmページに直接アクセス
        print("📄 https://yosocal.com/realtime.htm に直接アクセス中...")
        driver.get('https://yosocal.com/realtime.htm')
        time.sleep(5)
        
        # 初期ページの分析
        print("\n📊 realtime.htm初期ページ分析:")
        analyze_realtime_content(driver, "initial_load")
        
        # 日付クリックが必要かどうか確認
        print("\n🔍 日付選択要素の検索...")
        date_elements = driver.find_elements(By.XPATH, "//td[contains(@id, 'cal')]")
        if date_elements:
            print(f"   📅 {len(date_elements)} 個の日付要素を発見")
            
            # 最初の日付をクリックしてみる
            target_date = date_elements[2] if len(date_elements) > 2 else date_elements[0]
            date_id = target_date.get_attribute('id')
            print(f"   🖱️ {date_id} をクリック中...")
            
            driver.execute_script("arguments[0].click();", target_date)
            time.sleep(3)
            
            print(f"\n📊 {date_id} クリック後の分析:")
            analyze_realtime_content(driver, f"after_click_{date_id}")
            
            # さらに待機して動的読み込みを確認
            for wait_time in [5, 10]:
                time.sleep(wait_time - (5 if wait_time == 10 else 0))
                print(f"\n📊 {date_id} クリック後 {wait_time}秒経過:")
                analyze_realtime_content(driver, f"after_click_{date_id}_{wait_time}s")
        else:
            print("   ❌ 日付要素が見つかりません")
        
        # 最終HTML保存
        print(f"\n💾 realtime.htm最終HTML状態を保存中...")
        save_realtime_html(driver)
        
    except Exception as e:
        print(f"❌ realtime.htm調査中にエラー: {e}")
    
    return driver

def analyze_realtime_content(driver, stage_name):
    """realtime.htmページ内容の詳細分析"""
    print(f"  🔬 {stage_name} 段階分析:")
    
    try:
        # 基本統計
        page_source = driver.page_source
        print(f"    📏 ページサイズ: {len(page_source):,} 文字")
        
        # 待機時間関連の重要なクラスの存在確認
        important_classes = {
            'FPM': len(re.findall(r'class="FPM"', page_source)),
            'FPh2': len(re.findall(r'class="FPh2"', page_source)),
            'FXTABLE': len(re.findall(r'class="FXTABLE"', page_source)),
            'TDBT': len(re.findall(r'class="TDBT"', page_source)),
            'B0': len(re.findall(r'class="B0"', page_source)),
            'B1': len(re.findall(r'class="B1"', page_source)),
            'B2': len(re.findall(r'class="B2"', page_source)),
            'B3': len(re.findall(r'class="B3"', page_source)),
            'B4': len(re.findall(r'class="B4"', page_source)),
            'B6': len(re.findall(r'class="B6"', page_source)),
            'B8': len(re.findall(r'class="B8"', page_source)),
            'FPT': len(re.findall(r'class="FPT"', page_source)),
            'FPh': len(re.findall(r'class="FPh"', page_source))
        }
        
        print(f"    📊 待機時間関連クラス出現回数:")
        for class_name, count in important_classes.items():
            status = "✅" if count > 0 else "❌"
            print(f"      {status} {class_name}: {count}")
        
        # jamat div の存在確認
        jamat_divs = driver.find_elements(By.ID, "jamat")
        print(f"    🎯 jamat div数: {len(jamat_divs)}")
        
        # テーブル数
        all_tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"    📋 テーブル総数: {len(all_tables)}")
        
        # 特別なテーブルの検索
        for i, table in enumerate(all_tables[:5]):
            try:
                table_text = table.text[:100].replace('\n', ' ') if table.text else ""
                table_html = table.get_attribute('outerHTML')[:200] if table.get_attribute('outerHTML') else ""
                
                # 待機時間テーブルの特徴をチェック
                has_fpm = 'FPM' in table_html
                has_fph2 = 'FPh2' in table_html
                has_b_classes = any(f'B{i}' in table_html for i in [0,1,2,3,4,6,8])
                has_time_pattern = bool(re.search(r'\d{1,2}:\d{2}', table_text))
                
                if has_fpm or has_fph2 or has_b_classes or has_time_pattern:
                    print(f"    🎯 注目テーブル {i+1}: FPM={has_fpm}, FPh2={has_fph2}, B_class={has_b_classes}, 時間={has_time_pattern}")
                    print(f"       テキスト: {table_text}...")
                    print(f"       HTML: {table_html}...")
            except:
                continue
        
        # アトラクション名と時間パターンの検索
        attraction_keywords = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ビッグサンダー', 'スペース', 'ハニーハント', 'ホーンテッド']
        found_attractions = [kw for kw in attraction_keywords if kw in page_source]
        
        time_patterns = re.findall(r'\b\d{1,2}:\d{2}\b', page_source)
        
        print(f"    ⏰ 時間パターン発見数: {len(time_patterns)} (例: {time_patterns[:5] if time_patterns else 'なし'})")
        print(f"    🎢 アトラクション名発見: {len(found_attractions)} (例: {found_attractions[:5] if found_attractions else 'なし'})")
        
        # JavaScript実行状況確認
        ready_state = driver.execute_script("return document.readyState;")
        jamat_exists = driver.execute_script("return document.getElementById('jamat') !== null;")
        
        print(f"    🔧 document.readyState: {ready_state}")
        print(f"    🎯 jamat要素存在: {jamat_exists}")
        
    except Exception as e:
        print(f"    ❌ 分析エラー: {e}")

def save_realtime_html(driver):
    """realtime.htmページのHTML保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"yosocal_realtime_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"💾 realtime.htm詳細HTML保存完了: {filename}")
        
        # 統計情報も保存
        stats_filename = f"yosocal_realtime_stats_{timestamp}.txt"
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"yosocal.com/realtime.htm 詳細調査レポート\n")
            f.write(f"調査日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"HTMLファイルサイズ: {len(driver.page_source):,} 文字\n\n")
            
            page_source = driver.page_source
            
            # 重要なクラスの分析
            f.write("=== 待機時間関連クラス分析 ===\n")
            important_classes = {
                'FPM': len(re.findall(r'class="FPM"', page_source)),
                'FPh2': len(re.findall(r'class="FPh2"', page_source)),
                'FXTABLE': len(re.findall(r'class="FXTABLE"', page_source)),
                'TDBT': len(re.findall(r'class="TDBT"', page_source)),
                'B0': len(re.findall(r'class="B0"', page_source)),
                'B1': len(re.findall(r'class="B1"', page_source)),
                'B2': len(re.findall(r'class="B2"', page_source)),
                'B3': len(re.findall(r'class="B3"', page_source)),
                'B4': len(re.findall(r'class="B4"', page_source)),
                'B6': len(re.findall(r'class="B6"', page_source)),
                'B8': len(re.findall(r'class="B8"', page_source))
            }
            
            for class_name, count in important_classes.items():
                f.write(f"{class_name}: {count} 回出現\n")
            
            # アトラクション検索
            f.write(f"\n=== アトラクション名検索 ===\n")
            attraction_keywords = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ビッグサンダー', 'スペース', 'ハニーハント']
            found_attractions = [kw for kw in attraction_keywords if kw in page_source]
            f.write(f"発見されたアトラクション名: {found_attractions}\n")
            
            # 時間パターン
            time_patterns = re.findall(r'\b\d{1,2}:\d{2}\b', page_source)
            f.write(f"\n=== 時間パターン ===\n")
            f.write(f"時間パターン発見数: {len(time_patterns)}\n")
            f.write(f"例: {time_patterns[:20]}\n")
        
        print(f"📊 realtime.htm統計レポート保存完了: {stats_filename}")
        
    except Exception as e:
        print(f"❌ ファイル保存エラー: {e}")

def main():
    """メイン調査プロセス"""
    print("🔍 yosocal.com/realtime.htm ページ詳細調査")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_realtime_driver()
        
        # realtime.htm詳細調査実行
        investigate_realtime_page(driver)
        
        print("\n✅ realtime.htm詳細調査完了")
        print("💡 生成されたファイルを確認して、実際の待機時間データ構造を分析してください")
        
    except Exception as e:
        print(f"❌ 調査プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 