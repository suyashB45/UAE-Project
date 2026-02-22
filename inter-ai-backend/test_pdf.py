from cli_report import generate_report

# Simulated 15-section React-aligned schema payload
precomputed_data = {
  "meta": { "scenario_id": "coaching_sim", "outcome_status": "Completed", "overall_grade": "8/10", "summary": "Executive summary of the coaching effectiveness." },
  "type": "coaching_sim",
  "executive_summary": {
    "snapshot": "The user successfully established psychological safety.", "final_score": "8/10", "strengths_summary": "Great empathy", "improvements_summary": "Missed accountability", "outcome_summary": "Employee agreed to a plan but specifics were vague."
  },
  "goal_attainment": {
    "score": "7/10", "expectation_vs_reality": "Expected concrete plan, got vague agreement.", "primary_gaps": ["No timelines", "No clear owner"], "observation_focus": ["Always set a follow-up review date"]
  },
  "coaching_style": {
    "primary_style": "Supportive",
    "description": "The user prioritized the employee's feelings over the business metrics."
  },
  "deep_dive_analysis": [
    {"topic": "Psychological Safety Creation", "tone": "Warm", "language_impact": "Positive", "comfort_level": "High", "impact": "High", "questions_asked": "How are you feeling?", "exploration": "Good", "understanding_depth": "Surface", "analysis": "Good safety but low challenge."}
  ],
  "pattern_summary": "You build trust well but struggle to demand accountability.",
  "behaviour_analysis": [
    {
      "behavior": "Empathizing",
      "quote": "I hear you, it's been hard.",
      "insight": "Builds trust but needs to pivot to action.",
      "impact": "Positive",
      "improved_approach": "I hear you. Given the difficulty, what's our plan?"
    }
  ],
  "turning_points": [
    {"point": "Conversation slowed down when...", "timestamp": "02:15"}
  ],
  "eq_analysis": [
    {
      "nuance": "Empathetic but vague",
      "observation": "I hear you, let's try better next week.",
      "suggestion": "Be more specific with the word 'better'."
    }
  ],
  "heat_map": [
    { "dimension": "Empathy", "score": 9 },
    { "dimension": "Clarity", "score": 6 }
  ],
  "scorecard": [
    { 
      "dimension": "Empathy & Respect", 
      "score": "9/10", 
      "reasoning": "Excellent use of validating language.",
      "quote": "I hear you.",
      "suggestion": "Pair empathy with a challenge.",
      "alternative_questions": [{"question": "Given that, what's next?", "rationale": "Pivots to action"}]
    }
  ],
  "ideal_questions": ["What is the root cause?", "When will this be done?"],
  "action_plan": {
    "specific_actions": ["Review metrics sheet"], "owner": "Employee", "timeline": "Tomorrow", "success_indicators": ["Sheet is full"]
  },
  "follow_up_strategy": {
    "review_cadence": "Weekly", "metrics_to_track": ["Sales"], "accountability_method": "Email"
  },
  "strengths_and_improvements": {
    "strengths": ["Empathy"], "missed_opportunities": ["Timelines"]
  },
  "final_evaluation": {
    "readiness_level": "Developing", "maturity_rating": "6/10", "immediate_focus": ["Setting timelines"], "long_term_suggestion": "Read radical candor."
  }
}

print("Running testing simulation using exact React-aligned output schema...")
generate_report(
    transcript=[{"role": "user", "content": "I hear you, it has been hard."}],
    role="Manager",
    ai_role="Staff",
    scenario="You are coaching an employee.",
    filename="test_react_schema_alignment.pdf",
    mode="coaching",
    precomputed_data=precomputed_data,
    scenario_type="coaching_sim"
)
print("Finished generation!")
