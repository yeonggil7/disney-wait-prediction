# -*- coding: utf-8 -*-
"""
yosocal.com JavaScript月移動機能テスト
Fnc_L関数を使った月移動をテストし、2024年1月-2025年6月の各月にアクセスできるか確認
"""

import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """WebDriverセットアップ"""
    print("🔧 Chrome WebDriverをセットアップ中...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # automation detectionを回避
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ WebDriverセットアップ完了")
    return driver

def get_current_month(driver):
    """現在表示されている年月を取得"""
    try:
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '年') and contains(text(), '月')]")
        if month_elements:
            return month_elements[0].text.strip()
        return "不明"
    except:
        return "不明"

def test_javascript_month_navigation(driver):
    """JavaScript関数Fnc_Lを使った月移動をテスト"""
    print("\n🔧 JavaScript月移動機能テスト")
    print("=" * 50)
    
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(5)
        
        initial_month = get_current_month(driver)
        print(f"📅 初期月: {initial_month}")
        
        # 前月に移動してみる
        print(f"\n⬅️ 前月移動テスト")
        try:
            # Fnc_L関数を使って前月に移動
            js_code = "Fnc_L(new Date(zzDate.getFullYear(),zzDate.getMonth()-1,zzDate.getDate()))"
            print(f"JavaScript実行: {js_code}")
            driver.execute_script(js_code)
            time.sleep(5)
            
            new_month = get_current_month(driver)
            print(f"結果: {initial_month} → {new_month}")
            
            if new_month != initial_month:
                print(f"✅ 前月移動成功！")
                return True
            else:
                print(f"❌ 前月移動失敗")
                
        except Exception as e:
            print(f"❌ 前月移動エラー: {e}")
            
        # 元の月に戻す
        driver.get('https://yosocal.com/')
        time.sleep(3)
        
        # 次月に移動してみる  
        print(f"\n➡️ 次月移動テスト")
        try:
            js_code = "Fnc_L(new Date(zzDate.getFullYear(),zzDate.getMonth()+1,zzDate.getDate()))"
            print(f"JavaScript実行: {js_code}")
            driver.execute_script(js_code)
            time.sleep(5)
            
            new_month = get_current_month(driver)
            print(f"結果: {initial_month} → {new_month}")
            
            if new_month != initial_month:
                print(f"✅ 次月移動成功！")
                return True
            else:
                print(f"❌ 次月移動失敗")
                
        except Exception as e:
            print(f"❌ 次月移動エラー: {e}")
            
    except Exception as e:
        print(f"❌ JavaScript月移動テストエラー: {e}")
    
    return False

def test_specific_date_navigation(driver):
    """特定の年月日に直接移動するテスト"""
    print("\n📅 特定日付移動テスト")
    print("=" * 50)
    
    try:
        # メインページにアクセス
        driver.get('https://yosocal.com/')
        time.sleep(5)
        
        # テスト対象の年月
        test_dates = [
            (2024, 1, 1, "2024年1月"),   # 目標開始日
            (2024, 6, 1, "2024年6月"),   # 中間
            (2024, 12, 1, "2024年12月"), # 2024年末
            (2025, 1, 1, "2025年1月"),   # 2025年始
            (2025, 6, 1, "2025年6月"),   # 目標終了月
        ]
        
        successful_dates = []
        
        for year, month, day, description in test_dates:
            try:
                print(f"\n🎯 {description} テスト中...")
                
                # JavaScriptで特定の日付に移動
                js_code = f"Fnc_L(new Date({year}, {month-1}, {day}))"
                print(f"JavaScript実行: {js_code}")
                driver.execute_script(js_code)
                time.sleep(5)
                
                current_month = get_current_month(driver)
                print(f"結果: {current_month}")
                
                # 成功判定
                if str(year) in current_month and str(month) in current_month:
                    print(f"✅ {description} アクセス成功！")
                    successful_dates.append(description)
                else:
                    print(f"❌ {description} アクセス失敗")
                
                # 元のページに戻す
                driver.get('https://yosocal.com/')
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ {description} テストエラー: {e}")
        
        print(f"\n📊 成功した日付移動:")
        for date in successful_dates:
            print(f"   ✅ {date}")
        
        return len(successful_dates) > 0
        
    except Exception as e:
        print(f"❌ 特定日付移動テストエラー: {e}")
        return False

def test_target_period_access(driver):
    """目標期間（2024年1月-2025年6月）の全月アクセステスト"""
    print("\n🎯 目標期間全月アクセステスト")
    print("=" * 50)
    
    try:
        # 2024年1月から2025年6月までの全月
        months_to_test = []
        
        # 2024年1-12月
        for month in range(1, 13):
            months_to_test.append((2024, month, f"2024年{month}月"))
        
        # 2025年1-6月
        for month in range(1, 7):
            months_to_test.append((2025, month, f"2025年{month}月"))
        
        print(f"📋 テスト対象: {len(months_to_test)}ヶ月")
        
        accessible_months = []
        failed_months = []
        
        for year, month, description in months_to_test:
            try:
                print(f"\n📅 {description} テスト中...")
                
                # メインページに戻る
                driver.get('https://yosocal.com/')
                time.sleep(3)
                
                # 特定の月に移動
                js_code = f"Fnc_L(new Date({year}, {month-1}, 1))"
                driver.execute_script(js_code)
                time.sleep(5)
                
                current_month = get_current_month(driver)
                print(f"   結果: {current_month}")
                
                # 成功判定
                if str(year) in current_month and str(month) in current_month:
                    print(f"   ✅ アクセス成功")
                    accessible_months.append(description)
                else:
                    print(f"   ❌ アクセス失敗")
                    failed_months.append(description)
                
            except Exception as e:
                print(f"   ❌ エラー: {e}")
                failed_months.append(description)
        
        print(f"\n📊 アクセステスト結果:")
        print(f"   ✅ 成功: {len(accessible_months)}ヶ月")
        print(f"   ❌ 失敗: {len(failed_months)}ヶ月")
        
        if accessible_months:
            print(f"\n✅ アクセス可能な月:")
            for month in accessible_months[:10]:  # 最初の10個を表示
                print(f"   - {month}")
            if len(accessible_months) > 10:
                print(f"   ... 他{len(accessible_months)-10}ヶ月")
        
        if failed_months:
            print(f"\n❌ アクセス失敗した月:")
            for month in failed_months[:10]:  # 最初の10個を表示
                print(f"   - {month}")
            if len(failed_months) > 10:
                print(f"   ... 他{len(failed_months)-10}ヶ月")
        
        return len(accessible_months) > 0
        
    except Exception as e:
        print(f"❌ 目標期間アクセステストエラー: {e}")
        return False

def main():
    """メインテストプロセス"""
    print("🔧 yosocal.com JavaScript月移動機能テスト")
    print("=" * 60)
    
    driver = None
    try:
        driver = setup_driver()
        
        # 基本的な月移動テスト
        basic_success = test_javascript_month_navigation(driver)
        
        if basic_success:
            print(f"\n✅ 基本月移動テスト成功 - 詳細テストに進みます")
            
            # 特定日付移動テスト
            date_success = test_specific_date_navigation(driver)
            
            if date_success:
                print(f"\n✅ 特定日付移動テスト成功 - 全期間テストに進みます")
                
                # 目標期間全月アクセステスト
                period_success = test_target_period_access(driver)
                
                if period_success:
                    print(f"\n✅ 長期間データ取得の準備が整いました！")
                else:
                    print(f"\n❌ 目標期間の一部にアクセスできません")
            else:
                print(f"\n❌ 特定日付移動テストが失敗しました")
        else:
            print(f"\n❌ 基本月移動テストが失敗しました")
        
        print("\n📋 JavaScript月移動テスト完了")
        
    except Exception as e:
        print(f"❌ テストプロセスでエラー: {e}")
    
    finally:
        if driver:
            driver.quit()
            print("🔧 WebDriver終了")

if __name__ == "__main__":
    main() 