"""
プラン生成サービス - 待ち時間予測を使った最適プラン作成
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from closure_service import ClosureService


@dataclass
class TimeSlot:
    """時間スロット"""
    time: str
    hour: int
    attractions: Dict[str, float] = field(default_factory=dict)  # name -> wait_time


@dataclass
class RestaurantRecommendation:
    """レストラン推薦"""
    name: str
    cuisine: str
    price_range: str
    recommended_menu: List[str]
    tips: List[str] = field(default_factory=list)
    area: str = ""


@dataclass
class ShowRecommendation:
    """ショー・パレード推薦"""
    name: str
    time: str
    location: str
    duration_minutes: int
    tips: List[str] = field(default_factory=list)
    is_entry_required: bool = False  # 抽選が必要か


@dataclass
class PlanItem:
    """プランの1項目"""
    time: str
    attraction: str
    wait_minutes: int
    duration_minutes: int
    action_type: str  # "attraction", "meal", "show", "rest", "shopping", "parade"
    notes: str = ""
    travel_minutes: int = 0  # 移動時間
    area: str = ""  # エリア名
    end_time: str = ""  # 終了時刻
    restaurant: Optional[RestaurantRecommendation] = None  # レストラン情報
    show_info: Optional[ShowRecommendation] = None  # ショー情報


@dataclass
class DayPlan:
    """1日のプラン"""
    date: str
    park: str
    items: List[PlanItem]
    total_wait_minutes: int
    total_travel_minutes: int  # 移動時間の合計
    total_attractions: int
    user_preferences: Dict
    tips: List[str]
    data_source: str = "default"  # "prediction" or "default"
    closed_attractions: List[str] = field(default_factory=list)  # 休止中のアトラクション
    recommended_restaurants: List[RestaurantRecommendation] = field(default_factory=list)
    recommended_shows: List[ShowRecommendation] = field(default_factory=list)


class PlanGeneratorService:
    """プラン生成サービス"""
    
    # アトラクション属性データ
    ATTRACTION_ATTRIBUTES = {
        # ディズニーランド
        "美女と野獣": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "fantasyland", "duration": 8, "dpa": True},
        "ビッグサンダー": {"park": "tdl", "thrill": 3, "kids_friendly": False, "height": 102, "area": "westernland", "duration": 4, "dpa": True},
        "スペースマウンテン": {"park": "tdl", "thrill": 4, "kids_friendly": False, "height": 102, "area": "tomorrowland", "duration": 3, "dpa": True},
        "スプラッシュ": {"park": "tdl", "thrill": 3, "kids_friendly": False, "height": 90, "area": "critter_country", "duration": 10, "dpa": True, "wet": True},
        "ホーンテッド": {"park": "tdl", "thrill": 2, "kids_friendly": True, "area": "fantasyland", "duration": 15},
        "カリブ": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "adventureland", "duration": 15},
        "プーさん": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "fantasyland", "duration": 4, "dpa": True},
        "ベイマックス": {"park": "tdl", "thrill": 2, "kids_friendly": True, "height": 81, "area": "tomorrowland", "duration": 2, "dpa": True},
        "バズ": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "tomorrowland", "duration": 4},
        "モンスターズ": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "tomorrowland", "duration": 4},
        "イッツアスモールワールド": {"park": "tdl", "thrill": 1, "kids_friendly": True, "area": "fantasyland", "duration": 10},
        "スターツアーズ": {"park": "tdl", "thrill": 2, "kids_friendly": False, "height": 102, "area": "tomorrowland", "duration": 5},
        
        # ディズニーシー
        "ソアリン": {"park": "tds", "thrill": 2, "kids_friendly": True, "height": 102, "area": "mediterranean", "duration": 5, "dpa": True, "popular": True},
        "アナとエルサ": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "fantasy_springs", "duration": 6, "dpa": True, "popular": True},
        "ラプンツェル": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "fantasy_springs", "duration": 5, "dpa": True, "popular": True},
        "ピーターパン": {"park": "tds", "thrill": 2, "kids_friendly": True, "area": "fantasy_springs", "duration": 6, "dpa": True, "popular": True},
        "ティンカーベル": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "fantasy_springs", "duration": 2, "dpa": True},
        "タワーオブテラー": {"park": "tds", "thrill": 5, "kids_friendly": False, "height": 102, "area": "american", "duration": 2, "dpa": True},
        "トイストーリー": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "american", "duration": 7, "dpa": True, "popular": True},
        "センターオブジアース": {"park": "tds", "thrill": 4, "kids_friendly": False, "height": 117, "area": "mysterious", "duration": 3, "dpa": True},
        "インディージョーンズ": {"park": "tds", "thrill": 3, "kids_friendly": False, "height": 117, "area": "lost_river", "duration": 3, "dpa": True},
        "レイジングスピリッツ": {"park": "tds", "thrill": 4, "kids_friendly": False, "height": 117, "area": "lost_river", "duration": 2},
        "ニモ": {"park": "tds", "thrill": 2, "kids_friendly": True, "height": 90, "area": "port_discovery", "duration": 5},
        "海底二万マイル": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "mysterious", "duration": 5},
        "マジックランプシアター": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "arabian", "duration": 23},
        "シンドバッド": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "arabian", "duration": 10},
        "ゴンドラ": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "mediterranean", "duration": 12},
        "タートル": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "american", "duration": 30},
        "アクアトピア": {"park": "tds", "thrill": 1, "kids_friendly": True, "area": "port_discovery", "duration": 3},
    }
    
    # エリア間移動時間（分）- 徒歩での平均移動時間
    AREA_TRAVEL_TIMES = {
        # ディズニーランド
        "tdl": {
            ("world_bazaar", "adventureland"): 3,
            ("world_bazaar", "westernland"): 5,
            ("world_bazaar", "critter_country"): 8,
            ("world_bazaar", "fantasyland"): 4,
            ("world_bazaar", "toontown"): 7,
            ("world_bazaar", "tomorrowland"): 3,
            ("adventureland", "westernland"): 3,
            ("adventureland", "critter_country"): 5,
            ("adventureland", "fantasyland"): 6,
            ("adventureland", "toontown"): 10,
            ("adventureland", "tomorrowland"): 7,
            ("westernland", "critter_country"): 3,
            ("westernland", "fantasyland"): 5,
            ("westernland", "toontown"): 8,
            ("westernland", "tomorrowland"): 8,
            ("critter_country", "fantasyland"): 6,
            ("critter_country", "toontown"): 10,
            ("critter_country", "tomorrowland"): 10,
            ("fantasyland", "toontown"): 4,
            ("fantasyland", "tomorrowland"): 5,
            ("toontown", "tomorrowland"): 5,
        },
        # ディズニーシー
        "tds": {
            ("mediterranean", "american"): 5,
            ("mediterranean", "port_discovery"): 8,
            ("mediterranean", "lost_river"): 12,
            ("mediterranean", "arabian"): 10,
            ("mediterranean", "mermaid"): 8,
            ("mediterranean", "mysterious"): 6,
            ("mediterranean", "fantasy_springs"): 15,
            ("american", "port_discovery"): 5,
            ("american", "lost_river"): 8,
            ("american", "arabian"): 12,
            ("american", "mermaid"): 10,
            ("american", "mysterious"): 8,
            ("american", "fantasy_springs"): 12,
            ("port_discovery", "lost_river"): 5,
            ("port_discovery", "arabian"): 10,
            ("port_discovery", "mermaid"): 8,
            ("port_discovery", "mysterious"): 6,
            ("port_discovery", "fantasy_springs"): 10,
            ("lost_river", "arabian"): 6,
            ("lost_river", "mermaid"): 8,
            ("lost_river", "mysterious"): 4,
            ("lost_river", "fantasy_springs"): 8,
            ("arabian", "mermaid"): 3,
            ("arabian", "mysterious"): 8,
            ("arabian", "fantasy_springs"): 12,
            ("mermaid", "mysterious"): 6,
            ("mermaid", "fantasy_springs"): 10,
            ("mysterious", "fantasy_springs"): 10,
        },
    }
    
    # 予測データのアトラクション名とATTRACTION_ATTRIBUTESのマッピング
    PREDICTION_NAME_MAPPING = {
        # 予測データの名前 → ATTRACTION_ATTRIBUTESのキー
        "ソアリン": "ソアリン",
        "アナとエルサ": "アナとエルサ",
        "ラプンツェル": "ラプンツェル",
        "ピーターパン": "ピーターパン",
        "ティンカーベル": "ティンカーベル",
        "タワーオブテラー": "タワーオブテラー",
        "トイストーリーマニア": "トイストーリー",
        "センターオブジアース": "センターオブジアース",
        "インディージョーンズクリスタルスカルの謎": "インディージョーンズ",
        "レイジングスピリッツ": "レイジングスピリッツ",
        "ニモandフレンズシーライダー": "ニモ",
        "海底二万マイル": "海底二万マイル",
        "マジックランプシアター": "マジックランプシアター",
        "シンドバッド": "シンドバッド",
        "ゴンドラ": "ゴンドラ",
        "タートル・トーク": "タートル",
        "アクアトピア": "アクアトピア",
    }
    
    # 逆マッピング（ATTRACTION_ATTRIBUTES → 予測データ名）
    REVERSE_NAME_MAPPING = {
        "ソアリン": ["ソアリン"],
        "アナとエルサ": ["アナとエルサ"],
        "ラプンツェル": ["ラプンツェル"],
        "ピーターパン": ["ピーターパン"],
        "ティンカーベル": ["ティンカーベル"],
        "タワーオブテラー": ["タワーオブテラー"],
        "トイストーリー": ["トイストーリーマニア", "トイストーリー"],
        "センターオブジアース": ["センターオブジアース"],
        "インディージョーンズ": ["インディージョーンズクリスタルスカルの謎", "インディージョーンズ"],
        "レイジングスピリッツ": ["レイジングスピリッツ"],
        "ニモ": ["ニモandフレンズシーライダー", "ニモ"],
        "海底二万マイル": ["海底二万マイル"],
        "マジックランプシアター": ["マジックランプシアター"],
        "シンドバッド": ["シンドバッド"],
        "ゴンドラ": ["ゴンドラ"],
        "タートル": ["タートル・トーク", "タートル"],
        "アクアトピア": ["アクアトピア"],
        # ランド
        "美女と野獣": ["美女と野獣"],
        "ビッグサンダー": ["ビッグサンダー", "ビッグサンダーマウンテン"],
        "スペースマウンテン": ["スペースマウンテン"],
        "スプラッシュ": ["スプラッシュ", "スプラッシュマウンテン"],
        "ホーンテッド": ["ホーンテッド", "ホーンテッドマンション"],
        "カリブ": ["カリブ", "カリブの海賊"],
        "プーさん": ["プーさん", "プーさんのハニーハント"],
        "ベイマックス": ["ベイマックス"],
        "バズ": ["バズ", "バズライトイヤー"],
        "モンスターズ": ["モンスターズ", "モンスターズインク"],
        "イッツアスモールワールド": ["イッツアスモールワールド", "スモールワールド"],
        "スターツアーズ": ["スターツアーズ"],
    }
    
    # エリア名の日本語マッピング
    AREA_NAMES = {
        # ディズニーランド
        "world_bazaar": "ワールドバザール",
        "adventureland": "アドベンチャーランド",
        "westernland": "ウエスタンランド",
        "critter_country": "クリッターカントリー",
        "fantasyland": "ファンタジーランド",
        "toontown": "トゥーンタウン",
        "tomorrowland": "トゥモローランド",
        # ディズニーシー
        "mediterranean": "メディテレーニアンハーバー",
        "american": "アメリカンウォーターフロント",
        "port_discovery": "ポートディスカバリー",
        "lost_river": "ロストリバーデルタ",
        "arabian": "アラビアンコースト",
        "mermaid": "マーメイドラグーン",
        "mysterious": "ミステリアスアイランド",
        "fantasy_springs": "ファンタジースプリングス",
    }
    
    # ユーザータイプ別のプリセット
    USER_PRESETS = {
        "beginner": {
            "name": "初心者",
            "description": "初めてのディズニー。定番を効率よく回りたい",
            "thrill_max": 3,
            "priorities": ["popular", "定番"],
            "avoid": [],
            "max_wait": 60,
            "include_rest": True,
            "early_lunch": True,
        },
        "thrill_seeker": {
            "name": "絶叫好き",
            "description": "スリル系アトラクションを制覇したい",
            "thrill_min": 3,
            "priorities": ["thrill"],
            "avoid": [],
            "max_wait": 90,
            "include_rest": False,
        },
        "family_with_kids": {
            "name": "子連れファミリー",
            "description": "小さな子供と一緒に楽しみたい",
            "kids_only": True,
            "height_limit": 90,  # 子供の身長
            "priorities": ["kids_friendly"],
            "avoid": ["thrill"],
            "max_wait": 45,
            "include_rest": True,
            "early_lunch": True,
            "include_nap": True,
        },
        "fantasy_springs_focus": {
            "name": "ファンタジースプリングス優先",
            "description": "新エリアを中心に楽しみたい",
            "area_focus": ["fantasy_springs"],
            "priorities": ["fantasy_springs"],
            "max_wait": 120,
        },
        "efficient": {
            "name": "効率重視",
            "description": "待ち時間を最小化して多くのアトラクションを回りたい",
            "priorities": ["low_wait"],
            "max_wait": 30,
            "avoid_peak": True,
        },
        "relaxed": {
            "name": "ゆったり派",
            "description": "待ち時間が少ないアトラクションでゆったり過ごしたい",
            "priorities": ["low_wait", "atmosphere"],
            "max_wait": 20,
            "include_rest": True,
            "include_shows": True,
        },
        "couple": {
            "name": "カップル",
            "description": "ロマンチックなアトラクションを楽しみたい",
            "priorities": ["romantic", "atmosphere"],
            "recommended": ["ゴンドラ", "ソアリン", "シンドバッド", "美女と野獣"],
            "evening_focus": True,
        },
    }
    
    def __init__(self, prediction_dir: str = None, data_dir: str = None):
        if prediction_dir:
            self.prediction_dir = Path(prediction_dir)
        else:
            self.prediction_dir = Path(__file__).parent.parent / "predictions"
        
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / "data"
        
        self.predictions_cache = {}
        
        # 休止情報サービスを初期化
        self.closure_service = ClosureService(data_dir=str(self.data_dir))
        
        # レストラン・ショーデータを読み込む
        self.restaurants = self._load_restaurants()
        self.shows_parades = self._load_shows_parades()
    
    def _load_restaurants(self) -> Dict:
        """レストランデータを読み込む"""
        try:
            with open(self.data_dir / "restaurants_full.json", "r", encoding="utf-8") as f:
                return json.load(f).get("restaurants", {})
        except Exception as e:
            print(f"⚠️ レストランデータ読み込みエラー: {e}")
            return {}
    
    def _load_shows_parades(self) -> Dict:
        """ショー・パレードデータを読み込む"""
        try:
            with open(self.data_dir / "shows_parades_2025.json", "r", encoding="utf-8") as f:
                return json.load(f).get("shows_and_parades_2025", {})
        except Exception as e:
            print(f"⚠️ ショー・パレードデータ読み込みエラー: {e}")
            return {}
    
    def load_predictions(self, date: str = None) -> Dict[int, TimeSlot]:
        """予測データを読み込む"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if date in self.predictions_cache:
            return self.predictions_cache[date]
        
        # 予測CSVを探す
        csv_paths = [
            self.prediction_dir / date / f"prediction_{date}.csv",
            self.prediction_dir / f"prediction_{date}.csv",
        ]
        
        predictions = {}  # hour -> TimeSlot
        
        for csv_path in csv_paths:
            if csv_path.exists():
                print(f"📊 予測データを読み込み中: {csv_path}")
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        row_count = 0
                        for row in reader:
                            time_str = row.get("time", "")
                            attraction = row.get("attraction_name", "")
                            wait_time_str = row.get("predicted_wait_time", "0")
                            
                            if not time_str or not attraction:
                                continue
                            
                            try:
                                wait_time = float(wait_time_str)
                            except ValueError:
                                continue
                            
                            hour = int(time_str.split(":")[0])
                            
                            if hour not in predictions:
                                predictions[hour] = TimeSlot(time=time_str, hour=hour)
                            
                            # 予測データの名前をそのまま保存
                            predictions[hour].attractions[attraction] = wait_time
                            row_count += 1
                    
                    print(f"✅ 予測データ読み込み完了: {row_count}行, {len(predictions)}時間帯")
                    break
                except Exception as e:
                    print(f"Error loading predictions: {e}")
        
        if not predictions:
            print(f"⚠️ 予測データが見つかりません: {date}")
        
        self.predictions_cache[date] = predictions
        return predictions
    
    def get_best_time_for_attraction(self, attraction_name: str, predictions: Dict[int, TimeSlot], 
                                      start_hour: int = 9, end_hour: int = 21) -> tuple:
        """アトラクションの最適な時間帯を取得"""
        best_hour = None
        best_wait = float('inf')
        
        for hour in range(start_hour, end_hour + 1):
            if hour not in predictions:
                continue
            
            slot = predictions[hour]
            for name, wait_time in slot.attractions.items():
                if attraction_name.lower() in name.lower() or name.lower() in attraction_name.lower():
                    if wait_time < best_wait:
                        best_wait = wait_time
                        best_hour = hour
        
        return best_hour, best_wait if best_hour else (None, None)
    
    def generate_plan(self, park: str, user_type: str = "beginner", 
                      custom_preferences: Dict = None, date: str = None,
                      start_time: str = "09:00", end_time: str = "21:00") -> DayPlan:
        """
        ユーザーの要望に応じたプランを生成
        
        Args:
            park: "tdl" or "tds"
            user_type: ユーザータイプ（beginner, thrill_seeker, family_with_kids, etc.）
            custom_preferences: カスタム設定（上書き用）
            date: 日付（YYYY-MM-DD）、Noneなら今日
            start_time: 開始時刻
            end_time: 終了時刻
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # ユーザー設定を取得
        preferences = self.USER_PRESETS.get(user_type, self.USER_PRESETS["beginner"]).copy()
        if custom_preferences:
            preferences.update(custom_preferences)
        
        # 予測データを読み込む
        predictions = self.load_predictions(date)
        data_source = "prediction" if predictions else "default"
        
        # 休止中のアトラクションを取得
        closed_attractions = self._get_closed_attractions_for_date(park, date)
        
        # パークに応じたアトラクションをフィルタリング（休止中を除外）
        available_attractions = self._filter_attractions(park, preferences, closed_attractions)
        
        # プランを生成
        plan_items = []
        current_hour = int(start_time.split(":")[0])
        current_minute = int(start_time.split(":")[1]) if ":" in start_time else 0
        end_hour = int(end_time.split(":")[0])
        visited = set()
        total_wait = 0
        total_travel = 0
        current_area = ""  # 現在のエリア
        used_restaurants = []  # 使用済みレストラン
        
        # 朝イチの人気アトラクション（最大2つ）
        morning_attractions = self._get_morning_recommendations(available_attractions, predictions, preferences)
        for i, morning_pick in enumerate(morning_attractions[:2]):
            if current_hour >= 11:  # 11時以降は朝イチ枠終了
                break
            
            wait = self._get_wait_time(morning_pick, predictions, current_hour)
            attraction_area = self._get_area(morning_pick)
            duration = self._get_duration(morning_pick)
            travel_time = self._get_travel_time(park, current_area, attraction_area) if current_area else 0
            
            start_time_str = f"{current_hour:02d}:{current_minute:02d}"
            end_time_str = self._calculate_end_time(start_time_str, travel_time, int(wait), duration)
            
            # 待ち時間が長い場合はDPA推奨のノート
            notes = "朝イチで乗るのがおすすめ！" if i == 0 else "人気アトラクション！"
            if wait >= 60:
                notes += " / DPA利用推奨"
            
            plan_items.append(PlanItem(
                time=start_time_str,
                attraction=morning_pick,
                wait_minutes=int(wait),
                duration_minutes=duration,
                action_type="attraction",
                notes=notes,
                travel_minutes=travel_time,
                area=attraction_area,
                end_time=end_time_str
            ))
            visited.add(morning_pick)
            total_wait += int(wait)
            total_travel += travel_time
            current_area = attraction_area
            
            # 終了時刻から次の開始時刻を計算
            total_mins = travel_time + int(wait) + duration
            current_minute += total_mins
            current_hour += current_minute // 60
            current_minute = current_minute % 60
        
        # メインループ
        while current_hour < end_hour - 1:
            current_time_str = f"{current_hour:02d}:{current_minute:02d}"
            
            # 昼食タイム
            if current_hour in [11, 12] and preferences.get("early_lunch"):
                if current_hour == 11 and not any(i.action_type == "meal" and "昼食" in i.attraction for i in plan_items):
                    lunch_restaurant = self._get_restaurant_recommendation(park, "lunch", preferences, current_area, used_restaurants)
                    
                    restaurant_name = lunch_restaurant.name if lunch_restaurant else "レストラン"
                    if lunch_restaurant:
                        used_restaurants.append(lunch_restaurant.name)
                    notes = "混雑を避けて早めのランチがおすすめ"
                    if lunch_restaurant and lunch_restaurant.recommended_menu:
                        notes += f"\n   📍 おすすめ: {', '.join(lunch_restaurant.recommended_menu[:3])}"
                    
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction=f"🍽️ 昼食: {restaurant_name}",
                        wait_minutes=0,
                        duration_minutes=60,
                        action_type="meal",
                        notes=notes,
                        travel_minutes=0,
                        area=lunch_restaurant.area if lunch_restaurant else current_area,
                        end_time=self._calculate_end_time(current_time_str, 0, 0, 60),
                        restaurant=lunch_restaurant
                    ))
                    current_hour += 1
                    current_minute = 0
                    continue
            elif current_hour == 12 and not preferences.get("early_lunch"):
                if not any(i.action_type == "meal" and "昼食" in i.attraction for i in plan_items):
                    lunch_restaurant = self._get_restaurant_recommendation(park, "lunch", preferences, current_area, used_restaurants)
                    
                    restaurant_name = lunch_restaurant.name if lunch_restaurant else "レストラン"
                    if lunch_restaurant:
                        used_restaurants.append(lunch_restaurant.name)
                    notes = ""
                    if lunch_restaurant and lunch_restaurant.recommended_menu:
                        notes = f"おすすめ: {', '.join(lunch_restaurant.recommended_menu[:3])}"
                    
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction=f"🍽️ 昼食: {restaurant_name}",
                        wait_minutes=0,
                        duration_minutes=60,
                        action_type="meal",
                        notes=notes,
                        travel_minutes=0,
                        area=lunch_restaurant.area if lunch_restaurant else current_area,
                        end_time=self._calculate_end_time(current_time_str, 0, 0, 60),
                        restaurant=lunch_restaurant
                    ))
                    current_hour += 1
                    current_minute = 0
                    continue
            
            # 休憩タイム（子連れの場合）
            if current_hour == 14 and preferences.get("include_nap"):
                if not any(i.action_type == "rest" for i in plan_items):
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction="休憩・お昼寝タイム",
                        wait_minutes=0,
                        duration_minutes=60,
                        action_type="rest",
                        notes="暑さ・疲れ対策に休憩を",
                        travel_minutes=0,
                        area=current_area,
                        end_time=self._calculate_end_time(current_time_str, 0, 0, 60)
                    ))
                    current_hour += 1
                    current_minute = 0
                    continue
            
            # 通常の休憩
            if current_hour == 15 and preferences.get("include_rest") and not preferences.get("include_nap"):
                if not any(i.action_type == "rest" for i in plan_items):
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction="休憩・軽食",
                        wait_minutes=0,
                        duration_minutes=30,
                        action_type="rest",
                        notes="ここで一休み",
                        travel_minutes=0,
                        area=current_area,
                        end_time=self._calculate_end_time(current_time_str, 0, 0, 30)
                    ))
            
            # 夕食タイム
            if current_hour == 17:
                if not any(i.action_type == "meal" and "夕食" in i.attraction for i in plan_items):
                    dinner_restaurant = self._get_restaurant_recommendation(park, "dinner", preferences, current_area, used_restaurants)
                    
                    restaurant_name = dinner_restaurant.name if dinner_restaurant else "レストラン"
                    if dinner_restaurant:
                        used_restaurants.append(dinner_restaurant.name)
                    notes = "ショー前に済ませるのがおすすめ"
                    if dinner_restaurant:
                        if dinner_restaurant.recommended_menu:
                            notes += f"\n   📍 おすすめ: {', '.join(dinner_restaurant.recommended_menu[:3])}"
                        if dinner_restaurant.price_range:
                            notes += f"\n   💰 {dinner_restaurant.price_range}"
                    
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction=f"🍽️ 夕食: {restaurant_name}",
                        wait_minutes=0,
                        duration_minutes=60,
                        action_type="meal",
                        notes=notes,
                        travel_minutes=0,
                        area=dinner_restaurant.area if dinner_restaurant else current_area,
                        end_time=self._calculate_end_time(current_time_str, 0, 0, 60),
                        restaurant=dinner_restaurant
                    ))
                    current_hour += 1
                    current_minute = 0
                    continue
            
            # アトラクションを選択（移動時間を考慮）
            next_attraction = self._select_next_attraction_with_travel(
                park, available_attractions, predictions, current_hour, 
                visited, preferences, current_area
            )
            
            if next_attraction:
                wait = self._get_wait_time(next_attraction, predictions, current_hour)
                attraction_area = self._get_area(next_attraction)
                travel_time = self._get_travel_time(park, current_area, attraction_area)
                duration = self._get_duration(next_attraction)
                
                # 待ち時間が許容範囲内か確認
                max_wait = preferences.get("max_wait", 60)
                if wait <= max_wait or len(visited) < 3:  # 最初の3つは多少待っても入れる
                    end_time_str = self._calculate_end_time(current_time_str, travel_time, int(wait), duration)
                    
                    plan_items.append(PlanItem(
                        time=current_time_str,
                        attraction=next_attraction,
                        wait_minutes=int(wait),
                        duration_minutes=duration,
                        action_type="attraction",
                        notes=self._get_attraction_note(next_attraction, wait, preferences, travel_time),
                        travel_minutes=travel_time,
                        area=attraction_area,
                        end_time=end_time_str
                    ))
                    visited.add(next_attraction)
                    total_wait += int(wait)
                    total_travel += travel_time
                    current_area = attraction_area
                    
                    # 終了時刻から次の開始時刻を計算
                    total_mins = travel_time + int(wait) + duration
                    current_minute += total_mins
                    current_hour += current_minute // 60
                    current_minute = current_minute % 60
                    continue
            
            # 何も追加できなかった場合は時間を進める
            current_hour += 1
            current_minute = 0
        
        # ショー・パレード推薦を取得
        show_recommendations = self._get_show_recommendations(park, preferences)
        
        # 昼のパレード（14時台）を追加
        day_parades = [s for s in show_recommendations if "14:00" in s.time or "パレード" in s.name and "エレクトリカル" not in s.name]
        if day_parades and (preferences.get("include_shows") or user_type in ["beginner", "family_with_kids"]):
            parade = day_parades[0]
            # 既存のアイテムの間に挿入（14時台のアイテムを探す）
            insert_idx = len(plan_items)
            for idx, item in enumerate(plan_items):
                if item.time and item.time.startswith("14"):
                    insert_idx = idx
                    break
            
            parade_item = PlanItem(
                time="13:30",
                attraction=f"🎪 {parade.name}",
                wait_minutes=30,  # 場所取り時間
                duration_minutes=parade.duration_minutes,
                action_type="parade",
                notes="場所取りは30分前から。レジャーシート持参推奨",
                travel_minutes=5,
                area="",
                end_time=self._calculate_end_time("13:30", 5, 30, parade.duration_minutes),
                show_info=parade
            )
            plan_items.insert(insert_idx, parade_item)
            total_travel += 5
        
        # ナイトショー・パレードを追加
        night_shows = [s for s in show_recommendations if s.time and int(s.time.split(":")[0]) >= 19]
        if night_shows and (preferences.get("include_shows") or user_type in ["beginner", "family_with_kids", "couple"]):
            night_show = night_shows[0]
            
            # 場所取り開始時刻
            show_hour, show_min = map(int, night_show.time.split(":"))
            wait_start_hour = show_hour
            wait_start_min = show_min - 30
            if wait_start_min < 0:
                wait_start_hour -= 1
                wait_start_min += 60
            wait_start_time = f"{wait_start_hour:02d}:{wait_start_min:02d}"
            
            notes = "30分前から場所取りがおすすめ"
            if night_show.is_entry_required:
                notes = "⚠️ 抽選（エントリー受付）が必要！入園後すぐに抽選しましょう"
            if night_show.tips:
                notes += f"\n   💡 {night_show.tips[0]}"
            
            plan_items.append(PlanItem(
                time=wait_start_time,
                attraction=f"🌙 {night_show.name}",
                wait_minutes=30,  # 場所取り時間
                duration_minutes=night_show.duration_minutes,
                action_type="show",
                notes=notes,
                travel_minutes=5,
                area="",
                end_time=self._calculate_end_time(night_show.time, 0, 0, night_show.duration_minutes),
                show_info=night_show
            ))
            total_travel += 5
        
        # 閉園前のショッピング
        plan_items.append(PlanItem(
            time=f"{end_hour - 1:02d}:00",
            attraction="お土産ショッピング",
            wait_minutes=0,
            duration_minutes=30,
            action_type="shopping",
            notes="閉園間際は混雑するので少し早めに",
            travel_minutes=0,
            area="",
            end_time=f"{end_hour - 1:02d}:30"
        ))
        
        # Tips生成
        tips = self._generate_tips(park, preferences, predictions, total_travel)
        
        # 休止中のアトラクションリストを取得
        closed_list = self.closure_service.get_closed_attractions(park=park, date=date)
        
        return DayPlan(
            date=date,
            park=park,
            items=plan_items,
            total_wait_minutes=total_wait,
            total_travel_minutes=total_travel,
            total_attractions=len([i for i in plan_items if i.action_type == "attraction"]),
            user_preferences=preferences,
            tips=tips,
            data_source=data_source,
            closed_attractions=closed_list
        )
    
    def _get_closed_attractions_for_date(self, park: str, date: str) -> Set[str]:
        """指定日の休止アトラクションを取得"""
        try:
            closed_list = self.closure_service.get_closed_attractions(park=park, date=date)
            closed_set = set()
            
            for closed_name in closed_list:
                # 休止リストの名前を正規化
                normalized = closed_name.lower().replace(" ", "").replace("・", "").replace("　", "")
                closed_set.add(normalized)
                
                # ATTRACTION_ATTRIBUTESのキーとマッチング
                for attr_name in self.ATTRACTION_ATTRIBUTES.keys():
                    attr_normalized = attr_name.lower().replace(" ", "").replace("・", "")
                    if normalized in attr_normalized or attr_normalized in normalized:
                        closed_set.add(attr_name.lower())
            
            if closed_set:
                print(f"🔧 休止中アトラクション ({date}): {len(closed_list)}件")
            
            return closed_set
        except Exception as e:
            print(f"⚠️ 休止情報取得エラー: {e}")
            return set()
    
    def _filter_attractions(self, park: str, preferences: Dict, 
                           closed_attractions: Set[str] = None) -> List[str]:
        """条件に合うアトラクションをフィルタリング"""
        result = []
        
        if closed_attractions is None:
            closed_attractions = set()
        
        park_prefix = "tdl" if park == "tdl" else "tds"
        
        for name, attrs in self.ATTRACTION_ATTRIBUTES.items():
            if attrs.get("park") != park:
                continue
            
            # 休止中のアトラクションを除外
            if name.lower() in closed_attractions:
                print(f"  ⏸️ 休止中のためスキップ: {name}")
                continue
            
            # 子供向けフィルタ
            if preferences.get("kids_only") and not attrs.get("kids_friendly"):
                continue
            
            # 身長制限チェック
            height_limit = preferences.get("height_limit")
            if height_limit and attrs.get("height", 0) > height_limit:
                continue
            
            # スリルレベルチェック
            thrill_min = preferences.get("thrill_min", 0)
            thrill_max = preferences.get("thrill_max", 5)
            if not (thrill_min <= attrs.get("thrill", 1) <= thrill_max):
                continue
            
            # エリアフォーカス
            area_focus = preferences.get("area_focus")
            if area_focus and attrs.get("area") not in area_focus:
                # フォーカスエリア以外は優先度を下げる（でも除外はしない）
                pass
            
            result.append(name)
        
        return result
    
    def _get_morning_recommendation(self, attractions: List[str], 
                                     predictions: Dict, preferences: Dict) -> Optional[str]:
        """朝イチのおすすめアトラクション（1つ）"""
        recs = self._get_morning_recommendations(attractions, predictions, preferences)
        return recs[0] if recs else None
    
    def _get_morning_recommendations(self, attractions: List[str], 
                                      predictions: Dict, preferences: Dict) -> List[str]:
        """朝イチのおすすめアトラクション（複数）"""
        popular = []
        regular = []
        
        for name in attractions:
            attrs = self.ATTRACTION_ATTRIBUTES.get(name, {})
            if attrs.get("popular"):
                popular.append((name, 2))  # 最高優先度
            elif attrs.get("dpa"):
                popular.append((name, 1))  # 高優先度
            else:
                regular.append(name)
        
        # ファンタジースプリングス優先の場合
        if preferences.get("area_focus") == ["fantasy_springs"]:
            fs_popular = [(n, p + 1) for n, p in popular 
                          if self.ATTRACTION_ATTRIBUTES.get(n, {}).get("area") == "fantasy_springs"]
            if fs_popular:
                # FS内のアトラクションを優先的に並べる
                popular = fs_popular + [(n, p) for n, p in popular 
                                        if self.ATTRACTION_ATTRIBUTES.get(n, {}).get("area") != "fantasy_springs"]
        
        # 優先度でソート
        popular.sort(key=lambda x: x[1], reverse=True)
        
        result = [name for name, _ in popular]
        
        if not result:
            return attractions[:2] if attractions else []
        
        return result
    
    def _select_next_attraction(self, attractions: List[str], predictions: Dict,
                                 current_hour: int, visited: set, preferences: Dict) -> Optional[str]:
        """次のアトラクションを選択（移動時間なし）"""
        return self._select_next_attraction_with_travel(
            "tds", attractions, predictions, current_hour, visited, preferences, ""
        )
    
    def _select_next_attraction_with_travel(self, park: str, attractions: List[str], 
                                             predictions: Dict, current_hour: int, 
                                             visited: set, preferences: Dict,
                                             current_area: str) -> Optional[str]:
        """次のアトラクションを選択（移動時間を考慮）"""
        candidates = []
        
        for name in attractions:
            if name in visited:
                continue
            
            wait = self._get_wait_time(name, predictions, current_hour)
            attrs = self.ATTRACTION_ATTRIBUTES.get(name, {})
            attraction_area = attrs.get("area", "")
            
            # 移動時間を取得
            travel_time = self._get_travel_time(park, current_area, attraction_area) if current_area else 0
            
            # トータル時間（移動 + 待ち + 体験）
            total_time = travel_time + wait + attrs.get("duration", 5)
            
            # スコア計算
            score = 100 - wait  # 待ち時間が短いほど高スコア
            
            # 近いエリアにボーナス（移動時間が少ない方が効率的）
            if travel_time <= 3:
                score += 25  # 同エリアまたは隣接
            elif travel_time <= 6:
                score += 15
            elif travel_time <= 10:
                score += 5
            else:
                score -= 10  # 遠いエリアはペナルティ
            
            # 人気アトラクションはボーナス
            if attrs.get("popular"):
                score += 20
            
            # DPA対象はボーナス
            if attrs.get("dpa"):
                score += 10
            
            # エリアフォーカスボーナス
            if preferences.get("area_focus"):
                if attraction_area in preferences.get("area_focus"):
                    score += 30
            
            candidates.append((name, score, wait, travel_time))
        
        if not candidates:
            return None
        
        # スコアでソート
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def _get_wait_time(self, attraction_name: str, predictions: Dict[int, TimeSlot], hour: int) -> float:
        """特定時間帯の待ち時間を取得（予測データから）"""
        if not predictions or hour not in predictions:
            return self._get_default_wait_time(attraction_name)
        
        slot = predictions[hour]
        
        # REVERSE_NAME_MAPPINGを使って予測データの名前を探す
        possible_names = self.REVERSE_NAME_MAPPING.get(attraction_name, [attraction_name])
        
        for pred_name in possible_names:
            if pred_name in slot.attractions:
                return slot.attractions[pred_name]
        
        # 部分一致で探す
        for name, wait_time in slot.attractions.items():
            # 正規化して比較
            normalized_attr = attraction_name.replace(" ", "").replace("・", "").lower()
            normalized_pred = name.replace(" ", "").replace("・", "").lower()
            
            if normalized_attr in normalized_pred or normalized_pred in normalized_attr:
                return wait_time
        
        # 見つからない場合はデフォルト値
        return self._get_default_wait_time(attraction_name)
    
    def _get_default_wait_time(self, attraction_name: str) -> float:
        """デフォルトの待ち時間（予測データがない場合）"""
        attrs = self.ATTRACTION_ATTRIBUTES.get(attraction_name, {})
        
        # 人気度に応じたデフォルト値
        if attrs.get("popular"):
            return 90
        elif attrs.get("dpa"):
            return 60
        else:
            return 30
    
    def _get_duration(self, attraction_name: str) -> int:
        """アトラクションの所要時間を取得"""
        attrs = self.ATTRACTION_ATTRIBUTES.get(attraction_name, {})
        return attrs.get("duration", 5)
    
    def _get_attraction_note(self, attraction: str, wait: float, preferences: Dict, travel_time: int = 0) -> str:
        """アトラクションに対するノートを生成"""
        attrs = self.ATTRACTION_ATTRIBUTES.get(attraction, {})
        notes = []
        
        # 移動時間の注意
        if travel_time >= 10:
            notes.append(f"🚶移動{travel_time}分")
        
        if wait <= 20:
            notes.append("待ち時間短い！狙い目")
        elif wait >= 60:
            notes.append("DPA利用を検討")
        
        if attrs.get("wet"):
            notes.append("濡れる可能性あり")
        
        if attrs.get("area") == "fantasy_springs":
            notes.append("新エリア！")
        
        return " / ".join(notes) if notes else ""
    
    def _generate_tips(self, park: str, preferences: Dict, predictions: Dict, total_travel: int = 0) -> List[str]:
        """プランに対するTipsを生成"""
        tips = []
        
        # 移動に関するTips
        if total_travel >= 60:
            tips.append(f"📍 本日の総移動時間は約{total_travel}分。歩きやすい靴をおすすめします")
        
        # 一般的なTips
        tips.append("スタンバイパスは入園後すぐに取得しましょう")
        
        if preferences.get("kids_only"):
            tips.append("ベビーセンターの場所を事前に確認しておきましょう")
            tips.append("子供の体力に合わせて休憩を多めに")
        
        if preferences.get("area_focus") == ["fantasy_springs"]:
            tips.append("ファンタジースプリングスはスタンバイパスまたはDPAが必要な場合があります")
            tips.append("ホテル宿泊者はアーリーエントリーを活用しましょう")
        
        # パーク別の移動Tips
        if park == "tds":
            tips.append("シーは広いので、船やエレクトリックレールウェイも活用しましょう")
        elif park == "tdl":
            tips.append("ランドはシンデレラ城を中心に放射状。エリア間移動は城経由が便利")
        
        # 混雑時間帯の回避
        if predictions:
            peak_hours = self._find_peak_hours(predictions)
            if peak_hours:
                tips.append(f"混雑ピークは{peak_hours[0]}時台〜{peak_hours[-1]}時台。この時間帯は食事やショッピングがおすすめ")
        
        return tips
    
    def _find_peak_hours(self, predictions: Dict) -> List[int]:
        """混雑のピーク時間帯を見つける"""
        if not predictions:
            return [12, 13, 14]
        
        avg_waits = []
        for hour, slot in predictions.items():
            if slot.attractions:
                avg = sum(slot.attractions.values()) / len(slot.attractions)
                avg_waits.append((hour, avg))
        
        avg_waits.sort(key=lambda x: x[1], reverse=True)
        return [h for h, _ in avg_waits[:3]]
    
    def _get_restaurant_recommendation(self, park: str, meal_type: str, 
                                        preferences: Dict, current_area: str = "",
                                        exclude_names: List[str] = None) -> Optional[RestaurantRecommendation]:
        """レストラン推薦を取得"""
        park_key = "tokyo_disney_land" if park == "tdl" else "tokyo_disney_sea"
        park_restaurants = self.restaurants.get(park_key, {})
        
        if exclude_names is None:
            exclude_names = []
        
        candidates = []
        
        # ファンタジースプリングスの場合、専用レストランを優先
        if preferences.get("area_focus") == ["fantasy_springs"] and park == "tds":
            fs_restaurants = park_restaurants.get("fantasy_springs_restaurants", [])
            for r in fs_restaurants:
                if r.get("name", "") not in exclude_names:
                    candidates.append(r)
        
        # カップルの場合はテーブルサービスを優先
        if preferences.get("priorities") and "romantic" in preferences.get("priorities", []):
            for r in park_restaurants.get("table_service", []):
                if r.get("name", "") not in exclude_names:
                    candidates.append(r)
        
        # 子連れの場合はクイックサービスを優先
        if preferences.get("kids_only"):
            for r in park_restaurants.get("quick_service", []):
                if r.get("name", "") not in exclude_names:
                    candidates.append(r)
        else:
            # 夕食はテーブルサービスも候補に
            if meal_type == "dinner":
                for r in park_restaurants.get("table_service", []):
                    if r.get("name", "") not in exclude_names:
                        candidates.append(r)
            
            # クイックサービスも候補に
            for r in park_restaurants.get("quick_service", []):
                if r.get("name", "") not in exclude_names:
                    candidates.append(r)
        
        if not candidates:
            # 除外なしで再試行
            for r in park_restaurants.get("quick_service", []):
                candidates.append(r)
        
        if not candidates:
            return None
        
        # 現在のエリアに近いレストランを優先
        if current_area:
            area_restaurants = [r for r in candidates if r.get("area", "") == current_area]
            if area_restaurants:
                candidates = area_restaurants + [r for r in candidates if r.get("area", "") != current_area]
        
        # ランダムではなく、優先度で選択（夕食は2番目を選択するなど）
        idx = 0
        if meal_type == "dinner" and len(candidates) > 1:
            idx = 1  # 夕食は別のレストランを選ぶ
        
        selected = candidates[idx] if candidates else None
        
        if not selected:
            return None
        
        return RestaurantRecommendation(
            name=selected.get("name", ""),
            cuisine=selected.get("cuisine", ""),
            price_range=selected.get("price_range", ""),
            recommended_menu=selected.get("recommended_menu", []),
            tips=selected.get("tips", []),
            area=selected.get("area", "")
        )
    
    def _get_show_recommendations(self, park: str, preferences: Dict) -> List[ShowRecommendation]:
        """ショー・パレードの推薦リストを取得"""
        park_key = "tokyo_disney_land" if park == "tdl" else "tokyo_disney_sea"
        park_shows = self.shows_parades.get(park_key, {})
        
        recommendations = []
        
        # パレード（ランド）
        if park == "tdl":
            # 昼のパレード
            for parade in park_shows.get("day_parades", []):
                recommendations.append(ShowRecommendation(
                    name=parade.get("name", ""),
                    time="14:00",  # デフォルト時間
                    location=parade.get("route", "パレードルート"),
                    duration_minutes=parade.get("duration_minutes", 45),
                    tips=parade.get("tips", []),
                    is_entry_required=False
                ))
            
            # 夜のパレード
            for parade in park_shows.get("night_parades", []):
                times = parade.get("performance_times", ["19:35"])
                recommendations.append(ShowRecommendation(
                    name=parade.get("name", ""),
                    time=times[0] if times else "19:35",
                    location="パレードルート",
                    duration_minutes=parade.get("duration_minutes", 45),
                    tips=parade.get("tips", []),
                    is_entry_required=False
                ))
            
            # 花火
            for fireworks in park_shows.get("fireworks", []):
                recommendations.append(ShowRecommendation(
                    name=fireworks.get("name", "花火"),
                    time="20:30",
                    location="シンデレラ城前",
                    duration_minutes=fireworks.get("duration_minutes", 5),
                    tips=fireworks.get("viewing_tips", []),
                    is_entry_required=False
                ))
        
        # ハーバーショー（シー）
        if park == "tds":
            for show in park_shows.get("harbor_shows", []):
                times = show.get("performance_times", ["19:35"])
                recommendations.append(ShowRecommendation(
                    name=show.get("name", ""),
                    time=times[0] if times else "19:35",
                    location=show.get("location", "メディテレーニアンハーバー"),
                    duration_minutes=show.get("duration_minutes", 30),
                    tips=show.get("tips", []),
                    is_entry_required="抽選" in show.get("note", "")
                ))
            
            # シアターショー
            for show in park_shows.get("day_shows", []):
                recommendations.append(ShowRecommendation(
                    name=show.get("name", ""),
                    time="",  # 随時
                    location=show.get("location", ""),
                    duration_minutes=show.get("duration_minutes", 15),
                    tips=show.get("tips", []),
                    is_entry_required=False
                ))
        
        return recommendations
    
    def _get_travel_time(self, park: str, from_area: str, to_area: str) -> int:
        """2つのエリア間の移動時間を取得"""
        if not from_area or not to_area or from_area == to_area:
            return 0
        
        travel_times = self.AREA_TRAVEL_TIMES.get(park, {})
        
        # 両方向をチェック
        key1 = (from_area, to_area)
        key2 = (to_area, from_area)
        
        if key1 in travel_times:
            return travel_times[key1]
        elif key2 in travel_times:
            return travel_times[key2]
        
        return 5  # デフォルト5分
    
    def _get_area(self, attraction_name: str) -> str:
        """アトラクションのエリアを取得"""
        attrs = self.ATTRACTION_ATTRIBUTES.get(attraction_name, {})
        return attrs.get("area", "")
    
    def _get_area_name(self, area: str) -> str:
        """エリアの日本語名を取得"""
        return self.AREA_NAMES.get(area, area)
    
    def _calculate_end_time(self, start_time: str, travel_minutes: int, 
                            wait_minutes: int, duration_minutes: int) -> str:
        """終了時刻を計算"""
        try:
            hour, minute = map(int, start_time.split(":"))
            total_minutes = minute + travel_minutes + wait_minutes + duration_minutes
            end_hour = hour + total_minutes // 60
            end_minute = total_minutes % 60
            return f"{end_hour:02d}:{end_minute:02d}"
        except:
            return ""
    
    def format_plan(self, plan: DayPlan) -> str:
        """プランをテキストでフォーマット"""
        park_name = "ディズニーランド" if plan.park == "tdl" else "ディズニーシー"
        
        msg = f"🗓️ **{plan.date} {park_name}プラン**\n"
        msg += f"_{plan.user_preferences.get('name', '')}向け_\n"
        
        # データソースの表示
        if plan.data_source == "prediction":
            msg += f"📊 _待ち時間予測データ使用_\n\n"
        else:
            msg += f"📊 _推定待ち時間を使用_\n\n"
        
        msg += "**📋 タイムスケジュール**\n"
        current_area = ""
        restaurants_in_plan = []
        shows_in_plan = []
        
        for item in plan.items:
            icon = self._get_action_icon(item.action_type)
            
            # エリア移動の表示
            if item.area and item.area != current_area and item.action_type == "attraction":
                area_name = self._get_area_name(item.area)
                if item.travel_minutes > 0:
                    msg += f"   🚶 _{area_name}へ移動 ({item.travel_minutes}分)_\n"
                current_area = item.area
            
            if item.action_type == "attraction":
                end_display = f" → {item.end_time}" if item.end_time else ""
                msg += f"{item.time}{end_display} {icon} **{item.attraction}** ({item.wait_minutes}分待ち)\n"
            elif item.action_type == "meal":
                end_display = f" → {item.end_time}" if item.end_time else ""
                msg += f"{item.time}{end_display} {item.attraction}\n"
                
                # レストラン情報を追加
                if item.restaurant:
                    restaurants_in_plan.append(item.restaurant)
                    if item.restaurant.cuisine:
                        msg += f"   🍴 {item.restaurant.cuisine}\n"
                    if item.restaurant.price_range:
                        msg += f"   💰 {item.restaurant.price_range}\n"
                    if item.restaurant.recommended_menu:
                        menu_str = ", ".join(item.restaurant.recommended_menu[:3])
                        msg += f"   ⭐ おすすめ: {menu_str}\n"
            elif item.action_type in ["show", "parade"]:
                end_display = f" → {item.end_time}" if item.end_time else ""
                msg += f"{item.time}{end_display} {item.attraction}\n"
                
                # ショー情報を追加
                if item.show_info:
                    shows_in_plan.append(item.show_info)
                    if item.show_info.location:
                        msg += f"   📍 場所: {item.show_info.location}\n"
                    if item.show_info.is_entry_required:
                        msg += f"   ⚠️ **抽選（エントリー受付）必要**\n"
            else:
                msg += f"{item.time} {icon} {item.attraction}\n"
            
            if item.notes and item.action_type not in ["meal"]:  # 食事のノートは上で表示済み
                msg += f"   💡 {item.notes}\n"
        
        msg += f"\n**📊 サマリー**\n"
        msg += f"・アトラクション数: {plan.total_attractions}個\n"
        msg += f"・合計待ち時間: 約{plan.total_wait_minutes}分\n"
        msg += f"・合計移動時間: 約{plan.total_travel_minutes}分\n"
        
        # 1日の歩数目安
        estimated_steps = plan.total_travel_minutes * 100  # 1分で約100歩
        msg += f"・歩数目安: 約{estimated_steps:,}歩\n"
        
        # レストラン詳細
        if restaurants_in_plan:
            msg += "\n**🍽️ 本日のおすすめレストラン**\n"
            for rest in restaurants_in_plan:
                msg += f"・**{rest.name}**\n"
                if rest.cuisine:
                    msg += f"  ジャンル: {rest.cuisine}\n"
                if rest.price_range:
                    msg += f"  価格帯: {rest.price_range}\n"
                if rest.recommended_menu:
                    msg += f"  おすすめメニュー:\n"
                    for menu in rest.recommended_menu[:5]:
                        msg += f"    - {menu}\n"
                if rest.tips:
                    msg += f"  💡 {rest.tips[0]}\n"
        
        # ショー詳細
        if shows_in_plan:
            msg += "\n**🎭 本日のショー・パレード**\n"
            for show in shows_in_plan:
                msg += f"・**{show.name}**\n"
                if show.time:
                    msg += f"  開始時間: {show.time}\n"
                if show.duration_minutes:
                    msg += f"  上演時間: 約{show.duration_minutes}分\n"
                if show.location:
                    msg += f"  場所: {show.location}\n"
                if show.is_entry_required:
                    msg += f"  ⚠️ 抽選が必要（入園後すぐにエントリー！）\n"
        
        msg += "\n**💡 Tips**\n"
        for tip in plan.tips[:5]:
            msg += f"・{tip}\n"
        
        # 休止中のアトラクション
        if plan.closed_attractions:
            msg += "\n**🔧 本日休止中**\n"
            for closed in plan.closed_attractions[:5]:
                msg += f"・{closed}\n"
            if len(plan.closed_attractions) > 5:
                msg += f"...他{len(plan.closed_attractions) - 5}件\n"
        
        return msg
    
    def _get_action_icon(self, action_type: str) -> str:
        """アクションタイプに応じたアイコン"""
        icons = {
            "attraction": "🎢",
            "meal": "🍽️",
            "show": "🎭",
            "parade": "🎪",
            "rest": "☕",
            "shopping": "🛍️",
        }
        return icons.get(action_type, "📍")
    
    def get_available_user_types(self) -> List[Dict]:
        """利用可能なユーザータイプ一覧"""
        return [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in self.USER_PRESETS.items()
        ]


# テスト用
if __name__ == "__main__":
    service = PlanGeneratorService()
    
    print("=== プラン生成テスト ===\n")
    
    # 初心者向けプラン
    plan = service.generate_plan("tds", "beginner")
    print(service.format_plan(plan))
    
    print("\n" + "="*50 + "\n")
    
    # ファンタジースプリングス優先プラン
    plan = service.generate_plan("tds", "fantasy_springs_focus")
    print(service.format_plan(plan))

