import requests
import json
import time

# COMPLEX SCENARIO: Intersection of IBC, Consumer Law, and Supreme Court Precedents
SCENARIO = {
    "category": "Real Estate & Insolvency (Complex)",
    "query": """I am a homebuyer who booked a luxury apartment in Noida in 2019. The possession was due in 2022 but is delayed. 
    The builder is now undergoing Corporate Insolvency Resolution Process (CIRP) initiated by a bank under Section 7 of IBC. 
    I want to withdraw from the project and claim a full refund with 18% interest.
    
    1. Can I still file a consumer complaint in NCDRC for refund now that CIRP has started, or does the Moratorium bar it?
    2. What is my exact status as a homebuyer under IBC 2016 following the 'Pioneer Urban Land' judgment - am I a financial creditor or operational creditor?
    3. If the liquidation happens, where do I stand in the priority of distribution (waterfall mechanism)?"""
}

def evaluate_system():
    print(f"\n[EVALUATION START] Testing Complex Scenario...")
    print(f"Query: {SCENARIO['query']}\n")
    
    payload = {
        "question": SCENARIO['query'],
        "session_id": "eval_session_1",
        "web_search_mode": False  # Force it to use internal Knowledge Base
    }
    
    try:
        start_time = time.time()
        # Ensure server is running on localhost:5000
        response = requests.post("http://localhost:5000/api/query", json=payload)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json().get('response', {})
            
            print("="*80)
            print(f"RAG ANSWER (Time: {duration:.2f}s)")
            print("="*80)
            print(data.get('answer', 'NO ANSWER'))
            
            print("\n" + "="*80)
            print("REASONING TRACE")
            print("="*80)
            reasoning = data.get('reasoning_analysis', {}).get('trace', 'No trace')
            print(reasoning)
            
            print("\n" + "="*80)
            print("SOURCES CITED")
            print("="*80)
            for idx, source in enumerate(data.get('sources', [])):
                meta = source.get('metadata', {})
                content = source.get('page_content', 'No content')[:300].replace('\n', ' ')
                print(f"[{idx+1}] {meta.get('source', 'Unknown')} | {meta.get('act_name', '')} {meta.get('section', '')}")
                print(f"    Context: {content}...")
                print("-" * 40)
                
            # Save full output for my analysis
            with open("evaluation_output.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        else:
            print(f"Request Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error connecting to server: {e}")
        print("Make sure 'kaanoon_test/advanced_rag_api_server.py' is running!")

if __name__ == "__main__":
    evaluate_system()
