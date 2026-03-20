"""
Consumer Data Master Ingestion Script
Ingests core statutes, landmark judgments, and processed case data into Zilliz Cloud.
"""

import sys
import os
import uuid
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / "config" / ".env")

from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection
import rag_config

# Files to ingest
CONSUMER_FILES = [
    "DATA/Statutes/Consumer_Protection_E-Commerce_Rules_2020.txt",
    "DATA/Statutes/Consumer_Protection_Mediation_Rules_2020.txt",
    "DATA/Statutes/CCPA_Prevention_of_Misleading_Advertisements_Guidelines_2022.txt",
    "DATA/Statutes/Consumer_Protection_Direct_Selling_Rules_2021.txt",
    "DATA/Landmark_Consumer_Judgments_2020_2024.txt",
    "DATA/NCDRC/ncdrc_landmark_cases.json",
    "DATA/consumer_law_specifics.json",
    "DATA/Consumer_QA_Harvest.json"
]

# Add directory crawling
CONSUMER_DIRS = [
    "DATA/CaseLaw/Consumer",
    "DATA/SC_Judgments_FULL/consumer_filtered"
]

def get_all_files():
    all_files = list(CONSUMER_FILES)
    for d in CONSUMER_DIRS:
        dir_path = project_root / d
        if dir_path.exists():
            for f in dir_path.glob("*.txt"):
                all_files.append(str(f.relative_to(project_root)).replace("\\", "/"))
    return all_files

def main():
    print("="*60)
    print("CONSUMER DATA MASTER INGESTION - CLOUD")
    print("="*60)
    
    # 1. Load Model
    print("\n[1/4] Loading embedding model...")
    embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    print("  [OK] Embedding model loaded")
    
    # 2. Connect
    print("\n[2/4] Connecting to Zilliz Cloud...")
    connections.connect(
        alias="default",
        uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
        token=rag_config.ZILLIZ_TOKEN
    )
    print(f"  [OK] Connected to: {rag_config.ZILLIZ_CLUSTER_ENDPOINT}")
    
    # 3. Access Collection
    collection_name = rag_config.ZILLIZ_COLLECTION_NAME
    collection = Collection(collection_name)
    collection.load()
    print(f"  [OK] Collection loaded. Count: {collection.num_entities}")
    
    # 4. Ingest Files
    print("\n[4/4] Processing files...")
    
    ids, vectors, texts, metadatas = [], [], [], []
    
    for file_path in get_all_files():
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"  [SKIP] File not found: {file_path}")
            continue
            
        print(f"  [INGESTING] {file_path}...")
        
        if file_path.endswith(".json"):
            import json
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle list of cases (ncdrc_landmark_cases.json)
            if isinstance(data, list):
                for case in data:
                    text = f"Case: {case.get('case_name')}\nCourt: {case.get('court')}\nTopic: {case.get('topic')}\nSummary: {case.get('summary')}\nRatio: {case.get('ratio')}"
                    embedding = embed_model.encode(text).tolist()
                    ids.append(f"cons_json_{uuid.uuid4().hex[:8]}")
                    vectors.append(embedding)
                    texts.append(text)
                    metadatas.append({
                        "source": case.get("case_name", "Unknown Case"),
                        "type": "landmark_precedent",
                        "domain": "consumer",
                        "year": case.get("year")
                    })
            # Handle structured docs (consumer_law_specifics.json)
            elif isinstance(data, dict) and "documents" in data:
                for doc in data["documents"]:
                    text = f"Title: {doc.get('title')}\nContent: {doc.get('content')}"
                    embedding = embed_model.encode(text).tolist()
                    ids.append(f"cons_spec_{uuid.uuid4().hex[:8]}")
                    vectors.append(embedding)
                    texts.append(text)
                    metadatas.append({
                        "source": doc.get("title", "Consumer Guide"),
                        "type": "guide",
                        "domain": "consumer",
                        "category": doc.get("category")
                    })
        else:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Treat landmark judgments differently (split by entry)
            if "Landmark" in file_path:
                entries = content.split("\n\n")
                for entry in entries:
                    if len(entry.strip()) < 50: continue
                    embedding = embed_model.encode(entry).tolist()
                    ids.append(f"cons_land_{uuid.uuid4().hex[:8]}")
                    vectors.append(embedding)
                    texts.append(entry)
                    metadatas.append({"source": "Landmark Judgments", "type": "precedent", "domain": "consumer"})
            else:
                # Statutes: split by section or just by paragraphs if no section markers found
                paragraphs = [p for p in content.split("\n\n") if len(p.strip()) > 30]
                for p in paragraphs:
                    embedding = embed_model.encode(p).tolist()
                    ids.append(f"cons_stat_{uuid.uuid4().hex[:8]}")
                    vectors.append(embedding)
                    texts.append(p)
                    metadatas.append({"source": file_path.split("/")[-1], "type": "statute", "domain": "consumer"})
    
    if ids:
        try:
            # Milvus batch limit handling
            batch_size = 500
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_vectors = vectors[i:i+batch_size]
                batch_texts = texts[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]
                
                collection.insert([batch_ids, batch_vectors, batch_texts, batch_metadatas])
                print(f"  [OK] Batched insert {i} to {i+len(batch_ids)}")
                
            collection.flush()
            print(f"\nSUCCESS: Ingested {len(ids)} consumer law entities.")
        except Exception as e:
            print(f"  [ERROR] Insertion failed: {e}")
    else:
        print("  [WARN] No data to ingest.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
