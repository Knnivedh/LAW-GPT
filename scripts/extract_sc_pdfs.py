"""
Supreme Court Judgments PDF Extractor
Extracts text from SC judgment PDFs with metadata parsing and quality validation
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import pdfplumber
import fitz  # PyMuPDF
from tqdm import tqdm

class SCJudgmentExtractor:
    def __init__(self, 
                 pdf_root_dir="DATA/supreme_court_judgments_100%/supreme_court_judgments",
                 output_dir="DATA/SC_Judgments",
                 pilot_mode=True,
                 pilot_year=2024,
                 pilot_limit=100):
        """
        Initialize SC Judgment Extractor
        
        Args:
            pdf_root_dir: Root directory containing year folders with PDFs
            output_dir: Output directory for extracted text and metadata
            pilot_mode: If True, only process limited cases for testing
            pilot_year: Year to use for pilot extraction
            pilot_limit: Max number of cases to process in pilot mode
        """
        self.pdf_root = Path(pdf_root_dir)
        self.output_dir = Path(output_dir)
        self.pilot_mode = pilot_mode
        self.pilot_year = pilot_year
        self.pilot_limit = pilot_limit
        
        # Create output directories
        self.text_dir = self.output_dir / "text"
        self.metadata_dir = self.output_dir / "metadata"
        self.logs_dir = self.output_dir / "logs"
        
        for dir in [self.text_dir, self.metadata_dir, self.logs_dir]:
            dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
    
    def parse_filename_metadata(self, filename: str, year: int) -> Dict:
        """
        Extract metadata from filename
        Pattern: Petitioner_vs_Respondent_on_Date_1.PDF
        """
        # Remove .PDF extension
        name = filename.replace('.PDF', '').replace('.pdf', '')
        
        # Extract date using regex
        date_pattern = r'on_(\d+_\w+_\d{4})'
        date_match = re.search(date_pattern, name)
        
        judgment_date = None
        if date_match:
            date_str = date_match.group(1).replace('_', ' ')
            try:
                judgment_date = datetime.strptime(date_str, '%d %B %Y').strftime('%Y-%m-%d')
            except:
                pass
        
        # Split by _vs_
        parties = name.split('_vs_')
        petitioner = parties[0].replace('_', ' ').strip() if len(parties) > 0 else "Unknown"
        
        # Extract respondent (before _on_)
        respondent = "Unknown"
        if len(parties) > 1:
            respondent_part = parties[1].split('_on_')[0] if '_on_' in parties[1] else parties[1]
            respondent = respondent_part.replace('_', ' ').strip()
        
        # Generate case ID
        case_id = f"{year}_SC_{self.stats['total']:05d}"
        
        return {
            'case_id': case_id,
            'case_name': f"{petitioner} vs {respondent}",
            'petitioner': petitioner,
            'respondent': respondent,
            'judgment_date': judgment_date,
            'year': year,
            'filename': filename
        }
    
    def extract_with_pdfplumber(self, pdf_path: Path) -> Optional[str]:
        """Extract text using pdfplumber (better for complex layouts)"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                return '\n\n'.join(text_parts) if text_parts else None
        except Exception as e:
            return None
    
    def extract_with_pymupdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text using PyMuPDF (faster fallback)"""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            for page in doc:
                text = page.get_text()
                if text:
                    text_parts.append(text)
            doc.close()
            
            return '\n\n'.join(text_parts) if text_parts else None
        except Exception as e:
            return None
    
    def extract_text(self, pdf_path: Path) -> Optional[str]:
        """Extract text with fallback strategy"""
        # Try pdfplumber first
        text = self.extract_with_pdfplumber(pdf_path)
        
        # Fallback to PyMuPDF if pdfplumber fails
        if not text or len(text.strip()) < 100:
            text = self.extract_with_pymupdf(pdf_path)
        
        return text
    
    def validate_extraction(self, text: str) -> bool:
        """Validate if extraction was successful"""
        if not text:
            return False
        
        # Check minimum length (judgments should be substantial)
        if len(text.strip()) < 500:
            return False
        
        # Check for common judgment markers
        markers = ['supreme court', 'judgment', 'petitioner', 'respondent', 'held']
        text_lower = text.lower()
        if not any(marker in text_lower for marker in markers):
            return False
        
        return True
    
    def process_single_pdf(self, pdf_path: Path, year: int) -> Dict:
        """Process a single PDF file"""
        result = {
            'success': False,
            'pdf_path': str(pdf_path),
            'error': None
        }
        
        try:
            # Extract metadata from filename
            metadata = self.parse_filename_metadata(pdf_path.name, year)
            
            # Extract text
            text = self.extract_text(pdf_path)
            
            # Validate
            if not self.validate_extraction(text):
                result['error'] = "Validation failed (insufficient or invalid content)"
                return result
            
            # Save text
            year_text_dir = self.text_dir / str(year)
            year_text_dir.mkdir(parents=True, exist_ok=True)
            
            text_file = year_text_dir / f"{metadata['case_id']}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Update metadata with text stats
            metadata['word_count'] = len(text.split())
            metadata['char_count'] = len(text)
            metadata['text_file'] = str(text_file.relative_to(self.output_dir))
            
            # Save metadata
            year_meta_dir = self.metadata_dir / str(year)
            year_meta_dir.mkdir(parents=True, exist_ok=True)
            
            meta_file = year_meta_dir / f"{metadata['case_id']}_metadata.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            result['success'] = True
            result['metadata'] = metadata
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_pdf_files(self) -> List[tuple]:
        """Get list of PDF files to process"""
        pdf_files = []
        
        if self.pilot_mode:
            # Process only pilot year
            year_dir = self.pdf_root / str(self.pilot_year)
            if year_dir.exists():
                pdfs = list(year_dir.glob("*.PDF")) + list(year_dir.glob("*.pdf"))
                pdfs = pdfs[:self.pilot_limit]
                pdf_files = [(pdf, self.pilot_year) for pdf in pdfs]
        else:
            # Process all years
            for year_folder in sorted(self.pdf_root.iterdir()):
                if year_folder.is_dir() and year_folder.name.isdigit():
                    year = int(year_folder.name)
                    if 1950 <= year <= 2025:
                        pdfs = list(year_folder.glob("*.PDF")) + list(year_folder.glob("*.pdf"))
                        pdf_files.extend([(pdf, year) for pdf in pdfs])
        
        return pdf_files
    
    def run(self):
        """Main extraction process"""
        print("\n" + "="*70)
        print("SUPREME COURT JUDGMENTS PDF EXTRACTOR")
        print("="*70)
        
        if self.pilot_mode:
            print(f"[PILOT MODE] Processing {self.pilot_limit} cases from {self.pilot_year}")
        else:
            print("[FULL MODE] Processing all available cases")
        
        # Get PDF files
        pdf_files = self.get_pdf_files()
        self.stats['total'] = len(pdf_files)
        
        if not pdf_files:
            print("[ERROR] No PDF files found!")
            return
        
        print(f"\n[INFO] Found {len(pdf_files)} PDF files to process")
        print(f"[INFO] Output directory: {self.output_dir}")
        print("\n[PROGRESS] Starting extraction...\n")
        
        # Process files
        for pdf_path, year in tqdm(pdf_files, desc="Extracting PDFs"):
            result = self.process_single_pdf(pdf_path, year)
            
            if result['success']:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'file': pdf_path.name,
                    'error': result['error']
                })
        
        # Save statistics
        self.save_stats()
        
        # Print summary
        self.print_summary()
    
    def save_stats(self):
        """Save extraction statistics"""
        stats_file = self.logs_dir / f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)
    
    def print_summary(self):
        """Print extraction summary"""
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Total PDFs:     {self.stats['total']}")
        print(f"Successful:     {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        print(f"Failed:         {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        
        if self.stats['errors']:
            print(f"\n[ERRORS] First 5 failures:")
            for error in self.stats['errors'][:5]:
                print(f"  - {error['file']}: {error['error']}")
        
        print(f"\n[OUTPUT] Extracted text: {self.text_dir}")
        print(f"[OUTPUT] Metadata: {self.metadata_dir}")
        print("="*70 + "\n")

def main():
    # Create extractor instance
    extractor = SCJudgmentExtractor(
        pilot_mode=True,   # Start with pilot
        pilot_year=2024,   # Most recent year
        pilot_limit=100    # Test with 100 cases
    )
    
    # Run extraction
    extractor.run()

if __name__ == "__main__":
    main()
