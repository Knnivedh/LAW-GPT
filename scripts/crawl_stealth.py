import requests
from bs4 import BeautifulSoup
import time
import os
import random

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)

# Using a very standard, modern User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
}

def get_soup(url):
    try:
        # Long delay to be polite and avoid detection
        sleep_time = random.uniform(5.0, 8.0)
        print(f"Waiting {sleep_time:.2f}s...")
        time.sleep(sleep_time)
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        print(f"Failed to fetch {url}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def crawl(act_name, toc_url, filename):
    print(f"Starting Stealth Crawl for {act_name}...")
    
    soup = get_soup(toc_url)
    if not soup:
        print("Failed to access TOC. Aborting.")
        return

    links = []
    # Indian Kanoon TOC links
    # usually <a href="/doc/12345/">Section X</a>
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if href.startswith('/doc/') and 'indiankanoon' not in href:
             # Just basic filtering
             links.append((text, f"https://indiankanoon.org{href}"))
    
    # Dedupe
    links = list(dict.fromkeys(links))
    print(f"Found {len(links)} links. Processing...")
    
    # Sort or filter logic could go here, but raw order is usually fine on TOC
    
    full_text = f"ACT: {act_name}\nSOURCE: {toc_url}\n\n"
    
    valid_sections = 0
    for i, (title, link) in enumerate(links):
        if "Complete Act" in title or "Table of Contents" in title:
            continue
            
        print(f"  Fetching [{i+1}/{len(links)}]: {title}...")
        doc_soup = get_soup(link)
        
        if doc_soup:
            # Try multiple selectors
            content_div = doc_soup.find('div', {'class': 'judgments'}) or \
                          doc_soup.find('div', {'class': 'doc_content'}) or \
                          doc_soup.find('div', {'id': 'judgement'}) 
            
            if content_div:
                # Remove ads
                for ad in content_div.find_all('div', {'class': 'ad_content'}):
                    ad.decompose()
                
                text = content_div.get_text(separator='\n\n', strip=True)
                full_text += f"\n\n--- SECTION: {title} ---\n{text}"
                valid_sections += 1
            else:
                print("    > No content div found (Selectors failed).")
                # Fallback dump of body text if it's small? No, might be captcha.
        
        # Incremental Save
        if valid_sections % 5 == 0 and valid_sections > 0:
             with open(os.path.join(STATUTES_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(full_text)
                
    # Final Save
    with open(os.path.join(STATUTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"DONE. Saved {valid_sections} sections to {filename}")

def main():
    # 1. Transfer of Property Act 1882
    crawl("Transfer of Property Act 1882", "https://indiankanoon.org/doc/515323/", "Transfer_of_Property_Act_1882.txt")
    
    # 2. Consumer Protection Act 2019
    crawl("Consumer Protection Act 2019", "https://indiankanoon.org/doc/48103131/", "Consumer_Protection_Act_2019.txt")

if __name__ == "__main__":
    main()
