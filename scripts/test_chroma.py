"""Minimal test to diagnose ChromaDB crash"""
import sys
print("=== TEST START ===", flush=True)

try:
    print("Importing chromadb...", flush=True)
    import chromadb
    print("Import OK", flush=True)
except Exception as e:
    print(f"Import FAILED: {e}", flush=True)
    sys.exit(1)

try:
    print("Creating PersistentClient...", flush=True)
    client = chromadb.PersistentClient(path="chroma_db_hybrid")
    print("Client OK", flush=True)
except Exception as e:
    print(f"Client FAILED: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("Getting collection...", flush=True)
    coll = client.get_collection("legal_db_hybrid")
    print(f"Collection OK: {coll.count()} docs", flush=True)
except Exception as e:
    print(f"Collection FAILED: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=== TEST COMPLETE ===", flush=True)
