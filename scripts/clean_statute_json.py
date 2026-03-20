"""
Clean Statute JSON - Remove junk data
Filters out invalid sections like 'Cited by', empty sections, etc.
"""

import json
import re
from pathlib import Path

JSON_DIR = Path("DATA/Statutes/json")

# Patterns to identify junk sections
JUNK_PATTERNS = [
    r'^,?\s*Cited by\s*$',
    r'^\[\s*Cites\s*$',
    r'^\d+\s*$',  # Just numbers
    r'^,\s*$',     # Just commas
    r'^\]\s*$',    # Just brackets
    r'^Entire Act\s*$',
    r'^\[.*\]$',   # Just brackets with content
]

def is_junk_section(section: dict) -> bool:
    """Check if a section is junk data"""
    content = section.get('content', '').strip()
    title = section.get('section_title', '').strip()
    word_count = section.get('metadata', {}).get('word_count', 0)
    
    # Too short
    if word_count < 5:
        return True
    
    # Empty title and section number is 0
    if section.get('section_number') == '0' and not title:
        return True
    
    # Check against junk patterns
    for pattern in JUNK_PATTERNS:
        if re.match(pattern, content, re.IGNORECASE):
            return True
    
    # Content is mostly just brackets and metadata
    if content.startswith(']') and word_count < 20:
        return True
    
    return False

def clean_section_content(content: str) -> str:
    """Clean section content by removing website artifacts"""
    # Remove leading brackets and metadata
    content = re.sub(r'^\]\s*\n?', '', content)
    content = re.sub(r'^Section \d+\s*\n?\]\s*\n?', '', content)
    content = re.sub(r'^Entire Act\s*\n?\]\s*\n?', '', content)
    content = re.sub(r'^Union of India - (Section|Subsection|Act)\s*\n?', '', content)
    
    # Clean up the text
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    
    return content

def clean_json_file(file_path: Path) -> dict:
    """Clean a single JSON file"""
    print(f"\n[CLEANING] {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data.get('sections', []))
    
    # Filter out junk sections
    cleaned_sections = []
    removed_count = 0
    
    for section in data.get('sections', []):
        if is_junk_section(section):
            removed_count += 1
            continue
        
        # Clean the content
        section['content'] = clean_section_content(section['content'])
        
        # Recalculate metadata
        section['metadata']['word_count'] = len(section['content'].split())
        section['metadata']['char_count'] = len(section['content'])
        
        # Skip if still too short after cleaning
        if section['metadata']['word_count'] < 5:
            removed_count += 1
            continue
        
        cleaned_sections.append(section)
    
    # Update data
    data['sections'] = cleaned_sections
    data['total_sections'] = len(cleaned_sections)
    data['metadata']['total_words'] = sum(s['metadata']['word_count'] for s in cleaned_sections)
    data['metadata']['total_characters'] = sum(s['metadata']['char_count'] for s in cleaned_sections)
    data['metadata']['average_section_length'] = data['metadata']['total_words'] // max(1, len(cleaned_sections))
    
    # Save cleaned file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"  [REMOVED] {removed_count} junk sections")
    print(f"  [KEPT] {len(cleaned_sections)} valid sections (from {original_count})")
    print(f"  [WORDS] {data['metadata']['total_words']:,}")
    
    return {
        'file': file_path.name,
        'original': original_count,
        'cleaned': len(cleaned_sections),
        'removed': removed_count,
        'words': data['metadata']['total_words']
    }

def main():
    print("\n" + "="*60)
    print("CLEANING STATUTE JSON FILES")
    print("Removing junk data (Cited by, empty sections, etc.)")
    print("="*60)
    
    results = []
    
    for json_file in JSON_DIR.glob("*.json"):
        if json_file.name == "summary.json":
            continue
        result = clean_json_file(json_file)
        results.append(result)
    
    # Update summary
    summary = {
        'total_statutes': len(results),
        'statutes': [
            {
                'name': r['file'].replace('.json', '').replace('_', ' '),
                'sections': r['cleaned'],
                'words': r['words']
            }
            for r in results
        ]
    }
    
    with open(JSON_DIR / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*60)
    print("CLEANING COMPLETE")
    print("="*60)
    total_removed = sum(r['removed'] for r in results)
    total_kept = sum(r['cleaned'] for r in results)
    print(f"Total junk removed: {total_removed}")
    print(f"Total valid sections: {total_kept}")
    print("="*60)

if __name__ == "__main__":
    main()
