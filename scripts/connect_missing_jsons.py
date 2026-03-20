import json
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path.cwd()))
from rag_system.core.hybrid_chroma_store import HybridChromaStore

def connect_missing():
    print("--- Connecting High-Value Missing JSONs ---")
    store = HybridChromaStore()
    
    missing_files = [
        "consumer_law_specifics.json",
        "law_transitions_2024.json",
        "pwdva_comprehensive.json",
        "specific_gap_fix_cases.json",
        "landmark_legal_cases.json",
        "landmark_legal_cases_expansion.json",
        "NCDRC/ncdrc_landmark_cases.json"
    ]
    
    data_dir = Path("DATA")
    
    for filename in missing_files:
        p = data_dir / filename
        if not p.exists():
            print(f"Skipping {filename} (not found)")
            continue
            
        print(f"Ingesting {filename}...")
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        docs = []
        # Support both 'documents' key and list-at-root
        items = data.get('documents', data) if isinstance(data, dict) else data
        
        for i, item in enumerate(items):
            text = f"SOURCE: {filename}\n"
            if isinstance(item, dict):
                text += f"TITLE: {item.get('title', item.get('case_name', ''))}\n\n"
                text += item.get('content', item.get('text', item.get('description', json.dumps(item))))
            else:
                text += str(item)
                
            docs.append({
                "id": f"final_connect_{filename}_{i}",
                "text": text,
                "metadata": {"source": filename, "type": "knowledge_file"}
            })
            
        store.add_documents(docs, batch_size=50)
        print(f"✅ Connected {len(docs)} documents from {filename}")
    
    print("--- Rebuilding Index ---")
    store.rebuild_index()
    print("ALL CONNECTED SUCCESSFULY")

if __name__ == "__main__":
    connect_missing()
