"""
ディズニーチャットボット - コアエンジン
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    from wait_time_service import WaitTimeService
    WAIT_TIME_AVAILABLE = True
except ImportError:
    WAIT_TIME_AVAILABLE = False


@dataclass
class ChatResponse:
    """チャットボットの応答"""
    message: str
    category: str
    confidence: float
    related_data: Optional[dict] = None


class DisneyKnowledgeBase:
    """ディズニー情報のナレッジベース"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = Path(data_dir)
        self.parks = {}
        self.attractions = {}
        self.app_guide = {}
        self.tips = {}
        self.hidden_mickeys = {}
        self.restaurants = {}
        
        # 待ち時間サービス
        if WAIT_TIME_AVAILABLE:
            self.wait_time_service = WaitTimeService()
        else:
            self.wait_time_service = None
        
        self._load_data()
    
    def _load_data(self):
        """データファイルを読み込む"""
        try:
            with open(self.data_dir / "parks.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.parks = {p["id"]: p for p in data.get("parks", [])}
        except FileNotFoundError:
            print("Warning: parks.json not found")
        
        # attractions_full.jsonを優先して読み込む
        try:
            with open(self.data_dir / "attractions_full.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.attractions = {a["id"]: a for a in data.get("attractions", [])}
        except FileNotFoundError:
            try:
                with open(self.data_dir / "attractions.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.attractions = {a["id"]: a for a in data.get("attractions", [])}
            except FileNotFoundError:
                print("Warning: attractions.json not found")
        
        try:
            with open(self.data_dir / "app_guide.json", "r", encoding="utf-8") as f:
                self.app_guide = json.load(f)
        except FileNotFoundError:
            print("Warning: app_guide.json not found")
        
        try:
            with open(self.data_dir / "tips.json", "r", encoding="utf-8") as f:
                self.tips = json.load(f)
        except FileNotFoundError:
            print("Warning: tips.json not found")
        
        try:
            with open(self.data_dir / "hidden_mickeys.json", "r", encoding="utf-8") as f:
                self.hidden_mickeys = json.load(f)
        except FileNotFoundError:
            print("Warning: hidden_mickeys.json not found")
        
        # レストラン情報を読み込む
        try:
            with open(self.data_dir / "restaurants.json", "r", encoding="utf-8") as f:
                self.restaurants = json.load(f)
        except FileNotFoundError:
            self.restaurants = {}
            print("Warning: restaurants.json not found")
        
        # 公式情報を読み込む
        try:
            with open(self.data_dir / "official_info.json", "r", encoding="utf-8") as f:
                self.official_info = json.load(f)
        except FileNotFoundError:
            self.official_info = {}
            print("Warning: official_info.json not found")
        
        # 2025年版初心者ガイドを読み込む
        try:
            with open(self.data_dir / "beginner_guide_2025.json", "r", encoding="utf-8") as f:
                self.beginner_guide_2025 = json.load(f)
        except FileNotFoundError:
            self.beginner_guide_2025 = {}
            print("Warning: beginner_guide_2025.json not found")
        
        # 2025年イベント情報を読み込む
        try:
            with open(self.data_dir / "events_2025.json", "r", encoding="utf-8") as f:
                self.events_2025 = json.load(f)
        except FileNotFoundError:
            self.events_2025 = {}
            print("Warning: events_2025.json not found")
        
        # 施設マップを読み込む
        try:
            with open(self.data_dir / "facilities_map.json", "r", encoding="utf-8") as f:
                self.facilities_map = json.load(f)
        except FileNotFoundError:
            self.facilities_map = {}
            print("Warning: facilities_map.json not found")
    
    def search_attraction(self, query: str) -> list:
        """アトラクションを検索"""
        query_lower = query.lower()
        results = []
        
        for attr_id, attr in self.attractions.items():
            score = 0
            # 名前でマッチ
            if query_lower in attr["name"].lower():
                score += 10
            if query_lower in attr.get("name_en", "").lower():
                score += 8
            # エリアでマッチ
            if query_lower in attr.get("area", "").lower():
                score += 5
            # タイプでマッチ
            if query_lower in attr.get("type", "").lower():
                score += 3
            
            if score > 0:
                results.append((score, attr))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]
    
    def get_attraction_by_name(self, name: str) -> Optional[dict]:
        """アトラクション名で検索"""
        name_lower = name.lower()
        for attr in self.attractions.values():
            if name_lower in attr["name"].lower() or name_lower in attr.get("name_en", "").lower():
                return attr
        return None
    
    def get_hidden_mickeys_by_area(self, area: str, park: str = None) -> list:
        """エリア別の隠れミッキーを取得"""
        results = []
        locations = self.hidden_mickeys.get("hidden_mickeys", {}).get("locations", {})
        
        for park_id, areas in locations.items():
            if park and park_id != park:
                continue
            for area_data in areas:
                if area.lower() in area_data.get("area", "").lower():
                    results.extend(area_data.get("spots", []))
        
        return results
    
    def get_app_feature_guide(self, feature: str) -> Optional[dict]:
        """アプリ機能のガイドを取得"""
        features = self.app_guide.get("app_guide", {}).get("features", [])
        feature_lower = feature.lower()
        
        for f in features:
            if feature_lower in f.get("name", "").lower() or feature_lower in f.get("id", "").lower():
                return f
        return None
    
    def search_restaurant(self, query: str) -> list:
        """レストランを検索"""
        query_lower = query.lower()
        results = []
        
        restaurants = self.restaurants.get("restaurants", [])
        for rest in restaurants:
            score = 0
            # 名前でマッチ
            if query_lower in rest["name"].lower():
                score += 10
            if query_lower in rest.get("name_en", "").lower():
                score += 8
            # 料理ジャンルでマッチ
            if query_lower in rest.get("cuisine", "").lower():
                score += 5
            # エリアでマッチ
            if query_lower in rest.get("area", "").lower():
                score += 3
            # タイプでマッチ
            if query_lower in rest.get("type", "").lower():
                score += 2
            
            if score > 0:
                results.append((score, rest))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]
    
    def get_restaurants_by_park(self, park: str) -> list:
        """パーク別のレストランを取得"""
        restaurants = self.restaurants.get("restaurants", [])
        return [r for r in restaurants if r.get("park") == park]
    
    def get_restaurants_by_type(self, cuisine_type: str) -> list:
        """料理ジャンル別のレストランを取得"""
        cuisine_lower = cuisine_type.lower()
        restaurants = self.restaurants.get("restaurants", [])
        return [r for r in restaurants if cuisine_lower in r.get("cuisine", "").lower()]


class DisneyChatbot:
    """ディズニーチャットボット"""
    
    def __init__(self, knowledge_base: DisneyKnowledgeBase = None):
        self.kb = knowledge_base or DisneyKnowledgeBase()
        self.intent_patterns = self._build_intent_patterns()
    
    def _get_current_season(self) -> str:
        """現在の季節を取得"""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:  # 12, 1, 2
            return "winter"
    
    def _get_season_name_jp(self, season: str) -> str:
        """季節名を日本語で取得"""
        return {"spring": "春", "summer": "夏", "autumn": "秋", "winter": "冬"}.get(season, "")
    
    def _build_intent_patterns(self) -> dict:
        """意図パターンを構築"""
        return {
            "hidden_mickey": [
                r"隠れミッキー",
                r"かくれミッキー",
                r"ミッキー.*探",
                r"ミッキー.*教えて",
            ],
            "app_guide": [
                r"スタンバイパス",
                r"プレミアアクセス",
                r"DPA",
                r"エントリー受付",
                r"モバイルオーダー",
                r"プライオリティ.*シーティング",
                r"(?:レストラン|食事).*予約",
                r"アプリ.*(?:使い方|方法|やり方)",
                r"(?:スマホ|携帯).*(?:アプリ|予約)",
            ],
            "tips": [
                r"(?:初心者|初めて|デビュー)",
                r"(?:持ち物|準備|用意|何を持っていく)",
                r"(?:回り方|効率|コース)",
                r"(?:混雑|空いてる|すいてる)",
                r"(?:服装|何を着|着ていく)",
                r"アドバイス",
            ],
            "family": [
                r"(?:子連れ|子供|こども|キッズ)",
                r"(?:赤ちゃん|ベビー|幼児)",
                r"(?:身長制限|何歳から)",
                r"(?:ベビーカー|おむつ|授乳)",
                r"(?:シニア|高齢|おじいちゃん|おばあちゃん|祖父母)",
            ],
            "trivia": [
                r"(?:トリビア|うんちく|豆知識|裏話)",
                r"(?:なぜ|どうして|理由)",
            ],
            "greeting": [
                r"^(?:こんにちは|こんばんは|おはよう|ハロー|やあ|hi|hello)",
                r"^(?:ありがとう|サンキュー|thanks)",
            ],
            "attraction_info": [
                r"(.+?)(?:について|の情報|って何|とは)",
                r"(.+?)(?:の待ち時間|混んでる|空いてる)",
                r"(.+?)(?:の身長制限|何歳から|子供)",
                r"(.+?)教えて",
            ],
            "restaurant": [
                r"(?:レストラン|食事|ご飯|ランチ|ディナー|食べ)",
                r"(?:和食|イタリアン|中華|カレー|ハンバーガー)",
                r"(?:おすすめ.*(?:店|レストラン))",
                r"(?:予約.*(?:必要|いる|方法))",
            ],
            "wait_time": [
                r"(?:待ち時間|まちじかん|混み|混雑|空いて)",
                r"(?:今|現在).*(?:何分|どのくらい)",
                r"(?:リアルタイム)",
            ],
            "event": [
                r"(?:イベント|クリスマス|ハロウィン|正月|お正月)",
                r"(?:ショー|パレード|花火)",
                r"(?:25周年|周年)",
            ],
            "ticket": [
                r"(?:チケット|パスポート|入場券)",
                r"(?:料金|値段|いくら|価格)",
                r"(?:年パス|年間パスポート)",
            ],
            "facilities": [
                r"(?:トイレ|お手洗い|WC|化粧室)",
                r"(?:ベビーセンター|授乳|おむつ|オムツ)",
                r"(?:救護室|具合が悪い|体調)",
                r"(?:ロッカー|荷物|預ける)",
                r"(?:喫煙|タバコ|たばこ)",
                r"(?:ATM|お金|現金)",
                r"(?:迷子|はぐれた)",
                r"(?:どこ|場所|近く)",
            ],
            "plan": [
                r"(?:プラン|計画|スケジュール|回り方|まわり方)",
                r"(?:おすすめ|オススメ).*(?:回り方|まわり方|順番)",
                r"(?:効率|効率的|効率よく)",
                r"(?:初心者|はじめて|初めて).*(?:回|周|プラン)",
                r"(?:子連れ|こども|子供|ファミリー).*(?:回|周|プラン)",
                r"(?:絶叫|スリル).*(?:回|周|プラン)",
                r"(?:ファンタジースプリングス|新エリア).*(?:回|周|プラン|攻略)",
                r"(?:1日|一日).*(?:プラン|計画)",
                r"(?:モデルコース|モデル.*コース)",
            ],
            "closure": [
                r"(?:休止|休業|クローズ|運休|休園)",
                r"(?:やってない|やっていない|乗れない)",
                r"(?:工事|メンテナンス|点検)",
            ],
        }
    
    def _detect_intent(self, message: str) -> tuple:
        """メッセージの意図を検出"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return intent, 0.8
        
        # デフォルト
        return "general", 0.5
    
    def _extract_attraction_name(self, message: str) -> Optional[str]:
        """メッセージからアトラクション名を抽出"""
        # 既知のアトラクション名リスト（正規化形式、表示名）
        known_attractions = [
            ("美女と野獣", "美女と野獣"),
            ("ビッグサンダー", "ビッグサンダー"),
            ("スペースマウンテン", "スペースマウンテン"),
            ("スプラッシュ", "スプラッシュ"),
            ("タワーオブテラー", "タワー・オブ・テラー"),
            ("タワーオブテラー", "タワーオブテラー"),
            ("トイストーリーマニア", "トイ・ストーリー・マニア"),
            ("トイストーリー", "トイ・ストーリー"),
            ("トイマニ", "トイ・ストーリー・マニア"),
            ("ソアリン", "ソアリン"),
            ("センターオブジアース", "センター・オブ・ジ・アース"),
            ("カリブの海賊", "カリブの海賊"),
            ("ホーンテッドマンション", "ホーンテッドマンション"),
            ("ホーンテッド", "ホーンテッドマンション"),
            ("プーさん", "プーさん"),
            ("インディジョーンズ", "インディ・ジョーンズ"),
            ("ニモ", "ニモ"),
            ("バズ", "バズ"),
        ]
        
        # メッセージを正規化
        message_normalized = message.lower().replace(" ", "").replace("　", "").replace("・", "").replace("-", "")
        
        for pattern, display_name in known_attractions:
            pattern_normalized = pattern.lower().replace("・", "").replace("-", "")
            if pattern_normalized in message_normalized:
                return display_name
        
        return None
    
    def chat(self, message: str) -> ChatResponse:
        """チャットに応答"""
        intent, confidence = self._detect_intent(message)
        
        # 挨拶
        if intent == "greeting":
            return ChatResponse(
                message="こんにちは！🏰 ディズニーについて何でも聞いてください！\n\n"
                        "例えば：\n"
                        "・「美女と野獣について教えて」\n"
                        "・「スタンバイパスって何？」\n"
                        "・「隠れミッキーを教えて」\n"
                        "・「初心者におすすめの回り方」",
                category="greeting",
                confidence=1.0
            )
        
        # アトラクション情報
        if intent == "attraction_info":
            attraction_name = self._extract_attraction_name(message)
            if attraction_name:
                attr = self.kb.get_attraction_by_name(attraction_name)
                if attr:
                    return self._format_attraction_response(attr)
            
            # 検索を試みる
            results = self.kb.search_attraction(message)
            if results:
                return self._format_attraction_response(results[0])
        
        # 隠れミッキー
        if intent == "hidden_mickey":
            return self._format_hidden_mickey_response(message)
        
        # アプリガイド
        if intent == "app_guide":
            return self._format_app_guide_response(message)
        
        # Tips
        if intent == "tips":
            return self._format_tips_response(message)
        
        # Family（子連れ・シニア）
        if intent == "family":
            return self._format_family_response(message)
        
        # レストラン
        if intent == "restaurant":
            return self._format_restaurant_response(message)
        
        # 待ち時間
        if intent == "wait_time":
            return self._format_wait_time_response(message)
        
        # イベント
        if intent == "event":
            return self._format_event_response(message)
        
        # チケット
        if intent == "ticket":
            return self._format_ticket_response(message)
        
        # 施設（トイレ、ベビーセンターなど）
        if intent == "facilities":
            return self._format_facilities_response(message)
        
        # プラン生成
        if intent == "plan":
            return self._format_plan_response(message)
        
        # 休止情報
        if intent == "closure":
            return self._format_closure_response(message)
        
        # トリビア
        if intent == "trivia":
            attraction_name = self._extract_attraction_name(message)
            if attraction_name:
                attr = self.kb.get_attraction_by_name(attraction_name)
                if attr and attr.get("trivia"):
                    return self._format_trivia_response(attr)
        
        # アトラクション名の検索を試みる
        attraction_name = self._extract_attraction_name(message)
        if attraction_name:
            attr = self.kb.get_attraction_by_name(attraction_name)
            if attr:
                return self._format_attraction_response(attr)
        
        # デフォルト応答
        return ChatResponse(
            message="すみません、その質問にはまだ対応していません。🙇\n\n"
                    "以下のような質問に答えられます：\n"
                    "・アトラクションの情報（「美女と野獣について」）\n"
                    "・隠れミッキーの場所\n"
                    "・アプリの使い方（スタンバイパス、予約など）\n"
                    "・初心者向けのアドバイス",
            category="unknown",
            confidence=0.3
        )
    
    def _format_attraction_response(self, attr: dict) -> ChatResponse:
        """アトラクション情報をフォーマット"""
        park_name = "ディズニーランド" if attr["park"] == "tdl" else "ディズニーシー"
        
        msg = f"🎢 **{attr['name']}**\n"
        msg += f"📍 {park_name}\n\n"
        msg += f"{attr.get('description', '')}\n\n"
        
        # 基本情報
        msg += "**基本情報**\n"
        msg += f"・所要時間: 約{attr.get('duration_minutes', '?')}分\n"
        
        if attr.get("height_restriction"):
            msg += f"・身長制限: {attr['height_restriction']}cm以上\n"
        else:
            msg += "・身長制限: なし\n"
        
        if attr.get("dpa_available"):
            msg += f"・プレミアアクセス: あり（{attr.get('dpa_price', '?')}円）\n"
        
        if attr.get("standby_pass"):
            msg += "・スタンバイパス: あり\n"
        
        # 待ち時間の傾向
        if attr.get("wait_time_trend"):
            trend = attr["wait_time_trend"]
            msg += "\n**待ち時間の目安**\n"
            if "weekday" in trend:
                msg += f"・平日: 朝{trend['weekday'].get('morning', '?')}分 / 昼{trend['weekday'].get('afternoon', '?')}分 / 夜{trend['weekday'].get('evening', '?')}分\n"
            if "weekend" in trend:
                msg += f"・土日: 朝{trend['weekend'].get('morning', '?')}分 / 昼{trend['weekend'].get('afternoon', '?')}分 / 夜{trend['weekend'].get('evening', '?')}分\n"
        
        # Tips
        if attr.get("tips"):
            msg += "\n**Tips**\n"
            for tip in attr["tips"][:3]:
                msg += f"・{tip}\n"
        
        return ChatResponse(
            message=msg,
            category="attraction_info",
            confidence=0.9,
            related_data=attr
        )
    
    def _format_hidden_mickey_response(self, message: str) -> ChatResponse:
        """隠れミッキー情報をフォーマット"""
        hm_data = self.kb.hidden_mickeys.get("hidden_mickeys", {})
        
        msg = "🐭 **隠れミッキー情報**\n\n"
        msg += f"{hm_data.get('description', '')}\n\n"
        
        # エリア名が含まれているか確認
        area_keywords = {
            "ワールドバザール": "ワールドバザール",
            "アドベンチャー": "アドベンチャーランド",
            "ウエスタン": "ウエスタンランド",
            "ファンタジー": "ファンタジーランド",
            "トゥモロー": "トゥモローランド",
            "トゥーン": "トゥーンタウン",
            "メディテレーニアン": "メディテレーニアンハーバー",
            "アメリカンウォーター": "アメリカンウォーターフロント",
            "ミステリアス": "ミステリアスアイランド",
            "マーメイド": "マーメイドラグーン",
            "アラビアン": "アラビアンコースト",
            "ロストリバー": "ロストリバーデルタ",
        }
        
        found_area = None
        for keyword, area_name in area_keywords.items():
            if keyword in message:
                found_area = area_name
                break
        
        if found_area:
            spots = self.kb.get_hidden_mickeys_by_area(found_area)
            if spots:
                msg += f"**{found_area}の隠れミッキー**\n"
                for spot in spots:
                    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(spot.get("difficulty", ""), "⚪")
                    msg += f"\n{difficulty_emoji} **{spot['name']}**\n"
                    msg += f"ヒント: {spot.get('hint', 'なし')}\n"
        else:
            msg += "**人気の隠れミッキースポット**\n\n"
            
            # ランドから3つ
            msg += "【ディズニーランド】\n"
            tdl_spots = []
            for area in hm_data.get("locations", {}).get("tdl", []):
                for spot in area.get("spots", [])[:1]:
                    tdl_spots.append((area["area"], spot))
            for area, spot in tdl_spots[:3]:
                msg += f"・{area}: {spot['name']}\n"
            
            # シーから3つ
            msg += "\n【ディズニーシー】\n"
            tds_spots = []
            for area in hm_data.get("locations", {}).get("tds", []):
                for spot in area.get("spots", [])[:1]:
                    tds_spots.append((area["area"], spot))
            for area, spot in tds_spots[:3]:
                msg += f"・{area}: {spot['name']}\n"
            
            msg += "\n特定のエリアの隠れミッキーを知りたい場合は「ファンタジーランドの隠れミッキー」のように聞いてください！"
        
        return ChatResponse(
            message=msg,
            category="hidden_mickey",
            confidence=0.85
        )
    
    def _format_app_guide_response(self, message: str) -> ChatResponse:
        """アプリガイドをフォーマット"""
        message_lower = message.lower()
        
        # 特定の機能を探す
        if "スタンバイパス" in message:
            feature = self.kb.get_app_feature_guide("スタンバイパス")
            if feature:
                return self._format_feature_response(feature)
        
        if "プレミアアクセス" in message or "DPA" in message or "dpa" in message_lower:
            feature = self.kb.get_app_feature_guide("プレミアアクセス")
            if feature:
                return self._format_feature_response(feature)
        
        if "エントリー" in message or "抽選" in message:
            feature = self.kb.get_app_feature_guide("エントリー")
            if feature:
                return self._format_feature_response(feature)
        
        if "レストラン" in message or "予約" in message or "プライオリティ" in message:
            feature = self.kb.get_app_feature_guide("プライオリティ")
            if feature:
                return self._format_feature_response(feature)
        
        if "モバイルオーダー" in message:
            feature = self.kb.get_app_feature_guide("モバイルオーダー")
            if feature:
                return self._format_feature_response(feature)
        
        # 全般的なアプリ案内
        app_info = self.kb.app_guide.get("app_guide", {})
        msg = "📱 **ディズニーリゾート公式アプリ**\n\n"
        msg += "パークを効率よく楽しむための必須アプリです！\n\n"
        msg += "**主な機能**\n"
        
        for feature in app_info.get("features", []):
            msg += f"・**{feature['name']}**: {feature['description'][:50]}...\n"
        
        msg += "\n詳しく知りたい機能を教えてください！\n"
        msg += "例：「スタンバイパスって何？」「レストラン予約の方法」"
        
        return ChatResponse(
            message=msg,
            category="app_guide",
            confidence=0.8
        )
    
    def _format_feature_response(self, feature: dict) -> ChatResponse:
        """機能詳細をフォーマット"""
        msg = f"📱 **{feature['name']}**\n\n"
        msg += f"{feature['description']}\n\n"
        
        # 使い方
        if feature.get("how_to_use"):
            msg += "**使い方**\n"
            for i, step in enumerate(feature["how_to_use"], 1):
                msg += f"{i}. {step}\n"
        
        # 料金
        if feature.get("prices"):
            msg += "\n**料金**\n"
            for k, v in feature["prices"].items():
                msg += f"・{k}: {v}\n"
        
        # Tips
        if feature.get("tips"):
            msg += "\n**💡 Tips**\n"
            for tip in feature["tips"][:4]:
                msg += f"・{tip}\n"
        
        return ChatResponse(
            message=msg,
            category="app_guide",
            confidence=0.9,
            related_data=feature
        )
    
    def _format_tips_response(self, message: str) -> ChatResponse:
        """Tipsをフォーマット"""
        tips_data = self.kb.tips.get("tips", {})
        message_lower = message.lower()
        
        # 季節を取得
        current_season = self._get_current_season()
        season_name = self._get_season_name_jp(current_season)
        
        # 2025年版ガイドから季節情報を取得
        beginner_2025 = getattr(self.kb, 'beginner_guide_2025', {}).get("beginner_guide_2025", {})
        seasonal_guide = beginner_2025.get("seasonal_guide", {}).get(current_season, {})
        
        # 初心者ガイド
        if "初心者" in message or "初めて" in message or "デビュー" in message:
            msg = f"🎪 **初心者ガイド（{season_name}版）**\n\n"
            
            # 季節の概要
            if seasonal_guide:
                msg += f"**🗓️ 現在の季節: {season_name}**\n"
                msg += f"・天気: {seasonal_guide.get('weather_summary', '')}\n"
                msg += f"・気温: {seasonal_guide.get('temperature_range', '')}\n\n"
            
            # 絶対必要な事前準備
            essential_prep = beginner_2025.get("essential_preparation", {}).get("must_do", [])
            if essential_prep:
                msg += "**📝 絶対必要な事前準備**\n"
                for prep in essential_prep[:3]:
                    msg += f"・**{prep['item']}**: {prep['detail'][:50]}...\n"
                msg += "\n"
            
            # 季節イベント
            if seasonal_guide.get("events_2025"):
                msg += f"**🎉 {season_name}のイベント**\n"
                for event in seasonal_guide["events_2025"][:3]:
                    msg += f"・{event}\n"
                msg += "\n"
            
            # よくある失敗（2025版があれば使用）
            common_mistakes = beginner_2025.get("common_mistakes", {}).get("mistakes", [])
            if common_mistakes:
                msg += "**⚠️ よくある失敗と対策**\n"
                for mistake in common_mistakes[:3]:
                    msg += f"・{mistake['mistake']} → {mistake['solution']}\n"
            else:
                guide = tips_data.get("beginner_guide", {})
                msg += "**⚠️ よくある失敗と対策**\n"
                for mistake in guide.get("common_mistakes", [])[:3]:
                    msg += f"・{mistake['mistake']} → {mistake['solution']}\n"
            
            msg += f"\n「{season_name}の持ち物」「{season_name}の服装」も聞いてください！"
            
            return ChatResponse(
                message=msg,
                category="tips",
                confidence=0.9
            )
        
        # 持ち物
        if "持ち物" in message or "準備" in message or "何を持っていく" in message or "用意" in message:
            msg = f"🎒 **{season_name}の持ち物リスト**\n\n"
            
            if seasonal_guide:
                packing = seasonal_guide.get("packing_list", {})
                
                # 必須アイテム
                if packing.get("essential"):
                    msg += "**✅ 必須アイテム**\n"
                    for item in packing["essential"]:
                        msg += f"・{item}\n"
                    msg += "\n"
                
                # あると便利
                if packing.get("optional"):
                    msg += "**💡 あると便利**\n"
                    for item in packing["optional"]:
                        msg += f"・{item}\n"
                    msg += "\n"
                
                # 季節固有の注意点
                if seasonal_guide.get("special_tips"):
                    msg += f"**⚠️ {season_name}の注意点**\n"
                    for tip in seasonal_guide["special_tips"][:3]:
                        msg += f"・{tip}\n"
            else:
                # フォールバック
                guide = tips_data.get("beginner_guide", {})
                for section in guide.get("before_visit", []):
                    if "持ち物" in section["category"]:
                        for item in section["items"]:
                            msg += f"・{item}\n"
            
            return ChatResponse(
                message=msg,
                category="tips",
                confidence=0.9
            )
        
        # 服装
        if "服装" in message or "何を着" in message or "着ていく" in message:
            msg = f"👕 **{season_name}の服装アドバイス**\n\n"
            
            if seasonal_guide:
                msg += f"**🌡️ 気温: {seasonal_guide.get('temperature_range', '')}**\n\n"
                
                clothing = seasonal_guide.get("clothing", {})
                
                # おすすめ
                if clothing.get("recommended"):
                    msg += "**✅ おすすめの服装**\n"
                    for item in clothing["recommended"]:
                        msg += f"・{item}\n"
                    msg += "\n"
                
                # 避けた方がいい
                if clothing.get("avoid"):
                    msg += "**❌ 避けた方がいい服装**\n"
                    for item in clothing["avoid"]:
                        msg += f"・{item}\n"
                    msg += "\n"
                
                # 季節固有Tips
                if seasonal_guide.get("special_tips"):
                    msg += f"**💡 {season_name}のTips**\n"
                    for tip in seasonal_guide["special_tips"][:3]:
                        msg += f"・{tip}\n"
            else:
                msg += "季節に合った服装で、歩きやすい靴がおすすめです！"
            
            return ChatResponse(
                message=msg,
                category="tips",
                confidence=0.9
            )
        
        # 回り方・コース
        if "回り方" in message or "コース" in message or "効率" in message:
            courses = tips_data.get("model_courses", [])
            
            # パーク指定があるか確認
            target_park = None
            if "ランド" in message:
                target_park = "tdl"
            elif "シー" in message:
                target_park = "tds"
            
            msg = "🗺️ **おすすめコース**\n\n"
            
            for course in courses:
                if target_park and course["park"] != target_park:
                    continue
                msg += f"**{course['name']}**\n"
                msg += f"対象: {course['target']}\n\n"
                
                for item in course["schedule"][:8]:
                    msg += f"・{item['time']} {item['action']}\n"
                msg += "...\n\n"
            
            return ChatResponse(
                message=msg,
                category="tips",
                confidence=0.85
            )
        
        # 混雑
        if "混雑" in message or "空いて" in message or "すいて" in message:
            crowd = tips_data.get("crowd_calendar", {})
            msg = "📊 **混雑カレンダー**\n\n"
            
            msg += "**🔴 特に混む日**\n"
            for item in crowd.get("most_crowded", []):
                msg += f"・{item}\n"
            
            msg += "\n**🟢 比較的空いている日**\n"
            for item in crowd.get("relatively_empty", []):
                msg += f"・{item}\n"
            
            msg += "\n**💡 Tips**\n"
            for tip in crowd.get("tips", []):
                msg += f"・{tip}\n"
            
            return ChatResponse(
                message=msg,
                category="tips",
                confidence=0.9
            )
        
        # デフォルト
        return ChatResponse(
            message="🎪 **ディズニーTips**\n\n"
                    "以下について詳しくお答えできます：\n"
                    "・初心者ガイド（「初心者向けのアドバイス」）\n"
                    "・持ち物リスト（「持ち物を教えて」）\n"
                    "・おすすめコース（「ランドの回り方」）\n"
                    "・混雑情報（「空いてる日はいつ？」）",
            category="tips",
            confidence=0.7
        )
    
    def _format_family_response(self, message: str) -> ChatResponse:
        """子連れ・シニア向け情報をフォーマット"""
        beginner_2025 = getattr(self.kb, 'beginner_guide_2025', {}).get("beginner_guide_2025", {})
        special_needs = beginner_2025.get("with_special_needs", {})
        
        # 子連れ情報
        if any(kw in message for kw in ["子連れ", "子供", "こども", "キッズ", "赤ちゃん", "ベビー", "幼児", "ベビーカー", "おむつ", "授乳"]):
            kids_info = special_needs.get("with_kids", {})
            
            msg = "👶 **子連れディズニーガイド**\n\n"
            
            # 年齢別おすすめ
            if any(kw in message for kw in ["赤ちゃん", "0歳", "1歳", "2歳"]):
                age_info = kids_info.get("age_recommendations", {}).get("0-2歳", {})
                if age_info:
                    msg += "**👶 0-2歳のお子様向け**\n"
                    msg += "おすすめアトラクション:\n"
                    for attr in age_info.get("recommended_attractions", []):
                        msg += f"・{attr}\n"
                    msg += "\n**💡 Tips**\n"
                    for tip in age_info.get("tips", []):
                        msg += f"・{tip}\n"
            
            elif any(kw in message for kw in ["3歳", "4歳", "5歳", "幼児"]):
                age_info = kids_info.get("age_recommendations", {}).get("3-5歳", {})
                if age_info:
                    msg += "**🧒 3-5歳のお子様向け**\n"
                    msg += "おすすめアトラクション:\n"
                    for attr in age_info.get("recommended_attractions", []):
                        msg += f"・{attr}\n"
                    msg += "\n**💡 Tips**\n"
                    for tip in age_info.get("tips", []):
                        msg += f"・{tip}\n"
            
            # 身長制限
            elif "身長" in message:
                height_info = kids_info.get("height_restrictions_summary", {})
                if height_info:
                    msg += "**📏 身長制限まとめ**\n\n"
                    for height, attractions in height_info.items():
                        msg += f"**{height}以上**\n"
                        for attr in attractions:
                            msg += f"・{attr}\n"
                        msg += "\n"
            
            # 施設情報
            elif any(kw in message for kw in ["ベビーカー", "おむつ", "授乳", "ベビーセンター"]):
                facilities = kids_info.get("facilities", [])
                msg += "**🍼 ベビー施設情報**\n\n"
                for facility in facilities:
                    msg += f"**{facility['name']}**\n"
                    if facility.get("location_tdl"):
                        msg += f"・ランド: {facility['location_tdl']}\n"
                    if facility.get("location_tds"):
                        msg += f"・シー: {facility['location_tds']}\n"
                    if facility.get("services"):
                        msg += f"・サービス: {', '.join(facility['services'])}\n"
                    if facility.get("price"):
                        msg += f"・料金: {facility['price']}\n"
                    msg += "\n"
            
            else:
                # 一般的な子連れ情報
                msg += "**📍 年齢別ガイド**\n"
                msg += "・0-2歳 → 「赤ちゃん連れ」と聞いてください\n"
                msg += "・3-5歳 → 「幼児連れ」と聞いてください\n"
                msg += "・小学生 → ほぼ全てのアトラクションOK\n\n"
                
                msg += "**📏 身長制限について**\n"
                msg += "・「身長制限を教えて」と聞いてください\n\n"
                
                msg += "**🍼 施設について**\n"
                msg += "・「ベビーセンター」「ベビーカー」と聞いてください\n"
            
            return ChatResponse(
                message=msg,
                category="family",
                confidence=0.9
            )
        
        # シニア情報
        if any(kw in message for kw in ["シニア", "高齢", "おじいちゃん", "おばあちゃん", "祖父母", "年配"]):
            senior_info = special_needs.get("with_seniors", {})
            
            msg = "👴👵 **シニアと一緒に楽しむガイド**\n\n"
            
            if senior_info.get("tips"):
                msg += "**💡 Tips**\n"
                for tip in senior_info["tips"]:
                    msg += f"・{tip}\n"
                msg += "\n"
            
            if senior_info.get("recommended"):
                msg += "**✅ おすすめアトラクション**\n"
                for attr in senior_info["recommended"]:
                    msg += f"・{attr}\n"
            
            return ChatResponse(
                message=msg,
                category="family",
                confidence=0.9
            )
        
        # デフォルト
        return ChatResponse(
            message="👨‍👩‍👧‍👦 **ファミリー向けガイド**\n\n"
                    "以下についてお答えできます：\n"
                    "・子連れディズニー（「子供と一緒に」）\n"
                    "・身長制限（「身長制限を教えて」）\n"
                    "・ベビー施設（「ベビーセンター」）\n"
                    "・シニアと一緒に（「おじいちゃんと一緒」）",
            category="family",
            confidence=0.7
        )
    
    def _format_trivia_response(self, attr: dict) -> ChatResponse:
        """トリビアをフォーマット"""
        msg = f"💡 **{attr['name']}のトリビア**\n\n"
        
        for trivia in attr.get("trivia", []):
            msg += f"・{trivia}\n"
        
        if attr.get("backstory"):
            msg += f"\n**バックストーリー**\n{attr['backstory']}"
        
        return ChatResponse(
            message=msg,
            category="trivia",
            confidence=0.9,
            related_data=attr
        )
    
    def _format_restaurant_response(self, message: str) -> ChatResponse:
        """レストラン情報をフォーマット"""
        message_lower = message.lower()
        
        # 料理ジャンルで検索
        cuisine_keywords = {
            "和食": ["和食", "日本食", "日本料理"],
            "イタリアン": ["イタリアン", "パスタ", "ピザ", "ピッツァ"],
            "中華": ["中華", "チャイニーズ", "麻婆"],
            "カレー": ["カレー"],
            "フレンチ": ["フレンチ", "フランス料理"],
            "ハンバーガー": ["ハンバーガー", "バーガー"],
            "メキシカン": ["メキシカン", "タコス", "メキシコ"],
        }
        
        found_cuisine = None
        for cuisine, keywords in cuisine_keywords.items():
            for kw in keywords:
                if kw in message_lower:
                    found_cuisine = cuisine
                    break
            if found_cuisine:
                break
        
        if found_cuisine:
            restaurants = self.kb.get_restaurants_by_type(found_cuisine)
            if restaurants:
                msg = f"🍽️ **{found_cuisine}のおすすめレストラン**\n\n"
                for rest in restaurants[:5]:
                    park_name = "ランド" if rest["park"] == "tdl" else "シー"
                    msg += f"**{rest['name']}** [{park_name}]\n"
                    msg += f"・価格帯: {rest.get('price_range', '?')}\n"
                    msg += f"・特徴: {rest.get('description', '')[:50]}...\n"
                    if rest.get("priority_seating"):
                        msg += f"・予約: プライオリティ・シーティング対応\n"
                    msg += "\n"
                
                return ChatResponse(
                    message=msg,
                    category="restaurant",
                    confidence=0.9
                )
        
        # パークで絞り込み
        target_park = None
        if "ランド" in message and "シー" not in message:
            target_park = "tdl"
        elif "シー" in message and "ランド" not in message:
            target_park = "tds"
        
        if target_park:
            restaurants = self.kb.get_restaurants_by_park(target_park)
            park_name = "ディズニーランド" if target_park == "tdl" else "ディズニーシー"
            msg = f"🍽️ **{park_name}のレストラン**\n\n"
            
            # タイプ別に分類
            table_service = [r for r in restaurants if "テーブル" in r.get("type", "")]
            counter_service = [r for r in restaurants if "カウンター" in r.get("type", "") or "バフェテリア" in r.get("type", "")]
            
            if table_service:
                msg += "**予約推奨のレストラン**\n"
                for rest in table_service[:3]:
                    msg += f"・{rest['name']} ({rest.get('cuisine', '')})\n"
                msg += "\n"
            
            if counter_service:
                msg += "**予約不要のレストラン**\n"
                for rest in counter_service[:3]:
                    msg += f"・{rest['name']} ({rest.get('cuisine', '')})\n"
            
            return ChatResponse(
                message=msg,
                category="restaurant",
                confidence=0.85
            )
        
        # 予約関連
        if "予約" in message:
            tips = self.kb.restaurants.get("tips", {}).get("reservation", {})
            msg = "🍽️ **レストラン予約のコツ**\n\n"
            for tip in tips.get("tips", []):
                msg += f"・{tip}\n"
            
            msg += "\n**予約が必要な人気レストラン**\n"
            all_restaurants = self.kb.restaurants.get("restaurants", [])
            priority_restaurants = [r for r in all_restaurants if r.get("priority_seating")]
            for rest in priority_restaurants[:5]:
                park_name = "ランド" if rest["park"] == "tdl" else "シー"
                msg += f"・{rest['name']} [{park_name}]\n"
            
            return ChatResponse(
                message=msg,
                category="restaurant",
                confidence=0.9
            )
        
        # 一般的なレストラン情報
        msg = "🍽️ **レストランガイド**\n\n"
        msg += "以下の条件でレストランをお探しできます：\n\n"
        msg += "**料理ジャンル**\n"
        msg += "・和食、イタリアン、中華、カレー、フレンチなど\n\n"
        msg += "**パーク別**\n"
        msg += "・「ランドのレストラン」「シーのレストラン」\n\n"
        msg += "**予約情報**\n"
        msg += "・「レストラン予約の方法」\n\n"
        msg += "例：「シーで和食が食べたい」「イタリアンのおすすめ」"
        
        return ChatResponse(
            message=msg,
            category="restaurant",
            confidence=0.7
        )
    
    def _format_event_response(self, message: str) -> ChatResponse:
        """イベント情報をフォーマット"""
        official_info = self.kb.official_info if hasattr(self.kb, 'official_info') else {}
        events = official_info.get("events", {}).get("current_and_upcoming", [])
        
        msg = "🎉 **イベント情報**\n\n"
        
        if events:
            msg += "**開催中・開催予定のイベント**\n\n"
            for event in events:
                park_name = "両パーク" if event.get("park") == "both" else ("ランド" if event.get("park") == "tdl" else "シー")
                msg += f"🎪 **{event['name']}**\n"
                msg += f"・期間: {event.get('start_date', '?')} ～ {event.get('end_date', '?')}\n"
                msg += f"・場所: {park_name}\n"
                if event.get('description'):
                    msg += f"・{event['description']}\n"
                msg += "\n"
        else:
            msg += "現在イベント情報を取得できません。\n"
            msg += "最新情報は公式サイトをご確認ください。"
        
        msg += "_※最新情報は公式サイトでご確認ください_"
        
        return ChatResponse(
            message=msg,
            category="event",
            confidence=0.9
        )
    
    def _format_closure_response(self, message: str) -> ChatResponse:
        """休止情報のレスポンス"""
        from closure_service import ClosureService
        
        closure_service = ClosureService()
        
        # パークを特定
        park = None
        if "ランド" in message and "シー" not in message:
            park = "tdl"
        elif "シー" in message and "ランド" not in message:
            park = "tds"
        
        return ChatResponse(
            message=closure_service.format_closures(park),
            category="closure",
            confidence=0.95
        )
    
    def _format_plan_response(self, message: str) -> ChatResponse:
        """プラン生成のレスポンス"""
        from plan_generator import PlanGeneratorService
        
        plan_service = PlanGeneratorService()
        
        # パークを特定
        park = "tds"  # デフォルトはシー
        if "ランド" in message and "シー" not in message:
            park = "tdl"
        elif "シー" in message or "ファンタジースプリングス" in message:
            park = "tds"
        
        # ユーザータイプを特定
        user_type = "beginner"  # デフォルト
        
        if any(kw in message for kw in ["子連れ", "こども", "子供", "ファミリー", "家族"]):
            user_type = "family_with_kids"
        elif any(kw in message for kw in ["絶叫", "スリル", "ジェットコースター"]):
            user_type = "thrill_seeker"
        elif any(kw in message for kw in ["ファンタジースプリングス", "新エリア", "アナ雪", "ラプンツェル"]):
            user_type = "fantasy_springs_focus"
        elif any(kw in message for kw in ["効率", "たくさん", "いっぱい"]):
            user_type = "efficient"
        elif any(kw in message for kw in ["ゆっくり", "のんびり", "ゆったり"]):
            user_type = "relaxed"
        elif any(kw in message for kw in ["カップル", "デート", "二人"]):
            user_type = "couple"
        
        try:
            plan = plan_service.generate_plan(park, user_type)
            return ChatResponse(
                message=plan_service.format_plan(plan),
                category="plan",
                confidence=0.95
            )
        except Exception as e:
            # プラン生成に失敗した場合は選択肢を提示
            msg = "📋 **プラン作成**\n\n"
            msg += "どのようなプランがお好みですか？\n\n"
            
            user_types = plan_service.get_available_user_types()
            for ut in user_types:
                msg += f"・**{ut['name']}**: {ut['description']}\n"
            
            msg += "\n例: 「子連れでランドのプランを教えて」\n"
            msg += "例: 「ファンタジースプリングス中心のプラン」"
            
            return ChatResponse(message=msg, category="plan", confidence=0.7)
    
    def _format_facilities_response(self, message: str) -> ChatResponse:
        """施設情報をフォーマット（トイレ、ベビーセンターなど）"""
        facilities = getattr(self.kb, 'facilities_map', {}).get("facilities", {})
        
        # パークを特定
        target_park = None
        park_name = ""
        if "ランド" in message and "シー" not in message:
            target_park = "tokyo_disney_land"
            park_name = "ディズニーランド"
        elif "シー" in message and "ランド" not in message:
            target_park = "tokyo_disney_sea"
            park_name = "ディズニーシー"
        
        # エリアを特定
        area_keywords = {
            "ワールドバザール": "world_bazaar",
            "アドベンチャー": "adventureland",
            "ウエスタン": "westernland",
            "クリッター": "critter_country",
            "ファンタジー": "fantasyland",
            "美女と野獣": "fantasyland",
            "トゥーン": "toontown",
            "トゥモロー": "tomorrowland",
            "メディテレーニアン": "mediterranean_harbor",
            "アメリカン": "american_waterfront",
            "ケープコッド": "american_waterfront",
            "ポートディスカバリー": "port_discovery",
            "ロストリバー": "lost_river_delta",
            "ミステリアス": "mysterious_island",
            "マーメイド": "mermaid_lagoon",
            "アラビアン": "arabian_coast",
            "ファンタジースプリングス": "fantasy_springs",
        }
        
        target_area = None
        area_name = ""
        for keyword, area_id in area_keywords.items():
            if keyword in message:
                target_area = area_id
                area_name = keyword
                break
        
        # トイレ
        if any(kw in message for kw in ["トイレ", "お手洗い", "WC", "化粧室"]):
            msg = "🚻 **トイレの場所**\n\n"
            
            # エリア指定がある場合
            if target_area:
                msg += f"**{area_name}のトイレ**\n"
                parks_to_check = [target_park] if target_park else ["tokyo_disney_land", "tokyo_disney_sea"]
                
                for park in parks_to_check:
                    park_data = facilities.get(park, {})
                    restrooms = park_data.get("restrooms", [])
                    
                    for wc in restrooms:
                        if wc.get("area") == target_area:
                            emoji = "🟢" if wc.get("crowded_level") == "空いている" else "🟡" if wc.get("crowded_level") == "普通" else "🔴"
                            msg += f"\n{emoji} **{wc['name']}**\n"
                            msg += f"📍 {wc['landmark']}\n"
                            if wc.get("features"):
                                msg += f"・設備: {', '.join(wc['features'])}\n"
                            if wc.get("tip"):
                                msg += f"💡 {wc['tip']}\n"
                
                return ChatResponse(message=msg, category="facilities", confidence=0.95)
            
            # パーク指定がある場合
            elif target_park:
                park_data = facilities.get(target_park, {})
                restrooms = park_data.get("restrooms", [])
                
                msg += f"**{park_name}のトイレ**\n"
                msg += "🟢=空いている 🟡=普通 🔴=混みやすい\n\n"
                
                # 空いているトイレを優先表示
                empty_wcs = [wc for wc in restrooms if wc.get("crowded_level") == "空いている"]
                if empty_wcs:
                    msg += "**💡 穴場トイレ（空いていることが多い）**\n"
                    for wc in empty_wcs[:3]:
                        msg += f"🟢 {wc['name']}\n"
                        msg += f"   📍 {wc['landmark']}\n"
                    msg += "\n"
                
                msg += "**📍 全トイレリスト**\n"
                for wc in restrooms[:5]:
                    emoji = "🟢" if wc.get("crowded_level") == "空いている" else "🟡" if wc.get("crowded_level") == "普通" else "🔴"
                    msg += f"{emoji} {wc['name']} ({wc['landmark']})\n"
                
                if len(restrooms) > 5:
                    msg += f"...他 {len(restrooms) - 5} か所\n"
                
                return ChatResponse(message=msg, category="facilities", confidence=0.95)
            
            # パーク指定なし
            else:
                msg += "どちらのパークですか？\n\n"
                msg += "・「ランドのトイレ」\n"
                msg += "・「シーのトイレ」\n"
                msg += "・「ファンタジーランドのトイレ」（エリア指定も可）\n\n"
                msg += "**💡 穴場トイレ（空いていることが多い）**\n"
                msg += "・ランド: ウエスタンランド、トゥモローランド奥\n"
                msg += "・シー: ロストリバーデルタ、ポートディスカバリー"
                
                return ChatResponse(message=msg, category="facilities", confidence=0.8)
        
        # ベビーセンター・授乳室
        if any(kw in message for kw in ["ベビーセンター", "授乳", "おむつ", "オムツ", "ミルク"]):
            msg = "👶 **ベビーセンター**\n\n"
            
            if target_park:
                park_data = facilities.get(target_park, {})
                baby = park_data.get("baby_center", {})
                
                msg += f"**{park_name}のベビーセンター**\n"
                msg += f"📍 場所: {baby.get('landmark', '')}\n"
                msg += f"🕐 時間: {baby.get('hours', '')}\n\n"
                msg += "**サービス内容**\n"
                for service in baby.get("services", []):
                    msg += f"・{service}\n"
            else:
                for park_key, park_label in [("tokyo_disney_land", "ディズニーランド"), ("tokyo_disney_sea", "ディズニーシー")]:
                    park_data = facilities.get(park_key, {})
                    baby = park_data.get("baby_center", {})
                    
                    msg += f"**🏰 {park_label}**\n"
                    msg += f"📍 {baby.get('landmark', '')}\n\n"
            
            msg += "\n**サービス**: 授乳室、おむつ替え、ミルク用お湯、離乳食販売など"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # 救護室
        if any(kw in message for kw in ["救護室", "具合が悪い", "体調", "気持ち悪い"]):
            msg = "🏥 **救護室**\n\n"
            
            if any(kw in message for kw in ["具合が悪い", "体調", "気持ち悪い"]):
                msg += "**⚠️ 体調が悪い場合は無理せず休んでください！**\n\n"
            
            for park_key, park_label in [("tokyo_disney_land", "ディズニーランド"), ("tokyo_disney_sea", "ディズニーシー")]:
                park_data = facilities.get(park_key, {})
                first_aid = park_data.get("first_aid", {})
                
                msg += f"**🏰 {park_label}**\n"
                msg += f"📍 {first_aid.get('landmark', '')}\n\n"
            
            msg += "**💡 Tips**\n"
            msg += "・場所がわからない時は近くのキャストに声をかけてください\n"
            msg += "・AED設置あり\n"
            msg += "・応急処置・休憩ができます"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # ロッカー
        if any(kw in message for kw in ["ロッカー", "荷物", "預ける"]):
            msg = "🗄️ **コインロッカー**\n\n"
            
            for park_key, park_label in [("tokyo_disney_land", "ディズニーランド"), ("tokyo_disney_sea", "ディズニーシー")]:
                park_data = facilities.get(park_key, {})
                lockers = park_data.get("locker", [])
                
                msg += f"**🏰 {park_label}**\n"
                for locker in lockers:
                    msg += f"📍 {locker['name']}\n"
                    msg += f"   場所: {locker['location']}\n"
                    if locker.get("sizes"):
                        msg += f"   サイズ: {', '.join(locker['sizes'])}\n"
                    if locker.get("tip"):
                        msg += f"   💡 {locker['tip']}\n"
                msg += "\n"
            
            msg += "**💡 Tips**: 大きな荷物は入園前に預けるのがおすすめ！"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # 喫煙所
        if any(kw in message for kw in ["喫煙", "タバコ", "たばこ"]):
            msg = "🚬 **喫煙所**\n\n"
            msg += "**パーク内は全面禁煙です**\n\n"
            msg += "喫煙所はパーク外（メインエントランス左側）にあります。\n"
            msg += "一度退園すると再入園が必要です。"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # ATM
        if any(kw in message for kw in ["ATM", "お金", "現金"]):
            msg = "🏧 **ATM**\n\n"
            msg += "**ディズニーランド**: ワールドバザール内\n"
            msg += "**ディズニーシー**: メディテレーニアンハーバー内\n\n"
            msg += "💡 パーク内の支払いは現金・クレジットカード・電子マネー対応"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # 迷子
        if any(kw in message for kw in ["迷子", "はぐれた"]):
            msg = "👦 **迷子センター**\n\n"
            msg += "**ディズニーランド**: ワールドバザール（ベビーセンター付近）\n"
            msg += "**ディズニーシー**: メディテレーニアンハーバー（ベビーセンター付近）\n\n"
            msg += "**💡 Tips**\n"
            msg += "・迷子になったら近くのキャストに声をかけてください\n"
            msg += "・入園時に迷子シールをもらっておくと安心\n"
            msg += "・お子様に連絡先を書いて持たせておくのもおすすめ"
            
            return ChatResponse(message=msg, category="facilities", confidence=0.95)
        
        # 一般的な施設案内
        msg = "📍 **施設ガイド**\n\n"
        msg += "以下について聞いてください：\n\n"
        msg += "🚻 「トイレ」「ランドのトイレ」\n"
        msg += "👶 「ベビーセンター」「授乳室」\n"
        msg += "🏥 「救護室」「体調が悪い」\n"
        msg += "🗄️ 「ロッカー」「荷物を預けたい」\n"
        msg += "🚬 「喫煙所」\n"
        msg += "🏧 「ATM」\n"
        msg += "👦 「迷子センター」"
        
        return ChatResponse(message=msg, category="facilities", confidence=0.7)
    
    def _format_ticket_response(self, message: str) -> ChatResponse:
        """チケット情報をフォーマット"""
        official_info = self.kb.official_info if hasattr(self.kb, 'official_info') else {}
        ticket_info = official_info.get("ticket_prices", {})
        
        msg = "🎫 **チケット情報**\n\n"
        
        # ワンデーパスポート
        if "1day_passport" in ticket_info:
            passport = ticket_info["1day_passport"]
            msg += "**1デーパスポート（変動価格制）**\n"
            
            if "adult" in passport:
                adult = passport["adult"]
                msg += f"・大人（18歳以上）: ¥{adult.get('min', '?'):,}〜¥{adult.get('max', '?'):,}\n"
            
            if "junior" in passport:
                junior = passport["junior"]
                msg += f"・中人（{junior.get('age_range', '12-17歳')}）: ¥{junior.get('min', '?'):,}〜¥{junior.get('max', '?'):,}\n"
            
            if "child" in passport:
                child = passport["child"]
                msg += f"・小人（{child.get('age_range', '4-11歳')}）: ¥{child.get('min', '?'):,}〜¥{child.get('max', '?'):,}\n"
            
            msg += "\n💡 日によって価格が異なります（変動価格制）\n"
        else:
            msg += "**1デーパスポート**\n"
            msg += "・大人: ¥7,900〜¥10,900\n"
            msg += "・中人（12-17歳）: ¥6,600〜¥9,000\n"
            msg += "・小人（4-11歳）: ¥4,700〜¥5,600\n"
            msg += "\n💡 日によって価格が異なります\n"
        
        msg += "\n**購入方法**\n"
        msg += "・公式サイト: https://www.tokyodisneyresort.jp/\n"
        msg += "・公式アプリ: 東京ディズニーリゾート・アプリ\n"
        msg += "\n_※最新の料金は公式サイトでご確認ください_"
        
        return ChatResponse(
            message=msg,
            category="ticket",
            confidence=0.9
        )
    
    def _format_wait_time_response(self, message: str) -> ChatResponse:
        """待ち時間情報をフォーマット"""
        if not self.kb.wait_time_service:
            return ChatResponse(
                message="待ち時間情報は現在利用できません。",
                category="wait_time",
                confidence=0.5
            )
        
        message_lower = message.lower()
        
        # 特定のアトラクションを探す
        attraction_name = self._extract_attraction_name(message)
        if attraction_name:
            wt = self.kb.wait_time_service.get_wait_time(attraction_name)
            if wt:
                status = "🔴 混雑" if wt.wait_minutes >= 60 else "🟡 普通" if wt.wait_minutes >= 30 else "🟢 空いている"
                msg = f"⏰ **{wt.attraction_name}の待ち時間**\n\n"
                msg += f"**現在の待ち時間: {wt.wait_minutes}分** {status}\n\n"
                
                # アドバイス
                if wt.wait_minutes >= 60:
                    msg += "💡 **アドバイス**\n"
                    msg += "・プレミアアクセスの購入を検討\n"
                    msg += "・夕方以降は待ち時間が減る傾向\n"
                    msg += "・パレード中は空くことも"
                elif wt.wait_minutes >= 30:
                    msg += "💡 普通の混雑です。30分程度で乗れます。"
                else:
                    msg += "💡 今がチャンス！比較的空いています。"
                
                return ChatResponse(
                    message=msg,
                    category="wait_time",
                    confidence=0.9,
                    related_data={"wait_time": wt.wait_minutes}
                )
        
        # パーク指定があるか確認
        target_park = None
        if "ランド" in message and "シー" not in message:
            target_park = "tdl"
        elif "シー" in message and "ランド" not in message:
            target_park = "tds"
        
        # 全体の待ち時間サマリー
        msg = self.kb.wait_time_service.format_wait_times_summary(target_park)
        
        return ChatResponse(
            message=msg,
            category="wait_time",
            confidence=0.85
        )


# テスト用
if __name__ == "__main__":
    bot = DisneyChatbot()
    
    test_messages = [
        "こんにちは",
        "美女と野獣について教えて",
        "トイストーリーマニアの待ち時間は？",
        "隠れミッキーを教えて",
        "スタンバイパスって何？",
        "初心者向けのアドバイス",
        "ビッグサンダーのトリビア",
    ]
    
    for msg in test_messages:
        print(f"\n👤 {msg}")
        response = bot.chat(msg)
        print(f"🤖 {response.message[:200]}...")
        print(f"   [カテゴリ: {response.category}, 信頼度: {response.confidence}]")

