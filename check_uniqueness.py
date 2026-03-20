import os, sys, hashlib
sys.path.append(os.getcwd())
from rag_system.core.milvus_store import CloudMilvusStore

def check_uniqueness(sample_size=1000):
    print("--- 🔍 Zilliz Cloud Uniqueness & Connectivity Test ---")
    store = CloudMilvusStore()
    if not store.is_connected:
        print("❌ FAILED: Could not connect to Zilliz.")
        return

    print(f"✅ Connected to Collection: {store.collection_name}")
    print(f"📊 Total Entities: {store.collection.num_entities}")
    
    # Check for duplicates in the most recent data
    print(f"🔎 Sampling last {sample_size} chunks for uniqueness...")
    res = store.collection.query(expr="", output_fields=["text", "id"], limit=sample_size)
    
    texts = [item['text'] for item in res]
    unique_texts = set(texts)
    
    dupe_count = len(texts) - len(unique_texts)
    uniqueness_pct = (len(unique_texts) / len(texts)) * 100 if texts else 0
    
    print(f"✅ Sample Unique Items: {len(unique_texts)}/{len(texts)}")
    print(f"⚠️ Duplicates Found: {dupe_count}")
    print(f"📈 Uniqueness Score: {uniqueness_pct:.2f}%")
    
    if dupe_count > 0:
        print("💡 Note: Small duplicate counts are normal due to overlapping chunks.")
    
    # Check for Azure references in environment
    print("\n--- ☁️ Azure System Check ---")
    azure_keys = [k for k in os.environ.keys() if 'AZURE' in k.upper()]
    if azure_keys:
        print(f"✅ Found {len(azure_keys)} Azure-related environment variables.")
    else:
        print("❌ No Azure environment variables found. System is currently standalone/Zilliz-only.")

if __name__ == "__main__":
    check_uniqueness()
