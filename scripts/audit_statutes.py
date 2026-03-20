import sqlite3
import os
from pathlib import Path

def check_statutes():
    db_path = 'chroma_db_hybrid/chroma.sqlite3'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get all unique titles/filenames for statutes
    # We look for the 'source' = 'statute' and then get their metadata
    c.execute("""
        SELECT em_title.string_value, COUNT(*) 
        FROM embedding_metadata em_source
        JOIN embedding_metadata em_title ON em_source.id = em_title.id
        WHERE em_source.key = 'source' AND em_source.string_value = 'statute'
        AND em_title.key = 'title'
        GROUP BY em_title.string_value
    """)
    db_statutes = dict(c.fetchall())
    
    # Also check by 'filename' just in case
    c.execute("""
        SELECT em_file.string_value, COUNT(*) 
        FROM embedding_metadata em_source
        JOIN embedding_metadata em_file ON em_source.id = em_file.id
        WHERE em_source.key = 'source' AND em_source.string_value = 'statute'
        AND em_file.key = 'filename'
        GROUP BY em_file.string_value
    """)
    db_filenames = dict(c.fetchall())

    conn.close()

    json_dir = Path('DATA/Statutes/json')
    files = list(json_dir.glob('*.json'))
    
    print("=== AUDIT RESULTS ===")
    print(f"{'Statute File':<40} | {'In DB (Title)':<15} | {'In DB (Filename)':<15}")
    print("-" * 75)
    
    for f in files:
        if f.name == 'summary.json': continue
        
        # Strip extension for title comparison
        title = f.stem.replace('_', ' ')
        in_db_title = db_statutes.get(title, 0)
        
        # Check by filename
        in_db_file = db_filenames.get(f.name, 0)
        
        print(f"{f.name:<40} | {in_db_title:<15} | {in_db_file:<15}")

if __name__ == "__main__":
    check_statutes()
