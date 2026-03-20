
import os
import json
from pathlib import Path
from tqdm import tqdm
import hashlib

def generate_id(source, content):
    hash_seed = f"{source}_{content[:500]}"
    return hashlib.md5(hash_seed.encode('utf-8', errors='replace')).hexdigest()

def count_unique_docs():
    data_root = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA")
    all_json = list(data_root.glob("**/*.json"))
    
    unique_ids = set()
    total_found = 0
    
    print(f"Analyzing {len(all_json)} files...")
    
    for file_path in tqdm(all_json):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            source = file_path.parent.name
            items = data if isinstance(data, list) else [data]
            
            for entry in items:
                if not isinstance(entry, dict):
                    continue
                
                content = (entry.get('text') or entry.get('content') or 
                          entry.get('response_text') or entry.get('query_text') or str(entry))
                
                if len(str(content)) < 50:
                    continue
                
                doc_id = generate_id(source, str(content))
                unique_ids.add(doc_id)
                total_found += 1
        except:
            continue
            
    print(f"\nAnalysis Complete:")
    print(f"Total entries found in files: {total_found:,}")
    print(f"Total unique documents: {len(unique_ids):,}")
    print(f"Potential duplicates on disk: {total_found - len(unique_ids):,}")

if __name__ == "__main__":
    count_unique_docs()
