#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import os
import json

def yosocal_practical_solution():
    """yosocal.com 実用的データ収集・分析システム"""
    
    print("🚀 yosocal.com 実用的データ収集・分析システム")
    print("="*60)
    print("📋 現実的アプローチ: 16時間帯リアルタイムデータ活用")
    print("="*60)
    
    # WebDriverセットアップ
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    options.add_argument("--headless")  # バックグラウンド実行
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        
        # === データ収集 ===
        print("📡 リアルタイムデータ収集中...")
        current_data = collect_current_data(driver)
        
        if current_data:
            # === CSV保存 ===
            df = save_practical_csv(current_data)
            
            # === データ分析 ===
            analyze_practical_data(df)
            
            # === 統計レポート ===
            generate_statistics_report(df)
            
            # === 実用的提案 ===
            provide_practical_recommendations(df)
        
        driver.quit()
        print(f"\n🎉 実用的データ収集・分析完了！")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        if 'driver' in locals():
            driver.quit()

def collect_current_data(driver):
    """現在のリアルタイムデータ収集"""
    try:
        driver.get("https://yosocal.com/realtime.htm")
        time.sleep(8)
        
        # ディズニーランド選択
        try:
            land_radio = driver.find_element(By.ID, "park1")
            if not land_radio.is_selected():
                land_radio.click()
                time.sleep(3)
        except:
            pass
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # jamat div確認
        jamat_div = soup.find('div', id='jamat')
        if not jamat_div:
            return None
        
        table = jamat_div.find('table')
        if not table:
            return None
        
        rows = table.find_all('tr')
        
        # アトラクション名取得
        attractions = []
        for row in rows:
            fph2_cells = row.find_all('td', class_='FPh2')
            if fph2_cells:
                for cell in fph2_cells:
                    attraction_name = cell.get_text(strip=True).replace('｜', '').replace('<br>', '')
                    if attraction_name and attraction_name not in attractions:
                        attractions.append(attraction_name)
                break
        
        # 時間データ抽出（重複除去）
        time_data_rows = []
        seen_times = set()
        
        for row in rows:
            fpm_cell = row.find('td', class_='FPM')
            fpt_cell = row.find('td', class_='FPT')
            
            if fpm_cell:
                time_text = fpm_cell.get_text(strip=True)
                if re.match(r'^\d{2}:\d{2}$', time_text) and time_text not in seen_times:
                    time_data_rows.append((time_text, row))
                    seen_times.add(time_text)
            elif fpt_cell:
                time_text = fpt_cell.get_text(strip=True)
                if time_text == '平均' and time_text not in seen_times:
                    time_data_rows.append((time_text, row))
                    seen_times.add(time_text)
        
        print(f"✅ 時間帯数: {len(time_data_rows)}")
        print(f"🎯 アトラクション数: {len(attractions)}")
        
        # データ抽出
        all_data = []
        for time_slot, row in time_data_rows:
            data_cells = row.find_all('td', class_=re.compile(r'^B[0-8]$'))
            
            for i, cell in enumerate(data_cells):
                if i < len(attractions):
                    attraction = attractions[i]
                    cell_text = cell.get_text(strip=True)
                    css_classes = ' '.join(cell.get('class', []))
                    
                    wait_time = None
                    status = "unknown"
                    
                    if cell_text == "-" or cell_text == "" or cell_text == "　":
                        status = "no_data"
                    elif re.match(r'^\d+$', cell_text):
                        wait_time = float(cell_text)
                        status = "normal"
                    else:
                        status = "other"
                    
                    record = {
                        'collection_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'date': datetime.now().strftime("%Y%m%d"),
                        'formatted_date': datetime.now().strftime("%m月%d日"),
                        'time': time_slot,
                        'attraction': attraction,
                        'wait_time': wait_time,
                        'status': status,
                        'css_classes': css_classes,
                        'raw_value': cell_text,
                        'data_source': 'yosocal_practical_realtime'
                    }
                    all_data.append(record)
        
        return all_data
        
    except Exception as e:
        print(f"❌ データ収集失敗: {e}")
        return None

def save_practical_csv(data):
    """実用的CSV保存"""
    try:
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        os.makedirs('data', exist_ok=True)
        csv_filename = f"data/yosocal_practical_realtime_{timestamp}.csv"
        
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"💾 CSV保存: {csv_filename}")
        print(f"📊 総レコード数: {len(df)}")
        print(f"⏰ 時間帯数: {df['time'].nunique()}")
        print(f"🎯 アトラクション数: {df['attraction'].nunique()}")
        print(f"✅ 有効待ち時間: {df['wait_time'].notna().sum()}")
        
        return df
        
    except Exception as e:
        print(f"❌ CSV保存失敗: {e}")
        return None

def analyze_practical_data(df):
    """実用的データ分析"""
    try:
        print(f"\n📊 データ分析結果:")
        print("="*40)
        
        # 現在の最新待ち時間（最新時刻）
        if not df.empty:
            latest_time = df['time'].max()
            if latest_time != '平均':
                latest_data = df[df['time'] == latest_time]
                
                print(f"🕐 最新時刻: {latest_time}")
                print(f"📈 人気アトラクション（最新待ち時間）:")
                
                popular_latest = latest_data[latest_data['wait_time'].notna()].sort_values('wait_time', ascending=False).head(5)
                for _, row in popular_latest.iterrows():
                    print(f"  {row['attraction']}: {row['wait_time']:.0f}分")
        
        # 時間帯別平均待ち時間
        time_avg = df[df['wait_time'].notna()].groupby('time')['wait_time'].mean().round(1)
        print(f"\n⏰ 時間帯別平均待ち時間:")
        for time_slot, avg_wait in time_avg.items():
            if time_slot != '平均':
                print(f"  {time_slot}: {avg_wait}分")
        
        # アトラクション別統計
        attraction_stats = df[df['wait_time'].notna()].groupby('attraction')['wait_time'].agg(['mean', 'min', 'max', 'count']).round(1)
        attraction_stats = attraction_stats.sort_values('mean', ascending=False).head(10)
        
        print(f"\n🎯 人気アトラクション統計（上位10位）:")
        print(f"{'アトラクション':<12} {'平均':<6} {'最短':<6} {'最長':<6} {'データ数':<6}")
        print("-" * 50)
        for attraction, stats in attraction_stats.iterrows():
            print(f"{attraction:<12} {stats['mean']:>5.1f}分 {stats['min']:>5.0f}分 {stats['max']:>5.0f}分 {stats['count']:>6.0f}件")
        
    except Exception as e:
        print(f"❌ データ分析失敗: {e}")

def generate_statistics_report(df):
    """統計レポート生成"""
    try:
        print(f"\n📈 統計レポート:")
        print("="*40)
        
        valid_data = df[df['wait_time'].notna()]
        
        if not valid_data.empty:
            # 全体統計
            print(f"📊 全体統計:")
            print(f"  総データ数: {len(df):,}件")
            print(f"  有効データ数: {len(valid_data):,}件")
            print(f"  有効率: {len(valid_data)/len(df)*100:.1f}%")
            print(f"  平均待ち時間: {valid_data['wait_time'].mean():.1f}分")
            print(f"  中央値: {valid_data['wait_time'].median():.1f}分")
            print(f"  最短待ち時間: {valid_data['wait_time'].min():.0f}分")
            print(f"  最長待ち時間: {valid_data['wait_time'].max():.0f}分")
            
            # 待ち時間分布
            print(f"\n📊 待ち時間分布:")
            bins = [0, 5, 15, 30, 60, 999]
            labels = ['5分以内', '6-15分', '16-30分', '31-60分', '60分超']
            
            wait_distribution = pd.cut(valid_data['wait_time'], bins=bins, labels=labels, right=False)
            distribution_counts = wait_distribution.value_counts()
            
            for category, count in distribution_counts.items():
                percentage = count / len(valid_data) * 100
                print(f"  {category}: {count:3d}件 ({percentage:4.1f}%)")
        
    except Exception as e:
        print(f"❌ 統計レポート生成失敗: {e}")

def provide_practical_recommendations(df):
    """実用的提案"""
    try:
        print(f"\n💡 実用的活用提案:")
        print("="*40)
        
        valid_data = df[df['wait_time'].notna()]
        
        if not valid_data.empty:
            # 空いているアトラクション
            low_wait = valid_data[valid_data['wait_time'] <= 10].groupby('attraction')['wait_time'].mean().sort_values()
            if not low_wait.empty:
                print(f"🟢 現在空いているアトラクション（10分以下）:")
                for attraction, avg_wait in low_wait.head(5).items():
                    print(f"  {attraction}: {avg_wait:.1f}分")
            
            # 混雑しているアトラクション
            high_wait = valid_data[valid_data['wait_time'] >= 30].groupby('attraction')['wait_time'].mean().sort_values(ascending=False)
            if not high_wait.empty:
                print(f"\n🔴 現在混雑しているアトラクション（30分以上）:")
                for attraction, avg_wait in high_wait.head(5).items():
                    print(f"  {attraction}: {avg_wait:.1f}分")
            
            # 定期収集提案
            print(f"\n🔄 継続的データ収集提案:")
            print(f"  1. このスクリプトを1時間毎に実行")
            print(f"  2. 一日分のデータを蓄積して28時間帯相当の分析")
            print(f"  3. 混雑パターンの把握と予測")
            print(f"  4. 最適な訪問時間の特定")
            
            # データ品質評価
            data_quality = len(valid_data) / len(df) * 100
            if data_quality >= 80:
                quality_status = "優秀"
            elif data_quality >= 60:
                quality_status = "良好"
            else:
                quality_status = "要改善"
            
            print(f"\n📊 データ品質評価: {quality_status} ({data_quality:.1f}%)")
        
    except Exception as e:
        print(f"❌ 実用的提案生成失敗: {e}")

if __name__ == "__main__":
    yosocal_practical_solution() 