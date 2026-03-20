"""
RAG BACKUP SYSTEM
Creates a compressed backup of the permanent RAG database.
"""

import zipfile
import os
import datetime
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import rag_config

def create_backup():
    print("="*80)
    print("🛡️ RAG PERMANENT BACKUP SYSTEM")
    print("="*80)
    
    source_dir = rag_config.PERMANENT_ROOT
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"RAG_BACKUP_{timestamp}.zip"
    backup_path = rag_config.BACKUP_PATH / backup_filename
    
    print(f"Source: {source_dir}")
    print(f"Target: {backup_path}")
    
    if not source_dir.exists():
        print("❌ Error: Permanent storage directory not found!")
        return
        
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Don't backup the backup folder itself
                if str(rag_config.BACKUP_PATH) in root:
                    continue
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"\n✅ BACKUP SUCCESSFUL!")
        print(f"File: {backup_filename}")
        print(f"Size: {backup_path.stat().st_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    create_backup()
