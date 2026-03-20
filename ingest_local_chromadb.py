import os
import sys
import argparse
from pathlib import Path

# Add project root to sys.path so we can import rag_system
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

# Force execution with python-dotenv loaded
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def main():
    print("=" * 60)
    print("🚀 LAW-GPT CHROMADB INGESTION SCRIPT")
    print("=" * 60)
    
    db_path = PROJECT_ROOT / "kaanoon_test" / "chroma_db_hybrid"
    print(f"[INFO] Connecting to local ChromaDB: {db_path}")
    
    # Initialize connecting to Db
    store = HybridChromaStore(persist_directory=str(db_path))
    
    # 1. Look for Statutes Data
    data_dir = PROJECT_ROOT.parent.parent / "BACKUP_DATA" / "DATA" / "Statutes"
    print(f"\n[INFO] Checking directory: {data_dir}")
    
    if not data_dir.exists():
        print(f"[ERROR] Directory not found: {data_dir}")
        return
        
    txt_files = list(data_dir.glob("*.txt"))
    print(f"[INFO] Found {len(txt_files)} .txt statute files.")
    
    chunks = []
    
    for fpath in txt_files:
        print(f"Reading: {fpath.name}")
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            print(f"  [ERROR] {e}")
            continue
            
        # Basic chunking by paragraph or fixed size
        import re
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = []
        current_len = 0
        doc_chunks = 0
        
        for p in paragraphs:
            stripped = p.strip()
            if not stripped:
                continue
            
            p_len = len(stripped)
            if current_len + p_len > 1500 and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({"text": chunk_text, "metadata": {"source": fpath.name}})
                doc_chunks += 1
                current_chunk = [stripped]
                current_len = p_len
            else:
                current_chunk.append(stripped)
                current_len += p_len
                
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({"text": chunk_text, "metadata": {"source": fpath.name}})
            doc_chunks += 1
            
        print(f"  -> Created {doc_chunks} chunks.")
        
    print(f"\n[INFO] Total chunks to ingest: {len(chunks)}")
    
    if not chunks:
        print("[INFO] Nothing to ingest.")
        return
        
    print("[INFO] Adding to ChromaDB... this may take some time depending on embedding model.")
    store.add_documents(chunks)
    
    print("\n[SUCCESS] Ingestion complete.")
    print("=" * 60)

if __name__ == "__main__":
    main()
