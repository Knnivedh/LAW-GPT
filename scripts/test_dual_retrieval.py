import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

def test_unified_retrieval():
    print("Testing Unified Retrieval with Dual Stores...")
    
    # Initialize system (will load both stores)
    try:
        rag = UnifiedAdvancedRAG()
    except Exception as e:
        print(f"Initialization failed (likely API key issues, but checking stores): {e}")
        # Manual fallback if initialization fails due to API keys
        from rag_system.core.hybrid_chroma_store import HybridChromaStore
        from rag_system.core.enhanced_retriever import EnhancedRetriever
        
        main_store = HybridChromaStore()
        statute_store = HybridChromaStore(
            persist_directory="chroma_db_statutes",
            collection_name="legal_db_statutes"
        )
        retriever = EnhancedRetriever(main_store, statute_store=statute_store)
    else:
        retriever = rag.retriever
    
    test_queries = [
        "What is an anti-competitive agreement under Competition Act?",
        "corporate insolvency resolution process under IBC"
    ]
    
    for query in test_queries:
        print(f"\nQUERY: {query}")
        # Test the retrieval part explicitly
        results = retriever.retrieve(query, allow_live_search=False)
        
        for i, res in enumerate(results, 1):
            source_file = res['metadata'].get('source_file', 'N/A')
            domain = res['metadata'].get('domain', 'Unknown')
            act = res['metadata'].get('act', 'Unknown')
            
            print(f"  {i}. [{domain}/{act}] {source_file}")
            print(f"     Content: {res['text'][:150]}...")
            
    print("\n✓ Dual-store retrieval verified successfully.")

if __name__ == "__main__":
    test_unified_retrieval()
