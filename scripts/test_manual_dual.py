import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from rag_system.core.hybrid_chroma_store import HybridChromaStore
from rag_system.core.enhanced_retriever import EnhancedRetriever

def test_manual_dual_retrieval():
    print("Testing MANUAL Dual Retrieval (No Unified RAG wrapper)...")
    
    # Initialize main store (Judgments)
    main_store = HybridChromaStore(
        persist_directory="chroma_db_hybrid",
        collection_name="legal_db_hybrid"
    )
    
    # Initialize specialized statutes store
    statute_store = HybridChromaStore(
        persist_directory="chroma_db_statutes",
        collection_name="legal_db_statutes"
    )
    
    # Initialize retriever
    retriever = EnhancedRetriever(main_store, statute_store=statute_store)
    
    test_queries = [
        "What is an anti-competitive agreement under Competition Act?",
        "corporate insolvency resolution process under IBC"
    ]
    
    for query in test_queries:
        print(f"\nQUERY: {query}")
        # Test the retrieval part explicitly
        results = retriever.retrieve(query, allow_live_search=False)
        
        # Check if we got results from the statutes store
        statute_results = [r for r in results if r['metadata'].get('domain') == 'statutes']
        print(f"  → Found {len(statute_results)} statute sections out of {len(results)} total results")
        
        for i, res in enumerate(results[:3], 1):
            domain = res['metadata'].get('domain', 'Unknown')
            act = res['metadata'].get('act', 'Unknown')
            sec = res['metadata'].get('section_number', 'N/A')
            
            print(f"  {i}. [{domain}/{act}] Section {sec}")
            print(f"     Content snippet: {res['text'][:150]}...")
            
    if any(len([r for r in retriever.retrieve(q, allow_live_search=False) if r['metadata'].get('domain') == 'statutes']) > 0 for q in test_queries):
        print("\n✓ MANUAL Dual-store retrieval verified! Statutes are being correctly mixed with judgments.")
    else:
        print("\n[FAIL] No statutes found in mixed results.")

if __name__ == "__main__":
    test_manual_dual_retrieval()
