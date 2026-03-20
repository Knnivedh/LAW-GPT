import requests
import json

url = "http://localhost:5000/api/query"
payload = {"question": """You are a legal assistant answering under Indian consumer law.

A person purchased 10 laptops in his own name from an online marketplace for ₹7,50,000.
The laptops were later used in his small IT training institute.
Two laptops stopped working after 3 months.
The seller refused refund and offered only paid repair. [Unique ID: 888]

Answer the following:

1. Is the buyer a “consumer” under Indian law?
2. What legal remedy is available to him?
3. Which Consumer Commission should he approach?
4. Under which Consumer Protection Act should the complaint be filed?
5. Is the complaint still maintainable if the buyer files it after 2 years and 6 months?
6. What reliefs can the Consumer Commission grant in this case?"""}
try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        answer = data.get("response", {}).get("answer", "No answer found")
        print("\n=== RESPONSE ANSWER ===")
        print(answer)
        print("\n=======================")
        
        # Write to file for full inspection
        with open("debug_response.txt", "w", encoding="utf-8") as f:
            f.write(answer)
        print("Response written to debug_response.txt")
        
        # Validation Check
        if "✅ STANDARD LEGAL CHATBOT ANSWER FORMAT" in answer and "⚠️ 9. Disclaimer" in answer:
            print("\n✅ PASSED: Standard Format Detected")
        else:
            print("\n❌ FAILED: Standard Format NOT Detected")
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
