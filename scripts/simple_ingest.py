"""
Simple Sequential Ingestion Script
This script ingests missing data into the RAG system one step at a time
with explicit error handling and status printing.
"""

import sys
import os
from pathlib import Path
import json
import time

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def main():
    print("="*60)
    print("  SIMPLE SEQUENTIAL RAG INGESTION")
    print("="*60)
    
    start_time = time.time()
    base_dir = Path(__file__).parent.parent / "DATA"
    
    # Initialize store once
    print("\n[1] Initializing ChromaDB store...")
    try:
        store = HybridChromaStore()
        existing_count = store.collection.count()
        print(f"    Existing documents: {existing_count}")
    except Exception as e:
        print(f"    [ERROR] Failed to initialize: {e}")
        return
    
    # Get existing IDs to avoid duplicates
    print("\n[2] Loading existing document IDs...")
    try:
        existing_result = store.collection.get(include=[])
        existing_ids = set(existing_result['ids'])
        print(f"    Loaded {len(existing_ids)} existing IDs")
    except Exception as e:
        print(f"    [ERROR] Failed to load IDs: {e}")
        existing_ids = set()
    
    # Step 1: Indian Express QA
    print("\n[3] Ingesting Indian Express QA...")
    try:
        ie_file = base_dir / "indianexpress_property_law_qa" / "indianexpress_property_law_qa.json"
        if ie_file.exists():
            with open(ie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, item in enumerate(data):
                doc_id = f"ie_qa_{i}"
                if doc_id in existing_ids:
                    continue
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {"source": "Indian Express", "type": "qa", "domain": "property"}
                })
            
            if docs:
                print(f"    Adding {len(docs)} new documents...")
                store.add_documents(docs, show_progress=True, rebuild_bm25=False)
                print(f"    [OK] Added {len(docs)} docs")
            else:
                print("    [SKIP] All documents already exist")
        else:
            print(f"    [SKIP] File not found: {ie_file}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Step 2: NDTV QA
    print("\n[4] Ingesting NDTV Legal QA...")
    try:
        ndtv_file = base_dir / "ndtv_legal_qa_data" / "ndtv_legal_qa_data.json"
        if ndtv_file.exists():
            with open(ndtv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, item in enumerate(data):
                doc_id = f"ndtv_qa_{i}"
                if doc_id in existing_ids:
                    continue
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {"source": "NDTV", "type": "qa"}
                })
            
            if docs:
                print(f"    Adding {len(docs)} new documents...")
                store.add_documents(docs, show_progress=True, rebuild_bm25=False)
                print(f"    [OK] Added {len(docs)} docs")
            else:
                print("    [SKIP] All documents already exist")
        else:
            print(f"    [SKIP] File not found: {ndtv_file}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Step 3: 50K Case Studies (Large file, batch processing)
    print("\n[5] Ingesting 50K Case Studies (Large file)...")
    try:
        cs_file = base_dir / "Indian_Case_Studies_50K ORG" / "Indian_Case_Studies_50K ORG.json"
        if cs_file.exists():
            print("    Loading file (may take a moment)...")
            with open(cs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"    Total cases in file: {len(data)}")
            batch_size = 500
            added = 0
            
            for batch_start in range(0, len(data), batch_size):
                batch_end = min(batch_start + batch_size, len(data))
                batch_data = data[batch_start:batch_end]
                
                docs = []
                for i, case in enumerate(batch_data):
                    idx = batch_start + i
                    doc_id = f"cs_50k_{idx}_{case.get('case_id', 'unknown')}"
                    if doc_id in existing_ids:
                        continue
                    
                    text = f"Title: {case.get('case_title','')}\n"
                    text += f"Description: {case.get('case_description','')}\n"
                    text += f"Verdict: {case.get('verdict','')}"
                    
                    docs.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": {
                            "source": "50k_dataset",
                            "case_id": str(case.get('case_id', '')),
                            "type": "case_study"
                        }
                    })
                
                if docs:
                    store.add_documents(docs, show_progress=False, rebuild_bm25=False)
                    added += len(docs)
                    print(f"    Batch {batch_start//batch_size + 1}: Added {len(docs)} docs (Total: {added})")
            
            print(f"    [OK] Completed 50K ingestion. Added {added} new docs.")
        else:
            print(f"    [SKIP] File not found: {cs_file}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Step 4: Supreme Court Judgments FULL
    print("\n[6] Ingesting Supreme Court Judgments (FULL dataset)...")
    try:
        sc_dir = base_dir / "SC_Judgments_FULL" / "chunks"
        if sc_dir.exists():
            years = sorted([d.name for d in sc_dir.iterdir() if d.is_dir() and d.name.isdigit()])
            print(f"    Found years: {years[0]} to {years[-1]} ({len(years)} total)")
            
            total_added = 0
            for year in years:
                year_path = sc_dir / year
                chunk_files = list(year_path.glob("*_chunks.json"))
                
                year_docs = []
                for cf in chunk_files:
                    try:
                        with open(cf, 'r', encoding='utf-8') as f:
                            chunks = json.load(f)
                            for c in chunks:
                                if c.get('id') and c['id'] not in existing_ids:
                                    year_docs.append(c)
                    except:
                        pass
                    
                    # Batch every 1000 docs
                    if len(year_docs) >= 1000:
                        store.add_documents(year_docs, show_progress=False, rebuild_bm25=False)
                        total_added += len(year_docs)
                        year_docs = []
                
                if year_docs:
                    store.add_documents(year_docs, show_progress=False, rebuild_bm25=False)
                    total_added += len(year_docs)
                
                if (years.index(year) + 1) % 5 == 0 or year == years[-1]:
                    print(f"    Year {year}: Total added so far: {total_added}")
            
            print(f"    [OK] SC Judgments complete. Added {total_added} new chunks.")
        else:
            print(f"    [SKIP] Directory not found: {sc_dir}")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    # Final: Rebuild BM25 index
    print("\n[7] Rebuilding BM25 index...")
    try:
        store.rebuild_index()
        print("    [OK] Index rebuilt successfully")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"  COMPLETE! Total time: {elapsed/60:.1f} minutes")
    print("="*60)

if __name__ == "__main__":
    main()
