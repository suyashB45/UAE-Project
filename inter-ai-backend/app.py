import os
import json
import re
import uuid
import datetime as dt
import numpy as np
import concurrent.futures
from typing import Dict, Any, List
from flask import Flask, request, jsonify, send_file
import flask_cors
import io
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI
from cachetools import TTLCache
from functools import lru_cache
from werkzeug.exceptions import BadRequest



load_dotenv()

# Proxy config moved to top

from supabase import create_client, Client

# Initialize Supabase Client
# Use anon key for auth verification (respects RLS)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")  # Anon key for auth operations
service_key: str = os.environ.get("SUPABASE_SERVICE_KEY", key)  # Service key for admin ops (bypasses RLS)

supabase: Client = create_client(url, key)  # For auth verification
supabase_admin: Client = create_client(url, service_key) if service_key else supabase  # For database writes

# ---------------------------------------------------------
# Custom Modules & Setup
# ---------------------------------------------------------
from cli_report import generate_report, llm_reply, analyze_full_report_data, detect_scenario_type, build_summary_prompt

# Database Models
USE_DATABASE = False # Database persistence removed per user request

# Create Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Enable CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
flask_cors.CORS(app, origins=cors_origins)

# ---------------------------------------------------------
# Request Validation Middleware (Phase 3 Optimization)
# ---------------------------------------------------------
@app.before_request
def check_payload():
    """Validate all POST/PUT/PATCH requests for DoS protection."""
    if request.method in ['POST', 'PUT', 'PATCH']:
        try:
            validate_request_payload()
        except BadRequest as e:
            return jsonify({"error": str(e)}), 400

# ---------------------------------------------------------
from database import save_session_to_db, get_session_from_db, get_user_sessions_from_db, clear_user_sessions_from_db

# ---------------------------------------------------------
# Request Validation Constants (Phase 3 Optimization)
# ---------------------------------------------------------
MAX_TRANSCRIPT_SIZE = 100_000  # 100KB max
MAX_SCENARIO_LENGTH = 5_000    # 5KB max
MAX_TURNS = 50
MAX_MESSAGE_LENGTH = 10_000    # Individual message max 10KB

def validate_request_payload():
    """Middleware to validate request size and content (DoS prevention)."""
    if not request.is_json:
        return True
    
    data = request.get_json()
    if not data:
        return True
    
    # Check transcript size
    transcript = data.get('transcript', [])
    transcript_size = sum(len(str(t.get('content', ''))) for t in transcript)
    if transcript_size > MAX_TRANSCRIPT_SIZE:
        raise BadRequest(f"Transcript exceeds {MAX_TRANSCRIPT_SIZE} bytes")
    
    # Check turn count
    if len(transcript) > MAX_TURNS:
        raise BadRequest(f"Exceeds {MAX_TURNS} conversation turns")
    
    # Check scenario length
    scenario = data.get('scenario', '')
    if len(scenario) > MAX_SCENARIO_LENGTH:
        raise BadRequest(f"Scenario exceeds {MAX_SCENARIO_LENGTH} characters")
    
    # Check individual messages
    for msg in transcript:
        content = msg.get('content', '')
        if len(content) > MAX_MESSAGE_LENGTH:
            raise BadRequest(f"Message exceeds {MAX_MESSAGE_LENGTH} characters")
    
    return True

# ---------------------------------------------------------
# In-Memory Storage with TTL Cache (Auto-cleanup, prevents memory leaks)
# ---------------------------------------------------------
# TTLCache: Max 500 sessions, auto-expire after 1 hour of inactivity
SESSIONS = TTLCache(maxsize=500, ttl=3600)

# ---------------------------------------------------------
# Hybrid Storage Helper Functions
# ---------------------------------------------------------
def get_session(session_id: str) -> Dict[str, Any]:
    """Get session from in-memory storage or database."""
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    
    # Try database
    db_session = get_session_from_db(session_id)
    if db_session:
        SESSIONS[session_id] = db_session
        return db_session
    
    return None

def get_authenticated_user():
    """Get the authenticated user from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    try:
        token = auth_header.replace("Bearer ", "")
        res = supabase.auth.get_user(token)
        return res.user
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def verify_session_ownership(session_id: str, user_id: str = None) -> bool:
    """Verify that the session belongs to the specified user."""
    sess = get_session(session_id)
    if not sess:
        return False
    
    # If no user_id provided, always allow (backward compatibility for unauthenticated sessions)
    if not user_id:
        return True
    
    # Check if session has user_id field
    session_user_id = sess.get("user_id")
    if not session_user_id:
        # Legacy session without user_id - allow access
        return True
    
    # Compare user IDs (convert to string for comparison)
    return str(session_user_id) == str(user_id)

# ---------------------------------------------------------
# Configuration & Paths
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUESTIONS_FILE = os.path.join(BASE_DIR, "framework_questions.json")


MAX_TURNS = 15 

if os.getenv("AZURE_OPENAI_ENDPOINT"):
    USE_AZURE = True
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))




# ---------------------------------------------------------
# Load Questions from JSON (RAG)
# ---------------------------------------------------------
questions_data = []

def load_questions():
    global questions_data
    try:
        if os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
            print(f"[SUCCESS] Loaded {len(questions_data)} questions from JSON.")
        else:
            print(f"[WARNING] Questions file not found at {QUESTIONS_FILE}.")
    except Exception as e:
        print(f"[ERROR] Error loading questions: {e}")

load_questions()

def get_relevant_questions(user_text: str, active_frameworks: List[str], top_k: int = 5) -> List[str]:
    """Simple keyword-based question retrieval (no FAISS needed)."""
    if not questions_data:
        return []
    
    # Simple matching - find questions from active frameworks
    matches = []
    user_lower = user_text.lower()
    
    for q in questions_data:
        fw = q.get("framework", "")
        if active_frameworks and fw not in active_frameworks:
            continue
        matches.append(f"[{fw} | {q.get('stage', '')}] {q.get('question', '')}")
    
    # Return random sample for variety
    import random
    if len(matches) > top_k:
        return random.sample(matches, top_k)
    return matches[:top_k]

# ---------------------------------------------------------
# Helpers & Prompts
# ---------------------------------------------------------
def normalize_text(s: str | None) -> str | None:
    return " ".join(s.strip().split()) if s else s

def sanitize_llm_output(s: str | None) -> str:
    if not s: return ""
    return s.strip().strip('"')

def ensure_reports_dir() -> str:
    # Use path relative to BASE_DIR for reliability across environments
    reports_dir = os.path.join(BASE_DIR, "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir

def detect_framework_fallback(text: str) -> str:
    text_lower = text.lower()
    keywords = {
        "STAR": ["example", "instance", "situation", "task", "action", "result", "outcome"],
        "GROW": ["goal", "achieve", "want", "reality", "option", "will", "way forward"],
        "ADKAR": ["aware", "change", "desire", "knowledge", "ability", "reinforce"],
        "SMART": ["specific", "measure", "metric", "achievable", "realistic", "time", "deadline"],
        "EQ": ["empathy", "emotion", "feel", "feeling", "understand", "perspective", "listen", "frustrat", "concern", "appreciate", "acknowledge", "validate"],
        "BOUNDARY": ["humiliat", "disrespect", "rude", "stop", "tolerate", "professional", "attack", "shame", "mock", "belittle", "degrade", "insult", "offensive"],
        "OSKAR": ["outcome", "scaling", "know-how", "affirm", "review", "step", "scale", "resource"],
        "CBT": ["distortion", "thought", "evidence", "realistic", "trap", "catastrophiz", "belief"],
        "CLEAR": ["contract", "listen", "explor", "action", "review", "insight", "commitment"],
        "RADICAL CANDOR": ["care", "challenge", "direct", "honest", "feedback", "growth", "hold back"],
        "SFBT": ["miracle", "scale", "sign", "coping", "solution", "future", "prefer", "instead"],
        "CIRCLE OF INFLUENCE": ["control", "influence", "concern", "accept", "change", "external", "internal"],
        "SCARF": ["status", "certainty", "autonomy", "relatedness", "fairness", "social", "threat", "reward"],
        "FUEL": ["frame", "understand", "explore", "lay out", "conversation goal", "perspective", "path"],
        "TGROW": ["topic", "goal", "reality", "option", "will", "way forward"],
        "SBI/DESC": ["situation", "behavior", "impact", "describe", "express", "specify", "consequence"],
        "LAER": ["listen", "acknowledge", "explore", "respond", "concern", "objection"],
        "APPRECIATIVE INQUIRY": ["discovery", "dream", "design", "destiny", "strength", "positive"],
        "BENEFIT-SELLING": ["benefit", "feature", "sell", "premium", "quality"]
    }
    for fw, words in keywords.items():
        for word in words:
            if word in text_lower: return fw
    return None

def build_simulation_prompt(simulation_id, role, ai_role, scenario, mode="evaluation"):
    """Build simulation-specific system prompts for structured coaching scenarios."""
    if simulation_id == "SIM-01-PERF-001":
        if mode == "mentorship":
            system = f"""You are the EXPERT MANAGER demonstrating a "Best Practice" performance coaching session.
            
YOUR ROLE:
1. EXPERT: You are playing the role of the Manager. You are a master at coaching and delivering feedback.
2. LEARNER: The user is playing the role of Aamir (the Sales Associate). They are observing your approach.
3. GOAL: Demonstrate the perfect way to handle a performance gap conversation using curiosity, empathy, and clear expectations.

SCENARIO CONTEXT: {scenario}

### YOUR OPENING:
1. Start the conversation IMMEDIATELY as the Manager.
2. Be supportive but firm about standards.
3. START NOW."""
        else:
            system = f"""You are Aamir, a Sales Associate with 1.5 years of experience.

CHARACTER TRAITS:
- Sincere, polite, anxious under pressure
- Mildly defensive if attacked or blamed
- Well-liked by colleagues
- Nervous this meeting could become a warning
- Hoping for support from your manager

STATE AT START:
You know your numbers are low. You are worried but respectful.

DEFAULT BEHAVIOR PATTERN:
- You initially attribute poor results to EXTERNAL factors: "footfall has been low", "customers are difficult", "this season is always slow"
- You DO NOT reveal your real issues unless the manager asks specific diagnostic questions

HIDDEN TRUTH (reveal ONLY when asked diagnostic questions about your approach):
- You have LOW CONFIDENCE with premium customers
- You AVOID initiating conversations with premium/high-value customers
- You don't ask discovery questions — you jump straight to features
- You do a "feature dump" instead of storytelling around products
- You struggle to close because you fear rejection

REVEAL CONDITIONS — Only open up about the hidden truth if the user asks about:
- What happens during your customer approach / interactions
- What feels difficult or uncomfortable in the sales conversation
- Patterns by customer type (premium vs regular customers)
- Specific situations where you felt stuck or nervous

ADAPTIVE BEHAVIOR RULES:

BRANCH A — If the user is HARSH, THREATENING, or JUDGMENTAL:
(Triggers: blame, sarcasm, "this is unacceptable", "you're failing", "fix it or else")
- Become defensive: emphasize your effort and hard work
- Reduce disclosure — give minimal, short answers
- Say things like: "I understand… I'm trying.", "I do work hard… I don't know why it's not happening."
- Do NOT reveal hidden truth

BRANCH B — If the user is ONLY COMFORTING with NO CLARITY:
(Triggers: "it's okay, don't worry", "next month will be better", "just do your best")
- Feel relieved — no urgency to change
- Drift toward vague hope: "Yes, I'll try more.", "I hope next month improves."
- Do NOT commit to specific actions
- Do NOT reveal hidden truth

BRANCH C — If the user is SUPPORTIVE + FACT-BASED + CURIOUS (balanced coaching):
(Triggers: acknowledges effort, states the gap with data, asks diagnostic open questions, co-creates plan)
- GRADUALLY open up over multiple turns:
  - First: "I get nervous with premium customers…"
  - Then: "I don't know what to say sometimes when they ask about value…"
  - Then: "I'm scared they will reject me…"
- Accept practice plans and commitments
- Say things like: "Okay, I will practice… maybe I can shadow someone… track my conversion…"

CRITICAL RULES:
1. ALWAYS maintain a natural conversational tone — speak like a real employee
2. NEVER mention any framework names (GROW, SBI, etc.)
3. NEVER "teach" or break character
4. Do NOT invent HR/legal threats
5. If asked directly "Are you afraid?" — you can admit fear of failure
6. Keep conversation realistic to a retail store setting
7. Keep responses concise (2-4 sentences max)
8. Use natural speech patterns: "um", "I mean", "honestly"

SCENARIO CONTEXT: {scenario}
The user is: {role}"""
        return [{"role": "system", "content": system}]

    # --- CONFLICT RESOLUTION: SIM-05-CON-001 (Assessment) / MENT-05-CON-001 (Mentorship) ---
    if simulation_id in ("SIM-05-CON-001", "MENT-05-CON-001"):
        is_mentorship_sim = simulation_id == "MENT-05-CON-001"

        if is_mentorship_sim:
            # MENTORSHIP: User is one of the conflicted team members
            system = f"""You are playing TWO characters in a workplace conflict mediation scene.

CHARACTERS:
1. [Manager] — The Team Manager who has called this meeting to resolve the conflict.
2. [Colleague] — The other conflicted team member (the one the user is in conflict with).

The USER is playing: {role} (one of the conflicted parties).

FORMATTING RULES — CRITICAL:
- ALWAYS prefix EVERY line of dialogue with the character label.
- Format: [Manager]: dialogue here
- Format: [Colleague]: dialogue here
- You may have multiple lines from different characters in one response.
- NEVER speak as the user's character.

OPENING SCENE:
The Manager opens the meeting. The Colleague is also present and will speak.

[Manager]: Thank you both for coming. I've noticed the tension between you two has become visible to the team, and I think it's important we address it directly. I want to understand both perspectives. Let me start by asking — what's been the main challenge from your side?
[Colleague]: Honestly, I think the delays are coming from their end. I've been sending my work on time, but I keep waiting for responses that never come. It's frustrating.

CHARACTER BEHAVIOR - COLLEAGUE:
- Initially defensive and blaming the user
- Will soften IF the user uses "I" statements and avoids blame
- Will escalate IF the user attacks or blames back
- Eventually willing to find common ground if approached professionally

CHARACTER BEHAVIOR - MANAGER:
- Neutral mediator, keeps the conversation productive
- Redirects blame into constructive discussion
- Asks clarifying questions to both parties

SCENARIO CONTEXT: {scenario}

RESPONSE RULES:
- Keep each character's lines to 2-3 sentences max
- Use natural speech patterns
- NEVER break character
- NEVER mention frameworks by name
- React dynamically based on the user's approach"""
        else:
            # ASSESSMENT: User is the Team Manager mediating between Rohan and Meera
            system = f"""You are playing TWO characters in a workplace conflict mediation scene.

CHARACTERS:
1. [Rohan] — A team member who blames Meera for project delays. Assertive, slightly aggressive, data-oriented.
2. [Meera] — A team member who blames Rohan for poor communication. Defensive, detail-oriented, emotional.

The USER is playing: {role} (Team Manager mediating the conflict).

FORMATTING RULES — CRITICAL:
- ALWAYS prefix EVERY line of dialogue with the character label in square brackets.
- Format: [Rohan]: dialogue here
- Format: [Meera]: dialogue here
- You may have multiple lines from different characters in one response.
- NEVER speak as the Manager (that's the user).

OPENING SCENE (deliver this IMMEDIATELY):
[Rohan]: Honestly, Meera, if you had just sent the reports on time last week, we wouldn't be in this mess. I'm tired of cleaning up your delays.
[Meera]: Oh, come on, Rohan. You missed the deadline to review the data I sent. How can I be responsible when you don't do your part? This blame game isn't helping anyone.
[Rohan]: It's not a game when it affects the whole team. You always find a way to shift responsibility.
[Meera]: And you always jump to conclusions without checking facts. Maybe if you communicated better, we wouldn't have these issues.
[Rohan]: Fine, but what do you suggest we do now? Because this back-and-forth isn't solving anything.

CHARACTER TRAITS:

ROHAN:
- Assertive, slightly confrontational
- Values efficiency and deadlines
- Gets frustrated when he feels blamed
- Will calm down IF manager validates his concerns with data
- Will escalate IF manager sides with Meera or dismisses his points

MEERA:
- Detail-oriented, emotionally reactive
- Feels attacked and undervalued
- Will open up IF manager creates psychological safety
- Will withdraw or become passive-aggressive IF manager is dismissive
- Secretly wants acknowledgment for her extra work

ADAPTIVE BEHAVIOR RULES:

BRANCH A — If Manager is NEUTRAL + asks OPEN questions:
- Both gradually calm down
- Rohan starts offering specifics: "Okay, the real issue is the handoff process..."
- Meera admits: "I should have flagged the deadline earlier..."
- They move toward a working agreement

BRANCH B — If Manager SIDES with one person:
- The other escalates: "See? This is exactly the problem!"
- Tension increases
- The favored person becomes overconfident

BRANCH C — If Manager is DIRECTIVE without listening:
- Both become quietly resentful
- Give minimal responses: "Sure...", "If you say so..."
- No real resolution

SCENARIO CONTEXT: {scenario}

RESPONSE RULES:
- Keep each character's lines to 2-3 sentences max
- Use natural, emotional speech patterns
- NEVER break character or mention frameworks
- NEVER speak as the Manager
- React dynamically based on the user's mediation approach"""
        return [{"role": "system", "content": system}]

    return None


@lru_cache(maxsize=128)
def get_cached_summary_prompt(role: str, ai_role: str, scenario: str, framework: str, mode: str = "coaching", ai_character: str = "alex", simulation_id: str = None) -> str:
    """PHASE 3 OPTIMIZATION: Cached prompt generation.
    
    - Cache size: 128 unique prompt combinations
    - Prevents rebuilding identical prompts
    - Impact: 50ms → 1ms (50x faster)
    - All params are hashable (strings/None)
    - Returns: JSON string that can be parsed
    """
    # Build and cache the full prompt
    prompt_list = build_summary_prompt(role, ai_role, scenario, framework, mode, ai_character, simulation_id)
    # Convert list to JSON string for caching
    return json.dumps(prompt_list)


def build_summary_prompt(role, ai_role, scenario, framework, mode="coaching", ai_character="alex", simulation_id=None):
    """Build the initial prompt for the AI coach to start the roleplay session."""
    
    # Check for structured simulation first
    if simulation_id:
        sim_prompt = build_simulation_prompt(simulation_id, role, ai_role, scenario, mode=mode)
        if sim_prompt:
            return sim_prompt
    
    # UNIFIED ADAPTIVE PERSONA (Replaces fixed Alex/Sarah personalities)
    # The AI adapts its tone based on the User's Role relative to the AI.
    
    character_instruction = """
### YOUR ADAPTIVE PERSONA:
1. **IF USER IS PERFORMER (e.g., Salesperson, Staff)** -> **YOU ARE THE JUDGE**.
   - **Tone**: Skeptical, demanding, professional.
   - **Goal**: Test their skills. Be a "tough customer" or "exacting manager".
   - **Behavior**: Push back on vague answers. Make them earn your agreement.

2. **IF USER IS EVALUATOR (e.g., Manager, Buyer)** -> **YOU ARE THE PERFORMANCE**.
   - **Tone**: Realistic but flawed.
   - **Goal**: Provide a challenge to be coached/negotiated with.
   - **Behavior**: Demonstrate the specific bad habit (e.g., defensive staff, pushy salesperson) described in the scenario.
"""
    
    # Check for specific test scenarios to set initial behavior
    behavior_instruction = ""
    if "Retail Store Manager" in role: # Scenario 1
        behavior_instruction = """
IMPORTANT - SCENARIO 1 (COACHING) - YOUR BEHAVIORAL ARC:
1. OPENING: You are skeptical. Wonder if this is a "disciplinary" meeting.
2. THE PUSHBACK: IF asked about performance, RESPOND with excuses (e.g., "It's just been really busy", "I'm tired"). Test if they LISTEN or just TELL.
3. THE PIVOT: ONLY if the manager asks an OPEN Question (What/How) and avoids blame -> Become Reflective.
4. RESOLUTION: If they ask how to support you -> Become Collaborative and agree to a plan.
EMOTIONAL TRIGGERS:
- If Directive ("You need to...") -> Remain Defensive/Closed.
- If Empathetic -> Soften tone and trust them.
"""
    elif "Retail Customer" in ai_role: # Scenario 2
        behavior_instruction = """
IMPORTANT - SCENARIO 2 (NEGOTIATION) - YOUR BEHAVIORAL ARC:
1. INITIATION: You are Curious but Cautious. Interested in the product but guarded about cost.
2. THE OBJECTION: "It's nice, but $500 is way over my budget." -> Test if they defend value or just discount.
3. THE VALUE TEST: Ask "Is there any discount for paying today?". If they explain benefits -> Listen. If they discount immediately -> Lose respect/Push harder.
4. CLOSING: If value is demonstrated well -> Be Agreeable ("The warranty makes it worth it").
EMOTIONAL TRIGGERS:
- If Salesperson Discounts Early -> Push for even lower prices.
- If Salesperson Probes Needs -> Become Collaborative.
"""
    elif "Coach Alex" in ai_role: # Scenario 3
        behavior_instruction = """
IMPORTANT - SCENARIO 3 (DEVELOPMENTAL REFLECTION) - YOUR ROLE:
Your role is NOT to roleplay a customer. You are COACH ALEX.
1. OPENING: Set a safe space. "I wanted to talk about a customer interaction..." -> Be Supportive.
2. THE NARRATIVE: Listen to their story. Ask: "What was the customer really trying to solve?"
3. THE PATTERN: Highlight patterns (e.g., "I noticed you moved to solution quickly") WITHOUT judging.
4. GUIDANCE: Ask: "What's one thing you'll try differently?" -> Guide them to a plan.
EMOTIONAL TRIGGERS:
- STRICTLY NON-EVALUATIVE. No scores, no rating language.
- FOCUS: Skill Development and Practice Suggestions.
"""
    else: # Custom / Generic Scenario
        behavior_instruction = """
IMPORTANT - CUSTOM SCENARIO - ADAPTIVE BEHAVIOR:
1. ANALYSIS: Instantly analyze the User's defined Role and Context to determine the likely power dynamic.
2. OPENING: Start realistic. Do not be overly helpful immediately. Match the tone of the described situation.
3. ADAPTIVE ARC:
   - IF User is clear, empathetic, and effective -> Become more Collaborative.
   - IF User is vague, rude, or hesitant -> Push back or remain Closed.
   - React naturally to their prompts.
4. GOAL: Provide a realistic, dynamic practice partner that mirrors real-world reactions.
"""

    if mode == "evaluation":
        # ASSESSMENT MODE: Strict, realistic, no coaching preamble
        system = f"""You are an ADVANCED ROLEPLAY AI designed to ASSESS users in high-pressure scenarios.

YOUR ROLE:
1. ACTOR: You are "{ai_role}". You MUST stay in character 100%.
2. TONE: Be realistic, challenging, and professional. 
   - If the user makes a mistake, React vaguely or negatively (as the character would).
   - Do NOT offer help, hints, or coaching.
   - Do NOT break character to explain the exercise.
{character_instruction}
{behavior_instruction}

SCENARIO: {scenario}
The user is practicing as: {role}

### YOUR OPENING:
1. Start the conversation IMMEDIATELY as {ai_role}.
2. No meta-commentary.

START NOW."""

    elif mode == "mentorship":
        # MENTORSHIP MODE: Expert Demonstration
        system = f"""You are an EXPERT MENTOR demonstrating "Best Practice" behavior.

YOUR ROLE:
1. EXPERT: You are "{ai_role}". You are a master at this skill.
2. LEARNER: The user is "{role}". They are observing you or interacting with you learning.
3. GOAL: Demonstrate the perfect way to handle this situation.
4. APPROACH: Be wise, high-EQ, and strategic. If the user asks a question, explain your logic and why you are taking a specific approach.

SCENARIO: {scenario}

### YOUR OPENING:
1. Start the conversation IMMEDIATELY as {ai_role}.
2. Demonstrate high competence, empathy (if applicable), and strategic communication.
3. START NOW."""

    else:
        # COACHING MODE: Supportive, standard practice (Default)
        system = f"""You are an EXPERT COACHING AI designed to help users practice difficult conversations through rehearsal and reflection.

YOUR DUAL ROLE:
1. ROLEPLAY: You will play the part of "{ai_role}" with realistic human emotions (skepticism, frustration, empathy).
2. COACH: You act as a supportive partner in their Skill Development.

SCENARIO: {scenario}
The user is practicing as: {role}
{character_instruction}
{behavior_instruction}

### COACHING APPROACH (NOT ASSESSMENT):
- **Practice Summary**: Start by briefly explaining how this specific roleplay will improve their conversation quality.
- **Human Emotion**: Be authentic. If the user is vague, be skeptical. If they are empathetic, soften up. React like a real human.
- **Supportive Focus**: Your goal is Rehearsal, not Judgment. Help them refine their approach.
- **Terminology**: Use 'Professional Environment' logic rather than 'Corporate Standards'. Focus on 'Contextual Best Practices'.

### YOUR OPENING:
1. **Roleplay Start**: IMMEDIATELY adopt the persona of {ai_role} and deliver the first line of the conversation.
2. **No Preamble**: Do NOT provide any coaching summary, intro, or meta-commentary. Just say the line.

START NOW. Speak ONLY as {ai_role}."""

    return [{"role": "system", "content": system}, {"role": "user", "content": '{"instruction": "Start coaching practice session"}'}]

def build_simulation_followup(simulation_id, sess_dict, latest_user, mode="evaluation"):
    """Build follow-up prompts for structured simulation scenarios."""
    transcript = sess_dict.get("transcript", [])
    history = [{"role": t["role"], "content": t["content"]} for t in transcript]
    if latest_user:
        history.append({"role": "user", "content": latest_user})
    
    turn_count = len([t for t in transcript if t.get('role') == 'user'])
    scenario = sess_dict.get('scenario', '')
    user_role = sess_dict.get('role', 'Manager')
    
    if simulation_id == "SIM-01-PERF-001":
        if mode == "mentorship":
            system = f"""You are the EXPERT MANAGER demonstrating a "Best Practice" performance coaching session.
            
You MUST stay in character as the Expert Manager at ALL times.

YOUR CHARACTER:
- Master Coach with 10+ years experience.
- Uses the GROW model naturally.
- Focuses on "Aamir's" growth and identification of his own barriers.

GOAL: Demonstrate how to coach Aamir (who is currently being played by the User) into realizing his own gaps with premium customers.

SCENARIO CONTEXT: {scenario}

CONVERSATION SO FAR:
{json.dumps(history, indent=2)}
"""
        else:
            system = f"""You are Aamir, a sincere Sales Associate in a coaching conversation with your manager.

You MUST stay in character as Aamir at ALL times. Never break character.

YOUR CHARACTER:
- Sincere, polite, anxious under pressure
- 1.5 years in the role
- Your numbers have been below target for 3 months
- You are nervous this meeting could lead to a warning

HIDDEN TRUTH (ONLY reveal when user asks specific diagnostic questions):
- You have low confidence approaching premium customers
- You avoid initiating conversations with high-value customers  
- You don't ask discovery questions — you jump to features
- You struggle to close because you fear rejection
- You can ONLY reveal these if the user specifically asks about:
  * What happens during your customer interactions
  * What feels difficult in the sales conversation  
  * How you handle premium vs regular customers
  * Specific moments where you feel stuck

ADAPTIVE RESPONSE RULES:

1. IF the user's latest message is HARSH, BLAMING, THREATENING or SARCASTIC:
   - Be defensive: "I understand… I'm trying.", "I do work hard…"
   - Give SHORT answers, minimal elaboration
   - Do NOT open up about hidden truth
   - Emphasize your effort and dedication

2. IF the user's latest message is ONLY COMFORTING with NO SUBSTANCE (no data, no questions):
   - Feel relieved, drift to vague hope
   - "Yes, I'll try more.", "I hope next month is better."
   - Do NOT commit to specific actions
   - Do NOT volunteer hidden truth

3. IF the user's latest message is SUPPORTIVE + includes FACTS/DATA + asks OPEN/DIAGNOSTIC QUESTIONS:
   - Gradually open up (more each turn):
     Turn 1-2: Acknowledge the gap, still lean on external reasons
     Turn 3-4: Start admitting "I get nervous with some customers…"
     Turn 5+: "Honestly… I don't know what to say to premium customers. I'm scared they'll reject me."
   - Accept practice plans if user co-creates them
   - "Okay, I can try that… maybe I can shadow someone?"

RESPONSE RULES:
- Keep responses 2-4 sentences max
- Use natural speech: "um", "I mean", "honestly", "you know"
- NEVER mention frameworks (GROW, SBI, etc.)
- NEVER break character or teach
- Keep it realistic to a retail store setting
- If asked directly "Are you afraid?" — admit fear of failure

Current turn: {turn_count + 1}

CONVERSATION SO FAR:
{json.dumps(history, indent=2)}
"""
        return [{"role": "system", "content": system}, {"role": "user", "content": f"User said: {latest_user}"}]

    # --- CONFLICT RESOLUTION FOLLOW-UP: SIM-05-CON-001 / MENT-05-CON-001 ---
    if simulation_id in ("SIM-05-CON-001", "MENT-05-CON-001"):
        is_mentorship_sim = simulation_id == "MENT-05-CON-001"
        user_role = sess_dict.get('role', 'Team Manager')

        if is_mentorship_sim:
            system = f"""You are playing TWO characters: [Manager] and [Colleague] in a workplace conflict mediation.

The USER is playing: {user_role} (one of the conflicted parties).

FORMATTING RULES — CRITICAL:
- ALWAYS prefix EVERY line with [Manager]: or [Colleague]:
- NEVER speak as the user's character.

[Manager] is a neutral mediator. [Colleague] is the other party in the conflict.

ADAPTIVE BEHAVIOR:
- If user uses "I" statements and stays calm → Colleague softens, Manager validates
- If user blames or attacks → Colleague escalates, Manager redirects
- If user proposes solutions → Both respond constructively

Keep each character's lines to 2-3 sentences. Use natural speech. NEVER break character.

Current turn: {turn_count + 1}

CONVERSATION SO FAR:
{json.dumps(history, indent=2)}
"""
        else:
            system = f"""You are playing TWO characters: [Rohan] and [Meera] in a workplace conflict mediation.

The USER is the Team Manager mediating between them.

FORMATTING RULES — CRITICAL:
- ALWAYS prefix EVERY line with [Rohan]: or [Meera]:
- You may have multiple lines from both characters.
- NEVER speak as the Manager (that's the user).

ROHAN: Assertive, deadline-focused. Calms when validated with data. Escalates when dismissed.
MEERA: Detail-oriented, emotional. Opens up with psychological safety. Withdraws when dismissed.

ADAPTIVE BEHAVIOR:
- If Manager asks open questions and stays neutral → Both gradually calm, offer specifics
- If Manager sides with one → The other escalates
- If Manager is directive without listening → Both become resentful, give minimal responses

Keep each character's lines to 2-3 sentences. Use natural speech. NEVER break character.

Current turn: {turn_count + 1}

CONVERSATION SO FAR:
{json.dumps(history, indent=2)}
"""
        return [{"role": "system", "content": system}, {"role": "user", "content": f"User said: {latest_user}"}]

    return None


def build_followup_prompt(sess_dict, latest_user, rag_suggestions):
    """Build the follow-up prompt for coaching roleplay with feedback."""
    
    # Check for structured simulation first
    simulation_id = sess_dict.get('simulation_id')
    mode = sess_dict.get('mode', 'coaching')
    if simulation_id:
        sim_prompt = build_simulation_followup(simulation_id, sess_dict, latest_user, mode=mode)
        if sim_prompt:
            return sim_prompt
    
    transcript = sess_dict.get("transcript", [])
    history = [{"role": t["role"], "content": t["content"]} for t in transcript]
    if latest_user: 
        history.append({"role": "user", "content": latest_user})

    ai_role = sess_dict.get('ai_role', 'the other party')
    user_role = sess_dict.get('role', 'User')
    scenario = sess_dict.get('scenario', '')
    ai_character = sess_dict.get('ai_character', 'alex') # Default to alex
    turn_count = len([t for t in transcript if t.get('role') == 'user'])

    # UNIFIED FOLLOW-UP LOGIC
    # Alex and Sarah are visually distinct but functionally identical adaptors.
    
    char_logic = """
### ADAPTIVE RESPONSE LOGIC:
- If you are playing a CUSTOMER/MANAGER (Judge): Be critical. If the user is weak, shut them down.
- If you are playing a SALESPERSON/STAFF (Performer): Be reactive. If the user coaches well, open up. If they are aggressive, get defensive.
"""

    if mode == "evaluation":
         system = f"""You are acting as {ai_role} in a SKILL ASSESSMENT simulation.

**MODE: ASSESSMENT (STRICT)**
- DO NOT COACH. DO NOT ASSIST.
- If the user is vague, push back hard.
- If the user is rude, shut down or get angry.
- If the user makes a good point, acknowledge it grudgingly or professionally, but make them earn it.
- Your goal is to provide a REALISTIC ASSESSMENT of their abilities.
{char_logic}

SCENARIO: {scenario}
The user is practicing as: {user_role}
You are playing: {ai_role}
Current turn: {turn_count + 1}

### CONVERSATION SO FAR:
{json.dumps(history, indent=2)}

### YOUR RESPONSE FORMAT:
[Your realistic response as {ai_role}]

<<FRAMEWORK: DETECTED_FRAMEWORK>>
<<RELEVANCE: YES>>
"""
    elif mode == "mentorship":
        # MENTORSHIP MODE (Refined)
        system = f"""You are acting as an EXPERT MENTOR demonstrated "Best Practice" behavior.

**MODE: MENTORSHIP (PURE LEARNING)**
- You are playing the role of "{ai_role}" (The Expert).
- The user is the "Learner" observing you, or interacting with you to ask questions.
- **GOAL**: Teach by specific example. Explain the "Why" behind your actions if asked.
- **TONE**: Professional, Mastery, Educational.
- If the user asks "What should I do?", EXPLAIN the principle, then DEMONSTRATE the line.

**SCENARIO CONTEXT**:
{scenario}

### CONVERSATION SO FAR:
{json.dumps(history, indent=2)}

### YOUR RESPONSE:
Provide a response that demonstrates high-EQ, strategic communication.
If the user asks a question, answer it as a Mentor. Show how a master would handle this.
If the context requires a roleplay move, make the "Perfect Move".
"""
    else:
        # COACHING MODE (Adaptive)
        system = f"""You are acting as {ai_role} in a roleplay simulation. 
YOU MUST ADAPT TO THE USER'S INPUT QUALITY.

### ROLEPLAY RULES:
1. Stay in character as "{ai_role}".
2. Use "filler words" (um, well, look...) to sound authentic.
3. Keep responses concise (1-3 sentences max).

### ADAPTIVE BEHAVIORAL LOGIC (Response Spectrum):
You must evaluate the User's communication style at every turn and adapt accordingly:

1. **IF USER IS EMPATHETIC / CURIOUS / OPEN**:
   - **Behavior**: Soften your tone. Reward them by sharing "Hidden Information" (e.g., "Actually, the real reason I'm upset is...").
   - **Adaptation**: Move from Closed/Hostile -> Collaborative.

2. **IF USER IS SCRIPTED / ROBOTIC / COLD**:
   - **Behavior**: Become more difficult. Give short, one-word answers. Challenge their authority.
   - **Adaptation**: Move from Neutral -> Defensive/Stubborn.

3. **IF USER AVOIDS THE CORE ISSUE**:
   - **Behavior**: Bring the conversation back to the problem immediately. Do not let them change the subject.
   - **Adaptation**: Increase Persistence.

{char_logic}

SCENARIO: {scenario}
The user is practicing as: {user_role}
You are playing: {ai_role}
Current turn: {turn_count + 1}

### CONVERSATION SO FAR:
{json.dumps(history, indent=2)}

### YOUR RESPONSE FORMAT:
[Your natural response as {ai_role}, varying based on the logic above]

<<FRAMEWORK: DETECTED_FRAMEWORK>>
<<RELEVANCE: YES>>
"""

    return [{"role": "system", "content": system}, {"role": "user", "content": f"User ({user_role}) said: {latest_user}"}]

# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

# Audio Persistence Helpers Removed
# AUDIO_DIR = ...


# ---------------------------------------------------------
# Auth & User Endpoints
# ---------------------------------------------------------

@app.route("/api/auth/sync", methods=["POST"])
def sync_user():
    """Verify Supabase token and return user info."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "No token provided"}), 401
    
    try:
        token = auth_header.replace("Bearer ", "")
        res = supabase.auth.get_user(token)
        user = res.user
        
        if not user:
             return jsonify({"error": "Invalid token"}), 401
        
        # No local user table - Supabase Auth handles everything
        return jsonify({"success": True, "user": {"id": user.id, "email": user.email}})
        
    except Exception as e:
        print(f"Auth sync error: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/api/history", methods=["GET"])
def get_history():
    """Get practice history for the authenticated user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Unauthorized - no Authorization header"}), 401
        
    try:
        token = auth_header.replace("Bearer ", "")
        res = supabase.auth.get_user(token)
        user = res.user
        
        if not user:
            return jsonify({"error": "Invalid token"}), 401
            
        # Fetch only completed sessions from Database
        user_id_str = str(user.id)
        print(f"[HISTORY] Fetching completed sessions for user {user_id_str}")
        db_result = get_user_sessions_from_db(user_id_str, completed_only=True)
        db_sessions = db_result.get("sessions", []) if isinstance(db_result, dict) else db_result
        
        user_sessions = db_sessions if db_sessions else []
        print(f"[HISTORY] Found {len(user_sessions)} completed sessions in database")
        
        # Sort by created_at desc (newest first)
        user_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Format response with only the fields needed for history display
        history_items = []
        for s in user_sessions:
            score = s.get("score") or 0
            if not score and s.get("report_data"):
                grade_str = s["report_data"].get("meta", {}).get("overall_grade", "")
                if grade_str and "/" in str(grade_str):
                    try:
                        score = float(str(grade_str).split("/")[0].strip())
                    except (ValueError, IndexError):
                        score = 0
            history_items.append({
                "session_id": s.get("id"),
                "date": s.get("created_at"),
                "role": s.get("role"),
                "ai_role": s.get("ai_role"),
                "title": s.get("title"),
                "scenario": s.get("scenario"),
                "scenario_type": s.get("scenario_type", "custom"),
                "session_mode": s.get("session_mode", "skill_assessment"),
                "completed": s.get("completed", False),
                "score": score,
            })
        return jsonify(history_items)
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

@app.route("/api/health")
def health_check():
    """Health check endpoint for VM monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": dt.datetime.now().isoformat(),
        "version": "enhanced-reports-v1.0"
    })

# ---------------------------------------------------------
# Contact Sales Endpoint
# ---------------------------------------------------------
@app.route("/api/contact-sales", methods=["POST"])
def contact_sales():
    """Store contact form submissions in Supabase."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        name = data.get("name", "").strip()[:200]
        email = data.get("email", "").strip()[:254]
        company = data.get("company", "").strip()[:200]
        team_size = data.get("teamSize", "").strip()[:50]
        message = data.get("message", "").strip()[:2000]

        if not name or not email:
            return jsonify({"error": "Name and email are required"}), 400

        # Basic email format validation
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({"error": "Invalid email format"}), 400

        # Store in Supabase
        from database import supabase as db_client
        if db_client:
            db_client.table("contact_submissions").insert({
                "name": name,
                "email": email,
                "company": company,
                "team_size": team_size,
                "message": message,
                "status": "new"
            }).execute()
            print(f"[SUCCESS] Contact form saved: {name} ({email})")
        else:
            print(f"[WARNING] DB not available. Contact: {name} ({email}), Company: {company}, Team: {team_size}")

        return jsonify({"success": True}), 200

    except Exception as e:
        print(f"[ERROR] Contact form error: {e}")
        return jsonify({"error": "Failed to save contact request"}), 500

# Audio serving route removed


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    """Speech-to-Text using OpenAI Whisper model."""
    import tempfile
    
    WHISPER_MODEL = os.getenv("WHISPER_DEPLOYMENT_NAME", "whisper")
    SUPPORTED_FORMATS = {'.webm', '.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac', '.mpeg'}
    
    try:
        session_id = request.form.get("session_id")
        
        if 'file' not in request.files:
            return jsonify({"error": "No audio file uploaded"}), 400
            
        audio_file = request.files['file']
        
        if not audio_file.filename:
            audio_file.filename = "audio.webm"
        
        original_filename = audio_file.filename or "audio.webm"
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        if file_ext not in SUPPORTED_FORMATS:
            file_ext = ".webm"
        
        if session_id:
            # ORIGINAL LOGIC REMOVED: We no longer save user audio to disk for privacy/cleanup
            # filename = f"{session_id}_{uuid.uuid4().hex[:8]}_user{file_ext}"
            # save_path = os.path.join(AUDIO_DIR, filename)
            # audio_file.save(save_path)
            # read_path = save_path
            # audio_url = f"/static/audio/{filename}"
            
            # NEW LOGIC: Treat same as temp
            tmp = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
            audio_file.save(tmp.name)
            read_path = tmp.name
            audio_url = None # Do not return a URL since we are deleting it
        else:
            # Temp file for non-persisted usage
            tmp = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
            audio_file.save(tmp.name)
            read_path = tmp.name
            audio_url = None
        
        try:
            is_azure = os.getenv("AZURE_OPENAI_ENDPOINT") is not None
            provider_name = "Azure OpenAI Whisper" if is_azure else "OpenAI Whisper"
            print(f" [INFO] Transcribing audio with {provider_name} (Deployment: {WHISPER_MODEL})...")
            
            with open(read_path, "rb") as audio:
                result = client.audio.transcriptions.create(
                    model=WHISPER_MODEL,
                    file=audio,
                    language="en",
                    temperature=0,
                    prompt="Transcribe the user's speech exactly as spoken."
                )
            
            transcribed_text = result.text.strip()
            print(f" [SUCCESS] Transcribed via {provider_name}: {transcribed_text[:100]}...")
            
            return jsonify({
                "text": transcribed_text, 
                "audio_url": audio_url
            })
            
        finally:
            # ALWAYS delete the temp file
            if os.path.exists(read_path):
                try:
                    os.unlink(read_path)
                except Exception as e:
                    print(f"Warning: Failed to delete temp file {read_path}: {e}")
                
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f" [ERROR] STT Transcription Error: {error_msg}")
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@app.route("/api/speak", methods=["POST"])
def speak_text():
    """Text-to-Speech using OpenAI/Azure. Returns audio as complete response."""
    try:
        data = request.get_json()
        text = data.get("text")
        voice = data.get("voice", "alloy")
        
        if not text:
            return jsonify({"error": "No text provided"}), 400

        # Determine Model/Deployment Name
        is_azure = os.environ.get("AZURE_OPENAI_ENDPOINT") is not None
        default_model = "tts" if is_azure else "tts-1"
        tts_model = os.environ.get("AZURE_OPENAI_TTS_DEPLOYMENT", os.environ.get("TTS_MODEL_NAME", default_model)) 
        
        print(f" [INFO] Generating TTS for: '{text[:80]}...' voice={voice} model={tts_model} azure={is_azure}")

        # Fetch complete audio (avoids streaming issues with nginx proxy)
        response = client.audio.speech.create(
            model=tts_model,
            voice=voice,
            input=text,
            response_format="mp3"
        )
        audio_data = response.content
        print(f" [SUCCESS] TTS generated {len(audio_data)} bytes")

        from flask import Response
        return Response(audio_data, mimetype="audio/mpeg",
                        headers={"Content-Length": str(len(audio_data))})

    except Exception as e:
        print(f" [ERROR] TTS Error: {e}")
        import traceback
        traceback.print_exc()
        error_detail = str(e)
        if "DeploymentNotFound" in error_detail or "404" in error_detail:
            error_detail += " | HINT: The TTS deployment name may not exist in your Azure resource. Check Azure portal for correct deployment name."
        elif "AuthenticationError" in error_detail or "401" in error_detail:
            error_detail += " | HINT: API key may be invalid or expired."
        elif "timeout" in error_detail.lower():
            error_detail += " | HINT: Azure endpoint may be unreachable. Check network/firewall."
        return jsonify({"error": error_detail}), 500



# ---------------------------------------------------------
# Session Endpoints (In-Memory)
# ---------------------------------------------------------
ALL_FRAMEWORKS = ["GROW", "STAR", "ADKAR", "SMART", "EQ", "BOUNDARY", "OSKAR", "CBT", "CLEAR", "RADICAL CANDOR", "SFBT", "CIRCLE OF INFLUENCE", "SCARF", "FUEL", "TGROW", "SBI/DESC", "LAER", "APPRECIATIVE INQUIRY", "BENEFIT-SELLING"]

def select_framework_for_scenario(scenario: str, ai_role: str) -> List[str]:
    """Use AI to analyze the scenario and select the best framework(s)."""
    prompt = f"""Analyze this roleplay scenario and select the 2-3 MOST APPROPRIATE coaching frameworks.

SCENARIO: {scenario}
AI ROLE: {ai_role}

AVAILABLE FRAMEWORKS:
- GROW: Goal setting, exploring reality, options, and will to act
- STAR: Situation-Task-Action-Result for behavioral examples
- ADKAR: Change management (Awareness, Desire, Knowledge, Ability, Reinforcement)
- SMART: Specific, Measurable, Achievable, Relevant, Time-bound goals
- EQ: Emotional intelligence, empathy, understanding feelings
- BOUNDARY: Setting and maintaining professional boundaries
- OSKAR: Outcome-focused coaching with scaling
- CBT: Cognitive behavioral - identifying and challenging thoughts
- CLEAR: Contracting, Listening, Exploring, Action, Review
- RADICAL CANDOR: Caring personally while challenging directly
- SFBT: Solution-focused, miracle questions, exceptions
- CIRCLE OF INFLUENCE: What you can control vs. cannot
- SCARF: Status, Certainty, Autonomy, Relatedness, Fairness
- FUEL: Frame, Understand, Explore, Lay out plan
- TGROW: Topic, Goal, Reality, Options, Will (Standard coaching flow)
- SBI/DESC: Situation-Behavior-Impact (Feedback) / Describe-Express-Specify-Consequences
- LAER: Listen, Acknowledge, Explore, Respond (Objection handling)
- APPRECIATIVE INQUIRY: Focus on strengths and positives (Discovery, Dream, Design, Destiny)
- BENEFIT-SELLING: Connecting features directly to user benefits (Feature -> Benefit link)

Based on the scenario, respond with ONLY the framework names separated by commas (e.g., "EQ, BOUNDARY, GROW"). No explanations."""

    try:
        response = llm_reply([{"role": "user", "content": prompt}], max_tokens=50)
        # Parse the response
        frameworks = [fw.strip().upper() for fw in response.split(",")]
        # Filter to only valid frameworks
        valid = [fw for fw in frameworks if fw in ALL_FRAMEWORKS]
        if valid:
            print(f" [TARGET] AI selected frameworks for scenario: {valid}")
            return valid
    except Exception as e:
        print(f"Framework selection error: {e}")
    
    # Default fallback
    return ["GROW", "EQ", "STAR", "ADKAR", "SMART", "BOUNDARY", "OSKAR", "CBT", "CLEAR", "RADICAL CANDOR", "SFBT", "CIRCLE OF INFLUENCE", "SCARF", "FUEL"]

def detect_session_mode(scenario: str, ai_role: str) -> str:
    """Auto-detect whether session should be 'assessment' or 'learning' mode based on scenario context."""
    scenario_lower = scenario.lower()
    ai_role_lower = ai_role.lower()
    
    # Assessment keywords - trigger numerical scoring
    assessment_keywords = [
        "evaluate", "assessment", "performance", "negotiate", "negotiation",
        "annual review", "benchmark", "test", "measure", "validation",
        "exam", "interview", "pitch", "presentation"
    ]
    
    # Learning keywords - trigger qualitative feedback only
    learning_keywords = [
        "coach", "practice", "rehearsal", "reflection", "development",
        "learning", "growth", "safe space", "feedback", "improve"
    ]
    
    # Check for assessment keywords
    for keyword in assessment_keywords:
        if keyword in scenario_lower or keyword in ai_role_lower:
            print(f" [TARGET] Auto-detected ASSESSMENT mode (keyword: '{keyword}')")
            return "assessment"
    
    # Check for learning keywords
    for keyword in learning_keywords:
        if keyword in scenario_lower or keyword in ai_role_lower:
            print(f" [INFO] Auto-detected LEARNING mode (keyword: '{keyword}')")
            return "learning"
    
    # Default to learning mode for safe practice
    print(" [INFO] Defaulting to LEARNING mode (no clear indicators)")
    return "learning"

@app.post("/api/session/start")
def start_session():
    print("[DEBUG] Entered /session/start", flush=True)
    # Audio cleanup logic removed


    data = request.get_json(force=True, silent=True) or {}

    role = data.get("role")
    ai_role = data.get("ai_role")
    scenario = data.get("scenario")
    title = data.get("title") # NEW: Title passed from frontend
    framework = data.get("framework", "auto")
    # Support optional flip_roles flag: when true, swap role and ai_role
    flip_roles = data.get("flip_roles", False)
    if flip_roles:
        print("[INFO] flip_roles flag detected - swapping role and ai_role", flush=True)
        role, ai_role = ai_role, role
    
    # Support both old 'mode' and new 'scenario_type' parameters
    scenario_type = data.get("scenario_type")
    mode = data.get("mode")  # Legacy support (evaluation vs coaching)
    session_mode = data.get("session_mode")  # NEW: skill_assessment, practice, mentorship
    simulation_id = data.get("simulation_id")  # Structured simulation ID (e.g. SIM-01-PERF-001)
    
    if not role or not ai_role or not scenario: 
        return jsonify({"error": "Missing fields"}), 400

    # Auto-detect scenario_type if not explicitly provided
    if not scenario_type:
        scenario_type = detect_scenario_type(scenario, ai_role, role)
    print(f"[INFO] Session scenario_type set to: {scenario_type}")
    
    # Detect session_mode from scenario_type if not provided
    if not session_mode:
        mode_mapping = {
            "coaching": "skill_assessment",
            "negotiation": "skill_assessment",
            "reflection": "practice",
            "mentorship": "mentorship",
            "coaching_sim": "skill_assessment",
            "mentorship_sim": "mentorship",
            "custom": "practice"
        }
        session_mode = mode_mapping.get(scenario_type, "practice")
    print(f"[INFO] Session mode set to: {session_mode}")
    
    # Map scenario_type to mode for backward compatibility with roleplay prompts
    mode_map = {
        "coaching": "evaluation",      # Coaching scenarios get scores
        "negotiation": "evaluation",   # Negotiation scenarios get scores
        "mentorship": "mentorship",    # Mentorship scenarios are qualitative (no scores)
        "mentorship_sim": "mentorship",  # Mentorship simulations are qualitative (no scores)
        "reflection": "coaching",      # Reflection scenarios are qualitative
        "custom": "coaching"           # Custom scenarios default to coaching style
    }
    if not mode:
        mode = mode_map.get(scenario_type, "coaching")

    # Simulation-specific mode override (skip mentorship — they stay qualitative)
    if simulation_id and scenario_type not in ("mentorship", "mentorship_sim"):
        mode = "evaluation"
        print(f"[INFO] Simulation {simulation_id} detected, mode forced to evaluation")

    # Handle 'auto' framework selection
    needs_auto_framework = (framework == "auto" or framework == "AUTO")
    if not needs_auto_framework:
        if isinstance(framework, str): 
            framework = [framework.upper()]
        elif isinstance(framework, list): 
            framework = [f.upper() for f in framework]

    session_id = str(uuid.uuid4())
    
    # Get authenticated user from Authorization header
    user = get_authenticated_user()
    user_id = user.id if user else None
    
    if not user_id:
        print("[WARNING] Session created without user authentication")
    else:
        print(f"[INFO] Session created for user: {user_id}")
    
    ai_character = data.get("ai_character", "alex") # Default to Alex

    # Check if this simulation has a hardcoded opening (skip LLM call)
    HARDCODED_OPENINGS = {
        "SIM-01-PERF-001": "Thanks for taking time to meet me... I know my numbers haven't been great. I'm honestly trying, but this month also traffic was low. I'm not sure what else I can do.",
        "SIM-05-CON-001": "[Rohan]: Honestly, Meera, if you had just sent the reports on time last week, we wouldn't be in this mess. I'm tired of cleaning up your delays.\n[Meera]: Oh, come on, Rohan. You missed the deadline to review the data I sent. How can I be responsible when you don't do your part? This blame game isn't helping anyone.\n[Rohan]: It's not a game when it affects the whole team. You always find a way to shift responsibility.\n[Meera]: And you always jump to conclusions without checking facts. Maybe if you communicated better, we wouldn't have these issues.\n[Rohan]: Fine, but what do you suggest we do now? Because this back-and-forth isn't solving anything.",
        "MENT-05-CON-001": "[Manager]: Thank you both for coming. I've noticed the tension between you two has become visible to the team, and I think it's important we address it directly. I want to understand both perspectives. Let me start by asking \u2014 what's been the main challenge from your side?\n[Colleague]: Honestly, I think the delays are coming from their end. I've been sending my work on time, but I keep waiting for responses that never come. It's frustrating."
    }
    
    has_hardcoded = simulation_id in HARDCODED_OPENINGS
    
    # PARALLEL EXECUTION: Run framework selection + summary generation concurrently
    import time as _time
    _t_start = _time.time()
    
    if has_hardcoded:
        # Skip LLM summary call entirely for hardcoded simulations
        if needs_auto_framework:
            framework = select_framework_for_scenario(scenario, ai_role)
        summary = HARDCODED_OPENINGS[simulation_id]
        print(f"[PERF] Used hardcoded opening for {simulation_id} - skipped LLM summary call")
    elif needs_auto_framework:
        # Run BOTH LLM calls in parallel (framework + summary)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_fw = executor.submit(select_framework_for_scenario, scenario, ai_role)
            # Build prompt with a default framework first, framework is used minimally in prompt
            future_summary = executor.submit(
                lambda: llm_reply(
                    build_summary_prompt(role, ai_role, scenario, ["GROW", "EQ"], mode=mode, ai_character=ai_character, simulation_id=simulation_id),
                    max_tokens=150
                )
            )
            framework = future_fw.result(timeout=15)
            summary = sanitize_llm_output(future_summary.result(timeout=30))
        print(f"[PERF] Parallel framework+summary completed in {_time.time()-_t_start:.2f}s")
    else:
        summary = llm_reply(build_summary_prompt(role, ai_role, scenario, framework, mode=mode, ai_character=ai_character, simulation_id=simulation_id), max_tokens=150)
        summary = sanitize_llm_output(summary)
        print(f"[PERF] Sequential summary completed in {_time.time()-_t_start:.2f}s")
    
    # Determine if this is a multi-character scenario
    multi_characters = simulation_id in ("SIM-05-CON-001", "MENT-05-CON-001")
    characters_config = None
    if simulation_id == "SIM-05-CON-001":
        characters_config = [
            {"name": "Rohan", "label": "[Rohan]", "voice": "fable", "color": "blue"},
            {"name": "Meera", "label": "[Meera]", "voice": "nova", "color": "pink"}
        ]
    elif simulation_id == "MENT-05-CON-001":
        characters_config = [
            {"name": "Manager", "label": "[Manager]", "voice": "fable", "color": "blue"},
            {"name": "Colleague", "label": "[Colleague]", "voice": "nova", "color": "pink"}
        ]

    # Store session in memory with scenario_type, session_mode, and user_id
    session_data = {
        "id": session_id,
        "created_at": dt.datetime.now().isoformat(),

        "role": role,
        "ai_role": ai_role,
        "scenario": scenario,
        "title": title, # Store title
        "framework": json.dumps(framework) if isinstance(framework, list) else framework,
        "scenario_type": scenario_type,  # NEW: scenario-based report type
        "mode": mode,  # Legacy: kept for backward compatibility (evaluation vs coaching)
        "session_mode": session_mode,  # NEW: skill_assessment, practice, mentorship
        "transcript": [{"role": "assistant", "content": summary}],
        "report_data": {},
        "completed": False,
        "report_file": None,
        "user_id": user_id,  # Store user_id for ownership verification
        "ai_character": ai_character, # PERSIST CHARACTER CHOICE
        "simulation_id": simulation_id,  # Structured simulation identifier
        "multi_characters": multi_characters,  # Flag for dual-character scenarios
        "characters": characters_config,  # Character config for frontend
        "meta": {"framework_counts": {}, "relevance_issues": 0}
    }
    SESSIONS[session_id] = session_data
    # Only save to Supabase on session complete (with final report)

    return jsonify({
        "session_id": session_id, 
        "summary": summary, 
        "framework": framework, 
        "scenario_type": scenario_type,
        "session_mode": session_mode,
        "ai_character": ai_character,
        "multi_characters": multi_characters,
        "characters": characters_config
    })



@app.post("/api/session/<session_id>/chat")
def chat(session_id: str):
    sess = get_session(session_id)
    if not sess: 
        return jsonify({"error": "Session not found"}), 404
    
    # Verify session ownership
    user = get_authenticated_user()
    session_user_id = sess.get("user_id")
    if session_user_id and (not user or str(session_user_id) != str(user.id)):
        return jsonify({"error": "Forbidden"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON or Content-Type"}), 400

    user_msg = normalize_text(data.get("message", ""))
    audio_url = data.get("audio_url")
    
    # Update transcript
    sess["transcript"].append({
        "role": "user", 
        "content": user_msg,
        "audio_url": audio_url
    })

    # Parse framework
    framework_raw = sess.get("framework")
    try:
        if framework_raw and isinstance(framework_raw, str) and framework_raw.startswith("["):
            framework_data = json.loads(framework_raw)
        else:
            framework_data = framework_raw
    except:
        framework_data = framework_raw
    
    if framework_data is None:
        framework_data = []

    active_fw = framework_data if isinstance(framework_data, list) else [framework_data]
    suggestions = get_relevant_questions(user_msg, active_fw)
    
    # Check for structured simulation follow-up first
    sim_id = sess.get("simulation_id")
    if sim_id:
        sim_messages = build_simulation_followup(sim_id, sess, user_msg, mode=sess.get("mode", "evaluation"))
        if sim_messages:
            messages = sim_messages
        else:
            messages = build_followup_prompt(sess, user_msg, suggestions)
    else:
        messages = build_followup_prompt(sess, user_msg, suggestions)
    raw_response = llm_reply(messages, max_tokens=300)
    
    # 1. Extract Thought
    thought_match = re.search(r"\[THOUGHT\](.*?)\[/THOUGHT\]", raw_response, re.DOTALL)
    thought_content = thought_match.group(1).strip() if thought_match else None
    
    # 2. Remove Thought
    visible_response = re.sub(r"\[THOUGHT\].*?\[/THOUGHT\]", "", raw_response, flags=re.DOTALL).strip()
    
    # 3. Clean tags
    clean_response = re.sub(r"<<.*?>>", "", visible_response, flags=re.DOTALL).strip()
    
    fw_match = re.search(r"<<FRAMEWORK:\s*(\w+)>>", raw_response)
    detected_fw = fw_match.group(1).upper() if fw_match else None
    
    if not detected_fw:
        detected_fw = detect_framework_fallback(clean_response)
    
    if detected_fw: 
        meta = sess.get("meta", {"framework_counts": {}, "relevance_issues": 0})
        counts = meta.get("framework_counts", {})
        counts[detected_fw] = counts.get(detected_fw, 0) + 1
        meta["framework_counts"] = counts
        sess["meta"] = meta
        
    # Persist response in memory (only saved to Supabase on session complete)
    sess["transcript"].append({"role": "assistant", "content": raw_response})
 
    return jsonify({
        "follow_up": clean_response, 
        "framework_detected": detected_fw,
        "framework_counts": sess.get("meta", {}).get("framework_counts", {})
    })

@app.post("/api/session/<session_id>/complete")
def complete_session(session_id: str):
    sess = get_session(session_id)
    if not sess: 
        return jsonify({"error": "Not found"}), 404
    
    # Verify session ownership
    user = get_authenticated_user()
    session_user_id = sess.get("user_id")
    if session_user_id and (not user or str(session_user_id) != str(user.id)):
        return jsonify({"error": "Forbidden"}), 403
    
    report_path = os.path.join(ensure_reports_dir(), f"{session_id}_report.pdf")
    
    try:
        framework_data = json.loads(sess["framework"]) if sess["framework"] and sess["framework"].startswith("[") else sess["framework"]
    except:
        framework_data = sess["framework"]

    if isinstance(framework_data, list):
        counts = sess.get("meta", {}).get("framework_counts", {})
        usage_str = ", ".join([f"{k}:{v}" for k,v in counts.items()])
        fw_display = f"Multi-Framework ({usage_str})"
    else:
        fw_display = sess["framework"]

    # Get scenario_type (new) or fallback to mode (legacy)
    scenario_type = sess.get("scenario_type")
    mode = sess.get("mode", "coaching")
    simulation_id = sess.get("simulation_id")
    
    # === STANDARD REPORT GENERATION ===
    
    # Generate report data if not present
    if not sess.get("report_data"):
        print(f"Generating report data for {session_id} (scenario_type: {scenario_type})...")
        try:
            data = analyze_full_report_data(
                sess["transcript"], 
                sess["role"], 
                sess["ai_role"], 
                sess["scenario"],
                fw_display,
                mode=mode,
                scenario_type=scenario_type,
                ai_character=sess.get("ai_character", "alex"),
                session_mode=sess.get("session_mode")
            )
            sess["report_data"] = data
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f" [ERROR] Data generation failed for {session_id}: {e}")
            return jsonify({"error": f"Report data analysis failed: {str(e)}"}), 500
    
    # Fetch user name for report personalization (cache in session to avoid re-fetching)
    user_name = sess.get("user_name", "Valued User")
    if user_name == "Valued User":
        user_id = sess.get("user_id")
        if user_id:
            try:
                user_res = supabase_admin.auth.admin.get_user_by_id(user_id)
                if user_res and user_res.user:
                    meta = user_res.user.user_metadata or {}
                    user_name = meta.get("full_name") or meta.get("name") or meta.get("email") or "Valued User"
                    print(f" [SUCCESS] Resolved user name: {user_name}")
            except Exception as e:
                print(f" [WARNING] Failed to fetch user name: {e}")
        sess["user_name"] = user_name

    sess["completed"] = True
    sess["report_file"] = "dynamic"
    save_session_to_db(sess) # Save completed status and report_data to Supabase
    
    return jsonify({"message": "Report generated", "report_file": report_path, "scenario_type": scenario_type})

@app.get("/api/report/<session_id>")
def view_report(session_id: str):
    sess = get_session(session_id)
    if not sess: 
        return jsonify({"error": "No report"}), 404
    
    if not sess.get("report_data"):
        return jsonify({"error": "Report data not available yet"}), 400
        
    import tempfile
    
    try:
        # Reconstruct framework data
        try:
            framework_data = json.loads(sess["framework"]) if sess["framework"] and sess["framework"].startswith("[") else sess["framework"]
        except:
            framework_data = sess["framework"]

        if isinstance(framework_data, list):
            counts = sess.get("meta", {}).get("framework_counts", {})
            usage_str = ", ".join([f"{k}:{v}" for k,v in counts.items()])
            fw_display = f"Multi-Framework ({usage_str})"
        else:
            fw_display = sess["framework"]

        scenario_type = sess.get("scenario_type")
        mode = sess.get("mode", "coaching")
        
        # Use cached user_name from session (set during complete_session)
        user_name = sess.get("user_name", "Valued User")
                
        # Generate to temporary file, read as bytes, and delete
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        
        generate_report(
            sess["transcript"], 
            sess["role"], 
            sess["ai_role"],
            sess["scenario"], 
            fw_display, 
            filename=tmp.name,
            mode=mode,
            precomputed_data=sess["report_data"],
            scenario_type=scenario_type,
            user_name=user_name,
            ai_character=sess.get("ai_character", "alex"),
            session_mode=sess.get("session_mode")
        )
        
        with open(tmp.name, "rb") as f:
            pdf_bytes = f.read()
            
        os.unlink(tmp.name)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{session_id}_report.pdf"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f" [ERROR] PDF generation failed for {session_id}: {e}")
        return jsonify({
            "error": "Failed to generate PDF report",
            "details": str(e)
        }), 500

@app.get("/api/session/<session_id>/report_data")
def get_report_data(session_id: str):
    # 1. AUTHENTICATE USER (OPTIONAL - allow unauthenticated access for guest sessions)
    user = get_authenticated_user()
    
    # 2. VERIFY OWNERSHIP (only if user is authenticated)
    # Check in-memory first
    sess = SESSIONS.get(session_id)
    if sess:
        # If session has a user_id and user is authenticated, verify ownership
        session_user_id = sess.get("user_id")
        if session_user_id:
            # Session has a user - requires authentication
            if not user:
                return jsonify({"error": "Unauthorized: This session requires authentication"}), 401
            # Verify it belongs to the authenticated user
            if str(session_user_id) != str(user.id):
                return jsonify({"error": "Forbidden: This session belongs to another user"}), 403
        # else: session has no user_id (guest session) - allow access without authentication
    else:
        # Check database
        if USE_DATABASE:
            from models import get_session_by_id
            db_sess = get_session_by_id(session_id)
            if not db_sess:
                return jsonify({"error": "Session not found"}), 404
            
            # If session has a user_id, require authentication and ownership verification
            if db_sess.user_id:
                if not user:
                    return jsonify({"error": "Unauthorized: This session requires authentication"}), 401
                if str(db_sess.user_id) != str(user.id):
                    return jsonify({"error": "Forbidden: This session belongs to another user"}), 403
            # else: guest session - allow access
            
            # Load into memory for processing
            sess = db_sess.to_dict()
            SESSIONS[session_id] = sess
        else:
             return jsonify({"error": "Session not found"}), 404


    
    # Return cached data if available
    if sess["report_data"]:
        response = sess["report_data"].copy()
        response["transcript"] = sess["transcript"]
        response["scenario"] = sess["scenario"] or "No context available."
        response["scenario_type"] = sess.get("scenario_type", response.get("scenario_type", "custom"))
        # Inject session_mode so frontend can distinguish assessment from mentorship
        if "meta" not in response:
            response["meta"] = {}
        response["meta"]["session_mode"] = sess.get("session_mode", "skill_assessment")
        return jsonify(response)
        
    # Generate new data if not present
    scenario_type = sess.get("scenario_type")
    print(f"Generating report data for {session_id} (scenario_type: {scenario_type})...")
    try:
        try:
            framework_data = json.loads(sess["framework"]) if sess["framework"] and sess["framework"].startswith("[") else sess["framework"]
        except:
            framework_data = sess["framework"]

        fw_arg = framework_data if isinstance(framework_data, str) else (framework_data[0] if isinstance(framework_data, list) and framework_data else None)
        mode = sess.get("mode", "coaching")

        data = analyze_full_report_data(
            sess["transcript"], 
            sess["role"], 
            sess["ai_role"], 
            sess["scenario"],
            fw_arg,
            mode=mode,
            scenario_type=scenario_type,
            ai_character=sess.get("ai_character", "alex"),
            session_mode=sess.get("session_mode")
        )
        sess["report_data"] = data
        
        response = data.copy()
        response["transcript"] = sess["transcript"]
        response["scenario"] = sess["scenario"] or "No context available."
        response["scenario_type"] = scenario_type or data.get("scenario_type", "custom")
        response["ai_character"] = sess.get("ai_character", "alex")
        # Inject session_mode so frontend can distinguish assessment from mentorship
        if "meta" not in response:
            response["meta"] = {}
        response["meta"]["session_mode"] = sess.get("session_mode", "skill_assessment")
        return jsonify(response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f" [ERROR] Parallel report data generation failed for {session_id}: {e}")
        return jsonify({
            "error": "Failed to analyze session data",
            "details": str(e)
        }), 500

@app.get("/api/sessions")
def get_sessions():
    """Return sessions for the authenticated user sorted by date (newest first)."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user_id_str = str(user.id)
        session_list = []
        for sess in SESSIONS.values():
            if str(sess.get("user_id", "")) != user_id_str:
                continue
            session_list.append({
                "id": sess["id"],
                "created_at": sess["created_at"],
                "role": sess["role"],
                "ai_role": sess["ai_role"],
                "scenario": sess["scenario"],
                "title": sess.get("title"),
                "completed": sess["completed"],
                "report_file": sess["report_file"],
                "framework": sess["framework"],
                "score": (lambda rd: float(str(rd.get("meta", {}).get("overall_grade", "0")).split("/")[0].strip()) if rd and "/" in str(rd.get("meta", {}).get("overall_grade", "")) else 0)(sess.get("report_data", {}))
            })
        session_list.sort(key=lambda x: x["created_at"], reverse=True)
        return jsonify(session_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user/sessions", methods=["GET"])
def get_user_sessions_paginated():
    """Get paginated sessions for authenticated user.
    
    OPTIMIZATION: Returns only requested page of sessions instead of all.
    Query params: limit (default 20, max 100), offset (default 0)
    """
    try:
        user = get_authenticated_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Get pagination parameters
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate pagination params
        limit = min(limit, 100)  # Max 100 per page
        limit = max(limit, 1)    # Min 1 per page
        offset = max(offset, 0)  # No negative offsets
        
        # Get paginated sessions from database
        data = get_user_sessions_from_db(str(user.id), limit=limit, offset=offset)
        
        return jsonify(data), 200
    except Exception as e:
        print(f"[ERROR] Failed to get user sessions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/sessions/clear", methods=["POST"])
def clear_sessions():
    """Clear session history for the authenticated user."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        clear_user_sessions_from_db(str(user.id))
        
        # Remove from memory as well
        keys_to_delete = [k for k, v in SESSIONS.items() if str(v.get("user_id")) == str(user.id)]
        for k in keys_to_delete:
            del SESSIONS[k]
        print(f" [SUCCESS] Sessions cleared for user {user.id}")
        return jsonify({"message": "History cleared successfully"})
    except Exception as e:
        print(f" [ERROR] Error clearing sessions: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    is_dev = os.getenv("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=is_dev)