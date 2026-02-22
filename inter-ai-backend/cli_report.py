import json
import os
import math
import re
import unicodedata
import datetime as dt
from fpdf import FPDF
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import httpx
import concurrent.futures


load_dotenv()

import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import tempfile

USE_AZURE = True
# ... imports ... 
def setup_langchain_model():
    # Force httpx to ignore system proxies which cause hangs on Azure VMs
    http_client = httpx.Client(trust_env=False, timeout=30.0)
    
    if USE_AZURE:
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", os.getenv("MODEL_NAME", "gpt-4.1-mini")),
            http_client=http_client,
            temperature=0.4
        )
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), 
        model=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
        http_client=http_client,
        temperature=0.4
    )

llm = setup_langchain_model()

MODEL_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", os.getenv("MODEL_NAME", "gpt-4.1-mini"))

# --- Premium Modern Palette ---
COLORS = {
    'text_main': (30, 41, 59),       # Slate 800
    'text_light': (100, 116, 139),   # Slate 500
    'white': (255, 255, 255),
    
    # Premium Glassmorphism Palette
    'primary': (15, 23, 42),         # Deep Slate 900
    'secondary': (51, 65, 85),       # Slate 700
    'accent': (59, 130, 246),        # Blue 500 (Primary Brand)
    'accent_light': (96, 165, 250), # Blue 400
    
    # Gradients & UI
    'header_grad_1': (15, 23, 42),   # Slate 900
    'header_grad_2': (30, 58, 138),  # Blue 900
    'score_grad_1': (236, 253, 245), # Emerald 50
    'score_grad_2': (209, 250, 229), # Emerald 100
    'score_text': (4, 120, 87),      # Emerald 700
    
    # Chart Colors
    'chart_fill': (59, 130, 246),    # Blue 500
    'chart_stroke': (37, 99, 235),   # Blue 600
    'sentiment_pos': (16, 185, 129), # Emerald 500
    'sentiment_neg': (239, 68, 68),  # Red 500
    
    # Section colors
    'section_skills': (99, 102, 241),    # Indigo 500
    'section_eq': (236, 72, 153),        # Pink 500
    'section_comm': (14, 165, 233),      # Sky 500
    'section_coach': (245, 158, 11),     # Amber 500
    
    'divider': (226, 232, 240),
    'bg_light': (248, 250, 252),
    'sidebar_bg': (248, 250, 252),
    
    # Status
    'success': (16, 185, 129),       # Emerald 500
    'warning': (245, 158, 11),       # Amber 500
    'danger': (239, 68, 68),         # Red 500
    'rewrite_good': (236, 253, 245), # Emerald 50
    'bad_bg': (254, 226, 226),       # Red 100
    'grey_text': (100, 116, 139),    # Slate 500
    'grey_bg': (241, 245, 249),      # Slate 100
    'purple': (139, 92, 246),        # Violet 500
    'nuance_bg': (236, 72, 153)      # Pink 500 (for EQ nuance badges)
}

# UNIVERSAL REPORT STRUCTURE DEFINITIONS
SCENARIO_TITLES = {
    "universal": {
        "pulse": "THE PULSE",
        "narrative": "THE NARRATIVE",
        "blueprint": "THE BLUEPRINT"
    }
}


def sanitize_text(text):
    if text is None: return ""
    text = str(text)
    # Extended replacements for common Unicode characters
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2022': '*', '\u2026': '...',
        '\u2010': '-', '\u2011': '-', '\u2012': '-', '\u2015': '-',
        '\u2032': "'", '\u2033': '"', '\u2039': '<', '\u203a': '>',
        '\u00a0': ' ', '\u00b7': '*', '\u2027': '*', '\u25cf': '*',
        '\u25cb': 'o', '\u25a0': '*', '\u25a1': 'o', '\u2713': 'v',
        '\u2714': 'v', '\u2717': 'x', '\u2718': 'x', '\u2192': '->',
        '\u2190': '<-', '\u2194': '<->', '\u21d2': '=>', '\u2212': '-',
        '\u00d7': 'x', '\u00f7': '/', '\u2264': '<=', '\u2265': '>=',
        '\u2260': '!=', '\u00b0': ' deg', '\u00ae': '(R)', '\u00a9': '(C)',
        '\u2122': '(TM)', '\u00ab': '<<', '\u00bb': '>>', '\u201a': ',',
        '\u201e': '"', '\u2020': '+', '\u2021': '++', '\u00b6': 'P',
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    # First try to normalize and encode to ASCII
    try:
        normalized = unicodedata.normalize('NFKD', text)
        # Encode to latin-1, replacing any characters that can't be encoded
        return normalized.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        # Ultimate fallback: strip all non-ASCII
        return ''.join(c if ord(c) < 128 else '?' for c in text)

def build_summary_prompt(role, ai_role, scenario, framework=None, mode="coaching", ai_character="alex"):
    """
    Constructs the system prompt for the initial summary/greeting generation.
    """
    return [
        {"role": "system", "content": f"You are acting as {ai_character.capitalize()}, a professional coach."},
        {"role": "user", "content": f"Generate a brief welcoming sentence for a {scenario} session where the user plays {role} and you play {ai_role}."}
    ]

def sanitize_data(obj):
    """Recursively sanitize all strings in a dictionary or list for PDF compatibility."""
    if isinstance(obj, str):
        return sanitize_text(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_data(item) for item in obj]
    else:
        return obj

def get_score_theme(score):
    try: s = float(score)
    except: s = 0.0
    if s == 0.0: return COLORS['grey_bg'], COLORS['grey_text']
    if s >= 7.0: return COLORS['score_grad_1'], COLORS['score_text'] 
    if s >= 5.0: return (254, 249, 195), (161, 98, 7) 
    return (254, 226, 226), (185, 28, 28) 

def get_bar_color(score):
    try: s = float(score)
    except: s = 0.0
    if s >= 8.0: return COLORS['success']
    if s >= 5.0: return COLORS['warning']
    if s > 0.0: return COLORS['danger']
    return COLORS['grey_text']

def llm_reply(messages, max_tokens=4000):
    try:
        print(f" [DEBUG] llm_reply using LangChain model", flush=True)
        # LangChain accepts list of dicts directly in invoke
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return "{}"

def detect_scenario_type(scenario: str, ai_role: str, role: str) -> str:
    """Detect scenario type based on content to determine report structure."""
    scenario_lower = scenario.lower()
    ai_role_lower = ai_role.lower()
    role_lower = role.lower()
    
    combined_text = f"{scenario_lower} {ai_role_lower} {role_lower}"

    # 1. COACHING SIMULATION (New Scored Format)
    if "good attitude, poor results" in scenario_lower or "sim-01-perf-001" in scenario_lower or "aamir" in scenario_lower or "coaching_sim" in combined_text:
        return "coaching_sim"

    # 1. REFLECTION / MENTORSHIP (No Scorecard)
    # Trigger if AI is strictly a "Coach" or "Mentor" (Role-based)
    if "coach" in ai_role_lower or "mentor" in ai_role_lower:
        return "reflection"
    
    # Trigger if explicit "learning" or "reflection" keywords in text (Topic-based)
    # Note: Avoid "coach" in text search to prevent matching "Manager coaching staff" (which should be Scored)
    reflection_keywords = ["reflection", "learning plan", "development plan", "self-reflection"]
    if any(kw in combined_text for kw in reflection_keywords):
        return "reflection"
    
    # 2. NEGOTIATION / SALES (Scorecard)
    negotiation_keywords = ["sales", "negotiat", "price", "discount", "buyer", "seller", "deal", "purchase"]
    if any(kw in combined_text for kw in negotiation_keywords):
        return "negotiation"
    
    # 3. COACHING / LEADERSHIP (Scorecard)
    # User is the one doing the coaching/managing
    coaching_keywords = ["coaching", "performance", "feedback", "manager", "supervisor", "staff", "employee"]
    if any(kw in combined_text for kw in coaching_keywords):
        return "coaching"
    
    # 4. DE-ESCALATION (Scorecard)
    deescalation_keywords = ["angry", "upset", "complaint", "calm", "de-escalate"]
    if any(kw in combined_text for kw in deescalation_keywords):
        return "custom" # Currently maps to Custom but we can add specific later
    
    # Default
    return "custom"


def detect_user_role_context(role: str, ai_role: str) -> str:
    """Detect the specific sub-role of the user (e.g., Manager vs Staff, Seller vs Buyer)."""
    role_lower = role.lower()
    
    # Coaching Context
    if any(k in role_lower for k in ["manager", "supervisor", "lead", "coach"]):
        return "manager"
    if any(k in role_lower for k in ["staff", "associate", "employee", "report", "subordinate"]):
        return "staff"
        
    # Sales/Negotiation Context
    if any(k in role_lower for k in ["sales", "account executive", "rep", "seller"]):
        return "seller"
    if any(k in role_lower for k in ["customer", "buyer", "client", "prospect"]):
        return "buyer"
        
    return "unknown"

# =====================================================================
# NEW: Parallel Analysis Functions for Speed Optimization
# =====================================================================

def analyze_character_traits(transcript, role, ai_role, scenario, scenario_type):
    """
    Analyze user's character/personality traits and assess fit for the scenario.
    This runs in PARALLEL with main report generation for speed.
    """
    user_msgs = [t for t in transcript if t['role'] == 'user']
    if not user_msgs:
        return {}
    
    conversation = "\n".join([f"USER: {t['content']}" for t in user_msgs])
    
    # Define required traits based on scenario type
    required_traits_map = {
        "coaching": ["Openness to Feedback", "Accountability", "Active Listening", "Growth Mindset"],
        "negotiation": ["Rapport Building", "Active Listening", "Value Focus", "Confidence"],
        "sales": ["Rapport Building", "Active Listening", "Value Focus", "Confidence"],
        "learning": ["Curiosity", "Reflection", "Openness"],
        "mentorship": ["Observation", "Question Asking", "Pattern Recognition"]
    }
    
    required_traits = required_traits_map.get(scenario_type, ["Professional Communication"])
    
    prompt = f"""
You are analyzing a human player's CHARACTER and PERSONALITY in a {scenario_type} simulation.

CRITICAL: IN THE TRANSCRIPT, THE HUMAN PLAYER IS LABELED 'USER' AND PLAYED THE ROLE OF: '{role}'.
CRITICAL: YOU (THE AI) ARE LABELED 'ASSISTANT' AND PLAYED THE ROLE OF: '{ai_role}'.
YOUR EXCLUSIVE JOB IS TO EVALUATE THE HUMAN PLAYER ('USER'). DO NOT EVALUATE YOURSELF.

SCENARIO: {scenario}

REQUIRED TRAITS FOR SUCCESS: {', '.join(required_traits)}

Analyze the human player's ('USER's') character based exclusively on their responses. (Note: Only the USER's lines have been provided for brevity).

CONVERSATION:
{conversation}

Return VALID JSON with this EXACT structure:
{{
  "observed_traits": [
    {{
      "trait": "Trait Name (e.g., Defensiveness, Accountability, Curiosity)",
      "evidence_quote": "EXACT quote from conversation",
      "impact": "Positive" or "Negative",
      "insight": "Why this trait helps or hinders success in this scenario"
    }}
  ],
  "scenario_fit": {{
    "required_traits": {json.dumps(required_traits)},
    "user_strengths": ["Traits they demonstrated well"],
    "user_gaps": ["Traits they're missing or weak in"],
    "fit_score": "X/10",
    "fit_assessment": "Overall assessment of character fit",
    "development_priority": "The #1 character trait they need to develop"
  }},
  "character_development_plan": [
    "Specific behavior change 1 (e.g., Practice phrase: 'That's on me...')",
    "Specific behavior change 2 (e.g., Pause 3 seconds before defending)"
  ]
}}

Be SPECIFIC. Quote EXACT words. No generic advice.
"""
    
    try:
        parser = JsonOutputParser()
        prompt_template = PromptTemplate(
            template="{prompt}\n\n{format_instructions}",
            input_variables=["prompt"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt_template | llm | parser
        result = chain.invoke({"prompt": prompt})
        print(" [SUCCESS] Character analysis completed")
        return result
        
    except Exception as e:
        print(f" [ERROR] Character analysis failed: {e}")
        return {
            "observed_traits": [],
            "scenario_fit": {
                "required_traits": required_traits,
                "user_strengths": [],
                "user_gaps": ["Analysis unavailable"],
                "fit_score": "N/A",
                "fit_assessment": "Unable to analyze",
                "development_priority": "N/A"
            },
            "character_development_plan": []
        }


def analyze_questions_missed(transcript, role, ai_role, scenario, scenario_type):
    """
    Identify questions the user SHOULD have asked but didn't.
    This runs in PARALLEL for speed.
    """
    user_msgs = [t for t in transcript if t['role'] == 'user']
    if not user_msgs:
        return {}
    
    conversation = "\n".join([
        f"{'USER' if t['role'] == 'user' else 'ASSISTANT'}: {t['content']}" 
        for t in transcript
    ])
    
    # Count questions user actually asked
    questions_asked = sum(1 for msg in user_msgs if '?' in msg['content'])
    
    prompt = f"""
You are analyzing QUESTION QUALITY in a {scenario_type} simulation.

CRITICAL: IN THE TRANSCRIPT, THE HUMAN PLAYER IS LABELED 'USER' AND PLAYED THE ROLE OF: '{role}'.
CRITICAL: YOU (THE AI) ARE LABELED 'ASSISTANT' AND PLAYED THE ROLE OF: '{ai_role}'.
YOUR EXCLUSIVE JOB IS TO EVALUATE THE HUMAN PLAYER ('USER'). DO NOT EVALUATE YOURSELF.

SCENARIO: {scenario}

CONVERSATION:
{conversation}

Analyze what QUESTIONS the human player ('USER') SHOULD HAVE ASKED but DIDN'T.


For {scenario_type} scenarios, strong performers ask:
- Open-ended discovery questions (to understand needs)
- Probing questions (to uncover root causes)
- Clarifying questions (to remove ambiguity)
- Vision/Outcome questions (to align on goals)
- Closing/Action questions (to drive commitment)

Return VALID JSON with this EXACT structure:
{{
  "questions_asked_count": {questions_asked},
  "questions_missed": [
    {{
      "question": "The exact question they should have asked",
      "category": "Discovery | Probing | Clarifying | Vision | Closing",
      "timing": "Early | Mid | Late",
      "why_important": "Why this question matters for success",
      "when_to_ask": "At what point in the conversation (e.g., Turn 2, when X happened)",
      "impact_if_asked": "What outcome this question would have enabled"
    }}
  ],
  "question_quality_score": "X/10",
  "question_quality_feedback": "Overall assessment of their questioning approach",
  "questioning_improvement_tip": "Specific advice to ask better questions"
}}

Identify 5-8 HIGH-IMPACT questions they missed. Be SPECIFIC about WHEN and WHY.
Categorize each question and specify optimal timing in the conversation.
"""
    
    try:
        parser = JsonOutputParser()
        prompt_template = PromptTemplate(
            template="{prompt}\n\n{format_instructions}",
            input_variables=["prompt"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt_template | llm | parser
        result = chain.invoke({"prompt": prompt})
        print(" [SUCCESS] Question analysis completed")
        return result
        
    except Exception as e:
        print(f" [ERROR] Question analysis failed: {e}")
        return {
            "questions_asked_count": questions_asked,
            "questions_missed": [],
            "question_quality_score": "N/A",
            "question_quality_feedback": "Analysis unavailable",
            "questioning_improvement_tip": "Ask more open-ended questions to discover deeper needs"
        }


def analyze_full_report_data(transcript, role, ai_role, scenario, framework=None, mode="coaching", scenario_type=None, ai_character="alex"):
    """
    Generate report data using SCENARIO-SPECIFIC structures.
    """
    # Auto-detect scenario type if not provided
    if not scenario_type:
        scenario_type = detect_scenario_type(scenario, ai_role, role)
    
    # Detect granular user role
    user_context = detect_user_role_context(role, ai_role)
    print(f"[INFO] User Context Detected: {user_context} (Scenario: {scenario_type})")

    # CHARACTER SCHEMA OVERRIDE REMOVED - Relying on scenario_type detection
    # if ai_character == 'sarah': ...
    
    # Extract only user messages for focused analysis
    user_msgs = [t for t in transcript if t['role'] == 'user']
    
    # Base metadata
    meta = {
        "scenario_id": scenario_type,
        "outcome_status": "Completed", 
        "overall_grade": "N/A",
        "summary": "Session analysis.",
        "scenario_type": scenario_type,
        "scenario": scenario  # Pass full scenario text to frontend
    }

    if not user_msgs:
        meta["outcome_status"] = "Not Started"
        meta["summary"] = "Session started but no interaction recorded."
        return { "meta": meta, "type": scenario_type }

    # Determine Report Mode based on User Role Context
    # RULE: If User is PERFORMER -> EVALUATION (Scored)
    # RULE: If User is EVALUATOR -> MENTORSHIP (Unscored)
    
    is_user_performer = False
    if scenario_type == "coaching":
        # User is Staff (Performer) vs Manager (Evaluator)
        if user_context == "staff": is_user_performer = True
    elif scenario_type == "negotiation":
        # User is Seller (Performer) vs Buyer (Evaluator)
        if user_context == "seller": is_user_performer = True
    
    # -------------------------------------------------------------
    # BUILD SPECIFIC PROMPTS BASED ON SCENARIO TYPE & ROLE
    # -------------------------------------------------------------
    
    unified_instruction = ""
    
    if scenario_type == "coaching_sim":
        unified_instruction = """
### SCENARIO: COACHING SIMULATION (Good Attitude, Poor Results)
**GOAL**: Evaluate the manager's ability to coach an underperforming but well-meaning employee.
**MODE**: EVALUATION (Scored Simulation).
**CRITICAL RULE**: USE SIMPLE, ACCESSIBLE LANGUAGE. The reader is an everyday employee, not a psychologist. Write in plain, encouraging English. Avoid jargon, overly academic words, or complex long-winded sentences.
**CRITICAL RULE 2**: BE CONCISE AND DIRECT. Keep reasoning, insights, and suggestions to 1-2 crisp, easy-to-read sentences. Do not overwhelm the user with walls of text.
**CRITICAL RULE 3**: ONLY USE THE TRANSCRIPT AND SITUATION. DO NOT HALLUCINATE EXTERNAL FACTORS. Every insight MUST be grounded in what was actually said.
**INSTRUCTIONS**:
1. **BEHAVIORAL RULES**: The user must balance empathy with clear performance facts and actionable follow-ups.
2. **SCORECARD EXACT DIMENSIONS**: You MUST output EXACTLY 6 dimensions: 'Empathy & Respect', 'Clarity with Facts', 'Coaching Questions', 'Ownership Creation', 'Action Plan Quality', 'Follow-up Discipline'. Each dimension out of 10.
3. **TONE**: Supportive & Constructive. Focus on actionable growth.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "coaching_sim", "outcome_status": "Completed/Incomplete", "overall_grade": "X/10", "summary": "Executive summary of the coaching effectiveness." },
  "type": "coaching_sim",
  "executive_summary": {
    "snapshot": "...", "final_score": "X/10", "strengths_summary": "...", "improvements_summary": "...", "outcome_summary": "..."
  },
  "goal_attainment": {
    "score": "X/10", "expectation_vs_reality": "...", "primary_gaps": ["...", "..."], "observation_focus": ["...", "..."]
  },
  "coaching_style": {
    "primary_style": "Directive | Supportive | Avoidant | Balanced",
    "description": "Why this style was dominant based purely on the transcript."
  },
  "deep_dive_analysis": [
    {"topic": "Psychological Safety Creation", "tone": "...", "language_impact": "...", "comfort_level": "...", "impact": "...", "questions_asked": "...", "exploration": "...", "understanding_depth": "...", "analysis": "..."}
  ],
  "pattern_summary": "Brief summary of their dominant behavioural pattern.",
  "behaviour_analysis": [
    {
      "behavior": "Name of the behavior",
      "quote": "The exact verbatim line from the transcript demonstrates this.",
      "insight": "Detailed psychological breakdown based purely on the text.",
      "impact": "Positive/Negative",
      "improved_approach": "The exact phrase they SHOULD have used."
    }
  ],
  "turning_points": [
    {"point": "e.g., Conversation shifted defensively when...", "timestamp": "Brief context of when it happened in transcript"}
  ],
  "eq_analysis": [
    {
      "nuance": "Current Emotion",
      "observation": "Quote proving this emotion.",
      "suggestion": "Recommended emotional shift."
    }
  ],
  "heat_map": [
    { "dimension": "Empathy", "score": 8 }
  ],
  "scorecard": [
    { 
      "dimension": "Empathy & Respect", 
      "score": "X/10", 
      "reasoning": "...",
      "quote": "...",
      "suggestion": "...",
      "alternative_questions": [{"question": "...", "rationale": "..."}]
    }
  ],
  "ideal_questions": ["Better question 1", "Better question 2"],
  "action_plan": {
    "specific_actions": ["..."], "owner": "...", "timeline": "...", "success_indicators": ["..."]
  },
  "follow_up_strategy": {
    "review_cadence": "...", "metrics_to_track": ["..."], "accountability_method": "..."
  },
  "strengths_and_improvements": {
    "strengths": ["...", "..."], "missed_opportunities": ["...", "..."]
  },
  "final_evaluation": {
    "readiness_level": "...", "maturity_rating": "X/10", "immediate_focus": ["..."], "long_term_suggestion": "..."
  }
}
"""

    elif scenario_type == "coaching":
        if is_user_performer: # User is STAFF
            unified_instruction = """
### SCENARIO: COACHABILITY ASSESSMENT (USER IS STAFF)
**GOAL**: Evaluate the user's openness to feedback and their ability to pivot behavior.
**MODE**: EVALUATION (Growth-Oriented Assessment).
**CRITICAL RULE**: USE SIMPLE, ACCESSIBLE LANGUAGE. The reader is an everyday employee. Write in plain, encouraging English. Avoid jargon, overly academic words, or complex long-winded sentences.
**CRITICAL RULE 2**: BE CONCISE AND DIRECT. Keep reasoning, insights, and suggestions to 1-2 crisp, easy-to-read sentences. 
**INSTRUCTIONS**:
1. **BEHAVIORAL ANALYSIS**: Focus on simple communication signals (tone, pauses, word choice). 
2. **SCORECARD**: Every score MUST have a "Proof" (quote) and a "Growth Tactic" (specific alternative action).
3. **JUSTIFY WEAKNESS**: Keep it simple. "You seemed defensive when I asked X, because you replied [quote]."
4. **ACTIONABLE TIPS**: Do NOT give generic advice (e.g., "Listen better"). Give specific 1-2 sentence DRILLS.
5. **TONE**: Supportive & Constructive. Focus on actionable growth.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "coaching", "outcome_status": "Success/Partial/Failure", "overall_grade": "X/10", "summary": "A high-level executive summary of their coachability profile." },
  "type": "coaching",
  "eq_analysis": [
    {
      "nuance": "Current Emotion (e.g., Defensive)",
      "observation": "Quote proving this emotion.",
      "suggestion": "Recommended emotional shift."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Name of the behavior (e.g., Defensive Deflection, Active Evaluation)",
      "quote": "The exact verbatim line from the transcript demonstrates this.",
      "insight": "Detailed psychological breakdown of why this behavior undermines or aids growth.",
      "impact": "Positive/Negative",
      "improved_approach": "The exact phrase they SHOULD have used to build trust."
    }
  ],
  "detailed_analysis": [
    {"topic": "Psychological Safety Creation", "analysis": "Did they make it safe to give feedback?"},
    {"topic": "Ownership & Accountability", "analysis": "Did they own the problem or blame external factors?"}
  ],
  "scorecard": [
    { 
      "dimension": "Professionalism", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation of why this score was given. Cite specific evidence.",
      "quote": "The EXACT verbatim line from the transcript that demonstrates this dimension (good or bad).",
      "suggestion": "Write a simple 1-2 sentence tip explaining what they should say next time.",
      "alternative_questions": [{"question": "I appreciate that perspective...", "rationale": "Validates before disagreeing"}]
    },
    { 
      "dimension": "Ownership", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation. Show exactly how they handled responsibility.",
      "quote": "The line where they accepted or dodged responsibility. Must be verbatim.",
      "suggestion": "Write a simple 1-2 sentence tip telling them what to say next time.",
      "alternative_questions": [{"question": "That's on me, here is my plan...", "rationale": "Total accountability"}]
    },
    { 
      "dimension": "Active Listening", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation of whether they listened or interrupted.",
      "quote": "Evidence of listening (e.g., a reflective statement) or interrupting (the exact interruption).",
      "suggestion": "Write a simple 1-2 sentence tip prescribing a better listening technique.",
      "alternative_questions": [{"question": "So what you're seeing is...", "rationale": "Reflective listening loop"}]
    },
    { 
      "dimension": "Solution Focus", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation about the quality of their proposed solutions.",
      "quote": "The specific proposal they made (verbatim).",
      "suggestion": "Write a simple 1-2 sentence tip giving an alternative approach.",
      "alternative_questions": [{"question": "What does success look like to you?", "rationale": "Collaborative problem solving"}]
    }
  ],
  "strengths": ["Write a detailed 1-2 sentence description of high-impact strength 1...", "Write a detailed 1-2 sentence description of high-impact strength 2..."],
  "missed_opportunities": ["Write a detailed 1-2 sentence description of missed opportunity 1...", "Write a detailed 1-2 sentence description of missed opportunity 2..."],
  "actionable_tips": ["Write a detailed 1-2 sentence paragraph for Tactic 1...", "Write a detailed 1-2 sentence paragraph for Tactic 2..."]
}
"""
        else: # User is MANAGER (Evaluator -> Mentorship)
            unified_instruction = """
### SCENARIO: LEADERSHIP MENTORSHIP (USER IS MANAGER)
**GOAL**: specific guidance on improving the user's coaching style.
**MODE**: MENTORSHIP (No Scorecard).
**INSTRUCTIONS**:
1. **REFLECTIVE QUESTIONS**: Include a brief "Reference Answer" or "Key Insight" in parentheses for each question to guide self-reflection.
2. **PRACTICE PLAN**: Must be highly actionable, valid, and specific (e.g., "Use the 5-Whys technique...").

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "learning", "outcome_status": "Completed", "overall_grade": "N/A", "summary": "..." },
  "type": "learning",
  "eq_analysis": [
    {
      "nuance": "Detected Tone",
      "observation": "Evidence quote.",
      "suggestion": "How to shift tone."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Name of the behavior (e.g., Empathy)",
      "quote": "The exact sentence the user said.",
      "insight": "Why this mattered.",
      "impact": "Positive/Negative",
      "improved_approach": "Alternative phrasing."
    }
  ],
  "detailed_analysis": [
    {"topic": "Coaching Style", "analysis": "Analysis content..."},
    {"topic": "Empathy & Connection", "analysis": "Analysis content..."}
  ],
  "key_insights": ["Insight 1...", "Insight 2..."],
  "reflective_questions": ["Question 1? (Reference: Key principle...)", "Question 2? (Insight: Look for...)"],
  "growth_outcome": "Vision of the user as a better leader...",
  "practice_plan": ["Actionable Drill 1...", "Specific Technique 2..."]
}
"""
            # Override semantic type for Report.tsx to render Learning View
            scenario_type = "learning" 

    elif scenario_type == "negotiation": 
        if is_user_performer: # User is SELLER
            unified_instruction = """
### SCENARIO: SALES PERFORMANCE ASSESSMENT (USER IS SELLER)
**GOAL**: Generate a High-Performance Sales Audit.
**MODE**: EVALUATION (Commercial Excellence).
**CRITICAL RULE**: USE SIMPLE, ACCESSIBLE LANGUAGE. The reader is an everyday employee. Write in plain, encouraging English. Avoid jargon, overly complex words, or long-winded sentences.
**CRITICAL RULE 2**: BE CONCISE AND DIRECT. Keep reasoning, insights, and suggestions to 1-2 crisp, easy-to-read sentences. Do not overwhelm the user with walls of text.
**INSTRUCTIONS**:
1. **REVENUE FOCUS**: Evaluate every behavior based on its likelihood to CLOSE THE DEAL or KILL THE DEAL.
2. **EVIDENCE**: You cannot give a score without citing the exact quote that justifies it.
3. **JUSTIFY THE LOSS**: If they lost the deal, explain exactly where they lost it in 1-2 sentences. 
4. **RECOMMENDATIONS**: Must be commercially focused and specific. "Ask open questions" is bad. "Ask 'How does this impact your Q3 goals?'" is good.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "sales", "outcome_status": "Closed/Negotiating/Lost", "overall_grade": "X/10", "summary": "Executive summary of commercial impact." },
  "type": "sales",
  "eq_analysis": [
    {
      "nuance": "Buyer Sentiment / User EQ",
      "observation": "Evidence of emotional read.",
      "suggestion": "How to better align with buyer emotion."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Name of the behavior (e.g., Feature Dumping, Strategic Pausing)",
      "quote": "The exact sentence used.",
      "insight": "Why this behavior increased or decreased deal velocity.",
      "impact": "Positive/Negative",
      "improved_approach": "The winning line they should have used."
    }
  ],
  "suggested_questions": [
    "A specific, commercial question the user SHOULD HAVE ASKED.",
    "A high-impact discovery question they missed."
  ],
  "detailed_analysis": [
    {"topic": "Sales Methodology", "analysis": "Did they follow a structured path (e.g., MEDDIC/SPIN)?"},
    {"topic": "Value Proposition", "analysis": "Did they sell the 'Why' or just the 'What'?"}
  ],
  "scorecard": [
    { 
      "dimension": "Rapport Building", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation PROVING WHY this score was given.",
      "quote": "The exact rapport attempt (or lack thereof). Must be verbatim from transcript.",
      "suggestion": "Write a simple 1-2 sentence tip telling them EXACTLY what to say instead.",
      "alternative_questions": [{"question": "I noticed you... How is that impacting X?", "rationale": "Connects observation to business pain"}]
    },
    { 
      "dimension": "Needs Discovery", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation PROVING WHY this score was given. Did they ask good questions?",
      "quote": "The critical discovery question asked or missed. Must be word-for-word from the transcript.",
      "suggestion": "Write a simple 1-2 sentence tip giving them the EXACT question they should have asked.",
      "alternative_questions": [{"question": "What happens if you don't solve this?", "rationale": "Implication question (SPIN)"}]
    },
    { 
      "dimension": "Value Articulation", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation PROVING WHY this score was given.",
      "quote": "The value pitch. Exact words from transcript.",
      "suggestion": "Write a simple 1-2 sentence tip prescribing the EXACT value statement.",
      "alternative_questions": [{"question": "Based on what you said about X, here is how Y helps...", "rationale": "Direct solution mapping"}]
    },
    { 
      "dimension": "Objection Handling", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation PROVING WHY this score was given.",
      "quote": "Their response to the pushback. Word-for-word.",
      "suggestion": "Write a simple 1-2 sentence tip giving them the EXACT objection handling script.",
      "alternative_questions": [{"question": "It sounds like cost is a major factor...", "rationale": "Labeling the objection"}]
    },
    { 
      "dimension": "Closing", 
      "score": "X/10", 
      "reasoning": "Write a clear, 1-2 sentence explanation PROVING WHY this score was given.",
      "quote": "The closing line. Must be verbatim.",
      "suggestion": "Write a simple 1-2 sentence tip giving them the EXACT close.",
      "alternative_questions": [{"question": "Does it make sense to start the paperwork?", "rationale": "Assumptive Close"}]
    }
  ],
  "sales_recommendations": ["Write a detailed 3-4 sentence paragraph for Commercial Insight 1...", "Write a detailed 3-4 sentence paragraph for Commercial Insight 2...", "Write a detailed 3-4 sentence paragraph for Commercial Insight 3..."]
}
"""
        else: # User is BUYER (Evaluator -> Mentorship)
            unified_instruction = """
### SCENARIO: BUYER STRATEGY MENTORSHIP (USER IS BUYER)
**GOAL**: specific guidance on how to negotiate better deals as a buyer.
**MODE**: MENTORSHIP (No Scorecard).
**INSTRUCTIONS**:
1. **REFLECTIVE QUESTIONS**: Provide a "Reference Insight" for each question.
2. **PRACTICE PLAN**: Detailed, realistic tactics for a buyer.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "learning", "outcome_status": "Completed", "overall_grade": "N/A", "summary": "..." },
  "type": "learning",
  "eq_analysis": [
    {
      "nuance": "Negotiation stance",
      "observation": "Evidence.",
      "suggestion": "Adjustment."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Behavior Name",
      "quote": "Evidence quote.",
      "insight": "Analysis.",
      "impact": "Positive/Negative",
      "improved_approach": "Suggestion."
    }
  ],
  "detailed_analysis": [
    {"topic": "Negotiation Power", "analysis": "Analysis content..."},
    {"topic": "Leverage Usage", "analysis": "Analysis content..."}
  ],
  "key_insights": ["Insight 1...", "Insight 2..."],
  "reflective_questions": ["Question? (Insight: Power leverage comes from...)", "Question? (Reference: BATNA...)"],
  "growth_outcome": "Vision of the user as a stronger negotiator...",
  "practice_plan": ["Tactic: Walk away when...", "Drill: Ask for 3 concessions..."]
}
"""
            # Override semantic type for Report.tsx to render Learning View
            scenario_type = "learning"

    elif scenario_type == "mentorship":
        unified_instruction = """
### SCENARIO: EXPERT MENTORSHIP (REVERSE ROLE)
**GOAL**: Generate a "Key Takeaways" summary for the user who observed the AI.
**MODE**: MENTORSHIP (Observation).
**INSTRUCTIONS**:
1. **NO SCORES**: Do not grade the user (or the AI).
2. **FOCUS**: Explain the *strategy* behind what the AI did.
3. **SUGGESTED QUESTIONS**: List questions the user *could have asked* to learn more.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "mentorship", "outcome_status": "Completed", "overall_grade": "N/A", "summary": "Brief summary of the lesson demonstrated." },
  "type": "mentorship",
  "eq_analysis": [
    {
      "nuance": "Expert Emotional Control",
      "observation": "How the expert handled emotion.",
      "suggestion": "What you can learn from this."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Key Technique Demonstrated",
      "quote": "The exact line the AI (Expert) used.",
      "insight": "Why this technique works.",
      "impact": "Positive",
      "improved_approach": "N/A"
    }
  ],
  "suggested_questions": [
    "Question you could ask to deeper understand the strategy...",
    "Question about alternative approaches..."
  ],
  "detailed_analysis": [
    {"topic": "Strategic Intent", "analysis": "Why the AI chose this path..."},
    {"topic": "Key Principles", "analysis": "The core rules applied here..."}
  ],
  "key_insights": ["Principle 1...", "Principle 2..."],
  "reflective_questions": ["How would you have handled X differently?", "What did you notice about Y?"],
  "growth_outcome": "Understanding of expert-level execution.",
  "practice_plan": ["Try this technique in your next real conversation..."]
}
"""

    elif scenario_type == "reflection" or scenario_type == "learning":
        unified_instruction = """
### SCENARIO: PERSONAL LEARNING PLAN
**GOAL**: Generate a Developmental Learning Plan.
**MODE**: MENTORSHIP (Supportive, Qualitative Only).
**INSTRUCTIONS**:
1. **REFLECTIVE QUESTIONS**: Include a self-reflection prompt and a reference insight.
2. **PRACTICE PLAN**: Valid, specific, and actionable exercises.

**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "learning", "outcome_status": "Completed", "overall_grade": "N/A", "summary": "..." },
  "type": "learning",
  "eq_analysis": [
    {
      "nuance": "Self-Reflection Tone",
      "observation": "Evidence.",
      "suggestion": "Adjustment."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Behavior Name",
      "quote": "Evidence quote.",
      "insight": "Analysis.",
      "impact": "Positive/Negative",
      "improved_approach": "Suggestion."
    }
  ],
  "detailed_analysis": [
    {"topic": "Conversation Flow", "analysis": "Analysis content..."},
    {"topic": "Key Patterns", "analysis": "Analysis content..."}
  ],
  "key_insights": ["Pattern observed...", "Strength present..."],
  "reflective_questions": ["Question? (Insight: ...)", "Question? (Ref: ...)"],
  "practice_plan": ["Experiment 1: Try...", "Micro-habit: When X, do Y..."],
  "growth_outcome": "Vision of success..."
}
"""
    else: # Custom
        unified_instruction = """
### CUSTOM SCENARIO / ROLE PLAY
**GOAL**: Generate an Adaptive Feedback Report.
**OUTPUT JSON STRUCTURE**:
{
  "meta": { "scenario_id": "custom", "outcome_status": "Success/Partial", "overall_grade": "N/A", "summary": "..." },
  "type": "custom",
  "eq_analysis": [
    {
      "nuance": "Detected Emotion",
      "observation": "Evidence.",
      "suggestion": "Advice."
    }
  ],
  "behaviour_analysis": [
    {
      "behavior": "Behavior Name",
      "quote": "Evidence quote.",
      "insight": "Analysis.",
      "impact": "Positive/Negative",
      "improved_approach": "Suggestion."
    }
  ],
  "detailed_analysis": [
    {"topic": "Performance Overview", "analysis": "Analysis content..."},
    {"topic": "Specific Observations", "analysis": "Analysis content..."}
  ],
  "strengths_observed": ["..."],
  "development_opportunities": ["..."],
  "guidance": {
    "continue": ["..."],
    "adjust": ["..."],
    "try_next": ["..."]
  }
}
"""

    # ANALYST PERSONA (Layered on top of Scenario Logic)
    # The 'Content' (what is measured) is determined by the Scenario (above).
    # The 'Voice' (how it is written) is determined by the Character (below).
    
    analyst_persona = ""
    if ai_character == "sarah":
        analyst_persona = """
    ### ANALYST STYLE: COACH SARAH (MENTOR)
    - **Tone**: Warm, encouraging, high-EQ, "Sandwich Method" (Praise-Critique-Praise).
    - **Focus**: Psychological safety, "growth mindset", and emotional intelligence.
    - **Detail Level**: EXTREMELY HIGH. Write 2-3 distinct topic sections in `detailed_analysis`. Go deep into the "why" behind the user's choices.
    - **Signature**: Use phrases like "I just loved how you...", "Consider trying...", "A small tweak could be...".
    - **Evidence Requirement**: You MUST quote the user's exact words to support every insight. No generic praise.
    - **Tactical Advice**: Provide specific "Micro-Scripts" (e.g., "Next time say: 'I hear you...'") instead of general advice.
    """
    else: # Default to Alex
        analyst_persona = """
    ### ANALYST STYLE: COACH ALEX (EVALUATOR)
    - **Tone**: Professional, direct, analytical, "Bottom Line Up Front".
    - **Focus**: Efficiency, clear outcomes, negotiation leverage, and rapid improvement.
    - **Detail Level**: EXTREMELY HIGH. Audit the conversation mechanism by mechanism.
    - **Signature**: Use phrases like "The metrics show...", "You missed an opportunity to...", "To optimize, you must...".
    - **Evidence Requirement**: Every score or critique MUST be backed by a timestamped quote from the transcript.
    - **Tactical Advice**: Provide "High-Impact Power Moves" or specific phrasing adjustments. No fluff.
    """

    # Unified System Prompt
    system_prompt = (
        f"### SYSTEM ROLE\\n"
        f"You are {ai_character.title() if ai_character else 'The AI'}, an expert Soft Skills Coach. You just facilitated a roleplay simulation.\\n"
        f"CRITICAL: IN THE TRANSCRIPT, THE HUMAN PLAYER IS LABELED 'USER' AND PLAYED THE ROLE OF: '{role}'.\\n"
        f"CRITICAL: YOU (THE AI) ARE LABELED 'ASSISTANT' AND PLAYED THE ROLE OF: '{ai_role}'.\\n"
        f"YOUR EXCLUSIVE JOB IS TO EVALUATE THE HUMAN PLAYER ('USER'). DO NOT EVALUATE YOURSELF ('ASSISTANT').\\n"
        f"Context: {scenario}\\n"
        f"{analyst_persona}\\n"
        f"{unified_instruction}\\n"
        f"### GENERAL RULES\\n"
        "1. **STRICT TRANSCRIPT GROUNDING**: You MUST base EVERY score and insight SOLELY on the words the user actually spoke in the transcript below. DO NOT hallucinate, assume, or invent interactions that did not happen.\\n"
        "2. **VERBATIM QUOTES**: Every scorecard dimension and behavior analysis MUST contain an exact, verbatim quote from the transcript proving your point. If the user failed a dimension because they didn't do it, state: 'You did not attempt this.'\\n"
        "3. **JUSTIFICATION**: Do not just say 'Good job'. Explain 'You scored 8/10 because you asked X question at the start...'.\\n"
        "4. **DEPTH**: Avoid surface-level observations. Analyze subtext, tone, and strategy based on their explicit word choices.\\n"
        "5. **EQ & NUANCE**: You MUST include the 'eq_analysis' section. Identify the user's *current emotion/tone* and provide a specific *emotional adjustment* to improve.\\n"
        "6. **FORMAT**: OUTPUT MUST BE VALID JSON ONLY.\\n"
    )

    try:
        # Create conversation text for analysis
        full_conversation = "\\n".join([f"{'USER' if t['role'] == 'user' else 'ASSISTANT'}: {t['content']}" for t in transcript])
        
        # Setup LangChain Parser
        parser = JsonOutputParser()
        
        # Create Prompt Template
        prompt = PromptTemplate(
            template="{system_prompt}\n\n{format_instructions}\n\n### FULL CONVERSATION\n{conversation}",
            input_variables=["system_prompt", "conversation"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # Create Chain WITHOUT parser initially - we'll handle JSON parsing manually
        chain_raw = prompt | llm
        
        # Invoke Chain - MAIN REPORT (Core scorecard and behavior)
        print(f" [INFO] Starting PARALLEL report generation (3 LLM calls)...", flush=True)
        
        # ===== PARALLEL EXECUTION FOR SPEED =====
        # Run 3 analysis functions in parallel:
        # 1. Main report (scorecard, behavior analysis)
        # 2. Character assessment (NEW)
        # 3. Question analysis (NEW)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all 3 tasks  
            future_main = executor.submit(
                lambda: chain_raw.invoke({
                    "system_prompt": system_prompt,
                    "conversation": full_conversation
                })
            )
            
            future_character = executor.submit(
                analyze_character_traits,
                transcript, role, ai_role, scenario, scenario_type
            )
            
            future_questions = executor.submit(
                analyze_questions_missed,
                transcript, role, ai_role, scenario, scenario_type
            )
            
            # Wait for all to complete
            t1 = dt.datetime.now()
            raw_response = future_main.result()
            t2 = dt.datetime.now()
            print(f" [PERF] Main Report Generation took: {(t2-t1).total_seconds():.2f}s")
            
            character_analysis = future_character.result()
            t3 = dt.datetime.now()
            print(f" [PERF] Character Analysis took: {(t3-t2).total_seconds():.2f}s (relative to main)")
            
            question_analysis = future_questions.result()
            t4 = dt.datetime.now()
            print(f" [PERF] Question Analysis took: {(t4-t3).total_seconds():.2f}s (relative to char)")
        
        print(f" [SUCCESS] All analyses completed in parallel!", flush=True)
        
        # === ROBUST JSON PARSING WITH CLEANUP ===
        try:
            # Extract text content from LLM response
            if hasattr(raw_response, 'content'):
                json_text = raw_response.content
            else:
                json_text = str(raw_response)
            
            # Log first 500 chars for debugging
            print(f" [DEBUG] Raw LLM response (first 500 chars): {json_text[:500]}", flush=True)
            
            # Clean up common JSON formatting issues:
            # 1. Remove markdown code fences (```json ... ```)
            json_text = re.sub(r'^```(?:json)?\\s*', '', json_text.strip())
            json_text = re.sub(r'```\\s*$', '', json_text.strip())
            
            # 2. Fix escaped quotes at start/end of string values: "key": \\"value\\" -> "key": "value"
            # This is the main issue causing the parse error
            json_text = re.sub(r':\\s*\\\\"([^"]*)\\\\"', r': "\\1"', json_text)
            
            # 3. Parse the cleaned JSON
            data = json.loads(json_text)
            print(f" [SUCCESS] JSON parsed successfully after cleanup", flush=True)
            
        except json.JSONDecodeError as je:
            print(f" [ERROR] JSON Parse Error after cleanup: {je}", flush=True)
            print(f" [ERROR] Problematic JSON (first 1000 chars): {json_text[:1000]}", flush=True)
            
            # Last resort: try LangChain's parser
            try:
                data = parser.parse(json_text)
                print(f" [SUCCESS] LangChain parser succeeded as fallback", flush=True)
            except Exception as parser_error:
                print(f" [ERROR] LangChain parser also failed: {parser_error}", flush=True)
                # Re-raise original error with more context
                raise je
        
        # Ensure meta exists
        if 'meta' not in data: data['meta'] = {}
        data['meta']['scenario_type'] = scenario_type
        # Add type if missing
        if 'type' not in data: data['type'] = scenario_type

        # ==== MERGE NEW ANALYSES INTO REPORT ====
        if character_analysis:
            data['character_assessment'] = character_analysis
        
        if question_analysis:
            data['question_analysis'] = question_analysis

        return data
        
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        # Note: 'response' variable doesn't exist in this version, removing that debug line
        return {
            "meta": {
                "scenario_id": scenario_type,
                "outcome_status": "Failure", 
                "overall_grade": "F",
                "summary": "Error generating report. Please try again.",
                "scenario_type": scenario_type
            },
            "type": scenario_type
        }


class DashboardPDF(FPDF):
    def cell(self, w, h=0, txt='', border=0, ln=0, align='', fill=False, link=''):
        # Auto-sanitize all text going into cells
        txt = sanitize_text(txt) if txt else ''
        super().cell(w, h, txt, border, ln, align, fill, link)
    
    def multi_cell(self, w, h, txt, border=0, align='J', fill=False):
        # Auto-sanitize all text going into multi_cells  
        txt = sanitize_text(txt) if txt else ''
        # Use provided align, default to Justified if not specified for long text
        super().multi_cell(w, h, txt, border, align, fill)
    
    def footer(self):
        self.set_y(-15)
        # Add subtle line separator
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-12)
        # Page number on left
        self.set_font('Arial', '', 8)
        self.set_text_color(128, 128, 128)
        super().cell(30, 10, f'Page {self.page_no()}', 0, 0, 'L')
        # Branding in center
        self.set_font('Arial', 'I', 8)
        super().cell(140, 10, 'Generated by CoAct.AI Coaching Engine', 0, 0, 'C')
        # Timestamp on right
        self.set_font('Arial', '', 7)
        super().cell(0, 10, dt.datetime.now().strftime('%Y-%m-%d'), 0, 0, 'R')

    def set_scenario_type(self, scenario_type):
        self.scenario_type = scenario_type

    def get_title(self, section_key):
        stype = getattr(self, 'scenario_type', 'custom')
        return SCENARIO_TITLES.get(stype, SCENARIO_TITLES['custom']).get(section_key, section_key.upper())

    def linear_gradient(self, x, y, w, h, c1, c2, orientation='H'):
        self.set_line_width(0)
        if orientation == 'H':
            for i in range(int(w)):
                r = c1[0] + (c2[0] - c1[0]) * (i / w)
                g = c1[1] + (c2[1] - c1[1]) * (i / w)
                b = c1[2] + (c2[2] - c1[2]) * (i / w)
                self.set_fill_color(int(r), int(g), int(b))
                self.rect(x + i, y, 1, h, 'F')
        else:
            for i in range(int(h)):
                r = c1[0] + (c2[0] - c1[0]) * (i / h)
                g = c1[1] + (c2[1] - c1[1]) * (i / h)
                b = c1[2] + (c2[2] - c1[2]) * (i / h)
                self.set_fill_color(int(r), int(g), int(b))
                self.rect(x, y + i, w, 1, 'F')

    def set_user_name(self, name):
        self.user_name = sanitize_text(name)

    def set_character(self, character):
        self.ai_character = sanitize_text(character).capitalize()

    def header(self):
        if self.page_no() == 1:
            # Premium gradient header
            self.linear_gradient(0, 0, 210, 40, COLORS['header_grad_1'], COLORS['header_grad_2'], 'H')
            # Main title
            self.set_xy(10, 8)
            self.set_font('Arial', 'B', 24)
            self.set_text_color(255, 255, 255)
            super().cell(0, 10, 'COACT.AI', 0, 0, 'L')
            # Subtitle - Dynamic based on Coach
            self.set_xy(10, 22)
            self.set_font('Arial', '', 11)
            self.set_text_color(147, 197, 253)
            
            coach_name = getattr(self, 'ai_character', 'Alex')
            super().cell(0, 5, f'Performance Analysis by Coach {coach_name}', 0, 0, 'L')
            
            # Date on right
            self.set_xy(140, 10)
            self.set_font('Arial', '', 9)
            self.set_text_color(200, 220, 255)
            super().cell(50, 5, dt.datetime.now().strftime('%B %d, %Y'), 0, 0, 'R')
            
            # User Name Display
            if hasattr(self, 'user_name') and self.user_name:
                self.set_xy(140, 16)
                self.set_font('Arial', 'I', 9)
                super().cell(50, 5, f"Prepared for: {self.user_name}", 0, 0, 'R')

            # Avatar Image (Removed as per request)
            # if hasattr(self, 'ai_character'):
            #     char_name = self.ai_character.lower()
            #     img_path = f"{char_name}.png"
            #     if os.path.exists(img_path):
            #          self.image(img_path, x=188, y=8, w=15)

            self.ln(35)
        else:
            # Slim header for subsequent pages
            self.set_fill_color(*COLORS['header_grad_1'])
            self.rect(0, 0, 210, 14, 'F')
            self.set_xy(10, 4)
            self.set_font('Arial', 'B', 10)
            self.set_text_color(255, 255, 255)
            super().cell(100, 6, 'CoAct.AI Report', 0, 0, 'L')
            
            # Avatar Icon Scalling Small (Removed)
            # if hasattr(self, 'ai_character'):
            #     char_name = self.ai_character.lower()
            #     img_path = f"{char_name}.png"
            #     if os.path.exists(img_path):
            #         self.image(img_path, x=5, y=2, w=10)
                    
            # Page indicator
            self.set_font('Arial', '', 9)
            self.set_text_color(180, 200, 255)
            super().cell(0, 6, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(18)

    def set_context(self, role, ai_role, scenario):
        self.user_role = sanitize_text(role)
        self.ai_role = sanitize_text(ai_role)
        self.scenario_text = sanitize_text(scenario)

    def check_space(self, height):
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def draw_context_summary(self):
        """Draw a summary of the scenario context and roles."""
        if not hasattr(self, 'user_role'): return
        
        self.check_space(40)
        self.ln(5)
        
        # Section Header
        self.set_font('Arial', 'B', 10)
        self.set_text_color(71, 85, 105) # Slate 600
        self.cell(0, 6, "SCENARIO CONTEXT", 0, 1)
        
        # Grid Background
        self.set_fill_color(248, 250, 252) # Slate 50
        start_y = self.get_y()
        self.rect(10, start_y, 190, 35, 'F')
        
        # Draw Roles
        self.set_xy(15, start_y + 4)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*COLORS['primary'])
        self.cell(20, 5, "Your Role:", 0, 0)
        self.set_font('Arial', '', 9)
        self.set_text_color(*COLORS['text_main'])
        self.cell(60, 5, self.user_role, 0, 0)
        
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*COLORS['primary'])
        self.cell(20, 5, "Partner:", 0, 0)
        self.set_font('Arial', '', 9)
        self.set_text_color(*COLORS['text_main'])
        self.cell(60, 5, self.ai_role, 0, 1)
        
        # Draw Scenario Description
        self.set_xy(15, start_y + 12)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*COLORS['primary'])
        self.cell(0, 5, "Situation:", 0, 1)
        
        self.set_x(15)
        self.set_font('Arial', '', 9)
        self.set_text_color(*COLORS['text_light'])
        # Truncate if too long to fit in box
        # Truncate if too long to fit in box
        text = self.scenario_text
        
        # Clean up text: Remove CONTEXT: prefix and AI BEHAVIOR section
        # The user wants JUST the situation, not the "CONTEXT" label or "AI BEHAVIOR" section.
        text = text.replace("CONTEXT:", "").replace("Situation:", "").strip()
        
        # Split by typical behavioral markers to ensure we only get the situation description
        for marker in ["AI BEHAVIOR:", "AI ROLE:", "USER ROLE:", "SCENARIO:"]:
            if marker in text:
                text = text.split(marker)[0].strip()
        
        if len(text) > 300: text = text[:297] + "..."
        self.multi_cell(180, 5, text)
        
        # Move cursor past the box
        self.set_y(start_y + 40)

    def draw_scoring_methodology(self):
        """Draw the scoring rubric/methodology section."""
        self.check_space(50)
        self.ln(5)
        
        self.draw_section_header("SCORING METHODOLOGY (THE 'WHY')", COLORS['secondary'])
        
        # Grid Background
        self.set_fill_color(248, 250, 252)
        start_y = self.get_y()
        self.rect(10, start_y, 190, 35, 'F')
        
        # Scoring Levels
        levels = [
            ("9-10 (Expert)", "Exceptional application of skills. Creates deep psychological safety, handles conflict with mastery, and drives clear outcomes."),
            ("7-8 (Proficient)", "Strong performance. Meets all core objectives effectively. Good empathy and strategy, with minor opportunities for refinement."),
            ("4-6 (Competent)", "Functional performance. Achieves basic goals but may miss subtle cues, sound robotic, or struggle with difficult objections."),
            ("1-3 (Needs Ops)", "Struggles with core skills. May be defensive, dismissive, or completely miss the objective. Immediate practice required.")
        ]
        
        current_y = start_y + 4
        
        for grade, desc in levels:
            self.set_xy(15, current_y)
            self.set_font('Arial', 'B', 8)
            
            # Color coding for levels
            if "9-10" in grade: self.set_text_color(*COLORS['success'])
            elif "7-8" in grade: self.set_text_color(*COLORS['success']) # Lighter green ideally, but success works
            elif "4-6" in grade: self.set_text_color(*COLORS['warning'])
            else: self.set_text_color(*COLORS['danger'])
            
            self.cell(25, 6, grade, 0, 0)
            
            self.set_font('Arial', '', 8)
            self.set_text_color(*COLORS['text_light'])
            self.cell(3, 6, "|", 0, 0)
            
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(150, 6, desc)
            current_y += 7

        self.set_y(start_y + 42)

    def draw_detailed_analysis(self, analysis_data):
        """Draw the detailed analysis section (Supporting string or list of topics)."""
        if not analysis_data: return
        
        # 1. Handle Legacy String Format (Backward Compatibility)
        if isinstance(analysis_data, str):
            self.check_space(60)
            self.ln(5)
            self.draw_section_header("DETAILED ANALYSIS", COLORS['secondary'])
            
            # Background Box
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(226, 232, 240)
            self.rect(10, self.get_y(), 190, 45, 'DF') # Fixed height fallback
            
            # Icon
            self.set_xy(15, self.get_y() + 5)
            self.set_font('Arial', 'B', 14)
            self.set_text_color(*COLORS['secondary'])
            self.cell(10, 10, "i", 0, 0, 'C') 
            
            # Text
            self.set_xy(25, self.get_y() + 2)
            self.set_font('Arial', '', 10)
            self.set_text_color(*COLORS['text_main'])
            
            text = sanitize_text(analysis_data)
            if len(text) > 800: text = text[:797] + "..."
            self.multi_cell(170, 6, text)
            self.set_y(self.get_y() + 10)
            return

        # 2. Handle New List Format (Topic-Wise)
        # Expected: [{"topic": "Title", "analysis": "Content..."}, ...]
        if isinstance(analysis_data, list):
            self.check_space(60)
            self.ln(5)
            self.draw_section_header("DETAILED ANALYSIS", COLORS['secondary'])
            
            for item in analysis_data:
                topic = sanitize_text(item.get('topic', 'Topic'))
                content = sanitize_text(item.get('analysis', ''))
                
                # Estimate height
                self.set_font('Arial', '', 10)
                # approx 95 chars per line at 190mm width? 
                # safely assuming 85 chars per line for wrapped text
                num_lines = math.ceil(len(content) / 85) 
                height = (num_lines * 5) + 15 # +15 for padding/header
                
                self.check_space(height)
                
                # Draw Topic Header
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*COLORS['primary'])
                self.cell(0, 6, topic.upper(), 0, 1)
                
                # Draw Content
                self.set_font('Arial', '', 10)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(190, 5, content)
                self.ln(4) # Spacing between topics

    def draw_dynamic_questions(self, questions):
        """Draw the dynamic follow-up questions section."""
        if not questions: return
        
        self.check_space(60)
        self.ln(5)
        
        self.draw_section_header("DEEP DIVE QUESTIONS", COLORS['accent'])
        
        # Grid Background - Purple/Indigo theme
        self.set_fill_color(248, 250, 252) # Very light slate
        start_y = self.get_y()
        # Estimate height based on questions
        height = 15 + (len(questions) * 12)
        self.rect(10, start_y, 190, height, 'F')
        
        current_y = start_y + 5
        
        for i, q in enumerate(questions):
            self.set_xy(15, current_y)
            self.set_font('Arial', 'B', 12)
            self.set_text_color(*COLORS['accent'])
            self.cell(10, 8, "?", 0, 0, 'C')
            
            self.set_font('Arial', 'I', 10) # Italic for questions
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(160, 6, sanitize_text(q))
            
            # Update Y for next question, assuming single line or double line
            # Simple heuristic: add fixed spacing
            current_y = self.get_y() + 4
            
        self.set_y(start_y + height + 5)

    def draw_behaviour_analysis(self, analysis_data):
        """Draw the detailed Behaviour Analysis section."""
        if not analysis_data: return

        self.check_space(80)
        self.ln(5)
        self.draw_section_header("BEHAVIOURAL ANALYSIS", COLORS['primary'])

        for item in analysis_data:
            behavior = sanitize_text(item.get('behavior', 'Behavior'))
            quote = sanitize_text(item.get('quote', ''))
            insight = sanitize_text(item.get('insight', ''))
            impact = sanitize_text(item.get('impact', 'Neutral'))
            improved = sanitize_text(item.get('improved_approach', ''))

            # Determine color based on impact
            impact_color = COLORS['secondary']
            if 'positive' in impact.lower(): impact_color = COLORS['success']
            elif 'negative' in impact.lower(): impact_color = COLORS['danger']
            
            # Estimate height conservatively
            height = 15 # Base height
            if quote: height += int(len(quote) / 75 + 1) * 5 + 5
            if insight: height += int(len(insight) / 75 + 1) * 5 + 5
            if improved: height += int(len(improved) / 75 + 1) * 5 + 12
            
            self.check_space(height + 10)
            
            start_y = self.get_y()
            
            # Left Bar (Impact Color)
            self.set_fill_color(*impact_color)
            self.rect(10, start_y, 2, height, 'F')
            
            # Background
            self.set_fill_color(248, 250, 252)
            self.rect(12, start_y, 188, height, 'F')
            
            current_y = start_y + 3
            
            # Header: Behavior + Impact
            self.set_xy(15, current_y)
            self.set_font('Arial', 'B', 10)
            self.set_text_color(*COLORS['text_main'])
            self.cell(100, 6, behavior.upper(), 0, 0)
            
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*impact_color)
            self.cell(80, 6, impact.upper(), 0, 1, 'R')
            
            current_y += 8
            
            # Quote (Proof)
            if quote:
                self.set_xy(15, current_y)
                self.set_font('Arial', 'BI', 9) # Bold Italic
                self.set_text_color(80, 80, 80)
                self.multi_cell(180, 5, f'"{quote}"')
                current_y = self.get_y() + 2
                
            # Insight (Analysis)
            if insight:
                self.set_xy(15, current_y)
                self.set_font('Arial', '', 9)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(180, 5, insight, align='J')
                current_y = self.get_y() + 4
                
            # Improved Approach (Actionable Advice)
            if improved:
                self.set_xy(15, current_y)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*COLORS['accent'])
                self.cell(40, 5, "TRY THIS INSTEAD:", 0, 1) # Force new line
                
                # Draw a highlight box for the correction
                correction_y = self.get_y()
                self.set_fill_color(240, 249, 255) # Light blue bg
                # Calculate height safely
                lines = int(len(improved) / 75) + 1
                box_h = lines * 5 + 5
                self.rect(15, correction_y, 180, box_h, 'F')
                
                self.set_xy(17, correction_y + 2) # Indent slightly inside box
                self.set_font('Arial', 'I', 9)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(175, 5, improved, align='J')
                current_y = self.get_y() + 4

            # Bottom Spacer (safely preventing overlap)
            self.set_y(max(self.get_y(), start_y + height) + 4)

    def draw_detailed_analysis(self, items):
        """Draw the Deep Dive Analysis section."""
        if not items: return
        
        self.check_space(60)
        self.ln(5)
        self.draw_section_header("DEEP DIVE ANALYSIS", COLORS['accent'])
        
        if isinstance(items, list):
            for item in items:
                topic = sanitize_text(item.get('topic', ''))
                analysis = sanitize_text(item.get('analysis', ''))
                
                if not topic and not analysis: continue
                
                # Estimate height
                height = 15
                if analysis: height += len(analysis) // 90 * 5
                
                self.check_space(height + 10)
                
                # Topic Header
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*COLORS['accent'])
                self.cell(0, 6, topic.upper(), 0, 1)
                
                # Left border for analysis content
                start_y = self.get_y()
                self.set_fill_color(*COLORS['accent'])
                self.rect(10, start_y, 1, height - 5, 'F')
                
                # Analysis Text
                self.set_xy(15, start_y)
                self.set_font('Arial', '', 9)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(180, 5, analysis)
                self.ln(4)
        elif isinstance(items, str):
            # If it's a raw string instead of an array
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(0, 5, sanitize_text(items))
            self.ln(4)

    def draw_question_analysis(self, analysis):
        """Draw the Questions You Should Have Asked section."""
        if not analysis: return
        questions = analysis.get('questions_missed', [])
        if not questions: return
        
        self.check_space(70)
        self.ln(5)
        self.draw_section_header("QUESTIONS YOU SHOULD HAVE ASKED", COLORS['primary'])
        
        # Draw Quality Score Summary if present
        score = analysis.get('question_quality_score')
        feedback = analysis.get('question_quality_feedback')
        tip = analysis.get('questioning_improvement_tip')
        
        if score or feedback or tip:
            self.set_fill_color(248, 250, 252) # Light slate
            self.rect(10, self.get_y(), 190, 35, 'F')
            
            summary_y = self.get_y() + 4
            self.set_xy(15, summary_y)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['text_light'])
            self.cell(100, 5, "QUESTION QUALITY SCORE", 0, 0)
            
            if score:
                self.set_font('Arial', 'B', 14)
                self.set_text_color(*COLORS['primary'])
                self.cell(75, 5, str(score), 0, 1, 'R')
            else:
                self.ln(5)
                
            if feedback:
                self.set_xy(15, self.get_y() + 2)
                self.set_font('Arial', '', 9)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(180, 5, sanitize_text(feedback))
                
            if tip:
                self.set_xy(15, self.get_y() + 2)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*COLORS['accent'])
                self.multi_cell(180, 5, f"TIP: {sanitize_text(tip)}")
                
            self.ln(6)
            
        # Group Questions by Timing
        timings = ['Early', 'Mid', 'Late', 'Uncategorized']
        grouped_questions = {t: [] for t in timings}
        
        for q in questions:
            timing = q.get('timing', 'Uncategorized')
            if timing not in grouped_questions: 
                timing = 'Uncategorized'
            grouped_questions[timing].append(q)
            
        for timing in timings:
            timing_qs = grouped_questions[timing]
            if not timing_qs: continue
            
            if timing != 'Uncategorized':
                self.check_space(20)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*COLORS['text_light'])
                self.cell(0, 8, f"{timing.upper()} CONVERSATION", 0, 1)
                
            for q in timing_qs:
                question_text = sanitize_text(q.get('question', ''))
                category = sanitize_text(q.get('category', ''))
                why = sanitize_text(q.get('why_important', ''))
                when = sanitize_text(q.get('when_to_ask', ''))
                impact = sanitize_text(q.get('impact_if_asked', ''))
                
                # Base height calculation
                h = 10
                if why: h += len(why) // 90 * 5 + 5
                if when: h += len(when) // 90 * 5 + 5
                if impact: h += len(impact) // 90 * 5 + 5
                
                self.check_space(h + 15)
                start_q_y = self.get_y()
                
                # Border Box
                self.set_draw_color(226, 232, 240)
                self.rect(10, start_q_y, 190, h, 'D')
                
                # Question Line
                self.set_xy(15, start_q_y + 4)
                self.set_font('Arial', 'BI', 10)
                self.set_text_color(*COLORS['text_main'])
                self.multi_cell(140, 5, f'"{question_text}"')
                
                # Category Badge (Right Aligned roughly)
                if category:
                    badge_y = start_q_y + 4
                    self.set_xy(160, badge_y)
                    self.set_font('Arial', 'B', 8)
                    self.set_text_color(*COLORS['accent'])
                    self.cell(35, 5, f"[{category.upper()}]", 0, 0, 'R')
                    
                cur_y = self.get_y() + 2
                
                # Details
                self.set_font('Arial', '', 8)
                if why:
                    self.set_xy(15, cur_y)
                    self.set_text_color(*COLORS['primary'])
                    self.set_font('Arial', 'B', 8)
                    self.cell(15, 5, "WHY:", 0, 0)
                    self.set_font('Arial', '', 8)
                    self.set_text_color(*COLORS['text_main'])
                    self.multi_cell(160, 5, why)
                    cur_y = self.get_y()
                    
                if when:
                    self.set_xy(15, cur_y)
                    self.set_text_color(*COLORS['success'])
                    self.set_font('Arial', 'B', 8)
                    self.cell(15, 5, "WHEN:", 0, 0)
                    self.set_font('Arial', '', 8)
                    self.set_text_color(*COLORS['text_main'])
                    self.multi_cell(160, 5, when)
                    cur_y = self.get_y()
                    
                if impact:
                    self.set_xy(15, cur_y)
                    self.set_text_color(*COLORS['warning'])
                    self.set_font('Arial', 'B', 8)
                    self.cell(15, 5, "IMPACT:", 0, 0)
                    self.set_font('Arial', '', 8)
                    self.set_text_color(*COLORS['text_main'])
                    self.multi_cell(160, 5, impact)
                    
                self.set_y(start_q_y + h + 4)

    def draw_eq_analysis(self, eq_data):
        """Draw the Emotional Intelligence & Nuance section."""
        if not eq_data: return

        self.check_space(60)
        self.ln(5)
        self.draw_section_header("EMOTIONAL INTELLIGENCE (EQ) & NUANCE", COLORS['section_eq'])

        for item in eq_data:
            # Handle both dict and string items
            if isinstance(item, dict):
                nuance = sanitize_text(item.get('nuance', 'User Observation'))
                observation = sanitize_text(item.get('observation', ''))
                suggestion = sanitize_text(item.get('suggestion', '')) # Retain suggestion from dict
            elif isinstance(item, str):
                nuance = 'User Observation'
                observation = sanitize_text(item)
                suggestion = '' # No suggestion for string items
            else:
                continue  # Skip invalid items
                
            # If observation is empty, and it's a dict, check for suggestion.
            # The original code had 'proof' and 'suggestion'.
            # Assuming 'observation' replaces 'proof'.
            # The line `if not observation: continue_text(item.get('suggestion', ''))` from the user's prompt
            # seems to be a typo (`continue_text` is not defined) and potentially incorrect logic
            # if `item` is a string.
            # I will interpret this as: if there's no observation, we might still have a suggestion.
            # However, the original code always processed proof and suggestion if they existed.
            # I will proceed by using 'observation' where 'proof' was used, and 'suggestion' as before.
            # The user's provided `if not observation: continue_text(...)` line is problematic and will be omitted
            # as it's syntactically incorrect and its intent is unclear given the context.
            
            # Estimate height conservatively
            height = 15
            if observation: height += int(len(observation) / 75 + 1) * 5 + 5 
            if suggestion: height += int(len(suggestion) / 75 + 1) * 5 + 10
            
            self.check_space(height + 10)
            start_y = self.get_y()
            
            # Background
            self.set_fill_color(253, 242, 248) # Pink 50 (to match section_eq)
            self.rect(10, start_y, 190, height, 'F')
            
            # Left Bar
            self.set_fill_color(*COLORS['section_eq'])
            self.rect(10, start_y, 2, height, 'F')
            
            current_y = start_y + 3
            
            # Draw nuance badge
            self.set_xy(15, current_y)
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*COLORS['nuance_bg'])
            self.cell(0, 6, nuance.upper(), ln=True)
            
            # Draw observation (previously 'proof')
            if observation:
                self.set_font('Helvetica', '', 9)
                self.set_text_color(40, 40, 40)
                self.multi_cell(0, 5, f"Observation: {observation}")
                self.ln(2)
            
            # Draw suggestion
            if suggestion:
                self.set_text_color(100, 116, 139)
                self.cell(0, 5, "SUGGESTION:", 0, 1) # Auto move to next line
                
                self.set_font('Arial', '', 9)
                self.set_text_color(*COLORS['text_main'])
                self.set_x(15)
                self.multi_cell(180, 5, suggestion)
                current_y = self.get_y() + 4
            
            self.set_y(max(self.get_y(), start_y + height) + 4)

    def draw_section_header(self, title, color):
        self.ln(3)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*color)
        self.cell(0, 8, title, 0, 1)
        # Add colored underline
        self.set_draw_color(*color)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 50, self.get_y())
        self.set_line_width(0.2)
        self.ln(4)

    def draw_banner(self, meta, scenario_type="custom"):
        """Draw the summary banner at the top of the report."""
        summary = meta.get('summary', '')
        emotional_trajectory = meta.get('emotional_trajectory', '')
        session_quality = meta.get('session_quality', '')
        key_themes = meta.get('key_themes', [])
        overall_grade = meta.get('overall_grade', 'N/A')
        
        self.set_y(self.get_y() + 3)
        start_y = self.get_y()
        
        # Calculate banner height based on content
        base_height = 50
        if emotional_trajectory: base_height += 8
        if session_quality: base_height += 8
        if key_themes: base_height += 10
        banner_height = base_height
        
        # Main Card with shadow effect
        self.set_fill_color(245, 247, 250)  # Subtle shadow
        self.rect(12, start_y + 2, 190, banner_height, 'F')
        
        # Main Card Background
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(226, 232, 240)
        self.rect(10, start_y, 190, banner_height, 'DF')
        
        # Scenario-type specific colors and labels
        scenario_colors = {
            "coaching": (59, 130, 246),    # Blue
            "negotiation": (16, 185, 129), # Green  
            "reflection": (139, 92, 246),  # Purple
            "custom": (245, 158, 11),      # Orange/Amber
            "leadership": (99, 102, 241),  # Indigo (Authority)
            "customer_service": (239, 68, 68) # Red (Urgency/Resolution)
        }
        
        # New Labels matching frontend
        scenario_labels = {
            "coaching": "COACHING EFFICACY",
            "negotiation": "NEGOTIATION POWER",
            "reflection": "LEARNING INSIGHTS",
            "custom": "GOAL ATTAINMENT",
            "leadership": "LEADERSHIP & STRATEGY",
            "customer_service": "CUSTOMER SERVICE"
        }
        
        accent_color = scenario_colors.get(scenario_type, scenario_colors["custom"])
        verd_label = scenario_labels.get(scenario_type, scenario_labels["custom"])
        
        # Accent bar on left - scenario-specific color
        self.set_fill_color(*accent_color)
        self.rect(10, start_y, 4, banner_height, 'F')
        
        # Scenario-type label with icon
        self.set_xy(18, start_y + 6)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(71, 85, 105)  # Slate 600
        icon_map = {
            "coaching": "[C]", "negotiation": "[N]", "reflection": "[R]", "custom": "[*]",
            "leadership": "[L]", "customer_service": "[S]"
        }
        icon = icon_map.get(scenario_type, "[*]")
        self.cell(100, 5, f"{icon} {verd_label}", 0, 1)
        
        # Grade Display (Top Right)
        if scenario_type != 'reflection':
             self.set_xy(150, start_y + 6)
             self.set_font('Arial', 'B', 24)
             self.set_text_color(*COLORS['accent']) # Uses main accent
             # Determine color based on grade if possible, else default accent
             self.cell(40, 10, str(overall_grade), 0, 0, 'R')
        
        # Summary text
        self.set_xy(18, start_y + 15)
        self.set_font('Arial', '', 10)
        self.set_text_color(51, 65, 85)
        self.multi_cell(130, 5, sanitize_text(summary))
        
        # Metrics row with visual indicators
        current_y = start_y + 35
        
        if emotional_trajectory:
            self.set_xy(18, current_y)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(99, 102, 241)  # Indigo
            self.cell(3, 4, ">", 0, 0)
            self.set_text_color(100, 116, 139)
            self.cell(38, 4, "EMOTIONAL ARC:", 0, 0)
            self.set_font('Arial', '', 9)
            self.set_text_color(51, 65, 85)
            self.cell(0, 4, sanitize_text(emotional_trajectory), 0, 1)
            current_y += 7
        
        if session_quality:
            self.set_xy(18, current_y)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(16, 185, 129)  # Emerald
            self.cell(3, 4, ">", 0, 0)
            self.set_text_color(100, 116, 139)
            self.cell(38, 4, "SESSION QUALITY:", 0, 0)
            self.set_font('Arial', '', 9)
            self.set_text_color(51, 65, 85)
            self.cell(0, 4, sanitize_text(session_quality), 0, 1)
            current_y += 7
        
        # Key themes with pill-style display
        if key_themes:
            self.set_xy(18, current_y)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(236, 72, 153)  # Pink
            self.cell(3, 4, ">", 0, 0)
            self.set_text_color(100, 116, 139)
            self.cell(38, 4, "KEY THEMES:", 0, 0)
            self.set_font('Arial', 'I', 9)
            self.set_text_color(71, 85, 105)
            themes_text = " | ".join([sanitize_text(str(theme)) for theme in key_themes[:3]])
            self.cell(0, 4, themes_text, 0, 1)
        
        self.set_y(start_y + banner_height + 8)
    
    def draw_executive_summary(self, exec_summary):
        """Draw the Executive Summary section - NEW unified section for all reports."""
        if not exec_summary:
            return
        
        self.check_space(80)
        self.ln(5)
        
        # Section header with gradient-like background
        self.set_fill_color(30, 41, 59)  # Slate 800
        self.rect(10, self.get_y(), 190, 12, 'F')
        self.set_xy(15, self.get_y() + 3)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, self.get_title("exec_summary"), 0, 1)
        self.ln(3)
        
        # Performance Overview
        overview = exec_summary.get('performance_overview', '')
        if overview:
            self.set_font('Arial', '', 10)
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(0, 6, sanitize_text(overview))
            self.ln(6)
        
        # Two-column layout for strengths and growth areas
        start_y = self.get_y()
        
        # Key Strengths (left column)
        strengths = exec_summary.get('key_strengths', [])
        if strengths:
            self.set_fill_color(240, 253, 244)  # Green 50
            self.rect(10, start_y, 90, 45, 'F')
            self.set_xy(15, start_y + 5)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['success'])
            self.cell(80, 5, "KEY STRENGTHS", 0, 1)
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_main'])
            for i, strength in enumerate(strengths[:3]):
                self.set_x(15)
                self.multi_cell(80, 5, f"+ {sanitize_text(strength)}")
        
        # Areas for Growth (right column)
        growth = exec_summary.get('areas_for_growth', [])
        if growth:
            self.set_fill_color(254, 249, 195)  # Yellow 100
            self.rect(105, start_y, 95, 45, 'F')
            self.set_xy(110, start_y + 5)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['warning'])
            self.cell(85, 5, "AREAS FOR GROWTH", 0, 1)
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_main'])
            for i, area in enumerate(growth[:3]):
                self.set_x(110)
                self.multi_cell(85, 5, f"- {sanitize_text(area)}")
        
        self.set_y(start_y + 50)
        
        # Recommended Next Steps
        next_steps = exec_summary.get('recommended_next_steps', '')
        if next_steps:
            self.set_fill_color(248, 250, 252)  # Slate 50
            self.rect(10, self.get_y(), 190, 20, 'F')
            self.set_xy(15, self.get_y() + 5)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['accent'])
            self.cell(40, 5, "NEXT STEPS:", 0, 0)
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(145, 5, sanitize_text(next_steps))
            self.ln(5)
        
        self.ln(5)
    
    def draw_personalized_recommendations(self, recs):
        """Draw the unified personalized recommendations section."""
        if not recs:
            return
        
        self.check_space(70)
        self.ln(5)
        
        # Dark header block
        self.set_fill_color(30, 41, 59)  # Slate 800
        self.rect(10, self.get_y(), 190, 60, 'F')
        
        start_y = self.get_y()
        self.set_xy(15, start_y + 5)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, self.get_title("recs"), 0, 1)
        
        # Immediate Actions
        actions = recs.get('immediate_actions', [])
        if actions:
            self.set_font('Arial', 'B', 9)
            self.set_text_color(147, 197, 253)  # Blue 300
            self.cell(50, 6, "IMMEDIATE ACTIONS:", 0, 0)
            self.set_font('Arial', '', 9)
            self.set_text_color(255, 255, 255)
            actions_text = ", ".join([sanitize_text(a) for a in actions[:3]])
            self.multi_cell(135, 6, actions_text)
        
        # Focus Areas
        focus = recs.get('focus_areas', [])
        if focus:
            self.set_font('Arial', 'B', 9)
            self.set_text_color(147, 197, 253)
            self.cell(50, 6, "FOCUS AREAS:", 0, 0)
            self.set_font('Arial', '', 9)
            self.set_text_color(255, 255, 255)
            focus_text = ", ".join([sanitize_text(f) for f in focus[:3]])
            self.multi_cell(135, 6, focus_text)
        
        # Reflection Prompts
        prompts = recs.get('reflection_prompts', [])
        if prompts:
            self.ln(2)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(203, 213, 225)  # Slate 300
            for prompt in prompts[:2]:
                self.set_x(15)
                self.cell(0, 4, f"? {sanitize_text(prompt)}", 0, 1)
        
        self.set_y(start_y + 65)

    # --- ASSESSMENT MODE DRAWING METHODS ---

    def draw_assessment_table(self, scores, show_scores=True):
        if not scores: return
        self.check_space(80)
        self.ln(5)
        
        self.draw_section_header(self.get_title("skills"), COLORS['primary'])

        # Widths
        w_dim = 45 if show_scores else 50
        w_score = 15
        w_interp = 65 if show_scores else 70
        w_tip = 65 if show_scores else 70
        
        # Header
        self.set_fill_color(241, 245, 249)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*COLORS['text_main'])
        self.cell(w_dim, 8, "DIMENSION", 1, 0, 'L', True)
        if show_scores:
            self.cell(w_score, 8, "SCORE", 1, 0, 'C', True)
        self.cell(w_interp, 8, "INTERPRETATION", 1, 0, 'L', True)
        self.cell(w_tip, 8, "IMPROVEMENT TIP", 1, 1, 'L', True)

        for item in scores:
            dim = sanitize_text(item.get('dimension', ''))
            score = item.get('score', 0)
            interp = sanitize_text(item.get('interpretation', ''))
            tip = sanitize_text(item.get('improvement_tip', ''))

            # Calculate row height based on content
            row_height = max(15, len(interp) // 40 * 5 + 10, len(tip) // 40 * 5 + 10)

            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['text_main'])
            self.cell(w_dim, row_height, dim, 1, 0, 'L')
            
            if show_scores:
                # Score Color
                if score >= 8: self.set_text_color(*COLORS['success'])
                elif score >= 6: self.set_text_color(*COLORS['warning'])
                else: self.set_text_color(*COLORS['danger'])
                
                self.cell(w_score, row_height, f"{score}/10", 1, 0, 'C')
            
            # Interpretation
            self.set_text_color(*COLORS['text_main'])
            self.set_font('Arial', '', 8)
            current_x = self.get_x()
            current_y = self.get_y()
            self.multi_cell(w_interp, 7.5, interp, border=1, align='L')
            
            # Improvement tip
            self.set_xy(current_x + w_interp, current_y)
            self.set_text_color(*COLORS['accent'])
            self.multi_cell(w_tip, 7.5, tip, border=1, align='L')
            
            # Move to next row
            self.set_xy(10, current_y + row_height)

        self.ln(5)

    def draw_conversation_analytics(self, analytics):
        if not analytics: return
        self.check_space(40)
        
        self.draw_section_header(self.get_title("analytics"), COLORS['secondary'])
        
        # Create a 2x3 grid of metrics
        metrics = [
            ("Total Exchanges", analytics.get('total_exchanges', 'N/A')),
            ("Talk Time Balance", f"{analytics.get('user_talk_time_percentage', 0)}% User"),
            ("Question/Statement Ratio", analytics.get('question_to_statement_ratio', 'N/A')),
            ("Emotional Progression", analytics.get('emotional_tone_progression', 'N/A')),
            ("Framework Adherence", analytics.get('framework_adherence', 'N/A')),
        ]
        
        self.set_fill_color(248, 250, 252)
        self.rect(10, self.get_y(), 190, 35, 'F')
        
        start_y = self.get_y()
        for i, (label, value) in enumerate(metrics):
            x_pos = 15 + (i % 3) * 60
            y_pos = start_y + 5 + (i // 3) * 15
            
            self.set_xy(x_pos, y_pos)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*COLORS['text_light'])
            self.cell(55, 5, label, 0, 1)
            
            self.set_xy(x_pos, y_pos + 5)
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_main'])
            self.cell(55, 5, str(value), 0, 0)
        
        self.set_y(start_y + 40)

    def draw_learning_path(self, path):
        if not path: return
        self.check_space(60)
        
        self.draw_section_header("PERSONALIZED LEARNING PATH", COLORS['accent'])
        
        for item in path:
            skill = sanitize_text(item.get('skill', ''))
            priority = item.get('priority', 'Medium')
            timeline = sanitize_text(item.get('timeline', ''))
            
            # Priority color coding
            if priority == 'High': color = COLORS['danger']
            elif priority == 'Medium': color = COLORS['warning']
            else: color = COLORS['success']
            
            self.set_font('Arial', 'B', 10)
            self.set_text_color(*color)
            self.cell(100, 6, f"• {skill}", 0, 0)
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_light'])
            self.cell(0, 6, f"Priority: {priority} | {timeline}", 0, 1)
            self.ln(2)
        
        self.ln(5)

    def _extract_score_value(self, score_str):
        try:
            # Remove /10 or similar
            clean = str(score_str).split('/')[0].strip()
            return float(clean)
        except:
            return 0.0

    # --- SCENARIO SPECIFIC DRAWING METHODS ---

    def draw_scorecard(self, scorecard):
        """Draw a standard scorecard table with zebra striping."""
        if not scorecard: return
        self.check_space(60)
        self.ln(8) # Extra spacing
        
        # Draw Radar Chart First
        self.draw_section_header("SKILL VISUALIZATION", COLORS['secondary'])
        self.draw_radar_chart(scorecard)
        
        self.draw_section_header("PERFORMANCE SCORECARD", COLORS['primary'])
        
        # Table Header
        self.set_fill_color(30, 41, 59) # Dark header
        self.set_font('Arial', 'B', 9)
        self.set_text_color(255, 255, 255) # White text
        self.cell(50, 9, "DIMENSION", 0, 0, 'L', True)
        self.cell(20, 9, "SCORE", 0, 0, 'C', True)
        self.cell(120, 9, "OBSERVATION", 0, 1, 'L', True)
        
        # Rows
        for i, item in enumerate(scorecard):
            dim = sanitize_text(item.get('dimension', ''))
            score = str(item.get('score', 'N/A'))
            desc = sanitize_text(item.get('description', ''))
            
            if not desc:
                r = sanitize_text(item.get('reasoning', ''))
                q = sanitize_text(item.get('quote', ''))
                s = sanitize_text(item.get('suggestion', ''))
                parts = []
                if r: parts.append(r)
                if q: parts.append(f"Quote: \"{q}\"")
                if s: parts.append(f"Tip: {s}")
                desc = "\n".join(parts)
            
            # Calculate height accurately by counting physical chars per line and explicit newlines
            lines_estimate = sum(max(1, len(line)/70) for line in desc.split('\n'))
            
            alt_qs = item.get('alternative_questions', [])
            if alt_qs:
                lines_estimate += 1.5 # "TRY ASKING INSTEAD:" + padding
                for aq in alt_qs:
                    q_text = aq.get('question', '')
                    if q_text:
                        lines_estimate += max(1, len(q_text) / 70)
            
            row_height = max(14, int(lines_estimate * 5 + 6))
            
            self.check_space(row_height + 5)
            
            x_start = self.get_x()
            y_start = self.get_y()
            
            # Zebra striping explicitly via Rect to wrap entire content block
            if i % 2 == 0:
                self.set_fill_color(248, 250, 252) # Very light gray
            else:
                self.set_fill_color(255, 255, 255) # White
                
            self.rect(x_start, y_start, 190, row_height, 'F')
            
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['text_main'])
            
            self.set_xy(x_start, y_start)
            self.cell(50, row_height, dim, 0, 0, 'L')
            
            # Score Color
            try:
                s_val = float(score.split('/')[0])
                if s_val >= 8: self.set_text_color(*COLORS['success'])
                elif s_val <= 5: self.set_text_color(*COLORS['danger'])
                else: self.set_text_color(*COLORS['warning'])
            except:
                self.set_text_color(*COLORS['text_main'])
                
            self.cell(20, row_height, score, 0, 0, 'C')
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_light'])
            
            # Multi-cell handling (no background fill, proper 5mm line height)
            self.set_xy(x_start + 70, y_start + 2)
            self.multi_cell(120, 5, desc, border=0, align='L', fill=False)
            
            # Alternative Questions / Try Asking Instead
            if alt_qs:
                self.set_font('Arial', 'B', 8)
                self.set_text_color(*COLORS['accent'])
                self.set_x(x_start + 70)
                self.cell(40, 5, "TRY ASKING INSTEAD:", 0, 1)
                
                self.set_font('Arial', 'I', 8)
                self.set_text_color(*COLORS['text_main'])
                for aq in alt_qs:
                    q_text = aq.get('question', '')
                    if q_text:
                        self.set_x(x_start + 70)
                        self.multi_cell(120, 5, f"- \"{sanitize_text(q_text)}\"", 0, 'L')
            
            # Reset position for next row exactly at row_height boundary
            self.set_xy(x_start, y_start + row_height)
            self.set_draw_color(226, 232, 240)
            self.line(x_start, y_start + row_height, x_start + 190, y_start + row_height) # Bottom border
            self.set_text_color(*COLORS['text_main']) # Reset color

    def draw_radar_chart(self, scorecard):
        """Draw a radar chart for the scorecard dimensions."""
        if not scorecard: return

        # Extract data
        labels = []
        scores = []
        for item in scorecard:
            dim = sanitize_text(item.get('dimension', ''))
            # Extract numeric score "8/10" -> 8.0
            s_str = str(item.get('score', '0'))
            try:
                val = float(s_str.split('/')[0])
            except:
                val = 0.0
            
            labels.append(dim)
            scores.append(val)

        if not labels: return

        # Number of variables
        N = len(labels)
        
        # Compute angle for each axis
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1] # Close the loop
        
        scores += scores[:1] # Close the loop
        
        # Plot
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # Draw one axe per variable + add labels
        plt.xticks(angles[:-1], labels, color='grey', size=8)
        
        # Draw ylabels
        ax.set_rlabel_position(0)
        plt.yticks([2,4,6,8,10], ["2","4","6","8","10"], color="grey", size=7)
        plt.ylim(0, 10)
        
        # Plot data
        ax.plot(angles, scores, linewidth=2, linestyle='solid', color='#3b82f6') # Blue 500
        ax.fill(angles, scores, '#3b82f6', alpha=0.2)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, bbox_inches='tight', transparent=True)
            tmp_path = tmp.name
        
        plt.close(fig)
        
        # Embed in PDF
        # Center the chart
        self.check_space(90)
        self.image(tmp_path, x=60, y=self.get_y(), w=90)
        self.ln(90)
        
        # Cleanup
        try:
            os.remove(tmp_path)
        except:
            pass


    def draw_key_value_grid(self, title, data_dict, color=COLORS['secondary']):
        """Draw a grid of key-value pairs with better spacing."""
        if not data_dict: return
        self.check_space(50)
        self.ln(8)
        self.draw_section_header(title, color)
        
        self.set_fill_color(248, 250, 252) 
        self.rect(self.get_x(), self.get_y(), 190, len(data_dict)*8 + 5, 'F')
        self.ln(2)

        for key, value in data_dict.items():
            key_label = key.replace('_', ' ').title()
            val_text = sanitize_text(str(value))
            
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*COLORS['text_main'])
            self.cell(60, 8, "  " + key_label + ":", 0, 0) # Indent
            
            self.set_font('Arial', '', 9)
            self.set_text_color(*COLORS['text_light'])
            self.multi_cell(0, 8, val_text)
        self.ln(2)

    def draw_list_section(self, title, items, color=COLORS['section_comm'], bullet="•"):
        """Draw a bulleted list section with icons."""
        if not items: return
        self.check_space(len(items) * 10 + 20)
        self.ln(8)
        self.draw_section_header(title, color)
        
        self.set_font('Arial', '', 9)
        self.set_text_color(*COLORS['text_main'])
        for item in items:
            self.set_text_color(*color)
            self.cell(8, 7, bullet, 0, 0, 'R')
            self.set_text_color(*COLORS['text_main'])
            self.multi_cell(0, 7, sanitize_text(str(item)))

    def draw_two_column_lists(self, title_left, items_left, color_left, title_right, items_right, color_right):
        """Draw two lists side-by-side with dynamic height calculation."""
        if not items_left and not items_right: return
        
        start_y = self.get_y() + 5
        mid_x = 105
        col_width = 90
        
        # Helper to calculate list height
        def calculate_list_height(items, width_mm, font_size=9):
            total_h = 0
            chars_per_line = (width_mm * 2.3) # approx const for Arial 9
            for item in items:
                txt = sanitize_text(str(item))
                # rough estimate
                lines = math.ceil(len(txt) / 50) # conservative 50 chars per line for 90mm
                total_h += (lines * 6) + 2 # 6mm line height, 2mm padding
            return total_h

        # Calculate heights
        h_left = calculate_list_height(items_left, col_width) + 10 # +10 header
        h_right = calculate_list_height(items_right, col_width) + 10
        max_h = max(h_left, h_right)
        
        self.check_space(max_h + 20)
        self.ln(5)
        
        # Recalculate start_y in case of page break
        start_y = self.get_y()
        
        # Draw Headers
        self.set_xy(10, start_y)
        self.draw_section_header(title_left, color_left)
        self.set_xy(mid_x + 5, start_y)
        self.draw_section_header(title_right, color_right)
        
        content_start_y = self.get_y()
        
        # Draw Backgrounds with dynamic height
        # Left Card
        self.set_fill_color(250, 250, 255) 
        self.rect(10, content_start_y, col_width, max_h, 'F')
        # Right Card
        self.rect(mid_x + 5, content_start_y, col_width, max_h, 'F')
        
        # Draw LEFT Items
        self.set_xy(10, content_start_y + 2)
        self.set_font('Arial', '', 9)
        current_y_left = content_start_y + 2
        
        for item in items_left:
            self.set_xy(15, current_y_left) # Indent
            self.set_text_color(*color_left)
            self.cell(5, 6, "+", 0, 0)
            self.set_text_color(*COLORS['text_main'])
            
            # Save X,Y
            x = self.get_x()
            y = self.get_y()
            
            self.multi_cell(col_width - 10, 6, sanitize_text(str(item)))
            current_y_left = self.get_y() + 1 # small gap
            
        # Draw RIGHT Items
        current_y_right = content_start_y + 2
        for item in items_right:
            self.set_xy(mid_x + 10, current_y_right) # Indent
            self.set_text_color(*color_right)
            self.cell(5, 6, "!", 0, 0)
            self.set_text_color(*COLORS['text_main'])
            
            self.multi_cell(col_width - 10, 6, sanitize_text(str(item)))
            current_y_right = self.get_y() + 1 

        # Move cursor to bottom of tallest column
        self.set_y(content_start_y + max_h + 5)

    def draw_transcript(self, transcript):
        """Draw the detailed chat transcript at the end."""
        if not transcript: return
        self.add_page()
        
        self.draw_section_header("SESSION TRANSCRIPT", COLORS['primary'])
        self.ln(5)
        
        for msg in transcript:
            role = msg.get('role', 'user')
            content = sanitize_text(msg.get('content', ''))
            
            self.set_font('Arial', 'B', 8)
            
            if role == 'user':
                # User (Right side)
                self.set_text_color(*COLORS['accent'])
                self.cell(0, 5, "YOU", 0, 1, 'R')
                
                self.set_font('Arial', '', 9)
                self.set_text_color(255, 255, 255)
                self.set_fill_color(*COLORS['accent']) # Blue bubble
                
                # Calculate height
                # FPDF multi_cell doesn't return height easily, so estimating
                # We'll use a fixed width for the bubble
                bubble_w = 140
                x_pos = 200 - bubble_w - 10 # Right align
                
                self.set_x(x_pos)
                self.multi_cell(bubble_w, 6, content, 0, 'J', True)
                
            else:
                # Assistant (Left side)
                self.set_text_color(*COLORS['text_light'])
                self.cell(0, 5, "COACH", 0, 1, 'L')
                
                self.set_font('Arial', '', 9)
                self.set_text_color(*COLORS['text_main'])
                self.set_fill_color(241, 245, 249) # Gray bubble
                
                bubble_w = 140
                self.set_x(10)
                self.multi_cell(bubble_w, 6, content, 0, 'J', True)
            
            self.ln(3)

    # --- MAIN SCENARIO DRAWING ---

    def draw_coaching_report(self, data):
        self.draw_scorecard(data.get('scorecard', []))
        
        # Optional Legacy Section
        if 'behavioral_signals' in data and not data.get('behaviour_analysis'):
           self.draw_key_value_grid("BEHAVIORAL SIGNALS", data.get('behavioral_signals', {}))
        
        if 'coaching_impact' in data:
            self.draw_key_value_grid("COACHING IMPACT", data.get('coaching_impact', {}), COLORS['purple'])
            
        # Use 2-Column Layout for Strengths/Weaknesses
        self.draw_two_column_lists(
            "KEY STRENGTHS", data.get('strengths', []), COLORS['success'],
            "MISSED OPPORTUNITIES", data.get('missed_opportunities', []), COLORS['warning']
        )
            
        self.draw_list_section("ACTIONABLE TIPS", data.get('actionable_tips', []), COLORS['accent'], "->")

    def draw_coaching_sim_report(self, data):
        # Format "scores" from dict into a list expected by draw_assessment_table or draw_scorecard
        scores_dict = data.get('scores', {})
        scorecard_list = []
        for raw_key, value in scores_dict.items():
            dim = raw_key.replace('_', ' ').title()
            is_obj = isinstance(value, dict)
            num_val = float(value.get('score', 0)) if is_obj else float(value)
            reason = value.get('reasoning', '') if is_obj else ''
            # Output out of 5 but PDF system often expects string /10 or similar
            scorecard_list.append({
                'dimension': dim,
                'score': f"{num_val}/5",
                'description': reason
            })
            
        self.draw_scorecard(scorecard_list)
        
        self.draw_two_column_lists(
            "KEY STRENGTHS", data.get('strengths', []), COLORS['success'],
            "AREAS FOR IMPROVEMENT", data.get('improvements', []), COLORS['warning']
        )
        
        self.draw_list_section("SUGGESTED BETTER MOVES", data.get('suggested_moves', []), COLORS['accent'], "->")
        
        stages = data.get('conversation_stages', [])
        if stages:
            self.draw_list_section("CONVERSATION STAGES COVERED", stages, COLORS['accent'], "✓")

    def draw_assessment_report(self, data):
        self.draw_scorecard(data.get('scorecard', []))
            
        if 'simulation_analysis' in data:
            self.draw_key_value_grid("SIMULATION ANALYSIS", data.get('simulation_analysis', {}))
        
        # Use 2-Column Layout
        self.draw_two_column_lists(
            "WHAT WORKED", data.get('what_worked', []), COLORS['success'],
            "LIMITATIONS", data.get('what_limited_effectiveness', []), COLORS['danger']
        )
        
        if 'revenue_impact' in data:
            self.draw_key_value_grid("REVENUE IMPACT", data.get('revenue_impact', {}), COLORS['danger'])
            
        self.draw_list_section("RECOMMENDATIONS", data.get('sales_recommendations', []), COLORS['accent'])

    def draw_learning_report(self, data):
        self.draw_key_value_grid("CONTEXT", data.get('context_summary', {}))
        self.draw_list_section("KEY INSIGHTS", data.get('key_insights', []), COLORS['purple'])
        self.draw_list_section("REFLECTIVE QUESTIONS", data.get('reflective_questions', []), COLORS['accent'], "?")
        
        # Behavioral Shifts
        shifts = data.get('behavioral_shifts', [])
        if shifts:
            self.draw_section_header("BEHAVIORAL SHIFTS", COLORS['section_skills'])
            for s in shifts:
                self.set_font('Arial', '', 9)
                self.cell(90, 6, sanitize_text(s.get('from','')), 0, 0)
                self.cell(10, 6, "->", 0, 0)
                self.set_font('Arial', 'B', 9)
                self.multi_cell(0, 6, sanitize_text(s.get('to','')))
            self.ln(5)

        self.draw_list_section("PRACTICE PLAN", data.get('practice_plan', []), COLORS['success'])
        
        if data.get('growth_outcome'):
            self.ln(5)
            self.set_font('Arial', 'I', 11)
            self.set_text_color(*COLORS['primary'])
            self.multi_cell(0, 8, f"Growth Vision: {sanitize_text(data['growth_outcome'])}", align='C')

    def draw_custom_report(self, data):
        self.draw_key_value_grid("INTERACTION QUALITY", data.get('interaction_quality', {}))
        
        # Core Skills
        skills = data.get('core_skills', [])
        if skills:
            self.draw_section_header("CORE SKILLS", COLORS['section_skills'])
            for s in skills:
                self.set_font('Arial', 'B', 9)
                self.cell(50, 6, sanitize_text(s.get('skill', '')), 0, 0)
                self.cell(30, 6, sanitize_text(s.get('rating', '')), 0, 0)
                self.set_font('Arial', '', 9)
                self.multi_cell(0, 6, sanitize_text(s.get('feedback', '')))
        
        self.draw_list_section("STRENGTHS", data.get('strengths_observed', []), COLORS['success'])
        self.draw_list_section("DEVELOPMENT AREAS", data.get('development_opportunities', []), COLORS['warning'])
        
        # Guidance
        guidance = data.get('guidance', {})
        if guidance:
            self.draw_list_section("CONTINUE", guidance.get('continue', []), COLORS['success'])
            self.draw_list_section("ADJUST", guidance.get('adjust', []), COLORS['warning'])
            self.draw_list_section("TRY NEXT", guidance.get('try_next', []), COLORS['accent'])

    def draw_coaching_sim_report(self, data):
        """
        Renders the full Coaching Simulation report matching the React SimulationView component
        section by section, in the same layout order.
        """
        SLATE = (30, 41, 59)
        EMERALD = (16, 185, 129)
        BLUE = (59, 130, 246)
        AMBER = (245, 158, 11)
        INDIGO = (99, 102, 241)
        PURPLE = (168, 85, 247)
        ROSE = (244, 63, 94)
        LIGHT_BG = (248, 250, 252)
        TEXT_MAIN = COLORS['text_main']
        TEXT_LIGHT = COLORS['text_light']
        WHITE = (255, 255, 255)

        def block_title(title, color):
            self.check_space(18)
            self.ln(6)
            self.set_fill_color(*color)
            self.rect(10, self.get_y(), 3, 9, 'F')
            self.set_xy(16, self.get_y() + 1)
            self.set_font('Arial', 'B', 11)
            self.set_text_color(*color)
            self.cell(0, 7, title.upper(), 0, 1)
            self.ln(2)

        def small_label(text, color=None):
            self.set_x(12)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*(color or TEXT_LIGHT))
            self.cell(0, 5, text.upper(), 0, 1)

        def body_text(text):
            self.set_x(12)
            self.set_font('Arial', '', 9)
            self.set_text_color(*TEXT_MAIN)
            self.multi_cell(186, 5, sanitize_text(str(text)))

        def divider():
            self.ln(4)
            self.set_draw_color(*COLORS['divider'])
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

        # ─────────────────────────────────────────────────────────────
        # 1. EXECUTIVE DASHBOARD
        # ─────────────────────────────────────────────────────────────
        es = data.get('executive_summary', {})
        if es:
            block_title("Executive Dashboard", BLUE)
            small_label("Overall Snapshot")
            body_text(es.get('snapshot', ''))
            self.ln(2)

            score = es.get('final_score') or data.get('meta', {}).get('overall_grade', 'N/A')
            self.set_fill_color(*LIGHT_BG)
            self.rect(10, self.get_y(), 190, 18, 'F')
            self.set_xy(15, self.get_y() + 3)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*SLATE)
            self.cell(60, 6, "FINAL SCORE", 0, 0)
            sv = self._extract_score_value(str(score))
            self.set_font('Arial', 'B', 14)
            self.set_text_color(*get_bar_color(sv))
            self.cell(0, 6, sanitize_text(str(score)), 0, 1)
            self.set_y(self.get_y() + 6)
            self.ln(2)

            small_label("Outcome Summary")
            body_text(es.get('outcome_summary', ''))
            divider()

        # ─────────────────────────────────────────────────────────────
        # 2. COACHING STYLE PROFILE
        # ─────────────────────────────────────────────────────────────
        cs = data.get('coaching_style', {})
        if cs:
            block_title("Coaching Style Profile", EMERALD)
            self.set_x(15)
            self.set_font('Arial', 'B', 13)
            self.set_text_color(*EMERALD)
            self.cell(0, 8, sanitize_text(str(cs.get('primary_style', ''))).upper(), 0, 1)
            self.set_x(15)
            self.set_font('Arial', 'I', 9)
            self.set_text_color(*TEXT_LIGHT)
            self.multi_cell(180, 5, '"' + sanitize_text(str(cs.get('description', ''))) + '"')
            divider()

        # ─────────────────────────────────────────────────────────────
        # 3. GOAL ATTAINMENT
        # ─────────────────────────────────────────────────────────────
        ga = data.get('goal_attainment', {})
        if ga:
            block_title("Goal Attainment", BLUE)
            score = ga.get('score', 'N/A')
            self.set_x(15)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*TEXT_LIGHT)
            self.cell(70, 6, "ATTAINMENT SCORE", 0, 0)
            sv = self._extract_score_value(str(score))
            self.set_font('Arial', 'B', 14)
            self.set_text_color(*get_bar_color(sv))
            self.cell(0, 6, sanitize_text(str(score)), 0, 1)
            self.ln(2)

            small_label("Expectation vs Reality")
            body_text(ga.get('expectation_vs_reality', ''))
            self.ln(2)

            gaps = ga.get('primary_gaps', [])
            if gaps:
                small_label("Primary Gaps", ROSE)
                for g in gaps:
                    self.set_x(15)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*ROSE)
                    self.cell(5, 5, "x", 0, 0)
                    self.set_text_color(*TEXT_MAIN)
                    self.multi_cell(175, 5, sanitize_text(str(g)))

            focuses = ga.get('observation_focus', [])
            if focuses:
                self.ln(2)
                small_label("Observation Focus")
                for f in focuses:
                    self.set_x(12)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(100, 116, 139)
                    self.multi_cell(186, 5, "- " + sanitize_text(str(f)))
                self.ln(1)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 4. COMPETENCY HEAT MAP
        # ─────────────────────────────────────────────────────────────
        heat_map = data.get('heat_map', [])
        if heat_map:
            block_title("Competency Heat Map", PURPLE)
            for item in heat_map:
                self.check_space(10)
                dim = sanitize_text(str(item.get('dimension', '')))
                score_val = float(item.get('score', 0))

                self.set_x(15)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*TEXT_MAIN)
                self.cell(50, 6, dim, 0, 0)

                # Bar starts right after the 50px label (15+50=65), 110px wide, score at 180
                bar_x = 65
                bar_w = 110
                row_y = self.get_y()
                by = row_y + 1
                self.set_fill_color(226, 232, 240)
                self.rect(bar_x, by, bar_w, 4, 'F')
                fill_w = max(0, min((score_val / 10) * bar_w, bar_w))
                self.set_fill_color(*get_bar_color(score_val))
                self.rect(bar_x, by, fill_w, 4, 'F')

                self.set_xy(180, row_y)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*get_bar_color(score_val))
                self.cell(18, 6, f"{score_val:.0f}/10", 0, 1)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 5. SCORECARD
        # ─────────────────────────────────────────────────────────────
        scorecard = data.get('scorecard', [])
        if scorecard:
            block_title("Detailed Scorecard", SLATE)
            for item in scorecard:
                self.check_space(40)
                dim = sanitize_text(str(item.get('dimension', '')))
                score = sanitize_text(str(item.get('score', 'N/A')))
                sv = self._extract_score_value(score)
                color = get_bar_color(sv)

                self.set_font('Arial', 'B', 10)
                self.set_text_color(*SLATE)
                self.set_x(12)
                self.cell(140, 7, dim, 0, 0)
                self.set_font('Arial', 'B', 12)
                self.set_text_color(*color)
                self.cell(0, 7, score, 0, 1)

                for field, label, fcolor in [
                    ('reasoning', None, TEXT_LIGHT),
                    ('quote', None, INDIGO),
                    ('suggestion', 'Tip: ', EMERALD),
                ]:
                    val = sanitize_text(str(item.get(field, '')))
                    if val:
                        self.set_x(12)
                        prefix = label or ('"' if field == 'quote' else '')
                        suffix = '"' if field == 'quote' else ''
                        self.set_font('Arial', 'I' if field == 'quote' else '', 9)
                        self.set_text_color(*fcolor)
                        self.multi_cell(186, 5, prefix + val + suffix)

                for aq in item.get('alternative_questions', []):
                    q = sanitize_text(str(aq.get('question', '')))
                    r = sanitize_text(str(aq.get('rationale', '')))
                    if q:
                        self.set_x(12)
                        self.set_font('Arial', 'I', 8)
                        self.set_text_color(*BLUE)
                        self.multi_cell(186, 5, f'Try: "{q}" - {r}')

                self.ln(3)
                self.set_draw_color(*COLORS['divider'])
                self.line(12, self.get_y(), 198, self.get_y())
                self.ln(2)

        # ─────────────────────────────────────────────────────────────
        # 6. DEEP DIVE ANALYSIS
        # ─────────────────────────────────────────────────────────────
        dda = data.get('deep_dive_analysis', [])
        if dda:
            block_title("Deep Dive Analysis", INDIGO)
            for item in dda:
                self.check_space(35)
                topic = sanitize_text(str(item.get('topic', '')))
                self.set_fill_color(238, 242, 255)
                self.rect(10, self.get_y(), 190, 8, 'F')
                self.set_xy(14, self.get_y() + 1)
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*INDIGO)
                self.cell(0, 6, topic, 0, 1)
                self.ln(1)

                for key, label in [('tone','Tone'),('language_impact','Language Impact'),('comfort_level','Comfort Level'),
                                    ('impact','Impact'),('questions_asked','Questions'),('exploration','Exploration'),
                                    ('understanding_depth','Understanding Depth'),('analysis','Analysis')]:
                    val = item.get(key, '')
                    if val:
                        self.set_x(15)
                        self.set_font('Arial', 'B', 8)
                        self.set_text_color(*TEXT_LIGHT)
                        self.cell(42, 5, f"{label}:", 0, 0)
                        self.set_font('Arial', '', 8)
                        self.set_text_color(*TEXT_MAIN)
                        self.multi_cell(143, 5, sanitize_text(str(val)))
                self.ln(2)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 7. BEHAVIOURAL PATTERN SUMMARY
        # ─────────────────────────────────────────────────────────────
        ps = data.get('pattern_summary', '')
        if ps:
            block_title("Behavioural Pattern Summary", BLUE)
            self.set_x(15)
            self.set_font('Arial', 'I', 11)
            self.set_text_color(*SLATE)
            self.multi_cell(180, 6, f'"{sanitize_text(str(ps))}"')
            divider()

        # ─────────────────────────────────────────────────────────────
        # 8. EQ ANALYSIS
        # ─────────────────────────────────────────────────────────────
        eq = data.get('eq_analysis', [])
        if eq:
            block_title("EQ & Nuance Analysis", AMBER)
            for item in eq:
                self.check_space(22)
                nuance = sanitize_text(str(item.get('nuance', '')))
                obs = sanitize_text(str(item.get('observation', item.get('proof', ''))))
                suggestion = sanitize_text(str(item.get('suggestion', '')))

                self.set_x(12)
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*AMBER)
                self.cell(0, 6, nuance, 0, 1)
                if obs:
                    self.set_x(15)
                    self.set_font('Arial', 'I', 9)
                    self.set_text_color(*TEXT_LIGHT)
                    self.multi_cell(180, 5, f'"{obs}"')
                if suggestion:
                    self.set_x(15)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*EMERALD)
                    self.multi_cell(180, 5, "-> " + suggestion)
                self.ln(4)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 9. TURNING POINTS
        # ─────────────────────────────────────────────────────────────
        tp_list = data.get('turning_points', [])
        if tp_list:
            block_title("Turning Points Detected", AMBER)
            for tp in tp_list:
                self.check_space(16)
                ts = sanitize_text(str(tp.get('timestamp', '')))
                point = sanitize_text(str(tp.get('point', '')))

                self.set_x(12)
                self.set_font('Arial', 'B', 8)
                self.set_text_color(*AMBER)
                self.cell(0, 5, ts.upper(), 0, 1)
                self.set_x(15)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(180, 5, point)
                self.ln(3)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 10. BEHAVIOUR ANALYSIS
        # ─────────────────────────────────────────────────────────────
        ba = data.get('behaviour_analysis', [])
        if ba:
            block_title("Behaviour Analysis", SLATE)
            for item in ba:
                self.check_space(35)
                behavior = sanitize_text(str(item.get('behavior', '')))
                quote = sanitize_text(str(item.get('quote', '')))
                insight = sanitize_text(str(item.get('insight', '')))
                impact = sanitize_text(str(item.get('impact', '')))
                improved = sanitize_text(str(item.get('improved_approach', '')))
                impact_color = EMERALD if 'positive' in impact.lower() else ROSE

                self.set_fill_color(*LIGHT_BG)
                self.rect(10, self.get_y(), 190, 7, 'F')
                self.set_xy(12, self.get_y() + 1)
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*SLATE)
                self.cell(150, 5, behavior, 0, 0)
                self.set_font('Arial', 'B', 8)
                self.set_text_color(*impact_color)
                self.cell(0, 5, impact.upper(), 0, 1)
                self.ln(1)

                if quote:
                    self.set_x(15)
                    self.set_font('Arial', 'I', 9)
                    self.set_text_color(*INDIGO)
                    self.multi_cell(180, 5, f'"{quote}"')
                if insight:
                    self.set_x(15)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*TEXT_LIGHT)
                    self.multi_cell(180, 5, insight)
                if improved:
                    self.set_x(15)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*EMERALD)
                    self.multi_cell(180, 5, "Better: " + improved)
                self.ln(4)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 11. STRENGTHS & MISSED OPPORTUNITIES (dual column)
        # ─────────────────────────────────────────────────────────────
        si = data.get('strengths_and_improvements', {})
        strengths_list = si.get('strengths', []) if si else data.get('strengths', [])
        missed_list = si.get('missed_opportunities', []) if si else data.get('missed_opportunities', [])
        ideal_qs = data.get('ideal_questions', [])

        if strengths_list or missed_list:
            block_title("Strengths & Missed Opportunities", EMERALD)
            
            # Render both columns with explicit X positioning
            # Left column: X=10 to X=103, Right column: X=107 to X=200
            col_w = 90   # width of each column content area
            top_y = self.get_y()
            
            # --- LEFT COLUMN: KEY STRENGTHS ---
            self.set_xy(10, top_y)
            self.set_fill_color(235, 255, 245)  # Light emerald
            self.rect(10, top_y, col_w + 2, 8, 'F')
            self.set_xy(12, top_y + 1)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*EMERALD)
            self.cell(col_w, 6, "KEY STRENGTHS", 0, 1)
            
            left_y = top_y + 10
            for item in strengths_list:
                self.set_xy(12, left_y)
                self.set_text_color(*EMERALD)
                self.set_font('Arial', 'B', 9)
                self.cell(4, 5, "+", 0, 0)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                # Calculate how many lines this text takes
                self.multi_cell(col_w - 4, 5, sanitize_text(str(item)))
                left_y = self.get_y() + 2
            
            # --- RIGHT COLUMN: MISSED OPPORTUNITIES ---
            right_col_x = 107
            self.set_xy(right_col_x, top_y)
            self.set_fill_color(255, 245, 235)  # Light rose
            self.rect(right_col_x, top_y, col_w + 2, 8, 'F')
            self.set_xy(right_col_x + 2, top_y + 1)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(*ROSE)
            self.cell(col_w, 6, "MISSED OPPORTUNITIES", 0, 1)
            
            right_y = top_y + 10
            for item in missed_list:
                self.set_xy(right_col_x + 2, right_y)
                self.set_text_color(*ROSE)
                self.set_font('Arial', 'B', 9)
                self.cell(4, 5, "!", 0, 0)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(col_w - 4, 5, sanitize_text(str(item)))
                right_y = self.get_y() + 2
            
            # Move cursor past both columns (take the lower of left/right Y)
            self.set_y(max(left_y, right_y) + 2)
            divider()

        if ideal_qs:
            block_title("Ideal Coaching Questions", INDIGO)
            for q in ideal_qs:
                self.check_space(10)
                self.set_x(15)
                self.set_font('Arial', 'I', 9)
                self.set_text_color(*INDIGO)
                self.multi_cell(180, 6, f'"{sanitize_text(str(q))}"')
                self.ln(1)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 12. ACTION PLAN
        # ─────────────────────────────────────────────────────────────
        ap = data.get('action_plan', {})
        if ap:
            block_title("Action Plan", PURPLE)
            owner = sanitize_text(str(ap.get('owner', '')))
            timeline = sanitize_text(str(ap.get('timeline', '')))

            # Two-column info boxes - tracked with a single start_y
            box_y = self.get_y()
            self.set_fill_color(245, 243, 255)
            self.rect(10, box_y, 92, 14, 'F')
            self.rect(108, box_y, 92, 14, 'F')

            self.set_xy(14, box_y + 2)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*PURPLE)
            self.cell(80, 5, "OWNER", 0, 1)
            self.set_xy(14, self.get_y())
            self.set_font('Arial', '', 9)
            self.set_text_color(*TEXT_MAIN)
            self.cell(80, 5, owner, 0, 0)

            self.set_xy(112, box_y + 2)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*PURPLE)
            self.cell(80, 5, "TIMELINE", 0, 1)
            self.set_xy(112, self.get_y())
            self.set_font('Arial', '', 9)
            self.set_text_color(*TEXT_MAIN)
            self.cell(80, 5, timeline, 0, 0)

            # Move cursor past the boxes
            self.set_y(box_y + 18)

            actions = ap.get('specific_actions', [])
            if actions:
                small_label("Specific Actions")
                for i, act in enumerate(actions, 1):
                    self.set_x(12)
                    self.set_font('Arial', 'B', 9)
                    self.set_text_color(*PURPLE)
                    self.cell(8, 5, f"{i}.", 0, 0)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*TEXT_MAIN)
                    self.multi_cell(178, 5, sanitize_text(str(act)))
                    self.ln(1)

            for ind in ap.get('success_indicators', []):
                self.set_x(15)
                self.set_font('Arial', '', 9)
                self.set_text_color(*EMERALD)
                self.multi_cell(180, 5, "+ " + sanitize_text(str(ind)))
            divider()

        # ─────────────────────────────────────────────────────────────
        # 13. FOLLOW-UP STRATEGY
        # ─────────────────────────────────────────────────────────────
        fus = data.get('follow_up_strategy', {})
        if fus:
            block_title("Follow-Up Strategy", BLUE)
            cadence = sanitize_text(str(fus.get('review_cadence', '')))
            if cadence:
                self.set_fill_color(239, 246, 255)
                self.rect(10, self.get_y(), 190, 12, 'F')
                self.set_xy(14, self.get_y() + 2)
                self.set_font('Arial', 'B', 8)
                self.set_text_color(*BLUE)
                self.cell(0, 4, "REVIEW CADENCE", 0, 1)
                self.set_xy(14, self.get_y())
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*TEXT_MAIN)
                self.cell(0, 5, cadence, 0, 1)
                self.ln(2)

            for met in fus.get('metrics_to_track', []):
                self.set_x(15)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(180, 5, "* " + sanitize_text(str(met)))
            self.ln(1)

            method = sanitize_text(str(fus.get('accountability_method', '')))
            if method:
                small_label("Accountability Method")
                body_text(method)
            divider()

        # ─────────────────────────────────────────────────────────────
        # 14. FINAL EVALUATION
        # ─────────────────────────────────────────────────────────────
        fe = data.get('final_evaluation', {})
        if fe:
            self.check_space(60)
            self.add_page()
            block_title("Final Evaluation & Recommendation", INDIGO)

            readiness = sanitize_text(str(fe.get('readiness_level', '')))
            maturity = sanitize_text(str(fe.get('maturity_rating', '')))

            # Two-column badges - single start_y for both
            badge_y = self.get_y()
            self.set_fill_color(238, 242, 255)
            self.rect(10, badge_y, 92, 22, 'F')
            self.set_fill_color(245, 243, 255)
            self.rect(108, badge_y, 92, 22, 'F')

            self.set_xy(14, badge_y + 2)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*INDIGO)
            self.cell(80, 5, "MATURITY RATING", 0, 1)
            self.set_xy(14, self.get_y())
            self.set_font('Arial', 'B', 14)
            sv = self._extract_score_value(maturity)
            self.set_text_color(*get_bar_color(sv))
            self.cell(80, 8, maturity, 0, 0)

            self.set_xy(112, badge_y + 2)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*PURPLE)
            self.cell(80, 5, "READINESS LEVEL", 0, 1)
            self.set_xy(112, self.get_y())
            self.set_font('Arial', 'B', 12)
            self.set_text_color(*PURPLE)
            self.cell(80, 8, readiness, 0, 0)

            # Move cursor past both boxes
            self.set_y(badge_y + 26)

            for foc in fe.get('immediate_focus', []):
                self.set_x(15)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(180, 5, "* " + sanitize_text(str(foc)))
            self.ln(3)

            lt = sanitize_text(str(fe.get('long_term_suggestion', '')))
            if lt:
                small_label("Long-Term Development Suggestion", BLUE)
                self.set_x(15)
                self.set_font('Arial', 'I', 10)
                self.set_text_color(*SLATE)
                self.multi_cell(180, 6, f'"{lt}"')


    def draw_mentorship_report(self, data):
        """
        Renders a reflective, narrative-style mentorship report.
        No scorecard, no scoring. Focus: insights, reflection, growth.
        """
        SLATE = (30, 41, 59)
        TEAL = (20, 184, 166)
        INDIGO = (99, 102, 241) 
        AMBER = (245, 158, 11)
        EMERALD = (16, 185, 129)
        PURPLE = (168, 85, 247)
        BLUE = (59, 130, 246)
        LIGHT_BG = (248, 250, 252)
        TEXT_MAIN = COLORS['text_main']
        TEXT_LIGHT = COLORS['text_light']

        def block_title(title, color):
            self.check_space(18)
            self.ln(6)
            self.set_fill_color(*color)
            self.rect(10, self.get_y(), 3, 9, 'F')
            self.set_xy(16, self.get_y() + 1)
            self.set_font('Arial', 'B', 11)
            self.set_text_color(*color)
            self.cell(0, 7, title.upper(), 0, 1)
            self.ln(2)

        def small_label(text, color=None):
            self.set_x(12)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(*(color or TEXT_LIGHT))
            self.cell(0, 5, text.upper(), 0, 1)

        def body_text(text):
            self.set_x(12)
            self.set_font('Arial', '', 9)
            self.set_text_color(*TEXT_MAIN)
            self.multi_cell(186, 5, sanitize_text(str(text)))

        def divider():
            self.ln(4)
            self.set_draw_color(*COLORS['divider'])
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

        meta = data.get('meta', {})
        summary = meta.get('summary', '')

        # ─── SESSION OVERVIEW ───
        if summary:
            block_title("Session Overview", TEAL)
            body_text(summary)
            divider()

        # ─── EQ & TONE OBSERVATIONS ───
        eq = data.get('eq_analysis', [])
        if eq:
            block_title("Tone & Emotional Observations", AMBER)
            for item in eq:
                self.check_space(18)
                nuance = sanitize_text(str(item.get('nuance', '')))
                obs = sanitize_text(str(item.get('observation', item.get('proof', ''))))
                suggestion = sanitize_text(str(item.get('suggestion', '')))

                self.set_x(12)
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*AMBER)
                self.cell(0, 6, nuance, 0, 1)
                if obs:
                    self.set_x(14)
                    self.set_font('Arial', 'I', 9)
                    self.set_text_color(*TEXT_LIGHT)
                    self.multi_cell(184, 5, f'"{obs}"')
                if suggestion:
                    self.set_x(14)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*EMERALD)
                    self.multi_cell(184, 5, "-> " + suggestion)
                self.ln(4)
            divider()

        # ─── BEHAVIOUR INSIGHTS ───
        ba = data.get('behaviour_analysis', [])
        if ba:
            block_title("Behaviour Insights", SLATE)
            for item in ba:
                self.check_space(30)
                behavior = sanitize_text(str(item.get('behavior', '')))
                quote = sanitize_text(str(item.get('quote', '')))
                insight = sanitize_text(str(item.get('insight', '')))
                impact = sanitize_text(str(item.get('impact', '')))
                improved = sanitize_text(str(item.get('improved_approach', '')))
                impact_color = EMERALD if 'positive' in impact.lower() else (245, 101, 101)

                self.set_fill_color(*LIGHT_BG)
                self.rect(10, self.get_y(), 190, 7, 'F')
                self.set_xy(12, self.get_y() + 1)
                self.set_font('Arial', 'B', 10)
                self.set_text_color(*SLATE)
                self.cell(155, 5, behavior, 0, 0)
                self.set_font('Arial', 'B', 8)
                self.set_text_color(*impact_color)
                self.cell(0, 5, impact.upper(), 0, 1)
                self.ln(1)

                if quote:
                    self.set_x(14)
                    self.set_font('Arial', 'I', 9)
                    self.set_text_color(*INDIGO)
                    self.multi_cell(184, 5, f'"{quote}"')
                if insight:
                    self.set_x(14)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*TEXT_LIGHT)
                    self.multi_cell(184, 5, insight)
                if improved:
                    self.set_x(14)
                    self.set_font('Arial', '', 9)
                    self.set_text_color(*EMERALD)
                    self.multi_cell(184, 5, "Try instead: " + improved)
                self.ln(4)
            divider()

        # ─── KEY INSIGHTS ───
        insights = data.get('key_insights', [])
        if insights:
            block_title("Key Insights", INDIGO)
            for i, ins in enumerate(insights, 1):
                self.check_space(10)
                self.set_x(12)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*INDIGO)
                self.cell(6, 5, f"{i}.", 0, 0)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(180, 5, sanitize_text(str(ins)))
                self.ln(2)
            divider()

        # ─── REFLECTIVE QUESTIONS ───
        rqs = data.get('reflective_questions', [])
        if rqs:
            block_title("Reflective Questions", PURPLE)
            for q in rqs:
                self.check_space(12)
                self.set_fill_color(245, 243, 255)
                start_y = self.get_y()
                self.set_x(12)
                self.set_font('Arial', 'I', 9)
                self.set_text_color(*PURPLE)
                self.multi_cell(186, 6, sanitize_text(str(q)))
                self.ln(2)
            divider()

        # ─── GROWTH OUTCOME ───
        growth = data.get('growth_outcome', '')
        if growth:
            block_title("Growth Vision", EMERALD)
            self.set_fill_color(240, 253, 244)
            self.rect(10, self.get_y(), 190, 4, 'F')
            self.set_x(14)
            self.set_font('Arial', 'I', 10)
            self.set_text_color(*SLATE)
            self.multi_cell(184, 6, f'"{sanitize_text(str(growth))}"')
            divider()

        # ─── PRACTICE PLAN ───
        plan = data.get('practice_plan', [])
        if plan:
            block_title("Practice Plan", BLUE)
            for i, step in enumerate(plan, 1):
                self.check_space(12)
                self.set_x(12)
                self.set_fill_color(*BLUE)
                self.set_font('Arial', 'B', 9)
                self.set_text_color(*BLUE)
                self.cell(6, 5, f"{i}.", 0, 0)
                self.set_font('Arial', '', 9)
                self.set_text_color(*TEXT_MAIN)
                self.multi_cell(181, 5, sanitize_text(str(step)))
                self.ln(2)


def generate_report(transcript, role, ai_role, scenario, framework=None, filename="coaching_report.pdf", mode="coaching", precomputed_data=None, scenario_type=None, user_name="Valued User", ai_character="alex"):


    """
    Generate a UNIFIED PDF report for all scenario types.
    """
    # Auto-detect scenario type if not provided
    if not scenario_type:
        scenario_type = detect_scenario_type(scenario, ai_role, role)
    
    print(f"Generating Unified PDF Report (scenario_type: {scenario_type}) for user: {user_name}...")
    
    # Analyze data or use precomputed
    if precomputed_data:
        data = precomputed_data
        if 'scenario_type' not in data: 
            data['scenario_type'] = scenario_type
    else:
        print("Generating new report data...")
        data = analyze_full_report_data(transcript, role, ai_role, scenario, framework, mode, scenario_type)
    
    # Sanitize data for PDF
    def sanitize_data_recursive(obj):
        if isinstance(obj, str):
            return sanitize_text(obj)
        elif isinstance(obj, dict):
            return {k: sanitize_data_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_data_recursive(item) for item in obj]
        return obj
    
    data = sanitize_data_recursive(data)
    
    pdf = DashboardPDF()
    pdf.set_scenario_type(scenario_type)
    pdf.set_user_name(user_name)
    pdf.set_character(ai_character)
    pdf.set_context(role, ai_role, scenario)
    pdf.add_page()
    
    # Get scenario_type from data if available
    scenario_type = data.get('meta', {}).get('scenario_type', scenario_type)
    
    # 1. Banner (always shown)
    meta = data.get('meta', {})
    pdf.draw_banner(meta, scenario_type=scenario_type)
    
    # 2. Route to correct renderer
    stype = str(scenario_type).lower()
    
    try:
        if 'mentorship' in stype:
            # Mentorship: narrative, reflective, no scoring
            pdf.draw_context_summary()
            pdf.draw_mentorship_report(data)
        else:
            # ALL other scenarios (coaching_sim, coaching, sales, negotiation, custom)
            # use the same rich 14-section SimulationView-aligned renderer
            pdf.draw_coaching_sim_report(data)

        # Transcript always appended at the end
        if transcript:
            pdf.draw_transcript(transcript)

    except Exception as e:
        print(f"Error drawing report body: {e}")
        import traceback
        traceback.print_exc()
        pdf.draw_key_value_grid("RAW DATA DUMP (Drawing Failed)", {k:str(v)[:100] for k,v in data.items() if k != 'meta'})

    pdf.output(filename)
    print(f"[SUCCESS] Unified report saved: {filename} (scenario: {scenario_type})")
