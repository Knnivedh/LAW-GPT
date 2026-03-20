import chromadb
from pathlib import Path

def peek_statute_ids():
    persist_dir = "chroma_db_hybrid"
    collection_name = "legal_db_hybrid"
    
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name)
    
    # Peek at few docs from domain='statutes'
    res = collection.get(
        where={"domain": "statutes"},
        limit=5,
        include=["metadatas"]
    )
    
    print("Found IDs:")
    for i, doc_id in enumerate(res['ids']):
        print(f"ID: {doc_id} | Metadata: {res['metadatas'][i]}")

if __name__ == "__main__":
    peek_statute_ids()
