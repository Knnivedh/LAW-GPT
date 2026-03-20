"""
RESUME FULL INGESTION
"""
import sys
from pathlib import Path
import logging

# Root path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.process_kaggle_sc_pdfs import KaggleSCJudgmentProcessor
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    load_dotenv(project_root / "config" / ".env")
    
    # User specific path
    import os
    from pathlib import Path
    pdf_dir = str(Path(__file__).resolve().parent.parent / "DATA" / "supreme_court_judgments_100%" / "supreme_court_judgments")
    
    print(f"🚀 RESUMING FULL INGESTION for: {pdf_dir}")
    print("Optimization: Processing recent years (2024-1950) first.")
    
    processor = KaggleSCJudgmentProcessor(pdf_dir)
    
    # PROCESS ALL REMAINING PDFS
    try:
        count = processor.process_pdfs_in_batches(max_pdfs=None) # None = Process ALL
        
        if count > 0:
            processor.migrate_to_supabase()
            
        print("\n✅ FULL INGESTION COMPLETE!")
    except KeyboardInterrupt:
        print("\n⚠️ Paused by user.")

if __name__ == "__main__":
    main()
