"""
PHASE 1: Vector Database Audit Script
Connects to chroma_db_hybrid and reports document counts per collection,
verifies BM25 index consistency, and summarizes what is indexed.
"""

import sys
import os
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_OK = True
except ImportError:
    CHROMA_OK = False
    print("[ERROR] chromadb not installed. Run: pip install chromadb")

import pickle
import logging

logging.basicConfig(level=logging.WARNING)


def audit_collection(persist_dir: str, collection_name: str) -> dict:
    """Audit a single Chroma collection."""
    result = {
        "path": persist_dir,
        "collection": collection_name,
        "chroma_count": 0,
        "bm25_count": 0,
        "sqlite_size_mb": 0,
        "bm25_cache_exists": False,
        "consistent": False,
        "error": None,
    }

    db_path = Path(persist_dir)
    sqlite_file = db_path / "chroma.sqlite3"

    if sqlite_file.exists():
        result["sqlite_size_mb"] = round(sqlite_file.stat().st_size / (1024 * 1024), 2)

    # Check BM25 cache
    bm25_cache = db_path / f"{collection_name}_bm25.pkl"
    if bm25_cache.exists():
        result["bm25_cache_exists"] = True
        try:
            with open(bm25_cache, "rb") as f:
                bm25_data = pickle.load(f)
                result["bm25_count"] = len(bm25_data.get("documents", []))
        except Exception as e:
            result["error"] = f"BM25 load error: {e}"

    if not CHROMA_OK:
        result["error"] = "chromadb not available"
        return result

    try:
        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        col = client.get_collection(collection_name)
        result["chroma_count"] = col.count()
        result["consistent"] = (result["chroma_count"] == result["bm25_count"])
    except Exception as e:
        result["error"] = str(e)

    return result


def audit_all():
    """Run audit on all known vector stores."""
    collections = [
        (str(PROJECT_ROOT / "chroma_db_hybrid"), "legal_db_hybrid"),
        (str(PROJECT_ROOT / "chroma_db_statutes"), "legal_db_statutes"),
        # deployment copy
        (str(PROJECT_ROOT / "deployment_bundle" / "kaanoon_test" / "chroma_db_hybrid"), "legal_db_hybrid"),
    ]

    print("\n" + "=" * 70)
    print("LAW-GPT VECTOR DATABASE AUDIT REPORT")
    print("=" * 70)

    total_docs = 0
    for persist_dir, col_name in collections:
        if not Path(persist_dir).exists():
            print(f"\n[SKIP] {persist_dir} — directory not found")
            continue

        r = audit_collection(persist_dir, col_name)
        print(f"\nCollection : {r['collection']}")
        print(f"Path       : {r['path']}")
        print(f"SQLite     : {r['sqlite_size_mb']} MB")
        print(f"Chroma docs: {r['chroma_count']:,}")
        print(f"BM25 docs  : {r['bm25_count']:,}")
        print(f"BM25 cache : {'YES' if r['bm25_cache_exists'] else 'NO'}")
        print(f"Consistent : {'YES' if r['consistent'] else 'NO  <-- REBUILD NEEDED'}")
        if r["error"]:
            print(f"Error      : {r['error']}")
        total_docs += r["chroma_count"]

    print("\n" + "=" * 70)
    print(f"TOTAL INDEXED DOCUMENTS: {total_docs:,}")
    print("=" * 70)

    # Check data source files
    print("\nDATA SOURCE FILE CHECK:")
    data_dir = PROJECT_ROOT / "DATA"
    sources = [
        ("case_studies", "Indian_Case_Studies_50K ORG/Indian_Case_Studies_50K ORG.json"),
        ("kanoon", "kanoon.com/kanoon.com/kanoon_data.json"),
        ("indian_express", "indianexpress_property_law_qa/indianexpress_property_law_qa.json"),
        ("legallyin", "legallyin.com/legallyin.com.json"),
        ("ndtv", "ndtv_legal_qa_data/ndtv_legal_qa_data.json"),
        ("hindu", "thehindu/thehindu.json"),
        ("wikipedia", "wikipedia.org/wikipedia.org.json"),
        ("statutes", "Statutes/json"),
    ]
    for name, rel_path in sources:
        full = data_dir / rel_path
        exists = "FOUND" if full.exists() else "MISSING"
        size = ""
        if full.exists() and full.is_file():
            size = f"  ({round(full.stat().st_size / 1024 / 1024, 1)} MB)"
        print(f"  {exists:8s}  {name:20s}  {rel_path}{size}")

    # Check CONSUMER_DATA_COLLECTION
    consumer_dir = PROJECT_ROOT / "CONSUMER_DATA_COLLECTION"
    if consumer_dir.exists():
        files = list(consumer_dir.glob("*.json"))
        print(f"\n  CONSUMER_DATA_COLLECTION: {len(files)} JSON files")
    else:
        print(f"\n  CONSUMER_DATA_COLLECTION: NOT FOUND at {consumer_dir}")

    # Check SC_Judgments
    sc_dir = PROJECT_ROOT / "SC_Judgments_FULL"
    if sc_dir.exists():
        files = list(sc_dir.glob("**/*.json"))
        print(f"  SC_Judgments_FULL: {len(files)} JSON files")
    else:
        print(f"  SC_Judgments_FULL: NOT FOUND at {sc_dir}")

    print()


if __name__ == "__main__":
    audit_all()
