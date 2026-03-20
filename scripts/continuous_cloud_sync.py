"""
CONTINUOUS CLOUD SYNC
Runs the universal crawler in a continuous loop with error recovery
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_ingestion():
    """Run universal crawler with error handling"""
    print("\n" + "="*80)
    print(f"[{time.strftime('%H:%M:%S')}] Starting Cloud Sync...")
    print("="*80)
    
    try:
        result = subprocess.run(
            ["python", "scripts/universal_crawl_ingest.py"],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            text=True
        )
        
        return result.returncode
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

def main():
    """Continuous sync loop"""
    attempt = 0
    while True:
        attempt += 1
        print(f"\n▶ SYNC ATTEMPT #{attempt}")
        
        returncode = run_ingestion()
        
        if returncode == 0:
            print("✅ Sync completed successfully!")
            break
        else:
            print(f"⚠ Sync failed (exit code: {returncode})")
            print("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
