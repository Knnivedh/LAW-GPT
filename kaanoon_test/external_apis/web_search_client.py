
import requests
import re
import time
import os
import sys
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

# Try to import Config, handling path issues
try:
    from config.config import Config
except ImportError:
    # If running as script or from subfolder, add root to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    try:
        from config.config import Config
    except ImportError:
        print("[WARNING] Could not import Config. API keys may not be loaded.")
        Config = None

class WebSearchClient:
    """
    Advanced Web Search Client supporting multiple providers:
    1. Brave Search API (High quality, Free tier available)
    2. Serper.dev API (Google results, Free tier available)
    3. DuckDuckGo (Free, no key required)
    4. Fallback Scraper (Last resort)
    """
    
    def __init__(self):
        self.providers = []
        self._init_providers()
        
    def _init_providers(self):
        """Initialize providers based on available keys."""
        # 1. Brave Search (Priority 1)
        if Config and Config.BRAVE_API_KEY:
            self.providers.append({
                "name": "Brave Search",
                "func": self._search_brave,
                "limit": 10
            })
            print("[INFO] WebSearch: Brave Search enabled.")
            
        # 2. Serper.dev (Priority 2)
        if Config and Config.SERPER_API_KEY:
            self.providers.append({
                "name": "Serper.dev",
                "func": self._search_serper,
                "limit": 10
            })
            print("[INFO] WebSearch: Serper.dev enabled.")
            
        # 3. DuckDuckGo (Priority 3 - Always available)
        try:
            # v8.x uses duckduckgo_search.DDGS, older versions used ddgs.DDGS
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                from ddgs import DDGS  # Fallback for older versions
            self.ddgs = DDGS()
            self.providers.append({
                "name": "DuckDuckGo",
                "func": self._search_ddgs,
                "limit": 5
            })
            print("[INFO] WebSearch: DuckDuckGo enabled.")
        except ImportError as e:
            print(f"[WARNING] WebSearch: duckduckgo-search not installed. ({e})")
            
        # 4. Fallback Scraper (Priority 4)
        self.providers.append({
            "name": "Fallback Scraper",
            "func": self._search_fallback,
            "limit": 3
        })

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform search using the best available provider.
        Iterates through providers until one succeeds.
        """
        for provider in self.providers:
            try:
                # print(f"[DEBUG] Trying provider: {provider['name']}")
                results = provider["func"](query, min(max_results, provider["limit"]))
                if results:
                    # print(f"[INFO] Search successful with {provider['name']}")
                    return results
            except Exception as e:
                print(f"[WARNING] Provider {provider['name']} failed: {e}")
                continue
                
        print("[ERROR] All search providers failed.")
        return []

    def _search_brave(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using Brave Search API."""
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": Config.BRAVE_API_KEY
        }
        params = {"q": query, "count": max_results}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Brave API returned {response.status_code}")
            
        data = response.json()
        results = []
        
        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": "Brave Search"
                })
        return results

    def _search_serper(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using Serper.dev API (Google results)."""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": Config.SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": max_results}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Serper API returned {response.status_code}")
            
        data = response.json()
        results = []
        
        if "organic" in data:
            for item in data["organic"]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "Serper.dev (Google)"
                })
        return results

    def _search_ddgs(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using duckduckgo-search library."""
        results = []
        # DDGS text search
        ddgs_gen = self.ddgs.text(query, max_results=max_results)
        for r in ddgs_gen:
            results.append({
                "title": r.get("title", ""),
                "link": r.get("href", ""),
                "snippet": r.get("body", ""),
                "source": "DuckDuckGo"
            })
        return results

    def _search_fallback(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Fallback HTML scraping."""
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Fallback scraper returned {response.status_code}")
            
        html = response.text
        
        # Basic regex parsing
        link_pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>(.*?)</a>'
        
        links = re.findall(link_pattern, html)
        snippets = re.findall(snippet_pattern, html)
        
        for i in range(min(len(links), len(snippets), max_results)):
            link_url = links[i][0]
            title = links[i][1]
            snippet = snippets[i]
            
            # Clean up HTML entities
            title = self._clean_html(title)
            snippet = self._clean_html(snippet)
            
            results.append({
                "title": title,
                "link": link_url,
                "snippet": snippet,
                "source": "Web Search (Fallback)"
            })
        return results
        
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and entities."""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#x27;', "'").replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()

# Singleton
_web_client = None

def get_web_search_client() -> WebSearchClient:
    global _web_client
    if _web_client is None:
        _web_client = WebSearchClient()
    return _web_client
