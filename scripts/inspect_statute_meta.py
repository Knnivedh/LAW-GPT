import sqlite3

def inspect_statute_meta():
    conn = sqlite3.connect('chroma_db_hybrid/chroma.sqlite3')
    c = conn.cursor()

    # Get sample IDs for statute source
    c.execute("""
        SELECT id FROM embedding_metadata 
        WHERE key = 'source' AND string_value = 'statute' 
        LIMIT 5
    """)
    ids = [r[0] for r in c.fetchall()]
    
    if not ids:
        print("No statutes found")
        return

    print(f"Inspecting metadata for 5 IDs: {ids}")
    for doc_id in ids:
        print(f"\n--- Metadata for ID {doc_id} ---")
        c.execute("SELECT key, string_value FROM embedding_metadata WHERE id = ?", (doc_id,))
        for k, v in c.fetchall():
            print(f"  {k}: {v}")

    conn.close()

if __name__ == "__main__":
    inspect_statute_meta()
