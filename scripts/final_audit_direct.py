import chromadb
import os

def final_audit():
    print("=== FINAL DATA CONNECTION AUDIT (Direct DB Query) ===")
    
    # Path to chroma_db_hybrid
    persist_path = "chroma_db_hybrid"
    
    if not os.path.exists(persist_path):
        print(f"ERROR: DB path not found: {persist_path}")
        return

    try:
        client = chromadb.PersistentClient(path=persist_path)
        collection = client.get_collection(name="legal_db_hybrid")
        
        total_count = collection.count()
        print(f"Total documents in Main RAG: {total_count:,}")
        
        # We'll check for specific sources in metadata
        targets = [
            "consumer_law_specifics.json",
            "law_transitions_2024.json",
            "pwdva_comprehensive.json",
            "specific_gap_fix_cases.json",
            "landmark_legal_cases.json",
            "landmark_legal_cases_expansion.json",
            "ncdrc_landmark_cases.json",
            "tax_law.json",
            "labour_law.json",
            "ip_law.json",
            "cyber_law.json"
        ]
        
        print("\nConnection Status by File:")
        print("-" * 50)
        for target in targets:
            try:
                # Use 'where' to filter by source
                res = collection.get(where={"source": target}, include=[])
                count = len(res['ids'])
                status = "✅ CONNECTED" if count > 0 else "❌ NOT CONNECTED"
                print(f"{target:35} | {count:5} docs | {status}")
            except Exception as e:
                print(f"{target:35} | ERROR: {e}")
        
        # Also check Statutes (dedicated store)
        print("\n" + "="*50)
        print("Dedicated Statutes Store Audit:")
        statute_path = "chroma_db_statutes"
        if os.path.exists(statute_path):
            s_client = chromadb.PersistentClient(path=statute_path)
            s_collection = s_client.get_collection(name="legal_db_statutes")
            print(f"dedicated_statutes_store       | {s_collection.count():5} docs | ✅ CONNECTED")
        else:
            print(f"dedicated_statutes_store       | NOT FOUND      | ❌ NOT CONNECTED")
        print("-" * 50)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    final_audit()
