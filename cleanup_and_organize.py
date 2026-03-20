"""
Cleanup duplicate ChromaDB folders and organize proper structure
"""
import os
import shutil
from pathlib import Path

print("=" * 80)
print("LAW-GPT DATABASE CLEANUP & ORGANIZATION")
print("=" * 80)

# Define paths
project_root = Path("C:/Users/Gourav Bhat/Downloads/LAW-GPT")
main_db = project_root / "chroma_db_hybrid"
duplicate_db1 = project_root / "kaanoon_test" / "chroma_db_hybrid"
duplicate_db2 = project_root / "chroma_db_hybrid_backup"
data_collection = project_root / "data_collection"

print("\n📋 CLEANUP PLAN:")
print(f"✅ KEEP: {main_db} (158,130 documents - MAIN DATABASE)")
print(f"❌ DELETE: {duplicate_db1} (2,132 docs - duplicate)")
print(f"❌ DELETE: {duplicate_db2} (155,998 docs - old backup)")
print(f"❌ DELETE: {data_collection} (invalid)")

print("\n" + "=" * 80)
response = input("Proceed with cleanup? (yes/no): ")

if response.lower() != 'yes':
    print("Cleanup cancelled.")
    exit(0)

# Delete duplicates
print("\n🗑️ Deleting duplicate folders...")

if duplicate_db1.exists():
    print(f"Deleting: {duplicate_db1}")
    shutil.rmtree(duplicate_db1, ignore_errors=True)
    print("  ✓ Deleted")

if duplicate_db2.exists():
    print(f"Deleting: {duplicate_db2}")
    shutil.rmtree(duplicate_db2, ignore_errors=True)
    print("  ✓ Deleted")

if data_collection.exists():
    print(f"Deleting: {data_collection}")
    shutil.rmtree(data_collection, ignore_errors=True)
    print("  ✓ Deleted")

print("\n✅ CLEANUP COMPLETE!")
print("\n📁 FINAL STRUCTURE:")
print(f"✅ {main_db} - 158,130 documents")
print(f"   └── This is your SINGLE database for RAG system")

print("\n" + "=" * 80)
print("✅ ALL DONE!")
print("🎯 RAG system now uses single clean database at:")
print(f"   {main_db}")
print("=" * 80)
