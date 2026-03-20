"""
ZILLIZ CLOUD UPLOADER - Upload ALL local legal data to Zilliz Cloud
Sources:
  1. chroma_db_statutes  (~4000 statutes docs)
  2. CONSUMER_DATA_COLLECTION JSON files  (~50K+ case law + QA docs)

Run with: python scripts/upload_to_zilliz_now.py
"""

import sys
import os
import json
import time
import hashlib
import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
BATCH_SIZE    = 32       # NVIDIA embedding API limit (safe)
PAUSE_EVERY   = 200      # pause after this many docs to respect rate limits
PAUSE_SECS    = 3        # seconds to pause
MAX_TEXT_LEN  = 8000     # truncate long docs to avoid token limits

# ── Helpers ────────────────────────────────────────────────────────────────────
def make_id(source: str, text: str) -> str:
    seed = f"{source}_{text[:400]}"
    return hashlib.md5(seed.encode("utf-8", errors="replace")).hexdigest()

def clean_text(t: str) -> str:
    t = re.sub(r'<[^>]+>', '', str(t))
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:MAX_TEXT_LEN]

# ── Stage 1: Read ChromaDB statutes ────────────────────────────────────────────
def read_statutes_chroma() -> Tuple[List[str], List[Dict], List[str]]:
    print("\n[1/2] Reading chroma_db_statutes ...")
    texts, metas, ids = [], [], []
    try:
        import chromadb
        db_path = str(PROJECT_ROOT / "chroma_db_statutes")
        client = chromadb.PersistentClient(path=db_path)
        for col_obj in client.list_collections():
            col = client.get_collection(col_obj.name)
            total = col.count()
            print(f"    Collection '{col_obj.name}': {total:,} docs")
            offset = 0
            while offset < total:
                batch = col.get(limit=500, offset=offset, include=["documents", "metadatas"])
                for doc, meta, doc_id in zip(
                    batch["documents"] or [],
                    batch["metadatas"] or [],
                    batch["ids"] or []
                ):
                    if not doc or len(doc.strip()) < 20:
                        continue
                    t = clean_text(doc)
                    texts.append(t)
                    metas.append({
                        "source": meta.get("source", col_obj.name) if meta else col_obj.name,
                        "title": str(meta.get("title", meta.get("act", doc_id)))[:300] if meta else doc_id,
                        "category": meta.get("category", "statute") if meta else "statute"
                    })
                    ids.append(doc_id)
                offset += 500
    except Exception as e:
        print(f"    [WARN] ChromaDB statutes read error: {e}")
    print(f"    => Loaded {len(texts):,} statute documents")
    return texts, metas, ids


# ── Stage 2: Read CONSUMER_DATA_COLLECTION JSON files ─────────────────────────
def read_json_data() -> Tuple[List[str], List[Dict], List[str]]:
    print("\n[2/2] Reading CONSUMER_DATA_COLLECTION JSON files ...")
    texts, metas, ids = [], [], []
    data_root = PROJECT_ROOT / "CONSUMER_DATA_COLLECTION"
    if not data_root.exists():
        print("    [WARN] CONSUMER_DATA_COLLECTION not found, skipping.")
        return texts, metas, ids

    json_files = sorted(data_root.rglob("*.json"), key=lambda x: x.stat().st_size, reverse=True)
    print(f"    Found {len(json_files)} JSON files")

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"    [SKIP] {fp.name}: {e}")
            continue

        items = raw if isinstance(raw, list) else (raw.get("documents") or raw.get("data") or [raw])
        source = fp.stem[:80]
        file_docs = 0

        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            # Extract text content from various formats
            text = (
                item.get("text") or
                item.get("content") or
                item.get("judgment_text") or
                item.get("summary") or
                item.get("facts") or  
                (f"Q: {item['query_text']}\nA: {item['response_text']}"
                 if "query_text" in item and "response_text" in item else None) or
                (f"Q: {item['question']}\nA: {item['answer']}"
                 if "question" in item and "answer" in item else None) or
                (f"Q: {item['Question']}\nA: {item['Answer']}"
                 if "Question" in item and "Answer" in item else None) or
                str(item)
            )

            if not text or len(str(text).strip()) < 40:
                continue

            t = clean_text(str(text))
            title = (item.get("title") or item.get("case_name") or
                     item.get("case_title") or item.get("query_title") or
                     f"{source}_{i}")

            doc_id = make_id(source, t)
            texts.append(t)
            metas.append({
                "source": source[:100],
                "title": str(title)[:300],
                "category": item.get("category", item.get("query_category", "case_law"))
            })
            ids.append(doc_id)
            file_docs += 1

        if file_docs:
            print(f"    {fp.name[:60]}: {file_docs:,} docs")

    print(f"    => Loaded {len(texts):,} case law / QA documents")
    return texts, metas, ids


# ── Stage 3: Upload to Zilliz in batches ──────────────────────────────────────
def upload_all(texts: List[str], metas: List[Dict], ids: List[str]):
    from rag_system.core.milvus_store import CloudMilvusStore

    print(f"\n[UPLOAD] Connecting to Zilliz Cloud ...")
    store = CloudMilvusStore()
    if not store.is_connected:
        print("❌ Cannot connect to Zilliz. Check rag_config.py credentials!")
        return

    existing = store.count()
    total = len(texts)
    print(f"    Zilliz current count: {existing:,}")
    print(f"    Documents to upload:  {total:,}")
    print()

    uploaded = 0
    errors   = 0

    for start in range(0, total, BATCH_SIZE):
        batch_t = texts[start:start + BATCH_SIZE]
        batch_m = metas[start:start + BATCH_SIZE]
        batch_i = ids[start:start + BATCH_SIZE]

        try:
            store.add(batch_t, batch_m, batch_i)
            uploaded += len(batch_t)
        except Exception as e:
            err_str = str(e)
            if "rate" in err_str.lower() or "429" in err_str:
                print(f"\n    [RATE LIMIT] Pausing 30s ...")
                time.sleep(30)
                try:
                    store.add(batch_t, batch_m, batch_i)
                    uploaded += len(batch_t)
                except Exception as e2:
                    print(f"    [SKIP] Retry failed: {e2}")
                    errors += len(batch_t)
            else:
                print(f"    [ERR] Batch {start}: {err_str[:100]}")
                errors += len(batch_t)

        # Progress line
        pct = (start + len(batch_t)) / total * 100
        print(f"\r    Progress: {uploaded:,}/{total:,} ({pct:.1f}%) | errors: {errors}", end="", flush=True)

        # Periodic pause to respect NVIDIA rate limit
        if uploaded > 0 and uploaded % PAUSE_EVERY == 0:
            time.sleep(PAUSE_SECS)

    final_count = store.count()
    print(f"\n\n{'='*60}")
    print(f"✅ UPLOAD COMPLETE")
    print(f"   Uploaded this session: {uploaded:,}")
    print(f"   Errors/skipped:        {errors:,}")
    print(f"   Zilliz final count:    {final_count:,}")
    print(f"{'='*60}\n")


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  ZILLIZ CLOUD DATA UPLOADER")
    print("=" * 60)

    all_texts, all_metas, all_ids = [], [], []

    # Load statutes from ChromaDB
    t1, m1, i1 = read_statutes_chroma()
    all_texts += t1; all_metas += m1; all_ids += i1

    # Load JSON data
    t2, m2, i2 = read_json_data()
    all_texts += t2; all_metas += m2; all_ids += i2

    # Deduplicate by ID
    seen = set()
    dedup_t, dedup_m, dedup_i = [], [], []
    for t, m, i in zip(all_texts, all_metas, all_ids):
        if i not in seen:
            seen.add(i)
            dedup_t.append(t); dedup_m.append(m); dedup_i.append(i)

    print(f"\n📊 Total unique documents to upload: {len(dedup_t):,}")
    print(f"   (removed {len(all_texts) - len(dedup_t):,} duplicates)\n")

    if not dedup_t:
        print("❌ No documents found to upload!")
        sys.exit(1)

    upload_all(dedup_t, dedup_m, dedup_i)
