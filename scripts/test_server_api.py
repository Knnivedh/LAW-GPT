import requests
import json
import time

SCENARIOS = [
    {
        "id": "SCENARIO_1",
        "category": "Consumer Protection",
        "query": "I bought a premium laptop worth Rs. 1.2 Lakh from an e-commerce site. It has a motherboard defect, and the seller refuses to replace it. Where should I file my complaint, and can I hold the e-commerce platform jointly liable under the 2019 Act?"
    },
    {
        "id": "SCENARIO_3",
        "category": "Insolvency (IBC)",
        "query": "An operational creditor has not been paid a debt of Rs. 1.5 Crore for 6 months. What is the procedure to initiate CIRP under the IBC 2016, and what are the recent Supreme Court views on the maintainability of such petitions?"
    },
    {
        "id": "SCENARIO_5",
        "category": "Property Law / RERA",
        "query": "A builder has delayed possession of a flat by 2 years. Can the buyer approach both the Real Estate Regulatory Authority (RERA) and the Consumer Court simultaneously, or is one forum's jurisdiction barred by the other?"
    }
]

def test_api():
    print("Waiting for server to start...")
    # Polling for health
    for _ in range(30):
        try:
            r = requests.get("http://localhost:5000/health")
            if r.status_code == 200:
                print("Server is UP!")
                break
        except:
            time.sleep(2)
    else:
        print("Server failed to start.")
        return

    for scenario in SCENARIOS:
        print(f"\n[TEST] {scenario['category']}")
        print(f"Query: {scenario['query']}")
        
        payload = {
            "question": scenario['query'],
            "session_id": "test_session_1",
            "web_search_mode": False
        }
        
        try:
            start_time = time.time()
            response = requests.post("http://localhost:5000/api/query", json=payload)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                answer = data['response']['answer']
                sources = len(data['response']['sources'])
                trace = data['response']['reasoning_analysis']['trace']
                
                print(f"Status: {response.status_code} | Time: {duration:.2f}s")
                print(f"Answer: {answer[:100]}...")
                print(f"Sources: {sources}")
                print(f"Reasoning: {trace[:50]}...")
            else:
                print(f"FAILED: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_api()
