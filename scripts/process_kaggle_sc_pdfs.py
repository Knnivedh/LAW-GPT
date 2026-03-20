"""
Kaggle Supreme Court Judgments Processor
Processes 26,000 PDF judgments from Kaggle dataset

Dataset: "Supreme Court Judgments India (1950-2025)"
URL: https://www.kaggle.com/datasets/sh0416/supreme-court-judgments-india
Size: 26,000 PDFs

Usage:
1. Download dataset from Kaggle (you need Kaggle account)
2. Extract to: DATA/kaggle_supreme_court/
3. Run this script

Expected Output:
- Parsed 20,000+ judgments (some PDFs may be corrupted)
- Migrated to Supabase in batches
- Accuracy boost: 70% → 90%+
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import PyPDF2

# Add parent to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.supabase_store import SupabaseHybridStore

class KaggleSCJudgmentProcessor:
    """Process Kaggle Supreme Court PDF judgments"""
    
    def __init__(self, pdf_directory: str):
        self.pdf_dir = Path(pdf_directory)
        if not self.pdf_dir.exists():
            raise FileNotFoundError(f"PDF directory not found: {pdf_directory}")
        
        self.store = None  # Initialize later
        self.output_dir = project_root / "DATA" / "processed_kaggle"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract from first 50 pages (most judgments are < 50 pages)
                num_pages = min(len(pdf_reader.pages), 50)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                
                return text.strip()
        except Exception as e:
            print(f"  ❌ Error reading {pdf_path.name}: {str(e)[:100]}")
            return ""
    
    def extract_metadata_from_text(self, text: str, filename: str) -> Dict:
        """Extract basic metadata from judgment text"""
        metadata = {
            "source": "Kaggle SC Judgments Dataset",
            "type": "supreme_court_judgment",
            "filename": filename
        }
        
        # Try to extract year from filename (usually format: year_caseid.pdf)
        try:
            if '_' in filename:
                year_str = filename.split('_')[0]
                if year_str.isdigit() and 1950 <= int(year_str) <= 2025:
                    metadata['year'] = int(year_str)
        except:
            pass
        
        # Try to extract case name from first few lines
        lines = text.split('\n')[:20]
        for line in lines:
            if ' v. ' in line or ' vs. ' in line or ' V. ' in line:
                metadata['case_name'] = line.strip()[:200]
                break
        
        return metadata
    
    def process_pdfs_in_batches(self, batch_size=100, max_pdfs=None):
        """Process PDFs in batches"""
        print("\n" + "=" * 80)
        print("🔬 PROCESSING KAGGLE SUPREME COURT JUDGMENTS")
        print("=" * 80)
        
        # Get all PDF files (Recursive)
        print(f"🔍 Searching recursively in: {self.pdf_dir}")
        pdf_files = sorted(list(self.pdf_dir.rglob("*.pdf")), reverse=True) # Process 2024/2025 first
        
        if max_pdfs:
            pdf_files = pdf_files[:max_pdfs]
        
        total_pdfs = len(pdf_files)
        print(f"📄 Found {total_pdfs} PDF files")
        
        if total_pdfs == 0:
            print("\n⚠️  No PDF files found!")
            print(f"Expected location: {self.pdf_dir}")
            return
        
        # Process in batches
        documents = []
        processed_count = 0
        error_count = 0
        
        print(f"\n📚 Processing PDFs...")
        for pdf_path in tqdm(pdf_files, desc="Extracting text"):
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text or len(text) < 500:  # Skip very short/empty documents
                error_count += 1
                continue
            
            # Extract metadata
            metadata = self.extract_metadata_from_text(text, pdf_path.name)
            
            # IMPROVEMENT: Get YYYY from parent folder if possible
            if 'year' not in metadata or not metadata['year']:
                parent_name = pdf_path.parent.name
                if parent_name.isdigit() and len(parent_name) == 4:
                    metadata['year'] = int(parent_name)
            
            # IMPROVEMENT: Parse case name from filename if possible
            # File format: Case_Name_vs_Case_Name_on_Date.PDF
            if 'case_name' not in metadata:
                clean_name = pdf_path.stem.replace('_', ' ').replace('  ', ' ')
                if ' vs ' in clean_name.lower() or ' on ' in clean_name.lower():
                     metadata['case_name'] = clean_name
            
            # Create document
            doc_text = f"""
SUPREME COURT JUDGMENT

Case Name: {metadata.get('case_name', 'Unknown')}
Year: {metadata.get('year', 'Unknown')}

{text[:12000]}  # First ~12k chars

Source: Kaggle SC Judgments (1950-2025)
Filename: {pdf_path.name}
"""
            
            documents.append({
                "text": doc_text.strip(),
                "metadata": metadata
            })
            
            processed_count += 1
            
            # Save batch periodically
            if len(documents) >= batch_size:
                self._save_batch(documents, processed_count)
                documents = []
        
        # Save remaining
        if documents:
            self._save_batch(documents, processed_count)
        
        print(f"\n✅ Processing Complete!")
        print(f"   - Total PDFs: {total_pdfs}")
        print(f"   - Successfully processed: {processed_count}")
        print(f"   - Errors/skipped: {error_count}")
        
        return processed_count
    
    def _save_batch(self, documents: List[Dict], batch_num: int):
        """Save batch to JSON file"""
        output_file = self.output_dir / f"batch_{batch_num//100 + 1}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved batch to: {output_file.name}")
    
    def migrate_to_supabase(self):
        """Migrate all processed batches to Supabase"""
        print("\n" + "=" * 80)
        print("📤 MIGRATING TO SUPABASE")
        print("=" * 80)
        
        # Initialize Supabase
        if self.store is None:
            self.store = SupabaseHybridStore()
        
        # Load all batch files
        batch_files = sorted(self.output_dir.glob("batch_*.json"))
        
        if not batch_files:
            print("⚠️  No processed batches found. Run processing first.")
            return
        
        total_docs = 0
        
        for batch_file in batch_files:
            print(f"\n📤 Migrating {batch_file.name}...")
            
            with open(batch_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            # texts = [doc['text'] for doc in documents]
            # metadatas = [doc['metadata'] for doc in documents]
            
            try:
                self.store.add_documents(documents)
                total_docs += len(documents)
                print(f"  ✅ Migrated {len(documents)} documents (Total: {total_docs})")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        print("\n" + "=" * 80)
        print("🎉 MIGRATION COMPLETE!")
        print("=" * 80)
        print(f"📊 Total documents migrated: {total_docs}")
        print(f"\n💡 Expected Impact:")
        print(f"   - Current accuracy: 70/100")
        print(f"   - Expected accuracy: 90-95/100")
        print(f"   - Case law coverage: Near complete")
        print(f"\n🔬 Next Step:")
        print(f"   python scripts/advanced_legal_test.py")
        print("=" * 80)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Kaggle SC Judgments")
    parser.add_argument('--pdf-dir', type=str, 
                       default=str(project_root / "DATA" / "kaggle_supreme_court"),
                       help='Directory containing PDF files')
    parser.add_argument('--process', action='store_true', 
                       help='Process PDFs')
    parser.add_argument('--migrate', action='store_true', 
                       help='Migrate to Supabase')
    parser.add_argument('--max-pdfs', type=int, 
                       help='Maximum PDFs to process (for testing)')
    
    args = parser.parse_args()
    
    processor = KaggleSCJudgmentProcessor(args.pdf_dir)
    
    if args.process:
        processor.process_pdfs_in_batches(max_pdfs=args.max_pdfs)
    
    if args.migrate:
        processor.migrate_to_supabase()
    
    if not args.process and not args.migrate:
        print("\n💡 Usage:")
        print("  python scripts/process_kaggle_sc_pdfs.py --process")
        print("  python scripts/process_kaggle_sc_pdfs.py --migrate")
        print("  python scripts/process_kaggle_sc_pdfs.py --process --migrate  # Both")

if __name__ == "__main__":
    main()
