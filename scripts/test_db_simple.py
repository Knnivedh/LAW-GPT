import chromadb
from pathlib import Path

def test_db():
    persist_dir = "chroma_db_hybrid"
    print(f"Opening DB at {persist_dir}...")
    client = chromadb.PersistentClient(path=persist_dir)
    print("Client initialized.")
    collections = client.list_collections()
    print(f"Collections found: {[c.name for c in collections]}")
    
    collection = client.get_collection("legal_db_hybrid")
    print(f"Collection 'legal_db_hybrid' count: {collection.count()}")

if __name__ == "__main__":
    try:
        test_db()
    except Exception as e:
        print(f"FAILED: {e}")
