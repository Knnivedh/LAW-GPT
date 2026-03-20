"""Quick database status check"""
import chromadb
from collections import Counter

client = chromadb.PersistentClient(path="chroma_db_hybrid")
coll = client.get_collection("legal_db_hybrid")
total = coll.count()

print(f"Total documents: {total:,}")

# Sample to get source breakdown
sample_size = min(total, 20000)
metas = coll.get(limit=sample_size, include=['metadatas'])
sources = Counter(m.get('source', 'Unknown') for m in metas['metadatas'])

print(f"\nSources (from {sample_size:,} samples):")
for source, count in sources.most_common():
    # Extrapolate if we sampled
    if sample_size < total:
        estimated = int(count * (total / sample_size))
        print(f"  {source}: ~{estimated:,} (sampled: {count:,})")
    else:
        print(f"  {source}: {count:,}")

print(f"\nDatabase size: 648 MB")
print(f"\nProgress analysis:")
print(f"  Supreme Court target: 26,688")
print(f"  Case Studies target: 50,000")
print(f"  Kanoon Q&A target: 102,176")
print(f"  Knowledge files target: ~43")
