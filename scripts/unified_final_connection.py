import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force CPU to avoid CUDA initialization issues in background
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # Suppress TF logs

from rag_system.core.hybrid_chroma_store import HybridChromaStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedFinalConnector:
    def __init__(self, collection_name: str = "legal_db_hybrid"):
        self.store = HybridChromaStore(collection_name=collection_name)
        self.data_dir = PROJECT_ROOT / "DATA"
        self.stats = {}
        
    def ingest_json_file(self, file_path: Path):
        """Generic JSON ingester that handles multiple structures"""
        if not file_path.exists():
            return
            
        logger.info(f"Processing: {file_path.relative_to(self.data_dir)}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            
            # Identify the list of documents/cases
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Check common keys
                items = data.get('documents', data.get('cases', data.get('records', [])))
                if not items and any(isinstance(v, dict) for v in data.values()):
                    # Might be a dict of dicts (like domain-indexed)
                    items = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            v['_key'] = k
                            items.append(v)
                        elif isinstance(v, list):
                            items.extend(v)
            else:
                items = [data]
                
            if not items and isinstance(data, dict):
                # Last resort: treat the dict itself as an item if it has content-like keys
                if any(k in data for k in ['content', 'text', 'answer']):
                    items = [data]

            for i, item in enumerate(items):
                # Skip if empty
                if not item: continue
                
                # Extract text
                text = ""
                if isinstance(item, str):
                    text = item
                elif isinstance(item, dict):
                    # Try to build a readable string
                    title = item.get('title') or item.get('case_name') or item.get('question') or ""
                    content = item.get('content') or item.get('text') or item.get('answer') or item.get('description') or ""
                    
                    if title and content:
                        text = f"TITLE: {title}\n\n{content}"
                    elif content:
                        text = content
                    else:
                        # Fallback: dump JSON
                        text = json.dumps(item, indent=2)
                        
                # Prepare metadata
                metadata = {
                    'source': file_path.name,
                    'type': 'knowledge_file',
                    'category': str(item.get('category', 'general')) if isinstance(item, dict) else 'general'
                }
                
                # Check for duplicates or existing IDs
                doc_id = f"unified_{file_path.stem}_{i}"
                if isinstance(item, dict) and item.get('id'):
                    doc_id = f"unified_{file_path.stem}_{item['id']}"
                
                documents.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata
                })

            if documents:
                # Add in batches
                batch_size = 50
                for j in range(0, len(documents), batch_size):
                    batch = documents[j:j+batch_size]
                    self.store.add_documents(batch, show_progress=False, rebuild_bm25=False)
                
                self.stats[file_path.name] = len(documents)
                logger.info(f"  [OK] Ingested {len(documents)} docs")
                
        except Exception as e:
            logger.error(f"  [ERROR] Failed to process {file_path.name}: {e}")

    def run_full_audit_and_fix(self):
        """Traverse DATA directory and ingest all relevant JSONs"""
        logger.info("Starting Unified Final Connection Audit...")
        
        # Files we specifically know are high-value
        target_files = [
            "consumer_law_specifics.json",
            "law_transitions_2024.json",
            "pwdva_comprehensive.json",
            "specific_gap_fix_cases.json",
            "landmark_legal_cases.json",
            "landmark_legal_cases_expansion.json",
            "NCDRC/ncdrc_landmark_cases.json"
        ]
        
        # Also explore subdirectories
        target_dirs = [
            "data_collection/case_law",
            "data_collection/legal_domains",
            "data_collection/generated_10k"
        ]
        
        # Process specific files
        for rel_path in target_files:
            file_path = self.data_dir / rel_path
            self.ingest_json_file(file_path)
            
        # Process targeted directories
        for rel_dir in target_dirs:
            dir_path = self.data_dir / rel_dir
            if dir_path.exists():
                for json_file in dir_path.glob("*.json"):
                    self.ingest_json_file(json_file)
                    
        # Final Summary
        logger.info("\n" + "="*40)
        logger.info("FINAL CONNECTION SUMMARY")
        logger.info("="*40)
        total = 0
        for name, count in self.stats.items():
            logger.info(f"{name:35} : {count} docs")
            total += count
        logger.info("-" * 40)
        logger.info(f"TOTAL CONNECTED IN THIS RUN: {total}")
        logger.info("="*40)
        
        logger.info("Rebuilding BM25 index for all new data...")
        self.store.rebuild_index()
        logger.info("Indexing Complete!")

if __name__ == "__main__":
    try:
        connector = UnifiedFinalConnector()
        connector.run_full_audit_and_fix()
    except Exception as e:
        logger.error(f"CRITICAL ERROR IN SCRIPT: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
