"""Direct test of Wikipedia search"""
import requests

query = "artificial intelligence 2024"
encoded_query = query.replace(' ', '%20')

# Wikipedia Search API
search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={encoded_query}&limit=5&format=json"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Testing Wikipedia search for: {query}")
print(f"URL: {search_url}")
print("-" * 80)

try:
    resp = requests.get(search_url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nResponse structure: {len(data)} elements")
        
        if len(data) >= 4:
            titles = data[1]
            descriptions = data[2]
            urls = data[3]
            
            print(f"\nFound {len(titles)} results:")
            for i in range(len(titles)):
                print(f"\n{i+1}. {titles[i]}")
                print(f"   URL: {urls[i]}")
                print(f"   Description: {descriptions[i] if i < len(descriptions) else 'N/A'}")
    else:
        print(f"Error: {resp.text}")
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test completed!")
