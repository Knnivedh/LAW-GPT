"""
COMPREHENSIVE RAG AUDIT SCRIPT v2
Improved logic for verification.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console for emojis/special chars
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

from rag_system.core.milvus_store import CloudMilvusStore
try:
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    LOCAL_STORE_AVAILABLE = True
except ImportError:
    LOCAL_STORE_AVAILABLE = False

def generate_id(source, content):
    hash_seed = f"{source}_{content[:500]}"
    return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()

class RagAuditor:
    def __init__(self):
        print("Initializing Auditor...")
        self.cloud_store = CloudMilvusStore()
        # Initialize local store with a check to avoid unhealthy DB crashes
        try:
            self.local_store = HybridChromaStore() if LOCAL_STORE_AVAILABLE else None
        except:
            print("Warning: Local Chroma Store failed to initialize properly.")
            self.local_store = None
        self.data_root = PROJECT_ROOT / "DATA"
        
    def check_document_existence(self, doc_id: str, text_snippet: str):
        results = {"cloud": False, "local": False}
        search_query = text_snippet[:300]
        
        # 1. Check Cloud (Searching with more depth)
        if self.cloud_store.is_connected:
            try:
                cloud_hits = self.cloud_store.hybrid_search(search_query, n_results=10)
                for hit in cloud_hits:
                    if hit.get('id') == doc_id or search_query[:50] in str(hit.get('text')):
                        results["cloud"] = True
                        break
            except Exception as e:
                pass

        # 2. Check Local
        if self.local_store:
            try:
                local_hits = self.local_store.hybrid_search(search_query, n_results=10)
                for hit in local_hits:
                    if hit.get('id') == doc_id or search_query[:50] in str(hit.get('text')):
                        results["local"] = True
                        break
            except Exception as e:
                pass
                
        return results

    def audit_folder(self, folder_name: str, num_samples: int = 2):
        folder_path = self.data_root / folder_name
        if not folder_path.exists():
            print(f"Folder not found: {folder_path}")
            return
            
        print(f"\n--- Checking: {folder_name} ---")
        json_files = list(folder_path.glob("**/*.json"))
        if not json_files:
            print("No JSON files found.")
            return

        samples_done = 0
        success = {"local": 0, "cloud": 0}

        for file_path in json_files:
            if samples_done >= num_samples: break
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                
                items = data if isinstance(data, list) else [data]
                if not items: continue
                
                # Sample a few entries from big files
                for i in range(min(1, len(items))):
                    entry = items[i]
                    if not isinstance(entry, dict): continue
                    
                    content = (entry.get('text') or entry.get('content') or 
                              entry.get('response_text') or entry.get('query_text') or str(entry))
                    
                    if len(str(content)) < 50: continue
                    
                    doc_id = generate_id(folder_name, str(content))
                    status = self.check_document_existence(doc_id, str(content))
                    
                    print(f"  File: {file_path.name[:40]}...")
                    print(f"    Local: {'[OK]' if status['local'] else '[MISSING]'}")
                    print(f"    Cloud: {'[OK]' if status['cloud'] else '[MISSING]'}")
                    
                    if status['local']: success["local"] += 1
                    if status['cloud']: success["cloud"] += 1
                    samples_done += 1
                    if samples_done >= num_samples: break
            except:
                continue

        print(f"Summary for {folder_name}: Local={success['local']}, Cloud={success['cloud']}")

    def run(self):
        print("\n" + "="*60)
        print("RAG DATA INTEGRITY AUDIT")
        print("="*60)
        # Check primary folders
        for fd in ["Statutes", "NCDRC", "SC_Judgments", "kanoon_data"]:
            self.audit_folder(fd)
        print("\nAudit task finished.")

if __name__ == "__main__":
    RagAuditor().run()
