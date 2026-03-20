import requests
from bs4 import BeautifulSoup
import re
import os
import time

STATUTES_DIR = "DATA/Statutes"
os.makedirs(STATUTES_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def search_and_download(act_name, filename):
    print(f"Searching for: {act_name}...")
    
    # 1. Search Indian Kanoon
    search_url = f"https://indiankanoon.org/search?formInput={act_name}+doctypes:acts"
    try:
        response = requests.get(search_url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Failed to search {act_name}: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find first result link (usually in <div class="result_title">...<a href="/doc/ID/">)
        # result_title might be different, let's look for links starting with /doc/
        
        doc_link = None
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/doc/') and 'indiankanoon' not in href: # pure /doc/1234/
                # Check if title matches reasonably well?
                # Just take the first /doc/ result that isn't a fragment
                doc_link = f"https://indiankanoon.org{href}"
                print(f"Found document link: {doc_link}")
                break
        
        if not doc_link:
            print(f"No document found for {act_name}")
            return

        # 2. Download Content
        print(f"Downloading content from {doc_link}...")
        doc_response = requests.get(doc_link, headers=HEADERS)
        if doc_response.status_code != 200:
            print(f"Failed to fetch document: {doc_response.status_code}")
            return
            
        doc_soup = BeautifulSoup(doc_response.text, 'html.parser')
        
        # Extract meaningful text (usually in <div class="judgments"> or similar, but for Acts it might be different)
        # Indian Kanoon acts often have text directly or in a specific div.
        # Let's get the whole text of the relevant container.
        
        content_div = doc_soup.find('div', {'class': 'judgments'}) or doc_soup.find('div', {'class': 'doc_content'})
        
        if content_div:
            text = content_div.get_text(separator='\n\n')
        else:
            # Fallback: get text from body but remove scripts/styles
            print("Warning: Specific content div not found, extracting from body...")
            text = doc_soup.body.get_text(separator='\n\n')

        # Clean up text (remove excessive newlines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Save
        file_path = os.path.join(STATUTES_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"Saved {act_name} to {file_path} ({len(text)} chars)")
        
    except Exception as e:
        print(f"Error processing {act_name}: {e}")

def main():
    acts = [
        ("Consumer Protection Act 2019", "Consumer_Protection_Act_2019.txt"),
        ("Transfer of Property Act 1882", "Transfer_of_Property_Act_1882.txt"),
        ("Bharatiya Nyaya Sanhita 2023", "Bharatiya_Nyaya_Sanhita_2023.txt")
    ]
    
    for act, filename in acts:
        search_and_download(act, filename)
        time.sleep(2) # Be polite

if __name__ == "__main__":
    main()
