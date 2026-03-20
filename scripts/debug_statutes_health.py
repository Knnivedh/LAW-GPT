import chromadb
from chromadb.config import Settings
from pathlib import Path

def test_chroma():
    path = "chroma_db_statutes"
    print(f"Connecting to {path}...")
    client = chromadb.PersistentClient(path=path)
    
    print("Getting collection 'legal_db_statutes'...")
    try:
        collection = client.get_collection("legal_db_statutes")
        print("Success!")
        
        print("Attempting to count documents...")
        count = collection.count()
        print(f"Count: {count}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_chroma()
