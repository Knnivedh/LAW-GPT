"""
FULL SCALE SC JUDGMENTS INGESTION
Ingests ALL processed chunks into ChromaDB for Advanced RAG
Handles 500,000+ chunks efficiently
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Generator
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tqdm import tqdm

# Configuration
CHUNKS_DIR = Path("DATA/SC_Judgments_FULL/chunks")
BATCH_SIZE = 100  # Documents per batch
SAVE_EVERY = 1000  # Save progress every N documents

class FullScaleIngester:
    def __init__(self, collection_name="legal_db_hybrid"):
        self.chunks_dir = CHUNKS_DIR
        self.collection_name = collection_name
        self.store = None
        self.stats = {
            'total_files': 0,
            'total_chunks': 0,
            'ingested': 0,
            'failed': 0,
            'start_time': None
        }
    
    def initialize_store(self):
        """Initialize ChromaDB with optimized settings"""
        print("[INIT] Loading ChromaDB store...")
        from rag_system.core.hybrid_chroma_store import HybridChromaStore
        self.store = HybridChromaStore(collection_name=self.collection_name)
        print(f"[OK] Connected to: {self.collection_name}")
        print(f"[OK] Existing documents: {self.store.count():,}")
    
    def count_total_chunks(self) -> int:
        """Count total chunks to process"""
        total = 0
        for year_dir in self.chunks_dir.iterdir():
            if year_dir.is_dir():
                chunk_files = list(year_dir.glob("*_chunks.json"))
                total += len(chunk_files)
        return total
    
    def load_chunks_generator(self) -> Generator[Dict, None, None]:
        """Generator to load chunks file by file (memory efficient)"""
        for year_dir in sorted(self.chunks_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            
            chunk_files = sorted(year_dir.glob("*_chunks.json"))
            
            for chunk_file in chunk_files:
                try:
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        chunks = json.load(f)
                        for chunk in chunks:
                            yield chunk
                except Exception as e:
                    print(f"  [ERROR] Failed to load {chunk_file.name}: {e}")
    
    def prepare_document(self, chunk: Dict) -> Dict:
        """Convert chunk to ChromaDB format"""
        # Flatten and clean metadata
        judges = chunk.get('judges', [])
        if isinstance(judges, list):
            judges = ', '.join(str(j).replace('\n', ' ') for j in judges[:5])
        
        citations = chunk.get('citations', [])
        if isinstance(citations, list):
            citations = '; '.join(str(c).replace('\n', ' ') for c in citations[:10])
        
        return {
            'id': f"sc_{chunk.get('chunk_id', '')}",
            'text': chunk.get('text', ''),
            'metadata': {
                'domain': 'supreme_court_judgments',
                'case_id': str(chunk.get('case_id', '')),
                'case_name': str(chunk.get('case_name', ''))[:200],
                'petitioner': str(chunk.get('petitioner', ''))[:100],
                'respondent': str(chunk.get('respondent', ''))[:100],
                'judgment_date': str(chunk.get('judgment_date', '')),
                'year': int(chunk.get('year', 0)) if chunk.get('year') else 0,
                'section': str(chunk.get('section', 'unknown')),
                'priority': str(chunk.get('priority', 'medium')),
                'chunk_index': int(chunk.get('chunk_index', 0)),
                'total_chunks': int(chunk.get('total_chunks', 1)),
                'word_count': int(chunk.get('word_count', 0)),
                'judges': str(judges)[:500],
                'citations': str(citations)[:1000]
            }
        }
    
    def ingest_all(self):
        """Ingest all chunks into ChromaDB"""
        print("\n" + "="*70)
        print("SUPREME COURT JUDGMENTS - FULL SCALE RAG INGESTION")
        print("="*70)
        
        # Initialize
        self.initialize_store()
        self.stats['start_time'] = time.time()
        
        # Count total
        print("\n[SCAN] Counting chunk files...")
        self.stats['total_files'] = self.count_total_chunks()
        print(f"[OK] Found {self.stats['total_files']:,} chunk files")
        
        # Collect batches
        print("\n[INGEST] Starting ingestion...")
        batch = []
        
        with tqdm(desc="Processing chunks", unit="chunk") as pbar:
            for chunk in self.load_chunks_generator():
                try:
                    doc = self.prepare_document(chunk)
                    batch.append(doc)
                    self.stats['total_chunks'] += 1
                    
                    # Process batch
                    if len(batch) >= BATCH_SIZE:
                        self._ingest_batch(batch)
                        pbar.update(len(batch))
                        pbar.set_postfix({
                            'ingested': f"{self.stats['ingested']:,}",
                            'failed': self.stats['failed']
                        })
                        batch = []
                        
                except Exception as e:
                    self.stats['failed'] += 1
            
            # Process remaining
            if batch:
                self._ingest_batch(batch)
                pbar.update(len(batch))
        
        # Final stats
        self._print_summary()
    
    def _ingest_batch(self, batch: List[Dict]):
        """Ingest a batch of documents"""
        try:
            self.store.add_documents(documents=batch, show_progress=False)
            self.stats['ingested'] += len(batch)
        except Exception as e:
            self.stats['failed'] += len(batch)
            print(f"\n  [ERROR] Batch failed: {e}")
    
    def _print_summary(self):
        """Print final summary"""
        elapsed = time.time() - self.stats['start_time']
        
        print("\n" + "="*70)
        print("INGESTION COMPLETE")
        print("="*70)
        print(f"Total chunk files:   {self.stats['total_files']:,}")
        print(f"Total chunks:        {self.stats['total_chunks']:,}")
        print(f"Successfully added:  {self.stats['ingested']:,}")
        print(f"Failed:              {self.stats['failed']:,}")
        print(f"Time:                {elapsed/60:.1f} minutes")
        print(f"Speed:               {self.stats['ingested']/max(1,elapsed):.1f} chunks/sec")
        print("="*70)
        
        # Final count
        print(f"\n[FINAL] Total documents in RAG: {self.store.count():,}")

def main():
    ingester = FullScaleIngester()
    ingester.ingest_all()
    print("\n[SUCCESS] Full-scale ingestion complete!")
    print("[TIP] Test: python scripts/test_sc_search.py")

if __name__ == "__main__":
    main()
