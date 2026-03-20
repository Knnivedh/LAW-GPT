"""
Deep Audit & Fix for Consumer Protection Act 2019 JSON
Identifies and fixes all data quality issues
"""

import json
import re
from pathlib import Path
from collections import defaultdict

JSON_FILE = Path("DATA/Statutes/json/Consumer_Protection_Act_2019.json")

class CPAAuditor:
    def __init__(self):
        self.issues = {
            'incorrect_section_numbers': [],
            'duplicate_content': [],
            'too_short': [],
            'invalid_format': [],
            'missing_section_in_content': []
        }
        self.stats = defaultdict(int)
    
    def extract_section_from_content(self, content: str) -> str:
        """Extract actual section number from content"""
        # Pattern: "Section 107(2)" or "Section 107"
        match = re.search(r'Section\s+(\d+[A-Z]*(?:\([^)]+\))?)', content, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def audit_section(self, idx: int, section: dict) -> dict:
        """Audit a single section and return fixed version"""
        issues_found = []
        fixed_section = section.copy()
        
        # Extract actual section from content
        actual_section = self.extract_section_from_content(section['content'])
        declared_section = section.get('section_number', '')
        
        # Issue 1: Section number mismatch
        if actual_section and actual_section != declared_section:
            issues_found.append(f"Section mismatch: declared='{declared_section}', actual='{actual_section}'")
            fixed_section['section_number'] = actual_section
            self.issues['incorrect_section_numbers'].append({
                'index': idx,
                'declared': declared_section,
                'actual': actual_section
            })
        
        # Issue 2: Missing section number in content
        if not actual_section and declared_section:
            self.issues['missing_section_in_content'].append({
                'index': idx,
                'declared_section': declared_section,
                'content_preview': section['content'][:100]
            })
        
        # Issue 3: Too short (< 10 words)
        word_count = section.get('metadata', {}).get('word_count', 0)
        if word_count < 10:
            issues_found.append(f"Too short: {word_count} words")
            self.issues['too_short'].append({
                'index': idx,
                'section': declared_section,
                'words': word_count
            })
        
        # Issue 4: Extract proper title from content
        if not section.get('section_title'):
            # Try to extract title after section number
            title_match = re.search(r'Section\s+\d+[A-Z]*(?:\([^)]+\))?\s+in\s+Consumer Protection Act[^\n]*\n(.+?)(?:\n|$)', 
                                   section['content'], re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                if len(title) < 200 and not title.startswith('('):
                    fixed_section['section_title'] = title
        
        return fixed_section, issues_found
    
    def find_duplicates(self, sections: list) -> list:
        """Find duplicate sections by content hash"""
        seen_hashes = {}
        duplicates = []
        
        for idx, section in enumerate(sections):
            content_hash = hash(section['content'][:200])  # Hash first 200 chars
            if content_hash in seen_hashes:
                duplicates.append({
                    'index': idx,
                    'duplicate_of': seen_hashes[content_hash],
                    'section': section.get('section_number')
                })
                self.issues['duplicate_content'].append(duplicates[-1])
            else:
                seen_hashes[content_hash] = idx
        
        return duplicates
    
    def clean_content(self, content: str) -> str:
        """Clean section content"""
        # Remove redundant "Section X in Consumer Protection Act, 2019" prefix
        content = re.sub(r'^Section\s+\d+[A-Z]*(?:\([^)]+\))?\s+in\s+Consumer Protection Act,?\s+2019\s*\n', 
                        '', content, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    def audit_and_fix(self):
        """Main audit and fix process"""
        print("\n" + "="*70)
        print("DEEP AUDIT: Consumer Protection Act 2019")
        print("="*70)
        
        # Load JSON
        print("\n[LOAD] Reading JSON file...")
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_count = len(data['sections'])
        print(f"[OK] Loaded {original_count} sections")
        
        # Phase 1: Find duplicates
        print("\n[PHASE 1] Finding duplicates...")
        self.find_duplicates(data['sections'])
        print(f"  Found {len(self.issues['duplicate_content'])} duplicates")
        
        # Phase 2: Audit each section
        print("\n[PHASE 2] Auditing each section...")
        fixed_sections = []
        
        for idx, section in enumerate(data['sections']):
            fixed_section, issues = self.audit_section(idx, section)
            
            # Skip if it's a duplicate
            is_duplicate = any(d['index'] == idx for d in self.issues['duplicate_content'])
            if is_duplicate:
                continue
            
            # Skip if too short
            if fixed_section.get('metadata', {}).get('word_count', 0) < 10:
                continue
            
            # Clean content
            fixed_section['content'] = self.clean_content(fixed_section['content'])
            
            # Recalculate metadata
            fixed_section['metadata']['word_count'] = len(fixed_section['content'].split())
            fixed_section['metadata']['char_count'] = len(fixed_section['content'])
            
            fixed_sections.append(fixed_section)
        
        # Phase 3: Sort by section number
        print("\n[PHASE 3] Sorting sections...")
        
        def section_sort_key(section):
            """Extract numeric part for sorting"""
            section_num = section.get('section_number', '0')
            # Extract main number
            match = re.match(r'(\d+)', str(section_num))
            if match:
                return int(match.group(1))
            return 0
        
        fixed_sections.sort(key=section_sort_key)
        
        # Update data
        data['sections'] = fixed_sections
        data['total_sections'] = len(fixed_sections)
        data['metadata']['total_words'] = sum(s['metadata']['word_count'] for s in fixed_sections)
        data['metadata']['total_characters'] = sum(s['metadata']['char_count'] for s in fixed_sections)
        data['metadata']['average_section_length'] = data['metadata']['total_words'] // max(1, len(fixed_sections))
        
        # Save fixed JSON
        print("\n[SAVE] Writing fixed JSON...")
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Print report
        self.print_report(original_count, len(fixed_sections))
    
    def print_report(self, original: int, fixed: int):
        """Print detailed audit report"""
        print("\n" + "="*70)
        print("AUDIT REPORT")
        print("="*70)
        
        print(f"\n[SUMMARY]:")
        print(f"  Original sections:     {original}")
        print(f"  Fixed sections:        {fixed}")
        print(f"  Removed:               {original - fixed}")
        
        print(f"\n[ISSUES FOUND]:")
        print(f"  Incorrect section #:   {len(self.issues['incorrect_section_numbers'])}")
        print(f"  Duplicates:            {len(self.issues['duplicate_content'])}")
        print(f"  Too short:             {len(self.issues['too_short'])}")
        print(f"  Missing section ref:   {len(self.issues['missing_section_in_content'])}")
        
        # Show examples
        if self.issues['incorrect_section_numbers']:
            print(f"\n[SECTION NUMBER FIXES] (first 10):")
            for issue in self.issues['incorrect_section_numbers'][:10]:
                print(f"  #{issue['index']}: '{issue['declared']}' -> '{issue['actual']}'")
        
        if self.issues['duplicate_content']:
            print(f"\n[DUPLICATES REMOVED] (first 5):")
            for dup in self.issues['duplicate_content'][:5]:
                print(f"  Section {dup['section']} at index {dup['index']} (duplicate of #{dup['duplicate_of']})")
        
        print("\n" + "="*70)
        print("[OK] FIX COMPLETE")
        print("="*70)

def main():
    auditor = CPAAuditor()
    auditor.audit_and_fix()

if __name__ == "__main__":
    main()
