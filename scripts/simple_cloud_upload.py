"""
SIMPLE CLOUD UPLOAD - Crash Resistant
Upload documents to Zilliz Cloud in small, reliable batches
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleCloudUploader:
    def __init__(self):
        self.cloud_store = CloudMilvusStore()
        self.data_root = PROJECT_ROOT / "DATA"
        self.uploaded = 0
        self.skipped = 0
        
    def generate_id(self, source, content):
        hash_seed = f"{source}_{content[:200]}"
        return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()
    
    def upload_batch(self, texts, metadatas, ids):
        """Upload a single batch to cloud"""
        try:
            self.cloud_store.add(texts, metadatas, ids)
            self.uploaded += len(texts)
            logger.info(f"✅ Uploaded batch of {len(texts)} docs. Total: {self.uploaded}")
            return True
        except Exception as e:
            logger.error(f"❌ Batch upload failed: {e}")
            self.skipped += len(texts)
            return False
    
    def process_json_file(self, file_path: Path):
        """Process a single JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            texts, metadatas, ids = [], [], []
            source = file_path.parent.name
            
            # Handle list of documents
            if isinstance(data, list):
                for i, entry in enumerate(data[:1000]):  # Limit to 1000 per file to avoid memory issues
                    if not isinstance(entry, dict):
                        continue
                    
                    content = (entry.get('text') or entry.get('content') or 
                              entry.get('response_text') or str(entry))
                    
                    if len(str(content)) < 50:
                        continue
                    
                    doc_id = self.generate_id(source, str(content))
                    title = entry.get('title', f"{file_path.stem}_{i}")
                    
                    texts.append(str(content))
                    metadatas.append({
                        "source": source,
                        "title": str(title)[:300],
                        "file": file_path.name
                    })
                    ids.append(doc_id)
                    
                    # Upload in batches of 50
                    if len(texts) >= 50:
                        self.upload_batch(texts, metadatas, ids)
                        texts, metadatas, ids = [], [], []
            
            # Upload remaining
            if texts:
                self.upload_batch(texts, metadatas, ids)
                
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
    
    def run(self):
        """Main upload loop"""
        print("\n" + "="*80)
        print("📡 SIMPLE CLOUD UPLOADER - Zilliz Sync")
        print("="*80)
        
        if not self.cloud_store.is_connected:
            print("❌ Cloud connection failed. Check rag_config.py")
            return
        
        # Get all JSON files
        all_json = list(self.data_root.glob("**/*.json"))
        print(f"Found {len(all_json):,} JSON files")
        print(f"Current cloud count: {self.cloud_store.count():,} documents")
        print("\nStarting upload...")
        
        for json_file in tqdm(all_json, desc="Processing Files"):
            self.process_json_file(json_file)
        
        print("\n" + "="*80)
        print("📊 UPLOAD SUMMARY")
        print("="*80)
        print(f"Successfully Uploaded: {self.uploaded:,}")
        print(f"Skipped/Failed: {self.skipped:,}")
        print(f"Final Cloud Count: {self.cloud_store.count():,}")
        print("="*80)

if __name__ == "__main__":
    uploader = SimpleCloudUploader()
    uploader.run()
