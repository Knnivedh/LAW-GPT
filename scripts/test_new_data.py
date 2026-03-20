import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from rag_system.core.hybrid_chroma_store import HybridChromaStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_retrieval():
    """Test retrieval for newly ingested domains"""
    print("\n" + "="*60)
    print("VERIFYING RETRIEVAL FOR NEWLY INGESTED DATA")
    print("="*60)
    
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    
    test_queries = [
        # Constitution
        {
            "query": "Right to life and personal liberty Article 21",
            "expected_source": "Constitution of India",
            "topic": "Constitution"
        },
        # Property Law Case
        {
            "query": "adverse possession requirements T. Anjanappa nec vi nec clam",
            "expected_source": "Property Law Cases",
            "topic": "Property Case Law"
        },
        # Tax Law
        {
            "query": "GST registration threshold 40 lakhs",
            "expected_source": "Tax Law",
            "topic": "Tax Domain"
        },
        # IP Law
        {
            "query": "trademark infringement passing off principles",
            "expected_source": "Intellectual Property Law",
            "topic": "IP Domain"
        },
        # Landmark Expansion
        {
            "query": "Bachan Singh rarest of rare death penalty",
            "expected_source": "landmark_legal_cases.json",
            "topic": "Landmark Expansion"
        }
    ]
    
    success_count = 0
    
    for test in test_queries:
        print(f"\nCreated Query ({test['topic']}): '{test['query']}'")
        try:
            results = store.hybrid_search(test['query'], n_results=3)
            
            found = False
            print(f"  Top Result Sources:")
            for i, doc in enumerate(results):
                source = doc.get('metadata', {}).get('source', 'Unknown')
                title = doc.get('metadata', {}).get('title', '')
                case_name = doc.get('metadata', {}).get('case_name', '')
                name = title or case_name or "Untitled"
                
                print(f"  {i+1}. [{source}] {name}")
                
                # Loose matching for source verification
                if test['expected_source'].lower() in source.lower() or source.lower() in test['expected_source'].lower():
                    found = True
            
            if found:
                print(f"  RESULT: PASS (Found expected source)")
                success_count += 1
            else:
                print(f"  RESULT: WARNING (Expected source '{test['expected_source']}' not in top 3)")
                
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            
    print("\n" + "="*60)
    print(f"TEST SUMMARY: {success_count}/{len(test_queries)} PASSED")
    print("="*60)

if __name__ == "__main__":
    test_retrieval()
