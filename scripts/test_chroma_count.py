import chromadb
from chromadb.config import Settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_count():
    print("--- ChromaDB Count Test ---")
    try:
        client = chromadb.PersistentClient(path="chroma_db_hybrid")
        print("Client initialized")
        
        collection = client.get_collection("legal_db_hybrid")
        print(f"Collection '{collection.name}' retrieved")
        
        print("Calling count()...")
        c = collection.count()
        print(f"Count: {c}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_count()
