import requests
from bs4 import BeautifulSoup

def debug_links(url):
    print(f"Fetch: {url}")
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        print(f"LINK: {a['href']} | TEXT: {a.get_text(strip=True)[:20]}")

print("--- TPA ---")
debug_links("https://devgan.in/all_sections_tpa.php")
print("\n--- CPA ---")
debug_links("https://devgan.in/all_sections_cpa.php")
