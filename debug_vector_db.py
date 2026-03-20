import sys
from pathlib import Path
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    from rag_system.core.milvus_store import CloudMilvusStore
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def test_local_db():
    print("\n[TEST] 🏠 Testing Local HybridChromaStore...")
    try:
        store = HybridChromaStore()
        print(f"  > Initialized. Healthy? {store.is_vector_db_healthy}")
        print(f"  > Collection Info: {store.get_collection_info()}")
        
        results = store.hybrid_search("consumer protection", n_results=1)
        print(f"  > Search Result Count: {len(results)}")
    except Exception as e:
        print(f"  > ❌ FAILED: {e}")

def test_cloud_db():
    print("\n[TEST] ☁️ Testing CloudMilvusStore...")
    try:
        store = CloudMilvusStore()
        print(f"  > Connected? {store.is_connected}")
        print(f"  > Count: {store.count()}")
        
        results = store.hybrid_search("consumer protection", n_results=1)
        print(f"  > Search Result Count: {len(results)}")
    except Exception as e:
        print(f"  > ❌ FAILED: {e}")

if __name__ == "__main__":
    test_local_db()
    test_cloud_db()
