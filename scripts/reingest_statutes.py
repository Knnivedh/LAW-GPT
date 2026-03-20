"""
Re-Ingest Statutes with Structure-Aware Chunking
=================================================

This script:
1. Loads all statute JSON files using the new StatuteSectionChunker
2. Upserts the structured statute chunks into the LIVE Zilliz Cloud collection
   (legal_rag_cloud) using NVIDIA 2048D embeddings — matching the production schema
3. Produces ~3900+ properly structured chunks with rich metadata

IMPORTANT: Uploads to `legal_rag_cloud` (same collection the live backend queries).
           Does NOT drop existing data — only upserts statute records (IDs start with D8_).

Usage:
    python scripts/reingest_statutes.py [--dry-run] [--statutes-dir PATH]
    
    --dry-run        Show what would be uploaded without actually uploading
    --statutes-dir   Override the statute JSON directory path
"""

import sys
import os
import time
import logging
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from rag_system.core.statute_chunker import process_all_statutes

# Import cloud store — uses same NVIDIA embeddings + collection as live backend
try:
    from rag_config import (
        ZILLIZ_CLUSTER_ENDPOINT, ZILLIZ_TOKEN,
        ZILLIZ_COLLECTION_NAME, CLOUD_MODE_ENABLED
    )
    STATUTES_COLLECTION = ZILLIZ_COLLECTION_NAME  # Upload to the SAME collection live backend reads
except ImportError:
    print("ERROR: Cannot import rag_config. Run from project root.")
    sys.exit(1)


def find_statutes_dir() -> Path:
    """Find the statutes JSON directory."""
    candidates = [
        PROJECT_ROOT / "DATA" / "Statutes" / "json",
        Path(str(Path(__file__).resolve().parent / 'BACKUP_DATA'\DATA\Statutes\json"),
    ]
    for d in candidates:
        if d.exists():
            return d
    raise FileNotFoundError("Could not find statutes JSON directory")


def upload_to_zilliz(records: list, batch_size: int = 16, pause_every: int = 100):
    """
    Upload statute records to the live Zilliz Cloud collection using CloudMilvusStore.
    Uses NVIDIA 2048D embeddings to match existing production vectors.
    """
    # Use the production CloudMilvusStore — handles NVIDIA embeddings automatically
    from rag_system.core.milvus_store import CloudMilvusStore

    print(f"\nConnecting to Zilliz Cloud: {ZILLIZ_CLUSTER_ENDPOINT}")
    print(f"Collection: {STATUTES_COLLECTION} (production collection)")

    store = CloudMilvusStore(
        endpoint=ZILLIZ_CLUSTER_ENDPOINT,
        token=ZILLIZ_TOKEN,
        collection_name=STATUTES_COLLECTION
    )

    if not store.is_connected:
        print("ERROR: Could not connect to Zilliz Cloud. Check credentials.")
        sys.exit(1)

    existing_count = store.count()
    print(f"Collection currently has {existing_count:,} documents")
    print(f"Uploading {len(records)} statute chunks (upsert — existing data safe)\n")

    total_uploaded = 0
    failed = 0

    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]

        texts = [r['text'] for r in batch]
        ids   = [r['id']   for r in batch]
        # Build metadata dicts — CloudMilvusStore stores these as JSON
        metas = [{
            'domain': 'statutes',
            'act': r['metadata'].get('act', ''),
            'section_number': r['metadata'].get('section_number', ''),
            'section_title':  r['metadata'].get('section_title', ''),
            'chapter':        r['metadata'].get('chapter', ''),
            'source_file':    r['metadata'].get('source_file', ''),
        } for r in batch]

        try:
            store.add(documents=texts, metadatas=metas, ids=ids)
            total_uploaded += len(batch)
        except Exception as e:
            logger.error(f"  Batch {start}-{start+len(batch)} failed: {e}")
            failed += len(batch)

        # Progress display
        pct = total_uploaded / len(records) * 100
        print(f"  Progress: {total_uploaded}/{len(records)} ({pct:.1f}%)", end="\r")

        # Rate-limit pause every N records (NVIDIA API has limits)
        if total_uploaded > 0 and total_uploaded % pause_every < batch_size:
            time.sleep(3)

    print(f"\n\nUpload complete!")
    print(f"  Uploaded : {total_uploaded}")
    print(f"  Failed   : {failed}")
    print(f"  Collection total: {store.count():,} documents")
    return total_uploaded


def main():
    parser = argparse.ArgumentParser(description="Re-ingest statutes with structure-aware chunking")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without uploading")
    parser.add_argument("--statutes-dir", type=str, help="Override statute JSON directory")
    args = parser.parse_args()

    print("=" * 60)
    print("STATUTE RE-INGESTION WITH STRUCTURE-AWARE CHUNKING")
    print(f"Target collection : {ZILLIZ_COLLECTION_NAME}")
    print(f"Embedding model   : NVIDIA llama-3.2-nv-embedqa-1b-v2 (2048D)")
    print("=" * 60)

    # Find statutes directory
    if args.statutes_dir:
        statutes_dir = Path(args.statutes_dir)
    else:
        statutes_dir = find_statutes_dir()

    print(f"\nStatutes directory: {statutes_dir}")

    # Process all statutes
    print("\nProcessing statutes with StatuteSectionChunker...")
    records = process_all_statutes(statutes_dir, max_chunk_chars=3000)

    if not records:
        print("ERROR: No records produced!")
        sys.exit(1)

    # Print summary
    from collections import Counter
    act_counts = Counter(r['metadata']['act'] for r in records)

    print(f"\nTotal chunks      : {len(records)}")
    print(f"Unique acts       : {len(act_counts)}")

    sizes = [len(r['text']) for r in records]
    print(f"Chunk sizes       : min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}")

    print(f"\nTop 10 acts by chunk count:")
    for act, count in act_counts.most_common(10):
        print(f"  {act}: {count} chunks")

    if args.dry_run:
        print("\n[DRY RUN] Skipping upload. Remove --dry-run to upload to Zilliz.")
        print(f"\nSample chunks:")
        for r in records[:3]:
            print(f"\n--- {r['id']} ---")
            print(f"Act    : {r['metadata']['act']}")
            print(f"Section: {r['metadata']['section_number']} - {r['metadata']['section_title']}")
            print(f"Preview: {r['text'][:200]}...")
        return

    # Upload to Zilliz
    if not CLOUD_MODE_ENABLED:
        print("\nCLOUD_MODE_ENABLED is False in rag_config.py. Skipping upload.")
        return

    uploaded = upload_to_zilliz(records)

    print(f"\n{'='*60}")
    print(f"RE-INGESTION COMPLETE: {uploaded} statute chunks added to '{ZILLIZ_COLLECTION_NAME}'")
    print("The live backend will now retrieve properly structured statute sections.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()


# ========== LEGACY partial stubs below (kept for schema reference only) ==========

def _legacy_fields_reference():
    """NOT used — kept only for documentation of old schema."""
    from pymilvus import DataType, FieldSchema
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
        FieldSchema(name="act", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="section_number", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="section_title", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="chapter", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="domain", dtype=DataType.VARCHAR, max_length=64),
    ]
    pass  # End of legacy reference stub
