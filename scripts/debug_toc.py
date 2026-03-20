import requests
from bs4 import BeautifulSoup

url = 'https://indiankanoon.org/doc/1313209/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/doc/' in href and href != url:
            full_url = f"https://indiankanoon.org{href}" if href.startswith('/') else href
            title = a.get_text(strip=True)
            if title and len(title) < 300:
                links.append({'url': full_url, 'title': title})
    
    print(f"Found {len(links)} links")
    for l in links[:10]:
        print(f"  {l['title']}: {l['url']}")
        
except Exception as e:
    print(f"Error: {e}")
