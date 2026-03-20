import requests
from bs4 import BeautifulSoup
import time
import os
import random

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)
FILENAME = "Bharatiya_Nyaya_Sanhita_2023.txt"

# Devgan.in is friendly but let's be polite
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

def get_soup(url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        print(f"Failed to fetch {url}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def crawl_bns():
    print("Crawling Bharatiya Nyaya Sanhita 2023 from devgan.in...")
    
    # 1. Get List
    soup = get_soup("https://devgan.in/all_sections_bns.php")
    if not soup:
        return

    links = []
    # Links are usually <a href="bns/section/1.php">Section 1...</a>
    # Or relational paths.
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if "section" in href and "bns" in href:
             # href might be "bns/section/1.php" or "section/1.php" depending on page
             if href.startswith("bns/"):
                 full_link = f"https://devgan.in/{href}"
             elif href.startswith("/bns/"):
                 full_link = f"https://devgan.in{href}"
             else:
                 full_link = f"https://devgan.in/bns/{href}" # Best guess for relative
             
             links.append((text, full_link))
    
    # Dedupe
    links = list(dict.fromkeys(links))
    print(f"Found {len(links)} section links.")
    
    full_text = "ACT: Bharatiya Nyaya Sanhita 2023 (BNS)\nSOURCE: devgan.in\n\n"
    
    for i, (title, link) in enumerate(links):
        print(f"  Fetching [{i+1}/{len(links)}]: {title}...")
        doc_soup = get_soup(link)
        if doc_soup:
            # Content is usually in div#content or just body
            # devgan.in usually has a main container
            # Look for header and then text
            
            # Heuristic: Find h2 (Section title) and get subsequent p tags
            # Or just get the whole text of the main container
            content_div = doc_soup.find('div', {'id': 'content'}) # Common id
            if not content_div:
                 content_div = doc_soup.find('article')
            
            if content_div:
                text = content_div.get_text(separator='\n', strip=True)
                # Clean up Nav links
                text = text.replace("Home", "").replace("Prev", "").replace("Next", "")
                full_text += f"\n\n--- {title} ---\n{text}"
            else:
                 # Fallback to body
                 text = doc_soup.get_text(separator='\n', strip=True)
                 full_text += f"\n\n--- {title} ---\n{text}"
        
        if i % 20 == 0:
             # Save intermediate
             with open(os.path.join(STATUTES_DIR, FILENAME), 'w', encoding='utf-8') as f:
                f.write(full_text)

    # Final Save
    file_path = os.path.join(STATUTES_DIR, FILENAME)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"Saved BNS 2023 to {file_path}")

if __name__ == "__main__":
    crawl_bns()
