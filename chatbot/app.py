"""
ディズニーチャットボット - Webアプリケーション
"""
import os
from flask import Flask, render_template, request, jsonify, session
from chatbot import DisneyChatbot, DisneyKnowledgeBase
from llm_engine import DisneyLLMEngine, HybridChatEngine
from wait_time_service import WaitTimeService
from image_service import ImageService
from user_profile_service import UserProfileService
from plan_generator import PlanGeneratorService
from closure_service import ClosureService

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "disney-chatbot-secret-key-2024")

# チャットボットの初期化
kb = DisneyKnowledgeBase()
bot = DisneyChatbot(kb)
llm_engine = DisneyLLMEngine()
hybrid_engine = HybridChatEngine(kb, llm_engine)
wait_time_service = WaitTimeService()
image_service = ImageService()
user_profile_service = UserProfileService()
plan_generator = PlanGeneratorService()
closure_service = ClosureService()

# セッション別のエンジンを管理
session_engines = {}


@app.route("/")
def index():
    """メインページ"""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """チャットAPI"""
    data = request.get_json()
    message = data.get("message", "")
    use_llm = data.get("use_llm", True)  # デフォルトでLLMを使用
    
    if not message:
        return jsonify({"error": "メッセージを入力してください"}), 400
    
    # セッションIDを取得または生成
    session_id = request.headers.get("X-Session-ID", "default")
    
    # セッション別のエンジンを取得または作成
    if session_id not in session_engines:
        session_engines[session_id] = HybridChatEngine(kb, llm_engine)
    
    engine = session_engines[session_id]
    
    # ハイブリッドエンジンで応答を生成
    response = engine.chat(message, force_llm=(use_llm and llm_engine.is_available()))
    
    # ユーザープロファイルに会話を記録して学習
    user_profile_service.add_conversation(session_id, "user", message)
    user_profile_service.add_conversation(session_id, "assistant", response["message"])
    
    return jsonify({
        "message": response["message"],
        "category": response.get("category", "unknown"),
        "confidence": response.get("confidence", 0.5),
        "engine": response.get("engine", "unknown"),
        "llm_available": llm_engine.is_available()
    })


@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    """会話履歴をクリア"""
    session_id = request.headers.get("X-Session-ID", "default")
    
    if session_id in session_engines:
        session_engines[session_id].clear_history()
    
    return jsonify({"status": "ok"})


@app.route("/api/status")
def get_status():
    """システムステータス"""
    return jsonify({
        "llm_available": llm_engine.is_available(),
        "llm_model": llm_engine.model if llm_engine.is_available() else None,
        "attractions_count": len(kb.attractions),
        "version": "2.0.0"
    })


@app.route("/api/wait_times")
def get_wait_times():
    """待ち時間API"""
    park = request.args.get("park")  # "tdl" or "tds"
    
    wait_times = wait_time_service.get_wait_times(park)
    
    return jsonify({
        "wait_times": [
            {
                "id": wt.attraction_id,
                "name": wt.attraction_name,
                "wait_minutes": wt.wait_minutes,
                "is_operating": wt.is_operating,
                "is_realtime": wt.is_realtime,
                "source": wt.source
            }
            for wt in wait_times
        ],
        "updated_at": wait_time_service.cache_time.isoformat() if wait_time_service.cache_time else None
    })


@app.route("/api/wait_time/<attraction_name>")
def get_attraction_wait_time(attraction_name):
    """特定アトラクションの待ち時間"""
    wt = wait_time_service.get_wait_time(attraction_name)
    
    if wt:
        return jsonify({
            "id": wt.attraction_id,
            "name": wt.attraction_name,
            "wait_minutes": wt.wait_minutes,
            "is_operating": wt.is_operating,
            "is_realtime": wt.is_realtime,
            "source": wt.source
        })
    else:
        return jsonify({"error": "アトラクションが見つかりません"}), 404


@app.route("/api/hidden_mickeys")
def get_hidden_mickeys():
    """隠れミッキー情報を取得"""
    park = request.args.get("park")
    area = request.args.get("area")
    
    # 画像ありの隠れミッキー
    images = image_service.get_hidden_mickey_images(park, area)
    
    # 画像なしのプレースホルダーヒント
    placeholders = image_service.get_placeholder_hint_images()
    
    if park:
        placeholders = [p for p in placeholders if p["park"] == park]
    
    result = {
        "with_images": [
            {
                "id": img.id,
                "location": img.location,
                "description": img.description,
                "hint": img.hint,
                "difficulty": img.difficulty,
                "park": img.park,
                "image_url": image_service.get_image_url(img.id),
                "has_image": True
            }
            for img in images
        ],
        "without_images": placeholders
    }
    
    return jsonify(result)


@app.route("/api/hidden_mickey/<image_id>")
def get_hidden_mickey_detail(image_id):
    """隠れミッキー詳細を取得"""
    img = image_service.get_image(image_id)
    
    if img:
        return jsonify({
            "id": img.id,
            "location": img.location,
            "description": img.description,
            "hint": img.hint,
            "difficulty": img.difficulty,
            "park": img.park,
            "image_url": image_service.get_image_url(img.id),
            "tags": img.tags
        })
    else:
        return jsonify({"error": "見つかりません"}), 404


@app.route("/api/user/profile")
def get_user_profile():
    """ユーザープロファイルを取得"""
    session_id = request.headers.get("X-Session-ID", "default")
    summary = user_profile_service.get_profile_summary(session_id)
    return jsonify(summary)


@app.route("/api/user/preferences", methods=["POST"])
def update_user_preferences():
    """ユーザーの好みを更新"""
    session_id = request.headers.get("X-Session-ID", "default")
    data = request.get_json()
    
    profile = user_profile_service.update_preferences(session_id, data)
    
    return jsonify({
        "status": "ok",
        "preferences": {
            "favorite_park": profile.preferences.favorite_park,
            "thrill_preference": profile.preferences.thrill_preference,
            "has_children": profile.preferences.has_children,
            "favorite_characters": profile.preferences.favorite_characters,
            "food_preferences": profile.preferences.food_preferences
        }
    })


@app.route("/api/user/recommendations")
def get_recommendations():
    """パーソナライズされた推奨を取得"""
    session_id = request.headers.get("X-Session-ID", "default")
    
    recs = user_profile_service.get_personalized_recommendations(session_id, kb)
    
    return jsonify({
        "message": recs["message"],
        "attractions": [
            {
                "id": a["id"],
                "name": a["name"],
                "park": a["park"],
                "type": a.get("type", "")
            }
            for a in recs["attractions"][:5]
        ],
        "restaurants": [
            {
                "id": r.get("id", ""),
                "name": r["name"],
                "park": r["park"],
                "cuisine": r.get("cuisine", "")
            }
            for r in recs["restaurants"][:3]
        ]
    })


@app.route("/api/attractions")
def get_attractions():
    """アトラクション一覧を取得"""
    attractions = list(kb.attractions.values())
    return jsonify({
        "attractions": [
            {
                "id": a["id"],
                "name": a["name"],
                "park": a["park"],
                "type": a.get("type", ""),
                "area": a.get("area", "")
            }
            for a in attractions
        ]
    })


@app.route("/api/quick_actions")
def get_quick_actions():
    """クイックアクション一覧（カテゴリ別）"""
    return jsonify({
        "actions": [
            # 緊急・よく使う（最優先）
            {"label": "🚻 トイレ", "message": "近くのトイレを教えて", "category": "urgent", "priority": 1},
            {"label": "👶 ベビーセンター", "message": "ベビーセンターの場所", "category": "urgent", "priority": 2},
            {"label": "🏥 救護室", "message": "救護室の場所", "category": "urgent", "priority": 3},
            
            # 基本情報
            {"label": "🎢 アトラクション", "message": "人気のアトラクションを教えて", "category": "basic"},
            {"label": "🍽️ レストラン", "message": "おすすめのレストランを教えて", "category": "basic"},
            {"label": "📱 アプリの使い方", "message": "アプリの使い方を教えて", "category": "basic"},
            
            # プラン
            {"label": "📋 今日のプラン", "message": "今日のおすすめプランを教えて", "category": "plan"},
            
            # Tips
            {"label": "🗺️ 初心者ガイド", "message": "初心者向けのアドバイス", "category": "tips"},
            {"label": "🎒 今日の持ち物", "message": "今日の持ち物を教えて", "category": "tips"},
            {"label": "👕 今日の服装", "message": "今日の服装を教えて", "category": "tips"},
            
            # その他
            {"label": "🐭 隠れミッキー", "message": "隠れミッキーを教えて", "category": "fun"},
            {"label": "🗄️ ロッカー", "message": "ロッカーの場所", "category": "facility"},
            {"label": "👦 迷子センター", "message": "迷子センターの場所", "category": "urgent"},
        ]
    })


@app.route("/api/plan/generate", methods=["POST"])
def generate_plan():
    """プラン生成API"""
    data = request.get_json() or {}
    
    park = data.get("park", "tds")  # "tdl" or "tds"
    user_type = data.get("user_type", "beginner")
    date = data.get("date")  # YYYY-MM-DD形式、Noneなら今日
    custom_preferences = data.get("preferences", {})
    
    try:
        plan = plan_generator.generate_plan(
            park=park,
            user_type=user_type,
            custom_preferences=custom_preferences,
            date=date
        )
        
        return jsonify({
            "success": True,
            "plan": {
                "date": plan.date,
                "park": plan.park,
                "park_name": "ディズニーランド" if plan.park == "tdl" else "ディズニーシー",
                "user_type": user_type,
                "user_type_name": plan.user_preferences.get("name", ""),
                "items": [
                    {
                        "time": item.time,
                        "end_time": item.end_time,
                        "attraction": item.attraction,
                        "wait_minutes": item.wait_minutes,
                        "duration_minutes": item.duration_minutes,
                        "travel_minutes": item.travel_minutes,
                        "action_type": item.action_type,
                        "area": item.area,
                        "notes": item.notes
                    }
                    for item in plan.items
                ],
                "total_wait_minutes": plan.total_wait_minutes,
                "total_travel_minutes": plan.total_travel_minutes,
                "total_attractions": plan.total_attractions,
                "tips": plan.tips,
                "closed_attractions": plan.closed_attractions
            },
            "formatted_text": plan_generator.format_plan(plan)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/plan/user_types")
def get_plan_user_types():
    """利用可能なユーザータイプ一覧"""
    return jsonify({
        "user_types": plan_generator.get_available_user_types()
    })


@app.route("/api/closures")
def get_closures():
    """休止情報API"""
    park = request.args.get("park")  # "tdl" or "tds"
    date = request.args.get("date")  # YYYY-MM-DD
    
    closures = closure_service.get_closures(date)
    
    if park:
        closures = [c for c in closures if c.park == park]
    
    return jsonify({
        "closures": [
            {
                "attraction_name": c.attraction_name,
                "park": c.park,
                "start_date": c.start_date,
                "end_date": c.end_date,
                "reason": c.reason,
                "note": c.note
            }
            for c in closures
        ],
        "formatted_text": closure_service.format_closures(park, date)
    })


@app.route("/api/closures/refresh", methods=["POST"])
def refresh_closures():
    """休止情報を強制更新"""
    closures = closure_service.fetch_closures(force=True)
    
    return jsonify({
        "success": True,
        "count": len(closures),
        "message": f"休止情報を更新しました: {len(closures)}件"
    })


@app.route("/api/facilities")
def get_facilities():
    """施設情報APIエンドポイント"""
    park = request.args.get("park")  # "tdl" or "tds"
    facility_type = request.args.get("type")  # "restroom", "baby_center", "first_aid", etc.
    
    facilities_map = getattr(kb, 'facilities_map', {}).get("facilities", {})
    
    result = {}
    
    parks_to_check = []
    if park == "tdl":
        parks_to_check = [("tokyo_disney_land", "ディズニーランド")]
    elif park == "tds":
        parks_to_check = [("tokyo_disney_sea", "ディズニーシー")]
    else:
        parks_to_check = [("tokyo_disney_land", "ディズニーランド"), ("tokyo_disney_sea", "ディズニーシー")]
    
    for park_key, park_name in parks_to_check:
        park_data = facilities_map.get(park_key, {})
        
        if facility_type == "restroom" or not facility_type:
            restrooms = park_data.get("restrooms", [])
            result[park_key] = {
                "park_name": park_name,
                "restrooms": restrooms
            }
        
        if facility_type == "baby_center" or not facility_type:
            baby_center = park_data.get("baby_center", {})
            if park_key not in result:
                result[park_key] = {"park_name": park_name}
            result[park_key]["baby_center"] = baby_center
        
        if facility_type == "first_aid" or not facility_type:
            first_aid = park_data.get("first_aid", {})
            if park_key not in result:
                result[park_key] = {"park_name": park_name}
            result[park_key]["first_aid"] = first_aid
    
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

