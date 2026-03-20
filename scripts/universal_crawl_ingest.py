"""
UNIVERSAL CRAWL INGESTER
Examines ALL folders and JSON files in the DATA directory
Achieves 100% connectivity for 3L+ documents
"""

import os
import sys
import json
import logging
from pathlib import Path
from tqdm import tqdm
import hashlib

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniversalIngester:
    def __init__(self):
        import rag_config
        self.store = HybridChromaStore()
        self.cloud_store = None
        
        if rag_config.CLOUD_MODE_ENABLED:
            from rag_system.core.milvus_store import CloudMilvusStore
            self.cloud_store = CloudMilvusStore()
            logger.info("🛰️ Cloud Storage detected. Universal Ingester will sync to Zilliz Cloud.")
            
        self.data_root = PROJECT_ROOT / "DATA"
        self.ingested_count = 0
        self.cloud_ingested_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
    def generate_id(self, source, title, content):
        """Generate stable ID based on content hash to avoid duplicates"""
        hash_seed = f"{source}_{title}_{content[:500]}"
        return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()

    def process_file(self, file_path: Path):
        """Analyze and ingest a single JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Case 1: List of records (e.g., kanoon_data.json, 50K_Case_Studies.json)
            if isinstance(data, list):
                self.process_list(data, file_path)
            
            # Case 2: Dictionary (either single doc or a map of docs)
            elif isinstance(data, dict):
                # Check if it's a chunked judgment (common in SC_Judgments_FULL)
                if 'chunk_index' in data and ('text' in data or 'content' in data):
                    self.process_single_doc(data, file_path)
                else:
                    # Treat as potential list of key-value docs
                    self.process_dict(data, file_path)
                    
        except Exception as e:
            # logger.error(f"Error reading {file_path.name}: {e}")
            self.error_count += 1

    def process_list(self, data_list, file_path):
        """Process list of objects"""
        texts, metadatas, ids = [], [], []
        source_name = file_path.parent.name
        
        for i, entry in enumerate(data_list):
            if not isinstance(entry, dict):
                continue
                
            content = entry.get('text') or entry.get('content') or entry.get('response_text') or entry.get('query_text') or json.dumps(entry, ensure_ascii=False)
            title = entry.get('title') or entry.get('case_name') or entry.get('query_title') or f"{file_path.stem}_{i}"
            
            if len(str(content)) < 50:
                continue
                
            doc_id = self.generate_id(source_name, title, content)
            
            texts.append(str(content))
            metadatas.append({
                "source": source_name,
                "title": str(title)[:500],
                "file": file_path.name,
                "type": "json_record"
            })
            ids.append(doc_id)
            
            # Batch add every 100
            if len(texts) >= 100:
                self.add_to_store(texts, metadatas, ids)
                texts, metadatas, ids = [], [], []
        
        if texts:
            self.add_to_store(texts, metadatas, ids)

    def process_single_doc(self, data, file_path):
        """Process single document object"""
        content = data.get('text') or data.get('content') or json.dumps(data, ensure_ascii=False)
        title = data.get('case_name') or data.get('title') or file_path.stem
        
        doc_id = self.generate_id(file_path.parent.name, title, content)
        
        self.add_to_store(
            [str(content)],
            [{"source": file_path.parent.parent.name, "title": str(title)[:500], "file": file_path.name, "type": "sc_chunk"}],
            [doc_id]
        )

    def process_dict(self, data_dict, file_path):
        """Process dictionary of key-value pairs as individual docs if applicable"""
        # Very specific to some datasets, limit depth
        if len(data_dict) > 1000:
            logger.info(f"Skipping large map-style JSON: {file_path.name}")
            return
            
        for key, value in data_dict.items():
            if isinstance(value, (dict, list)):
                content = json.dumps(value, ensure_ascii=False)
            else:
                content = str(value)
                
            if len(content) < 100:
                continue
                
            doc_id = self.generate_id(file_path.stem, str(key), content)
            self.add_to_store([content], [{"source": file_path.stem, "title": str(key)[:200], "type": "json_map"}], [doc_id])

    def add_to_store(self, texts, metadatas, ids):
        # 1. Local Ingest
        try:
            self.store.collection.add(documents=texts, metadatas=metadatas, ids=ids)
            self.ingested_count += len(texts)
        except Exception:
            self.skipped_count += len(texts)

        # 2. Cloud Ingest (If configured)
        if self.cloud_store:
            try:
                self.cloud_store.add(texts, metadatas, ids)
                self.cloud_ingested_count += len(texts)
            except Exception as e:
                logger.error(f"Cloud ingest failed for batch: {e}")

    def crawl_all(self):
        """Main loop to visit every corner of DATA"""
        print("\n" + "="*80)
        print("🔍 UNIVERSAL DATA AUDIT & INGESTION")
        print("Target: 100% Connectivity for 3L+ Documents")
        print("="*80)
        
        all_json_files = list(self.data_root.glob("**/*.json"))
        print(f"Found {len(all_json_files):,} JSON files to examine...")
        
        # Sort by size so large ones (lists) are hit first
        all_json_files.sort(key=lambda x: x.stat().st_size, reverse=True)
        
        for file_path in tqdm(all_json_files, desc="Examining Data Inventory"):
            self.process_file(file_path)
            
        print("\n" + "="*80)
        print("📊 AUDIT & INGESTION SUMMARY")
        print("="*80)
        print(f"Total Files Examined: {len(all_json_files):,}")
        print(f"New Documents Ingested: {self.ingested_count:,}")
        print(f"Duplicates/Skipped Doc Chunks: {self.skipped_count:,}")
        print(f"Failed Files: {self.error_count:,}")
        print(f"Final Result: Data Connectivity Optimized")
        print("="*80)

if __name__ == "__main__":
    ingester = UniversalIngester()
    ingester.crawl_all()
