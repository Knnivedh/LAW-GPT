"""
NCDRC Consumer Cases RAG Ingestion Script
Ingests collected NCDRC judgment files into ChromaDB for RAG retrieval
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

class NCDRCIngester:
    def __init__(self, 
                 cases_dir="DATA/CaseLaw/Consumer",
                 collection_name="legal_db_hybrid"):
        self.cases_dir = Path(cases_dir)
        self.collection_name = collection_name
        self.store = None
        self.stats = {
            'total_files': 0,
            'ingested': 0,
            'failed': 0
        }
    
    def initialize_store(self):
        """Initialize the ChromaDB store"""
        print("[INFO] Initializing ChromaDB store...")
        self.store = HybridChromaStore(collection_name=self.collection_name)
        print(f"[OK] Connected to collection: {self.collection_name}")
    
    def parse_case_file(self, file_path: Path) -> Dict:
        """Parse a case file into document structure"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from header
            header_match = re.search(r"CASE: (.*)\nURL: (.*)\n\n", content)
            if header_match:
                case_title = header_match.group(1).strip()
                url = header_match.group(2).strip()
                text = content[header_match.end():].strip()
            else:
                # Fallback if header missing
                case_title = file_path.stem.replace('_', ' ')
                url = "unknown"
                text = content.strip()
                
            # Basic cleaning
            text = re.sub(r'\n+', '\n', text)
            
            return {
                'id': f"ncdrc_{file_path.stem}",
                'text': text,
                'metadata': {
                    'domain': 'consumer_law',
                    'court': 'NCDRC',
                    'case_name': case_title,
                    'url': url,
                    'type': 'case_law',
                    'source': 'indiankanoon'
                }
            }
        except Exception as e:
            print(f"  [ERROR] Failed to parse {file_path.name}: {e}")
            return None

    def ingest_cases(self, limit: int = None):
        """Ingest all cases from the directory"""
        print("\n" + "="*70)
        print("NCDRC CASES RAG INGESTION")
        print("="*70)
        
        # Initialize store
        self.initialize_store()
        
        # Get files
        files = list(self.cases_dir.glob("*.txt"))
        if limit:
            files = files[:limit]
            
        print(f"[INFO] Found {len(files)} case files")
        self.stats['total_files'] = len(files)
        
        documents = []
        for file_path in files:
            doc = self.parse_case_file(file_path)
            if doc:
                documents.append(doc)
        
        if not documents:
            print("[WARN] No valid documents to ingest")
            return

        batch_size = 20
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(documents), batch_size):
            batch_num = (i // batch_size) + 1
            batch_docs = documents[i:i+batch_size]
            
            try:
                self.store.add_documents(documents=batch_docs, show_progress=False)
                self.stats['ingested'] += len(batch_docs)
                print(f"  [BATCH {batch_num}/{total_batches}] Ingested {len(batch_docs)} cases")
            except Exception as e:
                self.stats['failed'] += len(batch_docs)
                print(f"  [ERROR] Batch {batch_num} failed: {e}")
                
        self.print_summary()

    def print_summary(self):
        """Print ingestion summary"""
        print("\n" + "="*70)
        print("INGESTION SUMMARY")
        print("="*70)
        print(f"Total Files:     {self.stats['total_files']}")
        print(f"Ingested:        {self.stats['ingested']}")
        print(f"Failed:          {self.stats['failed']}")
        print("="*70)

def main():
    ingester = NCDRCIngester()
    ingester.ingest_cases()
    print("\n[SUCCESS] NCDRC cases ingestion complete!")

if __name__ == "__main__":
    main()
