"""
Complete Fix for Consumer Protection Act 2019 JSON
Handles all deduplication and subsection merging issues
"""

import json
import re
from pathlib import Path
from collections import defaultdict

JSON_FILE = Path("DATA/Statutes/json/Consumer_Protection_Act_2019.json")

class CPACompleteFix:
    def __init__(self):
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
        # Count subsection markers like (1), (2), (3)
        subsection_count = len(re.findall(r'\n\(\d+\)', content))
        return subsection_count >= 2
    
    def is_complete_section(self, section: dict) -> bool:
        """Determine if this is a complete section (not just a subsection)"""
        section_num = section.get('section_number', '')
        content = section.get('content', '')
        
        # If it's a subsection number like "1(2)", it's not complete
        if self.is_subsection(section_num):
            return False
        
        # If it has multiple subsections in content, it's complete
        if self.has_subsections(content):
            return True
        
        # If it's reasonably long and has a title, likely complete
        word_count = section.get('metadata', {}).get('word_count', 0)
        has_title = bool(section.get('section_title', '').strip())
        
        return word_count > 50 and has_title
    
    def content_hash(self, content: str) -> str:
        """Create a hash of content for deduplication"""
        # Normalize whitespace and get first 500 chars
        normalized = re.sub(r'\s+', ' ', content[:500]).strip().lower()
        return normalized
    
    def deduplicate_sections(self, sections: list) -> list:
        """Remove duplicates and subsections"""
        # Group by main section number
        section_groups = defaultdict(list)
        
        for idx, section in enumerate(sections):
            section_num = section.get('section_number', '')
            main_num = self.extract_main_section_number(section_num)
            section_groups[main_num].append((idx, section))
        
        kept_sections = []
        
        for main_num, group in sorted(section_groups.items(), key=lambda x: self._section_sort_key(x[0])):
            if not group:
                continue
            
            # Find the most complete version
            complete_sections = [(idx, s) for idx, s in group if self.is_complete_section(s)]
            subsections = [(idx, s) for idx, s in group if self.is_subsection(s.get('section_number', ''))]
            
            if complete_sections:
                # Use the longest complete section
                best_idx, best_section = max(complete_sections, 
                                             key=lambda x: x[1].get('metadata', {}).get('word_count', 0))
                
                # Check for exact duplicates among complete sections
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
                # No complete section, keep all subsections but deduplicate
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
        
        # Remove redundant prefixes from content
        content = cleaned['content']
        
        # Remove "Section X in Consumer Protection Act, 2019" prefix
        content = re.sub(r'^Section\s+\d+[A-Z]*(?:\([^)]+\))?\s+in\s+Consumer Protection Act,?\s+2019\s*\n?',
                        '', content, flags=re.IGNORECASE)
        
        # Remove section number repetition at start if it matches section_number
        section_num = cleaned.get('section_number', '')
        if section_num:
            content = re.sub(rf'^{re.escape(section_num)}\.\s*[^\n]+\n', '', content)
        
        # Clean whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        cleaned['content'] = content
        
        # Recalculate metadata
        cleaned['metadata'] = {
            'word_count': len(content.split()),
            'char_count': len(content)
        }
        
        return cleaned
    
    def fix_all(self):
        """Main fix process"""
        print("\n" + "="*70)
        print("COMPLETE FIX: Consumer Protection Act 2019")
        print("="*70)
        
        # Load
        print("\n[LOAD] Reading JSON...")
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['original'] = len(data['sections'])
        print(f"[OK] Loaded {self.stats['original']} sections")
        
        # Deduplicate
        print("\n[DEDUPLICATE] Removing duplicates and merging subsections...")
        deduped_sections = self.deduplicate_sections(data['sections'])
        print(f"  Removed {self.stats['removed_subsections']} subsection duplicates")
        print(f"  Removed {self.stats['removed_duplicates']} exact duplicates")
        
        # Clean each section
        print("\n[CLEAN] Cleaning section content...")
        cleaned_sections = []
        for section in deduped_sections:
            cleaned = self.clean_section(section)
            # Skip if too short
            if cleaned['metadata']['word_count'] >= 10:
                cleaned_sections.append(cleaned)
            else:
                self.stats['removed_empty'] += 1
        
        # Sort by section number
        print("\n[SORT] Sorting sections...")
        cleaned_sections.sort(key=lambda s: self._section_sort_key(s.get('section_number', '0')))
        
        self.stats['final'] = len(cleaned_sections)
        
        # Update data
        data['sections'] = cleaned_sections
        data['total_sections'] = len(cleaned_sections)
        data['metadata']['total_words'] = sum(s['metadata']['word_count'] for s in cleaned_sections)
        data['metadata']['total_characters'] = sum(s['metadata']['char_count'] for s in cleaned_sections)
        data['metadata']['average_section_length'] = data['metadata']['total_words'] // max(1, len(cleaned_sections))
        
        # Save
        print("\n[SAVE] Writing fixed JSON...")
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Report
        self.print_report()
    
    def print_report(self):
        """Print final report"""
        print("\n" + "="*70)
        print("FIX COMPLETE - FINAL REPORT")
        print("="*70)
        
        print(f"\n[RESULTS]:")
        print(f"  Original sections:        {self.stats['original']}")
        print(f"  Subsection duplicates:    -{self.stats['removed_subsections']}")
        print(f"  Exact duplicates:         -{self.stats['removed_duplicates']}")
        print(f"  Too short/empty:          -{self.stats['removed_empty']}")
        print(f"  ---")
        print(f"  Final clean sections:     {self.stats['final']}")
        
        reduction = self.stats['original'] - self.stats['final']
        pct = (reduction / self.stats['original'] * 100) if self.stats['original'] > 0 else 0
        
        print(f"\n[CLEANUP]:")
        print(f"  Total removed:            {reduction} ({pct:.1f}%)")
        print(f"  Kept:                     {self.stats['final']} clean sections")
        
        print("\n" + "="*70)
        print("[SUCCESS] Consumer Protection Act 2019 is now clean!")
        print("="*70)

def main():
    fixer = CPACompleteFix()
    fixer.fix_all()

if __name__ == "__main__":
    main()
