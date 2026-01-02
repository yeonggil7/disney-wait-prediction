#!/usr/bin/env python3
"""
yosocal.com ディズニーランド専用データ取得スクリプト
ディズニーシーのアトラクションを完全に除外
"""

import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-images')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--page-load-strategy=eager')
    
    # 広告ブロック対策
    options.add_argument('--block-new-web-contents')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ WebDriverセットアップ完了")
        return driver
    except Exception as e:
        print(f"❌ WebDriverセットアップエラー: {e}")
        raise

def get_disneyland_attractions():
    """正しいディズニーランドアトラクション一覧（省略形とフル名のマッピング）"""
    return {
        'オムニバス': 'オムニバス',
        'リバ鉄道': 'ウエスタンリバー鉄道',
        'カリブの海賊': 'カリブの海賊',
        'ジャングル': 'ジャングルクルーズ',
        'ツリハウス': 'ツリーハウス',
        '魅惑のチキルム': '魅惑のチキルーム',
        'ビッグサンダ': 'ビッグサンダーマウンテン',
        'Ｓギャラリ': 'シューティングギャラリー',
        'ベア・シアタ': 'カントリーベアシアター',
        'いかだ': 'トムソーヤ島いかだ',
        'マークトゥ': '蒸気船マークトゥウェイン号',
        'スプラッシュ': 'スプラッシュマウンテン',
        'カヌー探検': 'ビーバーブラザーズのカヌー探検',
        'イッツ・ア・ス': 'イッツ・ア・スモールワールド',
        'プーさん': 'プーさんのハニーハント',
        'ホーンテッド': 'ホーンテッドマンション',
        'アリス': 'アリスのティーパーティー',
        'カルーセル': 'キャッスルカルーセル',
        'シンデレラ': 'シンデレラのフェアリーテイル・ホール',
        'ピノキオ': 'ピノキオの冒険旅行',
        'ピーターパン': 'ピーターパン空の旅',
        'フィルハー': 'ミッキーのフィルハーマジック',
        '白雪姫': '白雪姫と七人のこびと',
        'だんぼ': '空飛ぶダンボ',
        'ガジェット': 'ガジェットのゴーコースター',
        'グーフィー': 'グーフィーのペイント&プレイハウス',
        'チップデール': 'チップとデールのツリーハウス',
        'ドナルド': 'ドナルドのボート',
        'ミニーの家': 'ミニーの家',
        'カートゥーン': 'トゥーンタウン',
        'スター・ツアーズ': 'スター・ツアーズ',
        'スペマン': 'スペースマウンテン',
        'バズ': 'バズ・ライトイヤーのアストロブラスター',
        'モンスタ': 'モンスターズ・インク',
        '美女と野獣': '美女と野獣の物語',
        'ベイマックス': 'ベイマックスのハッピーライド',
        'スティッチ': 'スティッチエンカウンター'
    }

def get_disneysea_attractions():
    """除外すべきディズニーシーアトラクション（省略形）"""
    return {
        'タワ・オブ・テ', 'アクアト', 'トイマニ', 'ニモ＆フレンズ', 'タートル', 
        'マメマン', 'インディ', 'レイジング', 'ＪニーＣ', 'アクアト',
        'ビッグバンド', 'ソアリン', 'ヴェネツィア', 'アラビア', 'マーメイド',
        'エレクト', 'アブーズ', 'ジャスミン', 'フランダ', 'アリエル',
        'ゴー', 'ニモ', 'Ｓア', 'ブロホ', 'マジック', 'Ｆファン',
        'インクマン', 'ディズニー'
    }

def remove_ads(driver):
    """広告要素を削除"""
    try:
        driver.execute_script("""
            var ads = document.querySelectorAll('iframe[src*="googleads"], iframe[src*="doubleclick"]');
            for (var i = 0; i < ads.length; i++) {
                ads[i].style.display = 'none';
                ads[i].remove();
            }
            
            var adElements = document.querySelectorAll('[id*="ad"], [class*="ad"], [id*="banner"], [class*="banner"]');
            for (var i = 0; i < adElements.length; i++) {
                if (adElements[i].offsetHeight > 50 || adElements[i].offsetWidth > 200) {
                    adElements[i].style.display = 'none';
                }
            }
        """)
        print("🛡️ 広告要素を削除")
    except Exception as e:
        print(f"⚠️ 広告削除エラー: {e}")

def navigate_to_january_2025(driver):
    """2025年1月に移動"""
    print("📅 2025年1月への移動開始...")
    
    max_attempts = 20
    attempts = 0
    
    while attempts < max_attempts:
        try:
            month_element = driver.find_element(By.CLASS_NAME, "TDBT")
            month_text = month_element.text
            print(f"📅 現在表示月: {month_text}")
            
            if "2025年" in month_text and "1月" in month_text:
                print("✅ 2025年1月に到達しました！")
                return True
            
            print("⬅️ 前月ボタンをクリック...")
            prev_button = driver.find_element(By.XPATH, "//input[@value='前月']")
            driver.execute_script("arguments[0].click();", prev_button)
            time.sleep(3)
            
            remove_ads(driver)
            attempts += 1
            
        except Exception as e:
            print(f"⚠️ 月移動エラー: {e}")
            attempts += 1
            time.sleep(2)
    
    print("❌ 2025年1月への移動に失敗")
    return False

def click_date_js(driver, date_str, day):
    """JavaScript経由での確実な日付クリック"""
    try:
        remove_ads(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
        time.sleep(1)
        
        js_click = f"""
            var elements = document.querySelectorAll('[onclick*="fMouseclick({date_str},"]');
            if (elements.length > 0) {{
                elements[0].click();
                return true;
            }}
            
            var allDivs = document.querySelectorAll('div');
            for (var i = 0; i < allDivs.length; i++) {{
                var div = allDivs[i];
                if (div.textContent.trim() === '{day}') {{
                    var parent = div.parentElement;
                    if (parent && parent.onclick && parent.onclick.toString().includes('{date_str}')) {{
                        parent.click();
                        return true;
                    }}
                }}
            }}
            return false;
        """
        
        result = driver.execute_script(js_click)
        if result:
            print(f"✅ 日付{day}をクリック成功")
            return True
        else:
            print(f"❌ 日付{day}のクリック失敗")
            return False
        
    except Exception as e:
        print(f"⚠️ JSクリックエラー: {e}")
        return False

def extract_disneyland_only_data(driver, target_date):
    """ディズニーランドのみのデータを抽出"""
    try:
        time.sleep(3)
        
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        jamat_div = soup.find('div', {'id': 'jamat'})
        if not jamat_div:
            print("❌ jamatテーブルが見つかりません")
            return []
        
        table = jamat_div.find('table')
        if not table:
            print("❌ テーブルが見つかりません")
            return []
        
        rows = table.find_all('tr')
        
        # 正しいディズニーランドアトラクション
        disneyland_attractions = get_disneyland_attractions()
        disneysea_attractions = get_disneysea_attractions()
        
        all_data = []
        disneyland_count = 0
        disneysea_count = 0
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) <= 1:
                continue
            
            time_cell = cells[0]
            time_text = time_cell.get_text(strip=True)
            
            if not time_text or ':' not in time_text:
                continue
            
            print(f"🕐 時間帯: {time_text}")
            
            data_cells = cells[1:]
            cell_index = 0
            
            for cell in data_cells:
                cell_text = cell.get_text(strip=True)
                css_classes = cell.get('class', [])
                
                # セルから推定されるアトラクション名（簡易的な方法）
                # 実際には位置やCSSクラスから判断する必要があります
                
                # ディズニーランドアトラクションのみを抽出
                # この部分は、実際のHTMLの構造に応じて調整が必要です
                if cell_index < len(disneyland_attractions):
                    attraction_keys = list(disneyland_attractions.keys())
                    if cell_index < len(attraction_keys):
                        attraction_short = attraction_keys[cell_index]
                        attraction_full = disneyland_attractions[attraction_short]
                        
                        # ディズニーシーアトラクションは除外
                        if attraction_short not in disneysea_attractions:
                            wait_time = cell_text if cell_text and cell_text != '-' else '-'
                            status = 'active' if wait_time != '-' and wait_time.replace('.', '').isdigit() else 'no_data'
                            
                            all_data.append({
                                'Attraction': attraction_full,
                                'AttractionShort': attraction_short,
                                'WaitTime': wait_time,
                                'Status': status,
                                'Time': time_text,
                                'Date': target_date,
                                'CSSClasses': ' '.join(css_classes) if css_classes else '',
                                'RawValue': cell_text
                            })
                            disneyland_count += 1
                        else:
                            disneysea_count += 1
                            print(f"⚠️ ディズニーシーアトラクションを除外: {attraction_short}")
                
                cell_index += 1
        
        print(f"📊 抽出データ数: {len(all_data)}件")
        print(f"🏰 ディズニーランド: {disneyland_count}件")
        print(f"🌊 除外ディズニーシー: {disneysea_count}件")
        valid_count = len([d for d in all_data if d['WaitTime'] != '-'])
        print(f"✅ 有効待ち時間: {valid_count}件")
        
        return all_data
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return []

def save_to_csv(data, filename):
    """CSVファイルに保存"""
    try:
        os.makedirs('data', exist_ok=True)
        
        df = pd.DataFrame(data)
        filepath = os.path.join('data', filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        print(f"💾 {filepath} に保存完了")
        return True
    except Exception as e:
        print(f"❌ CSV保存エラー: {e}")
        return False

def scrape_disneyland_only():
    """ディズニーランド専用データ取得メイン処理"""
    print("🏰 ディズニーランド専用データ取得開始")
    print("📅 対象: 1月1日〜12日（ディズニーシー除外版）")
    print("=" * 60)
    
    driver = setup_driver()
    
    try:
        # realtime.htmに接続
        print("🌐 realtime.htmに接続中...")
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(5)
        
        # ディズニーランド選択確認
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
            print("✅ ディズニーランド選択確認")
        except Exception as e:
            print(f"⚠️ パーク選択失敗: {e}")
        
        # 初期読み込み待機と広告削除
        time.sleep(3)
        remove_ads(driver)
        
        # 2025年1月に移動
        if not navigate_to_january_2025(driver):
            print("❌ 2025年1月への移動に失敗しました")
            return
        
        # 現在取得可能な日付（1月1日〜12日）
        current_available_days = list(range(1, 13))
        print(f"📅 処理対象: {len(current_available_days)}日")
        
        success_count = 0
        error_count = 0
        
        for day in current_available_days:
            date_str = f"2025{1:02d}{day:02d}"
            filename = f"yosocal_disneyland_{date_str}.csv"
            filepath = os.path.join('data', filename)
            
            # 既存ファイルチェック（実際の存在確認）
            if os.path.exists(filepath):
                print(f"📁 1月{day:02d}日: 既存ファイルをスキップ")
                success_count += 1
                continue
            
            print(f"🔄 1月{day:02d}日: 処理中...")
            
            # 日付をクリック
            if click_date_js(driver, date_str, str(day)):
                # ディズニーランドのみのデータ抽出
                data = extract_disneyland_only_data(driver, date_str)
                
                if data and len(data) > 0:
                    # CSV保存
                    if save_to_csv(data, filename):
                        valid_count = len([d for d in data if d['WaitTime'] != '-'])
                        print(f"✅ 1月{day:02d}日: {len(data)}件 (有効: {valid_count}件)")
                        success_count += 1
                    else:
                        print(f"❌ 1月{day:02d}日: 保存失敗")
                        error_count += 1
                else:
                    print(f"❌ 1月{day:02d}日: データなし")
                    error_count += 1
            else:
                print(f"❌ 1月{day:02d}日: 日付クリック失敗")
                error_count += 1
            
            # 次の処理まで待機
            time.sleep(2)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print(f"🎉 ディズニーランド専用データの処理完了！")
        print(f"✅ 成功: {success_count}日")
        print(f"❌ エラー: {error_count}日")
        total_days = success_count + error_count
        success_rate = (success_count / total_days * 100) if total_days > 0 else 0
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"📁 保存場所: ./data/ フォルダ")
        print(f"🏰 ディズニーランドアトラクションのみ抽出")
        
    except Exception as e:
        print(f"❌ 処理エラー: {e}")
    finally:
        print("🔧 WebDriver終了...")
        driver.quit()

if __name__ == "__main__":
    scrape_disneyland_only() 