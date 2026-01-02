# -*- coding: utf-8 -*-
"""
yosocal.com サイト構造詳細調査スクリプト
実際の待機時間データがどのように読み込まれているかを徹底調査
"""

import time
import re
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_investigation_driver():
    """詳細調査用のWebDriverをセットアップ"""
    print("🔧 詳細調査用Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    # ログレベルを詳細に設定
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ 詳細調査用WebDriverセットアップ完了")
    return driver

def investigate_page_structure(driver, target_date_id="cal2"):
    """ページ構造の詳細調査"""
    print(f"\n🔍 ページ構造詳細調査開始")
    print("=" * 60)
    
    try:
        # ページ読み込み
        driver.get('https://yosocal.com/')
        print("📄 yosocal.comページ読み込み完了")
        time.sleep(3)
        
        # 初期ページの分析
        print("\n📊 初期ページ分析:")
        analyze_page_content(driver, "initial_load")
        
        # 2025年6月に移動
        navigate_to_month(driver, 2025, 6)
        time.sleep(2)
        
        print(f"\n📅 {target_date_id} をクリック前の状態:")
        analyze_page_content(driver, "before_click")
        
        # 日付をクリック
        print(f"\n🖱️ {target_date_id} をクリック中...")
        click_element = driver.find_element(By.ID, target_date_id)
        driver.execute_script("arguments[0].click();", click_element)
        
        # クリック後の段階的調査
        for wait_time in [1, 3, 5, 10, 15]:
            print(f"\n⏰ クリック後 {wait_time}秒経過:")
            time.sleep(1 if wait_time == 1 else wait_time - (1 if wait_time > 1 else 0))
            analyze_page_content(driver, f"after_click_{wait_time}s")
            
            # JavaScript実行状況をチェック
            check_javascript_execution(driver)
            
            # ネットワーク活動をチェック
            check_network_activity(driver)
        
        # 最終的な詳細HTML保存
        print(f"\n💾 最終HTML状態を保存中...")
        save_detailed_html(driver, target_date_id)
        
    except Exception as e:
        print(f"❌ 調査中にエラー: {e}")
    
    return driver

def analyze_page_content(driver, stage_name):
    """ページ内容の詳細分析"""
    print(f"  🔬 {stage_name} 段階分析:")
    
    try:
        # 基本統計
        page_source = driver.page_source
        print(f"    📏 ページサイズ: {len(page_source):,} 文字")
        
        # 重要なクラスの存在確認
        important_classes = {
            'FPM': len(re.findall(r'class="FPM"', page_source)),
            'FPh2': len(re.findall(r'class="FPh2"', page_source)),
            'FXTABLE': len(re.findall(r'class="FXTABLE"', page_source)),
            'TDBT': len(re.findall(r'class="TDBT"', page_source)),
            'B0-B8': len(re.findall(r'class="B[0-8]"', page_source))
        }
        
        print(f"    📊 重要クラス出現回数:")
        for class_name, count in important_classes.items():
            status = "✅" if count > 0 else "❌"
            print(f"      {status} {class_name}: {count}")
        
        # テーブル数
        all_tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"    📋 テーブル総数: {len(all_tables)}")
        
        # div要素の調査
        all_divs = driver.find_elements(By.TAG_NAME, "div")
        jamat_divs = driver.find_elements(By.ID, "jamat")
        print(f"    📦 div総数: {len(all_divs)}, jamat div: {len(jamat_divs)}")
        
        # JavaScript関連の要素
        scripts = driver.find_elements(By.TAG_NAME, "script")
        print(f"    📜 script要素数: {len(scripts)}")
        
        # フォームとボタン
        forms = driver.find_elements(By.TAG_NAME, "form")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"    🎛️ form: {len(forms)}, button: {len(buttons)}, input: {len(inputs)}")
        
        # iframe調査
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"    🖼️ iframe数: {len(iframes)}")
        if iframes:
            for i, iframe in enumerate(iframes[:3]):  # 最初の3つのみ
                src = iframe.get_attribute('src') or 'src無し'
                print(f"      iframe {i+1}: {src}")
        
        # 時間とアトラクション名の検索
        time_patterns = re.findall(r'\b\d{1,2}:\d{2}\b', page_source)
        attraction_keywords = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ビッグサンダー', 'スペース']
        found_attractions = [kw for kw in attraction_keywords if kw in page_source]
        
        print(f"    ⏰ 時間パターン発見数: {len(time_patterns)} (例: {time_patterns[:3] if time_patterns else 'なし'})")
        print(f"    🎢 アトラクション名発見: {len(found_attractions)} (例: {found_attractions[:3] if found_attractions else 'なし'})")
        
    except Exception as e:
        print(f"    ❌ 分析エラー: {e}")

def check_javascript_execution(driver):
    """JavaScript実行状況のチェック"""
    try:
        # ページの読み込み状況
        ready_state = driver.execute_script("return document.readyState;")
        print(f"    🔧 document.readyState: {ready_state}")
        
        # jQuery の存在確認
        jquery_exists = driver.execute_script("return typeof jQuery !== 'undefined';")
        print(f"    📚 jQuery存在: {jquery_exists}")
        
        # 動的に生成される可能性のある要素をチェック
        jamat_exists = driver.execute_script("return document.getElementById('jamat') !== null;")
        print(f"    🎯 jamat要素存在: {jamat_exists}")
        
        # 待機時間テーブル関連の関数をチェック
        functions_to_check = ['createAT2', 'loadWaitTimes', 'updateTable']
        for func_name in functions_to_check:
            exists = driver.execute_script(f"return typeof {func_name} !== 'undefined';")
            if exists:
                print(f"    ⚙️ 関数 {func_name}: 存在")
        
    except Exception as e:
        print(f"    ❌ JavaScript確認エラー: {e}")

def check_network_activity(driver):
    """ネットワーク活動のチェック（可能な範囲で）"""
    try:
        # Performance APIでネットワーク活動を確認
        performance_entries = driver.execute_script("""
            var entries = performance.getEntriesByType('navigation');
            if (entries.length > 0) {
                return {
                    loadEventEnd: entries[0].loadEventEnd,
                    domContentLoaded: entries[0].domContentLoadedEventEnd,
                    responseEnd: entries[0].responseEnd
                };
            }
            return null;
        """)
        
        if performance_entries:
            print(f"    ⚡ ページ読み込み完了: {performance_entries['loadEventEnd']:.0f}ms")
            print(f"    📦 DOM読み込み完了: {performance_entries['domContentLoaded']:.0f}ms")
        
        # XHR/Fetch リクエストの検出試行
        xhr_count = driver.execute_script("""
            // XHRやfetchの活動を検出する簡易的な方法
            var xhrActive = window.XMLHttpRequest && XMLHttpRequest.prototype.open;
            var fetchActive = window.fetch;
            return {
                xhr: !!xhrActive,
                fetch: !!fetchActive
            };
        """)
        
        print(f"    🌐 XHR利用可能: {xhr_count['xhr']}, Fetch利用可能: {xhr_count['fetch']}")
        
    except Exception as e:
        print(f"    ❌ ネットワーク活動確認エラー: {e}")

def navigate_to_month(driver, year, month):
    """指定の年月に移動"""
    print(f"📅 {year}年{month}月に移動中...")
    
    max_attempts = 12
    for attempt in range(max_attempts):
        try:
            # 現在表示されている年月を確認
            month_element = driver.find_element(By.XPATH, "//td[@class='MHDT']")
            current_display = month_element.text
            
            target_text = f"{year}年{month:02d}月"
            print(f"   現在表示: {current_display}, 目標: {target_text}")
            
            if target_text in current_display or f"{year}年{month}月" in current_display:
                print(f"   ✅ 目標の {target_text} に到達")
                return True
            
            # 現在の年月を解析
            current_match = re.search(r'(\d{4})年(\d{1,2})月', current_display)
            if current_match:
                current_year = int(current_match.group(1))
                current_month = int(current_match.group(2))
                
                # 目標より前か後かを判定
                if (current_year, current_month) > (year, month):
                    # 前月に移動
                    prev_button = driver.find_element(By.XPATH, "//td[@class='MHBT'][1]/a")
                    prev_button.click()
                    print(f"   ← 前月に移動")
                else:
                    # 次月に移動
                    next_button = driver.find_element(By.XPATH, "//td[@class='MHBT'][2]/a")
                    next_button.click()
                    print(f"   → 次月に移動")
                
                time.sleep(2)
            else:
                print(f"   ❌ 現在の年月を解析できません: {current_display}")
                break
        
        except Exception as e:
            print(f"   ❌ 月移動エラー: {e}")
            break
    
    print(f"   ❌ {max_attempts}回試行後も目標月に到達できませんでした")
    return False

def save_detailed_html(driver, date_id):
    """詳細HTMLファイルの保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"yosocal_investigation_{date_id}_{timestamp}.html"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"💾 詳細HTML保存完了: {filename}")
        
        # 統計情報も保存
        stats_filename = f"yosocal_stats_{date_id}_{timestamp}.txt"
        with open(stats_filename, 'w', encoding='utf-8') as f:
            f.write(f"yosocal.com 詳細調査レポート\n")
            f.write(f"調査日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"対象日付ID: {date_id}\n")
            f.write(f"HTMLファイルサイズ: {len(driver.page_source):,} 文字\n\n")
            
            # ページ分析結果を記録
            page_source = driver.page_source
            
            # 重要なクラスの分析
            f.write("=== 重要クラス分析 ===\n")
            important_classes = {
                'FPM': len(re.findall(r'class="FPM"', page_source)),
                'FPh2': len(re.findall(r'class="FPh2"', page_source)),
                'FXTABLE': len(re.findall(r'class="FXTABLE"', page_source)),
                'TDBT': len(re.findall(r'class="TDBT"', page_source)),
                'B0-B8': len(re.findall(r'class="B[0-8]"', page_source))
            }
            
            for class_name, count in important_classes.items():
                f.write(f"{class_name}: {count} 回出現\n")
            
            # テーブル分析
            f.write(f"\n=== テーブル分析 ===\n")
            all_tables = driver.find_elements(By.TAG_NAME, "table")
            f.write(f"総テーブル数: {len(all_tables)}\n")
            
            for i, table in enumerate(all_tables[:10]):  # 最初の10個のテーブルのみ
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    cells = table.find_elements(By.TAG_NAME, "td")
                    table_text = table.text[:100].replace('\n', ' ') if table.text else ""
                    f.write(f"テーブル {i+1}: {len(rows)}行, {len(cells)}セル, テキスト: {table_text}...\n")
                except:
                    f.write(f"テーブル {i+1}: 分析エラー\n")
            
            # 検索パターン
            f.write(f"\n=== 検索パターン ===\n")
            time_patterns = re.findall(r'\b\d{1,2}:\d{2}\b', page_source)
            f.write(f"時間パターン発見数: {len(time_patterns)}\n")
            f.write(f"時間例: {time_patterns[:10]}\n")
            
            attraction_keywords = ['美女と野獣', 'ベイマックス', 'スプラッシュ', 'ビッグサンダー', 'スペース', 'ハニーハント']
            found_attractions = [kw for kw in attraction_keywords if kw in page_source]
            f.write(f"アトラクション名発見: {found_attractions}\n")
        
        print(f"📊 統計レポート保存完了: {stats_filename}")
        
    except Exception as e:
        print(f"❌ ファイル保存エラー: {e}")

def main():
    """メイン調査プロセス"""
    print("🔍 yosocal.com サイト構造詳細調査")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_investigation_driver()
        
        # 詳細調査実行
        investigate_page_structure(driver, target_date_id="cal2")  # 6月3日をターゲット
        
        print("\n✅ 詳細調査完了")
        print("💡 生成されたファイルを確認して、実際の構造を分析してください")
        
    except Exception as e:
        print(f"❌ 調査プロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 