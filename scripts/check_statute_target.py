import chromadb
from sentence_transformers import SentenceTransformer
import os

def check_statute_data():
    print("=== TARGETED STATUTE DATA AUDIT (ASCII SAFE) ===")
    
    statute_path = "chroma_db_statutes"
    if not os.path.exists(statute_path):
        print("ERROR: Statute DB not found.")
        return

    try:
        client = chromadb.PersistentClient(path=statute_path)
        collection = client.get_collection(name="legal_db_statutes")
        
        print(f"Total Sections in Statutes DB: {collection.count()}")
        
        sections_to_check = [
            {"act": "IB Code 2016", "num": "14", "label": "Moratorium"},
            {"act": "Insolvency and Bankruptcy Code 2016", "num": "14", "label": "Moratorium (Alt Name)"},
            {"act": "IB Code 2016", "num": "53", "label": "Waterfall"},
            {"act": "Consumer Protection Act 2019", "num": "2", "label": "Definitions"}
        ]

        for item in sections_to_check:
            print(f"\nChecking: {item['act']} Section {item['num']} ({item['label']})...")
            res = collection.get(
                where={"$and": [
                    {"act": item['act']},
                    {"section_number": item['num']}
                ]}
            )
            if res['ids']:
                print(f"[OK] FOUND: {item['act']} Section {item['num']} exists.")
                text = res['documents'][0][:100].replace('\n', ' ')
                print(f"    Excerpt: {text}...")
            else:
                print(f"[FAIL] NOT FOUND: {item['act']} Section {item['num']} is missing.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_statute_data()
