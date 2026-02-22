import os
import sys
import unittest
import json
from unittest.mock import MagicMock, patch

# Ensure we can import from the backend directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'inter-ai-backend')))

# Mock necessary environment variables and imports before importing cli_report
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "mock-endpoint"

from cli_report import analyze_full_report_data, detect_scenario_type

class TestUnifiedReports(unittest.TestCase):
    def setUp(self):
        self.transcript = [
            {"role": "user", "content": "Hello, I need some guidance on my career."},
            {"role": "assistant", "content": "I can help with that. What are your goals?"},
            {"role": "user", "content": "I want to become a manager and lead a team."}
        ]
        self.scenarios = [
            {"name": "Coaching", "scenario": "A manager coaching a staff member", "ai_role": "Staff", "role": "Manager"},
            {"name": "Negotiation", "scenario": "A buyer and seller negotiating price", "ai_role": "Buyer", "role": "Seller"},
            {"name": "Mentorship", "scenario": "A mentor guiding a mentee", "ai_role": "Mentee", "role": "Mentor"},
            {"name": "Learning", "scenario": "A learner reflecting on a session", "ai_role": "Coach", "role": "Learner"}
        ]

    def test_scenario_detection(self):
        for s in self.scenarios:
            stype = detect_scenario_type(s['scenario'], s['ai_role'], s['role'])
            print(f"Detected {s['name']} as: {stype}")
            self.assertIsNotNone(stype)

    @patch('cli_report.llm_reply')
    @patch('cli_report.analyze_character_traits')
    @patch('cli_report.analyze_questions_missed')
    def test_unified_data_structure(self, mock_q, mock_char, mock_llm):
        mock_response = json.dumps({
            "meta": { "scenario_id": "mentorship", "outcome_status": "Completed", "overall_grade": "8/10", "summary": "Great session." },
            "type": "unified_report",
            "executive_summary": { "snapshot": "Snap", "final_score": "8/10", "strengths_summary": "S", "improvements_summary": "I", "outcome_summary": "O" },
            "goal_attainment": { "score": "8/10", "expectation_vs_reality": "E", "primary_gaps": ["G"], "observation_focus": ["F"] },
            "coaching_style": { "primary_style": "Supportive", "description": "D" },
            "deep_dive_analysis": [{"topic": "T", "tone": "T", "impact": "I", "analysis": "A"}],
            "pattern_summary": "P",
            "behaviour_analysis": [{"behavior": "B", "quote": "Q", "insight": "I", "impact": "Positive", "improved_approach": "A"}],
            "turning_points": [{"point": "P", "timestamp": "T"}],
            "eq_analysis": [{ "nuance": "N", "observation": "O", "suggestion": "S" }],
            "heat_map": [{"dimension": "D", "score": 8}],
            "scorecard": [{ "dimension": "D", "score": "8/10", "reasoning": "R", "quote": "Q", "suggestion": "S", "alternative_questions": []}],
            "ideal_questions": ["Q1"],
            "action_plan": { "specific_actions": ["A"], "owner": "User", "timeline": "T", "success_indicators": ["S"] },
            "follow_up_strategy": { "review_cadence": "C", "metrics_to_track": ["M"], "accountability_method": "A" },
            "strengths_and_improvements": { "strengths": ["S"], "missed_opportunities": ["M"] },
            "final_evaluation": { "readiness_level": "R", "maturity_rating": "8/10", "immediate_focus": ["F"], "long_term_suggestion": "S" }
        })
        mock_llm.return_value = mock_response
        mock_char.return_value = {"traits": []}
        mock_q.return_value = {"missed": []}

        for s in self.scenarios:
            print(f"Testing data generation for {s['name']}...")
            data = analyze_full_report_data(self.transcript, s['role'], s['ai_role'], s['scenario'])
            self.assertIn('executive_summary', data)
            self.assertIn('scorecard', data)
            self.assertIn('action_plan', data)
            self.assertIn('final_evaluation', data)
            self.assertEqual(data['type'], "unified_report")

if __name__ == "__main__":
    unittest.main()
