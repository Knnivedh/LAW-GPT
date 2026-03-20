import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.getcwd())

from rag_system.core.hybrid_chroma_store import HybridChromaStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_statutes():
    # Setup paths
    json_dir = Path("DATA/Statutes/json")
    persist_dir = "chroma_db_statutes"
    collection_name = "legal_db_statutes"

    # Initialize specialized store
    # This won't conflict with the 5GB legal_db_hybrid
    store = HybridChromaStore(
        persist_directory=persist_dir,
        collection_name=collection_name
    )

    all_records = []
    
    # Load all JSON statutes
    for file_path in json_dir.glob("*.json"):
        if file_path.name == "summary.json": continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            act_name = data.get('act_name', file_path.stem.replace("_", " "))
            sections = data.get('sections', [])
            
            logger.info(f"Processing {act_name} ({len(sections)} sections)...")
            
            for i, section in enumerate(sections):
                sec_num = section.get('section_number', str(i+1))
                sec_title = section.get('section_title', 'No Title')
                content = section.get('content', '')
                
                # Format text for embedding/search
                text = f"""Act: {act_name}
Section: {sec_num} ({sec_title})
Content: {content}"""
                
                # Check for duplicates or empty
                if not content: continue
                
                all_records.append({
                    'id': f"STAT_{file_path.stem}_{i:04d}",
                    'text': text,
                    'metadata': {
                        'domain': 'statutes',
                        'act': act_name,
                        'section_number': sec_num,
                        'section_title': sec_title,
                        'source_file': file_path.name
                    }
                })
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    if not all_records:
        logger.warning("No statute records found to ingest.")
        return

    logger.info(f"Ingesting {len(all_records)} refined statute sections into {collection_name}...")
    
    # Bulk add
    store.add_documents(all_records, batch_size=200)
    
    logger.info("="*60)
    logger.info(f"SUCCESS: Ingested {len(all_records)} sections into {collection_name}")
    logger.info(f"Persistence directory: {persist_dir}")
    logger.info("="*60)

if __name__ == "__main__":
    ingest_statutes()
