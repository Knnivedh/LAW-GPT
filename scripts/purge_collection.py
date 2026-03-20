"""
PURGE COLLECTION - Reset Zilliz Cloud
Clears all documents from the collection to reset storage quota.
"""

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
from pymilvus import utility

def purge():
    print("\n" + "="*50)
    print("🗑️ ZILLIZ COLLECTION PURGE")
    print("="*50)
    
    store = CloudMilvusStore()
    if not store.is_connected:
        print("❌ Cloud connection failed.")
        return

    collection_name = store.collection_name
    print(f"Collection: {collection_name}")
    print(f"Current Count: {store.count():,}")
    
    confirm = input(f"\n⚠️ WARNING: This will delete ALL data in '{collection_name}'. Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        # Dropping and recreating is the cleanest way in Milvus to reset quota
        print(f"Dropping collection '{collection_name}'...")
        utility.drop_collection(collection_name)
        
        print("Re-initializing collection with fresh schema...")
        store._initialize_collection()
        
        print("\n✅ Collection Purged Successfully!")
        print(f"New Count: {store.count():,}")
    except Exception as e:
        print(f"❌ Purge failed: {e}")

if __name__ == "__main__":
    purge()
