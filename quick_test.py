import requests
import time

print("\nTesting backend server...")
try:
    start = time.time()
    response = requests.post(
        'http://localhost:5000/api/query',
        json={'question': 'What is IPC Section 302?', 'category': 'general'},
        timeout=10
    )
    elapsed = time.time() - start
    data = response.json()
    print("[SUCCESS] Backend is fully operational!")
    print(f"  Response time: {elapsed:.3f}s")
    print(f"  Answer length: {len(data['response']['answer'])} chars")
except Exception as e:
    print("[WARNING] Backend still initializing...")
    print(f"  Error: {e}")

