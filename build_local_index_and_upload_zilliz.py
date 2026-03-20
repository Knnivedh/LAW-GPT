"""
LOCAL JSON INDEX BUILDER + ZILLIZ CLOUD UPLOADER
=================================================
This script does TWO things:

1. Reads ALL statute .txt files from BACKUP_DATA/DATA/Statutes/
   and chunks them into a comprehensive local JSON index file
   (local_statute_index.json) - your PERMANENT local knowledge base.

2. Uploads every chunk to Zilliz Cloud (Milvus) using NVIDIA embeddings
   so the RAG system can perform vector search on real legal data.

Usage:
    py build_local_index_and_upload_zilliz.py
    py build_local_index_and_upload_zilliz.py --index-only    # skip Zilliz upload
    py build_local_index_and_upload_zilliz.py --upload-only   # skip re-indexing
"""

from __future__ import annotations

import argparse
import json
import hashlib
import logging
import os
import re
import sys
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
STATUTES_DIR = ROOT.parent.parent / "BACKUP_DATA" / "DATA" / "Statutes"
LOCAL_INDEX_PATH = ROOT / "local_statute_index.json"
QA_FILES = [
    ROOT / "kaanoon_test" / "kaanoon_qa_dataset.json",
    ROOT / "kaanoon_test" / "kaanoon_qa_expanded.json",
    ROOT / "kaanoon_test" / "kaanoon_qa_dataset_cleaned.json",
    ROOT / "kaanoon_test" / "landmark_cases_database.json",
    ROOT / "kaanoon_test" / "gst_it_professionals_2024.json",
    # ── HUGE DATASETS ──
    ROOT.parent.parent / "BACKUP_DATA" / "DATA" / "kanoon_data.json",
    ROOT.parent.parent / "BACKUP_DATA" / "DATA" / "Indian_Case_Studies_50K ORG.json",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("index_builder")

# ── STEP 1: Build Local JSON Index ────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    chunks = []
    # First try splitting by sections (e.g., "Section 302.")
    section_pattern = re.compile(r'\n(?=Section \d+)', re.IGNORECASE)
    sections = section_pattern.split(text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            # Sub-chunk long sections by character limit with overlap
            start = 0
            while start < len(section):
                end = start + chunk_size
                chunk = section[start:end]
                chunks.append(chunk.strip())
                start += chunk_size - overlap

    return [c for c in chunks if len(c) > 50]  # Filter out tiny fragments
def get_chunks_stream():
    """Generator that yields chunks from all sources (Statutes + QA) one by one."""
    
    # ── 1. Statute Text Files ──
    if STATUTES_DIR.exists():
        txt_files = sorted(STATUTES_DIR.glob("*.txt"))
        logger.info(f"Indexing {len(txt_files)} statute files...")
        for fpath in txt_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                statute_name = fpath.stem.replace("_", " ")
                chunks = chunk_text(text)
                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(f"{fpath.stem}_{i}".encode()).hexdigest()[:16]
                    yield {
                        "id": f"statute_{doc_id}",
                        "text": chunk,
                        "metadata": {
                            "source": fpath.name,
                            "type": "statute",
                            "act_name": statute_name,
                            "chunk_index": i
                        }
                    }
            except Exception as e:
                logger.error(f"Error processing {fpath.name}: {e}")

    # ── 2. Massive JSON Datasets ──
    for qa_path in QA_FILES:
        if not qa_path.exists():
            continue
        logger.info(f"Streaming large dataset: {qa_path.name}")
        try:
            with open(qa_path, "r", encoding="utf-8") as f:
                data = json.load(f) # Note: For true RAM-safety, use ijson
                if isinstance(data, list):
                    for j, item in enumerate(data):
                        # Extract question/answer or general text
                        q = item.get("question", item.get("Q", ""))
                        a = item.get("answer", item.get("A", ""))
                        if not q and not a:
                            # Fallback to key-value pairs if not Q&A
                            content = " | ".join([f"{k}: {v}" for k, v in item.items() if isinstance(v, str)])
                        else:
                            content = f"Q: {q}\nA: {a}" if q and a else (q or a)
                        
                        if not content: continue
                        
                        doc_id = hashlib.md5(f"qa_{qa_path.stem}_{j}".encode()).hexdigest()[:16]
                        yield {
                            "id": f"qa_{doc_id}",
                            "text": content[:65000], # Milvus limit
                            "metadata": {
                                "source": qa_path.name,
                                "type": "qa",
                                "index": j
                            }
                        }
        except Exception as e:
            logger.error(f"Error streaming {qa_path.name}: {e}")

def upload_in_batches(batch_size=100):
    """Orchestrates the streaming upload to Zilliz Cloud."""
    logger.info("=" * 60)
    logger.info(f"POWER-RAG UPGRADE: Starting Streaming Ingestion")
    logger.info("=" * 60)

    # Ensure we can import milvus_store
    sys.path.insert(0, str(ROOT))
    try:
        from rag_system.core.milvus_store import CloudMilvusStore
    except ImportError:
        logger.error("CloudMilvusStore not found.")
        return

    store = CloudMilvusStore()
    if not store.is_connected:
        logger.error("Cloud connection failed.")
        return

    batch = []
    total_uploaded = 0

    for chunk in get_chunks_stream():
        batch.append(chunk)
        
        if len(batch) >= batch_size:
            ids = [c["id"] for c in batch]
            texts = [c["text"] for c in batch]
            metadatas = [c["metadata"] for c in batch]
            
            try:
                store.add(documents=texts, metadatas=metadatas, ids=ids)
                total_uploaded += len(batch)
                logger.info(f"🛰️ Progress: {total_uploaded} chunks uploaded...")
            except Exception as e:
                logger.error(f"Batch failed: {e}")
            
            batch = []
            time.sleep(0.05) # Prevent API saturation

    # Final batch
    if batch:
        try:
            store.add(
                documents=[c["text"] for c in batch],
                metadatas=[c["metadata"] for c in batch],
                ids=[c["id"] for c in batch]
            )
            total_uploaded += len(batch)
        except Exception as e:
            logger.error(f"Final batch failed: {e}")

    logger.info(f"✅ SUCCESS: {total_uploaded} total chunks are now LIVE in Zilliz Cloud.")

if __name__ == "__main__":
    upload_in_batches(batch_size=100)
