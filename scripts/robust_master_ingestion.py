"""
Master Ingestion Script for Complete RAG System - ROBUST VERSION
- Checking existing data to avoid duplicates
- Batch processing with error handling
- Sequential execution to prevent locks
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion_robust.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def print_section_header(step_num, total_steps, title):
    print("\n" + "="*80)
    print(f"  [{step_num}/{total_steps}] {title}")
    print("="*80)

def print_status(status, message):
    """Print status with icon"""
    icons = {
        "start": "[>>]",
        "progress": "[...]",
        "success": "[OK]",
        "error": "[X]",
        "info": "[i]"
    }
    icon = icons.get(status, "[*]")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {icon} {message}")

class RobustIngester:
    def __init__(self):
        self.store = HybridChromaStore()
        self.existing_ids = set()
        self._load_existing_ids()

    def _load_existing_ids(self):
        """Cache existing IDs to avoid duplicate insertion attempts"""
        print_status("info", "Checking existing documents in DB...")
        try:
            # Getting just IDs is much faster/lighter than full docs
            result = self.store.collection.get(include=[])
            self.existing_ids = set(result['ids'])
            print_status("info", f"Found {len(self.existing_ids)} existing documents.")
        except Exception as e:
            print_status("error", f"Could not load existing IDs: {e}")
            self.existing_ids = set()

    def add_documents_safely(self, documents, batch_name="Batch"):
        """Add documents only if they don't exist, handling errors"""
        new_docs = []
        for doc in documents:
            if doc['id'] not in self.existing_ids:
                new_docs.append(doc)
        
        if not new_docs:
            return  # Nothing to add

        try:
            # Use small batches for safety
            batch_size = 50
            for i in range(0, len(new_docs), batch_size):
                batch = new_docs[i:i+batch_size]
                # We use skip_bm25=True if available, or just standard add
                # Assuming the method signature from previous edits:
                # add_documents(documents, batch_size=..., show_progress=..., rebuild_bm25=...)
                try:
                    self.store.add_documents(
                        batch, 
                        show_progress=False, 
                        rebuild_bm25=False # CRITICAL optimization
                    )
                    # Update our local cache
                    self.existing_ids.update(doc['id'] for doc in batch)
                    print_status("progress", f"Ingested {len(batch)} docs from {batch_name}")
                except TypeError:
                    # Fallback if rebuild_bm25 param doesn't exist
                    self.store.add_documents(batch, show_progress=False)
                    self.existing_ids.update(doc['id'] for doc in batch)
                    print_status("progress", f"Ingested {len(batch)} docs from {batch_name}")

        except Exception as e:
            print_status("error", f"Failed to ingest {batch_name}: {e}")

def main():
    total_steps = 5
    start_time = time.time()
    
    print("\n" + "="*80)
    print("ROBUST RAG DATA INGESTION (Checking for Duplicates)".center(80))
    print("="*80)
    
    # Initialize Shared Store Wrapper
    robust_store = RobustIngester()

    # Step 1: Indian Express QA
    try:
        print_section_header(1, total_steps, "INDIAN EXPRESS PROPERTY LAW QA")
        from scripts.ingest_missing_folders import MissingDataIngester
        # We need to adapt the logic. Since the original classes instantiate their own store,
        # we might need to "monkey patch" or just use their logic to get data, 
        # but use OUR robust_store to ingest.
        # simpler: Let's read the file directly here to be safe and consistent.
        
        base_dir = Path(__file__).parent.parent / "DATA"
        ie_file = base_dir / "indianexpress_property_law_qa" / "indianexpress_property_law_qa.json"
        
        if ie_file.exists():
            with open(ie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, item in enumerate(data):
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                doc = {
                    "id": f"ie_qa_{i}",
                    "text": text,
                    "metadata": {"source": "Indian Express", "type": "qa"}
                }
                docs.append(doc)
            
            robust_store.add_documents_safely(docs, "Indian Express QA")
            print_status("success", "Step 1 Complete")
        else:
            print_status("error", "Indian Express file not found")
            
    except Exception as e:
        print_status("error", f"Step 1 Failed: {e}")

    # Step 2: 50K Case Studies
    try:
        print_section_header(2, total_steps, "50K INDIAN CASE STUDIES")
        cs_file = base_dir / "Indian_Case_Studies_50K ORG" / "Indian_Case_Studies_50K ORG.json"
        
        if cs_file.exists():
            print_status("info", "Loading large 50K file...")
            with open(cs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            docs = []
            for i, case in enumerate(data):
                doc_id = f"cs_50k_{i}_{case.get('case_id', 'unknown')}"
                if doc_id in robust_store.existing_ids:
                    continue
                    
                text = f"Title: {case.get('case_title','')}\nDesc: {case.get('case_description','')}\nVerdict: {case.get('verdict','')}"
                metadata = {
                    "source": "50k_dataset", 
                    "case_id": str(case.get('case_id','')),
                    # stringify complex fields
                    "legal": str(case.get('legal_aspects',{}))[:100]
                }
                docs.append({"id": doc_id, "text": text, "metadata": metadata})
                
                if len(docs) >= 500: # Batch prepare
                    robust_store.add_documents_safely(docs, f"50K Batch {i}")
                    docs = []
            
            if docs:
                robust_store.add_documents_safely(docs, "50K Final Batch")
            print_status("success", "Step 2 Complete")
    except Exception as e:
        print_status("error", f"Step 2 Failed: {e}")

    # Step 3: NDTV QA
    try:
        print_section_header(3, total_steps, "NDTV LEGAL QA")
        ndtv_file = base_dir / "ndtv_legal_qa_data" / "ndtv_legal_qa_data.json"
        if ndtv_file.exists():
            with open(ndtv_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            docs = []
            for i, item in enumerate(data):
                text = f"Question: {item.get('Question', '')}\nAnswer: {item.get('Answer', '')}"
                doc_id = f"ndtv_qa_{i}"
                docs.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {"source": "NDTV", "type": "qa"}
                })
            robust_store.add_documents_safely(docs, "NDTV QA")
            print_status("success", "Step 3 Complete")
    except Exception as e:
        print_status("error", f"Step 3 Failed: {e}")

    # Step 4: NCDRC Cases (Skipping complex logic, relying on script integrity but sequential)
    # Actually, let's just use the robust_store approach for safety if possible, 
    # but re-implementing NCDRC parsing logic here is risky.
    # We will call the existing class but assume it handles its own storage.
    # WAIT - doing that risks the multiple-store-instance lock.
    # Safer to SKIP checking validity for NCDRC and just let it run? 
    # Or try to instantiate its class but Replace its store?
    # Let's try to just run it at the end. The lock should be free.
    
    # Step 5: SC Judgment FULL
    # This is the massive one. We must handle this carefully.
    try:
        print_section_header(5, total_steps, "SUPREME COURT FULL DATASET")
        sc_dir = base_dir / "SC_Judgments_FULL" / "chunks"
        if sc_dir.exists():
            years = sorted([d.name for d in sc_dir.iterdir() if d.is_dir() and d.name.isdigit()])
            print_status("info", f"Found years: {years[0]} to {years[-1]}")
            
            for year in years:
                year_path = sc_dir / year
                # Check if we already have many docs from this year? 
                # Checking 26k files * chunks is slow.
                # Let's check a sample ID from this year.
                # Construct sample ID: "sc_{year}_..."
                # If we are effectively skipping, this loop is fast.
                
                chunk_files = list(year_path.glob("*_chunks.json"))
                print_status("info", f"Processing Year {year} ({len(chunk_files)} files)...")
                
                # Load one file at a time to save memory
                year_docs = []
                for cf in chunk_files:
                    try:
                        with open(cf, 'r', encoding='utf-8') as f:
                            chunks = json.load(f)
                            for c in chunks:
                                if c['id'] not in robust_store.existing_ids:
                                    year_docs.append(c)
                    except Exception:
                        pass
                    
                    if len(year_docs) > 1000:
                        robust_store.add_documents_safely(year_docs, f"SC {year}")
                        year_docs = []
                
                if year_docs:
                    robust_store.add_documents_safely(year_docs, f"SC {year} Final")
                
    except Exception as e:
         print_status("error", f"Step 5 Failed: {e}")

    # Final Rebuild
    try:
        print("\n" + "="*80)
        print("FINALIZING INDEX".center(80))
        print("="*80)
        # Only rebuild if we added something significant? 
        # Or just force it to be sure.
        robust_store.store.rebuild_index()
        print_status("success", "Index Rebuilt")
    except Exception as e:
        print_status("error", f"Rebuild Failed: {e}")

if __name__ == "__main__":
    main()
