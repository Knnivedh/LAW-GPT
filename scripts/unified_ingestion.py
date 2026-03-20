import json
import sys
import os
from pathlib import Path
from tqdm import tqdm

# Add parent dir to path to import rag_system
sys.path.append(str(Path("c:/Users/LOQ/Downloads/LAW-GPT_new/LAW-GPT_new/LAW-GPT")))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def ingest_statutes():
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_dir = Path("DATA/Statutes/json")
    json_files = list(json_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != "summary.json"]
    
    print(f"Found {len(json_files)} statute files for ingestion.")
    
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        act_name = data.get('act_name', json_file.stem)
        sections = data.get('sections', [])
        
        docs_to_add = []
        for i, section in enumerate(sections):
            doc_id = f"statute_{json_file.stem}_{section.get('section_number', i)}"
            text = f"ACT: {act_name}\nSECTION: {section.get('section_number')}\nTITLE: {section.get('section_title')}\n\n{section.get('content')}"
            
            metadata = {
                'source': 'statute',
                'act_name': act_name,
                'section_number': str(section.get('section_number')),
                'section_title': section.get('section_title', ''),
                'type': 'statute_section'
            }
            docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
        
        if docs_to_add:
            store.add_documents(docs_to_add, batch_size=100)
            print(f"DONE: Ingested {len(docs_to_add)} sections from {act_name}")

def ingest_sc_judgments(limit_batches=None, start_batch=0):
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    kaggle_dir = Path("DATA/processed_kaggle")
    batch_files = sorted(list(kaggle_dir.glob("batch_*.json")))
    
    if start_batch:
        batch_files = batch_files[start_batch:]
        
    if limit_batches:
        batch_files = batch_files[:limit_batches]
    
    print(f"Found {len(batch_files)} judgment batches for ingestion (starting from index {start_batch}).")
    
    for batch_file in tqdm(batch_files, desc="Processing SC Batches"):
        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
        
        docs_to_add = []
        for i, entry in enumerate(batch_data):
            # The entry already has 'text' and 'metadata' from the earlier extraction
            doc_id = f"scj_{batch_file.stem}_{i}"
            
            # Clean metadata for ChromaDB (no lists)
            metadata = entry.get('metadata', {}).copy()
            metadata['source'] = 'sc_judgment'
            metadata['type'] = 'case_law'
            
            docs_to_add.append({
                'id': doc_id,
                'text': entry['text'],
                'metadata': metadata
            })
        
        if docs_to_add:
            store.add_documents(docs_to_add, batch_size=50)

def ingest_ncdrc_landmark():
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_path = Path("DATA/NCDRC/ncdrc_landmark_cases.json")
    
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return
        
    print(f"Processing {json_path.name}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs_to_add = []
    for i, entry in enumerate(data):
        doc_id = f"ncdrc_l_{i}"
        text = f"COURT: {entry.get('court')}\nCASE: {entry.get('case_name')}\nTOPIC: {entry.get('topic')}\nSUMMARY: {entry.get('summary')}\nRATIO: {entry.get('ratio')}"
        
        metadata = entry.get('metadata', {}).copy()
        metadata.update({
            'case_name': entry.get('case_name'),
            'court': entry.get('court'),
            'type': 'case_law',
            'year': str(entry.get('year'))
        })
        docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
    
    if docs_to_add:
        store.add_documents(docs_to_add, batch_size=10)
        print(f"DONE: Ingested {len(docs_to_add)} NCDRC landmark cases.")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode in ["statutes", "all"]:
        print("\n--- INGESTING STATUTES ---")
        ingest_statutes()
    
    if mode in ["judgments", "all"]:
        print("\n--- INGESTING SC JUDGMENTS ---")
        limit_arg = sys.argv[2] if len(sys.argv) > 2 else "None"
        limit = int(limit_arg) if limit_arg.isdigit() else None
        start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        ingest_sc_judgments(limit_batches=limit, start_batch=start)
        
    if mode == "ncdrc":
        print("\n--- INGESTING NCDRC LANDMARK CASES ---")
        ingest_ncdrc_landmark()
