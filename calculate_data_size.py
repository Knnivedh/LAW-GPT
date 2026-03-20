import os
import json

def count_text_stats(directory):
    total_chars = 0
    total_words = 0
    file_stats = []

    print(f"Scanning {directory}...")

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.json', '.txt')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        chars = len(content)
                        words = len(content.split())
                        
                        total_chars += chars
                        total_words += words
                        
                        file_stats.append({
                            "file": file,
                            "chars": chars,
                            "words": words
                        })
                except Exception as e:
                    print(f"Error reading {file}: {e}")

    return total_chars, total_words, file_stats

def main():
    base_dirs = [
        str(Path(__file__).resolve().parent / "DATA"),
        str(Path(__file__).resolve().parent / "kaanoon_test")
    ]
    
    grand_total_chars = 0
    grand_total_words = 0
    
    print(f"{'File':<50} | {'Words':<10} | {'Size (MB)':<10}")
    print("-" * 80)

    for d in base_dirs:
        if os.path.exists(d):
            chars, words, stats = count_text_stats(d)
            grand_total_chars += chars
            grand_total_words += words
            
            # Sort by size and print top 10 biggest files
            stats.sort(key=lambda x: x['chars'], reverse=True)
            for s in stats[:5]:
                size_mb = s['chars'] / (1024 * 1024)
                print(f"{s['file']:<50} | {s['words']:<10} | {size_mb:.2f} MB")

    print("-" * 80)
    
    # Token estimation (rough rule of thumb: 1 token ~= 4 chars)
    total_tokens = grand_total_chars / 4
    
    print(f"\n📊 TOTAL DATASET STATISTICS:")
    print(f"Total Characters: {grand_total_chars:,}")
    print(f"Total Words:      {grand_total_words:,}")
    print(f"Estimated Tokens: {int(total_tokens):,} (approx)")
    print(f"Total Size:       {grand_total_chars / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
