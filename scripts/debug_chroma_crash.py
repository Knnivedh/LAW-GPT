import chromadb
from chromadb.config import Settings
from pathlib import Path

def test_chroma():
    path = "chroma_db_hybrid"
    print(f"Connecting to {path}...")
    client = chromadb.PersistentClient(path=path)
    
    print("Getting collection 'legal_db_hybrid'...")
    try:
        collection = client.get_collection("legal_db_hybrid")
        print("Success!")
        
        print("Attempting to count documents...")
        count = collection.count()
        print(f"Count: {count}")
        
        print("Attempting a small peek...")
        peek = collection.peek(limit=1)
        print(f"Peek IDs: {peek['ids']}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_chroma()
