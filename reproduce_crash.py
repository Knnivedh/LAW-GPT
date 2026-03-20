
import requests
import json
import sys

# Configure logging to stdout
# logging.basicConfig(level=logging.INFO)

print("Running Retrieval Debugger...")
url = "http://localhost:7860/api/query"

test_queries = [
    "Hadiya case marriage autonomy parens patriae",
    "Vidya Devi v State of Himachal Pradesh adverse possession",
    "Alchemist Asset Reconstruction Section 14 IBC"
]

for q in test_queries:
    print(f"\nScanning for: {q}")
    payload = {"question": q}
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        # Extract sources
        sources = data.get('sources', [])
        print(f"Found {len(sources)} sources.")
        for i, s in enumerate(sources[:3]):
             print(f"  [{i+1}] {s.get('case_name', 'No Title')} ({s.get('score', 0)})")
             
        # Check if key terms appear in answer
        answer = data.get('answer', '')
        print(f"Answer snippet: {answer[:100]}...")
        
    except Exception as e:
        print(f"Request failed: {e}")

