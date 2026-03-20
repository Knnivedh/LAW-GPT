import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def verify_connection():
    store = HybridChromaStore()
    collection = store.collection
    
    knowledge_files = [
        "consumer_law_specifics",
        "law_transitions_2024",
        "pwdva_comprehensive",
        "specific_gap_fix_cases",
        "landmark_legal_cases",
        "landmark_legal_cases_expansion",
        "ncdrc_landmark_cases",
        "statutes"
    ]
    
    print(f"Total documents in collection: {collection.count()}")
    
    results = {}
    
    for prefix in knowledge_files:
        # Try to find IDs starting with the prefix
        # Chroma doesn't have a direct 'startswith' get, so we'll try a small sample or check metadata if possible
        # Actually, let's use the 'where' clause on 'source' metadata
        try:
            # Most of these use the filename as 'source' in metadata or as prefix of ID
            count = collection.get(
                where={"source": {"$in": [f"{prefix}.json", prefix]}},
                include=[]
            )
            found_count = len(count['ids'])
            
            if found_count == 0:
                # Try prefix-based ID search (limited)
                # This is more expensive if we don't have a good index, but let's try a few samples
                # IDs are like 'consumer_law_specifics_0'
                sample = collection.get(
                    ids=[f"{prefix}_{i}" for i in range(5)],
                    include=[]
                )
                found_count = len(sample['ids'])
                if found_count > 0:
                    results[prefix] = f"Found (sample check: {found_count} docs)"
                else:
                    results[prefix] = "NOT FOUND"
            else:
                results[prefix] = f"Found ({found_count} docs)"
        except Exception as e:
            results[prefix] = f"Error: {e}"

    print("\nConnection Verification Report:")
    print("-" * 40)
    for file, status in results.items():
        print(f"{file:30} : {status}")
    print("-" * 40)

if __name__ == "__main__":
    verify_connection()
