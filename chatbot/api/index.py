"""
Vercel Serverless Function - Disney Chatbot
"""
import os
import sys

# プロジェクトのルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import Flask, render_template, request, jsonify
import json
from pathlib import Path

# Vercel環境ではテンプレートとデータのパスを調整
template_folder = os.path.join(project_root, 'templates')
static_folder = os.path.join(project_root, 'static')
data_folder = os.path.join(project_root, 'data')

app = Flask(__name__, 
            template_folder=template_folder,
            static_folder=static_folder)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "disney-chatbot-vercel-key")

# チャットボット関連のインポート
try:
    from chatbot import DisneyChatbot, DisneyKnowledgeBase
    from llm_engine import DisneyLLMEngine, HybridChatEngine
    from wait_time_service import WaitTimeService
    from image_service import ImageService
    from user_profile_service import UserProfileService
    from plan_generator import PlanGeneratorService
    from closure_service import ClosureService
    
    # チャットボットの初期化
    kb = DisneyKnowledgeBase(data_dir=data_folder)
    bot = DisneyChatbot(kb)
    llm_engine = DisneyLLMEngine()
    hybrid_engine = HybridChatEngine(kb, llm_engine)
    wait_time_service = WaitTimeService()
    image_service = ImageService()
    user_profile_service = UserProfileService(data_dir=os.path.join(data_folder, 'users'))
    plan_generator = PlanGeneratorService(data_dir=data_folder)
    closure_service = ClosureService(data_dir=data_folder)
    
    SERVICES_LOADED = True
except Exception as e:
    print(f"Warning: Some services failed to load: {e}")
    SERVICES_LOADED = False
    kb = None
    hybrid_engine = None
    llm_engine = None

# セッション別のエンジンを管理（Vercelはステートレスなので簡易版）
session_engines = {}


@app.route("/")
def index():
    """メインページ"""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """チャットAPI"""
    if not SERVICES_LOADED:
        return jsonify({"error": "サービスが初期化されていません"}), 500
    
    data = request.get_json()
    message = data.get("message", "")
    use_llm = data.get("use_llm", True)
    
    if not message:
        return jsonify({"error": "メッセージを入力してください"}), 400
    
    session_id = request.headers.get("X-Session-ID", "default")
    
    # ハイブリッドエンジンで応答を生成
    try:
        response = hybrid_engine.chat(message, force_llm=(use_llm and llm_engine.is_available()))
    except Exception as e:
        response = {"message": f"エラーが発生しました: {str(e)}", "category": "error", "confidence": 0}
    
    return jsonify({
        "message": response.get("message", ""),
        "category": response.get("category", "unknown"),
        "confidence": response.get("confidence", 0.5),
        "engine": response.get("engine", "unknown"),
        "llm_available": llm_engine.is_available() if llm_engine else False
    })


@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    """会話履歴をクリア"""
    return jsonify({"status": "ok"})


@app.route("/api/status")
def get_status():
    """システムステータス"""
    return jsonify({
        "llm_available": llm_engine.is_available() if llm_engine else False,
        "llm_model": llm_engine.model if llm_engine and llm_engine.is_available() else None,
        "attractions_count": len(kb.attractions) if kb else 0,
        "version": "2.0.0-vercel",
        "services_loaded": SERVICES_LOADED
    })


@app.route("/api/wait_times")
def get_wait_times():
    """待ち時間API"""
    if not SERVICES_LOADED:
        return jsonify({"wait_times": [], "updated_at": None})
    
    park = request.args.get("park")
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


@app.route("/api/quick_actions")
def get_quick_actions():
    """クイックアクション一覧"""
    return jsonify({
        "actions": [
            {"label": "🚻 トイレ", "message": "近くのトイレを教えて", "category": "urgent", "priority": 1},
            {"label": "👶 ベビーセンター", "message": "ベビーセンターの場所", "category": "urgent", "priority": 2},
            {"label": "🏥 救護室", "message": "救護室の場所", "category": "urgent", "priority": 3},
            {"label": "🎢 アトラクション", "message": "人気のアトラクションを教えて", "category": "basic"},
            {"label": "🍽️ レストラン", "message": "おすすめのレストランを教えて", "category": "basic"},
            {"label": "📱 アプリの使い方", "message": "アプリの使い方を教えて", "category": "basic"},
            {"label": "📋 今日のプラン", "message": "今日のおすすめプランを教えて", "category": "plan"},
            {"label": "🗺️ 初心者ガイド", "message": "初心者向けのアドバイス", "category": "tips"},
            {"label": "🎒 今日の持ち物", "message": "今日の持ち物を教えて", "category": "tips"},
            {"label": "👕 今日の服装", "message": "今日の服装を教えて", "category": "tips"},
            {"label": "🐭 隠れミッキー", "message": "隠れミッキーを教えて", "category": "fun"},
            {"label": "🗄️ ロッカー", "message": "ロッカーの場所", "category": "facility"},
            {"label": "👦 迷子センター", "message": "迷子センターの場所", "category": "urgent"},
        ]
    })


@app.route("/api/plan/generate", methods=["POST"])
def generate_plan():
    """プラン生成API"""
    if not SERVICES_LOADED:
        return jsonify({"success": False, "error": "サービスが初期化されていません"}), 500
    
    data = request.get_json() or {}
    
    park = data.get("park", "tds")
    user_type = data.get("user_type", "beginner")
    date = data.get("date")
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
    if not SERVICES_LOADED:
        return jsonify({"user_types": []})
    
    return jsonify({
        "user_types": plan_generator.get_available_user_types()
    })


@app.route("/api/closures")
def get_closures():
    """休止情報API"""
    if not SERVICES_LOADED:
        return jsonify({"closures": [], "formatted_text": ""})
    
    park = request.args.get("park")
    date = request.args.get("date")
    
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


@app.route("/api/facilities")
def get_facilities():
    """施設情報APIエンドポイント"""
    if not SERVICES_LOADED or not kb:
        return jsonify({})
    
    park = request.args.get("park")
    facility_type = request.args.get("type")
    
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
            result[park_key] = {"park_name": park_name, "restrooms": restrooms}
        
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


# Vercel用のハンドラー
def handler(request):
    """Vercel serverless handler"""
    return app(request)


# ローカル開発用
if __name__ == "__main__":
    app.run(debug=True, port=5000)

