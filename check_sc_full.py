"""Check if SC_Judgments_FULL is connected"""
import sqlite3
from pathlib import Path

# Database check
conn = sqlite3.connect('chroma_db_hybrid/chroma.sqlite3')
cursor = conn.cursor()

# Check SC related sources
cursor.execute("""
    SELECT string_value, COUNT(*) 
    FROM embedding_metadata 
    WHERE key='source' 
    GROUP BY string_value 
    ORDER BY COUNT(*) DESC
""")
print("=== All Sources in Database ===")
total = 0
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]:,}")
    total += r[1]
print(f"\nTotal documents: {total:,}")

# Check for sc_full specifically
cursor.execute("""
    SELECT COUNT(*) FROM embedding_metadata 
    WHERE key='source' AND string_value LIKE '%SC_Judgments_FULL%'
""")
sc_full = cursor.fetchone()[0]
print(f"\nSC_Judgments_FULL in DB: {sc_full}")

# Check chunk folder
sc_dir = Path("DATA/SC_Judgments_FULL/chunks")
if sc_dir.exists():
    files = list(sc_dir.rglob("*.json"))
    print(f"SC_Judgments_FULL folder: {len(files):,} JSON files")
    
    # Sample IDs from files
    sample_ids = []
    for f in files[:5]:
        name = f.stem.replace("_chunks", "")
        sample_ids.append(name)
    
    # Check if these IDs are in DB
    cursor.execute("""
        SELECT COUNT(*) FROM embeddings WHERE embedding_id LIKE ?
    """, (f"%{sample_ids[0][:30]}%",))
    found = cursor.fetchone()[0]
    print(f"\nSample check: '{sample_ids[0][:30]}...' found: {found}")

conn.close()
