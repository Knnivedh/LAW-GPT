import json
from pathlib import Path

def count_chunks():
    json_dir = Path('DATA/Statutes/json')
    files = list(json_dir.glob('*.json'))
    print(f"{'File':<40} | {'Chunks':<10}")
    print("-" * 55)
    for f in files:
        if f.name == 'summary.json': continue
        try:
            with open(f, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
                print(f"{f.name:<40} | {len(data):<10}")
        except Exception as e:
            print(f"{f.name:<40} | Error: {e}")

if __name__ == "__main__":
    count_chunks()
