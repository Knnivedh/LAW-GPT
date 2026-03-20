import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

# Test URL - a specific section from CPA 2019
test_url = "https://indiankanoon.org/doc/63599642/"

print(f"Fetching: {test_url}")
response = requests.get(test_url, headers=HEADERS, timeout=20)
print(f"Status: {response.status_code}")
print(f"Content Length: {len(response.text)}")

soup = BeautifulSoup(response.text, 'html.parser')

# Check for the divs we're looking for
print("\n=== Checking for known selectors ===")
print(f"div.judgments: {bool(soup.find('div', {'class': 'judgments'}))}")
print(f"div.doc_content: {bool(soup.find('div', {'class': 'doc_content'}))}")
print(f"div#judgement: {bool(soup.find('div', {'id': 'judgement'}))}")

# List all divs with classes
print("\n=== All DIVs with classes ===")
for div in soup.find_all('div', class_=True)[:20]:  # First 20
    classes = ' '.join(div.get('class', []))
    print(f"  <div class='{classes}'>")

# List all divs with IDs
print("\n=== All DIVs with IDs ===")
for div in soup.find_all('div', id=True)[:20]:
    print(f"  <div id='{div.get('id')}'>")

# Save full HTML for manual inspection
with open("DATA/Statutes/debug_page.html", 'w', encoding='utf-8') as f:
    f.write(response.text)
print("\n=== Saved full HTML to DATA/Statutes/debug_page.html ===")
