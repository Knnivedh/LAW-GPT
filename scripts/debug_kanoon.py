import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

def debug_section(url):
    print(f"Fetching {url}")
    r = requests.get(url, headers=HEADERS)
    print(f"Status: {r.status_code}")
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Try current selectors
    judgments = soup.find('div', {'class': 'judgments'})
    doc_content = soup.find('div', {'class': 'doc_content'})
    
    print(f"div.judgments found: {bool(judgments)}")
    print(f"div.doc_content found: {bool(doc_content)}")
    
    if not judgments and not doc_content:
        print("Dumping body structure (first 500 chars):")
        if soup.body:
             print(soup.body.prettify()[:1000])
        else:
             print("No body tag found")

# Test with Section 2 of CPA 2019
toc_url = "https://indiankanoon.org/doc/48103131/"
print(f"Fetching TOC: {toc_url}")
r = requests.get(toc_url, headers=HEADERS)
soup = BeautifulSoup(r.text, 'html.parser')
links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('/doc/')]
if links:
    print(f"Found link: {links[5]}") # randomly pick 5th
    debug_section(f"https://indiankanoon.org{links[5]}")
else:
    print("No links found on TOC")
