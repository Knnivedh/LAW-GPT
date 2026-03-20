import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def check_db_status():
    print("Checking ChromaDB Status...")
    try:
        store = HybridChromaStore()
        count = store.collection.count()
        print(f"Total Documents in 'legal_db_hybrid': {count}")
        
        # Peek at a few to see what we have
        peek = store.collection.peek(limit=5)
        if peek and peek['ids']:
            print(f"Sample IDs: {peek['ids']}")
            if peek['metadatas']:
                print(f"Sample Metadata sources: {[m.get('source', 'N/A') for m in peek['metadatas']]}")
    except Exception as e:
        print(f"Error accessing DB: {e}")

if __name__ == "__main__":
    check_db_status()
