"""
Ingest User Provided Data
"""
import sys
from pathlib import Path
import os

# Root path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.process_kaggle_sc_pdfs import KaggleSCJudgmentProcessor

def main():
    # User specific path (handled raw string)
    import os
    from pathlib import Path
    pdf_dir = str(Path(__file__).resolve().parent.parent / "DATA" / "supreme_court_judgments_100%" / "supreme_court_judgments")
    
    print(f"🚀 STARTING INGESTION for: {pdf_dir}")
    print("Optimization: Processing recent years (2024-2020) first.")
    
    # Load env vars for Supabase
    from dotenv import load_dotenv
    load_dotenv(project_root / "config" / ".env")
    
    processor = KaggleSCJudgmentProcessor(pdf_dir)
    
    # 1. Process
    # We will process ALL of them, but user can Ctrl+C if needed. 
    # For this session, we'll try to process a significant batch (e.g., 2000 files)
    # to show immediate impact, then migrating.
    # To process ALL, set max_pdfs=None. 
    # Let's set max_pdfs=5000 (Top 5000 recent cases) as a strong start.
    
    # SKIPPING PROCESSING AS BATCHES EXIST (Resume mode)
    # count = processor.process_pdfs_in_batches(max_pdfs=5000)
    
    # 2. Migrate
    # if count > 0:
    processor.migrate_to_supabase()
        
    print("\n✅ Ingestion batch complete.")

if __name__ == "__main__":
    main()
