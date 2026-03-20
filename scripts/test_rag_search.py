import sys
import os
from pathlib import Path

# Add parent dir to path to import rag_system
sys.path.append(str(Path("c:/Users/LOQ/Downloads/LAW-GPT_new/LAW-GPT_new/LAW-GPT")))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def test_search(query, top_k=3):
    print(f"\n[SEARCH] FOR: '{query}'")
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    results = store.hybrid_search(query, n_results=top_k)
    
    if not results:
        print("❌ No results found.")
        return

    for i, res in enumerate(results):
        meta = res.get('metadata', {})
        source_type = meta.get('source', 'Unknown')
        print(f"\n[{i+1}] SOURCE: {source_type.upper()}")
        if source_type == 'statute':
            print(f"    ACT: {meta.get('act_name')}")
            print(f"    SECTION: {meta.get('section_number')}")
        else:
            print(f"    CASE: {meta.get('case_name', 'N/A')}")
            print(f"    YEAR: {meta.get('year', 'N/A')}")
            
        # Truncate content for display
        text = res.get('text', '')
        snippet = text[:300].replace('\n', ' ') + "..."
        print(f"    CONTENT: {snippet}")

if __name__ == "__main__":
    queries = [
        "What are the penalties for misleading advertisements under Consumer Protection Act?",
        "Provisions for breach of contract and compensation",
        "Liability of directors under Companies Act 2013",
        "Definition of deficiency in service"
    ]
    
    for q in queries:
        test_search(q)
