# Mentorship Reflection Report - Implementation Guide

## 🎯 Overview

The **Mentorship Reflection Report** is a new report format that focuses on **learning through observation** rather than performance evaluation. This report analyzes what the AI demonstrated during the conversation, helping participants internalize best practices by observing coaching techniques.

---

## 📋 Report Structure

### **Cover Page (Banner)**
- **Title**: Mentorship Reflection Report
- **Platform**: COACT.ai
- **Mode**: Practice Simulation
- **Subtitle**: "This report summarizes key interaction patterns and learning insights from your practice simulation."
- **Grade Display**: Shows "Practice Simulation" instead of numerical scores

---

### **Section 1: Conversation Snapshot**

#### **A. Simulation Context**
Displays key information in a clean 2×2 grid:
- Your Role
- AI Role
- Scenario Type
- Primary Skill Focus

#### **B. Conversation Flow Overview**
5-7 line narrative summarizing:
- How the conversation started
- Emotional tone evolution
- Major turning points
- Final outcome

**Note**: This narrates the flow, NOT repeating content verbatim.

---

### **Section 2: Interaction Highlights**

#### **A. AI Response Strategy Observed**
Lists techniques the AI demonstrated:
- Emotional labeling before solution
- Calm boundary setting
- Reframing aggressive statements
- Clarifying assumptions
- Asking layered probing questions
- Offering structured negotiation alternatives

**Purpose**: Show what the participant just experienced.

---

#### **B. Questioning Techniques Used by AI**
Actual techniques used during conversation:
- Open-ended exploration
- Reflective paraphrasing
- Assumption testing
- Strategic silence moments
- Perspective shifting
- "What outcome are you aiming for?" style questions

**Purpose**: Becomes learning exposure.

---

#### **C. Emotional Handling Patterns**
How the AI handled tone:
- Managed escalation without reacting
- Acknowledged emotion before facts
- Avoided defensive language
- Separated behaviour from identity

**Purpose**: Critical insight for emotional intelligence.

---

### **Section 3: Turning Points in the Discussion**

Identifies 2-3 key moments in the conversation:

**Turning Point 1**:
- **Description**: When the conversation shifted from confrontation to clarification
- **AI Technique Used**: Specific technique or question that created the shift
- **Impact**: How this changed the conversation trajectory

**Turning Point 2**:
- **Description**: When a reframing question reduced emotional intensity
- **AI Technique Used**: Specific reframe used
- **Impact**: Observable change in tone or direction

**Turning Point 3**:
- **Description**: When options were introduced instead of positional arguments
- **AI Technique Used**: How the AI presented alternatives
- **Impact**: Shift from debate to collaboration

**Purpose**: Makes the report feel intelligent and insightful.

---

### **Section 4: Learning Takeaways for Practice**

**Title**: "What You Can Observe & Practice"

Lists neutral, observational takeaways:
- How emotional acknowledgment changes tone
- How structured questioning slows escalation
- How boundary language protects position
- How reframing shifts negotiation energy
- How silence creates space for reflection

**Purpose**: Keeps language neutral, not evaluative. Focuses on practice.

---

### **Section 5: Example Phrases Demonstrated by AI**

Provides 5-8 specific example lines the AI used during the conversation:

Each example includes:
- **Phrase**: "Help me understand what's most important to you here."
- **Context**: When/where the AI used this in the conversation
- **Technique**: Open-ended exploration / De-escalation

**Examples**:
1. "Help me understand what's most important to you here."
2. "Let's separate the issue from the emotion for a moment."
3. "What outcome would feel fair to you?"
4. "Here's what I can commit to right now."
5. "Can you walk me through your thinking on this?"

**Purpose**: Becomes a practical toolkit for participants.

---

### **Section 6: Alternative Pathways** (Optional but Powerful)

**Note**: "Based on this scenario, other effective approaches could include:"

**Alternatives**:
- Collaborative problem framing
- Option-based negotiation
- De-escalation pause technique
- Interest-based dialogue
- Empathy-first response

**Purpose**: No evaluation—just exposure to other methods. Broadens thinking.

---

### **Section 7: Closing Reflection Prompt**

Ends the report with 3-5 reflection questions:

1. At what moment did the emotional tone shift?
2. Which question changed the direction of the conversation?
3. What would you try differently in a real-world version?
4. What AI technique resonated most with you?
5. How might you adapt these strategies to your own style?

**Purpose**: Makes the platform feel coaching-driven. Encourages deep reflection.

---

## 🔧 Technical Implementation

### **Backend Changes** (`inter-ai-backend/cli_report.py`)

#### **1. Updated LLM Prompt** (Line ~550)
```python
is_mentorship = (session_mode == "mentorship" or mode == "mentorship")

if is_mentorship:
    unified_instruction = f"""
### MENTORSHIP REFLECTION REPORT - OBSERVATION-BASED LEARNING
**Core Principle**: This is a LEARNING EXPOSURE report, NOT a performance evaluation.
**Focus**: Analyze what the AI demonstrated during the conversation.
**CRITICAL**: Do NOT evaluate the user. Do NOT assign numerical scores.
```

**Key Changes**:
- Focus on AI actions, not user performance
- No numerical scores anywhere
- Observation-based language
- Extract AI techniques from transcript

---

#### **2. New PDF Rendering Function** (`draw_mentorship_reflection_report`)

Located at line ~2018, implements:
- Conversation Snapshot section (Simulation Context + Flow)
- Interaction Highlights (AI Strategy, Questions, Emotional Handling)
- Turning Points analysis
- Learning Takeaways display
- Example Phrases with context
- Alternative Pathways
- Closing Reflection Prompts

**Key Design Principles**:
- Clean, modern card-based layout
- Color-coded sections (Blue, Emerald, Indigo, Amber, Purple)
- Quote boxes for AI phrases
- Numbered lists for reflection questions
- No scores or ratings displayed

---

#### **3. Report Routing Logic** (Line ~3020)

```python
session_mode = data.get('meta', {}).get('session_mode', mode)

if session_mode == "mentorship" or data.get('type') == "mentorship_reflection":
    pdf.draw_mentorship_reflection_report(data)
else:
    pdf.draw_coaching_sim_report(data)
```

**Logic**:
- Checks `session_mode` in metadata
- Routes to new mentorship renderer if `session_mode == "mentorship"`
- Falls back to standard coaching report for all other modes

---

#### **4. Banner Update** (Line ~1500)

```python
if meta.get('session_mode') == "mentorship":
    label = "MENTORSHIP REFLECTION"
    icon = "[M]"
    overall_grade = "Practice Simulation"
```

**Changes**:
- Shows "MENTORSHIP REFLECTION" title
- Displays "Practice Simulation" instead of scores
- Uses "[M]" icon for mentorship mode

---

## 📊 JSON Data Schema

The LLM returns this JSON structure for mentorship reports:

```json
{
  "meta": {
    "scenario_id": "mentorship",
    "outcome_status": "Completed",
    "overall_grade": "Practice Simulation",
    "summary": "This report summarizes key interaction patterns...",
    "session_mode": "mentorship",
    "scenario": "Scenario description",
    "user_role": "Participant role",
    "ai_role": "AI coach role"
  },
  "type": "mentorship_reflection",
  
  "conversation_snapshot": {
    "simulation_context": {
      "your_role": "Manager",
      "ai_role": "Team Member",
      "scenario_type": "Conflict Resolution",
      "primary_skill_focus": "De-escalation"
    },
    "conversation_flow_overview": "The conversation started with..."
  },
  
  "interaction_highlights": {
    "ai_response_strategy_observed": [
      "Emotional labeling before solution",
      "Calm boundary setting"
    ],
    "questioning_techniques_used_by_ai": [
      "Open-ended exploration",
      "Reflective paraphrasing"
    ],
    "emotional_handling_patterns": [
      "Managed escalation without reacting",
      "Acknowledged emotion before facts"
    ]
  },
  
  "turning_points": [
    {
      "point_number": 1,
      "description": "When conversation shifted from confrontation to clarification",
      "ai_technique_used": "Reframing question",
      "impact": "Reduced emotional intensity by 50%"
    }
  ],
  
  "learning_takeaways": {
    "what_you_can_observe_and_practice": [
      "How emotional acknowledgment changes tone",
      "How structured questioning slows escalation"
    ]
  },
  
  "example_phrases_demonstrated": [
    {
      "phrase": "Help me understand what's most important to you here.",
      "context": "When tension was rising",
      "technique": "Open-ended exploration"
    }
  ],
  
  "alternative_pathways": {
    "note": "Based on this scenario, other effective approaches could include:",
    "alternatives": [
      "Collaborative problem framing",
      "Option-based negotiation"
    ]
  },
  
  "closing_reflection_prompts": [
    "At what moment did the emotional tone shift?",
    "Which question changed the direction of the conversation?"
  ]
}
```

---

## 🎨 Visual Design

### **Color Palette**
- **Blue (59, 130, 246)**: Primary sections (Conversation Snapshot, Example Phrases)
- **Emerald (16, 185, 129)**: Interaction Highlights, Closing Reflection
- **Indigo (99, 102, 241)**: Questioning Techniques, Learning Takeaways
- **Amber (245, 158, 11)**: Turning Points
- **Purple (168, 85, 247)**: Alternative Pathways, Emotional Handling

### **Typography**
- **Headers**: Helvetica Bold, 11pt, Uppercase
- **Body**: Helvetica Regular, 9pt
- **Quotes**: Helvetica Italic, 10pt, Blue color
- **Labels**: Helvetica Bold, 8pt, Uppercase, Light Gray

### **Layout Elements**
- **Info Boxes**: Light background fills (248, 250, 252)
- **Quote Boxes**: Light blue background (239, 246, 255)
- **Dividers**: Light gray lines between sections
- **Bullet Points**: Color-coded symbols (+, ?, *, ~)

---

## 🚀 Usage

### **Backend API**

When generating a report, set `session_mode="mentorship"`:

```python
from cli_report import generate_report

generate_report(
    transcript=conversation_data,
    role="Participant",
    ai_role="Coach",
    scenario="Conflict Resolution",
    mode="mentorship",  # Or pass session_mode parameter
    filename="mentorship_reflection.pdf",
    user_name="John Doe",
    ai_character="alex"
)
```

### **Frontend Integration**

Ensure the session data includes `session_mode`:

```typescript
const sessionData = {
  mode: "mentorship",
  scenario: "Conflict Resolution",
  // ... other data
}
```

---

## ✅ Key Differences from Standard Reports

| Feature | Standard Report | Mentorship Reflection Report |
|---------|----------------|------------------------------|
| **Focus** | User performance | AI techniques demonstrated |
| **Scoring** | Numerical scores (1-10) | No scores (qualitative only) |
| **Language** | Evaluative ("You did...") | Observational ("The AI demonstrated...") |
| **Purpose** | Performance assessment | Learning through observation |
| **Sections** | 15+ sections with scores | 7 focused narrative sections |
| **Tone** | Professional evaluation | Warm, coaching-oriented |
| **Takeaways** | Improvement areas | Practice opportunities |
| **Examples** | What user should have said | What AI actually said |

---

## 📝 Testing

### **Test Case 1: Verify Routing**
```python
data = {
    "meta": {"session_mode": "mentorship"},
    "type": "mentorship_reflection"
}
# Should route to draw_mentorship_reflection_report()
```

### **Test Case 2: Verify No Scores**
```python
# Check that no numerical scores appear in:
# - Banner (shows "Practice Simulation")
# - Section headers
# - Body content
```

### **Test Case 3: Verify AI Focus**
```python
# Verify LLM prompt includes:
# - "**CRITICAL**: Do NOT evaluate the user"
# - "Focus ONLY on what the AI did"
# - "Analyze what the AI demonstrated"
```

---

## 🔍 Troubleshooting

### **Issue**: Report still shows scores
**Solution**: Verify `session_mode="mentorship"` is set in metadata

### **Issue**: Wrong renderer used
**Solution**: Check routing logic in `generate_report()` function

### **Issue**: AI evaluates user instead of demonstrating techniques
**Solution**: Review LLM prompt - ensure it focuses on ASSISTANT role, not USER

### **Issue**: PDF layout breaks
**Solution**: Check `check_space()` calls before each section to prevent page overflow

---

## 📚 References

- **Main Implementation**: `inter-ai-backend/cli_report.py`
- **LLM Prompt**: Lines 550-640
- **PDF Renderer**: Lines 2018-2300
- **Routing Logic**: Lines 3020-3040
- **Banner Update**: Lines 1500-1520

---

## 🎯 Future Enhancements

1. **Interactive Elements**: Add QR codes linking to video examples
2. **Personalization**: Customize based on participant's role/industry
3. **Benchmarking**: Compare against anonymized peer data (qualitatively)
4. **Multi-Session Tracking**: Show progression across multiple simulations
5. **Export Options**: JSON, HTML, or interactive web version

---

**Status**: ✅ Fully Implemented (March 2026)  
**Version**: 1.0  
**Authors**: COACT.AI Development Team
