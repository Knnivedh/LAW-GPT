"""
SMART RESUME SCRIPT
Skipping existing batches based on Supabase Count.
"""
import sys
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Root path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.supabase_store import SupabaseHybridStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    load_dotenv(project_root / "config" / ".env")
    
    # 1. Initialize Store
    try:
        store = SupabaseHybridStore()
        info = store.get_collection_info()
        current_count = info['count']
        logger.info(f"🔎 Current Supabase Count: {current_count}")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        return

    # 2. Get Batches (Alphabetical Sort to match original migration order)
    processed_dir = project_root / "DATA" / "processed_kaggle"
    batch_files = sorted(list(processed_dir.glob("batch_*.json")))
    
    total_files = len(batch_files)
    logger.info(f"📂 Found {total_files} local batch files.")
    
    # 3. Calculate Resume Point
    # User reported crash again.
    # Current Count: 174,629.
    # Delta from last resume (166k) = ~8,200 docs.
    # Means roughly 82 batches processed since Batch 173.
    # 173 + 82 = 255.
    # Safe Resume: Batch 250.
    
    FORCE_RESUME_INDEX = 250
    batches_done = FORCE_RESUME_INDEX
    
    if batches_done >= total_files:
        logger.info("✅ All files seem to be processed based on FORCE_RESUME_INDEX.")
        return

    files_to_process = batch_files[batches_done:]
    
    logger.info(f"⏭️  Forcing Resume from Batch Index {batches_done} (File: {files_to_process[0].name})")
    logger.info(f"📊 Remaining Batches: {len(files_to_process)}")
    
    # 4. Process Loop
    total_uploaded = 0
    
    for batch_file in files_to_process:
        print(f"\n📤 Migrating {batch_file.name}...")
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            # Use strict list passing
            store.add_documents(documents)
            total_uploaded += len(documents)
            print(f"  ✅ Success. Total Session Upload: {total_uploaded}")
            
        except Exception as e:
            logger.error(f"❌ Failed {batch_file.name}: {e}")
            # Continue to next batch? Yes.
            continue
            
    print("\n✅ RECOVERY COMPLETE!")
    print(f"Total Added: {total_uploaded}")
    print(f"New DB Count (Est): {current_count + total_uploaded}")

if __name__ == "__main__":
    main()
