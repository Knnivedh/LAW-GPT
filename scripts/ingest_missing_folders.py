import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to import rag_system
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

class MissingDataIngester:
    def __init__(self, collection_name: str = "legal_db_hybrid"):
        self.store = HybridChromaStore(collection_name=collection_name)
        self.base_dir = Path(__file__).parent.parent / "DATA"
        
    def ingest_indian_express_qa(self):
        """Ingest Indian Express Property Law QA dataset"""
        file_path = self.base_dir / "indianexpress_property_law_qa" / "indianexpress_property_law_qa.json"
        
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

        print(f"[INFO] Found {len(data)} QA pairs. Starting ingestion...")
        
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
                "source": item.get("source", "Indian Express Legal Report"),
                "content_type": item.get("content_type", "property law"),
                "type": "legal_qa",
                "domain": "property_law"
            }
            
            doc = {
                "id": f"ie_qa_{i}",
                "text": text,
                "metadata": metadata
            }
            documents.append(doc)
            
            if len(documents) >= batch_size:
                self._flush_batch(documents, f"Indian Express QA Batch {i//batch_size}")
                documents = []
                
        # Flush remaining
        if documents:
            self._flush_batch(documents, "Indian Express QA Final Batch")

    def ingest_50k_case_studies(self):
        """Ingest 50K Case Studies dataset"""
        # Note: Handling space in folder name
        file_path = self.base_dir / "Indian_Case_Studies_50K ORG" / "Indian_Case_Studies_50K ORG.json"
        
        if not file_path.exists():
            print(f"[ERROR] File not found: {file_path}")
            return

        print(f"\n[INFO] Loading {file_path}...")
        print("[INFO] This is a large file, please wait...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load JSON: {e}")
            return

        print(f"[INFO] Found {len(data)} Case Studies. Starting ingestion...")
        
        batch_size = 50 
        documents = []
        
        for i, case in enumerate(data):
            # Construct rich text representation for embedding
            title = case.get("case_title", "")
            desc = case.get("case_description", "")
            legal = case.get("legal_aspects", {})
            sections = ", ".join(legal.get("sections_applied", []))
            verdict = case.get("verdict", "")
            
            text = f"Case Title: {title}\n"
            text += f"Description: {desc}\n"
            text += f"Legal Sections: {sections}\n"
            text += f"Verdict/Status: {verdict}\n"
            text += f"Location: {case.get('location', '')}\n"
            text += f"Lessons: {', '.join(case.get('lessons_learned', []))}"
            
            # Prepare metadata (flatten structure)
            metadata = {
                "case_id": case.get("case_id", ""),
                "case_type": case.get("case_type", ""),
                "court_level": legal.get("court_level", ""),
                "year": case.get("incident_date", "")[:4] if case.get("incident_date") else "",
                "domain": "case_study",
                "type": "case_law_study",
                "source": "50k_dataset"
            }
            
            doc = {
                "id": f"cs_50k_{i}_{case.get('case_id', 'unknown')}",
                "text": text,
                "metadata": metadata
            }
            documents.append(doc)
            
            if len(documents) >= batch_size:
                self._flush_batch(documents, f"Case Studies Batch {i//batch_size}")
                documents = []
        
        # Flush remaining
        if documents:
            self._flush_batch(documents, "Case Studies Final Batch")

    def _flush_batch(self, documents: List[Dict], batch_name: str):
        try:
            self.store.add_documents(documents, show_progress=False, rebuild_bm25=False)
            print(f"  [SUCCESS] Ingested {len(documents)} docs for {batch_name}")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {batch_name}: {e}")

def main():
    print("=== Starting Ingestion for Missing Folders ===")
    ingester = MissingDataIngester()
    
    # 1. Ingest Indian Express QA
    ingester.ingest_indian_express_qa()
    
    # 2. Ingest 50K Case Studies
    ingester.ingest_50k_case_studies()
    
    print("\n[INFO] Finalizing BM25 Index (One-time rebuild)...")
    ingester.store.rebuild_index()
    
    print("\n=== All Ingestion Tasks Completed ===")

if __name__ == "__main__":
    main()
