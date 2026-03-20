"""Test NewsAPI with real key"""
import requests
import os

# Set the key
os.environ['NEWSAPI_KEY'] = '27d5439e1c86430fa7190244cd6238fb'

query = "indigo flight cancellations india"
api_key = os.getenv('NEWSAPI_KEY')

print("=" * 80)
print(f"Testing NewsAPI for: {query}")
print(f"API Key: {api_key[:20]}...")
print("=" * 80)

try:
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://newsapi.org/v2/everything?q={encoded_query}&sortBy=publishedAt&language=en&pageSize=5&apiKey={api_key}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"\nStatus: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        
        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            print(f"\n✅ SUCCESS! Found {len(articles)} news articles:\n")
            
            for i, article in enumerate(articles[:5], 1):
                print(f"{i}. {article.get('title', 'No title')}")
                print(f"   Source: {article.get('source', {}).get('name', 'Unknown')}")
                print(f"   Published: {article.get('publishedAt', 'N/A')}")
                print(f"   URL: {article.get('url', '')[:80]}...")
                print()
        else:
            print(f"API Error: {data}")
    else:
        print(f"HTTP Error: {resp.text}")
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
print("NewsAPI Test Complete!")
