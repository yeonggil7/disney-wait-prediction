#!/usr/bin/env python3
"""
6月15日のデータを取得するテスト
"""

from yosocal_calendar_navigation_scraper import YosocalNavigationScraper

def main():
    print("🏰 6月15日データ取得テスト")
    print("=" * 50)
    
    scraper = YosocalNavigationScraper()
    
    # 6月15日のデータを取得
    target_year = 2025
    target_month = 6
    target_day = 15
    
    success = scraper.scrape_previous_month_date(target_year, target_month, target_day)
    
    if success:
        filename = f"yosocal_june15_data_{target_year}{target_month:02d}{target_day:02d}.csv"
        scraper.save_data(filename)
        print(f"✅ 6月15日データ取得完了！({filename})")
    else:
        print("❌ 6月15日データ取得に失敗しました")

if __name__ == "__main__":
    main() 