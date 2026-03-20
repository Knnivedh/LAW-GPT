import os, sys
sys.path.append(os.getcwd())
from rag_system.core.milvus_store import CloudMilvusStore

print("--- Live Test on Zilliz Cloud ---")
store = CloudMilvusStore()
if store.is_connected:
    results = store.hybrid_search("What is the punishment for murder under IPC Section 302?", n_results=1)
    if results:
        for r in results:
            text = r.get("text", "")
            print(f'MATCH SCORE: {r.get("distance", "N/A")}')
            print(f'TEXT: {text}...')
    else:
        print("NO RESULTS")
else:
    print("Store not connected.")
