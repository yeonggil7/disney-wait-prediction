"""
ユーザープロファイルサービス - 好み学習・記憶機能
"""
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import Counter


@dataclass
class UserPreferences:
    """ユーザーの好み"""
    favorite_park: Optional[str] = None  # tdl, tds
    thrill_preference: int = 3  # 1-5 (1=ゆったり, 5=絶叫大好き)
    has_children: bool = False
    favorite_attractions: List[str] = field(default_factory=list)
    disliked_attractions: List[str] = field(default_factory=list)
    favorite_characters: List[str] = field(default_factory=list)
    food_preferences: List[str] = field(default_factory=list)  # 和食, イタリアン, etc.
    visited_count: int = 0  # 来園回数
    last_visit: Optional[str] = None


@dataclass
class UserProfile:
    """ユーザープロファイル"""
    user_id: str
    name: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    conversation_history: List[Dict] = field(default_factory=list)
    learned_topics: Dict[str, int] = field(default_factory=dict)  # 話題 -> 回数
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class UserProfileService:
    """ユーザープロファイル管理サービス"""
    
    # 学習用キーワード
    THRILL_KEYWORDS = {
        "high": ["絶叫", "スリル", "怖い", "落下", "コースター", "タワー", "マウンテン", "レイジング"],
        "low": ["ゆったり", "のんびり", "子供", "怖くない", "優しい", "ボート", "シアター"]
    }
    
    CHARACTER_KEYWORDS = {
        "ミッキー": ["ミッキー", "mickey"],
        "ミニー": ["ミニー", "minnie"],
        "ダッフィー": ["ダッフィー", "duffy", "シェリーメイ", "ジェラトーニ"],
        "プリンセス": ["プリンセス", "シンデレラ", "アリエル", "ベル", "ラプンツェル", "エルサ", "アナ"],
        "ピクサー": ["トイストーリー", "ニモ", "モンスターズ", "ウッディ", "バズ"],
        "スター・ウォーズ": ["スターウォーズ", "スター・ウォーズ", "starwars"]
    }
    
    FOOD_KEYWORDS = {
        "和食": ["和食", "日本食", "うどん", "天ぷら", "寿司"],
        "イタリアン": ["イタリアン", "パスタ", "ピザ", "ピッツァ"],
        "中華": ["中華", "チャイニーズ", "麻婆"],
        "カレー": ["カレー"],
        "ハンバーガー": ["ハンバーガー", "バーガー"],
        "メキシカン": ["メキシカン", "タコス"]
    }
    
    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / "data" / "users"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, UserProfile] = {}
        self._load_all_profiles()
    
    def _load_all_profiles(self):
        """すべてのプロファイルを読み込む"""
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_id = data.get("user_id", file_path.stem)
                    
                    # Preferencesを復元
                    pref_data = data.get("preferences", {})
                    preferences = UserPreferences(**pref_data)
                    
                    profile = UserProfile(
                        user_id=user_id,
                        name=data.get("name"),
                        preferences=preferences,
                        conversation_history=data.get("conversation_history", []),
                        learned_topics=data.get("learned_topics", {}),
                        created_at=data.get("created_at", datetime.now().isoformat()),
                        updated_at=data.get("updated_at", datetime.now().isoformat())
                    )
                    self.profiles[user_id] = profile
            except Exception as e:
                print(f"Error loading profile {file_path}: {e}")
    
    def _save_profile(self, profile: UserProfile):
        """プロファイルを保存"""
        profile.updated_at = datetime.now().isoformat()
        file_path = self.data_dir / f"{profile.user_id}.json"
        
        try:
            data = {
                "user_id": profile.user_id,
                "name": profile.name,
                "preferences": asdict(profile.preferences),
                "conversation_history": profile.conversation_history[-100:],  # 最新100件のみ保存
                "learned_topics": profile.learned_topics,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving profile: {e}")
    
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """プロファイルを取得または作成"""
        if user_id not in self.profiles:
            profile = UserProfile(user_id=user_id)
            self.profiles[user_id] = profile
            self._save_profile(profile)
        return self.profiles[user_id]
    
    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserProfile:
        """好みを更新"""
        profile = self.get_or_create_profile(user_id)
        
        for key, value in preferences.items():
            if hasattr(profile.preferences, key):
                setattr(profile.preferences, key, value)
        
        self._save_profile(profile)
        return profile
    
    def add_conversation(self, user_id: str, role: str, content: str):
        """会話を記録"""
        profile = self.get_or_create_profile(user_id)
        
        profile.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 会話から学習
        if role == "user":
            self._learn_from_message(profile, content)
        
        self._save_profile(profile)
    
    def _learn_from_message(self, profile: UserProfile, message: str):
        """メッセージから学習"""
        message_lower = message.lower()
        
        # スリル好みを学習
        for keyword in self.THRILL_KEYWORDS["high"]:
            if keyword in message_lower:
                if profile.preferences.thrill_preference < 5:
                    profile.preferences.thrill_preference = min(5, profile.preferences.thrill_preference + 0.5)
                break
        
        for keyword in self.THRILL_KEYWORDS["low"]:
            if keyword in message_lower:
                if profile.preferences.thrill_preference > 1:
                    profile.preferences.thrill_preference = max(1, profile.preferences.thrill_preference - 0.5)
                break
        
        # キャラクター好みを学習
        for char_name, keywords in self.CHARACTER_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    if char_name not in profile.preferences.favorite_characters:
                        profile.preferences.favorite_characters.append(char_name)
                    break
        
        # 食事の好みを学習
        for food_type, keywords in self.FOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    if food_type not in profile.preferences.food_preferences:
                        profile.preferences.food_preferences.append(food_type)
                    break
        
        # パーク好みを学習
        if "ランド" in message and "シー" not in message:
            profile.learned_topics["tdl"] = profile.learned_topics.get("tdl", 0) + 1
        elif "シー" in message and "ランド" not in message:
            profile.learned_topics["tds"] = profile.learned_topics.get("tds", 0) + 1
        
        # 子連れかどうかを学習
        child_keywords = ["子供", "子ども", "こども", "赤ちゃん", "キッズ", "親子"]
        if any(kw in message_lower for kw in child_keywords):
            profile.preferences.has_children = True
        
        # 丸める
        profile.preferences.thrill_preference = round(profile.preferences.thrill_preference)
    
    def get_personalized_recommendations(self, user_id: str, knowledge_base) -> Dict:
        """パーソナライズされた推奨を取得"""
        profile = self.get_or_create_profile(user_id)
        prefs = profile.preferences
        
        recommendations = {
            "attractions": [],
            "restaurants": [],
            "tips": [],
            "message": ""
        }
        
        # アトラクション推奨
        attractions = list(knowledge_base.attractions.values())
        scored_attractions = []
        
        for attr in attractions:
            score = 50  # ベーススコア
            
            # スリルレベルでスコア調整
            thrill_level = attr.get("thrill_level", 3)
            thrill_diff = abs(thrill_level - prefs.thrill_preference)
            score -= thrill_diff * 10
            
            # 子連れの場合、身長制限なしを優先
            if prefs.has_children:
                if attr.get("height_restriction") is None:
                    score += 20
                else:
                    score -= 10
            
            # 好きなキャラクターのアトラクションを優先
            attr_name = attr.get("name", "").lower()
            for char in prefs.favorite_characters:
                if char.lower() in attr_name:
                    score += 30
            
            # パーク好みを反映
            if prefs.favorite_park == attr.get("park"):
                score += 10
            
            scored_attractions.append((score, attr))
        
        scored_attractions.sort(key=lambda x: x[0], reverse=True)
        recommendations["attractions"] = [a[1] for a in scored_attractions[:5]]
        
        # レストラン推奨
        restaurants = knowledge_base.restaurants.get("restaurants", [])
        scored_restaurants = []
        
        for rest in restaurants:
            score = 50
            
            # 食事の好みを反映
            cuisine = rest.get("cuisine", "").lower()
            for food_pref in prefs.food_preferences:
                if food_pref.lower() in cuisine:
                    score += 30
            
            # 子連れの場合、ファミリー向けを優先
            if prefs.has_children:
                if "ファミリー" in str(rest.get("recommended_for", [])):
                    score += 20
            
            scored_restaurants.append((score, rest))
        
        scored_restaurants.sort(key=lambda x: x[0], reverse=True)
        recommendations["restaurants"] = [r[1] for r in scored_restaurants[:3]]
        
        # パーソナライズメッセージ
        msg_parts = []
        
        if prefs.favorite_characters:
            msg_parts.append(f"好きなキャラクター: {', '.join(prefs.favorite_characters[:3])}")
        
        if prefs.thrill_preference >= 4:
            msg_parts.append("絶叫系が好き")
        elif prefs.thrill_preference <= 2:
            msg_parts.append("ゆったり系が好き")
        
        if prefs.has_children:
            msg_parts.append("子連れ")
        
        if prefs.food_preferences:
            msg_parts.append(f"食事: {', '.join(prefs.food_preferences[:2])}")
        
        if msg_parts:
            recommendations["message"] = f"あなたの好み: {' / '.join(msg_parts)}"
        
        return recommendations
    
    def get_profile_summary(self, user_id: str) -> Dict:
        """プロファイルサマリーを取得"""
        profile = self.get_or_create_profile(user_id)
        prefs = profile.preferences
        
        return {
            "user_id": user_id,
            "name": profile.name,
            "preferences": {
                "favorite_park": prefs.favorite_park,
                "thrill_preference": prefs.thrill_preference,
                "has_children": prefs.has_children,
                "favorite_characters": prefs.favorite_characters,
                "food_preferences": prefs.food_preferences
            },
            "conversation_count": len(profile.conversation_history),
            "created_at": profile.created_at,
            "updated_at": profile.updated_at
        }
    
    def format_recommendations_message(self, user_id: str, knowledge_base) -> str:
        """推奨メッセージをフォーマット"""
        recs = self.get_personalized_recommendations(user_id, knowledge_base)
        
        msg = "✨ **あなたへのおすすめ**\n\n"
        
        if recs["message"]:
            msg += f"_{recs['message']}_\n\n"
        
        if recs["attractions"]:
            msg += "**🎢 おすすめアトラクション**\n"
            for attr in recs["attractions"][:3]:
                park_name = "ランド" if attr["park"] == "tdl" else "シー"
                msg += f"・{attr['name']} [{park_name}]\n"
            msg += "\n"
        
        if recs["restaurants"]:
            msg += "**🍽️ おすすめレストラン**\n"
            for rest in recs["restaurants"][:2]:
                park_name = "ランド" if rest["park"] == "tdl" else "シー"
                msg += f"・{rest['name']} [{park_name}] - {rest.get('cuisine', '')}\n"
        
        if not recs["attractions"] and not recs["restaurants"]:
            msg = "まだあなたの好みを学習中です。\n"
            msg += "もっとお話しして、あなたにぴったりのおすすめを見つけましょう！"
        
        return msg


# テスト用
if __name__ == "__main__":
    service = UserProfileService()
    
    print("=== ユーザープロファイルサービステスト ===")
    
    # テストユーザー
    user_id = "test_user_1"
    profile = service.get_or_create_profile(user_id)
    print(f"プロファイル作成: {profile.user_id}")
    
    # 会話から学習
    service.add_conversation(user_id, "user", "子供と一緒にディズニーランドに行きたい")
    service.add_conversation(user_id, "user", "ミッキーに会いたい！")
    service.add_conversation(user_id, "user", "イタリアンのレストランを教えて")
    service.add_conversation(user_id, "user", "絶叫系はちょっと苦手...")
    
    # 学習結果を確認
    summary = service.get_profile_summary(user_id)
    print(f"\n学習結果:")
    print(f"・子連れ: {summary['preferences']['has_children']}")
    print(f"・好きなキャラ: {summary['preferences']['favorite_characters']}")
    print(f"・食事の好み: {summary['preferences']['food_preferences']}")
    print(f"・スリル好み: {summary['preferences']['thrill_preference']}")



