"""
Critical Consumer Law Acts Downloader
Downloads all missing acts needed for pro-level consumer law expertise
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from pathlib import Path

OUTPUT_DIR = Path("DATA/Statutes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# Critical Consumer Law Acts
CONSUMER_LAW_ACTS = [
    {
        'name': 'Indian_Contract_Act_1872',
        'url': 'https://indiankanoon.org/doc/1313209/',
        'priority': 'CRITICAL',
        'description': 'Foundation of all consumer contracts and disputes'
    },
    {
        'name': 'Sale_of_Goods_Act_1930',
        'url': 'https://indiankanoon.org/doc/1153646/',
        'priority': 'CRITICAL',
        'description': 'Product purchases, warranties, defects'
    },
    {
        'name': 'Specific_Relief_Act_1963',
        'url': 'https://indiankanoon.org/doc/1938925/',
        'priority': 'HIGH',
        'description': 'Remedies, compensation, injunctions'
    },
    {
        'name': 'Competition_Act_2002',
        'url': 'https://indiankanoon.org/doc/1356587/',
        'priority': 'HIGH',
        'description': 'Unfair trade practices, anti-competitive behavior'
    },
    {
        'name': 'Negotiable_Instruments_Act_1881',
        'url': 'https://indiankanoon.org/doc/1132672/',
        'priority': 'HIGH',
        'description': 'Cheque bounce cases (very common)'
    },
    {
        'name': 'Consumer_Protection_E-Commerce_Rules_2020',
        'url': 'https://indiankanoon.org/doc/37327206/',
        'priority': 'MEDIUM',
        'description': 'Online shopping, e-commerce consumer protection'
    }
]

def get_toc_links(url: str) -> list:
    """Get all section links from TOC"""
    try:
        print(f"  [FETCH] Getting TOC...")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/doc/' in href and href != url:
                full_url = f"https://indiankanoon.org{href}" if href.startswith('/') else href
                link_text = a.get_text(strip=True)
                if link_text and len(link_text) < 200:
                    links.append({'url': full_url, 'title': link_text})
        
        # Remove duplicates
        seen = set()
        unique = []
        for link in links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique.append(link)
        
        print(f"  [OK] Found {len(unique)} section links")
        return unique
    except Exception as e:
        print(f"  [ERROR] Failed: {e}")
        return []

def extract_content(url: str) -> str:
    """Extract content from page"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 429:
            print(f"    [WAIT] Rate limited, sleeping 60s...")
            time.sleep(60)
            response = requests.get(url, headers=HEADERS, timeout=30)
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try selectors
        for selector in [{'class': 'akoma-ntoso'}, {'class': 'doc_content'}, {'id': 'content'}]:
            content = soup.find('div', selector)
            if content:
                return content.get_text(separator='\n', strip=True)
        
        # Fallback
        body = soup.find('body')
        return body.get_text(separator='\n', strip=True)[:10000] if body else ""
    except:
        return ""

def download_act(act_info: dict) -> bool:
    """Download a complete act"""
    name = act_info['name']
    url = act_info['url']
    priority = act_info['priority']
    output_file = OUTPUT_DIR / f"{name}.txt"
    
    print(f"\n{'='*60}")
    print(f"[{priority}] {name.replace('_', ' ')}")
    print(f"{'='*60}")
    
    # Check if exists
    if output_file.exists() and output_file.stat().st_size > 10000:
        print(f"  [SKIP] Already downloaded ({output_file.stat().st_size:,} bytes)")
        return True
    
    # Get TOC
    links = get_toc_links(url)
    
    if len(links) < 5:
        print(f"  [WARN] Few links, trying direct extraction...")
        content = extract_content(url)
        if len(content) > 5000:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"ACT: {name.replace('_', ' ')}\n")
                f.write(f"SOURCE: {url}\n\n")
                f.write(content)
            print(f"  [SAVED] {output_file.name} ({len(content):,} chars)")
            return True
    
    # Download sections
    all_content = [
        f"ACT: {name.replace('_', ' ')}",
        f"SOURCE: {url}",
        ""
    ]
    
    for i, link in enumerate(links):
        print(f"  [{i+1}/{len(links)}] {link['title'][:50]}...")
        
        content = extract_content(link['url'])
        if content:
            all_content.append(f"\n--- SECTION: {link['title']} ---")
            all_content.append(content)
        
        # Checkpoint
        if (i + 1) % 10 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_content))
            print(f"    [Checkpoint]")
        
        time.sleep(1)
    
    # Final save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_content))
    
    size = output_file.stat().st_size
    print(f"\n  [DONE] {output_file.name} ({size:,} bytes)")
    return size > 1000

def main():
    print("\n" + "="*70)
    print("CRITICAL CONSUMER LAW ACTS DOWNLOADER")
    print("Downloading 6 acts for pro-level consumer law expertise")
    print("="*70)
    
    success = 0
    failed = 0
    
    for act in CONSUMER_LAW_ACTS:
        try:
            if download_act(act):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [ERROR] {act['name']}: {e}")
            failed += 1
        
        time.sleep(3)
    
    print("\n" + "="*70)
    print("DOWNLOAD COMPLETE")
    print("="*70)
    print(f"Successful: {success}")
    print(f"Failed:     {failed}")
    print(f"\n[NEXT] Run: python scripts/preprocess_statutes_v2.py")
    print(f"[THEN] Run: python scripts/fix_all_statutes.py")

if __name__ == "__main__":
    main()
