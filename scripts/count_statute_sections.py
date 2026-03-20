import json
from pathlib import Path

def count_sections():
    json_dir = Path('DATA/Statutes/json')
    files = list(json_dir.glob('*.json'))
    print(f"{'File':<40} | {'Sections':<10}")
    print("-" * 55)
    for f in files:
        if f.name == 'summary.json': continue
        try:
            with open(f, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
                if 'sections' in data:
                    print(f"{f.name:<40} | {len(data['sections']):<10}")
                else:
                    print(f"{f.name:<40} | No 'sections' key")
        except Exception as e:
            print(f"{f.name:<40} | Error: {e}")

if __name__ == "__main__":
    count_sections()
