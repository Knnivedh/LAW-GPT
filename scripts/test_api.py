import requests
import json

def test_backend():
    base_url = "http://localhost:5000"
    
    # Test Health
    try:
        health = requests.get(f"{base_url}/api/health")
        print(f"Health Status: {health.status_code}")
        print(health.json())
    except Exception as e:
        print(f"Health check failed: {e}")

    # Test Query
    try:
        payload = {
            "question": "What is Section 302 of IPC?",
            "stream": False
        }
        response = requests.post(f"{base_url}/api/query", json=payload)
        print(f"\nQuery Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            answer = result.get('response', {}).get('answer', 'No answer')
            print(f"Answer: {answer[:200]}...")
        else:
            print(response.text)
    except Exception as e:
        print(f"Query test failed: {e}")

if __name__ == "__main__":
    test_backend()
