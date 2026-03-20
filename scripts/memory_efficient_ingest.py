"""
Memory-Efficient Incremental Ingestion Script
==============================================
This script adds new documents WITHOUT loading all existing documents into RAM.

Key optimizations:
1. Adds directly to ChromaDB (handles duplicate IDs automatically)
2. Skips BM25 rebuilding during ingestion
3. Only rebuilds BM25 once at the very end
4. Processes files in batches to limit memory usage
"""

import sys
import os
from pathlib import Path
import json
import time
import gc

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Imports
import chromadb
from sentence_transformers import SentenceTransformer

def print_status(step, message):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{step}] {message}")

def main():
    print("="*70)
    print("  MEMORY-EFFICIENT INCREMENTAL INGESTION")
    print("  (Adds new data without loading existing 190k docs)")
    print("="*70)
    
    start_time = time.time()
    base_dir = Path(__file__).parent.parent / "DATA"
    chroma_dir = Path(__file__).parent.parent / "chroma_db_hybrid"
    
    # Step 1: Initialize ChromaDB client directly (bypass HybridChromaStore to save memory)
    print_status("1/6", "Initializing ChromaDB client...")
    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
        collection = client.get_or_create_collection("legal_db_hybrid")
        existing_count = collection.count()
        print_status("1/6", f"Connected! Existing documents: {existing_count}")
    except Exception as e:
        print_status("ERROR", f"ChromaDB init failed: {e}")
        return
    
    # Step 2: Initialize embedding model
    print_status("2/6", "Loading embedding model...")
    try:
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print_status("2/6", f"Model loaded! Device: {model.device}")
    except Exception as e:
        print_status("ERROR", f"Model load failed: {e}")
        return
    
    total_added = 0
    
    # Step 3: Indian Express QA
    print_status("3/6", "Adding Indian Express Property QA...")
    try:
        ie_file = base_dir / "indianexpress_property_law_qa" / "indianexpress_property_law_qa.json"
        if ie_file.exists():
            with open(ie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ids, texts, metas = [], [], []
            for i, item in enumerate(data):
                ids.append(f"ie_qa_{i}")
                texts.append(f"Question: {item.get('Question','')}\nAnswer: {item.get('Answer','')}")
                metas.append({"source": "Indian Express", "type": "qa", "domain": "property"})
            
            # Generate embeddings
            embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).tolist()
            
            # Add to ChromaDB (handles duplicates by ID)
            collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
            total_added += len(ids)
            print_status("3/6", f"Added {len(ids)} Indian Express QA docs")
        else:
            print_status("3/6", "File not found - skipping")
    except Exception as e:
        print_status("ERROR", f"Indian Express failed: {e}")
    
    gc.collect()  # Free memory
    
    # Step 4: NDTV Legal QA
    print_status("4/6", "Adding NDTV Legal QA...")
    try:
        ndtv_file = base_dir / "ndtv_legal_qa_data" / "ndtv_legal_qa_data.json"
        if ndtv_file.exists():
            with open(ndtv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ids, texts, metas = [], [], []
            for i, item in enumerate(data):
                ids.append(f"ndtv_qa_{i}")
                texts.append(f"Question: {item.get('Question','')}\nAnswer: {item.get('Answer','')}")
                metas.append({"source": "NDTV", "type": "qa"})
            
            embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True).tolist()
            collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
            total_added += len(ids)
            print_status("4/6", f"Added {len(ids)} NDTV QA docs")
        else:
            print_status("4/6", "File not found - skipping")
    except Exception as e:
        print_status("ERROR", f"NDTV failed: {e}")
    
    gc.collect()
    
    # Step 5: Supreme Court FULL Dataset (26,606 judgments)
    print_status("5/6", "Adding SC Judgments FULL (26,606 cases)...")
    try:
        sc_dir = base_dir / "SC_Judgments_FULL" / "chunks"
        if sc_dir.exists():
            years = sorted([d.name for d in sc_dir.iterdir() if d.is_dir() and d.name.isdigit()])
            print_status("5/6", f"Found years: {years[0]} to {years[-1]}")
            
            sc_added = 0
            batch_size = 100  # Small batches to limit memory
            
            for year in years:
                year_path = sc_dir / year
                chunk_files = list(year_path.glob("*_chunks.json"))
                
                ids, texts, metas = [], [], []
                
                for cf in chunk_files:
                    try:
                        with open(cf, 'r', encoding='utf-8') as f:
                            chunks = json.load(f)
                            for c in chunks:
                                if 'id' in c and 'text' in c:
                                    ids.append(c['id'])
                                    texts.append(c['text'])
                                    metas.append(c.get('metadata', {"source": "SC", "year": year}))
                                    
                                    # Process in batches
                                    if len(ids) >= batch_size:
                                        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
                                        collection.upsert(ids=ids, embeddings=embs, documents=texts, metadatas=metas)
                                        sc_added += len(ids)
                                        ids, texts, metas = [], [], []
                    except:
                        pass
                
                # Flush remaining
                if ids:
                    embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
                    collection.upsert(ids=ids, embeddings=embs, documents=texts, metadatas=metas)
                    sc_added += len(ids)
                    ids, texts, metas = [], [], []
                
                print_status("5/6", f"Year {year}: Total SC added = {sc_added}")
                gc.collect()
            
            total_added += sc_added
            print_status("5/6", f"SC Judgments complete! Added {sc_added} chunks")
        else:
            print_status("5/6", "SC directory not found - skipping")
    except Exception as e:
        print_status("ERROR", f"SC Judgments failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 6: Rebuild BM25 index (final step)
    print_status("6/6", "Rebuilding BM25 keyword index...")
    try:
        from rag_system.core.hybrid_chroma_store import HybridChromaStore
        # Initialize store - this will auto-rebuild BM25 from ChromaDB
        store = HybridChromaStore()
        store.rebuild_index()
        final_count = store.collection.count()
        print_status("6/6", f"BM25 rebuilt! Final document count: {final_count}")
    except Exception as e:
        print_status("ERROR", f"BM25 rebuild failed: {e}")
        print_status("INFO", "You can manually rebuild later with: store.rebuild_index()")
    
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print(f"  COMPLETE! Added {total_added} new documents")
    print(f"  Time: {elapsed/60:.1f} minutes")
    print("="*70)

if __name__ == "__main__":
    main()
