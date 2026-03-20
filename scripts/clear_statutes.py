import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.core.hybrid_chroma_store import HybridChromaStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_statutes():
    """
    Clear all documents with domain='statutes' from the RAG database.
    This prevents duplicates when re-ingesting improved data.
    """
    print("="*60)
    print("CLEARING EXISTING STATUTES FROM DATABASE")
    print("="*60)
    
    # 1. Initialize Store
    store = HybridChromaStore(
        persist_directory="chroma_db_hybrid",
        collection_name="legal_db_hybrid"
    )
    
    # 2. Count before
    count_before = store.collection.count()
    print(f"Total documents in database (before): {count_before}")
    
    # 3. Delete by metadata filter
    try:
        # Get count of statute docs specifically if possible
        statute_docs = store.collection.get(where={"domain": "statutes"})
        statute_count = len(statute_docs['ids'])
        print(f"Found {statute_count} documents with domain='statutes'")
        
        if statute_count > 0:
            print(f"Deleting {statute_count} statute documents...")
            store.collection.delete(where={"domain": "statutes"})
            print("✓ Deletion successful")
        else:
            print("No statute documents found to delete.")
            
        # Rebuild BM25 index after deletion
        print("Rebuilding BM25 index...")
        store.rebuild_index()
        
    except Exception as e:
        print(f"Error during clearing: {e}")
        return

    # 4. Count after
    count_after = store.collection.count()
    print(f"Total documents in database (after): {count_after}")
    print("="*60)
    print("SUCCESS: Statutes cleared and index rebuilt.")
    print("="*60)

if __name__ == "__main__":
    clear_statutes()
