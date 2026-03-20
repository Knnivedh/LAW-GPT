import requests
from bs4 import BeautifulSoup
import time
import os
import random
import sys

# Force unbuffered output so we see logs immediately
sys.stdout.reconfigure(encoding='utf-8')

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)

# Headers that mimic a standard browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

def get_soup(url, retries=3):
    for i in range(retries):
        try:
            print(f"[DEBUG] Fetching: {url} (Attempt {i+1})", flush=True)
            time.sleep(random.uniform(2.0, 4.0)) # Polite delay
            
            response = requests.get(url, headers=HEADERS, timeout=20)
            
            if response.status_code == 200:
                print(f"[DEBUG] Success: {url}", flush=True)
                return BeautifulSoup(response.text, 'html.parser')
            elif response.status_code == 429:
                 print("[WARN] Rate limited! Sleeping 60s...", flush=True)
                 time.sleep(60)
            else:
                print(f"[WARN] Status {response.status_code} for {url}", flush=True)
                
        except Exception as e:
            print(f"[ERROR] Exception fetching {url}: {e}", flush=True)
            time.sleep(5)
            
    return None

def crawl(act_name, toc_url, filename):
    print(f"\n============================================", flush=True)
    print(f"STARTING CRAWL: {act_name}", flush=True)
    print(f"Source: {toc_url}", flush=True)
    print(f"============================================", flush=True)
    
    soup = get_soup(toc_url)
    if not soup:
        print("!!! Failed to access TOC. Aborting this act. !!!", flush=True)
        return

    links = []
    # Extract links from TOC
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if href.startswith('/doc/') and 'indiankanoon' not in href:
             full_link = f"https://indiankanoon.org{href}"
             links.append((text, full_link))
    
    # Dedupe preservation of order
    seen = set()
    unique_links = []
    for text, link in links:
        if link not in seen:
            unique_links.append((text, link))
            seen.add(link)
    
    print(f"Found {len(unique_links)} potential sections.", flush=True)
    
    full_text = f"ACT: {act_name}\nSOURCE: {toc_url}\n\n"
    valid_sections = 0
    
    # Iterate through links
    for i, (title, link) in enumerate(unique_links):
        # Skip ToC-like entries if obvious (heuristic)
        if "Complete Act" in title or "Table of Contents" in title: continue
            
        print(f"  Processing [{i+1}/{len(unique_links)}]: {title}", flush=True)
        doc_soup = get_soup(link)
        
        if doc_soup:
            # Updated selectors based on debugging - Indian Kanoon now uses 'akoma-ntoso' class
            content_div = doc_soup.find('div', {'class': 'akoma-ntoso'}) or \
                          doc_soup.find('div', {'class': 'maindoc'}) or \
                          doc_soup.find('div', {'class': 'judgments'}) or \
                          doc_soup.find('div', {'class': 'doc_content'})
            
            if content_div:
                # Remove junk
                for junk in content_div.find_all(['div', 'span'], {'class': ['ad_content', 'doc_options', 'docsource_main']}):
                    junk.decompose()
                
                text = content_div.get_text(separator='\n\n', strip=True)
                
                if len(text) > 50: # Minimal validity check
                    full_text += f"\n\n--- SECTION: {title} ---\n{text}"
                    valid_sections += 1
                    print(f"    -> Extracted {len(text)} chars.", flush=True)
                else:
                    print(f"    -> Skipped (Content too short).", flush=True)
            else:
                print("    -> No content div found.", flush=True)
        
        # Save checkpoints frequently
        if valid_sections % 5 == 0 and valid_sections > 0:
             print("    [Saving Checkpoint]", flush=True)
             with open(os.path.join(STATUTES_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(full_text)
                
    # Final Save
    with open(os.path.join(STATUTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"DONE. Saved {valid_sections} sections to {filename}", flush=True)

def main():
    # 1. Consumer Protection Act 2019
    crawl("Consumer Protection Act 2019", "https://indiankanoon.org/doc/48103131/", "Consumer_Protection_Act_2019.txt")
    
    # 2. Transfer of Property Act 1882
    crawl("Transfer of Property Act 1882", "https://indiankanoon.org/doc/515323/", "Transfer_of_Property_Act_1882.txt")

if __name__ == "__main__":
    main()
