import os
import json
import gzip
import base64
import time
import functools
from datetime import datetime
from supabase import create_client, Client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

# ---------------------------------------------------------
# Resilient Supabase Client (auto-reconnect on PGRST002)
# ---------------------------------------------------------
_supabase_client = None

def get_supabase() -> Client:
    """Get the Supabase client, creating/recreating as needed."""
    global _supabase_client
    if not url or not key:
        return None
    if _supabase_client is None:
        _supabase_client = create_client(url, key)
        print("[DB] Supabase client created")
    return _supabase_client

def _recreate_supabase():
    """Force-recreate the Supabase client (called on PGRST002 errors)."""
    global _supabase_client
    if url and key:
        _supabase_client = create_client(url, key)
        print("[DB] Supabase client RECREATED (connection recovery)")
    return _supabase_client

def _is_connection_error(error):
    """Check if an error is a PostgREST connection issue (PGRST002)."""
    error_str = str(error)
    return "PGRST002" in error_str or "schema cache" in error_str

def db_retry(max_retries=3, base_delay=1.0):
    """Decorator that retries DB operations with exponential backoff.
    
    On PGRST002 errors, also recreates the Supabase client.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if _is_connection_error(e):
                        delay = base_delay * (2 ** (attempt - 1))
                        print(f"[DB RETRY] PGRST002 detected in {func.__name__} "
                              f"(attempt {attempt}/{max_retries}), "
                              f"recreating client, retrying in {delay}s...")
                        _recreate_supabase()
                        time.sleep(delay)
                    else:
                        # Non-connection error, don't retry
                        raise
            # All retries exhausted
            raise last_error
        return wrapper
    return decorator

# Backward compatibility: keep 'supabase' as a module-level reference
supabase = get_supabase()

# ---------------------------------------------------------
# Phase 3: Transcript Compression Utilities
# ---------------------------------------------------------
def compress_transcript(transcript: list) -> str:
    """Compress transcript using gzip + base64 encoding.
    
    PHASE 3 OPTIMIZATION:
    - Reduces transcript size by 70-80%
    - Example: 100KB transcript → 15-20KB compressed
    - Transparent compression/decompression
    - All transcript reads/writes handled automatically
    """
    try:
        # Convert to JSON string
        json_str = json.dumps(transcript)
        
        # Compress with gzip
        compressed = gzip.compress(json_str.encode('utf-8'))
        
        # Encode to base64 for storage
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Calculate reduction ratio for logging
        original_size = len(json_str.encode('utf-8'))
        compressed_size = len(compressed)
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        print(f"[COMPRESSION] Transcript: {original_size}B → {compressed_size}B ({ratio:.1f}% reduction)")
        
        return encoded
    except Exception as e:
        print(f"[COMPRESSION] Error compressing transcript: {e}")
        # Fallback: return uncompressed JSON string
        return json.dumps(transcript)


def decompress_transcript(compressed) -> list:
    """Decompress transcript from gzip + base64.
    
    Automatically called when loading transcripts from database.
    Handles multiple formats:
    - JSON object with "_compressed" key (new format)
    - Raw base64-encoded gzip string (legacy format)
    - Raw JSON array (uncompressed fallback)
    """
    if not compressed:
        return []
    
    try:
        # Handle new JSON-wrapped compressed format
        if isinstance(compressed, dict) and "_compressed" in compressed:
            compressed = compressed["_compressed"]
        
        # If it's already a list (raw JSON from DB), return directly
        if isinstance(compressed, list):
            return compressed

        # If it looks like base64-encoded gzip, decompress
        if isinstance(compressed, str) and len(compressed) > 50:
            try:
                decoded = base64.b64decode(compressed.encode('utf-8'))
                decompressed = gzip.decompress(decoded)
                return json.loads(decompressed.decode('utf-8'))
            except:
                # If decompression fails, try parsing as raw JSON
                pass
        
        # Fallback: try parsing as raw JSON
        if isinstance(compressed, str):
            return json.loads(compressed)
        
        return compressed
    except Exception as e:
        print(f"[COMPRESSION] Error decompressing transcript: {e}")
        return []

@db_retry(max_retries=3, base_delay=1.0)
def save_session_to_db(session_data):
    client = get_supabase()
    if not client: return False
    
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

        # PHASE 3: Compress transcript for storage (70-80% size reduction)
        transcript_original = session_data.get("transcript", [])
        transcript_compressed = compress_transcript(transcript_original)
        # Wrap compressed string in a JSON object for JSONB column compatibility
        transcript_jsonb = {"_compressed": transcript_compressed}

        # Ensure framework is a proper JSON value for JSONB column (not a double-serialized string)
        if isinstance(framework_val, str):
            try:
                framework_val = json.loads(framework_val)
            except (json.JSONDecodeError, TypeError):
                pass  # keep as string if not valid JSON

        data_to_insert = {
            "session_id": session_id,
            "user_id": str(user_id),
            "scenario_type": session_data.get("scenario_type", "custom"),
            "session_mode": session_data.get("session_mode"),
            "title": session_data.get("title"),
            "ai_character": session_data.get("ai_character", "alex"),
            "mode": session_data.get("mode"),
            "role": session_data.get("role"),
            "ai_role": session_data.get("ai_role"),
            "scenario": session_data.get("scenario"),
            "framework": framework_val,
            "transcript": transcript_jsonb,  # Store compressed transcript as JSON object
            "report_data": report_data_val,
            "completed": session_data.get("completed", False),
            "created_at": session_data.get("created_at"),
            "updated_at": datetime.now().isoformat()
        }
        
        # Extract score from overall_grade (e.g., "7/10" -> 7.0)
        score = None
        if report_data_val and "meta" in report_data_val:
            grade_str = report_data_val["meta"].get("overall_grade", "")
            if grade_str and "/" in str(grade_str):
                try:
                    score = float(str(grade_str).split("/")[0].strip())
                except (ValueError, IndexError):
                    score = None
        data_to_insert["score"] = score
        
        # Upsert the session record in practice_history
        # The schema uses session_id as the primary key
        res = client.table("practice_history").upsert(data_to_insert).execute()
        print(f"[SUCCESS] Saved session {session_id} to database.")
        return True
    except Exception as e:
        print(f"[ERROR] DB Save failed for {session_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

@db_retry(max_retries=3, base_delay=1.0)
def get_session_from_db(session_id):
    client = get_supabase()
    if not client: return None
    try:
        res = client.table("practice_history").select("*").eq("session_id", session_id).execute()
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
                "transcript": decompress_transcript(row.get("transcript", [])),  # Decompress on load
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

@db_retry(max_retries=3, base_delay=1.0)
def get_user_sessions_from_db(user_id, limit=20, offset=0, completed_only=False):
    """Get paginated sessions for user.
    
    OPTIMIZATION: Only fetches limit items instead of all sessions.
    This prevents large payloads and slow page loads for power users.
    When completed_only=True, returns only sessions with completed=True (has final report).
    """
    client = get_supabase()
    if not client: 
        return {"sessions": [], "total": 0, "limit": limit, "offset": offset}
    try:
        # Fetch with pagination using range()
        # count="exact" gives us the total count
        query = client.table("practice_history")\
            .select("session_id, user_id, scenario_type, session_mode, title, ai_character, mode, role, ai_role, scenario, framework, completed, created_at, score", count="exact")\
            .eq("user_id", user_id)
        
        if completed_only:
            query = query.eq("completed", True)
        
        res = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
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
                "completed": row.get("completed", False),
                "created_at": row.get("created_at"),
                "score": row.get("score")
            })
        
        return {
            "sessions": sessions,
            "total": res.count or 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        print(f"[ERROR] DB Fetch Sessions failed for user {user_id}: {e}")
        return {"sessions": [], "total": 0, "limit": limit, "offset": offset}

@db_retry(max_retries=3, base_delay=1.0)
def clear_user_sessions_from_db(user_id):
    client = get_supabase()
    if not client: return False
    try:
        res = client.table("practice_history").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"[ERROR] DB Delete Sessions failed for user {user_id}: {e}")
        return False
