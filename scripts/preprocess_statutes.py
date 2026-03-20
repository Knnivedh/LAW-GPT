"""
Statute Data Preprocessor
Converts raw statute text files to clean, structured JSON format
Handles cleaning, parsing, and structuring for RAG system optimization
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict

class StatutePreprocessor:
    def __init__(self, input_dir="DATA/Statutes", output_dir="DATA/Statutes/json"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove standalone numbers and fragments
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just numbers, single chars, or short fragments
            if stripped and len(stripped) > 2 and not stripped.isdigit():
                # Skip common noise patterns
                if stripped in ['—', 'BNS', 'Chapter', 'S.', 'Description', 'Illustration', 'Explanation']:
                    continue
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Normalize spacing
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n ', '\n', text)
        
        return text.strip()
    
    def parse_sections(self, content: str, act_name: str) -> List[Dict]:
        """Parse text content into structured sections"""
        sections = []
        
        # Split by section markers
        parts = re.split(r'---\s*Section\s+(\d+[a-zA-Z]?)\s*---', content)
        
        # First part is header/metadata
        header = parts[0] if parts else ""
        
        # Extract act info from header
        source_match = re.search(r'SOURCE:\s*(.+)', header)
        source = source_match.group(1).strip() if source_match else "Unknown"
        
        # Process sections (pairs of section_num and section_content)
        for i in range(1, len(parts), 2):
            if i+1 < len(parts):
                section_num = parts[i].strip()
                section_content = parts[i+1].strip()
                
                # Clean the content
                section_content = self.clean_text(section_content)
                
                # Extract section title (usually first line or after "Section X" marker)
                lines = section_content.split('\n')
                title = ""
                description = ""
                
                # Try to find title
                for idx, line in enumerate(lines):
                    if len(line.strip()) > 10 and '.' in line:
                        title = line.strip()
                        description = '\n'.join(lines[idx+1:]).strip()
                        break
                
                if not title:
                    title = f"Section {section_num}"
                    description = section_content
                
                # Create structured section
                section = {
                    "section_number": section_num,
                    "section_title": title,
                    "content": description,
                    "metadata": {
                        "act": act_name,
                        "source": source,
                        "word_count": len(description.split()),
                        "character_count": len(description)
                    }
                }
                
                sections.append(section)
        
        return sections
    
    def process_file(self, input_file: Path) -> Dict:
        """Process a single statute file"""
        print(f"\n{'='*60}")
        print(f"Processing: {input_file.name}")
        print(f"{'='*60}")
        
        # Read file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract act name from filename
        act_name = input_file.stem.replace('_', ' ')
        
        # Parse sections
        sections = self.parse_sections(content, act_name)
        
        print(f"[OK] Extracted {len(sections)} sections")
        
        # Create output structure
        output_data = {
            "act_name": act_name,
            "total_sections": len(sections),
            "source_file": input_file.name,
            "sections": sections,
            "metadata": {
                "total_words": sum(s['metadata']['word_count'] for s in sections),
                "total_characters": sum(s['metadata']['character_count'] for s in sections),
                "average_section_length": sum(s['metadata']['word_count'] for s in sections) // len(sections) if sections else 0
            }
        }
        
        # Save JSON
        output_file = self.output_dir / f"{input_file.stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVED] Output: {output_file}")
        print(f"[STATS] Statistics:")
        print(f"   - Total Words: {output_data['metadata']['total_words']:,}")
        print(f"   - Avg Section Length: {output_data['metadata']['average_section_length']} words")
        
        return output_data
    
    def process_all(self):
        """Process all .txt files in input directory"""
        txt_files = list(self.input_dir.glob("*.txt"))
        
        # Filter out README
        txt_files = [f for f in txt_files if 'README' not in f.name.upper()]
        
        print(f"\n[INFO] Found {len(txt_files)} statute files to process")
        
        results = []
        for txt_file in txt_files:
            try:
                result = self.process_file(txt_file)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Error processing {txt_file.name}: {e}")
        
        # Create summary
        summary = {
            "total_acts": len(results),
            "acts": [
                {
                    "name": r["act_name"],
                    "sections": r["total_sections"],
                    "words": r["metadata"]["total_words"]
                }
                for r in results
            ]
        }
        
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"[SUCCESS] PREPROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"[OUTPUT] Directory: {self.output_dir}")
        print(f"[STATS] Total Acts Processed: {len(results)}")
        print(f"[STATS] Total Sections: {sum(r['total_sections'] for r in results)}")
        print(f"[SUMMARY] Saved to: {summary_file}")

def main():
    preprocessor = StatutePreprocessor()
    preprocessor.process_all()

if __name__ == "__main__":
    main()
