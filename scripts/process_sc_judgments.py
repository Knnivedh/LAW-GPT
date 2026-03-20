"""
Supreme Court Judgments - Metadata Enhancement & Intelligent Chunking
Parses SC judgment text to extract rich metadata and creates optimized chunks for RAG
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class SCJudgmentProcessor:
    def __init__(self, 
                 text_dir="DATA/SC_Judgments/text",
                 metadata_dir="DATA/SC_Judgments/metadata",
                 output_dir="DATA/SC_Judgments/json"):
        self.text_dir = Path(text_dir)
        self.metadata_dir = Path(metadata_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_judges(self, text: str) -> List[str]:
        """Extract judge names from judgment text"""
        judges = []
        
        # Pattern: "BEFORE: Justice X, Justice Y"
        pattern1 = r'BEFORE:?\s*(.+?)(?:\n|JUDGMENT)'
        match = re.search(pattern1, text, re.IGNORECASE | re.DOTALL)
        if match:
            judges_text = match.group(1)
            # Extract individual judge names
            judge_names = re.findall(r'(?:Justice|J\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', judges_text)
            judges.extend(judge_names)
        
        # Pattern: "Author: Judge Name"
        pattern2 = r'Author:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        match2 = re.search(pattern2, text)
        if match2 and match2.group(1) not in judges:
            judges.append(match2.group(1))
        
        return list(set(judges)) if judges else ["Unknown"]
    
    def extract_citations(self, text: str) -> List[str]:
        """Extract case citations from judgment"""
        citations = []
        
        # Common citation patterns
        patterns = [
            r'\d{4}\s+INSC\s+\d+',  # 2024 INSC 718
            r'\d{4}\s+SCC\s+\d+',   # 2024 SCC 567
            r'AIR\s+\d{4}\s+SC\s+\d+',  # AIR 2024 SC 123
            r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',  # (2024) 5 SCC 123
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        
        return list(set(citations))
    
    def extract_case_number(self, text: str) -> Optional[str]:
        """Extract case number from judgment"""
        # Pattern: "Criminal Appeal No. 123/2024" or similar
        patterns = [
            r'(?:Criminal|Civil)\s+Appeal\s+No\.?\s*(\d+/\d{4})',
            r'SLP\(Crl\.\)\s+No\.(\d+\s+of\s+\d{4})',
            r'W\.P\.\(Crl\.\)\s+No\.(\d+\s+of\s+\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def detect_sections(self, text: str) -> Dict[str, tuple]:
        """Detect major sections of the judgment"""
        sections = {}
        
        # Common section markers
        markers = {
            'facts': [r'BACKGROUND FACTS', r'FACTS OF THE CASE', r'FACTS'],
            'arguments': [r'ARGUMENTS? ADVANCED', r'SUBMISSIONS?'],
            'issues': [r'QUESTIONS? FOR CONSIDERATION', r'ISSUES?'],
            'reasoning': [r'CONSIDERATION', r'ANALYSIS', r'DISCUSSION'],
            'conclusion': [r'CONCLUSION', r'HELD', r'ORDER'],
        }
        
        for section_name, patterns in markers.items():
            for pattern in patterns:
                match = re.search(f'{pattern}', text, re.IGNORECASE)
                if match:
                    start_pos = match.start()
                    sections[section_name] = (start_pos, pattern)
                    break
        
        return sections
    
    def create_smart_chunks(self, text: str, metadata: Dict, chunk_size=1500, overlap=150) -> List[Dict]:
        """Create intelligent chunks with context preservation"""
        chunks = []
        sections = self.detect_sections(text)
        
        # If judgment has clear sections, chunk by section
        if sections:
            sorted_sections = sorted(sections.items(), key=lambda x: x[1][0])
            
            for i, (section_name, (start_pos, _)) in enumerate(sorted_sections):
                # Determine end position
                if i + 1 < len(sorted_sections):
                    end_pos = sorted_sections[i + 1][1][0]
                else:
                    end_pos = len(text)
                
                section_text = text[start_pos:end_pos].strip()
                
                # Chunk large sections
                if len(section_text) > chunk_size:
                    section_chunks = self.chunk_text(section_text, chunk_size, overlap)
                    for j, chunk_text in enumerate(section_chunks):
                        chunks.append({
                            'chunk_id': f"{metadata['case_id']}_sec_{section_name}_{j}",
                            'text': chunk_text,
                            'section': section_name,
                            'priority': 'high' if section_name in ['issues', 'conclusion'] else 'medium',
                            'chunk_type': 'section',
                            **metadata
                        })
                else:
                    chunks.append({
                        'chunk_id': f"{metadata['case_id']}_sec_{section_name}_0",
                        'text': section_text,
                        'section': section_name,
                        'priority': 'high' if section_name in ['issues', 'conclusion'] else 'medium',
                        'chunk_type': 'section',
                        **metadata
                    })
        else:
            # Fallback: chunk by size with overlap
            text_chunks = self.chunk_text(text, chunk_size, overlap)
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'chunk_id': f"{metadata['case_id']}_chunk_{i}",
                    'text': chunk_text,
                    'section': 'full_text',
                    'priority': 'medium',
                    'chunk_type': 'sequential',
                    **metadata
                })
        
        return chunks
    
    def chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(' '.join(chunk_words))
            i += chunk_size - overlap
        
        return chunks
    
    def process_judgment(self, text_file: Path, metadata_file: Path) -> Dict:
        """Process a single judgment file"""
        # Load existing metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load text
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Enhance metadata
        metadata['judges'] = self.extract_judges(text)
        metadata['citations'] = self.extract_citations(text)
        metadata['case_number'] = self.extract_case_number(text)
        
        # Create chunks
        chunks = self.create_smart_chunks(text, metadata)
        
        return {
            'metadata': metadata,
            'chunks': chunks,
            'num_chunks': len(chunks)
        }
    
    def process_year(self, year: int, limit: Optional[int] = None):
        """Process all judgments from a specific year"""
        year_text_dir = self.text_dir / str(year)
        year_meta_dir = self.metadata_dir / str(year)
        year_output_dir = self.output_dir / str(year)
        year_output_dir.mkdir(parents=True, exist_ok=True)
        
        if not year_text_dir.exists():
            print(f"[WARN] No text directory for year {year}")
            return
        
        # Get all text files
        text_files = sorted(year_text_dir.glob("*.txt"))
        if limit:
            text_files = text_files[:limit]
        
        print(f"\n[INFO] Processing {len(text_files)} judgments from {year}")
        
        processed = 0
        for text_file in text_files:
            case_id = text_file.stem
            metadata_file = year_meta_dir / f"{case_id}_metadata.json"
            
            if not metadata_file.exists():
                print(f"  [SKIP] No metadata for {case_id}")
                continue
            
            try:
                result = self.process_judgment(text_file, metadata_file)
                
                # Save enhanced metadata
                enhanced_meta_file = year_output_dir / f"{case_id}_metadata_enhanced.json"
                with open(enhanced_meta_file, 'w', encoding='utf-8') as f:
                    json.dump(result['metadata'], f, indent=2)
                
                # Save chunks
                chunks_file = year_output_dir / f"{case_id}_chunks.json"
                with open(chunks_file, 'w', encoding='utf-8') as f:
                    json.dump(result['chunks'], f, indent=2)
                
                processed += 1
                print(f"  [{processed}/{len(text_files)}] Processed {case_id} -> {result['num_chunks']} chunks")
                
            except Exception as e:
                print(f"  [ERROR] Failed to process {case_id}: {e}")
        
        print(f"\n[SUCCESS] Processed {processed}/{len(text_files)} judgments from {year}")

def main():
    processor = SCJudgmentProcessor()
    
    # Process 2024 pilot data
    processor.process_year(2024, limit=100)
    
    print("\n[COMPLETE] Metadata enhancement and chunking complete!")

if __name__ == "__main__":
    main()
