"""Check ChromaDB schema"""
import sqlite3
conn = sqlite3.connect('chroma_db_hybrid/chroma.sqlite3')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables:", tables)

# Check each table structure
for table in tables[:10]:
    print(f"\n--- {table} ---")
    cursor.execute(f"PRAGMA table_info({table})")
    cols = cursor.fetchall()
    for c in cols:
        print(f"  {c[1]}: {c[2]}")
    
    # Sample row
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"  Sample: {str(row)[:100]}...")
    except:
        pass

conn.close()
