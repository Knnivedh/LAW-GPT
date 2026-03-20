import sys
import os
import numpy as np

# Add project root to sys.path
sys.path.append(os.getcwd())

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def verify_statutes():
    store = HybridChromaStore(
        persist_directory="chroma_db_statutes",
        collection_name="legal_db_statutes"
    )
    
    test_queries = [
        "What is an anti-competitive agreement under Competition Act?",
        "Who is an unpaid seller under Sale of Goods Act?",
        "Definition of partnership",
        "How to initiate corporate insolvency under IBC?"
    ]
    
    print("\n" + "="*80)
    print("STATUTE SEARCH VERIFICATION")
    print("="*80)
    
    for query in test_queries:
        print(f"\nQUERY: {query}")
        results = store.hybrid_search(query, n_results=3)
        for i, res in enumerate(results, 1):
            print(f"  {i}. [{res['metadata'].get('act', 'Unknown')}] {res['metadata'].get('section_number', 'N/A')}: {res['metadata'].get('section_title', 'No Title')}")
            print(f"     Snippet: {res['text'][:200]}...")
            print(f"     Score: {res['rrf_score']:.4f}")

if __name__ == "__main__":
    verify_statutes()
