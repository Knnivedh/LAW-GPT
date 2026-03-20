from pymilvus import connections, Collection
import sys
import os

# Internal imports assuming standard path
sys.path.append(os.getcwd())
import rag_config

def check():
    connections.connect(
        alias="default",
        uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
        token=rag_config.ZILLIZ_TOKEN
    )
    
    collection = Collection(rag_config.ZILLIZ_COLLECTION_NAME)
    collection.flush()
    print(f"Collection: {rag_config.ZILLIZ_COLLECTION_NAME}")
    print(f"Total Entities: {collection.num_entities}")

if __name__ == "__main__":
    check()
