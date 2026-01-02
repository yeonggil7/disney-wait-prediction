"""
LLMエンジン - OpenAI/Claude APIを使用した自然な対話
"""
import os
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLMからの応答"""
    message: str
    used_context: list
    tokens_used: int = 0


class DisneyLLMEngine:
    """OpenAI/Claude APIを使用したディズニーチャットエンジン"""
    
    SYSTEM_PROMPT = """あなたは東京ディズニーリゾートの専門ガイド「ディズニーガイドBot」です。
以下のルールに従って回答してください：

## 役割
- 東京ディズニーランド・ディズニーシーについての質問に親切に答える
- 初心者にもわかりやすく説明する
- 楽しさとワクワク感を伝える
- 2025年の最新情報に基づいて回答する

## 季節への配慮
- 現在の季節に応じた服装・持ち物のアドバイスを提供する
- 季節特有の注意点（夏の熱中症、冬の防寒など）を必ず伝える
- 季節イベント（クリスマス、ハロウィーンなど）の情報も添える
- 混雑状況は季節によって異なることを考慮する

## 回答スタイル
- 絵文字を適度に使用（🏰🎢🐭✨🌸☀️🍂❄️など）
- 重要なポイントは**太字**で強調
- 箇条書きを活用して読みやすく
- 長すぎず、簡潔に

## 注意事項
- 提供されたナレッジベースの情報を優先して使用
- 不確かな情報は「最新情報は公式サイトでご確認ください」と添える
- 安全に関わる情報（身長制限など）は正確に伝える
- 天候や季節に関するアドバイスは具体的に

## 禁止事項
- 公式でない情報を断定的に伝えること
- ネガティブな表現や批判
- 他のテーマパークとの比較"""

    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        """
        Args:
            api_key: APIキー（環境変数からも取得可能）
            provider: "openai", "anthropic", または "auto"（自動検出）
        """
        self.client = None
        self.provider = None
        self.model = None
        
        # 自動検出またはOpenAI優先
        if provider == "auto" or provider == "openai":
            openai_key = api_key or os.environ.get("OPENAI_API_KEY")
            if openai_key:
                try:
                    from openai import OpenAI
                    self.client = OpenAI(api_key=openai_key)
                    self.provider = "openai"
                    self.model = "gpt-4o-mini"  # コスト効率の良いモデル
                    print(f"✅ OpenAI API initialized (model: {self.model})")
                except ImportError:
                    print("Warning: openai package not installed. Run: pip install openai")
        
        # OpenAIが使えない場合はAnthropicを試す
        if not self.client and (provider == "auto" or provider == "anthropic"):
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
            if anthropic_key:
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(api_key=anthropic_key)
                    self.provider = "anthropic"
                    self.model = "claude-sonnet-4-20250514"
                    print(f"✅ Anthropic API initialized (model: {self.model})")
                except ImportError:
                    print("Warning: anthropic package not installed. Run: pip install anthropic")
    
    def is_available(self) -> bool:
        """LLMが利用可能かどうか"""
        return self.client is not None
    
    def build_context(self, knowledge_base, user_message: str) -> str:
        """ナレッジベースからコンテキストを構築"""
        context_parts = []
        
        # 2025年イベント・休止情報を読み込み
        events_2025 = self._load_events_2025(knowledge_base)
        shows_parades = self._load_shows_parades(knowledge_base)
        hidden_mickeys_full = self._load_hidden_mickeys_full(knowledge_base)
        restaurants_full = self._load_restaurants_full(knowledge_base)
        beginner_guide = self._load_beginner_guide_2025(knowledge_base)
        tips_advanced = self._load_tips_advanced_2025(knowledge_base)
        facilities_map = self._load_facilities_map(knowledge_base)
        
        # 現在の季節を取得
        current_season = self._get_current_season()
        season_name = self._get_season_name_jp(current_season)
        
        # アトラクション情報を検索
        attractions = knowledge_base.search_attraction(user_message)
        if attractions:
            context_parts.append("## 関連アトラクション情報")
            for attr in attractions[:3]:
                context_parts.append(f"""
### {attr['name']}
- パーク: {'ディズニーランド' if attr['park'] == 'tdl' else 'ディズニーシー'}
- タイプ: {attr.get('type', '不明')}
- 所要時間: {attr.get('duration_minutes', '?')}分
- 身長制限: {attr.get('height_restriction', 'なし')}cm以上
- 説明: {attr.get('description', '')}
- トリビア: {', '.join(attr.get('trivia', [])[:2])}
- Tips: {', '.join(attr.get('tips', [])[:2])}
""")
        
        # アプリガイド情報
        app_keywords = ["スタンバイパス", "プレミアアクセス", "DPA", "エントリー", "予約", "モバイルオーダー", "アプリ"]
        if any(kw in user_message for kw in app_keywords):
            context_parts.append("## アプリ・予約システム情報")
            app_guide = knowledge_base.app_guide.get("app_guide", {})
            for feature in app_guide.get("features", []):
                if any(kw.lower() in feature.get("name", "").lower() or kw.lower() in user_message.lower() 
                       for kw in app_keywords):
                    context_parts.append(f"""
### {feature['name']}
- 説明: {feature.get('description', '')}
- 使い方: {', '.join(feature.get('how_to_use', [])[:3])}
- Tips: {', '.join(feature.get('tips', [])[:3])}
""")
        
        # 隠れミッキー
        if "隠れミッキー" in user_message or "ミッキー" in user_message:
            context_parts.append("## 隠れミッキー情報")
            hm = knowledge_base.hidden_mickeys.get("hidden_mickeys", {})
            context_parts.append(f"説明: {hm.get('description', '')}")
            
            # いくつかの例を追加
            for park_id, areas in hm.get("locations", {}).items():
                park_name = "ディズニーランド" if park_id == "tdl" else "ディズニーシー"
                for area in areas[:2]:
                    for spot in area.get("spots", [])[:1]:
                        context_parts.append(f"- {park_name} {area['area']}: {spot['name']} (ヒント: {spot.get('hint', '')})")
        
        # Tips・初心者ガイド
        tip_keywords = ["初心者", "初めて", "持ち物", "回り方", "コース", "混雑", "服装", "準備", "何を持っていく", "用意"]
        if any(kw in user_message for kw in tip_keywords):
            context_parts.append("## Tips情報（2025年版）")
            context_parts.append(f"※現在の季節: {season_name}（{current_season}）")
            
            # 2025年版初心者ガイドから季節別情報を取得
            if beginner_guide:
                seasonal_info = beginner_guide.get("beginner_guide_2025", {}).get("seasonal_guide", {}).get(current_season, {})
                
                if "初心者" in user_message or "初めて" in user_message:
                    context_parts.append(f"### {season_name}の基本情報")
                    context_parts.append(f"- 天気: {seasonal_info.get('weather_summary', '')}")
                    context_parts.append(f"- 気温: {seasonal_info.get('temperature_range', '')}")
                    
                    # 事前準備
                    essential_prep = beginner_guide.get("beginner_guide_2025", {}).get("essential_preparation", {}).get("must_do", [])
                    if essential_prep:
                        context_parts.append("### 絶対必要な事前準備")
                        for prep in essential_prep[:3]:
                            context_parts.append(f"- {prep['item']}: {prep['detail']}")
                    
                    # イベント情報
                    if seasonal_info.get("events_2025"):
                        context_parts.append(f"### {season_name}のイベント")
                        for event in seasonal_info["events_2025"]:
                            context_parts.append(f"- {event}")
                
                if "持ち物" in user_message or "準備" in user_message or "用意" in user_message or "何を持っていく" in user_message:
                    context_parts.append(f"### {season_name}の持ち物リスト")
                    packing = seasonal_info.get("packing_list", {})
                    
                    if packing.get("essential"):
                        context_parts.append("**必須アイテム**")
                        for item in packing["essential"]:
                            context_parts.append(f"- {item}")
                    
                    if packing.get("optional"):
                        context_parts.append("**あると便利**")
                        for item in packing["optional"][:5]:
                            context_parts.append(f"- {item}")
                    
                    # 季節固有の持ち物
                    if current_season == "winter" and packing.get("warming_spots"):
                        context_parts.append("**暖まれるスポット**")
                        for spot in seasonal_info.get("warming_spots", [])[:3]:
                            context_parts.append(f"- {spot}")
                
                if "服装" in user_message:
                    context_parts.append(f"### {season_name}の服装アドバイス")
                    clothing = seasonal_info.get("clothing", {})
                    
                    if clothing.get("recommended"):
                        context_parts.append("**おすすめ**")
                        for item in clothing["recommended"]:
                            context_parts.append(f"- {item}")
                    
                    if clothing.get("avoid"):
                        context_parts.append("**避けた方がいい**")
                        for item in clothing["avoid"]:
                            context_parts.append(f"- {item}")
                
                # 季節固有のTips
                if seasonal_info.get("special_tips"):
                    context_parts.append(f"### {season_name}の注意点・Tips")
                    for tip in seasonal_info["special_tips"][:5]:
                        context_parts.append(f"- {tip}")
                
                # 夏の熱中症対策
                if current_season == "summer" and seasonal_info.get("heat_stroke_prevention"):
                    context_parts.append("### 熱中症対策")
                    for tip in seasonal_info["heat_stroke_prevention"]:
                        context_parts.append(f"- {tip}")
            
            if "混雑" in user_message or "空いて" in user_message:
                if beginner_guide:
                    seasonal_info = beginner_guide.get("beginner_guide_2025", {}).get("seasonal_guide", {}).get(current_season, {})
                    crowd = seasonal_info.get("crowd_info", {})
                    if crowd:
                        context_parts.append(f"### {season_name}の混雑情報")
                        if crowd.get("crowded"):
                            context_parts.append("混む時期: " + ", ".join(crowd["crowded"]))
                        if crowd.get("empty"):
                            context_parts.append("空いている時期: " + ", ".join(crowd["empty"]))
                        if crowd.get("tips"):
                            context_parts.append(f"Tips: {crowd['tips']}")
        
        # 2025年イベント情報
        event_keywords = ["イベント", "クリスマス", "ハロウィン", "ハロウィーン", "正月", "お正月", "25周年", "ダッフィー", "2025", "今年"]
        if any(kw in user_message for kw in event_keywords):
            if events_2025:
                context_parts.append("## 2025年イベント情報")
                
                # 東京ディズニーランド
                tdl_events = events_2025.get("events_2025", {}).get("tokyo_disney_land", {}).get("annual_events", [])
                if tdl_events:
                    context_parts.append("### ディズニーランド")
                    for event in tdl_events[:3]:
                        context_parts.append(f"- {event['name']}: {event.get('start_date', '?')} ～ {event.get('end_date', '?')}")
                        if event.get('description'):
                            context_parts.append(f"  {event['description']}")
                
                # 東京ディズニーシー
                tds_events = events_2025.get("events_2025", {}).get("tokyo_disney_sea", {}).get("annual_events", [])
                if tds_events:
                    context_parts.append("### ディズニーシー")
                    for event in tds_events[:3]:
                        context_parts.append(f"- {event['name']}: {event.get('start_date', '?')} ～ {event.get('end_date', '?')}")
                        if event.get('description'):
                            context_parts.append(f"  {event['description']}")
        
        # 休止情報
        if "休止" in user_message or "運休" in user_message or "メンテナンス" in user_message or "休み" in user_message:
            if events_2025:
                closures = events_2025.get("events_2025", {}).get("tokyo_disney_land", {}).get("maintenance_closures", [])
                if closures:
                    context_parts.append("## アトラクション休止予定")
                    for closure in closures[:5]:
                        context_parts.append(f"- {closure['name']}: {closure.get('closure_start', '?')} ～ {closure.get('closure_end', '?')}")
        
        # ショー・パレード情報
        show_keywords = ["ショー", "パレード", "花火", "ビリーヴ", "エレクトリカル", "グリーティング", "抽選", "エントリー"]
        if any(kw in user_message for kw in show_keywords):
            if shows_parades:
                context_parts.append("## ショー・パレード情報")
                
                # ランド
                tdl_shows = shows_parades.get("shows_and_parades_2025", {}).get("tokyo_disney_land", {})
                if "パレード" in user_message and tdl_shows.get("day_parades"):
                    for show in tdl_shows["day_parades"]:
                        context_parts.append(f"### {show['name']}")
                        context_parts.append(f"- {show.get('description', '')}")
                        if show.get("tips"):
                            context_parts.append(f"- Tips: {', '.join(show['tips'][:2])}")
                
                # シー
                tds_shows = shows_parades.get("shows_and_parades_2025", {}).get("tokyo_disney_sea", {})
                if tds_shows.get("harbor_shows"):
                    for show in tds_shows["harbor_shows"]:
                        context_parts.append(f"### {show['name']}")
                        context_parts.append(f"- {show.get('description', '')}")
                        if show.get("tips"):
                            context_parts.append(f"- Tips: {', '.join(show['tips'][:2])}")
        
        # レストラン情報（拡張）
        restaurant_keywords = ["レストラン", "食事", "ご飯", "ランチ", "ディナー", "予約", "和食", "イタリアン", "中華", "カレー"]
        if any(kw in user_message for kw in restaurant_keywords):
            if restaurants_full:
                context_parts.append("## レストラン情報（2025年版）")
                
                # 予約情報
                if "予約" in user_message:
                    reservation_tips = restaurants_full.get("restaurants", {}).get("reservation_tips", {})
                    if reservation_tips.get("priority_seating"):
                        ps = reservation_tips["priority_seating"]
                        context_parts.append("### プライオリティ・シーティング（予約）")
                        context_parts.append(f"- {ps.get('description', '')}")
                        context_parts.append(f"- 予約開始: {ps.get('booking_start', '?')}")
                        if ps.get("tips"):
                            context_parts.append(f"- Tips: {', '.join(ps['tips'][:3])}")
        
        # 隠れミッキー（拡張）
        if "隠れミッキー" in user_message or "ミッキー探" in user_message:
            if hidden_mickeys_full:
                context_parts.append("## 隠れミッキー情報（最新版）")
                hm = hidden_mickeys_full.get("hidden_mickeys", {})
                context_parts.append(f"{hm.get('description', '')}")
                
                # 難易度ガイド
                if hm.get("difficulty_guide"):
                    context_parts.append("### 難易度の目安")
                    for level, desc in hm["difficulty_guide"].items():
                        context_parts.append(f"- {level}: {desc}")
        
        # チケット・料金情報
        ticket_keywords = ["チケット", "料金", "値段", "価格", "いくら", "パスポート"]
        if any(kw in user_message for kw in ticket_keywords):
            if events_2025:
                ticket_info = events_2025.get("ticket_prices_2025", {})
                if ticket_info:
                    context_parts.append("## 2025年チケット情報")
                    passport = ticket_info.get("1day_passport", {})
                    if passport.get("adult_18_and_over"):
                        adult = passport["adult_18_and_over"]
                        context_parts.append(f"- 大人（18歳以上）: ¥{adult.get('min_price', '?'):,}〜¥{adult.get('max_price', '?'):,}")
                    if passport.get("junior_12_to_17"):
                        junior = passport["junior_12_to_17"]
                        context_parts.append(f"- 中人（12-17歳）: ¥{junior.get('min_price', '?'):,}〜¥{junior.get('max_price', '?'):,}")
                    if passport.get("child_4_to_11"):
                        child = passport["child_4_to_11"]
                        context_parts.append(f"- 小人（4-11歳）: ¥{child.get('min_price', '?'):,}〜¥{child.get('max_price', '?'):,}")
                    context_parts.append("※変動価格制。日によって価格が異なります")
        
        # 子連れ・シニア向け情報
        family_keywords = ["子連れ", "子供", "こども", "赤ちゃん", "ベビー", "幼児", "キッズ", "身長制限", "ベビーカー"]
        if any(kw in user_message for kw in family_keywords):
            if beginner_guide:
                kids_info = beginner_guide.get("beginner_guide_2025", {}).get("with_special_needs", {}).get("with_kids", {})
                if kids_info:
                    context_parts.append("## 子連れディズニーガイド")
                    
                    # 年齢別おすすめ
                    if "赤ちゃん" in user_message or "0歳" in user_message or "1歳" in user_message or "2歳" in user_message:
                        age_info = kids_info.get("age_recommendations", {}).get("0-2歳", {})
                        if age_info:
                            context_parts.append("### 0-2歳のお子様向け")
                            context_parts.append("おすすめアトラクション: " + ", ".join(age_info.get("recommended_attractions", [])))
                            for tip in age_info.get("tips", []):
                                context_parts.append(f"- {tip}")
                    
                    elif "3歳" in user_message or "4歳" in user_message or "5歳" in user_message or "幼児" in user_message:
                        age_info = kids_info.get("age_recommendations", {}).get("3-5歳", {})
                        if age_info:
                            context_parts.append("### 3-5歳のお子様向け")
                            context_parts.append("おすすめアトラクション: " + ", ".join(age_info.get("recommended_attractions", [])))
                            for tip in age_info.get("tips", []):
                                context_parts.append(f"- {tip}")
                    
                    elif "小学生" in user_message or ("6歳" in user_message or "7歳" in user_message or "8歳" in user_message):
                        age_info = kids_info.get("age_recommendations", {}).get("6-11歳", {})
                        if age_info:
                            context_parts.append("### 6-11歳のお子様向け")
                            for tip in age_info.get("tips", []):
                                context_parts.append(f"- {tip}")
                    
                    # 身長制限
                    if "身長" in user_message:
                        height_info = kids_info.get("height_restrictions_summary", {})
                        if height_info:
                            context_parts.append("### 身長制限まとめ")
                            for height, attractions in height_info.items():
                                context_parts.append(f"- {height}以上: {', '.join(attractions)}")
                    
                    # 施設情報
                    if "ベビー" in user_message or "おむつ" in user_message or "授乳" in user_message:
                        facilities = kids_info.get("facilities", [])
                        for facility in facilities:
                            context_parts.append(f"### {facility['name']}")
                            if facility.get("location_tdl"):
                                context_parts.append(f"- ランド: {facility['location_tdl']}")
                            if facility.get("location_tds"):
                                context_parts.append(f"- シー: {facility['location_tds']}")
                            if facility.get("services"):
                                context_parts.append(f"- サービス: {', '.join(facility['services'])}")
        
        # シニア向け情報
        senior_keywords = ["シニア", "高齢", "おじいちゃん", "おばあちゃん", "祖父母", "年配", "足が悪い", "車椅子"]
        if any(kw in user_message for kw in senior_keywords):
            if beginner_guide:
                senior_info = beginner_guide.get("beginner_guide_2025", {}).get("with_special_needs", {}).get("with_seniors", {})
                if senior_info:
                    context_parts.append("## シニアと一緒に楽しむガイド")
                    for tip in senior_info.get("tips", []):
                        context_parts.append(f"- {tip}")
                    if senior_info.get("recommended"):
                        context_parts.append("### おすすめアトラクション")
                        context_parts.append(", ".join(senior_info["recommended"]))
        
        # 攻略・裏技情報
        strategy_keywords = ["攻略", "裏技", "効率", "コツ", "おすすめの回り方", "穴場", "空いてる"]
        if any(kw in user_message for kw in strategy_keywords):
            if tips_advanced:
                advanced = tips_advanced.get("advanced_tips_2025", {})
                
                if "朝" in user_message or "開園" in user_message:
                    morning = advanced.get("morning_strategy", {})
                    if morning:
                        context_parts.append(f"## {morning.get('title', '朝の攻略法')}")
                        for tip in morning.get("tips", []):
                            context_parts.append(f"- {tip['tip']}: {tip['detail']}")
                
                if "DPA" in user_message or "プレミアアクセス" in user_message:
                    dpa = advanced.get("dpa_strategy", {})
                    if dpa:
                        context_parts.append(f"## {dpa.get('title', 'DPA攻略')}")
                        for tip in dpa.get("tips", []):
                            context_parts.append(f"- {tip['tip']}: {tip['detail']}")
                
                if "穴場" in user_message or "裏技" in user_message:
                    hidden = advanced.get("hidden_gems", {})
                    if hidden:
                        context_parts.append(f"## {hidden.get('title', '穴場スポット')}")
                        for tip in hidden.get("tips", []):
                            context_parts.append(f"- {tip['tip']}: {tip['detail']}")
                
                # ファンタジースプリングス攻略
                if "ファンタジースプリングス" in user_message:
                    fs = advanced.get("fantasy_springs_tips_2025", {})
                    if fs:
                        context_parts.append("## ファンタジースプリングス攻略2025")
                        context_parts.append(fs.get("description", ""))
                        
                        access = fs.get("access", {})
                        if access.get("methods"):
                            context_parts.append("### 入場方法")
                            for method in access["methods"]:
                                context_parts.append(f"- {method}")
                        
                        if access.get("tips"):
                            context_parts.append("### Tips")
                            for tip in access["tips"]:
                                context_parts.append(f"- {tip}")
        
        # プラン生成のコンテキスト
        plan_keywords = ["プラン", "計画", "スケジュール", "回り方", "まわり方", "効率", "モデルコース", "1日", "一日"]
        if any(kw in user_message for kw in plan_keywords):
            try:
                from plan_generator import PlanGeneratorService
                plan_service = PlanGeneratorService()
                
                # パークを特定
                park = "tds"
                if "ランド" in user_message and "シー" not in user_message:
                    park = "tdl"
                
                # ユーザータイプを特定
                user_type = "beginner"
                if any(kw in user_message for kw in ["子連れ", "こども", "子供", "ファミリー"]):
                    user_type = "family_with_kids"
                elif any(kw in user_message for kw in ["絶叫", "スリル"]):
                    user_type = "thrill_seeker"
                elif any(kw in user_message for kw in ["ファンタジースプリングス", "新エリア"]):
                    user_type = "fantasy_springs_focus"
                elif any(kw in user_message for kw in ["効率"]):
                    user_type = "efficient"
                
                plan = plan_service.generate_plan(park, user_type)
                
                context_parts.append("## 本日のおすすめプラン")
                context_parts.append(plan_service.format_plan(plan))
                
            except Exception as e:
                print(f"Error generating plan context: {e}")
        
        # 施設情報（トイレ、ベビーセンターなど）
        facility_keywords = ["トイレ", "お手洗い", "ベビーセンター", "授乳", "おむつ", "救護室", "体調", "ロッカー", "荷物", "喫煙", "ATM", "迷子"]
        if any(kw in user_message for kw in facility_keywords):
            if facilities_map:
                context_parts.append("## 施設情報")
                
                facilities = facilities_map.get("facilities", {})
                
                if "トイレ" in user_message or "お手洗い" in user_message:
                    context_parts.append("### トイレ情報")
                    tips = facilities.get("quick_answers", {}).get("restroom_tips", [])
                    for tip in tips:
                        context_parts.append(f"- {tip}")
                    
                    # 穴場トイレ
                    context_parts.append("### 穴場トイレ（空いていることが多い）")
                    for park_key, park_name in [("tokyo_disney_land", "ランド"), ("tokyo_disney_sea", "シー")]:
                        park_data = facilities.get(park_key, {})
                        restrooms = park_data.get("restrooms", [])
                        empty_wcs = [wc for wc in restrooms if wc.get("crowded_level") == "空いている"]
                        if empty_wcs:
                            for wc in empty_wcs[:2]:
                                context_parts.append(f"- [{park_name}] {wc['name']}: {wc['landmark']}")
                
                if any(kw in user_message for kw in ["ベビーセンター", "授乳", "おむつ"]):
                    context_parts.append("### ベビーセンター")
                    for park_key, park_name in [("tokyo_disney_land", "ランド"), ("tokyo_disney_sea", "シー")]:
                        park_data = facilities.get(park_key, {})
                        baby = park_data.get("baby_center", {})
                        if baby:
                            context_parts.append(f"- [{park_name}] {baby.get('landmark', '')}")
                            context_parts.append(f"  サービス: {', '.join(baby.get('services', [])[:4])}")
                
                if any(kw in user_message for kw in ["救護室", "体調", "具合"]):
                    context_parts.append("### 救護室")
                    for park_key, park_name in [("tokyo_disney_land", "ランド"), ("tokyo_disney_sea", "シー")]:
                        park_data = facilities.get(park_key, {})
                        first_aid = park_data.get("first_aid", {})
                        if first_aid:
                            context_parts.append(f"- [{park_name}] {first_aid.get('landmark', '')}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _load_events_2025(self, knowledge_base) -> dict:
        """2025年イベント情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "events_2025.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_shows_parades(self, knowledge_base) -> dict:
        """ショー・パレード情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "shows_parades_2025.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_hidden_mickeys_full(self, knowledge_base) -> dict:
        """隠れミッキー詳細情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "hidden_mickeys_full.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_restaurants_full(self, knowledge_base) -> dict:
        """レストラン詳細情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "restaurants_full.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_beginner_guide_2025(self, knowledge_base) -> dict:
        """2025年版初心者ガイドを読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "beginner_guide_2025.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_tips_advanced_2025(self, knowledge_base) -> dict:
        """2025年版攻略情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "tips_advanced_2025.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _load_facilities_map(self, knowledge_base) -> dict:
        """施設マップ情報を読み込む"""
        try:
            data_dir = knowledge_base.data_dir
            with open(data_dir / "facilities_map.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
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
    
    def chat(self, user_message: str, knowledge_base, conversation_history: list = None) -> LLMResponse:
        """
        LLMを使用してチャット
        
        Args:
            user_message: ユーザーのメッセージ
            knowledge_base: DisneyKnowledgeBaseインスタンス
            conversation_history: 過去の会話履歴
        """
        if not self.is_available():
            return LLMResponse(
                message="LLMが設定されていません。ANTHROPIC_API_KEY環境変数を設定してください。",
                used_context=[],
                tokens_used=0
            )
        
        # コンテキストを構築
        context = self.build_context(knowledge_base, user_message)
        
        # メッセージを構築
        messages = []
        
        # 会話履歴を追加
        if conversation_history:
            for msg in conversation_history[-10:]:  # 最新10件
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 現在のメッセージ
        user_content = user_message
        if context:
            user_content = f"""以下のナレッジベース情報を参考に回答してください：

{context}

---
ユーザーの質問: {user_message}"""
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        try:
            if self.provider == "openai":
                # OpenAI API
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        *messages
                    ]
                )
                
                return LLMResponse(
                    message=response.choices[0].message.content,
                    used_context=[context] if context else [],
                    tokens_used=response.usage.total_tokens if response.usage else 0
                )
            else:
                # Anthropic API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=self.SYSTEM_PROMPT,
                    messages=messages
                )
                
                return LLMResponse(
                    message=response.content[0].text,
                    used_context=[context] if context else [],
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens
                )
        except Exception as e:
            return LLMResponse(
                message=f"エラーが発生しました: {str(e)}",
                used_context=[],
                tokens_used=0
            )


class HybridChatEngine:
    """ルールベース + LLMのハイブリッドエンジン"""
    
    def __init__(self, knowledge_base, llm_engine: DisneyLLMEngine = None):
        from chatbot import DisneyChatbot
        self.rule_based = DisneyChatbot(knowledge_base)
        self.llm_engine = llm_engine or DisneyLLMEngine()
        self.knowledge_base = knowledge_base
        self.conversation_history = []
        self.use_llm = self.llm_engine.is_available()
    
    def chat(self, user_message: str, force_llm: bool = False) -> dict:
        """
        ハイブリッドチャット
        
        まずルールベースで回答を試み、信頼度が低い場合はLLMを使用
        
        Args:
            user_message: ユーザーのメッセージ
            force_llm: 強制的にLLMを使用
        """
        # 会話履歴に追加
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # ルールベースで試行
        if not force_llm:
            rule_response = self.rule_based.chat(user_message)
            
            # 信頼度が高い場合はルールベースの回答を使用
            if rule_response.confidence >= 0.7:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": rule_response.message
                })
                
                return {
                    "message": rule_response.message,
                    "category": rule_response.category,
                    "confidence": rule_response.confidence,
                    "engine": "rule_based"
                }
        
        # LLMを使用
        if self.use_llm:
            llm_response = self.llm_engine.chat(
                user_message,
                self.knowledge_base,
                self.conversation_history
            )
            
            self.conversation_history.append({
                "role": "assistant",
                "content": llm_response.message
            })
            
            return {
                "message": llm_response.message,
                "category": "llm",
                "confidence": 0.9,
                "engine": "llm",
                "tokens_used": llm_response.tokens_used
            }
        
        # LLMが使えない場合はルールベースの結果を返す
        rule_response = self.rule_based.chat(user_message)
        self.conversation_history.append({
            "role": "assistant",
            "content": rule_response.message
        })
        
        return {
            "message": rule_response.message,
            "category": rule_response.category,
            "confidence": rule_response.confidence,
            "engine": "rule_based"
        }
    
    def clear_history(self):
        """会話履歴をクリア"""
        self.conversation_history = []


# テスト用
if __name__ == "__main__":
    from chatbot import DisneyKnowledgeBase
    
    kb = DisneyKnowledgeBase()
    engine = HybridChatEngine(kb)
    
    print("=== ハイブリッドチャットエンジンテスト ===")
    print(f"LLM使用可能: {engine.use_llm}")
    
    test_messages = [
        "こんにちは",
        "トイストーリーマニアについて教えて",
        "ディズニーシーで絶叫系以外でおすすめは？",
    ]
    
    for msg in test_messages:
        print(f"\n👤 {msg}")
        response = engine.chat(msg)
        print(f"🤖 [{response['engine']}] {response['message'][:200]}...")

