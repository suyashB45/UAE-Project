import os
import json
from datetime import datetime
from supabase import create_client, Client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key) if url and key else None

def save_session_to_db(session_data):
    if not supabase: return False
    
    session_id = session_data.get("id")
    user_id = session_data.get("user_id")
    
    if not session_id or not user_id:
        # Expected for guest sessions; do not print an error/warning
        return False
        
    try:
        # Avoid json serialization issues for Postgres JSONB framework column
        framework_val = session_data.get("framework")
        if isinstance(framework_val, list):
            framework_val = json.dumps(framework_val)

        report_data_val = session_data.get("report_data", {})
        if not report_data_val:
            report_data_val = {}

        data_to_insert = {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_type": session_data.get("scenario_type", "custom"),
            "session_mode": session_data.get("session_mode"),
            "title": session_data.get("title"),
            "ai_character": session_data.get("ai_character", "alex"),
            "mode": session_data.get("mode"),
            "role": session_data.get("role"),
            "ai_role": session_data.get("ai_role"),
            "scenario": session_data.get("scenario"),
            "framework": framework_val,
            "transcript": session_data.get("transcript", []),
            "report_data": report_data_val,
            "completed": session_data.get("completed", False),
            "created_at": session_data.get("created_at"),
            "updated_at": datetime.now().isoformat()
        }
        
        # We need to extract the score manually
        score = None
        if report_data_val and "meta" in report_data_val:
            score = report_data_val["meta"].get("fit_score")
        data_to_insert["score"] = score
        
        # Upsert the session record in practice_history
        # The schema uses session_id as the primary key
        res = supabase.table("practice_history").upsert(data_to_insert).execute()
        print(f"[SUCCESS] Saved session {session_id} to database.")
        return True
    except Exception as e:
        print(f"[ERROR] DB Save failed for {session_id}: {e}")
        return False

def get_session_from_db(session_id):
    if not supabase: return None
    try:
        res = supabase.table("practice_history").select("*").eq("session_id", session_id).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            # Convert DB row format back to in-memory format
            session_data = {
                "id": row.get("session_id"),
                "user_id": row.get("user_id"),
                "scenario_type": row.get("scenario_type"),
                "session_mode": row.get("session_mode"),
                "title": row.get("title"),
                "ai_character": row.get("ai_character", "alex"),
                "mode": row.get("mode"),
                "role": row.get("role"),
                "ai_role": row.get("ai_role"),
                "scenario": row.get("scenario"),
                "framework": row.get("framework"),
                "transcript": row.get("transcript", []),
                "report_data": row.get("report_data", {}),
                "completed": row.get("completed", False),
                "created_at": row.get("created_at"),
                "score": row.get("score")
            }
            return session_data
        return None
    except Exception as e:
        print(f"[ERROR] DB Fetch failed for {session_id}: {e}")
        return None

def get_user_sessions_from_db(user_id):
    if not supabase: return []
    try:
        res = supabase.table("practice_history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        sessions = []
        for row in res.data:
            sessions.append({
                "id": row.get("session_id"),
                "user_id": row.get("user_id"),
                "scenario_type": row.get("scenario_type"),
                "session_mode": row.get("session_mode"),
                "title": row.get("title"),
                "ai_character": row.get("ai_character", "alex"),
                "mode": row.get("mode"),
                "role": row.get("role"),
                "ai_role": row.get("ai_role"),
                "scenario": row.get("scenario"),
                "framework": row.get("framework"),
                "transcript": row.get("transcript", []),
                "report_data": row.get("report_data", {}),
                "completed": row.get("completed", False),
                "created_at": row.get("created_at"),
                "score": row.get("score")
            })
        return sessions
    except Exception as e:
        print(f"[ERROR] DB Fetch Sessions failed for user {user_id}: {e}")
        return []

def clear_user_sessions_from_db(user_id):
    if not supabase: return False
    try:
        res = supabase.table("practice_history").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"[ERROR] DB Delete Sessions failed for user {user_id}: {e}")
        return False
