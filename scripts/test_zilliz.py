import logging
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

sys.path.insert(0, str(Path(__file__).parent.parent))
import rag_config
from pymilvus import connections, utility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_zilliz_connection():
    print("="*50)
    print("ZILLIZ CLOUD CONNECTION TEST")
    print("="*50)
    print(f"Endpoint: {rag_config.ZILLIZ_CLUSTER_ENDPOINT}")
    
    try:
        connections.connect(
            alias="default",
            uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
            token=rag_config.ZILLIZ_TOKEN
        )
        print("SUCCESS: Connection Established!")
        
        collections = utility.list_collections()
        print(f"Existing Collections: {collections}")
        
        if 'legal_rag_cloud' in collections:
            from pymilvus import Collection
            collection = Collection('legal_rag_cloud')
            # For serverless, num_entities might be approximate or require flush
            print(f"Document Count in 'legal_rag_cloud': {collection.num_entities}")
        
        connections.disconnect("default")
        return True
    except Exception as e:
        print(f"FAILURE: Connection Failed: {e}")
        return False

if __name__ == "__main__":
    test_zilliz_connection()
