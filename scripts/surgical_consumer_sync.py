import sys
import os
import uuid
import json
from pathlib import Path

# Add project root to path
project_root = Path(str(Path(__file__).resolve().parent))
sys.path.insert(0, str(project_root))

from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection
import rag_config

# Filtered Sync List
SYCN_FILES = [
    "DATA/Consumer_QA_Harvest.json",
    "DATA/Statutes/Consumer_Protection_E-Commerce_Rules_2020.txt",
    "DATA/Statutes/Consumer_Protection_Mediation_Rules_2020.txt",
    "DATA/Statutes/CCPA_Prevention_of_Misleading_Advertisements_Guidelines_2022.txt",
    "DATA/Statutes/Consumer_Protection_Direct_Selling_Rules_2021.txt"
]

def main():
    print("FINAL CONSUMER DATA SYNC...")
    embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    
    connections.connect(
        alias="default",
        uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
        token=rag_config.ZILLIZ_TOKEN
    )
    
    collection = Collection(rag_config.ZILLIZ_COLLECTION_NAME)
    collection.load()
    
    ids, vectors, texts, metadatas = [], [], [], []
    
    # 1. Harvested QA
    harv_path = project_root / "DATA/Consumer_QA_Harvest.json"
    if harv_path.exists():
        print(f"Ingesting {harv_path.name}...")
        with open(harv_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for doc in data.get("documents", []):
                text = doc.get("content", "")
                embedding = embed_model.encode(text).tolist()
                ids.append(f"cons_harv_{uuid.uuid4().hex[:8]}")
                vectors.append(embedding)
                texts.append(text)
                metadatas.append({
                    "source": doc.get("source", "Harvest"),
                    "title": doc.get("title"),
                    "domain": "consumer",
                    "type": "QA"
                })

    # 2. SC Judgments (2021-2025)
    sc_dir = project_root / "DATA/SC_Judgments_FULL/consumer_filtered"
    if sc_dir.exists():
        print("Ingesting SC Judgments (2021-2025)...")
        for f in sc_dir.glob("*.txt"):
            year = f.name[:4]
            if year in ["2021", "2022", "2023", "2024", "2025"]:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                    # Split into chunks if too long for Zilliz (max 65535)
                    max_chars = 60000
                    chunks = [content[i:i+max_chars] for i in range(0, len(content), max_chars)]
                    
                    for idx, chunk in enumerate(chunks):
                        embedding = embed_model.encode(chunk).tolist()
                        chunk_id = f"cons_sc_{year}_{uuid.uuid4().hex[:4]}_{idx}"
                        ids.append(chunk_id)
                        vectors.append(embedding)
                        texts.append(chunk)
                        metadatas.append({
                            "source": f.name,
                            "year": year,
                            "domain": "consumer",
                            "type": "judgment",
                            "chunk": idx
                        })

    if ids:
        print(f"Inserting {len(ids)} items...")
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i+batch_size]
            b_vecs = vectors[i:i+batch_size]
            b_txts = texts[i:i+batch_size]
            b_meta = metadatas[i:i+batch_size]
            collection.insert([b_ids, b_vecs, b_txts, b_meta])
            print(f"  Batch {i} done")
        collection.flush()
        print("Final Sync Complete.")
    else:
        print("No new data found for surgical sync.")

if __name__ == "__main__":
    main()
