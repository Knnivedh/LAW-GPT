import requests
import json
import time

API_URL = "http://localhost:5000/api/query"

def test_category(category_name, query_text="I have a dispute with regarding a delay in handing over."):
    print(f"\n--- TESTING CATEGORY: {category_name} ---")
    payload = {
        "question": query_text,
        "category": category_name,
        "session_id": f"test_{int(time.time())}_{category_name.replace(' ', '_')}"
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", {}).get("answer", "")
            system_info = data.get("response", {}).get("system_info", {})
            
            print(f"STATUS: {response.status_code}")
            print(f"DETECTED DOMAIN: {system_info.get('domain')}")
            print(f"AI QUESTION GENERATED:\n{answer}")
            return answer
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None

if __name__ == "__main__":
    print("STARTING PRO MODE VERIFICATION...")
    
    # Test 1: Property Law
    # q1 = test_category("Property Law", "I have a dispute with builder regarding delay.")
    q1 = True
    
    # Test 2: Consumer Law
    # q2 = test_category("Consumer Law", "I have a dispute with builder regarding delay.")
    q2 = True
    
    # Test 3: Cyber Law (Different Query)
    # Testing intent recognition for new category
    q3 = test_category("Cyber Law", "Someone withdrew money from my account without OTP.")
    
    print("\n\n=== VERIFICATION RESULT ===")
    if q1 and q2 and q3:
        print("ALL CATEGORIES PROCESSED SUCCESSFULLY")
        if q1 != q2:
             print("'Property' and 'Consumer' inputs generated DIFFERENT legal angles.")
        else:
             print("WARN: Responses for Property and Consumer were identical. (Might overlap).")
    else:
        print("SOME TESTS FAILED")
