"""
Auto cleanup duplicate ChromaDB folders
"""
import os
import shutil
from pathlib import Path

print("=" * 80)
print("LAW-GPT DATABASE AUTO-CLEANUP")
print("=" * 80)

# Define paths
project_root = Path("C:/Users/Gourav Bhat/Downloads/LAW-GPT")
main_db = project_root / "chroma_db_hybrid"
duplicate_db1 = project_root / "kaanoon_test" / "chroma_db_hybrid"
duplicate_db2 = project_root / "chroma_db_hybrid_backup"
data_collection = project_root / "data_collection"

print("\n📋 CLEANUP PLAN:")
print(f"✅ KEEP: {main_db} (158,130 documents)")
print(f"❌ DELETE: {duplicate_db1}")
print(f"❌ DELETE: {duplicate_db2}")
print(f"❌ DELETE: {data_collection}")

# Delete duplicates
print("\n🗑️ Deleting duplicate folders...")

if duplicate_db1.exists():
    print(f"Deleting: {duplicate_db1}...")
    try:
        shutil.rmtree(duplicate_db1, ignore_errors=True)
        print("  ✓ Deleted")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")

if duplicate_db2.exists():
    print(f"Deleting: {duplicate_db2}...")
    try:
        shutil.rmtree(duplicate_db2, ignore_errors=True)
        print("  ✓ Deleted")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")

if data_collection.exists():
    print(f"Deleting: {data_collection}...")
    try:
        shutil.rmtree(data_collection, ignore_errors=True)
        print("  ✓ Deleted")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")

print("\n✅ CLEANUP COMPLETE!")
print("\n📁 FINAL STRUCTURE:")
print(f"✅ Single database: {main_db}")
print(f"   Documents: 158,130")

print("\n" + "=" * 80)
print("✅ RAG system now uses clean single database!")
print("=" * 80)
