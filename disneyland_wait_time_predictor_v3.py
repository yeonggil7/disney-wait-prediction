#!/usr/bin/env python3
"""
ディズニーランド待ち時間予測システム v3
- 前日までのデータで学習（時系列分割）
- 直近データの重み付け（時間減衰）
- 曜日・特別日の強化
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 機械学習ライブラリ
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# 日本の祝日
try:
    import jpholiday
    HAS_JPHOLIDAY = True
except ImportError:
    HAS_JPHOLIDAY = False

# LightGBM
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

# 天気データコレクター
from weather_data_collector import OpenMeteoCollector


class DisneyLandFeatureEngineerV3:
    """特徴量エンジニアリングクラス（時系列対応・曜日強化版）"""
    
    def __init__(self):
        # アトラクションのエリア分類（ディズニーランド）
        self.attraction_areas = {
            'オムニバス': 'ワールドバザール',
            'ウエスタンリバー鉄道': 'ウエスタンランド',
            'カリブの海賊': 'アドベンチャーランド',
            'ジャングルクルーズ': 'アドベンチャーランド',
            'ツリーハウス': 'アドベンチャーランド',
            '魅惑のチキルーム': 'アドベンチャーランド',
            'ビッグサンダーマウンテン': 'ウエスタンランド',
            'シューティングギャラリー': 'ウエスタンランド',
            'カントリーベアシアター': 'ウエスタンランド',
            'トムソーヤ島いかだ': 'ウエスタンランド',
            '蒸気船マークトゥウェイン号': 'ウエスタンランド',
            'スプラッシュマウンテン': 'クリッターカントリー',
            'ビーバーブラザーズのカヌー探検': 'クリッターカントリー',
            'イッツ・ア・スモールワールド': 'ファンタジーランド',
            'プーさんのハニーハント': 'ファンタジーランド',
            'ホーンテッドマンション': 'ファンタジーランド',
            'アリスのティーパーティー': 'ファンタジーランド',
            'キャッスルカルーセル': 'ファンタジーランド',
            'シンデレラのフェアリーテイル・ホール': 'ファンタジーランド',
            'ピノキオの冒険旅行': 'ファンタジーランド',
            'ピーターパン空の旅': 'ファンタジーランド',
            'ミッキーのフィルハーマジック': 'ファンタジーランド',
            '白雪姫と七人のこびと': 'ファンタジーランド',
            '空飛ぶダンボ': 'ファンタジーランド',
            'ガジェットのゴーコースター': 'トゥーンタウン',
            'グーフィーのペイント&プレイハウス': 'トゥーンタウン',
            'チップとデールのツリーハウス': 'トゥーンタウン',
            'ドナルドのボート': 'トゥーンタウン',
            'ミニーの家': 'トゥーンタウン',
            'カートゥーンスピン': 'トゥーンタウン',
            'スター・ツアーズ': 'トゥモローランド',
            'スペースマウンテン': 'トゥモローランド',
            'バズ・ライトイヤーのアストロブラスター': 'トゥモローランド',
            'モンスターズ・インク': 'トゥモローランド',
            '美女と野獣の物語': 'ファンタジーランド',
            'ベイマックスのハッピーライド': 'トゥモローランド',
            'スティッチ・エンカウンター': 'トゥモローランド',
            'ハウス前グリーティング': 'ファンタジーランド',
            'ドナルドグリーティング': 'トゥーンタウン',
            'デイジーグリーティング': 'トゥーンタウン',
            'ミニーグリーティング': 'トゥーンタウン',
            'ミート・ミッキー': 'トゥーンタウン'
        }
        
        # アトラクションのタイプ分類（ディズニーランド）
        self.attraction_types = {
            'オムニバス': '移動・遊覧', 'ウエスタンリバー鉄道': '移動・遊覧',
            'カリブの海賊': 'ボートライド', 'ジャングルクルーズ': 'ボートライド',
            'ツリーハウス': '探索', '魅惑のチキルーム': 'シアター',
            'ビッグサンダーマウンテン': 'スリル', 'シューティングギャラリー': 'シューティング',
            'カントリーベアシアター': 'シアター', 'トムソーヤ島いかだ': '移動・遊覧',
            '蒸気船マークトゥウェイン号': '移動・遊覧', 'スプラッシュマウンテン': 'スリル',
            'ビーバーブラザーズのカヌー探検': '移動・遊覧', 'イッツ・ア・スモールワールド': 'ボートライド',
            'プーさんのハニーハント': 'ダークライド', 'ホーンテッドマンション': 'ダークライド',
            'アリスのティーパーティー': 'スピン系', 'キャッスルカルーセル': 'キッズ',
            'シンデレラのフェアリーテイル・ホール': 'ウォークスルー', 'ピノキオの冒険旅行': 'ダークライド',
            'ピーターパン空の旅': 'ダークライド', 'ミッキーのフィルハーマジック': 'シアター',
            '白雪姫と七人のこびと': 'ダークライド', '空飛ぶダンボ': 'スピン系',
            'ガジェットのゴーコースター': 'キッズ', 'グーフィーのペイント&プレイハウス': 'キッズ',
            'チップとデールのツリーハウス': '探索', 'ドナルドのボート': '探索',
            'ミニーの家': 'ウォークスルー', 'カートゥーンスピン': 'スピン系',
            'スター・ツアーズ': 'シアター・ライド', 'スペースマウンテン': 'スリル',
            'バズ・ライトイヤーのアストロブラスター': 'シューティング',
            'モンスターズ・インク': 'ライド', '美女と野獣の物語': 'ボートライド',
            'ベイマックスのハッピーライド': 'スピン系', 'スティッチ・エンカウンター': 'シアター',
            'ハウス前グリーティング': 'グリーティング', 'ドナルドグリーティング': 'グリーティング',
            'デイジーグリーティング': 'グリーティング', 'ミニーグリーティング': 'グリーティング',
            'ミート・ミッキー': 'グリーティング'
        }
        
        # アトラクションの人気度（ディズニーランド）
        self.attraction_popularity = {
            '美女と野獣の物語': 10, 'ベイマックスのハッピーライド': 9,
            'スプラッシュマウンテン': 9, 'ビッグサンダーマウンテン': 9,
            'プーさんのハニーハント': 9, 'スペースマウンテン': 8,
            'モンスターズ・インク': 8, 'バズ・ライトイヤーのアストロブラスター': 7,
            'ホーンテッドマンション': 7, 'ピーターパン空の旅': 7,
            'カリブの海賊': 6, 'ジャングルクルーズ': 6,
            'イッツ・ア・スモールワールド': 5, 'スター・ツアーズ': 5,
            'ミート・ミッキー': 8, 'ミニーグリーティング': 6,
            'ドナルドグリーティング': 5, 'デイジーグリーティング': 5,
            'ハウス前グリーティング': 5, 'スティッチ・エンカウンター': 5,
            'ミッキーのフィルハーマジック': 5, 'シンデレラのフェアリーテイル・ホール': 4,
            'ピノキオの冒険旅行': 4, '白雪姫と七人のこびと': 4,
            'アリスのティーパーティー': 4, 'カートゥーンスピン': 4,
            '空飛ぶダンボ': 4, 'ガジェットのゴーコースター': 3,
            'キャッスルカルーセル': 3, 'カントリーベアシアター': 3,
            '魅惑のチキルーム': 3, 'グーフィーのペイント&プレイハウス': 3,
            'チップとデールのツリーハウス': 2, 'ドナルドのボート': 2,
            'ミニーの家': 2, 'ツリーハウス': 2,
            'ウエスタンリバー鉄道': 3, '蒸気船マークトゥウェイン号': 3,
            'トムソーヤ島いかだ': 2, 'ビーバーブラザーズのカヌー探検': 2,
            'オムニバス': 2, 'シューティングギャラリー': 2
        }
        
        # 屋外/屋内アトラクション（ディズニーランド）
        self.outdoor_attractions = {
            'オムニバス': True, 'ウエスタンリバー鉄道': True,
            'カリブの海賊': False, 'ジャングルクルーズ': True,
            'ツリーハウス': True, '魅惑のチキルーム': False,
            'ビッグサンダーマウンテン': True, 'シューティングギャラリー': False,
            'カントリーベアシアター': False, 'トムソーヤ島いかだ': True,
            '蒸気船マークトゥウェイン号': True, 'スプラッシュマウンテン': True,
            'ビーバーブラザーズのカヌー探検': True, 'イッツ・ア・スモールワールド': False,
            'プーさんのハニーハント': False, 'ホーンテッドマンション': False,
            'アリスのティーパーティー': True, 'キャッスルカルーセル': True,
            'シンデレラのフェアリーテイル・ホール': False, 'ピノキオの冒険旅行': False,
            'ピーターパン空の旅': False, 'ミッキーのフィルハーマジック': False,
            '白雪姫と七人のこびと': False, '空飛ぶダンボ': True,
            'ガジェットのゴーコースター': True, 'グーフィーのペイント&プレイハウス': False,
            'チップとデールのツリーハウス': True, 'ドナルドのボート': True,
            'ミニーの家': False, 'カートゥーンスピン': False,
            'スター・ツアーズ': False, 'スペースマウンテン': False,
            'バズ・ライトイヤーのアストロブラスター': False, 'モンスターズ・インク': False,
            '美女と野獣の物語': False, 'ベイマックスのハッピーライド': True,
            'スティッチ・エンカウンター': False, 'ハウス前グリーティング': True,
            'ドナルドグリーティング': False, 'デイジーグリーティング': False,
            'ミニーグリーティング': False, 'ミート・ミッキー': False
        }
        
        # 特別日の混雑係数（詳細版）
        self.special_dates_crowding = {
            # クリスマス関連（12月中旬から段階的に混雑増加）
            'christmas_eve': {'dates': [(12, 24)], 'impact': 1.8},
            'christmas': {'dates': [(12, 25)], 'impact': 1.7},
            'christmas_week_peak': {'dates': [(12, 20), (12, 21), (12, 22), (12, 23), (12, 26), (12, 27)], 'impact': 1.5},
            'christmas_week_early': {'dates': [(12, 15), (12, 16), (12, 17), (12, 18), (12, 19)], 'impact': 1.4},
            'christmas_week_late': {'dates': [(12, 28), (12, 29), (12, 30)], 'impact': 1.5},
            # 年末年始
            'new_year_eve': {'dates': [(12, 31)], 'impact': 1.7},
            'new_year': {'dates': [(1, 1), (1, 2), (1, 3)], 'impact': 1.6},
            # バレンタイン・ホワイトデー
            'valentine': {'dates': [(2, 14)], 'impact': 1.4},
            'white_day': {'dates': [(3, 14)], 'impact': 1.3},
            # ハロウィン
            'halloween': {'dates': [(10, 31)], 'impact': 1.5},
            'halloween_week': {'dates': [(10, 25), (10, 26), (10, 27), (10, 28), (10, 29), (10, 30)], 'impact': 1.3},
            # その他
            'tanabata': {'dates': [(7, 7)], 'impact': 1.2},
        }
        
        self.label_encoders = {}
        self.weather_data = None
        
    def load_weather_data(self):
        """天気データを読み込み"""
        weather_file = "weather_data/weather_hourly_all.csv"
        if os.path.exists(weather_file):
            self.weather_data = pd.read_csv(weather_file)
            print(f"✅ 天気データ読み込み: {len(self.weather_data)}レコード")
            return True
        return False
    
    def merge_weather_data(self, df):
        """天気データをマージ"""
        if self.weather_data is None:
            self.load_weather_data()
        
        if self.weather_data is None or len(self.weather_data) == 0:
            return df
        
        if 'time' in df.columns:
            df['hour'] = df['time'].apply(lambda x: int(str(x).split(':')[0]))
        
        df['merge_key'] = df['date'].astype(str) + '_' + df['hour'].astype(str)
        
        weather_cols = ['date', 'hour', 'temperature_2m', 'relative_humidity_2m', 
                       'precipitation', 'cloud_cover', 'wind_speed_10m',
                       'apparent_temperature', 'is_sunny', 'is_cloudy', 
                       'is_rainy', 'weather_impact']
        
        available_cols = [c for c in weather_cols if c in self.weather_data.columns]
        weather_subset = self.weather_data[available_cols].copy()
        weather_subset['merge_key'] = weather_subset['date'].astype(str) + '_' + weather_subset['hour'].astype(str)
        weather_subset = weather_subset.drop_duplicates(subset=['merge_key'])
        
        original_len = len(df)
        df = df.merge(
            weather_subset.drop(columns=['date', 'hour'], errors='ignore'), 
            on='merge_key', how='left'
        )
        
        rename_map = {
            'temperature_2m': 'temperature',
            'relative_humidity_2m': 'humidity',
            'apparent_temperature': 'feels_like_temperature',
            'wind_speed_10m': 'wind_speed'
        }
        df = df.rename(columns=rename_map)
        
        # デフォルト値
        df['temperature'] = df.get('temperature', pd.Series([20.0]*len(df))).fillna(20.0)
        df['humidity'] = df.get('humidity', pd.Series([50.0]*len(df))).fillna(50.0)
        df['precipitation'] = df.get('precipitation', pd.Series([0.0]*len(df))).fillna(0.0)
        df['cloud_cover'] = df.get('cloud_cover', pd.Series([50.0]*len(df))).fillna(50.0)
        df['wind_speed'] = df.get('wind_speed', pd.Series([5.0]*len(df))).fillna(5.0)
        df['is_sunny'] = df.get('is_sunny', pd.Series([1]*len(df))).fillna(1)
        df['is_cloudy'] = df.get('is_cloudy', pd.Series([0]*len(df))).fillna(0)
        df['is_rainy'] = df.get('is_rainy', pd.Series([0]*len(df))).fillna(0)
        df['weather_impact'] = df.get('weather_impact', pd.Series([1.0]*len(df))).fillna(1.0)
        
        df = df.drop(columns=['merge_key'], errors='ignore')
        
        matched = len(df[df['temperature'] != 20.0])
        print(f"  🌤️ 天気データマージ: {matched}/{original_len}レコード ({100*matched/original_len:.1f}%)")
        
        return df
        
    def add_time_features(self, df):
        """時間関連の特徴量"""
        df['hour'] = df['time'].apply(lambda x: int(str(x).split(':')[0]))
        df['minute'] = df['time'].apply(lambda x: int(str(x).split(':')[1]))
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        
        def get_time_period(hour):
            if hour < 10:
                return 'early_morning'
            elif hour < 12:
                return 'morning'
            elif hour < 14:
                return 'lunch'
            elif hour < 17:
                return 'afternoon'
            elif hour < 19:
                return 'evening'
            else:
                return 'night'
        
        df['time_period'] = df['hour'].apply(get_time_period)
        df['hours_since_open'] = (df['time_decimal'] - 8.0).clip(lower=0)
        df['hours_until_close'] = (22.0 - df['time_decimal']).clip(lower=0)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        return df
    
    def add_date_features(self, df):
        """日付関連の特徴量"""
        df['date_parsed'] = pd.to_datetime(df['date'])
        df['year'] = df['date_parsed'].dt.year
        df['month'] = df['date_parsed'].dt.month
        df['day'] = df['date_parsed'].dt.day
        df['day_of_week'] = df['date_parsed'].dt.dayofweek
        df['day_of_year'] = df['date_parsed'].dt.dayofyear
        df['week_of_year'] = df['date_parsed'].dt.isocalendar().week
        df['quarter'] = df['date_parsed'].dt.quarter
        
        day_names = ['月', '火', '水', '木', '金', '土', '日']
        df['day_name'] = df['day_of_week'].apply(lambda x: day_names[x])
        
        # 曜日特徴量（強化版）
        df['is_saturday'] = (df['day_of_week'] == 5).astype(int)
        df['is_sunday'] = (df['day_of_week'] == 6).astype(int)
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)
        df['is_monday'] = (df['day_of_week'] == 0).astype(int)
        
        # 曜日の混雑度係数（経験値ベース）
        weekday_crowding = {
            0: 0.9,   # 月曜
            1: 0.85,  # 火曜（最も空いている）
            2: 0.9,   # 水曜
            3: 0.95,  # 木曜
            4: 1.1,   # 金曜（週末前）
            5: 1.3,   # 土曜（最も混雑）
            6: 1.2    # 日曜
        }
        df['weekday_crowding'] = df['day_of_week'].map(weekday_crowding)
        
        # 周期的特徴量
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        df['is_month_start'] = (df['day'] <= 3).astype(int)
        df['is_month_end'] = (df['day'] >= 28).astype(int)
        
        return df
    
    def add_holiday_features(self, df):
        """祝日・休暇関連の特徴量（強化版）"""
        if HAS_JPHOLIDAY:
            df['is_holiday'] = df['date_parsed'].apply(
                lambda x: 1 if jpholiday.is_holiday(x.date()) else 0
            )
            df['holiday_name'] = df['date_parsed'].apply(
                lambda x: jpholiday.is_holiday_name(x.date()) or ''
            )
        else:
            df['is_holiday'] = 0
            df['holiday_name'] = ''
        
        # 祝日の前日・翌日
        df['date_shifted_prev'] = df['date_parsed'] - timedelta(days=1)
        df['date_shifted_next'] = df['date_parsed'] + timedelta(days=1)
        
        if HAS_JPHOLIDAY:
            df['is_before_holiday'] = df['date_shifted_next'].apply(
                lambda x: 1 if jpholiday.is_holiday(x.date()) else 0
            )
            df['is_after_holiday'] = df['date_shifted_prev'].apply(
                lambda x: 1 if jpholiday.is_holiday(x.date()) else 0
            )
        else:
            df['is_before_holiday'] = 0
            df['is_after_holiday'] = 0
        
        df = df.drop(columns=['date_shifted_prev', 'date_shifted_next'], errors='ignore')
        
        # 連休判定
        df['is_long_weekend'] = ((df['is_holiday'] == 1) | (df['is_weekend'] == 1)).astype(int)
        
        # 3連休以上の判定
        df['is_extended_holiday'] = (
            (df['is_long_weekend'] == 1) & 
            ((df['is_before_holiday'] == 1) | (df['is_after_holiday'] == 1))
        ).astype(int)
        
        # 学校休暇期間
        def get_school_holiday(date):
            month, day = date.month, date.day
            if (month == 3 and day >= 20) or (month == 4 and day <= 7):
                return 'spring_break'
            elif month == 4 and day >= 29 or (month == 5 and day <= 5):
                return 'golden_week'
            elif (month == 7 and day >= 20) or month == 8:
                return 'summer_break'
            elif month == 8 and 11 <= day <= 16:
                return 'obon'
            elif month == 9 and 14 <= day <= 23:
                return 'silver_week'
            elif (month == 12 and day >= 24) or (month == 1 and day <= 7):
                return 'winter_break'
            else:
                return 'none'
        
        df['school_holiday'] = df['date_parsed'].apply(get_school_holiday)
        df['is_school_holiday'] = (df['school_holiday'] != 'none').astype(int)
        
        # 夏休み強度
        def get_summer_intensity(date):
            month, day = date.month, date.day
            if month == 8 and 11 <= day <= 17:
                return 3  # お盆
            elif (month == 7 and day >= 22) or (month == 8 and day <= 10):
                return 2
            elif month == 8 and day >= 18:
                return 1
            else:
                return 0
        
        df['summer_intensity'] = df['date_parsed'].apply(get_summer_intensity)
        
        return df
    
    def add_special_date_features(self, df):
        """特別日の特徴量（詳細版）"""
        
        def get_special_date_crowding(date):
            """特別日の混雑係数を取得"""
            month, day = date.month, date.day
            
            for name, info in self.special_dates_crowding.items():
                for d in info['dates']:
                    if month == d[0] and day == d[1]:
                        return info['impact'], name
            
            return 1.0, 'none'
        
        results = df['date_parsed'].apply(get_special_date_crowding)
        df['special_date_crowding'] = results.apply(lambda x: x[0])
        df['special_date_name'] = results.apply(lambda x: x[1])
        
        # クリスマス関連フラグ
        df['is_christmas'] = df['date_parsed'].apply(
            lambda x: 1 if x.month == 12 and x.day == 25 else 0
        )
        df['is_christmas_eve'] = df['date_parsed'].apply(
            lambda x: 1 if x.month == 12 and x.day == 24 else 0
        )
        df['is_christmas_season'] = df['date_parsed'].apply(
            lambda x: 1 if x.month == 12 and 15 <= x.day <= 30 else 0
        )
        
        # 年末年始フラグ
        df['is_new_year'] = df['date_parsed'].apply(
            lambda x: 1 if (x.month == 1 and x.day <= 3) or (x.month == 12 and x.day == 31) else 0
        )
        
        # ハロウィンフラグ
        df['is_halloween'] = df['date_parsed'].apply(
            lambda x: 1 if x.month == 10 and x.day == 31 else 0
        )
        df['is_halloween_season'] = df['date_parsed'].apply(
            lambda x: 1 if x.month == 10 and x.day >= 20 else 0
        )
        
        return df
    
    def add_event_features(self, df):
        """イベント関連の特徴量"""
        special_events = [
            {'name': 'halloween', 'start': (9, 10), 'end': (10, 31), 'impact': 1.2},
            {'name': 'christmas', 'start': (11, 8), 'end': (12, 25), 'impact': 1.3},
            {'name': 'beauty_and_beast', 'start': (1, 1), 'end': (12, 31), 'impact': 1.1},
            {'name': 'summer_event', 'start': (7, 1), 'end': (9, 15), 'impact': 1.1},
        ]
        
        def get_event_impact(date):
            impact = 1.0
            events = []
            
            for event in special_events:
                start_month, start_day = event['start']
                end_month, end_day = event['end']
                
                try:
                    start_date = datetime(date.year, start_month, start_day)
                    end_date = datetime(date.year, end_month, end_day)
                    
                    if start_date <= date <= end_date:
                        impact *= event['impact']
                        events.append(event['name'])
                except:
                    pass
            
            return impact, ','.join(events) if events else 'none'
        
        results = df['date_parsed'].apply(get_event_impact)
        df['event_impact'] = results.apply(lambda x: x[0])
        df['active_events'] = results.apply(lambda x: x[1])
        
        return df
    
    def add_attraction_features(self, df):
        """アトラクション関連の特徴量"""
        df['area'] = df['attraction_name'].map(self.attraction_areas).fillna('その他')
        df['attraction_type'] = df['attraction_name'].map(self.attraction_types).fillna('その他')
        df['popularity'] = df['attraction_name'].map(self.attraction_popularity).fillna(5)
        df['is_outdoor'] = df['attraction_name'].map(self.outdoor_attractions).fillna(False).astype(int)
        df['is_new_area'] = (df['area'] == 'ファンタジーランド').astype(int)  # 美女と野獣エリア含む
        df['is_thrill'] = (df['attraction_type'] == 'スリル').astype(int)
        df['is_kids'] = (df['attraction_type'] == 'キッズ').astype(int)
        df['is_greeting'] = (df['attraction_type'] == 'グリーティング').astype(int)
        
        return df
    
    def add_weather_features(self, df):
        """天気関連の特徴量"""
        for col, default in [('temperature', 20.0), ('humidity', 50.0), ('precipitation', 0.0),
                            ('wind_speed', 5.0), ('cloud_cover', 50.0), ('is_rainy', 0), 
                            ('weather_impact', 1.0)]:
            if col not in df.columns:
                df[col] = default
        
        def temp_category(temp):
            if temp < 10:
                return 'cold'
            elif temp < 20:
                return 'cool'
            elif temp < 28:
                return 'comfortable'
            else:
                return 'hot'
        
        df['temp_category'] = df['temperature'].apply(temp_category)
        df['discomfort_index'] = abs(df['temperature'] - 22)
        df['is_windy'] = (df['wind_speed'] > 10).astype(int)
        df['is_heavy_rain'] = (df['precipitation'] > 5).astype(int)
        df['outdoor_weather_impact'] = df['is_outdoor'] * (1 - df['weather_impact'])
        df['hot_indoor_boost'] = ((df['temperature'] > 30) & (df['is_outdoor'] == 0)).astype(int)
        df['rainy_indoor_boost'] = ((df['is_rainy'].astype(int) == 1) & (df['is_outdoor'] == 0)).astype(int)
        
        return df
    
    def add_lag_features(self, df):
        """ラグ特徴量"""
        df = df.sort_values(['attraction_name', 'date', 'time'])
        df['prev_wait_time'] = df.groupby(['attraction_name', 'date'])['wait_time'].shift(1)
        df['prev_wait_time'] = df['prev_wait_time'].fillna(0)
        df['prev_2h_wait_time'] = df.groupby(['attraction_name', 'date'])['wait_time'].shift(4)
        df['prev_2h_wait_time'] = df['prev_2h_wait_time'].fillna(0)
        
        return df
    
    def add_interaction_features(self, df):
        """交互作用特徴量（曜日強化）"""
        # 人気度との交互作用
        df['popularity_weekend'] = df['popularity'] * df['is_weekend']
        df['popularity_saturday'] = df['popularity'] * df['is_saturday']
        df['popularity_sunday'] = df['popularity'] * df['is_sunday']
        df['popularity_holiday'] = df['popularity'] * df['is_long_weekend']
        
        # ピーク時間との交互作用
        df['is_peak_hour'] = ((df['hour'] >= 10) & (df['hour'] <= 15)).astype(int)
        df['popularity_peak'] = df['popularity'] * df['is_peak_hour']
        
        # 曜日混雑度との交互作用
        df['popularity_weekday_crowding'] = df['popularity'] * df['weekday_crowding']
        
        # 特別日との交互作用
        df['popularity_special'] = df['popularity'] * df['special_date_crowding']
        df['popularity_christmas'] = df['popularity'] * df['is_christmas']
        df['popularity_christmas_season'] = df['popularity'] * df['is_christmas_season']
        
        # イベントとの交互作用
        df['event_popularity'] = df['event_impact'] * df['popularity']
        
        # 人気エリアとの交互作用
        df['new_area_weekend'] = df['is_new_area'] * df['is_weekend']
        df['new_area_holiday'] = df['is_new_area'] * df['is_long_weekend']
        
        # 天候との交互作用
        df['weather_popularity'] = df['weather_impact'] * df['popularity']
        df['temp_popularity'] = df['temperature'] * df['popularity'] / 100
        
        return df
    
    def encode_categorical(self, df, fit=True):
        """カテゴリ変数のエンコーディング"""
        categorical_cols = ['time_period', 'day_name', 'school_holiday', 
                          'area', 'attraction_type', 'active_events', 
                          'special_date_name', 'temp_category']
        
        for col in categorical_cols:
            if col in df.columns:
                if fit:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(
                        df[col].astype(str)
                    )
                else:
                    if col in self.label_encoders:
                        known_labels = set(self.label_encoders[col].classes_)
                        df[col] = df[col].astype(str).apply(
                            lambda x: x if x in known_labels else 'unknown'
                        )
                        if 'unknown' not in known_labels:
                            self.label_encoders[col].classes_ = np.append(
                                self.label_encoders[col].classes_, 'unknown'
                            )
                        df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col])
        
        return df
    
    def engineer_features(self, df, fit=True, with_weather=True):
        """全特徴量を追加"""
        print("🔧 特徴量エンジニアリング開始...")
        
        if with_weather:
            df = self.merge_weather_data(df)
        
        df = self.add_time_features(df)
        print("  ✅ 時間特徴量追加")
        
        df = self.add_date_features(df)
        print("  ✅ 日付特徴量追加（曜日強化）")
        
        df = self.add_holiday_features(df)
        print("  ✅ 祝日・休暇特徴量追加")
        
        df = self.add_special_date_features(df)
        print("  ✅ 特別日特徴量追加（クリスマス等）")
        
        df = self.add_event_features(df)
        print("  ✅ イベント特徴量追加")
        
        df = self.add_attraction_features(df)
        print("  ✅ アトラクション特徴量追加")
        
        df = self.add_weather_features(df)
        print("  ✅ 天気特徴量追加")
        
        df = self.add_lag_features(df)
        print("  ✅ ラグ特徴量追加")
        
        df = self.add_interaction_features(df)
        print("  ✅ 交互作用特徴量追加（曜日強化）")
        
        df = self.encode_categorical(df, fit=fit)
        print("  ✅ カテゴリエンコーディング完了")
        
        print(f"🎯 特徴量エンジニアリング完了: {len(df.columns)}列")
        
        return df


class DisneyLandWaitTimePredictorV3:
    """ディズニーランド待ち時間予測モデル（時系列対応・曜日強化版）"""
    
    def __init__(self, decay_rate=0.15, seasonal_boost=2.0):
        """
        Args:
            decay_rate: 時間減衰率（大きいほど直近データを重視）
                        0.15 = 約5日で重み半減（直近重視）
            seasonal_boost: 同じ季節のデータへの重みブースト倍率
        """
        self.feature_engineer = DisneyLandFeatureEngineerV3()
        self.models = {}
        self.feature_columns = None
        self.scaler = StandardScaler()
        self.model_dir = "models_land_v3"
        self.weather_collector = OpenMeteoCollector()
        self.decay_rate = decay_rate
        self.seasonal_boost = seasonal_boost
        self.latest_training_date = None
        
        os.makedirs(self.model_dir, exist_ok=True)
    
    def load_data(self, data_dir="Disneyland"):
        """データを読み込み"""
        print("📂 データ読み込み中...")
        
        csv_files = glob.glob(os.path.join(data_dir, "disneyland_daily_*.csv"))
        
        if not csv_files:
            print("❌ CSVファイルが見つかりません")
            return None
        
        dfs = []
        for file in csv_files:
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                print(f"⚠️ {file} 読み込みエラー: {e}")
        
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"✅ {len(csv_files)}ファイル読み込み完了: {len(combined_df)}レコード")
        
        return combined_df
    
    def calculate_sample_weights(self, df, reference_date=None):
        """
        時間減衰重みを計算（同曜日データを最重視 + 去年同週強化）
        
        重み付けの優先順位:
        1. 前週の同曜日（祝日の場合は前週土曜日）: 最大ブースト（100倍）
        2. 前前週の同曜日: 超高ブースト（80倍）
        3. 3週前の同曜日: 高ブースト（50倍）
        4. 4週前の同曜日: 中ブースト（30倍）
        5. 去年の同週・同曜日: 高ブースト（40倍）
        6. 去年の同週（週平均参考）: 中ブースト（20倍）
        7. その他の同曜日: ブースト（10倍）
        """
        if reference_date is None:
            reference_date = df['date_parsed'].max()
        
        # 日数の差を計算
        days_diff = (reference_date - df['date_parsed']).dt.days
        
        # 基本重み: 指数関数的減衰（ただし去年のデータも考慮するため減衰を緩める）
        # 1年前のデータも意味のある重みを持つように調整
        weights = np.exp(-self.decay_rate * days_diff.clip(upper=60))  # 60日以上は同じ減衰
        
        # === 曜日マッチング（最重要）===
        ref_weekday = reference_date.weekday()  # 0=月, 6=日
        data_weekdays = df['date_parsed'].dt.weekday
        
        # 祝日判定（クリスマス、年末年始、GW、お盆など）
        ref_month = reference_date.month
        ref_day = reference_date.day
        is_ref_holiday = (
            (ref_month == 12 and ref_day >= 23) or  # クリスマス期間
            (ref_month == 1 and ref_day <= 3) or    # 年始
            (ref_month == 5 and 3 <= ref_day <= 5) or  # GW
            (ref_month == 8 and 10 <= ref_day <= 16) or  # お盆
            (ref_weekday >= 5)                       # 週末
        )
        
        # 祝日の場合は土曜日（weekday=5）を参照曜日とする
        target_weekday = 5 if is_ref_holiday and ref_weekday < 5 else ref_weekday
        
        # 同じ曜日のマスク（厳密に同曜日のみ）
        same_weekday_mask = (data_weekdays == target_weekday)
        
        # 前週の同曜日（厳密に7日前）: 最大ブースト
        prev_week_mask = (days_diff == 7) & same_weekday_mask
        weights = np.where(prev_week_mask, weights * 100.0, weights)
        
        # 前前週の同曜日（厳密に14日前）: 超高ブースト
        two_weeks_mask = (days_diff == 14) & same_weekday_mask
        weights = np.where(two_weeks_mask, weights * 80.0, weights)
        
        # 3週前の同曜日（厳密に21日前）
        three_weeks_mask = (days_diff == 21) & same_weekday_mask
        weights = np.where(three_weeks_mask, weights * 50.0, weights)
        
        # 4週前の同曜日（厳密に28日前）
        four_weeks_mask = (days_diff == 28) & same_weekday_mask
        weights = np.where(four_weeks_mask, weights * 30.0, weights)
        
        # === 去年の同週データを強化 ===
        ref_week = reference_date.isocalendar()[1]  # ISO週番号 (1-53)
        ref_year = reference_date.year
        data_weeks = df['date_parsed'].apply(lambda x: x.isocalendar()[1])
        data_years = df['date_parsed'].dt.year
        
        # 去年の同週・同曜日: 高ブースト（シーズンの傾向を反映）
        last_year_same_week_same_day_mask = (
            (data_years == ref_year - 1) & 
            (data_weeks == ref_week) & 
            same_weekday_mask
        )
        weights = np.where(last_year_same_week_same_day_mask, weights * 40.0, weights)
        
        # 去年の同週（全曜日）: 週平均として参考
        last_year_same_week_mask = (
            (data_years == ref_year - 1) & 
            (data_weeks == ref_week)
        ) & ~last_year_same_week_same_day_mask
        weights = np.where(last_year_same_week_mask, weights * 20.0, weights)
        
        # 去年の前後1週も参考にする
        adjacent_weeks = [(ref_week - 1) if ref_week > 1 else 52,
                         (ref_week + 1) if ref_week < 52 else 1]
        last_year_adjacent_week_mask = (
            (data_years == ref_year - 1) & 
            (data_weeks.isin(adjacent_weeks))
        )
        weights = np.where(last_year_adjacent_week_mask, weights * 10.0, weights)
        
        # その他の同じ曜日（7日刻み）- 去年分も含む
        other_same_weekday = same_weekday_mask & (days_diff % 7 == 0) & \
                            ~prev_week_mask & ~two_weeks_mask & ~three_weeks_mask & ~four_weeks_mask & \
                            ~last_year_same_week_same_day_mask
        weights = np.where(other_same_weekday, weights * 10.0, weights)
        
        # === 季節ブースト ===
        data_months = df['date_parsed'].dt.month
        
        # 同月データにブースト
        same_month_mask = (data_months == ref_month)
        weights = np.where(same_month_mask, weights * self.seasonal_boost, weights)
        
        # 隣接月にも軽くブースト
        adjacent_months = [(ref_month - 1) if ref_month > 1 else 12,
                          (ref_month + 1) if ref_month < 12 else 1]
        adjacent_mask = data_months.isin(adjacent_months)
        weights = np.where(adjacent_mask, weights * (self.seasonal_boost * 0.5), weights)
        
        # === 週末/平日マッチング ===
        ref_is_weekend = reference_date.weekday() >= 5
        data_is_weekend = df['date_parsed'].dt.weekday >= 5
        same_weekday_type = (data_is_weekend == ref_is_weekend)
        weights = np.where(same_weekday_type, weights * 3.0, weights)
        
        # 正規化
        weights = weights / weights.sum() * len(weights)
        
        # 統計表示
        prev_week_weight = weights[prev_week_mask].mean() if prev_week_mask.any() else 0
        two_weeks_weight = weights[two_weeks_mask].mean() if two_weeks_mask.any() else 0
        last_year_same_week_weight = weights[last_year_same_week_same_day_mask].mean() if last_year_same_week_same_day_mask.any() else 0
        last_year_week_avg_weight = weights[last_year_same_week_mask].mean() if last_year_same_week_mask.any() else 0
        same_weekday_weight = weights[same_weekday_mask].mean() if same_weekday_mask.any() else 0
        other_weight = weights[~same_weekday_mask].mean() if (~same_weekday_mask).any() else 0
        
        print(f"📊 サンプル重み（同曜日 + 去年同週強化）:")
        print(f"   🎯 前週同曜日: {prev_week_weight:.1f} ({prev_week_mask.sum()}サンプル)")
        print(f"   🎯 前前週同曜日: {two_weeks_weight:.1f} ({two_weeks_mask.sum()}サンプル)")
        print(f"   📆 去年同週同曜日: {last_year_same_week_weight:.1f} ({last_year_same_week_same_day_mask.sum()}サンプル)")
        print(f"   📆 去年同週(週平均): {last_year_week_avg_weight:.2f} ({last_year_same_week_mask.sum()}サンプル)")
        print(f"   📅 全同曜日平均: {same_weekday_weight:.3f}")
        print(f"   📉 他曜日平均: {other_weight:.5f}")
        print(f"   最大={weights.max():.1f}, 最小={weights.min():.5f}")
        
        return weights
    
    def prepare_features(self, df, fit=True, with_weather=True):
        """特徴量を準備"""
        df = self.feature_engineer.engineer_features(df, fit=fit, with_weather=with_weather)
        
        # 特徴量カラムを選択
        feature_cols = [
            # 時間特徴量
            'hour', 'minute', 'time_decimal', 'hours_since_open', 
            'hours_until_close', 'hour_sin', 'hour_cos',
            # 日付特徴量
            'month', 'day', 'day_of_week', 'day_of_year', 'week_of_year',
            'quarter', 'is_saturday', 'is_sunday', 'is_weekend', 'is_friday', 'is_monday',
            'weekday_crowding',
            'month_sin', 'month_cos', 'dow_sin', 'dow_cos',
            'is_month_start', 'is_month_end',
            # 祝日・休暇
            'is_holiday', 'is_long_weekend', 'is_extended_holiday',
            'is_before_holiday', 'is_after_holiday',
            'is_school_holiday', 'summer_intensity',
            # 特別日
            'special_date_crowding', 'is_christmas', 'is_christmas_eve',
            'is_christmas_season', 'is_new_year', 'is_halloween', 'is_halloween_season',
            # イベント
            'event_impact',
            # アトラクション
            'attraction_index', 'popularity', 'is_new_area',
            'is_thrill', 'is_kids', 'is_greeting', 'is_outdoor',
            # 天候
            'temperature', 'humidity', 'precipitation', 'cloud_cover',
            'wind_speed', 'is_rainy', 'weather_impact', 'discomfort_index',
            'is_windy', 'is_heavy_rain', 'outdoor_weather_impact',
            'hot_indoor_boost', 'rainy_indoor_boost',
            # ラグ
            'prev_wait_time', 'prev_2h_wait_time',
            # 交互作用（曜日強化）
            'popularity_weekend', 'popularity_saturday', 'popularity_sunday',
            'popularity_holiday', 'is_peak_hour', 'popularity_peak',
            'popularity_weekday_crowding', 'popularity_special',
            'popularity_christmas', 'popularity_christmas_season',
            'event_popularity', 'new_area_weekend', 'new_area_holiday',
            'weather_popularity', 'temp_popularity',
            # エンコード済みカテゴリ
            'time_period_encoded', 'day_name_encoded', 'school_holiday_encoded',
            'area_encoded', 'attraction_type_encoded', 'temp_category_encoded',
            'special_date_name_encoded'
        ]
        
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if fit:
            self.feature_columns = available_cols
        
        return df, available_cols
    
    def train(self, df=None, prediction_date=None, test_size=0.15):
        """
        モデルを訓練
        
        Args:
            df: 訓練データ（Noneの場合は自動読み込み）
            prediction_date: 予測対象日（この日より前のデータのみで訓練）
            test_size: テストデータの割合
        """
        if df is None:
            df = self.load_data()
        
        if df is None:
            return False
        
        print("\n🎓 モデル訓練開始（時系列対応・曜日強化版）...")
        print(f"   ⚙️ 時間減衰率: {self.decay_rate} (約{int(0.693/self.decay_rate)}日で半減)")
        print(f"   ⚙️ 季節ブースト: {self.seasonal_boost}x")
        
        # 特徴量準備
        df, feature_cols = self.prepare_features(df, fit=True, with_weather=True)
        
        # 待ち時間0のデータは除外
        df_train = df[df['wait_time'] > 0].copy()
        
        # 時系列でソート
        df_train = df_train.sort_values('date_parsed')
        
        # 予測対象日が指定されている場合、その前日までのデータのみを使用
        if prediction_date is not None:
            pred_date = pd.to_datetime(prediction_date)
            df_train = df_train[df_train['date_parsed'] < pred_date]
            print(f"   📅 訓練データ: {prediction_date} より前のデータ")
        
        if len(df_train) == 0:
            print("❌ 訓練データがありません")
            return False
        
        # 最新の訓練日を記録
        self.latest_training_date = df_train['date_parsed'].max()
        print(f"   📅 訓練データ期間: {df_train['date_parsed'].min().strftime('%Y-%m-%d')} ~ {self.latest_training_date.strftime('%Y-%m-%d')}")
        
        X = df_train[feature_cols]
        y = df_train['wait_time']
        
        # 時間減衰重みを計算
        sample_weights = self.calculate_sample_weights(df_train)
        
        print(f"📊 訓練データ: {len(X)}サンプル, {len(feature_cols)}特徴量")
        
        # 欠損値を埋める
        X = X.fillna(0)
        
        # 時系列分割（最後の15%をテストに使用）
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        weights_train = sample_weights[:split_idx]  # numpy array
        
        print(f"   訓練: {len(X_train)}サンプル, テスト: {len(X_test)}サンプル")
        
        # モデル訓練
        print("\n📈 モデル訓練中...")
        
        # 1. Random Forest（重み付き）
        print("  🌲 Random Forest（時間減衰重み付き）...")
        rf_model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=8,
            min_samples_leaf=4,
            n_jobs=-1,
            random_state=42
        )
        rf_model.fit(X_train, y_train, sample_weight=weights_train)
        self.models['random_forest'] = rf_model
        
        rf_pred = rf_model.predict(X_test)
        rf_mae = mean_absolute_error(y_test, rf_pred)
        rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
        rf_r2 = r2_score(y_test, rf_pred)
        print(f"    MAE: {rf_mae:.2f}分, RMSE: {rf_rmse:.2f}分, R²: {rf_r2:.3f}")
        
        # 2. Gradient Boosting（重み付き）
        print("  🚀 Gradient Boosting（時間減衰重み付き）...")
        gb_model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=12,
            learning_rate=0.08,
            min_samples_split=8,
            min_samples_leaf=4,
            random_state=42
        )
        gb_model.fit(X_train, y_train, sample_weight=weights_train)
        self.models['gradient_boosting'] = gb_model
        
        gb_pred = gb_model.predict(X_test)
        gb_mae = mean_absolute_error(y_test, gb_pred)
        gb_rmse = np.sqrt(mean_squared_error(y_test, gb_pred))
        gb_r2 = r2_score(y_test, gb_pred)
        print(f"    MAE: {gb_mae:.2f}分, RMSE: {gb_rmse:.2f}分, R²: {gb_r2:.3f}")
        
        # 3. LightGBM（重み付き）
        if HAS_LIGHTGBM:
            print("  💡 LightGBM（時間減衰重み付き）...")
            lgb_model = lgb.LGBMRegressor(
                n_estimators=300,
                max_depth=15,
                learning_rate=0.05,
                num_leaves=60,
                min_child_samples=15,
                random_state=42,
                verbose=-1
            )
            lgb_model.fit(X_train, y_train, sample_weight=weights_train)
            self.models['lightgbm'] = lgb_model
            
            lgb_pred = lgb_model.predict(X_test)
            lgb_mae = mean_absolute_error(y_test, lgb_pred)
            lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
            lgb_r2 = r2_score(y_test, lgb_pred)
            print(f"    MAE: {lgb_mae:.2f}分, RMSE: {lgb_rmse:.2f}分, R²: {lgb_r2:.3f}")
        
        # 特徴量重要度
        print("\n📊 特徴量重要度 (Top 25):")
        importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for i, row in importance.head(25).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
        
        # モデル保存
        self.save_models()
        
        print("\n✅ モデル訓練完了（時系列対応・曜日強化版）")
        
        return True
    
    def save_models(self):
        """モデルを保存"""
        joblib.dump(self.models, os.path.join(self.model_dir, 'wait_time_models.joblib'))
        joblib.dump(self.scaler, os.path.join(self.model_dir, 'scaler.joblib'))
        joblib.dump(self.feature_columns, os.path.join(self.model_dir, 'feature_columns.joblib'))
        joblib.dump(self.feature_engineer.label_encoders, 
                   os.path.join(self.model_dir, 'label_encoders.joblib'))
        joblib.dump({
            'decay_rate': self.decay_rate,
            'seasonal_boost': self.seasonal_boost,
            'latest_training_date': self.latest_training_date
        }, os.path.join(self.model_dir, 'model_config.joblib'))
        print(f"💾 モデル保存完了: {self.model_dir}/")
    
    def load_models(self):
        """モデルを読み込み"""
        try:
            self.models = joblib.load(os.path.join(self.model_dir, 'wait_time_models.joblib'))
            self.scaler = joblib.load(os.path.join(self.model_dir, 'scaler.joblib'))
            self.feature_columns = joblib.load(os.path.join(self.model_dir, 'feature_columns.joblib'))
            self.feature_engineer.label_encoders = joblib.load(
                os.path.join(self.model_dir, 'label_encoders.joblib')
            )
            config = joblib.load(os.path.join(self.model_dir, 'model_config.joblib'))
            self.decay_rate = config.get('decay_rate', 0.15)
            self.seasonal_boost = config.get('seasonal_boost', 2.0)
            self.latest_training_date = config.get('latest_training_date')
            print("✅ モデル読み込み完了")
            if self.latest_training_date:
                print(f"   📅 最終訓練日: {self.latest_training_date.strftime('%Y-%m-%d')}")
            return True
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {e}")
            return False
    
    def get_weather_for_prediction(self, date_str):
        """予測用の天気データを取得"""
        print(f"🌤️ {date_str} の天気データを取得中...")
        
        try:
            hourly_df, daily_df = self.weather_collector.get_forecast(days=16)
            
            if len(hourly_df) > 0 and 'date' in hourly_df.columns:
                day_data = hourly_df[hourly_df['date'] == date_str]
                
                if len(day_data) > 0:
                    return day_data
            
            print("⚠️ 天気データが取得できませんでした。デフォルト値を使用します。")
            return None
            
        except Exception as e:
            print(f"⚠️ 天気データ取得エラー: {e}")
            return None
    
    def predict(self, date, time_slots=None, attractions=None, 
                weather_data=None, model_name='gradient_boosting'):
        """待ち時間を予測"""
        
        if not self.models:
            if not self.load_models():
                print("❌ モデルが見つかりません。先に train() を実行してください。")
                return None
        
        if time_slots is None:
            time_slots = [f"{h:02d}:{m:02d}" 
                         for h in range(8, 22) 
                         for m in [15, 45]]
        
        if attractions is None:
            attractions = list(self.feature_engineer.attraction_popularity.keys())
        
        # 天気データを取得
        if weather_data is None:
            weather_data = self.get_weather_for_prediction(date)
        
        # 予測用データフレーム作成
        records = []
        for time in time_slots:
            hour = int(time.split(':')[0])
            
            if weather_data is not None and 'hour' in weather_data.columns:
                hour_weather = weather_data[weather_data['hour'] == hour]
                if len(hour_weather) > 0:
                    hw = hour_weather.iloc[0]
                    temp = hw.get('temperature_2m', 20.0)
                    humidity = hw.get('relative_humidity_2m', 50.0)
                    precip = hw.get('precipitation', 0.0)
                    cloud = hw.get('cloud_cover', 50.0)
                    wind = hw.get('wind_speed_10m', 5.0)
                    weather_code = hw.get('weather_code', 0)
                    
                    weather_info = self.weather_collector.decode_weather_code(
                        weather_code if pd.notna(weather_code) else 0
                    )
                else:
                    temp, humidity, precip, cloud, wind = 20.0, 50.0, 0.0, 50.0, 5.0
                    weather_info = {'is_rainy': 0, 'impact': 1.0}
            else:
                temp, humidity, precip, cloud, wind = 20.0, 50.0, 0.0, 50.0, 5.0
                weather_info = {'is_rainy': 0, 'impact': 1.0}
            
            for i, attraction in enumerate(attractions, 1):
                records.append({
                    'time': time,
                    'attraction_index': i,
                    'attraction_name': attraction,
                    'date': date,
                    'wait_time': 0,
                    'temperature': temp if pd.notna(temp) else 20.0,
                    'humidity': humidity if pd.notna(humidity) else 50.0,
                    'precipitation': precip if pd.notna(precip) else 0.0,
                    'cloud_cover': cloud if pd.notna(cloud) else 50.0,
                    'wind_speed': wind if pd.notna(wind) else 5.0,
                    'is_rainy': weather_info.get('is_rainy', 0),
                    'weather_impact': weather_info.get('impact', 1.0)
                })
        
        df = pd.DataFrame(records)
        
        # 特徴量準備
        df, _ = self.prepare_features(df, fit=False, with_weather=False)
        
        # 予測実行
        X = df[self.feature_columns].fillna(0)
        
        if model_name in self.models:
            predictions = self.models[model_name].predict(X)
        else:
            predictions = self.models['gradient_boosting'].predict(X)
        
        df['predicted_wait_time'] = predictions.clip(min=0)
        
        # ハイブリッド予測: 前週・前前週の実データで補正
        df = self.apply_weekly_adjustment(df, date)
        
        return df[['date', 'time', 'attraction_name', 'predicted_wait_time', 
                  'temperature', 'is_rainy', 'weather_impact', 'is_weekend',
                  'is_holiday', 'weekday_crowding', 'special_date_crowding']]
    
    def apply_weekly_adjustment(self, df, target_date):
        """前週・前前週の実データで予測を補正"""
        import os
        import glob
        
        target = pd.to_datetime(target_date)
        target_weekday = target.weekday()
        
        # 祝日・特別日判定
        is_special = (
            (target.month == 12 and target.day >= 15) or  # クリスマス期間
            (target.month == 1 and target.day <= 3) or    # 年始
            (target.weekday() >= 5)                        # 週末
        )
        
        # 祝日の場合は土曜日を参照
        ref_weekday = 5 if is_special and target_weekday < 5 else target_weekday
        
        # 前週・前前週の同曜日を探す
        prev_week_date = target - pd.Timedelta(days=7)
        prev_prev_week_date = target - pd.Timedelta(days=14)
        
        # 祝日の場合、前週・前前週の土曜日を探す
        if is_special and target_weekday < 5:
            days_to_saturday = (5 - target_weekday) % 7
            if days_to_saturday == 0:
                days_to_saturday = 7
            prev_week_date = target - pd.Timedelta(days=days_to_saturday)
            prev_prev_week_date = target - pd.Timedelta(days=days_to_saturday + 7)
        
        # データファイルを読み込み
        prev_week_data = None
        prev_prev_week_data = None
        
        data_dir = "Disneyland"
        
        prev_week_file = os.path.join(data_dir, f"disneyland_daily_{prev_week_date.strftime('%Y-%m-%d')}.csv")
        prev_prev_week_file = os.path.join(data_dir, f"disneyland_daily_{prev_prev_week_date.strftime('%Y-%m-%d')}.csv")
        
        if os.path.exists(prev_week_file):
            try:
                prev_week_data = pd.read_csv(prev_week_file)
                prev_week_avg = prev_week_data.groupby(['time', 'attraction_name'])['wait_time'].mean().reset_index()
                prev_week_avg.columns = ['time', 'attraction_name', 'prev_week_wait']
            except:
                prev_week_avg = None
        else:
            prev_week_avg = None
        
        if os.path.exists(prev_prev_week_file):
            try:
                prev_prev_week_data = pd.read_csv(prev_prev_week_file)
                prev_prev_week_avg = prev_prev_week_data.groupby(['time', 'attraction_name'])['wait_time'].mean().reset_index()
                prev_prev_week_avg.columns = ['time', 'attraction_name', 'prev_prev_week_wait']
            except:
                prev_prev_week_avg = None
        else:
            prev_prev_week_avg = None
        
        # 補正を適用
        if prev_week_avg is not None or prev_prev_week_avg is not None:
            # マージ
            if prev_week_avg is not None:
                df = df.merge(prev_week_avg, on=['time', 'attraction_name'], how='left')
            else:
                df['prev_week_wait'] = np.nan
            
            if prev_prev_week_avg is not None:
                df = df.merge(prev_prev_week_avg, on=['time', 'attraction_name'], how='left')
            else:
                df['prev_prev_week_wait'] = np.nan
            
            # 加重平均で予測を補正
            # モデル予測 40% + 前週 40% + 前前週 20%
            model_weight = 0.4
            prev_week_weight = 0.4
            prev_prev_week_weight = 0.2
            
            # 特別日（クリスマス期間）は前週データをより重視
            if is_special:
                model_weight = 0.3
                prev_week_weight = 0.5
                prev_prev_week_weight = 0.2
            
            def blend_prediction(row):
                model_pred = row['predicted_wait_time']
                prev_week = row.get('prev_week_wait', np.nan)
                prev_prev_week = row.get('prev_prev_week_wait', np.nan)
                
                total_weight = model_weight
                weighted_sum = model_pred * model_weight
                
                if pd.notna(prev_week) and prev_week > 0:
                    weighted_sum += prev_week * prev_week_weight
                    total_weight += prev_week_weight
                
                if pd.notna(prev_prev_week) and prev_prev_week > 0:
                    weighted_sum += prev_prev_week * prev_prev_week_weight
                    total_weight += prev_prev_week_weight
                
                return weighted_sum / total_weight if total_weight > 0 else model_pred
            
            df['predicted_wait_time'] = df.apply(blend_prediction, axis=1)
            
            # 一時カラムを削除
            df = df.drop(columns=['prev_week_wait', 'prev_prev_week_wait'], errors='ignore')
            
            print(f"📊 ハイブリッド予測: 前週({prev_week_date.strftime('%m/%d')}) + 前前週({prev_prev_week_date.strftime('%m/%d')}) データで補正")
        
        return df
    
    def predict_day(self, date, model_name='gradient_boosting'):
        """1日分の予測を実行"""
        pred_date = pd.to_datetime(date)
        day_names = ['月', '火', '水', '木', '金', '土', '日']
        day_name = day_names[pred_date.weekday()]
        
        print(f"\n🔮 {date} ({day_name}曜日) の待ち時間予測")
        print("=" * 60)
        
        predictions = self.predict(date=date, model_name=model_name)
        
        if predictions is None:
            return None
        
        # 曜日・特別日情報を表示
        is_weekend = predictions['is_weekend'].iloc[0] if 'is_weekend' in predictions.columns else 0
        is_holiday = predictions['is_holiday'].iloc[0] if 'is_holiday' in predictions.columns else 0
        weekday_crowding = predictions['weekday_crowding'].iloc[0] if 'weekday_crowding' in predictions.columns else 1.0
        special_crowding = predictions['special_date_crowding'].iloc[0] if 'special_date_crowding' in predictions.columns else 1.0
        
        day_type = []
        if is_weekend:
            day_type.append("📅 週末")
        if is_holiday:
            day_type.append("🎌 祝日")
        if special_crowding > 1.0:
            day_type.append(f"🎄 特別日 (混雑係数: {special_crowding:.1f})")
        
        if day_type:
            print(" | ".join(day_type))
        print(f"📊 曜日混雑係数: {weekday_crowding:.2f}")
        
        # 天気情報を表示
        if 'temperature' in predictions.columns:
            avg_temp = predictions['temperature'].mean()
            is_rainy = predictions['is_rainy'].max()
            weather_str = "🌧️ 雨" if is_rainy else "☀️ 晴れ"
            print(f"🌡️ 予測気温: {avg_temp:.1f}℃ | 天気: {weather_str}")
        
        # アトラクション別の平均待ち時間
        avg_by_attraction = predictions.groupby('attraction_name')['predicted_wait_time'].mean()
        avg_by_attraction = avg_by_attraction.sort_values(ascending=False)
        
        print("\n📊 アトラクション別 予測平均待ち時間:")
        for name, wait in avg_by_attraction.head(15).items():
            print(f"  {name}: {wait:.1f}分")
        
        # 時間帯別の平均待ち時間
        predictions['hour'] = predictions['time'].apply(lambda x: int(x.split(':')[0]))
        avg_by_hour = predictions.groupby('hour')['predicted_wait_time'].mean()
        
        print("\n⏰ 時間帯別 予測平均待ち時間:")
        for hour, wait in avg_by_hour.items():
            print(f"  {hour:02d}時台: {wait:.1f}分")
        
        # 最適な訪問時間帯
        best_hours = avg_by_hour.nsmallest(3)
        print("\n🎯 おすすめの時間帯（混雑が少ない）:")
        for hour, wait in best_hours.items():
            print(f"  {hour:02d}時台: 平均{wait:.1f}分")
        
        return predictions


def main():
    """メイン処理"""
    print("🏰 ディズニーランド待ち時間予測システム V3")
    print("   （時系列対応・直近重視・曜日強化版）")
    print("=" * 60)
    
    # 時間減衰率を設定（0.15 = 約5日で重みが半減、直近重視）
    # 季節ブースト（同月データに2倍の重み）
    predictor = DisneyLandWaitTimePredictorV3(decay_rate=0.15, seasonal_boost=2.0)
    
    # データ読み込みと訓練
    print("\n📚 モデル訓練...")
    predictor.train()
    
    # 予測テスト
    print("\n" + "=" * 60)
    print("🔮 予測テスト")
    
    # 1. 今週末の予測
    from datetime import datetime, timedelta
    
    # 次の土曜日を取得
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    next_saturday = (today + timedelta(days=days_until_saturday)).strftime("%Y-%m-%d")
    
    predictor.predict_day(date=next_saturday)
    
    # 2. クリスマスの予測
    print("\n" + "=" * 60)
    predictor.predict_day(date="2025-12-25")


if __name__ == "__main__":
    main()

