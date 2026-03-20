import sys
from pathlib import Path

# Add parent dir to path to import rag_system
sys.path.append(str(Path("c:/Users/LOQ/Downloads/LAW-GPT_new/LAW-GPT_new/LAW-GPT")))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def check_metadata():
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    
    # Get a sample of documents from "Supreme Court Kaggle"
    data = store.collection.get(
        where={"source": "Supreme Court Kaggle"},
        limit=5,
        include=['metadatas', 'documents']
    )
    
    metadatas = data.get('metadatas', [])
    documents = data.get('documents', [])
    
    print("\n--- SAMPLE: Supreme Court Kaggle Metadata ---")
    for i in range(len(metadatas)):
        print(f"\n[DOC {i+1}]")
        print(f"METADATA: {metadatas[i]}")
        print(f"CONTENT PREVIEW: {documents[i][:200]}...")

    # Get a sample of documents from "sc_judgment" (my new batch)
    data_new = store.collection.get(
        where={"source": "sc_judgment"},
        limit=5,
        include=['metadatas', 'documents']
    )
    
    metadatas_new = data_new.get('metadatas', [])
    documents_new = data_new.get('documents', [])
    
    print("\n--- SAMPLE: sc_judgment (New) Metadata ---")
    for i in range(len(metadatas_new)):
        print(f"\n[DOC {i+1}]")
        print(f"METADATA: {metadatas_new[i]}")
        print(f"CONTENT PREVIEW: {documents_new[i][:200]}...")

if __name__ == "__main__":
    check_metadata()
