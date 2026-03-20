import sys
from pathlib import Path

# Add parent dir to path to import rag_system
sys.path.append(str(Path("c:/Users/LOQ/Downloads/LAW-GPT_new/LAW-GPT_new/LAW-GPT")))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def audit_database():
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    
    # Get all documents
    # Note: ChromaDB get() can return all if ids is None
    data = store.collection.get(include=['metadatas'])
    metadatas = data.get('metadatas', [])
    
    source_counts = {}
    for meta in metadatas:
        source = meta.get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    
    print("\n--- DATABASE SOURCE AUDIT ---")
    for source, count in source_counts.items():
        print(f"SOURCE: {source:20} | COUNT: {count}")
    print(f"TOTAL DOCUMENTS: {len(metadatas)}")

if __name__ == "__main__":
    audit_database()
