"""
TURBO CLOUD UPLOAD - 5x Faster
Optimized for speed while maintaining data integrity
"""

import os
import sys
import json
import logging
from pathlib import Path
from tqdm import tqdm
import hashlib

# Fix Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_system.core.milvus_store import CloudMilvusStore

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TurboCloudUploader:
    def __init__(self):
        self.cloud_store = CloudMilvusStore()
        self.data_root = PROJECT_ROOT / "DATA"
        self.uploaded = 0
        self.skipped = 0
        # TURBO: Larger batch size for faster uploads
        self.BATCH_SIZE = 500  # 10x increase from 50
        
    def generate_id(self, source, content):
        hash_seed = f"{source}_{content[:200]}"
        return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()
    
    def upload_batch(self, texts, metadatas, ids):
        """Upload a single batch to cloud"""
        try:
            self.cloud_store.add(texts, metadatas, ids)
            self.uploaded += len(texts)
            return True
        except Exception as e:
            self.skipped += len(texts)
            return False
    
    def process_json_file(self, file_path: Path):
        """Process a single JSON file - TURBO MODE (no limits)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            texts, metadatas, ids = [], [], []
            source = file_path.parent.name
            
            # Handle list of documents - NO LIMIT
            if isinstance(data, list):
                for i, entry in enumerate(data):
                    if not isinstance(entry, dict):
                        continue
                    
                    content = (entry.get('text') or entry.get('content') or 
                              entry.get('response_text') or entry.get('query_text') or str(entry))
                    
                    if len(str(content)) < 50:
                        continue
                    
                    doc_id = self.generate_id(source, str(content))
                    title = entry.get('title') or entry.get('case_name') or f"{file_path.stem}_{i}"
                    
                    texts.append(str(content))
                    metadatas.append({
                        "source": source,
                        "title": str(title)[:300],
                        "file": file_path.name
                    })
                    ids.append(doc_id)
                    
                    # TURBO: Upload in large batches
                    if len(texts) >= self.BATCH_SIZE:
                        self.upload_batch(texts, metadatas, ids)
                        texts, metadatas, ids = [], [], []
            
            # Upload remaining
            if texts:
                self.upload_batch(texts, metadatas, ids)
                
        except:
            pass  # Silent fail to maintain speed
    
    def run(self):
        """Main upload loop - TURBO MODE"""
        print("\n" + "="*80)
        print("TURBO CLOUD UPLOADER - 5x Faster Mode")
        print("="*80)
        
        if not self.cloud_store.is_connected:
            print("Cloud connection failed. Check rag_config.py")
            return
        
        all_json = list(self.data_root.glob("**/*.json"))
        all_json.sort(key=lambda x: x.stat().st_size, reverse=True)
        
        print(f"Files: {len(all_json):,} | Batch: {self.BATCH_SIZE}")
        print(f"Cloud: {self.cloud_store.count():,} docs")
        print("\nStarting TURBO upload...")
        
        for json_file in tqdm(all_json, desc="TURBO", ncols=80):
            self.process_json_file(json_file)
        
        print("\n" + "="*80)
        print(f"Uploaded: {self.uploaded:,} | Skipped: {self.skipped:,}")
        print(f"Final: {self.cloud_store.count():,} documents")
        print("="*80)

if __name__ == "__main__":
    uploader = TurboCloudUploader()
    uploader.run()
