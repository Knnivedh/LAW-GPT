"""
Test Q4 Hadiya Case Only
"""
import requests
import json
import time

API_URL = "http://localhost:7860/api/query"

def test_hadiya():
    query = "A 24-year-old woman converts religion and marries by choice. Her parents file a writ claiming 'psychological coercion' and seek custody. What will the court prioritize? Discuss personal liberty, consent, and parental rights."
    
    print(f"Sending query: {query[:50]}...")
    
    response = requests.post(API_URL, json={"question": query, "category": "Family Law"})
    
    if response.status_code == 200:
        ans = response.json().get('answer', '')
        print("\nANSWER:")
        print(ans)
        
        if "Hadiya" in ans or "Shafin" in ans:
            print("\n✅ SUCCESS: Cites Hadiya Case")
        else:
            print("\n❌ FAIL: Does NOT cite Hadiya Case")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_hadiya()
