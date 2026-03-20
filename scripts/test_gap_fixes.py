"""
Test Gap Fixes (Q7 Najeeb & Q9 Dev Dutt)
"""
import requests
import json

API_URL = "http://localhost:7860/api/query"

def test_najeeb():
    query = "An accused is in custody for 4 years under NDPS Act. Trial has not commenced due to forensic delays. Can constitutional bail override statutory restrictions? Discuss Article 21 jurisprudence."
    print("="*60)
    print(f"Testing Q7 (NDPS): {query[:50]}...")
    
    response = requests.post(API_URL, json={"question": query, "category": "Criminal Law"})
    
    if response.status_code == 200:
        ans = response.json().get('answer', '')
        if "Najeeb" in ans or "K.A. Najeeb" in ans:
            print("✅ SUCCESS: Cites K.A. Najeeb")
        else:
            print("❌ FAIL: No citation")
            print(f"Snippet: {ans[:200]}...")
    else:
        print("Error")

def test_dev_dutt():
    query = "A civil servant is compulsorily retired based on confidential reports never communicated to him. Is the action valid? Examine fairness, transparency, and judicial review scope."
    print("="*60)
    print(f"Testing Q9 (Service Law): {query[:50]}...")
    
    response = requests.post(API_URL, json={"question": query, "category": "Service Law"})
    
    if response.status_code == 200:
        ans = response.json().get('answer', '')
        if "Dev Dutt" in ans:
            print("✅ SUCCESS: Cites Dev Dutt")
        else:
            print("❌ FAIL: No citation")
            print(f"Snippet: {ans[:200]}...")
    else:
        print("Error")

if __name__ == "__main__":
    test_najeeb()
    test_dev_dutt()
