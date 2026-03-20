"""
ULTRA CLOUD UPLOAD - MAXIMUM SPEED (100% POWER)
Uses multi-threading, GPU mega-batching, and parallel network streams.
"""

import os
import sys
import json
import logging
from pathlib import Path
from tqdm import tqdm
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

from rag_system.core.milvus_store import CloudMilvusStore

# Minimal logging for maximum speed
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class UltraParallelUploader:
    def __init__(self, num_workers=6, batch_size=1000):
        self.cloud_store = CloudMilvusStore()
        self.data_root = PROJECT_ROOT / "DATA"
        self.uploaded_count = 0
        self.skipped_count = 0
        self.lock = threading.Lock()
        
        # Performance Settings
        self.num_workers = num_workers
        self.batch_size = batch_size
        
        # Data integrity tracking
        self.processed_files = set()
        
    def generate_id(self, source, content):
        """Stable unique ID per document"""
        hash_seed = f"{source}_{content[:500]}"
        return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()

    def process_and_upload_batch(self, texts, metadatas, ids):
        """Worker function for parallel upload"""
        if not texts:
            return 0
            
        try:
            # The GPU embedding happens here (inside add)
            self.cloud_store.add(texts, metadatas, ids)
            
            with self.lock:
                self.uploaded_count += len(ids)
            return len(ids)
        except Exception as e:
            logger.error(f"Batch upload failed: {e}")
            with self.lock:
                self.skipped_count += len(texts)
            return 0

    def process_single_file(self, file_path: Path):
        """Extracts data from one file and prepares it for batching"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            source = file_path.parent.name
            file_texts, file_metadatas, file_ids = [], [], []
            
            # Detect list or dict
            items = data if isinstance(data, list) else [data]
            
            for i, entry in enumerate(items):
                if not isinstance(entry, dict):
                    continue
                
                content = (entry.get('text') or entry.get('content') or 
                          entry.get('response_text') or entry.get('query_text') or str(entry))
                
                if len(str(content)) < 50:
                    continue
                    
                doc_id = self.generate_id(source, str(content))
                title = entry.get('title') or entry.get('case_name') or f"{file_path.stem}_{i}"
                
                file_texts.append(str(content))
                file_metadatas.append({
                    "source": source,
                    "title": str(title)[:300],
                    "file": file_path.name
                })
                file_ids.append(doc_id)
                
            return file_texts, file_metadatas, file_ids
        except Exception:
            return [], [], []

    def run(self):
        print("\n" + "="*80)
        print("🔥 ULTRA PARALLEL LOADER - INITIALIZING (100% POWER MODE)")
        print("="*80)
        
        if not self.cloud_store.is_connected:
            print("❌ Initial connection failed. Check your rag_config.py")
            return

        # 1. Discover all files
        all_json = list(self.data_root.glob("**/*.json"))
        # Sort by size (big files first to keep GPU busy)
        all_json.sort(key=lambda x: x.stat().st_size, reverse=True)
        
        print(f"Target: {len(all_json):,} JSON files")
        print(f"Parallel Workers: {self.num_workers}")
        print(f"Sync Batch Size: {self.batch_size}")
        print(f"Initial Cloud Count: {self.cloud_store.count():,}")
        
        current_texts, current_metadatas, current_ids = [], [], []
        
        # 2. Parallel Pipeline
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            pbar = tqdm(total=len(all_json), desc="[ULTRA SYNC]", unit="file")
            
            # Start the main loop
            for file_path in all_json:
                texts, metas, ids = self.process_single_file(file_path)
                
                current_texts.extend(texts)
                current_metadatas.extend(metas)
                current_ids.extend(ids)
                
                # If we have enough for a Mega-Batch, send it to a worker thread
                while len(current_texts) >= self.batch_size:
                    batch_texts = current_texts[:self.batch_size]
                    batch_metas = current_metadatas[:self.batch_size]
                    batch_ids = current_ids[:self.batch_size]
                    
                    # Offload to worker
                    executor.submit(self.process_and_upload_batch, batch_texts, batch_metas, batch_ids)
                    
                    current_texts = current_texts[self.batch_size:]
                    current_metadatas = current_metadatas[self.batch_size:]
                    current_ids = current_ids[self.batch_size:]
                
                pbar.update(1)
                
            # Final cleanup batch
            if current_texts:
                executor.submit(self.process_and_upload_batch, current_texts, current_metadatas, current_ids)
                
            pbar.close()

        print("\n" + "="*80)
        print("📊 ULTRA MISSION COMPLETE")
        print("="*80)
        print(f"Documents Ingested this session: {self.uploaded_count:,}")
        print(f"Documents Skipped/Errors: {self.skipped_count:,}")
        print(f"Final Count on Zilliz: {self.cloud_store.count():,}")
        print("="*80)

if __name__ == "__main__":
    # 6 workers, 1000 batch size is usually sweet spot for high-power desktops
    uploader = UltraParallelUploader(num_workers=8, batch_size=1000)
    uploader.run()
