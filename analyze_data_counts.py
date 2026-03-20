import os
import json
from pathlib import Path

ROOT = Path(r"C:\Users\LOQ\Downloads\LAW-GPT_new")
BACKUP_DATA = ROOT / "BACKUP_DATA"

print("=" * 60)
print("MATHEMATICAL DATA COUNT DIAGNOSTIC")
print("=" * 60)

total_files = 0
total_json_items = 0
total_txt_lines = 0

for root, dirs, files in os.walk(BACKUP_DATA):
    for f in files:
        fpath = Path(root) / f
        total_files += 1
        
        if f.endswith('.json'):
            try:
                with open(fpath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        items = len(data)
                    elif isinstance(data, dict):
                        items = len(data.keys())
                    else:
                        items = 1
                    total_json_items += items
                    print(f"[JSON] {fpath.name}: {items} items")
            except Exception as e:
                print(f"[JSON ERROR] {fpath.name}: {e}")
                
        elif f.endswith('.txt'):
            try:
                with open(fpath, 'r', encoding='utf-8') as file:
                    lines = sum(1 for line in file)
                    total_txt_lines += lines
                    print(f"[TXT] {fpath.name}: {lines} lines")
            except Exception as e:
                print(f"[TXT ERROR] {fpath.name}: {e}")

print("=" * 60)
print("SUMMARY RESULTS")
print("=" * 60)
print(f"Total Files Scanned: {total_files}")
print(f"Total JSON Data Items: {total_json_items}")
print(f"Total TXT Lines: {total_txt_lines}")

# Estimate Chunks
estimated_txt_chunks = total_txt_lines // 10 # rough heuristic
total_estimated_chunks = estimated_txt_chunks + total_json_items
print(f"Total Estimated Chunks: {total_estimated_chunks}")

