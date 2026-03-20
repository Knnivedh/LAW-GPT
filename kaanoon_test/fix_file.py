from pathlib import Path

with open(str(Path(__file__).resolve().parent / 'system_adapters' / 'rag_system_adapter_ULTIMATE.py'), 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Delete lines 847-1646 (800 orphaned lines)
cleaned_lines = lines[:846] + lines[1646:]

with open(str(Path(__file__).resolve().parent / 'system_adapters' / 'rag_system_adapter_ULTIMATE.py'), 'w', encoding='utf-8') as f:
    f.writelines(cleaned_lines)

print(f'SUCCESS: Deleted lines 847-1646')
print(f'File now has {len(cleaned_lines)} lines (was {len(lines)})')
