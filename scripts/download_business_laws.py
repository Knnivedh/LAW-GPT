"""
Download Consumer & Business Laws from Indian Kanoon
Downloads 5 major acts and converts to structured format
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path

# Configuration
OUTPUT_DIR = Path("DATA/Statutes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# Consumer & Business Laws to download
ACTS_TO_DOWNLOAD = [
    {
        'name': 'Companies_Act_2013',
        'url': 'https://indiankanoon.org/doc/1353758/',
        'description': 'Corporate law, company formation, governance'
    },
    {
        'name': 'Partnership_Act_1932',
        'url': 'https://indiankanoon.org/doc/1376129/',
        'description': 'Business partnerships'
    },
    {
        'name': 'Insolvency_and_Bankruptcy_Code_2016',
        'url': 'https://indiankanoon.org/doc/1480029/',
        'description': 'IBC - Insolvency resolution'
    },
    {
        'name': 'Competition_Act_2002',
        'url': 'https://indiankanoon.org/doc/1356587/',
        'description': 'Anti-monopoly, fair competition'
    },
    {
        'name': 'Negotiable_Instruments_Act_1881',
        'url': 'https://indiankanoon.org/doc/1132672/',
        'description': 'Cheques, promissory notes, bills'
    }
]

def get_toc_links(url: str) -> list:
    """Get all section links from the TOC page"""
    try:
        print(f"  [FETCH] Getting TOC: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links to sections
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/doc/' in href and href != url:
                full_url = f"https://indiankanoon.org{href}" if href.startswith('/') else href
                link_text = a.get_text(strip=True)
                if link_text and len(link_text) < 200:
                    links.append({
                        'url': full_url,
                        'title': link_text
                    })
        
        # Remove duplicates
        seen = set()
        unique_links = []
        for link in links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)
        
        print(f"  [OK] Found {len(unique_links)} section links")
        return unique_links
        
    except Exception as e:
        print(f"  [ERROR] Failed to get TOC: {e}")
        return []

def extract_content(url: str) -> str:
    """Extract text content from a section page"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 429:
            print(f"    [WARN] Rate limited, waiting 60s...")
            time.sleep(60)
            response = requests.get(url, headers=HEADERS, timeout=30)
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try different content selectors
        content = None
        selectors = [
            {'class': 'akoma-ntoso'},
            {'class': 'doc_content'},
            {'class': 'judgments'},
            {'id': 'content'}
        ]
        
        for selector in selectors:
            content = soup.find('div', selector)
            if content:
                break
        
        if content:
            # Clean the text
            text = content.get_text(separator='\n', strip=True)
            return text
        else:
            # Fallback: get main body
            body = soup.find('body')
            if body:
                text = body.get_text(separator='\n', strip=True)
                return text[:10000]  # Limit fallback
        
        return ""
        
    except Exception as e:
        return ""

def download_act(act_info: dict) -> bool:
    """Download a complete act"""
    name = act_info['name']
    url = act_info['url']
    output_file = OUTPUT_DIR / f"{name}.txt"
    
    print(f"\n{'='*60}")
    print(f"[ACT] {name.replace('_', ' ')}")
    print(f"{'='*60}")
    
    # Check if already exists
    if output_file.exists() and output_file.stat().st_size > 10000:
        print(f"  [SKIP] Already downloaded ({output_file.stat().st_size:,} bytes)")
        return True
    
    # Get TOC links
    links = get_toc_links(url)
    
    if len(links) < 5:
        print(f"  [WARN] Too few links, trying direct content extraction...")
        content = extract_content(url)
        if len(content) > 5000:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"ACT: {name.replace('_', ' ')}\n")
                f.write(f"SOURCE: {url}\n\n")
                f.write(content)
            print(f"  [SAVED] {output_file.name} ({len(content):,} chars)")
            return True
    
    # Download each section
    all_content = [
        f"ACT: {name.replace('_', ' ')}",
        f"SOURCE: {url}",
        ""
    ]
    
    for i, link in enumerate(links):
        section_url = link['url']
        section_title = link['title']
        
        print(f"  [{i+1}/{len(links)}] {section_title[:50]}...")
        
        content = extract_content(section_url)
        if content:
            all_content.append(f"\n--- SECTION: {section_title} ---")
            all_content.append(content)
        
        # Save checkpoint every 10 sections
        if (i + 1) % 10 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_content))
            print(f"    [Checkpoint saved]")
        
        # Rate limiting
        time.sleep(1)
    
    # Final save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_content))
    
    file_size = output_file.stat().st_size
    print(f"\n  [DONE] {output_file.name} ({file_size:,} bytes)")
    
    return file_size > 1000

def main():
    print("\n" + "="*70)
    print("CONSUMER & BUSINESS LAWS DOWNLOADER")
    print("Downloading 5 major acts from Indian Kanoon")
    print("="*70)
    
    success = 0
    failed = 0
    
    for act in ACTS_TO_DOWNLOAD:
        try:
            if download_act(act):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [ERROR] {act['name']}: {e}")
            failed += 1
        
        # Delay between acts
        time.sleep(3)
    
    print("\n" + "="*70)
    print("DOWNLOAD COMPLETE")
    print("="*70)
    print(f"Successful: {success}")
    print(f"Failed: {failed}")
    print(f"\n[NEXT] Run: python scripts/preprocess_statutes_v2.py")

if __name__ == "__main__":
    main()
