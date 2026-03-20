"""
REBUILD DATABASE WITH ALL 156K DOCUMENTS
Fixes: Kanoon.com grouping issue - loads each response separately
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore
from rag_system.core.data_loader_FULL import FullLegalDataLoader
import logging
import shutil
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def rebuild_database_156K():
    """
    Complete database rebuild with ALL 156K documents
    Kanoon.com: 102K responses loaded separately (not grouped)
    """
    print("="*80)
    print("COMPLETE DATABASE REBUILD - LOADING ALL 156K+ DOCUMENTS")
    print("="*80)
    print("\nFIXING: Kanoon.com grouping issue")
    print("  Old: 102K responses -> 2K grouped questions")
    print("  New: 102K responses -> 102K separate documents")
    print("\n" + "="*80)
    
    # Step 1: Backup existing database
    db_path = Path(__file__).parent / "chroma_db_hybrid"
    
    if db_path.exists():
        backup_path = Path(__file__).parent / "chroma_db_hybrid_backup"
        
        print(f"\n[STEP 1] Backing up existing database...")
        print(f"  From: {db_path}")
        print(f"  To: {backup_path}")
        
        if backup_path.exists():
            print(f"  Removing old backup...")
            shutil.rmtree(backup_path)
        
        shutil.copytree(db_path, backup_path)
        print("  OK Backup complete!")
        
        # Remove old database
        print(f"\n[STEP 2] Removing old database...")
        shutil.rmtree(db_path)
        print("  OK Old database removed")
    else:
        print("\n[STEP 1-2] No existing database found. Creating new one...")
    
    # Step 2: Load all data with FULL loader
    print(f"\n[STEP 3] Loading ALL legal domains (FULL MODE)...")
    
    data_dir = Path(__file__).parent / "DATA"
    loader = FullLegalDataLoader(data_dir=str(data_dir))
    
    start_load = time.time()
    all_documents = loader.load_all()
    load_time = time.time() - start_load
    
    print(f"\n OK Loaded {len(all_documents):,} total documents in {load_time:.1f}s")
    print("\nDomain breakdown:")
    for domain, count in loader.get_stats().items():
        print(f"  {domain}: {count:,} docs")
    
    # Step 3: Create new hybrid store
    print(f"\n[STEP 4] Creating new hybrid vector store...")
    
    vector_store = HybridChromaStore(
        persist_directory=str(db_path),
        collection_name="legal_db_hybrid",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Step 4: Add all documents
    print(f"\n[STEP 5] Adding {len(all_documents):,} documents to database...")
    print("  This will take some time...")
    print("  Estimated time: 30-40 minutes for 156K docs")
    print("  Progress will be shown below:")
    print()
    
    start_add = time.time()
    vector_store.add_documents(
        documents=all_documents,
        batch_size=100,
        show_progress=True
    )
    add_time = time.time() - start_add
    
    # Step 5: Verify
    print(f"\n[STEP 6] Verifying database...")
    
    doc_count = vector_store.count()
    
    print(f"\n{'='*80}")
    print("DATABASE REBUILD COMPLETE!")
    print(f"{'='*80}")
    print(f"Documents in database: {doc_count:,}")
    print(f"Expected documents: {len(all_documents):,}")
    
    if doc_count == len(all_documents):
        print("\n OK SUCCESS! All documents loaded correctly.")
        print(f"\n   Total time: {(load_time + add_time)/60:.1f} minutes")
        print(f"   Load time: {load_time:.1f}s")
        print(f"   Add time: {add_time/60:.1f} minutes")
    else:
        print(f"\n WARNING: Document count mismatch!")
        print(f"  Expected: {len(all_documents):,}")
        print(f"  Actual: {doc_count:,}")
        print(f"  Missing: {len(all_documents) - doc_count:,}")
    
    # Step 6: Test search
    print(f"\n[STEP 7] Testing hybrid search...")
    
    test_queries = [
        "What is IPC 302?",
        "Property inheritance laws",
        "How to file consumer complaint?"
    ]
    
    for query in test_queries:
        results = vector_store.hybrid_search(query, n_results=3)
        print(f"\nQuery: '{query}'")
        print(f"  Retrieved: {len(results)} documents")
        if results:
            print(f"  Top result from: {results[0].get('metadata', {}).get('domain', 'unknown')}")
    
    print(f"\n{'='*80}")
    print("ALL STEPS COMPLETE!")
    print(f"{'='*80}")
    print(f"\nDatabase location: {db_path}")
    if 'backup_path' in locals():
        print(f"Backup location: {backup_path}")
    
    print(f"\nYou can now use the enhanced RAG system with all {doc_count:,} documents!")
    print("\nTo use the new database:")
    print("  python scripts/multi_api_rag_improved.py")
    
    return vector_store


if __name__ == "__main__":
    start = time.time()
    
    try:
        vector_store = rebuild_database_156K()
        
        elapsed = time.time() - start
        
        print(f"\n Total rebuild time: {elapsed/60:.1f} minutes ({elapsed:.0f} seconds)")
        print("\n SUCCESS - Database ready for use!")
        
    except KeyboardInterrupt:
        print("\n\n X Rebuild interrupted by user!")
        print("The backup database is still available if needed.")
    except Exception as e:
        print(f"\n\n X ERROR during rebuild: {e}")
        import traceback
        traceback.print_exc()
        print("\nThe backup database is still available if needed.")

