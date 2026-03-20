"""
PHASE 1: Index Completeness Verification Script
Verifies all data sources are indexed by spot-checking domain-specific queries
against the ChromaDB and reporting which domains have coverage.
"""

import sys
import os
from pathlib import Path
import json
import logging

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.WARNING)

# Spot-check queries per domain
DOMAIN_PROBES = {
    "case_studies": ["murder case IPC 302", "criminal case accused convicted"],
    "kanoon": ["section 138 cheque dishonour", "maintenance under Section 125"],
    "indian_express": ["property registration stamp duty", "sale deed property transfer"],
    "legallyin": ["company incorporation directors", "corporate compliance board"],
    "ndtv": ["supreme court judgment ruling", "high court order verdict"],
    "hindu": ["constitutional amendment article", "parliament legislation"],
    "wikipedia": ["Indian Penal Code overview", "civil procedure code"],
    "statutes": ["section 302 punishment", "Indian Evidence Act"],
}


def probe_domain(col, domain: str, queries: list, top_k: int = 3) -> dict:
    """Search for domain-specific content and verify metadata matches."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        return {"domain": domain, "found": False, "error": str(e), "hits": 0}

    hits = 0
    for q in queries:
        try:
            emb = model.encode([q]).tolist()
            results = col.query(
                query_embeddings=emb,
                n_results=top_k,
                include=["metadatas"],
            )
            if results and results["metadatas"]:
                for meta in results["metadatas"][0]:
                    if meta and meta.get("domain", "").lower() in domain.lower():
                        hits += 1
                        break
        except Exception:
            pass

    return {
        "domain": domain,
        "queries_tested": len(queries),
        "domain_hits": hits,
        "found": hits > 0,
    }


def verify_completeness():
    """Verify each data domain has coverage in the vector store."""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("[ERROR] chromadb not installed.")
        return

    persist_dir = PROJECT_ROOT / "chroma_db_hybrid"
    if not persist_dir.exists():
        print(f"[ERROR] chroma_db_hybrid not found at {persist_dir}")
        return

    print("\n" + "=" * 70)
    print("LAW-GPT INDEX COMPLETENESS VERIFICATION")
    print("=" * 70)

    try:
        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        col = client.get_collection("legal_db_hybrid")
        total = col.count()
        print(f"Total documents in legal_db_hybrid: {total:,}\n")
    except Exception as e:
        print(f"[ERROR] Could not connect to ChromaDB: {e}")
        return

    print("Domain Coverage (spot-check via semantic search):")
    print("-" * 50)

    all_found = True
    for domain, queries in DOMAIN_PROBES.items():
        r = probe_domain(col, domain, queries)
        status = "COVERED" if r["found"] else "MISSING"
        if not r["found"]:
            all_found = False
        err = f"  ERROR: {r.get('error', '')}" if r.get("error") else ""
        print(f"  {status:8s}  {domain:20s}  (hits: {r.get('domain_hits', 0)}/{r['queries_tested']}){err}")

    print("-" * 50)
    if all_found:
        print("\nRESULT: All domains are covered in the vector index!")
    else:
        print("\nRESULT: Some domains are MISSING. Run data_loader_FULL.py to re-index.")

    # Quick count by domain via metadata filter
    print("\nDocument count by domain (from BM25 cache):")
    import pickle
    bm25_cache = persist_dir / "legal_db_hybrid_bm25.pkl"
    if bm25_cache.exists():
        try:
            with open(bm25_cache, "rb") as f:
                data = pickle.load(f)
            metas = data.get("metadatas", [])
            domain_counts: dict = {}
            for m in metas:
                d = m.get("domain", "unknown") if m else "unknown"
                domain_counts[d] = domain_counts.get(d, 0) + 1
            for domain, cnt in sorted(domain_counts.items(), key=lambda x: -x[1]):
                print(f"  {domain:25s}: {cnt:,}")
        except Exception as e:
            print(f"  Could not read BM25 cache: {e}")
    else:
        print("  BM25 cache not found — run rebuild_index() on HybridChromaStore")

    print()


if __name__ == "__main__":
    verify_completeness()
