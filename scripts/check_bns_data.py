"""Check what BNS-related data exists in ChromaDB and add missing facts."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

import chromadb

c = chromadb.PersistentClient(path="chroma_db_statutes")
col = c.get_collection("legal_db_statutes")

print(f"Total docs: {col.count()}")
print()

# Search for BNS metadata / chapters+sections info
queries = [
    "Bharatiya Nyaya Sanhita 2023 came into force 1 July 2024 chapters sections",
    "BNS 20 chapters 358 sections commencement date",
    "three new criminal laws replaced IPC CrPC Evidence Act 2024",
    "BNSS Bharatiya Nagarik Suraksha Sanhita BSA Bharatiya Sakshya",
]
for q in queries:
    r = col.query(query_texts=[q], n_results=3)
    print(f"Query: {q[:60]}...")
    for doc, meta in zip(r["documents"][0], r["metadatas"][0]):
        src = str(meta.get("source", "?"))[:60]
        print(f"  [{src}] {doc[:150].strip()}")
    print()
