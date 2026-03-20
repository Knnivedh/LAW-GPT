import sqlite3

def list_act_names():
    conn = sqlite3.connect('chroma_db_hybrid/chroma.sqlite3')
    c = conn.cursor()
    c.execute("SELECT string_value, COUNT(*) FROM embedding_metadata WHERE key = 'act_name' GROUP BY string_value")
    results = dict(c.fetchall())
    print("=== Acts in DB ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    conn.close()

if __name__ == "__main__":
    list_act_names()
