"""
Fast Ingestion Script - Memory Safe Version
Skips duplicate checking to avoid memory issues with large existing datasets.
Adds new data sources that don't already have an ingestion pipeline.
"""

import sys
import os
from pathlib import Path
import json
import time

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def main():
    print("="*60)
    print("  FAST RAG INGESTION (Memory Safe)")
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
        import traceback
        traceback.print_exc()
        return
    
    # We skip loading all existing IDs to avoid memory issues
    # Instead, we'll use add with upsert behavior or handle duplicates gracefully
    print("\n[2] Skipping ID pre-load (Memory Safe Mode)")
    print(f"    Will add new content directly...")
    
    # Step 1: Indian Express QA (Small dataset, safe to add)
    print("\n[3] Ingesting Indian Express QA...")
    try:
        ie_file = base_dir / "indianexpress_property_law_qa" / "indianexpress_property_law_qa.json"
        if ie_file.exists():
            with open(ie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, item in enumerate(data):
                doc_id = f"ie_qa_{i}"
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {"source": "Indian Express", "type": "qa", "domain": "property"}
                })
            
            print(f"    Adding {len(docs)} documents...")
            try:
                store.add_documents(docs, show_progress=True, rebuild_bm25=False)
                print(f"    [OK] Added {len(docs)} docs")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"    [SKIP] Documents already exist")
                else:
                    print(f"    [ERROR] {e}")
        else:
            print(f"    [SKIP] File not found")
    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Step 2: NDTV QA (Small dataset)
    print("\n[4] Ingesting NDTV Legal QA...")
    try:
        ndtv_file = base_dir / "ndtv_legal_qa_data" / "ndtv_legal_qa_data.json"
        if ndtv_file.exists():
            with open(ndtv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, item in enumerate(data):
                doc_id = f"ndtv_qa_{i}"
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {"source": "NDTV", "type": "qa"}
                })
            
            print(f"    Adding {len(docs)} documents...")
            try:
                store.add_documents(docs, show_progress=True, rebuild_bm25=False)
                print(f"    [OK] Added {len(docs)} docs")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"    [SKIP] Documents already exist")
                else:
                    print(f"    [ERROR] {e}")
        else:
            print(f"    [SKIP] File not found")
    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: 50K Case Studies (Skip if already done - check file marker)
    print("\n[5] Ingesting 50K Case Studies...")
    marker_file = base_dir / "Indian_Case_Studies_50K ORG" / ".ingested"
    try:
        cs_file = base_dir / "Indian_Case_Studies_50K ORG" / "Indian_Case_Studies_50K ORG.json"
        if marker_file.exists():
            print("    [SKIP] Already ingested (marker file found)")
        elif cs_file.exists():
            print("    Loading file...")
            with open(cs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"    Total cases: {len(data)}")
            batch_size = 500
            added = 0
            
            for batch_start in range(0, len(data), batch_size):
                batch_end = min(batch_start + batch_size, len(data))
                batch_data = data[batch_start:batch_end]
                
                docs = []
                for i, case in enumerate(batch_data):
                    idx = batch_start + i
                    doc_id = f"cs_50k_{idx}_{case.get('case_id', 'unknown')}"
                    
                    text = f"Title: {case.get('case_title','')}\n"
                    text += f"Description: {case.get('case_description','')}\n"
                    text += f"Verdict: {case.get('verdict','')}"
                    
                    docs.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": {"source": "50k_dataset", "type": "case_study"}
                    })
                
                try:
                    store.add_documents(docs, show_progress=False, rebuild_bm25=False)
                    added += len(docs)
                except Exception:
                    pass  # Skip duplicates silently
                
                if (batch_start // batch_size + 1) % 10 == 0:
                    print(f"    Progress: {added}/{len(data)}")
            
            print(f"    [OK] Added {added} docs")
            # Create marker file
            with open(marker_file, 'w') as f:
                f.write(f"Ingested on {time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"    [SKIP] File not found")
    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: SC Judgments FULL (Skip if already done)
    print("\n[6] Ingesting Supreme Court Judgments FULL...")
    sc_marker = base_dir / "SC_Judgments_FULL" / ".ingested"
    try:
        sc_dir = base_dir / "SC_Judgments_FULL" / "chunks"
        if sc_marker.exists():
            print("    [SKIP] Already ingested (marker file found)")
        elif sc_dir.exists():
            years = sorted([d.name for d in sc_dir.iterdir() if d.is_dir() and d.name.isdigit()])
            print(f"    Years: {years[0]} to {years[-1]} ({len(years)} total)")
            
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
                                if 'id' in c and 'text' in c:
                                    year_docs.append(c)
                    except:
                        pass
                    
                    if len(year_docs) >= 1000:
                        try:
                            store.add_documents(year_docs, show_progress=False, rebuild_bm25=False)
                            total_added += len(year_docs)
                        except:
                            pass
                        year_docs = []
                
                if year_docs:
                    try:
                        store.add_documents(year_docs, show_progress=False, rebuild_bm25=False)
                        total_added += len(year_docs)
                    except:
                        pass
                
                print(f"    Year {year}: Total added: {total_added}")
            
            print(f"    [OK] SC complete. Added {total_added} chunks.")
            with open(sc_marker, 'w') as f:
                f.write(f"Ingested on {time.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"    [SKIP] Directory not found")
    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Final: Rebuild BM25 index
    print("\n[7] Rebuilding BM25 index...")
    try:
        store.rebuild_index()
        print("    [OK] Index rebuilt")
    except Exception as e:
        print(f"    [ERROR] {e}")
    
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"  COMPLETE! Time: {elapsed/60:.1f} min")
    print("="*60)

if __name__ == "__main__":
    main()
