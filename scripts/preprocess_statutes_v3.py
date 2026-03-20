"""
Statute Preprocessor v3 - Robust Section Parsing
Handles Indian Kanoon's '--- SECTION' format and standard numbering.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

class StatutePreprocessorV3:
    def __init__(self, input_dir="DATA/Statutes", output_dir="DATA/Statutes/json"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove [Cites...], [Cited by...]
        text = re.sub(r'\[Cites\s*\d+\s*,\s*Cited by\s*\d+\s*\]', '', text)
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()
    
    def parse_section_marker_format(self, text: str, act_name: str) -> List[Dict]:
        """Parse format using '--- SECTION: ... ---' markers"""
        sections = []
        # Split by marker: --- SECTION: name ---
        # Note: Some markers have extra info like (Act 21 of 1929)
        pattern = r'--- SECTION:\s*(.*?)\s*---'
        parts = re.split(pattern, text)
        
        # parts[0] is header
        # parts[1] is section 1 title, parts[2] is section 1 content...
        for i in range(1, len(parts), 2):
            title = parts[i].strip()
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            
            if not content: continue
            
            # Clean content of repeated metadata
            content = re.sub(r'^\[.*?\]', '', content, flags=re.MULTILINE)
            content = self.clean_text(content)
            
            # Try to extract a section number from title
            # e.g. "section 46 (2)" -> "46"
            num_match = re.search(r'(?:section|article)\s*(\d+[A-Za-z]*)', title, re.IGNORECASE)
            num = num_match.group(1) if num_match else title
            
            sections.append({
                'section_number': num,
                'section_title': title,
                'content': content,
                'metadata': {
                    'word_count': len(content.split()),
                    'char_count': len(content)
                }
            })
        return sections

    def parse_standard_format(self, text: str) -> List[Dict]:
        """Fallback to standard numbering detection"""
        sections = []
        # Attempt to detect sections like "1. Title\nContent"
        # Since this is a fallback, we use the v2 logic basically
        pattern = r'\n(\d+[A-Za-z]*)\.\s+([^\n]+)\n(.*?)(?=\n\d+\.|$)'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            num, title, content = match.groups()
            content = self.clean_text(content)
            sections.append({
                'section_number': num,
                'section_title': title,
                'content': content,
                'metadata': {
                    'word_count': len(content.split()),
                    'char_count': len(content)
                }
            })
        return sections

    def process_file(self, file_path: Path) -> Dict:
        print(f"\n[PROCESSING] {file_path.name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # 1. Try Section Marker format
        sections = self.parse_section_marker_format(text, file_path.stem)
        format_type = "marker-based"
        
        # 2. If nothing found, try standard numbering
        if not sections:
            sections = self.parse_standard_format(text)
            format_type = "number-based"
            
        # 3. Simple chunking if still nothing
        if not sections:
            parts = text.split('\n\n')
            for idx, part in enumerate(parts):
                if len(part.strip()) > 100:
                    sections.append({
                        'section_number': str(idx+1),
                        'section_title': f"Chunk {idx+1}",
                        'content': self.clean_text(part),
                        'metadata': {'word_count': len(part.split()), 'char_count': len(part)}
                    })
            format_type = "chunk-based"

        print(f"  [FORMAT] {format_type}")
        print(f"  [PARSED] Found {len(sections)} sections")

        # Build final object
        act_name = file_path.stem.replace('_', ' ')
        total_words = sum(s['metadata']['word_count'] for s in sections)
        
        result = {
            'act_name': act_name,
            'total_sections': len(sections),
            'source_file': file_path.name,
            'format_detected': format_type,
            'sections': sections,
            'metadata': {
                'total_words': total_words,
                'total_characters': sum(s['metadata']['char_count'] for s in sections)
            }
        }
        
        output_file = self.output_dir / f"{file_path.stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        return result

    def process_all(self):
        txt_files = [f for f in self.input_dir.glob("*.txt") if f.name != 'summary.txt']
        print(f"Found {len(txt_files)} files.")
        
        results = []
        for f in txt_files:
            try:
                results.append(self.process_file(f))
            except Exception as e:
                print(f"Error processing {f.name}: {e}")
        
        summary = {
            'total_statutes': len(results),
            'statutes': [{'name': r['act_name'], 'sections': r['total_sections']} for r in results]
        }
        with open(self.output_dir / "summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

if __name__ == "__main__":
    preprocessor = StatutePreprocessorV3()
    preprocessor.process_all()
