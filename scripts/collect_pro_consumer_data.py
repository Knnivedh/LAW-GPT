"""
Pro-Level Consumer Law Data Collector FINAL
Downloads high-quality act text and NCDRC case law.
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import random
from pathlib import Path

OUTPUT_DIR = Path("DATA/Statutes")
CASE_LAW_DIR = Path("DATA/CaseLaw/Consumer")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CASE_LAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

ACTS = [
    {'name': 'Indian_Contract_Act_1872', 'url': 'https://indiankanoon.org/doc/171398/'},
    {'name': 'Sale_of_Goods_Act_1930', 'url': 'https://indiankanoon.org/doc/651105/'},
    {'name': 'Specific_Relief_Act_1963', 'url': 'https://indiankanoon.org/doc/1671917/'},
    {'name': 'Indian_Partnership_Act_1932', 'url': 'https://indiankanoon.org/doc/1073410/'},
    {'name': 'Competition_Act_2002', 'url': 'https://indiankanoon.org/doc/1356587/'},
    {'name': 'Negotiable_Instruments_Act_1881', 'url': 'https://indiankanoon.org/doc/1132672/'},
    {'name': 'Consumer_Protection_E-Commerce_Rules_2020', 'url': 'https://indiankanoon.org/doc/37327206/'},
]

def get_with_retry(url, delay=5):
    try:
        time.sleep(random.uniform(2, 4))
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            print(f"    [429] Waiting {delay*2}s...")
            time.sleep(delay*2)
            resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"    [ERR] {url}: {e}")
        return None

def extract_clean_text(soup):
    for selector in [{'class': 'akoma-ntoso'}, {'class': 'doc_content'}, {'id': 'content'}]:
        cont = soup.find('div', selector)
        if cont: return cont.get_text(separator='\n', strip=True)
    return soup.get_text(separator='\n', strip=True)

def download_act_full(act):
    name = act['name']
    url = act['url']
    path = OUTPUT_DIR / f"{name}.txt"
    
    # Try the "Entire Act" view if possible
    print(f"\n[ACT] {name}")
    
    # If file exists and is >50KB, skip (except for small ones like E-Commerce)
    if path.exists() and path.stat().st_size > 50000:
        print(f"  [SKIP] Already exists ({path.stat().st_size} bytes)")
        return
        
    resp = get_with_retry(url)
    if not resp: return
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Look for "Entire Act" link
    entire_link = None
    for a in soup.find_all('a', href=True):
        if 'Entire Act' in a.get_text():
            entire_link = f"https://indiankanoon.org{a['href']}"
            break
            
    if entire_link:
        print(f"  [FETCH] Entire Act: {entire_link}")
        resp = get_with_retry(entire_link)
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
    text = extract_clean_text(soup)
    if len(text) > 1000:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"ACT: {name}\nSOURCE: {url}\n\n{text}")
        print(f"  [OK] Saved {len(text)} chars")
    else:
        print(f"  [ERR] Text too short ({len(text)})")

def collect_cases(limit=30):
    print(f"\n[CASES] NCDRC Search")
    # Refined search query
    search_url = "https://indiankanoon.org/search/?formInput=consumer+complaint+doctypes%3Ancdrc"
    count = 0
    page = 0
    while count < limit:
        print(f"  [PAGE] Fetching page {page}...")
        paged_url = f"{search_url}&pagenum={page}"
        resp = get_with_retry(paged_url)
        if not resp: break
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        titles = soup.find_all('h4', class_='result_title')
        
        if not titles:
            print("  [INFO] No more results found.")
            break
            
        print(f"  Found {len(titles)} cases on page {page}")
        
        for title_tag in titles:
            if count >= limit: break
            
            a = title_tag.find('a', href=True)
            if not a: continue
            
            case_url = f"https://indiankanoon.org{a['href']}"
            case_title = a.get_text(strip=True)
            safe_name = re.sub(r'\W+', '_', case_title)[:60]
            cpath = CASE_LAW_DIR / f"{safe_name}.txt"
            
            if cpath.exists():
                count += 1
                continue
                
            print(f"  [{count+1}] Case: {case_title[:50]}")
            cresp = get_with_retry(case_url)
            if cresp:
                csoup = BeautifulSoup(cresp.text, 'html.parser')
                ctext = extract_clean_text(csoup)
                with open(cpath, 'w', encoding='utf-8') as f:
                    f.write(f"CASE: {case_title}\nURL: {case_url}\n\n{ctext}")
                count += 1
            time.sleep(2)
        
        page += 1
        time.sleep(2)

def main():
    # for act in ACTS:
    #     download_act_full(act)
    collect_cases(limit=100)
    print("\nDONE")

if __name__ == "__main__":
    main()
