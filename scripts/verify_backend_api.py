import requests
import json
import time

API_URL = "http://localhost:7860/api/query"

def test_backend():
    print("🚀 Starting Comprehensive Backend Verification...")
    print(f"📡 Connecting to: {API_URL}")
    
    # 1. Health Check
    try:
        health = requests.get("http://localhost:7860/health")
        if health.status_code == 200:
            print("✅ Health Check: PASSED")
        else:
            print(f"❌ Health Check Failed: {health.status_code}")
            return
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return

    # 2. Complex Legal Query
    query = "Explain Article 21 of the Indian Constitution and cite landmark cases like Maneka Gandhi."
    payload = {
        "question": query,
        "category": "Constitutional Law"
    }
    
    print(f"\n❓ Sending Query: '{query}'")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            
            print(f"\n⏱️ Response Time: {duration:.2f}s")
            print("-" * 50)
            print("📝 GENERATED ANSWER:\n")
            print(answer[:500] + "..." if len(answer) > 500 else answer) # Truncate for display
            print("-" * 50)
            
            # 3. Validation Logic
            if "Article 21" in answer or "life and personal liberty" in answer.lower():
                print("✅ Relevance Check: PASSED (Topic found)")
            else:
                print("⚠️ Relevance Check: WARNING (Topic description might be missing)")
                
            if len(sources) > 0:
                print(f"✅ Source Retrieval: PASSED ({len(sources)} documents found)")
                # Check for Supabase
                if any("supabase" in str(s).lower() or "cases" in str(s).lower() for s in sources):
                     print("✅ Database Integration: PASSED (Retrieved from Supabase/Vector Store)")
            else:
                print("❌ Source Retrieval: FAILED (No sources found - DB might be empty or disconnected)")

            if "Maneka Gandhi" in answer:
                 print("✅ Specific Case Law Check: PASSED (Maneka Gandhi found)")
            else:
                 print("⚠️ Specific Case Law Check: MISSING (Maneka Gandhi not explicitly mentioned)")

        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    test_backend()
