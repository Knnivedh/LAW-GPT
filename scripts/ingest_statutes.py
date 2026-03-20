import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.core.data_loader_FULL import FullLegalDataLoader
from rag_system.core.hybrid_chroma_store import HybridChromaStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_statutes():
    """
    Ingest ONLY Domain 8: Statutes
    """
    print("="*60)
    print("INGESTING GOVERNMENT STATUTES (RULE BOOKS)")
    print("="*60)
    
    # 1. Load Data
    loader = FullLegalDataLoader()
    statutes = loader.load_domain_8_statutes()
    
    if not statutes:
        print("No statutes found! Please ensure text files are in DATA/Statutes/")
        return
        
    print(f"Found {len(statutes)} statute records to ingest.")
    
    # 2. Initialize Store
    store = HybridChromaStore(
        persist_directory="chroma_db_hybrid",
        collection_name="legal_db_hybrid"
    )
    
    # 3. Add to Database
    store.add_documents(statutes)
    
    print("="*60)
    print("SUCCESS: Statutes ingested successfully!")
    print("="*60)

if __name__ == "__main__":
    ingest_statutes()
