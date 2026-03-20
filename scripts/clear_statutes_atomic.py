import sys
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clear_statutes_atomic():
    """
    Clear statutes using raw ChromaDB client to avoid memory-heavy HybridChromaStore initialization.
    """
    print("="*60)
    print("ATOMIC CLEARING OF STATUTES (MEMORY EFFICIENT)")
    print("="*60)
    
    persist_dir = "chroma_db_hybrid"
    collection_name = "legal_db_hybrid"
    
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name)
    
    # 1. Check count of statutes
    print("Checking for documents with domain='statutes'...")
    res = collection.get(where={"domain": "statutes"}, include=[])
    ids = res.get('ids', [])
    count = len(ids)
    
    if count == 0:
        print("No statute documents found.")
        return
        
    print(f"Found {count} statute documents. Deleting...")
    
    # Delete in batches to be safe
    batch_size = 5000
    for i in range(0, count, batch_size):
        batch_ids = ids[i : i + batch_size]
        collection.delete(ids=batch_ids)
        print(f"  ✓ Deleted batch {i//batch_size + 1}")

    print("="*60)
    print(f"SUCCESS: {count} statutes deleted.")
    print("NOTE: You must delete the BM25 cache file manually or rebuild it to sync keyword search.")
    print(f"Cache file: {persist_dir}/{collection_name}_bm25.pkl")
    print("="*60)

if __name__ == "__main__":
    clear_statutes_atomic()
