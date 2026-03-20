import os
from pathlib import Path

# Paths
source_dir = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA\SC_Judgments_FULL\text")
target_dir = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA\SC_Judgments_FULL\consumer_filtered")

# Keywords
KEYWORDS = [
    "Consumer Protection Act",
    "NCDRC",
    "District Forum",
    "State Commission",
    "Deficiency in Service",
    "Defect in Goods",
    "Unfair Trade Practice",
    "National Consumer Disputes Redressal"
]

def main():
    if not target_dir.exists():
        target_dir.mkdir(parents=True)
    
    print(f"Scanning {source_dir}...")
    count = 0
    matched = 0
    
    # Use rglob for recursive scanning through year subdirectories
    for file_path in source_dir.rglob("*.txt"):
        count += 1
        if count % 1000 == 0:
            print(f"Processed {count} files...")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if any(kw.lower() in content.lower() for kw in KEYWORDS):
                    # Copy or record
                    target_file = target_dir / file_path.name
                    with open(target_file, 'w', encoding='utf-8') as tf:
                        tf.write(content)
                    matched += 1
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print(f"DONE. Scanned {count} files. Found {matched} consumer judgments.")

if __name__ == "__main__":
    main()
