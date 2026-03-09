import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_long_conversation():
    print("Testing long conversation flow (20 turns)...")
    
    # 1. Start a session
    resp = requests.post(f"{BASE_URL}/api/session/start", json={
        "role": "Sales Associate",
        "ai_role": "Tough Customer",
        "scenario": "Customer wants a discount on a premium item",
        "title": "Sales Negotiation Practice",
        "mode": "coaching",
        "ai_character": "alex",
        "custom_ai_role": "Tough Customer",
        "scenario_type": "sales",
        "framework": "GROW",
        "user_id": "test_user_123"
    })
    
    if resp.status_code != 200:
        print(f"Failed to start session: {resp.text}")
        return
        
    data = resp.json()
    session_id = data.get("session_id")
    print(f"Started session: {session_id}")
    
    # 2. Simulate 20 turns
    for i in range(1, 21):
        print(f"\n--- Turn {i} ---")
        chat_resp = requests.post(f"{BASE_URL}/api/session/{session_id}/chat", json={
            "message": f"This is turn {i}. I am trying to explain the value of the product to you."
        })
        
        if chat_resp.status_code == 200:
            ai_reply = chat_resp.json().get("follow_up", "")
            print(f"AI: {ai_reply[:100]}...")
            
            # Simulate TTS request the frontend would make
            print(f"Requesting TTS for turn {i}...")
            tts_resp = requests.post(f"{BASE_URL}/api/speak", json={
                "text": ai_reply,
                "voice": "alloy"
            })
            if tts_resp.status_code == 200:
                print(f"TTS Success: {len(tts_resp.content)} bytes")
            else:
                print(f"TTS Failed: {tts_resp.text}")
                
        else:
            print(f"Chat failed on turn {i}: {chat_resp.text}")
            break
            
        time.sleep(1) # brief pause
        
    # 3. Complete session and generate report
    print("\n--- Generating Report ---")
    complete_resp = requests.post(f"{BASE_URL}/api/session/{session_id}/complete")
    
    if complete_resp.status_code == 200:
        print("Session completed successfully!")
        
        # 4. Try fetching report data
        report_data = requests.get(f"{BASE_URL}/api/session/{session_id}/report_data")
        if report_data.status_code == 200:
            print("Successfully fetched JSON report data!")
        else:
            print(f"Failed to fetch report data: {report_data.text}")
            
    else:
        print(f"Failed to complete session: {complete_resp.text}")

if __name__ == "__main__":
    test_long_conversation()
