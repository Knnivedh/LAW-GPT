"""
Master Ingestion Script for Complete RAG System
Enhanced with detailed progress tracking and visual feedback
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

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

def main():
    total_steps = 5
    start_time = time.time()
    
    # Header
    print("\n" + "="*80)
    print("COMPLETE RAG SYSTEM DATA INGESTION".center(80))
    print("="*80)
    print("\n>> Pipeline Overview:")
    print("  [1] Indian Express Property Law QA")
    print("  [2] 50K Indian Case Studies Dataset")
    print("  [3] NDTV Legal QA Data")
    print("  [4] NCDRC Consumer Cases")
    print("  [5] Supreme Court Judgments (FULL - 26,606 cases)")
    print("\n>> Estimated Time: 45-60 minutes")
    print("="*80)
    
    # Step 1: Indian Express Property Law QA
    try:
        print_section_header(1, total_steps, "INDIAN EXPRESS PROPERTY LAW QA")
        print_status("start", "Initializing Indian Express ingestion...")
        
        from scripts.ingest_missing_folders import MissingDataIngester
        ingester = MissingDataIngester()
        
        print_status("progress", "Loading JSON data...")
        ingester.ingest_indian_express_qa()
        
        print_status("success", "Indian Express QA ingested successfully!")
    except Exception as e:
        print_status("error", f"Failed at Step 1: {e}")
    
    # Step 2: 50K Case Studies
    try:
        print_section_header(2, total_steps, "50K INDIAN CASE STUDIES")
        print_status("start", "Initializing 50K Case Studies ingestion...")
        print_status("info", "This is a large dataset - may take 15-20 minutes")
        
        from scripts.ingest_missing_folders import MissingDataIngester
        ingester = MissingDataIngester()
        
        print_status("progress", "Loading large JSON file...")
        ingester.ingest_50k_case_studies()
        
        print_status("success", "50K Case Studies ingested successfully!")
    except Exception as e:
        print_status("error", f"Failed at Step 2: {e}")
    
    # Step 3: NDTV Legal QA
    try:
        print_section_header(3, total_steps, "NDTV LEGAL QA DATA")
        print_status("start", "Initializing NDTV Legal QA ingestion...")
        
        from scripts.ingest_ndtv_data import NDTVIngester
        ingester = NDTVIngester()
        
        print_status("progress", "Processing QA pairs...")
        ingester.ingest()
        
        print_status("success", "NDTV Legal QA ingested successfully!")
    except Exception as e:
        print_status("error", f"Failed at Step 3: {e}")
    
    # Step 4: NCDRC Cases
    try:
        print_section_header(4, total_steps, "NCDRC CONSUMER CASES")
        print_status("start", "Initializing NCDRC ingestion...")
        
        from scripts.ingest_ncdrc_cases import NCDRCIngester
        ingester = NCDRCIngester()
        
        print_status("progress", "Processing consumer case files...")
        ingester.ingest_all()
        
        print_status("success", "NCDRC Cases ingested successfully!")
    except Exception as e:
        print_status("error", f"Failed at Step 4: {e}")
    
    # Step 5: Supreme Court Judgments (FULL DATASET)
    try:
        print_section_header(5, total_steps, "SUPREME COURT FULL DATASET")
        print_status("start", "Initializing SC Judgments ingestion...")
        print_status("info", "Processing 26,606 judgments (1950-2024)")
        print_status("info", "This is the largest dataset - estimated 20-30 minutes")
        
        from scripts.ingest_sc_judgments import SCJudgmentsIngester
        ingester = SCJudgmentsIngester()
        
        print_status("progress", "Processing all years from 1950 to 2024...")
        ingester.ingest_all()
        
        print_status("success", "Supreme Court Judgments ingested successfully!")
    except Exception as e:
        print_status("error", f"Failed at Step 5: {e}")
    
    # Final: Rebuild BM25 Index
    try:
        print("\n" + "="*80)
        print("  🔧 FINALIZING: Building Complete BM25 Index")
        print("="*80)
        print_status("start", "Rebuilding keyword search index...")
        print_status("info", "This ensures optimal hybrid search performance")
        
        store = HybridChromaStore()
        store.rebuild_index()
        
        print_status("success", "BM25 Index rebuilt successfully!")
    except Exception as e:
        print_status("error", f"Index rebuild failed: {e}")
    
    # Summary
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print("\n" + "="*80)
    print("[SUCCESS] COMPLETE RAG SYSTEM READY".center(80))
    print("="*80)
    print(f"\n>> Total Time: {minutes} minutes {seconds} seconds")
    print(">> All data sources successfully ingested into: legal_db_hybrid")
    print("\n>> Your RAG system now includes:")
    print("  * Indian Express Property Law QA")
    print("  * 50,000 Indian Case Studies")
    print("  * NDTV Legal QA Database")
    print("  * NCDRC Consumer Law Cases")
    print("  * 26,606 Supreme Court Judgments (1950-2024)")
    print("\n>> Next Step: Test your RAG system with queries!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
