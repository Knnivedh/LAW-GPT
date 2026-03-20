import sys
from pathlib import Path
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChromaDebug")

# Add project root
file_path = Path(__file__).resolve()
PROJECT_ROOT = file_path.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def test_db_init():
    logger.info("--- Starting ChromaDB Isolation Test ---")
    try:
        logger.info("Initializing HybridChromaStore...")
        store = HybridChromaStore(
            persist_directory="chroma_db_hybrid",
            collection_name="legal_db_hybrid"
        )
        logger.info("Store initialized.")
        
        logger.info("Attempting store.count()...")
        count = store.count()
        logger.info(f"Count result: {count}")
        
    except Exception as e:
        logger.error(f"Captured Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_db_init()
