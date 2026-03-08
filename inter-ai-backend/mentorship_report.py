"""
Mentorship Reflection Report Generator
=======================================
Separate module for generating observation-based mentorship reports (NO scores).
Handles both:
  - LLM prompt construction for mentorship data
  - PDF rendering of the mentorship reflection report
"""

import datetime as dt
from cli_report import (
    COLORS, DashboardPDF, sanitize_text, parse_json_robustly,
    detect_scenario_type, setup_langchain_model, llm,
)
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser


# ─────────────────────────────────────────────────────────────────────
# 1. LLM PROMPT & DATA GENERATION
# ─────────────────────────────────────────────────────────────────────

def build_mentorship_prompt(role, ai_role, scenario, scenario_type):
    """Return the mentorship‑specific LLM instruction string."""
    return f"""
### MENTORSHIP REFLECTION REPORT - OBSERVATION-BASED LEARNING (NO SCORES)
OBJECTIVE: Analyze what the AI DEMONSTRATED in this practice simulation to help the participant learn through observation. Focus ONLY on AI techniques and interaction patterns, NOT on evaluating the user. Absolutely NO numerical scores anywhere.

Return JSON with this EXACT structure:
{{
  "meta": {{
    "scenario_id": "{scenario_type}",
    "outcome_status": "Completed",
    "overall_grade": "Practice Simulation",
    "summary": "This report summarizes key interaction patterns and learning insights from your practice simulation.",
    "session_mode": "mentorship",
    "scenario": "{scenario}"
  }},
  "type": "mentorship_reflection",
  "conversation_snapshot": {{
    "simulation_context": {{
      "your_role": "{role}",
      "ai_role": "{ai_role}",
      "scenario_type": "{scenario_type}",
      "primary_skill_focus": "The main skill being practiced (e.g., Conflict Resolution, Negotiation, Feedback Delivery)"
    }},
    "conversation_flow_overview": "A structured narrative (5-7 lines max) covering: how the conversation started, emotional tone evolution, major turning points, and final outcome. This should NARRATE the flow, NOT repeat content."
  }},
  "interaction_highlights": {{
    "ai_response_strategy_observed": [
      "Strategy 1 - e.g. Emotional labeling before solution",
      "Strategy 2 - e.g. Calm boundary setting",
      "Strategy 3 - e.g. Reframing aggressive statements",
      "Strategy 4 - e.g. Asking layered probing questions",
      "Strategy 5 - e.g. Offering structured negotiation alternatives"
    ],
    "questioning_techniques_used_by_ai": [
      "Technique 1 - e.g. Open-ended exploration",
      "Technique 2 - e.g. Reflective paraphrasing",
      "Technique 3 - e.g. Assumption testing",
      "Technique 4 - e.g. Perspective shifting",
      "Technique 5 - e.g. 'What outcome are you aiming for?' style questions"
    ],
    "emotional_handling_patterns": [
      "Pattern 1 - e.g. Managed escalation without reacting",
      "Pattern 2 - e.g. Acknowledged emotion before facts",
      "Pattern 3 - e.g. Avoided defensive language",
      "Pattern 4 - e.g. Separated behaviour from identity"
    ]
  }},
  "turning_points": [
    {{
      "point_number": 1,
      "title": "Short title of the turning point",
      "description": "When the conversation shifted from confrontation to clarification.",
      "ai_technique_used": "The specific technique the AI used",
      "impact": "How this changed the direction of the conversation"
    }},
    {{
      "point_number": 2,
      "title": "Short title",
      "description": "When a reframing question reduced emotional intensity.",
      "ai_technique_used": "Technique name",
      "impact": "Result of that shift"
    }},
    {{
      "point_number": 3,
      "title": "Short title",
      "description": "When options were introduced instead of positional arguments.",
      "ai_technique_used": "Technique name",
      "impact": "Result"
    }}
  ],
  "learning_takeaways": {{
    "what_you_can_observe_and_practice": [
      "How emotional acknowledgment changes tone",
      "How structured questioning slows escalation",
      "How boundary language protects position",
      "How reframing shifts negotiation energy"
    ]
  }},
  "example_phrases_demonstrated": [
    {{
      "phrase": "Help me understand what's most important to you here.",
      "context": "When/why the AI used this phrase",
      "technique": "Open-ended exploration"
    }},
    {{
      "phrase": "Let's separate the issue from the emotion for a moment.",
      "context": "Context of usage",
      "technique": "De-escalation framing"
    }}
  ],
  "alternative_pathways": {{
    "note": "Based on this scenario, other effective approaches could include:",
    "alternatives": [
      "Collaborative problem framing",
      "Option-based negotiation",
      "De-escalation pause technique"
    ]
  }},
  "closing_reflection_prompts": [
    "At what moment did the emotional tone shift?",
    "Which question changed the direction of the conversation?",
    "What would you try differently in a real-world version?"
  ]
}}

KEY INSTRUCTIONS:
1. Provide 4-6 AI response strategies that were actually demonstrated in the transcript
2. List 4-5 specific questioning techniques the AI used
3. Identify 3-4 emotional handling patterns from the conversation
4. Find exactly 2-3 key turning points where the conversation shifted direction
5. Extract 5-8 VERBATIM example phrases the AI actually said in the transcript
6. Provide 3-4 alternative approaches that could also work for this scenario
7. End with exactly 3 reflection questions
8. Use observational language throughout: 'The AI demonstrated...', 'Notice how...'
9. Ground ALL observations in specific transcript moments
10. NO evaluation of the user. NO scores. NO ratings. Focus on AI strategy ONLY.
11. The conversation_flow_overview should NARRATE the flow (how it started, evolved, concluded) - NOT repeat dialogue.
"""


def analyze_mentorship_report_data(transcript, role, ai_role, scenario,
                                    scenario_type=None, ai_character="alex",
                                    session_mode="mentorship"):
    """
    Generate the JSON data for a mentorship reflection report.
    Uses a single LLM call (no parallel character / question analysis).
    """
    if not scenario_type:
        scenario_type = detect_scenario_type(scenario, ai_role, role)

    meta = {
        "scenario_id": scenario_type,
        "outcome_status": "Completed",
        "overall_grade": "Practice Simulation",
        "summary": "This report summarizes key interaction patterns and learning insights from your practice simulation.",
        "scenario_type": scenario_type,
        "session_mode": "mentorship",
        "scenario": scenario,
    }

    user_msgs = [t for t in transcript if t["role"] == "user"]
    if not user_msgs:
        meta["outcome_status"] = "Not Started"
        meta["summary"] = "Session started but no interaction recorded."
        return {"meta": meta, "type": "mentorship_reflection"}

    unified_instruction = build_mentorship_prompt(role, ai_role, scenario, scenario_type)

    system_prompt = (
        f"You are {ai_character.title() if ai_character else 'a professional coach'} providing a session assessment.\n"
        f"In the conversation below, the human participant is 'USER' (Role: {role}) and the AI assistant is 'ASSISTANT' (Role: {ai_role}).\n"
        f"Your task is to analyze what the AI demonstrated so the user can learn through observation.\n"
        f"Context: {scenario}\n"
        f"\n### ANALYST STYLE: MENTORSHIP OBSERVER\n"
        f"- **Tone**: Objective, encouraging, and insight-driven.\n"
        f"- **Focus**: AI techniques, interaction patterns, and learning moments.\n"
        f"- **Evidence**: Reference specific moments and phrases from the transcript.\n"
        f"- **Language**: Observational — 'Notice how...', 'The AI demonstrated...'\n"
        f"\n{unified_instruction}\n"
        f"Assessment Criteria:\n"
        "1. GROUNDING: Use the transcript below as the sole source of truth.\n"
        "2. EVIDENCE: Include short, verbatim quotes to support your findings.\n"
        "3. DEPTH: Look for tone and subtext in the AI's choices.\n"
        "4. RESPONSE FORMAT: Provide your analysis as a single JSON object matching the requested schema.\n"
    )

    full_conversation = "\n".join(
        [f"{'USER' if t['role'] == 'user' else 'ASSISTANT'}: {t['content']}" for t in transcript]
    )

    parser = JsonOutputParser()
    prompt = PromptTemplate(
        template="{system_prompt}\n\n{format_instructions}\n\n### FULL CONVERSATION\n{conversation}",
        input_variables=["system_prompt", "conversation"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    try:
        chain_raw = prompt | llm
        raw_response = chain_raw.invoke({
            "system_prompt": system_prompt,
            "conversation": full_conversation,
        })

        json_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
        data = parse_json_robustly(json_text)

        if data is None:
            data = parser.parse(json_text)

        # Ensure meta is always present and correct
        if "meta" not in data:
            data["meta"] = {}
        data["meta"]["scenario_type"] = scenario_type
        data["meta"]["session_mode"] = "mentorship"
        if "type" not in data:
            data["type"] = "mentorship_reflection"

        return data

    except Exception as e:
        print(f"[ERROR] Mentorship report generation failed: {e}")
        return {"meta": meta, "type": "mentorship_reflection", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# 2. PDF RENDERING  (operates on a DashboardPDF instance)
# ─────────────────────────────────────────────────────────────────────

# Color palette shared across sections
_SLATE  = (30, 41, 59)
_EMERALD = (16, 185, 129)
_BLUE   = (59, 130, 246)
_AMBER  = (245, 158, 11)
_INDIGO = (99, 102, 241)
_PURPLE = (168, 85, 247)
_TEAL   = (20, 184, 166)
_LIGHT_BG = (248, 250, 252)
_TEXT_MAIN  = COLORS["text_main"]
_TEXT_LIGHT = COLORS["text_light"]
_WHITE  = (255, 255, 255)

_CONTENT_LEFT  = 12
_CONTENT_WIDTH = 186
_BULLET_X      = 16
_BULLET_TEXT_X = 22
_BULLET_TEXT_W = 174


def _section_title(pdf, title, color):
    """Colored accent bar + section heading."""
    pdf.check_space(20)
    pdf.ln(8)
    pdf.set_fill_color(*color)
    pdf.rect(10, pdf.get_y(), 3, 10, "F")
    pdf.set_xy(16, pdf.get_y() + 1.5)
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*color)
    FPDF_cell(pdf, 0, 7, title, 0, 1)
    pdf.ln(3)


def _sub_label(pdf, text, color=None):
    pdf.check_space(10)
    pdf.set_x(_CONTENT_LEFT)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(*(color or _TEXT_LIGHT))
    FPDF_cell(pdf, 0, 5, text.upper(), 0, 1)
    pdf.ln(1)


def _bullet_item(pdf, text, icon=None, icon_color=None):
    pdf.check_space(8)
    if icon and icon_color:
        pdf.set_xy(_BULLET_X, pdf.get_y())
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*icon_color)
        FPDF_cell(pdf, 6, 5, icon, 0, 0)
    else:
        pdf.set_xy(_BULLET_X, pdf.get_y())
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*_TEXT_LIGHT)
        FPDF_cell(pdf, 6, 5, "-", 0, 0)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*_TEXT_MAIN)
    y = pdf.draw_wrapped_text(_BULLET_TEXT_X, pdf.get_y(), _BULLET_TEXT_W, 5, str(text))
    pdf.set_y(y + 1)


def _divider(pdf):
    pdf.ln(4)
    pdf.set_draw_color(*COLORS["divider"])
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)


def FPDF_cell(pdf, *args, **kwargs):
    """Call the base FPDF.cell to bypass DashboardPDF overrides."""
    super(DashboardPDF, pdf).cell(*args, **kwargs)


# ── Cover page (called from DashboardPDF.header) ─────────────────

def draw_mentorship_cover(pdf):
    """Draw the mentorship-specific cover page.
    Called inside DashboardPDF.header() when session_mode == 'mentorship'.
    """
    pdf.linear_gradient(0, 0, 210, 55, (15, 23, 42), (30, 58, 95), "H")

    # Title
    pdf.set_xy(10, 8)
    pdf.set_font("helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    FPDF_cell(pdf, 0, 10, "Mentorship Reflection Report", 0, 0, "L")

    # Platform
    pdf.set_xy(10, 20)
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(147, 197, 253)
    FPDF_cell(pdf, 60, 5, "COACT.AI", 0, 0, "L")

    # Mode badge
    pdf.set_xy(10, 27)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(16, 185, 129)
    FPDF_cell(pdf, 60, 5, "Mode: Practice Simulation", 0, 0, "L")

    # Scenario (right side)
    scenario_txt = getattr(pdf, "scenario_text", "")
    if scenario_txt:
        pdf.set_xy(80, 20)
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(200, 220, 255)
        label = scenario_txt if len(scenario_txt) <= 60 else scenario_txt[:57] + "..."
        FPDF_cell(pdf, 120, 5, f"Scenario: {label}", 0, 0, "R")

    # Participant name
    if hasattr(pdf, "user_name") and pdf.user_name:
        pdf.set_xy(80, 27)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(200, 220, 255)
        FPDF_cell(pdf, 120, 5, f"Participant: {pdf.user_name}", 0, 0, "R")

    # Date
    pdf.set_xy(80, 34)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(200, 220, 255)
    FPDF_cell(pdf, 120, 5, dt.datetime.now().strftime("%B %d, %Y"), 0, 0, "R")

    # Tagline
    pdf.set_xy(10, 42)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    FPDF_cell(
        pdf, 0, 5,
        "This report summarizes key interaction patterns and learning insights from your practice simulation.",
        0, 0, "L",
    )
    pdf.ln(50)


# ── Body sections ────────────────────────────────────────────────

def draw_mentorship_body(pdf, data):
    """
    Render all 7 sections of the Mentorship Reflection Report on *pdf*.

    Sections:
      1. Conversation Snapshot (Context + Flow Overview)
      2. Interaction Highlights (AI Strategy, Questioning, Emotional Handling)
      3. Turning Points in the Discussion
      4. Learning Takeaways for Practice
      5. Example Phrases Demonstrated by AI
      6. Alternative Pathways
      7. Closing Reflection Prompt
    """

    # ═══════════════════════════════════════════════════════════════
    # SECTION 1: CONVERSATION SNAPSHOT
    # ═══════════════════════════════════════════════════════════════
    snapshot = data.get("conversation_snapshot", {})
    if snapshot:
        _section_title(pdf, "Conversation Snapshot", _BLUE)

        # ── Simulation Context Card ──
        sim = snapshot.get("simulation_context", {})
        if sim:
            _sub_label(pdf, "Simulation Context", _BLUE)
            card_y = pdf.get_y()
            pdf.set_fill_color(*_LIGHT_BG)
            pdf.rect(10, card_y, 190, 34, "F")
            pdf.set_draw_color(226, 232, 240)
            pdf.rect(10, card_y, 190, 34, "D")

            # Row 1
            pdf.set_xy(15, card_y + 3)
            pdf.set_font("helvetica", "B", 7.5)
            pdf.set_text_color(*_TEXT_LIGHT)
            FPDF_cell(pdf, 90, 4, "YOUR ROLE", 0, 0)
            FPDF_cell(pdf, 0, 4, "AI ROLE", 0, 1)

            pdf.set_xy(15, card_y + 8)
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(*_TEXT_MAIN)
            FPDF_cell(pdf, 90, 5, sanitize_text(str(sim.get("your_role", "-"))), 0, 0)
            FPDF_cell(pdf, 0, 5, sanitize_text(str(sim.get("ai_role", "-"))), 0, 1)

            # Row 2
            pdf.set_xy(15, card_y + 17)
            pdf.set_font("helvetica", "B", 7.5)
            pdf.set_text_color(*_TEXT_LIGHT)
            FPDF_cell(pdf, 90, 4, "SCENARIO TYPE", 0, 0)
            FPDF_cell(pdf, 0, 4, "PRIMARY SKILL FOCUS", 0, 1)

            pdf.set_xy(15, card_y + 22)
            pdf.set_font("helvetica", "", 9.5)
            pdf.set_text_color(*_TEXT_MAIN)
            FPDF_cell(pdf, 90, 5, sanitize_text(str(sim.get("scenario_type", "-"))), 0, 0)
            FPDF_cell(pdf, 0, 5, sanitize_text(str(sim.get("primary_skill_focus", "-"))), 0, 1)

            pdf.set_y(card_y + 37)

        # ── Conversation Flow Overview ──
        flow = snapshot.get("conversation_flow_overview", "")
        if flow:
            _sub_label(pdf, "Conversation Flow Overview", _BLUE)
            pdf.set_font("helvetica", "", 9)
            pdf.set_text_color(*_TEXT_MAIN)
            y = pdf.draw_wrapped_text(_CONTENT_LEFT, pdf.get_y(), _CONTENT_WIDTH, 5, str(flow))
            pdf.set_y(y)

        _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 2: INTERACTION HIGHLIGHTS
    # ═══════════════════════════════════════════════════════════════
    highlights = data.get("interaction_highlights", {})
    if highlights:
        _section_title(pdf, "Interaction Highlights", _EMERALD)

        # 2.1 AI Response Strategy Observed
        strategies = highlights.get("ai_response_strategy_observed", [])
        if strategies:
            _sub_label(pdf, "AI Response Strategy Observed", _EMERALD)
            pdf.set_x(_CONTENT_LEFT)
            pdf.set_font("helvetica", "I", 8.5)
            pdf.set_text_color(*_TEXT_LIGHT)
            FPDF_cell(pdf, 0, 5, "What techniques did the AI demonstrate?", 0, 1)
            pdf.ln(1)
            for s in strategies:
                _bullet_item(pdf, s, "+", _EMERALD)
            pdf.ln(3)

        # 2.2 Questioning Techniques Used by AI
        questions = highlights.get("questioning_techniques_used_by_ai", [])
        if questions:
            _sub_label(pdf, "Questioning Techniques Used by AI", _INDIGO)
            for q in questions:
                _bullet_item(pdf, q, "?", _INDIGO)
            pdf.ln(3)

        # 2.3 Emotional Handling Patterns
        emotional = highlights.get("emotional_handling_patterns", [])
        if emotional:
            _sub_label(pdf, "Emotional Handling Patterns", _PURPLE)
            for e in emotional:
                _bullet_item(pdf, e, "*", _PURPLE)
            pdf.ln(2)

        _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 3: TURNING POINTS IN THE DISCUSSION
    # ═══════════════════════════════════════════════════════════════
    turning = data.get("turning_points", [])
    if turning:
        _section_title(pdf, "Turning Points in the Discussion", _AMBER)

        for tp in turning:
            num = tp.get("point_number", "")
            title = tp.get("title", "")
            desc = tp.get("description", "")
            technique = tp.get("ai_technique_used", "")
            impact = tp.get("impact", "")

            pdf.check_space(30)

            # Header bar
            tp_y = pdf.get_y()
            pdf.set_fill_color(255, 251, 235)  # Amber-50
            pdf.rect(10, tp_y, 190, 8, "F")
            pdf.set_xy(15, tp_y + 1.5)
            pdf.set_font("helvetica", "B", 10)
            pdf.set_text_color(*_AMBER)
            tp_label = f"Turning Point {num}"
            if title:
                tp_label += f":  {sanitize_text(str(title))}"
            FPDF_cell(pdf, 0, 5, tp_label, 0, 1)
            pdf.set_y(tp_y + 10)

            if desc:
                pdf.set_font("helvetica", "", 9)
                pdf.set_text_color(*_TEXT_MAIN)
                y = pdf.draw_wrapped_text(15, pdf.get_y(), 180, 5, str(desc))
                pdf.set_y(y + 1)

            if technique:
                pdf.set_xy(15, pdf.get_y())
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*_AMBER)
                FPDF_cell(pdf, 28, 5, "AI Technique:", 0, 0)
                pdf.set_font("helvetica", "I", 9)
                pdf.set_text_color(*_TEXT_MAIN)
                y = pdf.draw_wrapped_text(43, pdf.get_y(), 152, 5, str(technique))
                pdf.set_y(y + 1)

            if impact:
                pdf.set_xy(15, pdf.get_y())
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*_TEXT_LIGHT)
                FPDF_cell(pdf, 16, 5, "Impact:", 0, 0)
                pdf.set_font("helvetica", "", 9)
                pdf.set_text_color(*_TEXT_LIGHT)
                y = pdf.draw_wrapped_text(31, pdf.get_y(), 164, 5, str(impact))
                pdf.set_y(y + 1)

            pdf.ln(3)

        _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 4: LEARNING TAKEAWAYS FOR PRACTICE
    # ═══════════════════════════════════════════════════════════════
    learning = data.get("learning_takeaways", {})
    if learning:
        _section_title(pdf, "Learning Takeaways for Practice", _TEAL)

        takeaways = learning.get("what_you_can_observe_and_practice", []) if isinstance(learning, dict) else learning
        if takeaways:
            _sub_label(pdf, "What You Can Observe & Practice", _TEAL)
            for t in takeaways:
                _bullet_item(pdf, t, ">", _TEAL)

        _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 5: EXAMPLE PHRASES DEMONSTRATED BY AI
    # ═══════════════════════════════════════════════════════════════
    examples = data.get("example_phrases_demonstrated", [])
    if examples:
        _section_title(pdf, "Example Phrases Demonstrated by AI", _BLUE)
        _sub_label(pdf, "Specific Lines Used During Conversation", _BLUE)
        pdf.ln(1)

        for ex in examples:
            phrase = ex.get("phrase", "")
            context = ex.get("context", "")
            technique = ex.get("technique", "")
            if not phrase:
                continue

            pdf.check_space(22)

            # Measure phrase height
            pdf.set_font("helvetica", "I", 10)
            words = str(phrase).split(" ")
            lines = []
            cur = ""
            for w in words:
                test = f"{cur} {w}".strip() if cur else w
                if pdf.get_string_width(test) <= 172:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            phrase_h = max(len(lines) * 5.5, 8)
            box_h = phrase_h + 6

            quote_y = pdf.get_y()
            pdf.set_fill_color(239, 246, 255)  # Blue-50
            pdf.rect(12, quote_y, 186, box_h, "F")
            pdf.set_fill_color(*_BLUE)
            pdf.rect(12, quote_y, 2, box_h, "F")

            pdf.set_font("helvetica", "I", 10)
            pdf.set_text_color(*_BLUE)
            y = pdf.draw_wrapped_text(18, quote_y + 3, 172, 5.5, f'"{sanitize_text(str(phrase))}"')
            pdf.set_y(quote_y + box_h + 1)

            if technique:
                pdf.set_xy(16, pdf.get_y())
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*_TEXT_LIGHT)
                FPDF_cell(pdf, 22, 5, "TECHNIQUE:", 0, 0)
                pdf.set_font("helvetica", "", 8)
                pdf.set_text_color(*_TEXT_MAIN)
                y = pdf.draw_wrapped_text(38, pdf.get_y(), 158, 5, str(technique))
                pdf.set_y(y)

            if context:
                pdf.set_xy(16, pdf.get_y())
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*_TEXT_LIGHT)
                FPDF_cell(pdf, 22, 5, "CONTEXT:", 0, 0)
                pdf.set_font("helvetica", "", 8)
                pdf.set_text_color(*_TEXT_MAIN)
                y = pdf.draw_wrapped_text(38, pdf.get_y(), 158, 5, str(context))
                pdf.set_y(y)

            pdf.ln(3)

        _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 6: ALTERNATIVE PATHWAYS
    # ═══════════════════════════════════════════════════════════════
    alt = data.get("alternative_pathways", {})
    if alt:
        alternatives = alt.get("alternatives", [])
        if alternatives:
            _section_title(pdf, "Alternative Pathways", _PURPLE)

            note = alt.get("note", "Based on this scenario, other effective approaches could include:")
            pdf.set_x(_CONTENT_LEFT)
            pdf.set_font("helvetica", "I", 9)
            pdf.set_text_color(*_TEXT_LIGHT)
            y = pdf.draw_wrapped_text(_CONTENT_LEFT, pdf.get_y(), _CONTENT_WIDTH, 5, str(note))
            pdf.set_y(y + 2)

            for a in alternatives:
                _bullet_item(pdf, a, "~", _PURPLE)

            _divider(pdf)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 7: CLOSING REFLECTION PROMPT
    # ═══════════════════════════════════════════════════════════════
    prompts = data.get("closing_reflection_prompts", [])
    if prompts:
        _section_title(pdf, "Closing Reflection Prompt", _EMERALD)

        bar_y = pdf.get_y()
        pdf.set_fill_color(236, 253, 245)  # Emerald-50
        pdf.rect(10, bar_y, 190, 8, "F")
        pdf.set_xy(15, bar_y + 1.5)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*_EMERALD)
        FPDF_cell(pdf, 0, 5, "Reflect on These Questions:", 0, 1)
        pdf.set_y(bar_y + 11)

        for i, prompt in enumerate(prompts, 1):
            pdf.check_space(10)
            pdf.set_xy(15, pdf.get_y())
            pdf.set_font("helvetica", "B", 9)
            pdf.set_text_color(*_EMERALD)
            FPDF_cell(pdf, 8, 6, f"{i}.", 0, 0)
            pdf.set_font("helvetica", "I", 9)
            pdf.set_text_color(*_TEXT_MAIN)
            y = pdf.draw_wrapped_text(23, pdf.get_y(), 173, 6, str(prompt))
            pdf.set_y(y + 2)


# ─────────────────────────────────────────────────────────────────────
# 3. PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def generate_mentorship_report(transcript, role, ai_role, scenario,
                                filename="mentorship_report.pdf",
                                precomputed_data=None, scenario_type=None,
                                user_name="Valued User", ai_character="alex"):
    """
    Top-level function: analyse transcript → render mentorship PDF.
    Can also accept precomputed JSON data to skip the LLM call.
    """
    if not scenario_type:
        scenario_type = detect_scenario_type(scenario, ai_role, role)

    print(f"[MENTORSHIP] Generating report (scenario: {scenario_type}) for {user_name}...")

    # 1. Data
    if precomputed_data:
        data = precomputed_data
        if "scenario_type" not in data:
            data["scenario_type"] = scenario_type
    else:
        data = analyze_mentorship_report_data(
            transcript, role, ai_role, scenario,
            scenario_type=scenario_type, ai_character=ai_character,
        )

    # Sanitize
    def _sanitize(obj):
        if isinstance(obj, str):
            return sanitize_text(obj)
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(i) for i in obj]
        return obj

    data = _sanitize(data)

    # 2. Build PDF
    pdf = DashboardPDF()
    pdf.set_scenario_type(scenario_type)
    pdf.set_user_name(user_name)
    pdf.set_character(ai_character)
    pdf.set_context(role, ai_role, scenario)
    pdf._session_mode = "mentorship"

    pdf.add_page()   # triggers header() → mentorship cover

    # Body
    draw_mentorship_body(pdf, data)

    # Transcript
    if transcript:
        pdf.draw_transcript(transcript)

    pdf.output(filename)
    print(f"[MENTORSHIP] Report saved: {filename}")
    return data
