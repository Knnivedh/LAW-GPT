
import json
import os
import shutil

# Keywords to identify consumer data
# Expanded list for broader capture
KEYWORDS = [
    "consumer", "consumer protection", "ncdrc", "scdrc", "district forum", 
    "deficiency in service", "unfair trade practice", "refund", "compensation",
    "product liability", "consumer court", "consumer commission", "jago grahak jago",
    "section 12", "section 35", "section 47", "section 58", "district commission",
    "state commission", "national commission"
]

ROOT_DIR = str(Path(__file__).resolve().parent)
DEST_DIR = os.path.join(ROOT_DIR, "CONSUMER_DATA_COLLECTION")

IGNORE_DIRS = {".git", ".idea", "node_modules", "dist", "build", "__pycache__", "CONSUMER_DATA_COLLECTION", ".gemini", ".agent"}

def contains_keyword(text):
    if not text:
        return False
    text = str(text).lower()
    return any(kw in text for kw in KEYWORDS)

def process_file(file_path):
    try:
        # Skip small files or non-json first to save time, but user said "check each and every folder"
        # We focus on JSONs as they likely contain the structured data. 
        # But we will also check .txt files if they contain "Consumer" in the first few lines?
        # Sticking to JSON for high quality structured data first.
        
        if not file_path.lower().endswith(".json"):
            return 0

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return 0
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

    extracted_data = []
    
    if isinstance(data, list):
        for item in data:
            if contains_keyword(str(item)):
                extracted_data.append(item)
    elif isinstance(data, dict):
        if contains_keyword(str(data)):
             extracted_data.append(data)
             
    if extracted_data:
        # Create unique filename to avoid collisions
        rel_path = os.path.relpath(file_path, ROOT_DIR).replace(os.path.sep, "_")
        dest_path = os.path.join(DEST_DIR, f"extracted_{rel_path}")
        
        try:
            with open(dest_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Extracted {len(extracted_data)} records from {os.path.basename(file_path)}")
            return len(extracted_data)
        except Exception as e:
             print(f"Error writing to {dest_path}: {e}")
    
    return 0

def main():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
        
    print(f"Starting Recursive Consumer Data Extraction in {ROOT_DIR}...")
    
    total_records = 0
    files_processed = 0
    
    for root, dirs, files in os.walk(ROOT_DIR):
        # Filter directories to ignore
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            # Skip if file is in destination folder (redundancy check)
            if DEST_DIR in file_path:
                continue
                
            count = process_file(file_path)
            if count > 0:
                total_records += count
            files_processed += 1
            
            if files_processed % 100 == 0:
                print(f"Scanned {files_processed} files...")
        
    print(f"Alignment Complete. Total extracted records: {total_records}")

if __name__ == "__main__":
    main()
