"""
Supreme Court Judgments RAG Ingestion Script
Ingests processed SC judgment chunks into ChromaDB for RAG retrieval
"""

import sys
import json
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

class SCJudgmentsIngester:
    def __init__(self, 
                 chunks_dir="DATA/SC_Judgments_FULL/chunks",
                 collection_name="legal_db_hybrid"):
        self.chunks_dir = Path(chunks_dir)
        self.collection_name = collection_name
        self.store = None
        self.stats = {
            'total_chunks': 0,
            'ingested': 0,
            'failed': 0,
            'years_processed': []
        }
    
    def initialize_store(self):
        """Initialize the ChromaDB store"""
        print("[INFO] Initializing ChromaDB store...")
        self.store = HybridChromaStore(collection_name=self.collection_name)
        print(f"[OK] Connected to collection: {self.collection_name}")
    
    def load_chunks_for_year(self, year: int) -> List[Dict]:
        """Load all chunk files for a specific year"""
        year_dir = self.chunks_dir / str(year)
        if not year_dir.exists():
            return []
        
        all_chunks = []
        chunk_files = list(year_dir.glob("*_chunks.json"))
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
            except Exception as e:
                print(f"  [ERROR] Failed to load {chunk_file.name}: {e}")
        
        return all_chunks
    
    def prepare_documents(self, chunks: List[Dict]) -> List[Dict]:
        """Prepare chunks for ChromaDB ingestion"""
        documents = []
        
        for chunk in chunks:
            # Create document in expected format {'id', 'text', 'metadata'}
            doc = {
                'id': f"sc_{chunk['chunk_id']}",
                'text': chunk['text'],
                'metadata': {
                    'domain': 'supreme_court_judgments',
                    'case_id': chunk.get('case_id', ''),
                    'case_name': chunk.get('case_name', ''),
                    'petitioner': chunk.get('petitioner', ''),
                    'respondent': chunk.get('respondent', ''),
                    'judgment_date': chunk.get('judgment_date', ''),
                    'year': chunk.get('year', 0),
                    'section': chunk.get('section', 'unknown'),
                    'priority': chunk.get('priority', 'medium'),
                    'chunk_type': chunk.get('chunk_type', 'sequential'),
                    'case_number': chunk.get('case_number', ''),
                    'word_count': chunk.get('word_count', 0),
                    # Convert lists to strings for ChromaDB
                    'judges': ', '.join(chunk.get('judges', [])),
                    'citations': '; '.join(chunk.get('citations', [])[:10])
                }
            }
            documents.append(doc)
        
        return documents
    
    def ingest_year(self, year: int, batch_size: int = 50):
        """Ingest all chunks from a specific year"""
        print(f"\n[YEAR {year}] Loading chunks...")
        
        chunks = self.load_chunks_for_year(year)
        if not chunks:
            print(f"  [SKIP] No chunks found for {year}")
            return
        
        print(f"  [INFO] Found {len(chunks)} chunks")
        
        # Prepare documents in correct format
        documents = self.prepare_documents(chunks)
        
        # Ingest in batches
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(documents), batch_size):
            batch_num = (i // batch_size) + 1
            batch_docs = documents[i:i+batch_size]
            
            try:
                self.store.add_documents(documents=batch_docs, show_progress=False, rebuild_bm25=False)
                self.stats['ingested'] += len(batch_docs)
                print(f"  [BATCH {batch_num}/{total_batches}] Ingested {len(batch_docs)} chunks")
            except Exception as e:
                self.stats['failed'] += len(batch_docs)
                print(f"  [ERROR] Batch {batch_num} failed: {e}")
        
        self.stats['years_processed'].append(year)
        self.stats['total_chunks'] += len(chunks)
    
    def ingest_all(self, years: List[int] = None, limit_per_year: int = None):
        """Ingest chunks from multiple years"""
        print("\n" + "="*70)
        print("SUPREME COURT JUDGMENTS RAG INGESTION")
        print("="*70)
        
        # Initialize store
        self.initialize_store()
        
        # Get available years
        if years is None:
            years = sorted([
                int(d.name) for d in self.chunks_dir.iterdir() 
                if d.is_dir() and d.name.isdigit()
            ])
        
        print(f"\n[INFO] Processing years: {years}")
        
        # Ingest each year
        for year in years:
            self.ingest_year(year)

        # Final rebuild of BM25 index after all batches
        print("\n[INFO] Finalizing BM25 Index (One-time rebuild)...")
        self.store.rebuild_index()
        print("[SUCCESS] Ingestion Complete")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print ingestion summary"""
        print("\n" + "="*70)
        print("INGESTION SUMMARY")
        print("="*70)
        print(f"Total Chunks:    {self.stats['total_chunks']}")
        print(f"Ingested:        {self.stats['ingested']}")
        print(f"Failed:          {self.stats['failed']}")
        print(f"Years Processed: {self.stats['years_processed']}")
        print("="*70)

def main():
    ingester = SCJudgmentsIngester()
    
    # Ingest pilot data (2024)
    ingester.ingest_all(years=[2024])
    
    print("\n[SUCCESS] SC Judgments ingestion complete!")
    print("[TIP] Test with: python -c \"from rag_system.core.hybrid_chroma_store import HybridChromaStore; s = HybridChromaStore(); print(s.search('UAPA sanction timeline'))\"")

if __name__ == "__main__":
    main()
