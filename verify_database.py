"""
Database Verification Script
Check if ChromaDB contains the indexed data and if server is using it
"""

import chromadb
from pathlib import Path

print("="*80)
print("CHROMADB VERIFICATION")
print("="*80)

# Check the database that was used for ingestion
db_path = Path("chroma_db_hybrid").absolute()
print(f"\n1. Database Path: {db_path}")
print(f"   Exists: {db_path.exists()}")

if db_path.exists():
    print(f"   Size: {sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file()) / (1024*1024):.2f} MB")

# Connect to the database
print("\n2. Connecting to ChromaDB...")
client = chromadb.PersistentClient(path=str(db_path))

# List collections
collections = client.list_collections()
print(f"\n3. Collections found: {len(collections)}")
for coll in collections:
    print(f"   - {coll.name}")

# Check the main collection
if collections:
    collection = client.get_collection(name="legal_db_hybrid")
    count = collection.count()
    
    print(f"\n4. Collection 'legal_db_hybrid' stats:")
    print(f"   Total documents: {count:,}")
    
    # Sample a few documents to see their sources
    if count > 0:
        sample = collection.get(limit=10, include=['metadatas'])
        
        print(f"\n5. Sample document sources:")
        sources = {}
        for meta in sample['metadatas']:
            source = meta.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        for source, count_src in sorted(sources.items()):
            print(f"   - {source}: {count_src}")
        
        # Check for specific sources we indexed
        print(f"\n6. Searching for recently indexed data...")
        
        # Try to find Supreme Court cases
        try:
            sc_results = collection.get(
                where={"source": {"$eq": "Supreme Court Kaggle"}},
                limit=5
            )
            print(f"   Supreme Court cases found: {len(sc_results['ids'])}")
        except:
            print(f"   Supreme Court cases: 0 (or error querying)")
        
        # Try to find Case Studies
        try:
            cs_results = collection.get(
                where={"source": {"$eq": "Indian Case Studies 50K"}},
                limit=5
            )
            print(f"   Case Studies found: {len(cs_results['ids'])}")
        except:
            print(f"   Case Studies: 0 (or error querying)")
    
    # Get all unique sources by querying with limit
    print(f"\n7. All unique sources in database:")
    all_docs = collection.get(limit=1000, include=['metadatas'])
    all_sources = set()
    for meta in all_docs['metadatas']:
        all_sources.add(meta.get('source', 'Unknown'))
    
    for source in sorted(all_sources):
        print(f"   - {source}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
