"""
Hugging Face Legal Dataset Collector
Downloads and processes high-quality Indian legal datasets for RAG system

Target Datasets:
1. opennyaiorg/InJudgements_dataset (Hugging Face)
2. opennyaiorg/Aalap (Instruction dataset)
3. Supreme Court Judgments (Kaggle - need manual download)
4. InLegalBERT corpus (if available)
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Install datasets library if needed
try:
    from datasets import load_dataset
except ImportError:
    print("Installing datasets library...")
    os.system("pip install datasets")
    from datasets import load_dataset

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.supabase_store import SupabaseHybridStore

class HuggingFaceLegalCollector:
    """Collect and process legal datasets from Hugging Face"""
    
    def __init__(self):
        self.store = None  # Initialize later when migrating
        self.output_dir = project_root / "DATA" / "huggingface_legal"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_opennyai_judgments(self):
        """Collect InJudgements dataset from OpenNyAI"""
        print("\n📚 Collecting OpenNyAI InJudgements Dataset...")
        print("=" * 80)
        
        try:
            # Load dataset
            print("Downloading dataset from Hugging Face...")
            dataset = load_dataset("opennyaiorg/InJudgements_dataset", split="train")
            
            print(f"✅ Loaded {len(dataset)} judgments")
            
            # Process and format
            documents = []
            for item in tqdm(dataset, desc="Processing judgments"):
                # Extract text and metadata
                text = item.get('text', '')
                if not text or len(text) < 100:
                    continue
                
                # Create rich document
                doc_text = f"""
SUPREME COURT JUDGMENT

{text}

Source: OpenNyAI InJudgements Dataset
"""
                
                metadata = {
                    "source": "OpenNyAI InJudgements",
                    "type": "supreme_court_judgment",
                    "dataset": "huggingface_opennyai",
                }
                
                # Add any additional fields
                for key in ['year', 'case_id', 'court', 'category']:
                    if key in item:
                        metadata[key] = str(item[key])
                
                documents.append({
                    "text": doc_text.strip(),
                    "metadata": metadata
                })
            
            print(f"\n✅ Processed {len(documents)} valid judgments")
            return documents
            
        except Exception as e:
            print(f"❌ Error loading OpenNyAI dataset: {e}")
            print("Tip: Try installing with: pip install datasets")
            return []
    
    def collect_aalap_instructions(self):
        """Collect Aalap legal instruction dataset"""
        print("\n📚 Collecting Aalap Legal Instructions Dataset...")
        print("=" * 80)
        
        try:
            print("Downloading dataset from Hugging Face...")
            dataset = load_dataset("opennyaiorg/Aalap", split="train")
            
            print(f"✅ Loaded {len(dataset)} instruction pairs")
            
            documents = []
            for item in tqdm(dataset, desc="Processing instructions"):
                # Extract instruction and response
                instruction = item.get('instruction', '')
                output = item.get('output', '')
                
                if not instruction or not output:
                    continue
                
                # Format as Q&A
                doc_text = f"""
LEGAL Q&A PAIR

QUESTION: {instruction}

ANSWER: {output}

Source: Aalap Legal Assistant Dataset
"""
                
                metadata = {
                    "source": "OpenNyAI Aalap",
                    "type": "legal_qa",
                    "dataset": "huggingface_aalap"
                }
                
                documents.append({
                    "text": doc_text.strip(),
                    "metadata": metadata
                })
            
            print(f"\n✅ Processed {len(documents)} Q&A pairs")
            return documents
            
        except Exception as e:
            print(f"❌ Error loading Aalap dataset: {e}")
            return []
    
    def migrate_to_supabase(self, documents: List[Dict], batch_size=20):
        """Migrate collected documents to Supabase"""
        print(f"\n📤 Migrating {len(documents)} documents to Supabase...")
        print("=" * 80)
        
        # Initialize Supabase store now
        if self.store is None:
            self.store = SupabaseHybridStore()
        
        texts = [doc['text'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        
        total_batches = (len(documents) + batch_size - 1) // batch_size
        success_count = 0
        
        for i in range(0, len(documents), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            try:
                self.store.add_documents(batch_texts, batch_metadatas)
                success_count += len(batch_texts)
                print(f"  ✅ Batch {i//batch_size + 1}/{total_batches} uploaded ({success_count}/{len(documents)})")
            except Exception as e:
                print(f"  ❌ Error in batch {i//batch_size + 1}: {e}")
                continue
        
        print(f"\n🎉 Migration complete! {success_count}/{len(documents)} documents added to Supabase")
        return success_count
    
    def run_collection(self):
        """Run full collection pipeline"""
        print("\n" + "=" * 80)
        print("🚀 HUGGING FACE LEGAL DATASET COLLECTION")
        print("=" * 80)
        
        all_documents = []
        
        # Collect from OpenNyAI InJudgements
        judgments = self.collect_opennyai_judgments()
        all_documents.extend(judgments)
        
        # Collect from Aalap
        aalap = self.collect_aalap_instructions()
        all_documents.extend(aalap)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 COLLECTION SUMMARY")
        print("=" * 80)
        print(f"Total documents collected: {len(all_documents)}")
        print(f"  - Supreme Court Judgments: {len(judgments)}")
        print(f"  - Legal Q&A Pairs: {len(aalap)}")
        
        if len(all_documents) == 0:
            print("\n⚠️  No documents collected. Check errors above.")
            return
        
        # Save locally
        output_file = self.output_dir / f"collected_legal_data_{len(all_documents)}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_documents, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to: {output_file}")
        
        # Ask user before migrating
        print("\n" + "=" * 80)
        migrate = input("Migrate to Supabase now? (y/n): ").lower().strip()
        
        if migrate == 'y':
            success = self.migrate_to_supabase(all_documents)
            
            print("\n" + "=" * 80)
            print("🎯 EXPECTED IMPACT")
            print("=" * 80)
            print(f"Documents added: {success}")
            print(f"Current accuracy: 70/100")
            print(f"Expected new accuracy: 75-80/100 (+7-14%)")
            print(f"Recommendation: Re-run advanced_legal_test.py to verify")
            print("=" * 80)
        else:
            print(f"\n💾 Data saved locally. Run migration later with:")
            print(f"python scripts/migrate_legal_knowledge.py")

if __name__ == "__main__":
    collector = HuggingFaceLegalCollector()
    collector.run_collection()
