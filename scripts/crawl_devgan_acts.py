import requests
from bs4 import BeautifulSoup
import time
import os
import random

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

def get_soup(url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser'), response.url
        print(f"Failed to fetch {url}: Status {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None, None

def crawl_act(act_name, list_url, filename, code_slug):
    print(f"==================================================")
    print(f"Crawling {act_name}")
    print(f"Source: {list_url}")
    print(f"==================================================")
    
    soup, final_url = get_soup(list_url)
    if not soup:
        print(f"Skipping {act_name} due to connection error.")
        return

    links = []
    # Identify links. 
    # TPA links: href="tpa/section/1.php"
    # CPA links: href="cpa/section/1.php"
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        
        # Filter for section links
        if "section" in href and code_slug in href:
            full_link = href
            if not href.startswith("http"):
                 # Handle relative paths carefully
                 # if href is "tpa/section/1.php" and we are at "devgan.in/all_sections_tpa.php", base is "devgan.in"
                 if href.startswith("/"):
                     full_link = f"https://devgan.in{href}"
                 elif href.startswith(code_slug):
                     full_link = f"https://devgan.in/{href}"
                 else:
                     # sometimes "section/1.php" if we are in a subdir? 
                     # But all_sections pages are usually at root.
                     # Let's assume devgan.in root relative if it contains the slug
                     full_link = f"https://devgan.in/{href}"
            
            links.append((text, full_link))
    
    # Dedupe
    links = list(dict.fromkeys(links))
    print(f"Found {len(links)} section links for {act_name}.")
    
    if not links:
        print(f"WARNING: No links found for {act_name} with slug '{code_slug}'. Check logic.")
        return

    full_text = f"ACT: {act_name}\nSOURCE: {list_url}\n\n"
    
    for i, (title, link) in enumerate(links):
        print(f"  Fetching [{i+1}/{len(links)}]: {title}...")
        doc_soup, _ = get_soup(link)
        if doc_soup:
            content_div = doc_soup.find('div', {'id': 'content'}) 
            if not content_div:
                 content_div = doc_soup.find('article')
            
            if content_div:
                text = content_div.get_text(separator='\n', strip=True)
                # Cleanup common footer/nav noise
                text = text.replace("Home", "").replace("Prev", "").replace("Next", "")
                text = text.replace("A Lawyers Reference", "")
                full_text += f"\n\n--- {title} ---\n{text}"
            else:
                 text = doc_soup.get_text(separator='\n', strip=True)
                 full_text += f"\n\n--- {title} ---\n{text}"
        
        # Save every 20 sections
        if i % 20 == 0:
             with open(os.path.join(STATUTES_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(full_text)

    # Final Save
    file_path = os.path.join(STATUTES_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"SUCCESS: Saved {act_name} to {file_path}")


def main():
    # 1. Transfer of Property Act 1882
    crawl_act(
        act_name="Transfer of Property Act 1882",
        list_url="https://devgan.in/all_sections_tpa.php",
        filename="Transfer_of_Property_Act_1882.txt",
        code_slug="tpa"
    )
    
    # 2. Consumer Protection Act 2019
    # Note: trying 'cpa' slug.
    crawl_act(
        act_name="Consumer Protection Act 2019",
        list_url="https://devgan.in/all_sections_cpa.php",
        filename="Consumer_Protection_Act_2019.txt",
        code_slug="cpa"
    )

if __name__ == "__main__":
    main()
