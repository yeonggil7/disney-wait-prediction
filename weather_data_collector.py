#!/usr/bin/env python3
"""
天気データ収集システム
気象庁API・Open-Meteo APIから天気データを取得
東京ディズニーシー（千葉県浦安市）周辺の天気情報
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# 東京ディズニーシーの位置情報
TDS_LOCATION = {
    'name': '東京ディズニーシー',
    'latitude': 35.6267,
    'longitude': 139.8851,
    'jma_area_code': '120000',  # 千葉県
    'jma_station_code': '45106'  # 船橋（最寄りのアメダス）
}


class JMAWeatherCollector:
    """気象庁APIから天気データを取得"""
    
    def __init__(self):
        self.base_url = "https://www.jma.go.jp/bosai"
        self.forecast_url = f"{self.base_url}/forecast/data/forecast/{TDS_LOCATION['jma_area_code']}.json"
        
    def get_weather_forecast(self):
        """天気予報を取得（今日〜1週間）"""
        try:
            response = requests.get(self.forecast_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            
            for area_data in data:
                time_series = area_data.get('timeSeries', [])
                
                for ts in time_series:
                    time_defines = ts.get('timeDefines', [])
                    areas = ts.get('areas', [])
                    
                    for area in areas:
                        area_name = area.get('area', {}).get('name', '')
                        
                        # 千葉県北西部を探す
                        if '北西部' in area_name or '千葉' in area_name:
                            weathers = area.get('weathers', [])
                            temps = area.get('temps', [])
                            pops = area.get('pops', [])  # 降水確率
                            
                            for i, time_str in enumerate(time_defines):
                                forecast = {
                                    'datetime': time_str,
                                    'date': time_str[:10] if len(time_str) >= 10 else time_str,
                                    'area': area_name
                                }
                                
                                if weathers and i < len(weathers):
                                    forecast['weather'] = weathers[i]
                                    forecast['is_rainy'] = 1 if '雨' in weathers[i] else 0
                                    forecast['is_cloudy'] = 1 if '曇' in weathers[i] else 0
                                    forecast['is_sunny'] = 1 if '晴' in weathers[i] else 0
                                
                                if temps and i < len(temps):
                                    try:
                                        forecast['temperature'] = float(temps[i])
                                    except:
                                        pass
                                
                                if pops and i < len(pops):
                                    try:
                                        forecast['precipitation_probability'] = int(pops[i])
                                    except:
                                        pass
                                
                                forecasts.append(forecast)
            
            df = pd.DataFrame(forecasts)
            if len(df) > 0:
                df = df.drop_duplicates(subset=['date'], keep='first')
            
            print(f"✅ 気象庁天気予報取得: {len(df)}日分")
            return df
            
        except Exception as e:
            print(f"❌ 気象庁API取得エラー: {e}")
            return pd.DataFrame()
    
    def get_weather_description(self, weather_text):
        """天気テキストから詳細情報を抽出"""
        info = {
            'is_rainy': 0,
            'is_cloudy': 0,
            'is_sunny': 0,
            'is_snow': 0,
            'weather_impact': 1.0
        }
        
        if not weather_text:
            return info
        
        if '雨' in weather_text:
            info['is_rainy'] = 1
            info['weather_impact'] = 0.75
        if '曇' in weather_text:
            info['is_cloudy'] = 1
            if info['weather_impact'] == 1.0:
                info['weather_impact'] = 0.9
        if '晴' in weather_text:
            info['is_sunny'] = 1
        if '雪' in weather_text:
            info['is_snow'] = 1
            info['weather_impact'] = 0.6
        if '暴風' in weather_text or '台風' in weather_text:
            info['weather_impact'] = 0.5
        
        return info


class OpenMeteoCollector:
    """Open-Meteo APIから天気データを取得（過去データ対応）"""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1"
        self.archive_url = f"{self.base_url}/archive"
        self.forecast_url = f"{self.base_url}/forecast"
        self.lat = TDS_LOCATION['latitude']
        self.lon = TDS_LOCATION['longitude']
    
    def get_historical_weather(self, start_date, end_date):
        """過去の天気データを取得（過去92日間まで対応）"""
        # 過去データ取得用のエンドポイント
        # Open-Meteoのforecast APIでpast_daysを使用
        
        today = datetime.now().date()
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 過去何日分か計算
        past_days = (today - start).days
        if past_days < 0:
            past_days = 0
        if past_days > 92:
            past_days = 92  # 最大92日
        
        # 未来何日分か
        forecast_days = (end - today).days + 1
        if forecast_days < 1:
            forecast_days = 1
        if forecast_days > 16:
            forecast_days = 16
        
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'past_days': past_days,
            'forecast_days': forecast_days,
            'hourly': ','.join([
                'temperature_2m',
                'relative_humidity_2m',
                'precipitation',
                'weather_code',
                'cloud_cover',
                'wind_speed_10m',
                'apparent_temperature'
            ]),
            'daily': ','.join([
                'temperature_2m_max',
                'temperature_2m_min',
                'precipitation_sum',
                'weather_code',
                'sunrise',
                'sunset'
            ]),
            'timezone': 'Asia/Tokyo'
        }
        
        try:
            response = requests.get(self.forecast_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 時間別データ
            hourly = data.get('hourly', {})
            hourly_df = pd.DataFrame(hourly)
            
            if 'time' in hourly_df.columns:
                hourly_df['datetime'] = pd.to_datetime(hourly_df['time'])
                hourly_df['date'] = hourly_df['datetime'].dt.date.astype(str)
                hourly_df['hour'] = hourly_df['datetime'].dt.hour
            
            # 日別データ
            daily = data.get('daily', {})
            daily_df = pd.DataFrame(daily)
            
            if 'time' in daily_df.columns:
                daily_df['date'] = daily_df['time']
            
            print(f"✅ Open-Meteo過去データ取得: {start_date} ~ {end_date}")
            print(f"   時間別: {len(hourly_df)}レコード, 日別: {len(daily_df)}レコード")
            
            return hourly_df, daily_df
            
        except Exception as e:
            print(f"❌ Open-Meteo過去データ取得エラー: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def get_forecast(self, days=7):
        """天気予報を取得"""
        params = {
            'latitude': self.lat,
            'longitude': self.lon,
            'hourly': ','.join([
                'temperature_2m',
                'relative_humidity_2m',
                'precipitation_probability',
                'precipitation',
                'weather_code',
                'cloud_cover',
                'wind_speed_10m',
                'apparent_temperature'
            ]),
            'daily': ','.join([
                'temperature_2m_max',
                'temperature_2m_min',
                'precipitation_sum',
                'precipitation_probability_max',
                'weather_code',
                'sunrise',
                'sunset'
            ]),
            'timezone': 'Asia/Tokyo',
            'forecast_days': days
        }
        
        try:
            response = requests.get(self.forecast_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get('hourly', {})
            hourly_df = pd.DataFrame(hourly)
            
            if 'time' in hourly_df.columns:
                hourly_df['datetime'] = pd.to_datetime(hourly_df['time'])
                hourly_df['date'] = hourly_df['datetime'].dt.date.astype(str)
                hourly_df['hour'] = hourly_df['datetime'].dt.hour
            
            daily = data.get('daily', {})
            daily_df = pd.DataFrame(daily)
            
            if 'time' in daily_df.columns:
                daily_df['date'] = daily_df['time']
            
            print(f"✅ Open-Meteo予報データ取得: {days}日分")
            
            return hourly_df, daily_df
            
        except Exception as e:
            print(f"❌ Open-Meteo予報取得エラー: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def decode_weather_code(self, code):
        """WMO天気コードを解釈"""
        # WMO Weather interpretation codes
        weather_codes = {
            0: {'description': '快晴', 'is_sunny': 1, 'is_cloudy': 0, 'is_rainy': 0, 'impact': 1.0},
            1: {'description': '晴れ', 'is_sunny': 1, 'is_cloudy': 0, 'is_rainy': 0, 'impact': 1.0},
            2: {'description': '一部曇り', 'is_sunny': 1, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.95},
            3: {'description': '曇り', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.9},
            45: {'description': '霧', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.85},
            48: {'description': '着氷性の霧', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.8},
            51: {'description': '弱い霧雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.8},
            53: {'description': '霧雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.75},
            55: {'description': '強い霧雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.7},
            61: {'description': '弱い雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.75},
            63: {'description': '雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.7},
            65: {'description': '強い雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.6},
            71: {'description': '弱い雪', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.65},
            73: {'description': '雪', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.55},
            75: {'description': '強い雪', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 0, 'impact': 0.45},
            80: {'description': 'にわか雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.75},
            81: {'description': '強いにわか雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.65},
            82: {'description': '激しいにわか雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.5},
            95: {'description': '雷雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.5},
            96: {'description': '雹を伴う雷雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.4},
            99: {'description': '激しい雹を伴う雷雨', 'is_sunny': 0, 'is_cloudy': 1, 'is_rainy': 1, 'impact': 0.3},
        }
        
        return weather_codes.get(code, {
            'description': '不明',
            'is_sunny': 0,
            'is_cloudy': 0,
            'is_rainy': 0,
            'impact': 1.0
        })


class WeatherDataManager:
    """天気データの統合管理"""
    
    def __init__(self, data_dir="weather_data"):
        self.data_dir = data_dir
        self.jma = JMAWeatherCollector()
        self.open_meteo = OpenMeteoCollector()
        
        os.makedirs(data_dir, exist_ok=True)
    
    def collect_historical_weather(self, start_date, end_date):
        """過去の天気データを収集して保存"""
        print(f"🌤️ 過去の天気データ収集: {start_date} ~ {end_date}")
        
        hourly_df, daily_df = self.open_meteo.get_historical_weather(start_date, end_date)
        
        if len(hourly_df) > 0:
            # 天気コードをデコード
            if 'weather_code' in hourly_df.columns:
                decoded = hourly_df['weather_code'].apply(
                    lambda x: self.open_meteo.decode_weather_code(x) if pd.notna(x) else {}
                )
                hourly_df['weather_description'] = decoded.apply(lambda x: x.get('description', ''))
                hourly_df['is_sunny'] = decoded.apply(lambda x: x.get('is_sunny', 0))
                hourly_df['is_cloudy'] = decoded.apply(lambda x: x.get('is_cloudy', 0))
                hourly_df['is_rainy'] = decoded.apply(lambda x: x.get('is_rainy', 0))
                hourly_df['weather_impact'] = decoded.apply(lambda x: x.get('impact', 1.0))
            
            # 保存
            hourly_file = os.path.join(self.data_dir, f"weather_hourly_{start_date}_{end_date}.csv")
            hourly_df.to_csv(hourly_file, index=False)
            print(f"💾 時間別データ保存: {hourly_file}")
        
        if len(daily_df) > 0:
            if 'weather_code' in daily_df.columns:
                decoded = daily_df['weather_code'].apply(
                    lambda x: self.open_meteo.decode_weather_code(x) if pd.notna(x) else {}
                )
                daily_df['weather_description'] = decoded.apply(lambda x: x.get('description', ''))
                daily_df['is_sunny'] = decoded.apply(lambda x: x.get('is_sunny', 0))
                daily_df['is_cloudy'] = decoded.apply(lambda x: x.get('is_cloudy', 0))
                daily_df['is_rainy'] = decoded.apply(lambda x: x.get('is_rainy', 0))
                daily_df['weather_impact'] = decoded.apply(lambda x: x.get('impact', 1.0))
            
            daily_file = os.path.join(self.data_dir, f"weather_daily_{start_date}_{end_date}.csv")
            daily_df.to_csv(daily_file, index=False)
            print(f"💾 日別データ保存: {daily_file}")
        
        return hourly_df, daily_df
    
    def get_weather_for_date(self, date_str):
        """特定の日付の天気データを取得"""
        # まずキャッシュを確認
        cache_file = os.path.join(self.data_dir, "weather_cache.csv")
        
        if os.path.exists(cache_file):
            cache_df = pd.read_csv(cache_file)
            if date_str in cache_df['date'].values:
                return cache_df[cache_df['date'] == date_str].iloc[0].to_dict()
        
        # キャッシュにない場合はAPIから取得
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now()
        
        if date <= today:
            # 過去のデータ
            hourly_df, daily_df = self.open_meteo.get_historical_weather(date_str, date_str)
            if len(daily_df) > 0:
                return daily_df.iloc[0].to_dict()
        else:
            # 予報データ
            days_ahead = (date - today).days + 1
            if days_ahead <= 16:  # Open-Meteoは16日先まで
                hourly_df, daily_df = self.open_meteo.get_forecast(days=days_ahead)
                if len(daily_df) > 0:
                    matching = daily_df[daily_df['date'] == date_str]
                    if len(matching) > 0:
                        return matching.iloc[0].to_dict()
        
        return None
    
    def merge_weather_with_waittime(self, waittime_df):
        """待ち時間データに天気データをマージ"""
        print("🔄 天気データをマージ中...")
        
        # 日付のリストを取得
        dates = waittime_df['date'].unique()
        start_date = min(dates)
        end_date = max(dates)
        
        print(f"   対象期間: {start_date} ~ {end_date}")
        
        # 過去の天気データを取得
        hourly_df, daily_df = self.collect_historical_weather(start_date, end_date)
        
        if len(hourly_df) == 0:
            print("⚠️ 天気データが取得できませんでした")
            return waittime_df
        
        # 時刻からhourを抽出
        if 'time' in waittime_df.columns:
            waittime_df['hour'] = waittime_df['time'].apply(lambda x: int(str(x).split(':')[0]))
        
        # マージキーを作成
        waittime_df['merge_key'] = waittime_df['date'] + '_' + waittime_df['hour'].astype(str)
        hourly_df['merge_key'] = hourly_df['date'] + '_' + hourly_df['hour'].astype(str)
        
        # 天気関連カラムを選択
        weather_cols = ['merge_key', 'temperature_2m', 'relative_humidity_2m', 
                       'precipitation', 'cloud_cover', 'wind_speed_10m',
                       'apparent_temperature', 'is_sunny', 'is_cloudy', 
                       'is_rainy', 'weather_impact', 'weather_description']
        
        available_cols = [c for c in weather_cols if c in hourly_df.columns]
        weather_subset = hourly_df[available_cols].drop_duplicates(subset=['merge_key'])
        
        # マージ
        merged_df = waittime_df.merge(weather_subset, on='merge_key', how='left')
        
        # カラム名を整理
        rename_map = {
            'temperature_2m': 'temperature',
            'relative_humidity_2m': 'humidity',
            'apparent_temperature': 'feels_like_temperature',
            'wind_speed_10m': 'wind_speed'
        }
        
        merged_df = merged_df.rename(columns=rename_map)
        
        # 欠損値を埋める
        if 'temperature' in merged_df.columns:
            merged_df['temperature'] = merged_df['temperature'].fillna(20.0)
        if 'is_rainy' in merged_df.columns:
            merged_df['is_rainy'] = merged_df['is_rainy'].fillna(0)
        if 'weather_impact' in merged_df.columns:
            merged_df['weather_impact'] = merged_df['weather_impact'].fillna(1.0)
        
        # 一時カラムを削除
        merged_df = merged_df.drop(columns=['merge_key'], errors='ignore')
        
        print(f"✅ マージ完了: {len(merged_df)}レコード")
        print(f"   天気カラム追加: {[c for c in available_cols if c != 'merge_key']}")
        
        return merged_df
    
    def collect_all_historical_data(self):
        """ディズニーシーデータの全期間の天気データを収集"""
        print("📊 ディズニーシーデータの天気情報を収集")
        
        # ディズニーシーデータの日付範囲を確認
        import glob
        csv_files = glob.glob("Disneysea/disneysea_daily_*.csv")
        
        if not csv_files:
            print("❌ ディズニーシーのCSVファイルが見つかりません")
            return
        
        all_dates = []
        for file in csv_files:
            # ファイル名から日付を抽出
            filename = os.path.basename(file)
            date_part = filename.replace('disneysea_daily_', '').replace('.csv', '')
            all_dates.append(date_part)
        
        all_dates.sort()
        start_date = all_dates[0]
        end_date = all_dates[-1]
        
        print(f"📅 データ期間: {start_date} ~ {end_date}")
        
        # 期間を分割して取得（APIの制限を考慮）
        current_start = datetime.strptime(start_date, "%Y-%m-%d")
        final_end = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_hourly = []
        all_daily = []
        
        while current_start <= final_end:
            current_end = min(current_start + timedelta(days=90), final_end)
            
            start_str = current_start.strftime("%Y-%m-%d")
            end_str = current_end.strftime("%Y-%m-%d")
            
            print(f"\n📥 取得中: {start_str} ~ {end_str}")
            
            hourly_df, daily_df = self.open_meteo.get_historical_weather(start_str, end_str)
            
            if len(hourly_df) > 0:
                all_hourly.append(hourly_df)
            if len(daily_df) > 0:
                all_daily.append(daily_df)
            
            current_start = current_end + timedelta(days=1)
            time.sleep(1)  # API負荷軽減
        
        # 結合して保存
        if all_hourly:
            combined_hourly = pd.concat(all_hourly, ignore_index=True)
            
            # 天気コードをデコード
            if 'weather_code' in combined_hourly.columns:
                decoded = combined_hourly['weather_code'].apply(
                    lambda x: self.open_meteo.decode_weather_code(x) if pd.notna(x) else {}
                )
                combined_hourly['weather_description'] = decoded.apply(lambda x: x.get('description', ''))
                combined_hourly['is_sunny'] = decoded.apply(lambda x: x.get('is_sunny', 0))
                combined_hourly['is_cloudy'] = decoded.apply(lambda x: x.get('is_cloudy', 0))
                combined_hourly['is_rainy'] = decoded.apply(lambda x: x.get('is_rainy', 0))
                combined_hourly['weather_impact'] = decoded.apply(lambda x: x.get('impact', 1.0))
            
            hourly_file = os.path.join(self.data_dir, "weather_hourly_all.csv")
            combined_hourly.to_csv(hourly_file, index=False)
            print(f"\n💾 全期間時間別データ保存: {hourly_file} ({len(combined_hourly)}レコード)")
        
        if all_daily:
            combined_daily = pd.concat(all_daily, ignore_index=True)
            
            if 'weather_code' in combined_daily.columns:
                decoded = combined_daily['weather_code'].apply(
                    lambda x: self.open_meteo.decode_weather_code(x) if pd.notna(x) else {}
                )
                combined_daily['weather_description'] = decoded.apply(lambda x: x.get('description', ''))
                combined_daily['is_sunny'] = decoded.apply(lambda x: x.get('is_sunny', 0))
                combined_daily['is_cloudy'] = decoded.apply(lambda x: x.get('is_cloudy', 0))
                combined_daily['is_rainy'] = decoded.apply(lambda x: x.get('is_rainy', 0))
                combined_daily['weather_impact'] = decoded.apply(lambda x: x.get('impact', 1.0))
            
            daily_file = os.path.join(self.data_dir, "weather_daily_all.csv")
            combined_daily.to_csv(daily_file, index=False)
            print(f"💾 全期間日別データ保存: {daily_file} ({len(combined_daily)}レコード)")
        
        return combined_hourly if all_hourly else None, combined_daily if all_daily else None


def main():
    """メイン処理"""
    print("🌤️ ディズニーシー天気データ収集システム")
    print("=" * 60)
    
    manager = WeatherDataManager()
    
    # 全期間の天気データを収集
    manager.collect_all_historical_data()
    
    print("\n✅ 天気データ収集完了")


if __name__ == "__main__":
    main()

