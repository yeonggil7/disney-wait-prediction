#!/usr/bin/env python3
"""
ディズニーシー待ち時間予測システム
豊富な特徴量を使用した機械学習ベースの予測モデル
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 機械学習ライブラリ
from sklearn.model_selection import train_test_split, cross_val_score
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
    print("⚠️ jpholidayがインストールされていません。pip install jpholiday でインストールしてください。")

# LightGBM（オプション）
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("⚠️ LightGBMがインストールされていません。pip install lightgbm でインストールしてください。")


class DisneySeaFeatureEngineer:
    """特徴量エンジニアリングクラス"""
    
    def __init__(self):
        # アトラクションのエリア分類
        self.attraction_areas = {
            'ソアリン': 'メディテレーニアンハーバー',
            '船メディテレーニアンハーバー発': 'メディテレーニアンハーバー',
            'フォートレスエクスプロレーション': 'メディテレーニアンハーバー',
            'ゴンドラ': 'メディテレーニアンハーバー',
            'タワーオブテラー': 'アメリカンウォーターフロント',
            'トイストーリーマニア': 'アメリカンウォーターフロント',
            'タートル・トーク': 'アメリカンウォーターフロント',
            'エレクトリックレールウェイアメリカンウォーターフロント発': 'アメリカンウォーターフロント',
            '船アメリカンウォーターフロント発': 'アメリカンウォーターフロント',
            'ヴィークル': 'アメリカンウォーターフロント',
            'センターオブジアース': 'ミステリアスアイランド',
            '海底二万マイル': 'ミステリアスアイランド',
            'ニモandフレンズシーライダー': 'ポートディスカバリー',
            'アクアトピア': 'ポートディスカバリー',
            '鉄道ポートディスカバリー発': 'ポートディスカバリー',
            'インディージョーンズクリスタルスカルの謎': 'ロストリバーデルタ',
            'レイジングスピリッツ': 'ロストリバーデルタ',
            '船ロストリバーデルタ発': 'ロストリバーデルタ',
            'マーメイドラグーン': 'マーメイドラグーン',
            'ジャンピン': 'マーメイドラグーン',
            'スカットルのスクーター': 'マーメイドラグーン',
            'フランダー': 'マーメイドラグーン',
            'バルーンレース': 'マーメイドラグーン',
            'ワールプール': 'マーメイドラグーン',
            'アナとエルサ': 'ファンタジースプリングス',
            'ラプンツェル': 'ファンタジースプリングス',
            'ピーターパン': 'ファンタジースプリングス',
            'ティンカーベル': 'ファンタジースプリングス',
            'マジックランプシアター': 'アラビアンコースト',
            'カルーセル': 'アラビアンコースト',
            'シンドバッド': 'アラビアンコースト',
            'ジャスミン': 'アラビアンコースト',
            'プラザグリーティング': 'メディテレーニアンハーバー',
            'ヴィレッジグリーティング': 'アメリカンウォーターフロント',
            'サルードス・アミーゴス': 'ロストリバーデルタ',
            'ドナルドグリーティング': 'ロストリバーデルタ',
            'ミッキーグリーティング': 'ロストリバーデルタ',
            'ミニーグリーティング': 'ロストリバーデルタ',
            'マーメイドラグーングリーティング': 'マーメイドラグーン',
            'アラビアンコーストグリーティング': 'アラビアンコースト'
        }
        
        # アトラクションのタイプ分類
        self.attraction_types = {
            'ソアリン': 'シアター・ライド',
            '船メディテレーニアンハーバー発': '移動・遊覧',
            'フォートレスエクスプロレーション': 'ウォークスルー',
            'ゴンドラ': '移動・遊覧',
            'タワーオブテラー': 'スリル',
            'トイストーリーマニア': 'シューティング',
            'タートル・トーク': 'シアター',
            'エレクトリックレールウェイアメリカンウォーターフロント発': '移動・遊覧',
            '船アメリカンウォーターフロント発': '移動・遊覧',
            'ヴィークル': '移動・遊覧',
            'センターオブジアース': 'スリル',
            '海底二万マイル': 'ダークライド',
            'ニモandフレンズシーライダー': 'シアター・ライド',
            'アクアトピア': 'スピン系',
            '鉄道ポートディスカバリー発': '移動・遊覧',
            'インディージョーンズクリスタルスカルの謎': 'スリル',
            'レイジングスピリッツ': 'スリル',
            '船ロストリバーデルタ発': '移動・遊覧',
            'マーメイドラグーン': 'キッズ',
            'ジャンピン': 'キッズ',
            'スカットルのスクーター': 'キッズ',
            'フランダー': 'キッズ',
            'バルーンレース': 'キッズ',
            'ワールプール': 'キッズ',
            'アナとエルサ': 'ボートライド',
            'ラプンツェル': 'ボートライド',
            'ピーターパン': 'ライド',
            'ティンカーベル': 'グリーティング',
            'マジックランプシアター': 'シアター',
            'カルーセル': 'キッズ',
            'シンドバッド': 'ボートライド',
            'ジャスミン': 'スピン系',
            'プラザグリーティング': 'グリーティング',
            'ヴィレッジグリーティング': 'グリーティング',
            'サルードス・アミーゴス': 'グリーティング',
            'ドナルドグリーティング': 'グリーティング',
            'ミッキーグリーティング': 'グリーティング',
            'ミニーグリーティング': 'グリーティング',
            'マーメイドラグーングリーティング': 'グリーティング',
            'アラビアンコーストグリーティング': 'グリーティング'
        }
        
        # アトラクションの人気度（ベースライン、1-10スケール）
        self.attraction_popularity = {
            'ソアリン': 10,
            'アナとエルサ': 10,
            'ラプンツェル': 9,
            'ピーターパン': 9,
            'トイストーリーマニア': 9,
            'センターオブジアース': 8,
            'タワーオブテラー': 8,
            'インディージョーンズクリスタルスカルの謎': 7,
            'レイジングスピリッツ': 7,
            'ティンカーベル': 7,
            'タートル・トーク': 6,
            '海底二万マイル': 6,
            'ニモandフレンズシーライダー': 6,
            'マジックランプシアター': 5,
            'シンドバッド': 5,
            'アクアトピア': 5,
            'ゴンドラ': 4,
            'ジャスミン': 4,
            'カルーセル': 3,
            'ジャンピン': 3,
            'スカットルのスクーター': 3,
            'フランダー': 3,
            'バルーンレース': 3,
            'ワールプール': 3,
            'マーメイドラグーン': 3,
            '船メディテレーニアンハーバー発': 2,
            '船アメリカンウォーターフロント発': 2,
            '船ロストリバーデルタ発': 2,
            'エレクトリックレールウェイアメリカンウォーターフロント発': 2,
            '鉄道ポートディスカバリー発': 2,
            'ヴィークル': 2,
            'フォートレスエクスプロレーション': 2,
            'プラザグリーティング': 5,
            'ヴィレッジグリーティング': 4,
            'サルードス・アミーゴス': 4,
            'ドナルドグリーティング': 5,
            'ミッキーグリーティング': 6,
            'ミニーグリーティング': 6,
            'マーメイドラグーングリーティング': 4,
            'アラビアンコーストグリーティング': 4
        }
        
        # 日本の学校休暇期間（概算）
        self.school_holidays = {
            # 春休み
            'spring_break': [(3, 20), (4, 7)],  # 3/20 - 4/7
            # ゴールデンウィーク
            'golden_week': [(4, 29), (5, 5)],
            # 夏休み
            'summer_break': [(7, 20), (8, 31)],
            # お盆
            'obon': [(8, 11), (8, 16)],
            # 秋休み（シルバーウィーク）
            'silver_week': [(9, 14), (9, 23)],
            # 冬休み
            'winter_break': [(12, 24), (1, 7)],
            # 正月
            'new_year': [(1, 1), (1, 3)]
        }
        
        # 特別イベント期間（2025年）
        self.special_events_2025 = [
            # ハロウィン
            {'name': 'halloween', 'start': (9, 10), 'end': (10, 31), 'impact': 1.2},
            # クリスマス
            {'name': 'christmas', 'start': (11, 8), 'end': (12, 25), 'impact': 1.3},
            # ファンタジースプリングス新エリア効果
            {'name': 'fantasy_springs', 'start': (1, 1), 'end': (12, 31), 'impact': 1.15},
            # サマーイベント
            {'name': 'summer_event', 'start': (7, 1), 'end': (9, 15), 'impact': 1.1},
        ]
        
        self.label_encoders = {}
        
    def add_time_features(self, df):
        """時間関連の特徴量を追加"""
        # 時刻をパース
        df['hour'] = df['time'].apply(lambda x: int(x.split(':')[0]))
        df['minute'] = df['time'].apply(lambda x: int(x.split(':')[1]))
        
        # 時間を連続値に変換
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        
        # 時間帯カテゴリ
        def get_time_period(hour):
            if hour < 10:
                return 'early_morning'  # 開園直後
            elif hour < 12:
                return 'morning'  # 午前
            elif hour < 14:
                return 'lunch'  # 昼食時
            elif hour < 17:
                return 'afternoon'  # 午後
            elif hour < 19:
                return 'evening'  # 夕方
            else:
                return 'night'  # 夜
        
        df['time_period'] = df['hour'].apply(get_time_period)
        
        # 開園からの経過時間（8:00開園と仮定）
        df['hours_since_open'] = df['time_decimal'] - 8.0
        df['hours_since_open'] = df['hours_since_open'].clip(lower=0)
        
        # 閉園までの時間（22:00閉園と仮定）
        df['hours_until_close'] = 22.0 - df['time_decimal']
        df['hours_until_close'] = df['hours_until_close'].clip(lower=0)
        
        # 時間の周期的特徴（サイン・コサイン変換）
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        return df
    
    def add_date_features(self, df):
        """日付関連の特徴量を追加"""
        # 日付をパース
        df['date_parsed'] = pd.to_datetime(df['date'])
        
        # 基本的な日付特徴
        df['year'] = df['date_parsed'].dt.year
        df['month'] = df['date_parsed'].dt.month
        df['day'] = df['date_parsed'].dt.day
        df['day_of_week'] = df['date_parsed'].dt.dayofweek  # 0=月曜日
        df['day_of_year'] = df['date_parsed'].dt.dayofyear
        df['week_of_year'] = df['date_parsed'].dt.isocalendar().week
        df['quarter'] = df['date_parsed'].dt.quarter
        
        # 曜日名
        day_names = ['月', '火', '水', '木', '金', '土', '日']
        df['day_name'] = df['day_of_week'].apply(lambda x: day_names[x])
        
        # 週末フラグ
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # 金曜日フラグ（週末に近い）
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)
        
        # 月曜日フラグ（週末の続き）
        df['is_monday'] = (df['day_of_week'] == 0).astype(int)
        
        # 月の周期的特徴
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # 曜日の周期的特徴
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # 月初・月末フラグ
        df['is_month_start'] = (df['day'] <= 3).astype(int)
        df['is_month_end'] = (df['day'] >= 28).astype(int)
        
        return df
    
    def add_holiday_features(self, df):
        """祝日・休暇関連の特徴量を追加"""
        
        # 日本の祝日フラグ
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
        
        # 連休判定（祝日または週末が連続）
        def is_consecutive_holiday(date, is_holiday, is_weekend):
            # 簡易版：祝日と週末を組み合わせた判定
            return is_holiday or is_weekend
        
        df['is_long_weekend'] = (
            (df['is_holiday'] == 1) | (df['is_weekend'] == 1)
        ).astype(int)
        
        # 学校休暇期間
        def get_school_holiday(date):
            month, day = date.month, date.day
            
            # 春休み
            if (month == 3 and day >= 20) or (month == 4 and day <= 7):
                return 'spring_break'
            # ゴールデンウィーク
            elif month == 4 and day >= 29 or (month == 5 and day <= 5):
                return 'golden_week'
            # 夏休み
            elif (month == 7 and day >= 20) or month == 8:
                return 'summer_break'
            # お盆
            elif month == 8 and 11 <= day <= 16:
                return 'obon'
            # シルバーウィーク
            elif month == 9 and 14 <= day <= 23:
                return 'silver_week'
            # 冬休み
            elif (month == 12 and day >= 24) or (month == 1 and day <= 7):
                return 'winter_break'
            else:
                return 'none'
        
        df['school_holiday'] = df['date_parsed'].apply(get_school_holiday)
        df['is_school_holiday'] = (df['school_holiday'] != 'none').astype(int)
        
        # 夏休みの強度（A/B/Cランク）
        def get_summer_intensity(date):
            month, day = date.month, date.day
            if month == 8 and 11 <= day <= 17:
                return 3  # お盆期間（最も混雑）
            elif (month == 7 and day >= 22) or (month == 8 and day <= 10):
                return 2  # 夏休みA
            elif month == 8 and day >= 18:
                return 1  # 夏休みC
            else:
                return 0
        
        df['summer_intensity'] = df['date_parsed'].apply(get_summer_intensity)
        
        return df
    
    def add_event_features(self, df):
        """イベント関連の特徴量を追加"""
        
        # 特別イベント期間判定
        def get_event_impact(date):
            impact = 1.0
            events = []
            
            for event in self.special_events_2025:
                start_month, start_day = event['start']
                end_month, end_day = event['end']
                
                # イベント期間内かチェック
                start_date = datetime(date.year, start_month, start_day)
                end_date = datetime(date.year, end_month, end_day)
                
                if start_date <= date <= end_date:
                    impact *= event['impact']
                    events.append(event['name'])
            
            return impact, ','.join(events) if events else 'none'
        
        results = df['date_parsed'].apply(get_event_impact)
        df['event_impact'] = results.apply(lambda x: x[0])
        df['active_events'] = results.apply(lambda x: x[1])
        
        # クリスマス・バレンタイン等の特別日
        def get_special_date_impact(date):
            month, day = date.month, date.day
            
            if month == 12 and 23 <= day <= 25:
                return 1.5, 'christmas'
            elif month == 2 and 13 <= day <= 14:
                return 1.3, 'valentine'
            elif month == 3 and 13 <= day <= 14:
                return 1.2, 'white_day'
            elif month == 10 and 30 <= day <= 31:
                return 1.4, 'halloween_peak'
            elif month == 1 and 1 <= day <= 3:
                return 1.4, 'new_year'
            else:
                return 1.0, 'none'
        
        special_results = df['date_parsed'].apply(get_special_date_impact)
        df['special_date_impact'] = special_results.apply(lambda x: x[0])
        df['special_date_name'] = special_results.apply(lambda x: x[1])
        
        return df
    
    def add_attraction_features(self, df):
        """アトラクション関連の特徴量を追加"""
        
        # エリア
        df['area'] = df['attraction_name'].map(self.attraction_areas).fillna('その他')
        
        # タイプ
        df['attraction_type'] = df['attraction_name'].map(self.attraction_types).fillna('その他')
        
        # 人気度
        df['popularity'] = df['attraction_name'].map(self.attraction_popularity).fillna(5)
        
        # ファンタジースプリングス新エリアフラグ
        df['is_fantasy_springs'] = (df['area'] == 'ファンタジースプリングス').astype(int)
        
        # スリル系フラグ
        df['is_thrill'] = (df['attraction_type'] == 'スリル').astype(int)
        
        # キッズ向けフラグ
        df['is_kids'] = (df['attraction_type'] == 'キッズ').astype(int)
        
        # グリーティングフラグ
        df['is_greeting'] = (df['attraction_type'] == 'グリーティング').astype(int)
        
        return df
    
    def add_weather_placeholder(self, df):
        """天候関連の特徴量（プレースホルダー）"""
        # 実際の天気データがない場合はデフォルト値を設定
        if 'temperature' not in df.columns:
            df['temperature'] = 20.0  # デフォルト気温
        if 'weather' not in df.columns:
            df['weather'] = 'sunny'  # デフォルト天気
        if 'is_rainy' not in df.columns:
            df['is_rainy'] = 0
        if 'weather_impact' not in df.columns:
            df['weather_impact'] = 1.0
        
        return df
    
    def add_lag_features(self, df):
        """過去データからのラグ特徴量"""
        # アトラクション×日付でグループ化してソート
        df = df.sort_values(['attraction_name', 'date', 'time'])
        
        # 同じアトラクションの前の時間帯の待ち時間
        df['prev_wait_time'] = df.groupby(['attraction_name', 'date'])['wait_time'].shift(1)
        df['prev_wait_time'] = df['prev_wait_time'].fillna(0)
        
        # 同じアトラクションの2時間前の待ち時間
        df['prev_2h_wait_time'] = df.groupby(['attraction_name', 'date'])['wait_time'].shift(4)
        df['prev_2h_wait_time'] = df['prev_2h_wait_time'].fillna(0)
        
        return df
    
    def add_interaction_features(self, df):
        """特徴量の交互作用"""
        # 人気度 × 週末
        df['popularity_weekend'] = df['popularity'] * df['is_weekend']
        
        # 人気度 × 祝日
        df['popularity_holiday'] = df['popularity'] * df['is_long_weekend']
        
        # 人気度 × 時間帯（ピーク時間）
        df['is_peak_hour'] = ((df['hour'] >= 10) & (df['hour'] <= 15)).astype(int)
        df['popularity_peak'] = df['popularity'] * df['is_peak_hour']
        
        # 新エリア × 週末
        df['fantasy_springs_weekend'] = df['is_fantasy_springs'] * df['is_weekend']
        
        # イベント影響 × 人気度
        df['event_popularity'] = df['event_impact'] * df['popularity']
        
        return df
    
    def encode_categorical(self, df, fit=True):
        """カテゴリ変数のエンコーディング"""
        categorical_cols = ['time_period', 'day_name', 'school_holiday', 
                          'area', 'attraction_type', 'active_events', 
                          'special_date_name', 'weather']
        
        for col in categorical_cols:
            if col in df.columns:
                if fit:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                        df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(
                            df[col].astype(str)
                        )
                    else:
                        df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(
                            df[col].astype(str)
                        )
                else:
                    if col in self.label_encoders:
                        # 未知のラベルを処理
                        known_labels = set(self.label_encoders[col].classes_)
                        df[col] = df[col].astype(str).apply(
                            lambda x: x if x in known_labels else 'unknown'
                        )
                        # unknownを追加（必要な場合）
                        if 'unknown' not in known_labels:
                            self.label_encoders[col].classes_ = np.append(
                                self.label_encoders[col].classes_, 'unknown'
                            )
                        df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col])
        
        return df
    
    def engineer_features(self, df, fit=True):
        """全特徴量を追加"""
        print("🔧 特徴量エンジニアリング開始...")
        
        df = self.add_time_features(df)
        print("  ✅ 時間特徴量追加")
        
        df = self.add_date_features(df)
        print("  ✅ 日付特徴量追加")
        
        df = self.add_holiday_features(df)
        print("  ✅ 祝日・休暇特徴量追加")
        
        df = self.add_event_features(df)
        print("  ✅ イベント特徴量追加")
        
        df = self.add_attraction_features(df)
        print("  ✅ アトラクション特徴量追加")
        
        df = self.add_weather_placeholder(df)
        print("  ✅ 天候特徴量追加")
        
        df = self.add_lag_features(df)
        print("  ✅ ラグ特徴量追加")
        
        df = self.add_interaction_features(df)
        print("  ✅ 交互作用特徴量追加")
        
        df = self.encode_categorical(df, fit=fit)
        print("  ✅ カテゴリエンコーディング完了")
        
        print(f"🎯 特徴量エンジニアリング完了: {len(df.columns)}列")
        
        return df


class DisneySeaWaitTimePredictor:
    """ディズニーシー待ち時間予測モデル"""
    
    def __init__(self):
        self.feature_engineer = DisneySeaFeatureEngineer()
        self.models = {}
        self.feature_columns = None
        self.scaler = StandardScaler()
        self.model_dir = "models"
        
        os.makedirs(self.model_dir, exist_ok=True)
    
    def load_data(self, data_dir="Disneysea"):
        """データを読み込み"""
        print("📂 データ読み込み中...")
        
        csv_files = glob.glob(os.path.join(data_dir, "disneysea_daily_*.csv"))
        
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
    
    def prepare_features(self, df, fit=True):
        """特徴量を準備"""
        df = self.feature_engineer.engineer_features(df, fit=fit)
        
        # 特徴量カラムを選択
        feature_cols = [
            # 時間特徴量
            'hour', 'minute', 'time_decimal', 'hours_since_open', 
            'hours_until_close', 'hour_sin', 'hour_cos',
            # 日付特徴量
            'month', 'day', 'day_of_week', 'day_of_year', 'week_of_year',
            'quarter', 'is_weekend', 'is_friday', 'is_monday',
            'month_sin', 'month_cos', 'dow_sin', 'dow_cos',
            'is_month_start', 'is_month_end',
            # 祝日・休暇
            'is_holiday', 'is_long_weekend', 'is_school_holiday',
            'summer_intensity',
            # イベント
            'event_impact', 'special_date_impact',
            # アトラクション
            'attraction_index', 'popularity', 'is_fantasy_springs',
            'is_thrill', 'is_kids', 'is_greeting',
            # 天候
            'temperature', 'is_rainy', 'weather_impact',
            # ラグ
            'prev_wait_time', 'prev_2h_wait_time',
            # 交互作用
            'popularity_weekend', 'popularity_holiday', 'is_peak_hour',
            'popularity_peak', 'fantasy_springs_weekend', 'event_popularity',
            # エンコード済みカテゴリ
            'time_period_encoded', 'day_name_encoded', 'school_holiday_encoded',
            'area_encoded', 'attraction_type_encoded'
        ]
        
        # 存在するカラムのみ選択
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if fit:
            self.feature_columns = available_cols
        
        return df, available_cols
    
    def train(self, df=None, test_size=0.2):
        """モデルを訓練"""
        if df is None:
            df = self.load_data()
        
        if df is None:
            return False
        
        print("\n🎓 モデル訓練開始...")
        
        # 特徴量準備
        df, feature_cols = self.prepare_features(df, fit=True)
        
        # 待ち時間0のデータは除外（クローズ中）
        df_train = df[df['wait_time'] > 0].copy()
        
        X = df_train[feature_cols]
        y = df_train['wait_time']
        
        print(f"📊 訓練データ: {len(X)}サンプル, {len(feature_cols)}特徴量")
        
        # 欠損値を埋める
        X = X.fillna(0)
        
        # 訓練/テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # スケーリング
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # モデル訓練
        print("\n📈 モデル訓練中...")
        
        # 1. Random Forest
        print("  🌲 Random Forest...")
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42
        )
        rf_model.fit(X_train, y_train)
        self.models['random_forest'] = rf_model
        
        rf_pred = rf_model.predict(X_test)
        rf_mae = mean_absolute_error(y_test, rf_pred)
        rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
        rf_r2 = r2_score(y_test, rf_pred)
        print(f"    MAE: {rf_mae:.2f}分, RMSE: {rf_rmse:.2f}分, R²: {rf_r2:.3f}")
        
        # 2. Gradient Boosting
        print("  🚀 Gradient Boosting...")
        gb_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=8,
            learning_rate=0.1,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        )
        gb_model.fit(X_train, y_train)
        self.models['gradient_boosting'] = gb_model
        
        gb_pred = gb_model.predict(X_test)
        gb_mae = mean_absolute_error(y_test, gb_pred)
        gb_rmse = np.sqrt(mean_squared_error(y_test, gb_pred))
        gb_r2 = r2_score(y_test, gb_pred)
        print(f"    MAE: {gb_mae:.2f}分, RMSE: {gb_rmse:.2f}分, R²: {gb_r2:.3f}")
        
        # 3. LightGBM（インストールされている場合）
        if HAS_LIGHTGBM:
            print("  💡 LightGBM...")
            lgb_model = lgb.LGBMRegressor(
                n_estimators=200,
                max_depth=10,
                learning_rate=0.05,
                num_leaves=31,
                min_child_samples=20,
                random_state=42,
                verbose=-1
            )
            lgb_model.fit(X_train, y_train)
            self.models['lightgbm'] = lgb_model
            
            lgb_pred = lgb_model.predict(X_test)
            lgb_mae = mean_absolute_error(y_test, lgb_pred)
            lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
            lgb_r2 = r2_score(y_test, lgb_pred)
            print(f"    MAE: {lgb_mae:.2f}分, RMSE: {lgb_rmse:.2f}分, R²: {lgb_r2:.3f}")
        
        # 特徴量重要度
        print("\n📊 特徴量重要度 (Top 15):")
        importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for i, row in importance.head(15).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
        
        # モデル保存
        self.save_models()
        
        print("\n✅ モデル訓練完了")
        
        return True
    
    def save_models(self):
        """モデルを保存"""
        joblib.dump(self.models, os.path.join(self.model_dir, 'wait_time_models.joblib'))
        joblib.dump(self.scaler, os.path.join(self.model_dir, 'scaler.joblib'))
        joblib.dump(self.feature_columns, os.path.join(self.model_dir, 'feature_columns.joblib'))
        joblib.dump(self.feature_engineer.label_encoders, 
                   os.path.join(self.model_dir, 'label_encoders.joblib'))
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
            print("✅ モデル読み込み完了")
            return True
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {e}")
            return False
    
    def predict(self, date, time_slots=None, attractions=None, 
                temperature=20.0, is_rainy=False, model_name='random_forest'):
        """待ち時間を予測"""
        
        if not self.models:
            if not self.load_models():
                print("❌ モデルが見つかりません。先に train() を実行してください。")
                return None
        
        # デフォルトの時間スロット
        if time_slots is None:
            time_slots = [f"{h:02d}:{m:02d}" 
                         for h in range(8, 22) 
                         for m in [15, 45]]
        
        # デフォルトのアトラクション
        if attractions is None:
            attractions = list(self.feature_engineer.attraction_popularity.keys())
        
        # 予測用データフレーム作成
        records = []
        for time in time_slots:
            for i, attraction in enumerate(attractions, 1):
                records.append({
                    'time': time,
                    'attraction_index': i,
                    'attraction_name': attraction,
                    'date': date,
                    'wait_time': 0,  # ダミー
                    'temperature': temperature,
                    'is_rainy': 1 if is_rainy else 0,
                    'weather': 'rainy' if is_rainy else 'sunny',
                    'weather_impact': 0.75 if is_rainy else 1.0
                })
        
        df = pd.DataFrame(records)
        
        # 特徴量準備
        df, _ = self.prepare_features(df, fit=False)
        
        # 予測実行
        X = df[self.feature_columns].fillna(0)
        
        if model_name in self.models:
            predictions = self.models[model_name].predict(X)
        else:
            predictions = self.models['random_forest'].predict(X)
        
        # 結果をデータフレームに追加
        df['predicted_wait_time'] = predictions.clip(min=0)  # 負の値を0に
        
        return df[['date', 'time', 'attraction_name', 'predicted_wait_time']]
    
    def predict_day(self, date, temperature=20.0, is_rainy=False, 
                   model_name='random_forest'):
        """1日分の予測を実行"""
        print(f"\n🔮 {date} の待ち時間予測")
        print("=" * 60)
        
        predictions = self.predict(
            date=date,
            temperature=temperature,
            is_rainy=is_rainy,
            model_name=model_name
        )
        
        if predictions is None:
            return None
        
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
    print("🏰 ディズニーシー待ち時間予測システム")
    print("=" * 60)
    
    predictor = DisneySeaWaitTimePredictor()
    
    # データ読み込みと訓練
    print("\n📚 モデル訓練...")
    predictor.train()
    
    # 予測例
    print("\n" + "=" * 60)
    print("🔮 予測テスト")
    
    # 任意の日付で予測（例：2025年7月20日）
    predictor.predict_day(
        date="2025-07-20",
        temperature=28.0,
        is_rainy=False
    )


if __name__ == "__main__":
    main()



