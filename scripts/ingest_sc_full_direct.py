"""
SC_Judgments_FULL Direct Ingestion
===================================
Adds 26,606 Supreme Court judgment chunks directly to ChromaDB SQLite.
Uses memory-efficient batch processing with SentenceTransformer on GPU.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
import time
import gc
from sentence_transformers import SentenceTransformer

def ingest_sc_full():
    print("="*70)
    print("  SC_JUDGMENTS_FULL DIRECT INGESTION")
    print("  26,606 Supreme Court Judgments (1950-2024)")
    print("="*70)
    
    start_time = time.time()
    
    # Paths
    sc_dir = Path("DATA/SC_Judgments_FULL/chunks")
    db_path = "chroma_db_hybrid/chroma.sqlite3"
    
    # Connect to database
    print("\n[1/4] Connecting to ChromaDB SQLite...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get segment_id for the collection
    cursor.execute("""
        SELECT id FROM segments 
        WHERE collection = (SELECT id FROM collections WHERE name = 'legal_db_hybrid')
        AND type LIKE '%metadata%'
    """)
    segment_row = cursor.fetchone()
    if not segment_row:
        print("ERROR: Could not find segment for legal_db_hybrid")
        return
    segment_id = segment_row[0]
    print(f"    Segment ID: {segment_id}")
    
    # Get current max ID
    cursor.execute("SELECT MAX(id) FROM embeddings")
    max_id = cursor.fetchone()[0] or 0
    print(f"    Current max ID: {max_id}")
    
    # Load embedding model
    print("\n[2/4] Loading embedding model (GPU)...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print(f"    Model loaded on: {model.device}")
    
    # Get years to process
    years = sorted([d.name for d in sc_dir.iterdir() if d.is_dir() and d.name.isdigit()])
    print(f"\n[3/4] Processing {len(years)} years ({years[0]} to {years[-1]})...")
    
    total_added = 0
    batch_size = 100
    current_id = max_id + 1
    
    for year_idx, year in enumerate(years):
        year_path = sc_dir / year
        chunk_files = list(year_path.glob("*_chunks.json"))
        
        year_texts = []
        year_ids = []
        year_metas = []
        
        for cf in chunk_files:
            try:
                with open(cf, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                    for chunk in chunks:
                        if 'chunk_id' in chunk and 'text' in chunk:
                            year_ids.append(chunk['chunk_id'])
                            year_texts.append(chunk['text'][:5000])  # Limit text length
                            year_metas.append({
                                'source': 'SC_Judgments_FULL',
                                'case_name': chunk.get('case_name', ''),
                                'year': str(chunk.get('year', year)),
                                'petitioner': chunk.get('petitioner', ''),
                                'respondent': chunk.get('respondent', ''),
                                'judgment_date': chunk.get('judgment_date', ''),
                                'section': chunk.get('section', '')
                            })
            except Exception as e:
                continue
        
        if not year_texts:
            continue
        
        # Process in batches
        for i in range(0, len(year_texts), batch_size):
            batch_ids = year_ids[i:i+batch_size]
            batch_texts = year_texts[i:i+batch_size]
            batch_metas = year_metas[i:i+batch_size]
            
            # Generate embeddings
            embeddings = model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=True)
            
            # Insert into database
            for j, (doc_id, text, meta, emb) in enumerate(zip(batch_ids, batch_texts, batch_metas, embeddings)):
                try:
                    # Insert embedding record
                    cursor.execute("""
                        INSERT OR IGNORE INTO embeddings (id, segment_id, embedding_id, seq_id)
                        VALUES (?, ?, ?, ?)
                    """, (current_id, segment_id, doc_id, current_id.to_bytes(8, 'big')))
                    
                    # Insert document text
                    cursor.execute("""
                        INSERT OR IGNORE INTO embedding_metadata (id, key, string_value)
                        VALUES (?, 'chroma:document', ?)
                    """, (current_id, text))
                    
                    # Insert source metadata
                    source = meta.get('source', 'SC_Judgments_FULL')
                    cursor.execute("""
                        INSERT OR IGNORE INTO embedding_metadata (id, key, string_value)
                        VALUES (?, 'source', ?)
                    """, (current_id, source))
                    
                    # Insert year metadata
                    cursor.execute("""
                        INSERT OR IGNORE INTO embedding_metadata (id, key, string_value)
                        VALUES (?, 'year', ?)
                    """, (current_id, year))
                    
                    current_id += 1
                    total_added += 1
                except sqlite3.IntegrityError:
                    pass  # Skip duplicates
            
            conn.commit()
        
        # Progress update
        progress = (year_idx + 1) / len(years) * 100
        elapsed = time.time() - start_time
        eta = (elapsed / (year_idx + 1)) * (len(years) - year_idx - 1) if year_idx > 0 else 0
        print(f"    Year {year}: {len(year_texts):,} chunks | Total: {total_added:,} | {progress:.0f}% | ETA: {eta/60:.0f}min")
        
        gc.collect()
    
    conn.commit()
    conn.close()
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print(f"  [4/4] COMPLETE!")
    print(f"  Added: {total_added:,} SC judgment chunks")
    print(f"  Time: {elapsed/60:.1f} minutes")
    print("="*70)

if __name__ == "__main__":
    ingest_sc_full()
