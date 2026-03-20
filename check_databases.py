import chromadb
import os

print("=" * 80)
print("CHECKING ALL CHROMADB FOLDERS")
print("=" * 80)

paths = [
    'C:/Users/Gourav Bhat/Downloads/LAW-GPT/chroma_db_hybrid',
    'C:/Users/Gourav Bhat/Downloads/LAW-GPT/kaanoon_test/chroma_db_hybrid',
    'C:/Users/Gourav Bhat/Downloads/LAW-GPT/chroma_db_hybrid_backup',
    'C:/Users/Gourav Bhat/Downloads/LAW-GPT/data_collection'
]

for path in paths:
    if os.path.exists(path):
        try:
            client = chromadb.PersistentClient(path=path)
            collection = client.get_collection('legal_db_hybrid')
            count = collection.count()
            print(f"\n✓ {path}")
            print(f"  Documents: {count:,}")
        except Exception as e:
            print(f"\n⚠️ {path}")
            print(f"  Error: {e}")
    else:
        print(f"\n✗ {path}")
        print(f"  NOT FOUND")

print(f"\n{'=' * 80}")
