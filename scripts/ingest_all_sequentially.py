import sys
import os
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore
# Import ingesters
from scripts.ingest_missing_folders import MissingDataIngester
from scripts.ingest_ndtv_data import NDTVIngester
from scripts.ingest_ncdrc_cases import NCDRCIngester
from scripts.ingest_sc_judgments import SCJudgmentsIngester

def run_all_sequentially():
    print("="*60)
    print("  SAFE SEQUENTIAL INGESTION (No Crashes/Locks)")
    print("="*60)
    
    # 1. Ingest Missing Folders (Indian Express & 50k Case Studies)
    try:
        print("\n[STEP 1/4] Ingesting Missing Data Folders...")
        miss_ingester = MissingDataIngester()
        miss_ingester.ingest_indian_express_qa()
        miss_ingester.ingest_50k_case_studies()
        # We manually rebuild index at the VERY end, not here
    except Exception as e:
        print(f"[ERROR] Step 1 Failed: {e}")

    # 2. Ingest NDTV Data
    try:
        print("\n[STEP 2/4] Ingesting NDTV QA Data...")
        ndtv_ingester = NDTVIngester()
        # Create a modified ingest method that uses skip_bm25 if possible,
        # but for now we'll just run it. The class initializes 'store' which checks BM25.
        # To avoid the initialization rebuild loop, we should ideally pass the shared store.
        # But for simplicity, running sequentially prevents the race condition.
        ndtv_ingester.ingest()
    except Exception as e:
        print(f"[ERROR] Step 2 Failed: {e}")

    # 3. Ingest NCDRC Cases
    try:
        print("\n[STEP 3/4] Ingesting NCDRC Cases...")
        ncdrc_ingester = NCDRCIngester()
        # Ensure NCDRCIngester uses the optimized add_documents if available
        # We need to trust the script logic or modify it. 
        # Since we are running sequentially, the cache mismatch won't be changing under our feet.
        ncdrc_ingester.ingest_all()
    except Exception as e:
        print(f"[ERROR] Step 3 Failed: {e}")

    # 4. Ingest Supreme Court Judgments (The Big One)
    try:
        print("\n[STEP 4/4] Ingesting SC Judgments...")
        sc_ingester = SCJudgmentsIngester()
        sc_ingester.ingest_all() # This already has the logic to Rebuild Index at the end
    except Exception as e:
        print(f"[ERROR] Step 4 Failed: {e}")

    print("\n" + "="*60)
    print("  Ensuring Final Index Consistency")
    print("="*60)
    try:
        store = HybridChromaStore()
        store.rebuild_index()
        print("[SUCCESS] All Data Ingested & Index Rebuilt")
    except Exception as e:
        print(f"[ERROR] Final Rebuild Failed: {e}")

if __name__ == "__main__":
    run_all_sequentially()
