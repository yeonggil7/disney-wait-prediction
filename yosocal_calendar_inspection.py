#!/usr/bin/env python3
"""
yosocal.com カレンダー要素の詳細検査
利用可能な全ての日付を調査
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import time
import re
from datetime import datetime

def setup_driver_with_adblock():
    """広告ブロック対応Chrome WebDriverの設定"""
    options = Options()
    
    # 基本設定
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 広告ブロック設定
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-default-apps')
    
    # 広告関連ドメインをブロック
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "popups": 2,
            "media_stream": 2,
        }
    }
    options.add_experimental_option("prefs", prefs)
    
    # User-Agent設定
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(30)
    
    # 広告スクリプトをブロック
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*googlesyndication.com*",
            "*doubleclick.net*",
            "*googleadservices.com*",
            "*google-analytics.com*",
            "*googletagmanager.com*",
            "*facebook.com/tr*",
            "*ads*",
            "*adnxs.com*"
        ]
    })
    driver.execute_cdp_cmd('Network.enable', {})
    
    return driver

def remove_ads(driver):
    """広告要素を除去"""
    ad_removal_script = """
    // 広告iframeを除去
    var iframes = document.querySelectorAll('iframe');
    var removedCount = 0;
    iframes.forEach(function(iframe) {
        var src = iframe.src || '';
        var id = iframe.id || '';
        if (src.includes('googlesyndication') || 
            src.includes('doubleclick') || 
            src.includes('googleads') ||
            id.includes('aswift') ||
            iframe.getAttribute('sandbox')) {
            iframe.remove();
            removedCount++;
        }
    });
    
    // 広告div除去
    var adDivs = document.querySelectorAll('div[id*="ad"], div[class*="ad"]');
    adDivs.forEach(function(div) {
        if (div.offsetHeight > 100 || div.offsetWidth > 100) {
            div.style.display = 'none';
            removedCount++;
        }
    });
    
    return removedCount;
    """
    
    try:
        removed_count = driver.execute_script(ad_removal_script)
        print(f"  ✅ {removed_count}個の広告要素を除去")
    except Exception as e:
        print(f"  ⚠️ 広告除去エラー: {e}")

def parse_calendar_date(onclick_attr):
    """onclickから日付情報を抽出"""
    try:
        # fMouseclick(20250629,0) から 20250629 を抽出
        match = re.search(r'fMouseclick\((\d{8}),\d+\)', onclick_attr)
        if match:
            date_str = match.group(1)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            return year, month, day, f"{year}-{month:02d}-{day:02d}"
    except:
        pass
    return None, None, None, None

def get_day_type(day_of_week):
    """曜日から日本語の曜日を取得"""
    days = ["月", "火", "水", "木", "金", "土", "日"]
    return days[day_of_week]

def main():
    """メイン実行関数"""
    print("🔍 yosocal.com カレンダー要素詳細検査")
    print("=" * 70)
    
    base_url = "https://yosocal.com/realtime.htm"
    driver = setup_driver_with_adblock()
    
    try:
        print(f"🌐 アクセス中: {base_url}")
        driver.get(base_url)
        
        # ページロード待機
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        # 広告要素を除去
        remove_ads(driver)
        print("✅ ページロード完了（広告除去済み）")
        
        # カレンダー要素を検出
        print("\n📅 カレンダー要素検出中...")
        
        calendar_elements = []
        selectors = [
            "div.BOXA[onclick*='fMouseclick']",
            "div.BOXA",
            "div.BOX[onclick*='fMouseclick']", 
            "div.BOX",
            "[onclick*='fMouseclick']"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    onclick = element.get_attribute('onclick')
                    if onclick and 'fMouseclick' in onclick:
                        calendar_elements.append(element)
            except Exception as e:
                print(f"  セレクター {selector} エラー: {e}")
                continue
        
        # 重複除去
        unique_elements = []
        seen_onclick = set()
        for elem in calendar_elements:
            onclick = elem.get_attribute('onclick')
            if onclick not in seen_onclick:
                unique_elements.append(elem)
                seen_onclick.add(onclick)
        
        print(f"📅 カレンダー要素: {len(unique_elements)}個発見")
        print("\n📋 利用可能な全日付一覧:")
        print("-" * 70)
        
        # 日付でソート
        dates_info = []
        for elem in unique_elements:
            onclick = elem.get_attribute('onclick')
            text = elem.text.strip()
            class_name = elem.get_attribute('class')
            
            year, month, day, date_str = parse_calendar_date(onclick)
            if year and month and day:
                # 曜日を計算
                try:
                    date_obj = datetime(year, month, day)
                    day_of_week = get_day_type(date_obj.weekday())
                    dates_info.append({
                        'date': date_obj,
                        'date_str': date_str,
                        'year': year,
                        'month': month,
                        'day': day,
                        'day_of_week': day_of_week,
                        'class': class_name,
                        'text': text,
                        'onclick': onclick
                    })
                except:
                    pass
        
        # 日付でソート
        dates_info.sort(key=lambda x: x['date'])
        
        # 月別で整理して表示
        current_month = None
        january_found = False
        
        for info in dates_info:
            if current_month != info['month']:
                current_month = info['month']
                print(f"\n📅 {info['year']}年{info['month']}月:")
                
                if info['month'] == 1:
                    january_found = True
            
            jam_info = ""
            lines = info['text'].split('\n')
            if len(lines) > 1:
                jam_info = f" (混雑度: {lines[1]})"
            
            print(f"  {info['date_str']} ({info['day_of_week']}) - クラス: {info['class']}{jam_info}")
            
        # 1月データの存在確認
        print("\n" + "=" * 70)
        if january_found:
            print("✅ 1月のデータが見つかりました！")
            
            # 1月1日があるかチェック
            jan_1_found = any(info['month'] == 1 and info['day'] == 1 for info in dates_info)
            if jan_1_found:
                print("🎯 1月1日のデータが利用可能です！")
            else:
                print("❌ 1月1日のデータは見つかりませんでした")
                jan_days = [info['day'] for info in dates_info if info['month'] == 1]
                print(f"📋 1月の利用可能日: {sorted(jan_days)}")
        else:
            print("❌ 1月のデータは見つかりませんでした")
            
        print(f"\n📊 利用可能期間: {dates_info[0]['date_str']} ~ {dates_info[-1]['date_str']}")
        
    except Exception as e:
        print(f"❌ エラー発生: {e}")
        
    finally:
        driver.quit()
        print("🛑 WebDriver終了")

if __name__ == "__main__":
    main() 