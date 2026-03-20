import sys
from pathlib import Path
import chromadb

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

def check():
    client = chromadb.PersistentClient(path="chroma_db_hybrid")
    collection = client.get_collection(name="legal_db_hybrid")
    
    print(f"Total: {collection.count()}")
    
    files = [
        "consumer_law_specifics",
        "law_transitions_2024",
        "pwdva_comprehensive",
        "specific_gap_fix_cases",
        "landmark_legal_cases",
        "landmark_legal_cases_expansion"
    ]
    
    for f in files:
        # Check source metadata
        res = collection.get(where={"source": f + ".json"}, include=[])
        print(f"{f:30}: {len(res['ids'])}")

if __name__ == "__main__":
    check()
