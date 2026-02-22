import os
import sys
from dotenv import load_dotenv

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from cli_report import generate_report, analyze_full_report_data

def test_pdf_rendering():
    print("Testing PDF rendering with mock data...")
    mock_data = {
        "meta": {
            "scenario_id": "test_scenario",
            "outcome_status": "Completed",
            "overall_grade": "8/10",
            "summary": "This is a test summary."
        },
        "executive_summary": {
            "snapshot": "Good performance overall.",
            "final_score": "8/10",
            "strengths_summary": "Strong opening.",
            "improvements_summary": "Need better closing.",
            "outcome_summary": "Success."
        },
        "scorecard": [
            {"dimension": "Communication", "score": "9/10", "reasoning": "Clear and concise."},
            {"dimension": "Empathy", "score": "7/10", "reasoning": "Could be warmer."}
        ],
        "heat_map": [
            {"dimension": "Clarity", "score": 9},
            {"dimension": "Tone", "score": 7}
        ]
    }
    
    transcript = [
        {"role": "user", "content": "Hello, I want to talk about my performance."},
        {"role": "assistant", "content": "Sure, let's talk about it."}
    ]
    
    try:
        generate_report(
            transcript=transcript,
            role="Manager",
            ai_role="Employee",
            scenario="Performance Review",
            filename="verification_report.pdf",
            precomputed_data=mock_data,
            scenario_type="coaching_sim"
        )
        print("[SUCCESS] PDF rendered to verification_report.pdf")
    except Exception as e:
        print(f"[FAILED] PDF rendering failed: {e}")

def test_llm_analysis():
    print("\nTesting LLM analysis (requires API keys)...")
    if not os.getenv("AZURE_OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("[SKIP] No API keys found in environment.")
        return

    transcript = [
        {"role": "user", "content": "I'm worried about the upcoming project deadline."},
        {"role": "assistant", "content": "I understand. What specifically is worrying you?"},
        {"role": "user", "content": "We don't have enough resources to finish on time."},
        {"role": "assistant", "content": "Let's look at the resource allocation and see where we can optimize."}
    ]
    
    try:
        data = analyze_full_report_data(
            transcript=transcript,
            role="Employee",
            ai_role="Manager",
            scenario="Resource Planning",
            scenario_type="coaching"
        )
        print("[SUCCESS] LLM analysis completed.")
        print(f"Outcome Status: {data.get('meta', {}).get('outcome_status')}")
    except Exception as e:
        print(f"[FAILED] LLM analysis failed: {e}")

if __name__ == "__main__":
    load_dotenv()
    test_pdf_rendering()
    test_llm_analysis()
