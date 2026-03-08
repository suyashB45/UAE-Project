# Mentorship Report Integration Guide

## 🎯 Quick Start

To generate the new **Mentorship Reflection Report** (observation-based, no scores), simply pass `session_mode="mentorship"` when calling the report generation endpoint.

---

## 📡 API Integration

### **Option 1: Via Flask Endpoint** (Recommended)

```python
# In app.py or your API endpoint
from cli_report import analyze_full_report_data, generate_report

@app.route('/api/report/generate', methods=['POST'])
def generate_session_report():
    data = request.json
    
    transcript = data.get('transcript', [])
    session_data = data.get('session_data', {})
    user_name = data.get('user_name', 'Participant')
    
    # KEY: Set session_mode to "mentorship" for the new report format
    session_mode = session_data.get('mode', 'coaching')  # Get from session data
    
    # Generate report with mentorship mode
    filename = f"reports/{user_name}_mentorship_reflection.pdf"
    
    generate_report(
        transcript=transcript,
        role=session_data.get('role', 'Participant'),
        ai_role=session_data.get('ai_role', 'Coach'),
        scenario=session_data.get('scenario', 'General Coaching'),
        mode=session_mode,  # Pass "mentorship" here
        filename=filename,
        user_name=user_name,
        ai_character=session_data.get('ai_character', 'alex')
    )
    
    return jsonify({"status": "success", "filename": filename})
```

---

### **Option 2: Direct Function Call**

```python
from cli_report import generate_report

# Example conversation transcript
transcript = [
    {"role": "user", "content": "I'm feeling overwhelmed with the project."},
    {"role": "assistant", "content": "Help me understand what's most important to you here."},
    {"role": "user", "content": "I think it's the deadline pressure."},
    {"role": "assistant", "content": "Let's separate the issue from the emotion for a moment. What specifically about the deadline is creating pressure?"}
]

# Generate mentorship reflection report
generate_report(
    transcript=transcript,
    role="Manager",
    ai_role="Team Member",
    scenario="Conflict Resolution - Deadline Pressure",
    framework=None,
    filename="mentorship_report.pdf",
    mode="mentorship",  # THIS IS KEY!
    user_name="Jane Smith",
    ai_character="alex"
)
```

**Output**: `mentorship_report.pdf` with observation-based learning content (NO SCORES)

---

### **Option 3: Using Precomputed Data**

```python
from cli_report import analyze_full_report_data, generate_report

# Step 1: Analyze transcript with mentorship mode
analysis_data = analyze_full_report_data(
    transcript=transcript,
    role="Sales Rep",
    ai_role="Difficult Customer",
    scenario="Handling Objections",
    mode="mentorship",  # Critical parameter
    scenario_type="sales",
    ai_character="sarah"
)

# Step 2: Generate PDF from precomputed data
generate_report(
    transcript=transcript,
    role="Sales Rep",
    ai_role="Difficult Customer",
    scenario="Handling Objections",
    filename="sales_mentorship.pdf",
    mode="mentorship",
    precomputed_data=analysis_data,  # Pass analyzed data
    user_name="John Doe"
)
```

---

## 🔄 Frontend Integration

### **React/TypeScript Frontend**

```typescript
// In your Practice.tsx or Report.tsx component

const generateMentorshipReport = async (sessionId: string) => {
  const response = await fetch(`${API_URL}/api/report/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      user_name: userName,
      session_data: {
        mode: 'mentorship',  // KEY: Set mode to mentorship
        role: 'Manager',
        ai_role: 'Team Member',
        scenario: sessionData.scenario,
        ai_character: 'alex'
      },
      transcript: conversationHistory
    })
  });
  
  const { filename } = await response.json();
  
  // Download or display the PDF
  window.open(`${API_URL}/reports/${filename}`, '_blank');
};
```

---

### **Session Data Structure**

Make sure your session data includes the `mode` field:

```typescript
interface SessionData {
  session_id: string;
  mode: 'coaching' | 'mentorship';  // Use 'mentorship' for new format
  role: string;
  ai_role: string;
  scenario: string;
  ai_character?: 'alex' | 'sarah';
  multi_characters?: boolean;
}

// Example
const mentorshipSession: SessionData = {
  session_id: 'abc123',
  mode: 'mentorship',  // ← This triggers the new report format
  role: 'Participant',
  ai_role: 'Coach',
  scenario: 'Conflict Resolution',
  ai_character: 'alex'
};
```

---

## 🧪 Testing the Integration

### **Test 1: Basic Mentorship Report**

```python
# test_mentorship_report.py
from cli_report import generate_report

transcript = [
    {"role": "user", "content": "I need help with my team."},
    {"role": "assistant", "content": "What specific challenge are you facing?"}
]

generate_report(
    transcript=transcript,
    role="Manager",
    ai_role="HR Advisor",
    scenario="Team Management",
    mode="mentorship",
    filename="test_mentorship.pdf",
    user_name="Test User"
)

print("✅ Test PDF generated: test_mentorship.pdf")
```

**Expected Output**:
- PDF with "MENTORSHIP REFLECTION" title
- Banner shows "Practice Simulation" (not a score)
- Sections focus on AI techniques
- No numerical scores anywhere

---

### **Test 2: Verify Routing**

```python
# Test that mentorship mode routes correctly
from cli_report import analyze_full_report_data

data = analyze_full_report_data(
    transcript=transcript,
    role="User",
    ai_role="Coach",
    scenario="General",
    mode="mentorship"
)

# Check that data has correct structure
assert data['type'] == 'mentorship_reflection'
assert data['meta']['session_mode'] == 'mentorship'
assert 'conversation_snapshot' in data
assert 'interaction_highlights' in data
print("✅ Routing test passed")
```

---

### **Test 3: Compare Standard vs Mentorship**

```python
# Generate both report types for comparison
transcript = [...]  # Your transcript

# Standard coaching report (with scores)
generate_report(
    transcript=transcript,
    role="User",
    ai_role="Coach",
    scenario="Test",
    mode="coaching",  # Standard mode
    filename="standard_report.pdf"
)

# Mentorship reflection report (no scores)
generate_report(
    transcript=transcript,
    role="User",
    ai_role="Coach",
    scenario="Test",
    mode="mentorship",  # Mentorship mode
    filename="mentorship_report.pdf"
)

print("✅ Both reports generated for comparison")
```

---

## 🎯 What Changes in Mentorship Mode?

| Aspect | Standard Report | Mentorship Report |
|--------|----------------|-------------------|
| **Title** | "Coaching Efficacy X/10" | "Mentorship Reflection - Practice Simulation" |
| **Focus** | Evaluates user performance | Analyzes AI techniques |
| **Sections** | 15+ sections with scoring | 7 narrative sections |
| **Language** | "You did...", "Your score..." | "The AI demonstrated...", "Notice how..." |
| **Scores** | Numerical (1-10) throughout | None (qualitative only) |
| **Purpose** | Performance assessment | Learning through observation |
| **Takeaways** | "Areas for improvement" | "What you can observe & practice" |
| **Examples** | "Better question: ..." | "AI used: 'Help me understand...'" |

---

## 🚨 Important Notes

### **1. Mode Parameter Priority**

The system checks for mentorship mode in this order:
1. `session_mode` in metadata
2. `mode` parameter passed to function
3. Falls back to "coaching" if neither is set

### **2. Backward Compatibility**

- ✅ Existing standard reports continue to work
- ✅ All old API calls remain functional
- ✅ Only sessions with `mode="mentorship"` use new format

### **3. AI Character Compatibility**

Both "alex" and "sarah" characters work with mentorship mode:
- **Alex**: Professional, analytical tone
- **Sarah**: Warm, empathetic tone

Choose based on your scenario context.

---

## 🔧 Troubleshooting

### **Problem**: Report still shows scores

**Solution**: 
```python
# Make sure mode is explicitly set
generate_report(
    ...,
    mode="mentorship",  # MUST be "mentorship", not "coaching"
    ...
)
```

---

### **Problem**: Wrong report format generated

**Diagnosis**:
```python
# Check the data structure
data = analyze_full_report_data(..., mode="mentorship")
print(data.get('type'))  # Should be "mentorship_reflection"
print(data.get('meta', {}).get('session_mode'))  # Should be "mentorship"
```

**Solution**: Verify `mode="mentorship"` is passed to both analyze and generate functions.

---

### **Problem**: Missing sections in PDF

**Diagnosis**: Check that the LLM returned the correct JSON structure

**Solution**:
```python
# Add debug logging
import json

data = analyze_full_report_data(..., mode="mentorship")
print(json.dumps(data, indent=2))

# Verify these keys exist:
# - conversation_snapshot
# - interaction_highlights
# - turning_points
# - learning_takeaways
# - example_phrases_demonstrated
# - alternative_pathways
# - closing_reflection_prompts
```

---

## 📊 Example API Response

### **Request**:
```json
{
  "session_id": "abc123",
  "user_name": "Jane Doe",
  "session_data": {
    "mode": "mentorship",
    "role": "Manager",
    "ai_role": "Team Member",
    "scenario": "Performance Feedback",
    "ai_character": "alex"
  },
  "transcript": [
    {"role": "user", "content": "I need to give feedback."},
    {"role": "assistant", "content": "What's most important to address?"}
  ]
}
```

### **Response**:
```json
{
  "status": "success",
  "report_type": "mentorship_reflection",
  "filename": "Jane_Doe_mentorship_reflection.pdf",
  "summary": "This report summarizes key interaction patterns and learning insights from your practice simulation.",
  "sections": [
    "Conversation Snapshot",
    "Interaction Highlights",
    "Turning Points",
    "Learning Takeaways",
    "Example Phrases",
    "Alternative Pathways",
    "Reflection Prompts"
  ]
}
```

---

## ✅ Implementation Checklist

Before deploying mentorship reports:

- [ ] Update session creation to include `mode` field
- [ ] Add UI toggle for "Mentorship Mode" vs "Coaching Mode"
- [ ] Test report generation with sample transcripts
- [ ] Verify no scores appear in mentorship PDFs
- [ ] Check that AI techniques are properly extracted
- [ ] Validate turning points are identified correctly
- [ ] Ensure example phrases include verbatim AI quotes
- [ ] Test with both "alex" and "sarah" AI characters
- [ ] Verify PDF downloads correctly in frontend
- [ ] Add analytics tracking for mentorship report usage

---

## 🎓 Best Practices

### **1. When to Use Mentorship Mode**

✅ **Use Mentorship Mode For**:
- Practice simulations where users want to learn techniques
- Onboarding sessions to demonstrate best practices
- Training scenarios focused on observation
- Sessions where evaluation anxiety might hinder learning

❌ **Use Standard Mode For**:
- Performance assessments and evaluations
- Skill gap analysis
- Certification or competency validation
- When participants need specific scoring/benchmarking

---

### **2. Transcript Quality**

For best results:
- Ensure AI responses demonstrate varied techniques
- Include 2-3 clear conversation turning points
- Capture emotional shifts (escalation → de-escalation)
- Use diverse question types in AI responses
- Keep conversations at least 8-10 exchanges

---

### **3. AI Character Selection**

**Choose Alex** when:
- Professional, corporate scenarios
- Analytical, logic-driven conversations
- Sales, negotiation, leadership contexts

**Choose Sarah** when:
- Emotional intelligence is key
- Mentorship, wellness, career development
- High-empathy scenarios

---

## 📚 Related Documentation

- [MENTORSHIP_REPORT_FORMAT.md](./MENTORSHIP_REPORT_FORMAT.md) - Detailed specification
- [cli_report.py](./inter-ai-backend/cli_report.py) - Implementation code
- [API Documentation](./inter-ai-backend/README.md) - Full API reference

---

**Last Updated**: March 5, 2026  
**Version**: 1.0  
**Status**: ✅ Production Ready
