"""
Statute Preprocessor - Improved Version
Handles both Devgan.in and Indian Kanoon formats
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

class StatutePreprocessor:
    def __init__(self, input_dir="DATA/Statutes", output_dir="DATA/Statutes/json"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()
    
    def parse_devgan_format(self, text: str) -> List[Dict]:
        """Parse Devgan.in format (BNS style)"""
        sections = []
        # Pattern: SECTION X - Title followed by content
        pattern = r'SECTION\s+(\d+[A-Za-z]*)\s*[-:]\s*([^\n]+)\n(.*?)(?=SECTION\s+\d|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        for section_num, title, content in matches:
            sections.append({
                'section_number': section_num.strip(),
                'section_title': title.strip(),
                'content': self.clean_text(content),
                'metadata': {
                    'word_count': len(content.split()),
                    'char_count': len(content)
                }
            })
        
        return sections
    
    def parse_indian_kanoon_format(self, text: str) -> List[Dict]:
        """Parse Indian Kanoon format (CPA, TPA style)"""
        sections = []
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        # Patterns for section detection
        section_start_pattern = r'^(\d+[A-Za-z]*)\.?\s*$'  # Just number on its own line
        title_pattern = r'^([A-Z][A-Za-z\s,\-\.]+)\.?\s*$'  # Title on its own line
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and metadata
            if not line or line.startswith('[') or line.startswith('---'):
                i += 1
                continue
            
            # Check if this is a section number
            match = re.match(section_start_pattern, line)
            if match and i + 1 < len(lines):
                # Save previous section
                if current_section:
                    content_text = '\n'.join(current_content)
                    sections.append({
                        'section_number': current_section['number'],
                        'section_title': current_section['title'],
                        'content': self.clean_text(content_text),
                        'metadata': {
                            'word_count': len(content_text.split()),
                            'char_count': len(content_text)
                        }
                    })
                
                # Start new section
                section_num = match.group(1)
                
                # Look ahead for title
                title = ""
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    if next_line and not re.match(r'^\(\d+\)', next_line):
                        if next_line[0].isupper() and len(next_line) > 3:
                            title = next_line.rstrip('.-')
                            break
                    j += 1
                
                current_section = {
                    'number': section_num,
                    'title': title
                }
                current_content = []
                i = j + 1 if title else i + 1
                continue
            
            # Add to current content
            if current_section:
                current_content.append(line)
            
            i += 1
        
        # Save last section
        if current_section and current_content:
            content_text = '\n'.join(current_content)
            sections.append({
                'section_number': current_section['number'],
                'section_title': current_section['title'],
                'content': self.clean_text(content_text),
                'metadata': {
                    'word_count': len(content_text.split()),
                    'char_count': len(content_text)
                }
            })
        
        return sections
    
    def parse_chunked_format(self, text: str, act_name: str) -> List[Dict]:
        """Alternative parser: Create chunks without strict section detection"""
        sections = []
        
        # Split by common section markers
        parts = re.split(r'\n(?=\d+[A-Za-z]*\.?\s*\n)', text)
        
        for idx, part in enumerate(parts):
            if len(part.strip()) < 50:  # Skip tiny parts
                continue
            
            # Try to extract section number from start
            section_match = re.match(r'^(\d+[A-Za-z]*)\.?\s*\n', part)
            if section_match:
                section_num = section_match.group(1)
                content = part[section_match.end():].strip()
            else:
                section_num = str(idx + 1)
                content = part.strip()
            
            # Try to extract title from first line
            first_line = content.split('\n')[0] if content else ""
            title = first_line[:100] if first_line else f"Section {section_num}"
            
            sections.append({
                'section_number': section_num,
                'section_title': title,
                'content': self.clean_text(content),
                'metadata': {
                    'word_count': len(content.split()),
                    'char_count': len(content)
                }
            })
        
        return sections
    
    def detect_format(self, text: str) -> str:
        """Detect which format the file is in"""
        if 'SOURCE: https://indiankanoon.org' in text:
            return 'indian_kanoon'
        elif 'SECTION ' in text and ' - ' in text:
            return 'devgan'
        else:
            return 'unknown'
    
    def process_file(self, file_path: Path) -> Dict:
        """Process a single statute file"""
        print(f"\n[PROCESSING] {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Detect format
        format_type = self.detect_format(text)
        print(f"  [FORMAT] Detected: {format_type}")
        
        # Parse based on format
        if format_type == 'devgan':
            sections = self.parse_devgan_format(text)
        elif format_type == 'indian_kanoon':
            sections = self.parse_indian_kanoon_format(text)
        else:
            sections = self.parse_chunked_format(text, file_path.stem)
        
        print(f"  [PARSED] Found {len(sections)} sections")
        
        # If still no sections, use chunk-based approach
        if len(sections) < 5:
            print(f"  [FALLBACK] Using chunk-based parsing...")
            sections = self.parse_chunked_format(text, file_path.stem)
            print(f"  [RESULT] Created {len(sections)} chunks")
        
        # Build output
        act_name = file_path.stem.replace('_', ' ')
        total_words = sum(s['metadata']['word_count'] for s in sections)
        total_chars = sum(s['metadata']['char_count'] for s in sections)
        
        result = {
            'act_name': act_name,
            'total_sections': len(sections),
            'source_file': file_path.name,
            'format_detected': format_type,
            'sections': sections,
            'metadata': {
                'total_words': total_words,
                'total_characters': total_chars,
                'average_section_length': total_words // max(1, len(sections))
            }
        }
        
        # Save to JSON
        output_file = self.output_dir / f"{file_path.stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"  [SAVED] {output_file.name} ({len(sections)} sections, {total_words:,} words)")
        
        return result
    
    def process_all(self):
        """Process all statute files"""
        print("\n" + "="*70)
        print("STATUTE PREPROCESSOR - IMPROVED VERSION")
        print("="*70)
        
        txt_files = list(self.input_dir.glob("*.txt"))
        print(f"\n[FOUND] {len(txt_files)} statute files")
        
        results = []
        for txt_file in txt_files:
            result = self.process_file(txt_file)
            results.append(result)
        
        # Create summary
        summary = {
            'total_statutes': len(results),
            'statutes': [
                {
                    'name': r['act_name'],
                    'sections': r['total_sections'],
                    'words': r['metadata']['total_words']
                }
                for r in results
            ]
        }
        
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print("\n" + "="*70)
        print("PREPROCESSING COMPLETE")
        print("="*70)
        for r in results:
            print(f"  {r['act_name']}: {r['total_sections']} sections, {r['metadata']['total_words']:,} words")
        print("="*70)

def main():
    preprocessor = StatutePreprocessor()
    preprocessor.process_all()
    print("\n[SUCCESS] All statutes converted to JSON!")

if __name__ == "__main__":
    main()
