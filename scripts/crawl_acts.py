import requests
from bs4 import BeautifulSoup
import time
import os
import random

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def get_soup(url):
    try:
        time.sleep(random.uniform(1.5, 3.0)) # Be polite
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        print(f"Failed to fetch {url}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def crawl_indian_kanoon_act(act_name, toc_url, output_filename):
    print(f"Crawling {act_name} from {toc_url}...")
    
    soup = get_soup(toc_url)
    if not soup:
        return

    # Find all section links
    # Usually in div.docsource_content or just flat list of links
    # We look for links starting with /doc/ and having text that looks like "Section X" or number.
    # Actually, Indian Kanoon TOC lists sections cleanly.
    
    links = []
    # Try multiple selectors for links
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if href.startswith('/doc/') and len(href) > 6:
             # Basic filter: must be a doc link.
             # On TOC page, usually these are the sections.
             full_link = f"https://indiankanoon.org{href}"
             links.append((text, full_link))
    
    # Remove duplicates
    links = list(dict.fromkeys(links))
    print(f"Found {len(links)} potential section links.")

    file_path = os.path.join(STATUTES_DIR, output_filename)
    full_text = f"ACT: {act_name}\nSOURCE: {toc_url}\n\n"
    
    count = 0
    for title, link in links:
        # Filter out "Entire Act" link itself if present (recursion)
        if "Entire Act" in title or toc_url in link:
            continue
            
        print(f"  Fetching: {title[:50]}...")
        doc_soup = get_soup(link)
        if doc_soup:
            # Extract content
            # Try div.judgments first
            content_div = doc_soup.find('div', {'class': 'judgments'})
            if not content_div:
                content_div = doc_soup.find('div', {'class': 'doc_content'})
            
            if content_div:
                # Remove fluff
                for ads in content_div.find_all('div', {'class': 'ad_content'}):
                    ads.decompose()
                
                text = content_div.get_text(separator='\n', strip=True)
                full_text += f"\n\n--- SECTION: {title} ---\n{text}"
                count += 1
            else:
                print("    No content div found.")
        
        # Safety limit for demo/speed? No, user said "make it".
        # But 100+ requests might take 5 mins.
        if count % 10 == 0:
            print(f"    Progress: {count} sections downloaded.")
            # Incremental save to show progress
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_text)

    # Final Save
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"Saved {act_name} to {file_path} ({len(full_text)} chars)")

def main():
    acts = [
        # Consumer Protection Act 2019
        ("Consumer Protection Act 2019", "https://indiankanoon.org/doc/48103131/", "Consumer_Protection_Act_2019.txt"),
        
        # Transfer of Property Act 1882
        ("Transfer of Property Act 1882", "https://indiankanoon.org/doc/515323/", "Transfer_of_Property_Act_1882.txt"),
    ]
    
    for name, url, file in acts:
        crawl_indian_kanoon_act(name, url, file)

    print("Done crawling.")

if __name__ == "__main__":
    main()
