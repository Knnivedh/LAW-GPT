"""
Universal Statute JSON Fixer
Applies comprehensive fix to all statute JSON files
"""

import json
import re
from pathlib import Path
from collections import defaultdict

JSON_DIR = Path("DATA/Statutes/json")

class UniversalStatuteFixer:
    def __init__(self, json_file: Path):
        self.json_file = json_file
        self.stats = {
            'original': 0,
            'final': 0,
            'removed_subsections': 0,
            'removed_duplicates': 0,
            'removed_empty': 0
        }
    
    def extract_main_section_number(self, section_num: str) -> str:
        """Extract main section number (e.g., '1' from '1(2)')"""
        match = re.match(r'^(\d+[A-Z]*)', str(section_num))
        return match.group(1) if match else section_num
    
    def is_subsection(self, section_num: str) -> bool:
        """Check if this is a subsection entry (e.g., '1(2)')"""
        return bool(re.match(r'^\d+[A-Z]*\([^)]+\)$', str(section_num)))
    
    def has_subsections(self, content: str) -> bool:
        """Check if content contains multiple subsections"""
        subsection_count = len(re.findall(r'\n\(\d+\)', content))
        return subsection_count >= 2
    
    def is_complete_section(self, section: dict) -> bool:
        """Determine if this is a complete section"""
        section_num = section.get('section_number', '')
        content = section.get('content', '')
        
        if self.is_subsection(section_num):
            return False
        
        if self.has_subsections(content):
            return True
        
        word_count = section.get('metadata', {}).get('word_count', 0)
        has_title = bool(section.get('section_title', '').strip())
        
        return word_count > 50 and has_title
    
    def content_hash(self, content: str) -> str:
        """Create a hash of content for deduplication"""
        normalized = re.sub(r'\s+', ' ', content[:500]).strip().lower()
        return normalized
    
    def deduplicate_sections(self, sections: list) -> list:
        """Remove duplicates and subsections"""
        section_groups = defaultdict(list)
        
        for idx, section in enumerate(sections):
            section_num = section.get('section_number', '')
            main_num = self.extract_main_section_number(section_num)
            section_groups[main_num].append((idx, section))
        
        kept_sections = []
        
        for main_num, group in sorted(section_groups.items(), key=lambda x: self._section_sort_key(x[0])):
            if not group:
                continue
            
            complete_sections = [(idx, s) for idx, s in group if self.is_complete_section(s)]
            subsections = [(idx, s) for idx, s in group if self.is_subsection(s.get('section_number', ''))]
            
            if complete_sections:
                # Use the longest complete section
                best_idx, best_section = max(complete_sections, 
                                             key=lambda x: x[1].get('metadata', {}).get('word_count', 0))
                
                seen_hashes = set()
                content_hash_val = self.content_hash(best_section['content'])
                
                if content_hash_val not in seen_hashes:
                    kept_sections.append(best_section)
                    seen_hashes.add(content_hash_val)
                    self.stats['removed_subsections'] += len(subsections)
                    self.stats['removed_duplicates'] += len(complete_sections) - 1
                else:
                    self.stats['removed_duplicates'] += 1
            else:
                # Keep subsections but deduplicate
                seen_hashes = set()
                for idx, subsection in subsections:
                    content_hash_val = self.content_hash(subsection['content'])
                    if content_hash_val not in seen_hashes:
                        kept_sections.append(subsection)
                        seen_hashes.add(content_hash_val)
                    else:
                        self.stats['removed_duplicates'] += 1
        
        return kept_sections
    
    def _section_sort_key(self, section_num):
        """Extract numeric part for sorting"""
        match = re.match(r'(\d+)', str(section_num))
        return int(match.group(1)) if match else 0
    
    def clean_section(self, section: dict) -> dict:
        """Clean a single section"""
        cleaned = section.copy()
        content = cleaned['content']
        
        # Remove redundant prefixes
        content = re.sub(r'^Section\s+\d+[A-Z]*(?:\([^)]+\))?\s+in\s+[^\n]+\n?',
                        '', content, flags=re.IGNORECASE)
        
        # Clean whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        cleaned['content'] = content
        cleaned['metadata'] = {
            'word_count': len(content.split()),
            'char_count': len(content)
        }
        
        return cleaned
    
    def fix(self):
        """Main fix process"""
        act_name = self.json_file.stem.replace('_', ' ')
        print(f"\n[PROCESSING] {act_name}")
        
        # Load
        with open(self.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['original'] = len(data['sections'])
        print(f"  Original sections: {self.stats['original']}")
        
        # Deduplicate
        deduped_sections = self.deduplicate_sections(data['sections'])
        
        # Clean
        cleaned_sections = []
        for section in deduped_sections:
            cleaned = self.clean_section(section)
            if cleaned['metadata']['word_count'] >= 10:
                cleaned_sections.append(cleaned)
            else:
                self.stats['removed_empty'] += 1
        
        # Sort
        cleaned_sections.sort(key=lambda s: self._section_sort_key(s.get('section_number', '0')))
        
        self.stats['final'] = len(cleaned_sections)
        
        # Update data
        data['sections'] = cleaned_sections
        data['total_sections'] = len(cleaned_sections)
        data['metadata']['total_words'] = sum(s['metadata']['word_count'] for s in cleaned_sections)
        data['metadata']['total_characters'] = sum(s['metadata']['char_count'] for s in cleaned_sections)
        data['metadata']['average_section_length'] = data['metadata']['total_words'] // max(1, len(cleaned_sections))
        
        # Save
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Report
        reduction = self.stats['original'] - self.stats['final']
        pct = (reduction / self.stats['original'] * 100) if self.stats['original'] > 0 else 0
        
        print(f"  Removed subsections:  {self.stats['removed_subsections']}")
        print(f"  Removed duplicates:   {self.stats['removed_duplicates']}")
        print(f"  Removed empty:        {self.stats['removed_empty']}")
        print(f"  Final sections:       {self.stats['final']} ({reduction} removed, {pct:.1f}%)")
        
        return self.stats

def main():
    print("\n" + "="*70)
    print("UNIVERSAL STATUTE JSON FIXER")
    print("Fixing all statute files in DATA/Statutes/json")
    print("="*70)
    
    json_files = list(JSON_DIR.glob("*.json"))
    # Exclude summary.json
    json_files = [f for f in json_files if f.name != "summary.json"]
    
    total_original = 0
    total_final = 0
    
    results = []
    for json_file in sorted(json_files):
        fixer = UniversalStatuteFixer(json_file)
        stats = fixer.fix()
        
        total_original += stats['original']
        total_final += stats['final']
        
        # Load data for summary
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            results.append({
                'name': data['act_name'],
                'sections': data['total_sections'],
                'words': data['metadata']['total_words']
            })
    
    # Update summary
    summary = {
        'total_statutes': len(results),
        'total_sections': total_final,
        'statutes': results
    }
    
    with open(JSON_DIR / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print("FIX COMPLETE - ALL STATUTES")
    print("="*70)
    print(f"Total Statutes:         {len(results)}")
    print(f"Total sections before:  {total_original}")
    print(f"Total sections after:   {total_final}")
    print(f"Total removed:          {total_original - total_final}")
    print("="*70)
    print("\n[SUCCESS] All statute JSONs are now clean and ready for RAG!")

if __name__ == "__main__":
    main()
