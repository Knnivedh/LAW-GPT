"""Test Google News RSS and NewsAPI"""
import requests
import xml.etree.ElementTree as ET
import urllib.parse

query = "indigo flight cancellations"
encoded_query = urllib.parse.quote(query)

print("=" * 80)
print(f"Testing Google News RSS for: {query}")
print("=" * 80)

# Test Google News RSS
try:
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"\nStatus: {resp.status_code}")
    
    if resp.status_code == 200:
        root = ET.fromstring(resp.content)
        
        results = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            
            if title is not None:
                results.append({
                    'title': title.text,
                    'url': link.text if link is not None else '',
                    'published': pub_date.text if pub_date is not None else ''
                })
        
        print(f"\n✅ Found {len(results)} Google News results:\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title']}")
            print(f"   Published: {r['published']}")
            print(f"   URL: {r['url'][:80]}...")
            print()
    else:
        print(f"Error: {resp.status_code}")
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)
print("Test completed!")
