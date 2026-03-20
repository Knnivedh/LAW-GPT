import json
import sys
import os
from pathlib import Path

# Add parent directory to path to import rag_system
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

class NDTVIngester:
    def __init__(self, collection_name: str = "legal_db_hybrid"):
        self.store = HybridChromaStore(collection_name=collection_name)
        self.base_dir = Path(__file__).parent.parent / "DATA"
        
    def ingest(self):
        """Ingest NDTV Legal QA dataset"""
        file_path = self.base_dir / "ndtv_legal_qa_data" / "ndtv_legal_qa_data.json"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return

        print(f"\n[INFO] Loading {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load JSON: {e}")
            return

        print(f"[INFO] Found {len(data)} NDTV QA pairs. Starting ingestion...")
        
        batch_size = 100
        documents = []
        
        for i, item in enumerate(data):
            # Construct text content
            question = item.get("Question", "").strip()
            answer = item.get("Answer", "").strip()
            
            if not question or not answer:
                continue
                
            text = f"Question: {question}\nAnswer: {answer}"
            
            # Prepare metadata
            metadata = {
                "source": "NDTV Legal",
                "content_type": item.get("content_type", "article"),
                "category": item.get("category", "General"),
                "topic": item.get("topic", "General"),
                "type": "legal_qa",
                "domain": "legal_news_qa"
            }
            
            doc = {
                "id": f"ndtv_qa_{i}",
                "text": text,
                "metadata": metadata
            }
            documents.append(doc)
            
            if len(documents) >= batch_size:
                self._flush_batch(documents, f"NDTV Batch {i//batch_size}")
                documents = []
                
        # Flush remaining
        if documents:
            self._flush_batch(documents, "NDTV Final Batch")

    def _flush_batch(self, documents, batch_name):
        try:
            self.store.add_documents(documents, show_progress=False)
            print(f"  [SUCCESS] Ingested {len(documents)} docs for {batch_name}")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {batch_name}: {e}")

if __name__ == "__main__":
    print("=== Starting NDTV Data Ingestion ===")
    ingester = NDTVIngester()
    ingester.ingest()
    print("\n=== NDTV Ingestion Completed ===")
