"""Test web search functionality via API"""
import requests
import json
import time

print("=" * 80)
print("Testing Deep Web Search via API")
print("=" * 80)

# Test 1: Simple web search query
print("\n TEST 1: Testing with query 'do you have web access?'")
print("-" * 80)

try:
    response = requests.post(
        'http://localhost:5000/api/query',
        json={
            'question': 'do you have web access?',
            'web_search_mode': True
        },
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nAnswer Length: {len(result.get('answer', ''))}")
        print(f"Number of Sources: {len(result.get('sources', []))}")
        print(f"\nAnswer Preview:")
        print("-" * 80)
        answer = result.get('answer', 'No answer')
        print(answer[:500])
        print("-" * 80)
        
        if result.get('sources'):
            print(f"\nFirst 3 Sources:")
            for i, source in enumerate(result['sources'][:3], 1):
                print(f"{i}. {source.get('title', 'N/A')}")
                print(f"   URL: {source.get('url', 'N/A')[:80]}")
                
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
