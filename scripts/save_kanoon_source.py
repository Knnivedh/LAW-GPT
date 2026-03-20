import requests

url = 'https://indiankanoon.org/doc/1313209/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

try:
    response = requests.get(url, headers=headers, timeout=30)
    with open('kanoon_debug.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"Status: {response.status_code}")
    print(f"Saved to kanoon_debug.html")
except Exception as e:
    print(f"Error: {e}")
