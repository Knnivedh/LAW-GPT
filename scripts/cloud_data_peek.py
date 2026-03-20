"""
CLOUDBRAIN PEEK - Direct Zilliz Data Verification
Retrieves actual document excerpts from different sources in your cloud.
"""

import os
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

from rag_system.core.milvus_store import CloudMilvusStore

def peek_cloud():
    print("\n" + "="*60)
    print("📡 DIRECT CLOUDBRAIN PEEK - REAL DATA PROOF")
    print("="*60)
    
    store = CloudMilvusStore()
    if not store.is_connected:
        print("❌ Could not connect to Zilliz.")
        return

    print(f"Total Documents in Cloud: {store.count():,}")
    
    # Test queries for your key data areas
    test_queries = {
        "Statutes": "Indian Penal Code or Transfer of Property Act",
        "Kanoon Q&A": "What are the rights of a consumer?",
        "SC Judgments": "Supreme Court judgment on property rights",
        "Case Studies": "Medical negligence case study"
    }
    
    for area, query in test_queries.items():
        print(f"\n🔍 PROBING AREA: {area}")
        print(f"Query: '{query}'")
        try:
            hits = store.hybrid_search(query, n_results=2)
            if not hits:
                print("  ❌ No direct matches found for this query snippet.")
                continue
                
            for i, hit in enumerate(hits):
                source = hit.get('metadata', {}).get('source', 'Unknown')
                title = hit.get('metadata', {}).get('title', 'No Title')[:50]
                text = str(hit.get('text'))[:150].replace('\n', ' ')
                
                print(f"  [{i+1}] Source: {source}")
                print(f"      Title: {title}")
                print(f"      Text: {text}...")
        except Exception as e:
            print(f"  ❌ Error probing {area}: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    peek_cloud()
