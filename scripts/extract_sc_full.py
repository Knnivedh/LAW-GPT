"""
FULL SCALE SC JUDGMENTS EXTRACTOR
Processes ALL 26,688 Supreme Court judgment PDFs
Optimized for reliability and speed
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# PDF extraction libraries
try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[WARN] PyMuPDF not installed. Using pdfplumber only.")
    fitz = None

from tqdm import tqdm

# Configuration
PDF_SOURCE_DIR = Path("DATA/supreme_court_judgments_100%/supreme_court_judgments")
OUTPUT_DIR = Path("DATA/SC_Judgments_FULL")
TEXT_DIR = OUTPUT_DIR / "text"
METADATA_DIR = OUTPUT_DIR / "metadata"
CHUNKS_DIR = OUTPUT_DIR / "chunks"
LOGS_DIR = OUTPUT_DIR / "logs"

# Processing settings
MAX_WORKERS = 4  # Parallel processing threads
BATCH_SIZE = 100  # Save progress every N files
MIN_TEXT_LENGTH = 500  # Minimum valid text length

# Thread-safe counters
lock = threading.Lock()
stats = {
    'total': 0,
    'processed': 0,
    'success': 0,
    'failed': 0,
    'skipped': 0
}

def setup_directories():
    """Create output directories"""
    for d in [TEXT_DIR, METADATA_DIR, CHUNKS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Output directory: {OUTPUT_DIR}")

def parse_filename(filename: str) -> dict:
    """Extract metadata from PDF filename"""
    # Pattern: {Petitioner}_vs_{Respondent}_on_{Date}_1.PDF
    pattern = r'^(.+?)_vs_(.+?)_on_(\d+_\w+_\d{4}).*\.PDF$'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if match:
        petitioner = match.group(1).replace('_', ' ').strip()
        respondent = match.group(2).replace('_', ' ').strip()
        date_str = match.group(3).replace('_', ' ')
        
        # Parse date
        try:
            date_obj = datetime.strptime(date_str, "%d %B %Y")
            judgment_date = date_obj.strftime("%Y-%m-%d")
            year = date_obj.year
        except:
            judgment_date = date_str
            year = None
            
        return {
            'petitioner': petitioner,
            'respondent': respondent,
            'case_name': f"{petitioner} vs {respondent}",
            'judgment_date': judgment_date,
            'year': year
        }
    
    # Fallback: extract year from parent directory
    return {
        'petitioner': 'Unknown',
        'respondent': 'Unknown', 
        'case_name': filename.replace('.PDF', '').replace('_', ' '),
        'judgment_date': None,
        'year': None
    }

def extract_text_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber (higher quality)"""
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n\n'.join(text_parts)
    except Exception as e:
        return None

def extract_text_pymupdf(pdf_path: Path) -> str:
    """Extract text using PyMuPDF (faster, fallback)"""
    if fitz is None:
        return None
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return '\n\n'.join(text_parts)
    except:
        return None

def extract_text(pdf_path: Path) -> tuple:
    """Extract text with dual-engine fallback"""
    # Try pdfplumber first (better quality)
    text = extract_text_pdfplumber(pdf_path)
    engine = 'pdfplumber'
    
    # Fallback to PyMuPDF if needed
    if not text or len(text) < MIN_TEXT_LENGTH:
        text2 = extract_text_pymupdf(pdf_path)
        if text2 and len(text2) > len(text or ''):
            text = text2
            engine = 'pymupdf'
    
    return text, engine

def clean_text(text: str) -> str:
    """Clean extracted text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove page headers/footers (common patterns)
    text = re.sub(r'Indian Kanoon - http://indiankanoon\.org/doc/\d+/\s*\d*', '', text)
    
    return text.strip()

def create_chunks(text: str, metadata: dict, chunk_size: int = 1500, overlap: int = 150) -> list:
    """Create intelligent chunks from text"""
    chunks = []
    words = text.split()
    total_words = len(words)
    
    if total_words == 0:
        return []
    
    chunk_idx = 0
    i = 0
    
    while i < total_words:
        chunk_words = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk_words)
        
        # Detect section type
        section = 'full_text'
        priority = 'medium'
        
        chunk_lower = chunk_text[:500].lower()
        if any(x in chunk_lower for x in ['held:', 'conclusion', 'order:', 'judgment']):
            section = 'conclusion'
            priority = 'high'
        elif any(x in chunk_lower for x in ['issue', 'question', 'consideration']):
            section = 'issues'
            priority = 'high'
        elif any(x in chunk_lower for x in ['facts', 'background']):
            section = 'facts'
            priority = 'medium'
        elif any(x in chunk_lower for x in ['argument', 'submission', 'contention']):
            section = 'arguments'
            priority = 'medium'
        
        chunk = {
            'chunk_id': f"{metadata['case_id']}_chunk_{chunk_idx:04d}",
            'text': chunk_text,
            'section': section,
            'priority': priority,
            'chunk_index': chunk_idx,
            'total_chunks': None,  # Will be updated
            **metadata
        }
        chunks.append(chunk)
        
        chunk_idx += 1
        i += chunk_size - overlap
    
    # Update total chunks
    for c in chunks:
        c['total_chunks'] = len(chunks)
    
    return chunks

def process_pdf(pdf_path: Path, year_dir: str) -> dict:
    """Process a single PDF file"""
    try:
        filename = pdf_path.name
        case_id = f"{year_dir}_{pdf_path.stem[:50]}"  # Truncate long names
        case_id = re.sub(r'[^\w\-]', '_', case_id)  # Clean ID
        
        # Check if already processed
        text_file = TEXT_DIR / year_dir / f"{case_id}.txt"
        if text_file.exists():
            return {'status': 'skipped', 'case_id': case_id}
        
        # Extract text
        text, engine = extract_text(pdf_path)
        
        if not text or len(text) < MIN_TEXT_LENGTH:
            return {'status': 'failed', 'case_id': case_id, 'reason': 'insufficient_text'}
        
        # Clean text
        text = clean_text(text)
        
        # Parse metadata from filename
        metadata = parse_filename(filename)
        metadata['case_id'] = case_id
        metadata['filename'] = filename
        metadata['year'] = metadata.get('year') or int(year_dir) if year_dir.isdigit() else None
        metadata['word_count'] = len(text.split())
        metadata['char_count'] = len(text)
        metadata['extraction_engine'] = engine
        
        # Create output directories
        (TEXT_DIR / year_dir).mkdir(parents=True, exist_ok=True)
        (METADATA_DIR / year_dir).mkdir(parents=True, exist_ok=True)
        (CHUNKS_DIR / year_dir).mkdir(parents=True, exist_ok=True)
        
        # Save text
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save metadata
        meta_file = METADATA_DIR / year_dir / f"{case_id}_meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Create and save chunks
        chunks = create_chunks(text, metadata)
        chunks_file = CHUNKS_DIR / year_dir / f"{case_id}_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2)
        
        return {
            'status': 'success',
            'case_id': case_id,
            'chunks': len(chunks),
            'words': metadata['word_count']
        }
        
    except Exception as e:
        return {'status': 'failed', 'case_id': str(pdf_path.name), 'reason': str(e)}

def process_year(year_dir: Path) -> list:
    """Process all PDFs in a year directory"""
    year_name = year_dir.name
    pdf_files = list(year_dir.glob("*.PDF")) + list(year_dir.glob("*.pdf"))
    
    results = []
    for pdf_path in pdf_files:
        result = process_pdf(pdf_path, year_name)
        results.append(result)
        
        # Update stats thread-safely
        with lock:
            stats['processed'] += 1
            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'failed':
                stats['failed'] += 1
            else:
                stats['skipped'] += 1
    
    return results

def get_all_pdfs() -> list:
    """Get all PDF files organized by year"""
    all_pdfs = []
    
    for year_dir in sorted(PDF_SOURCE_DIR.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            pdf_files = list(year_dir.glob("*.PDF")) + list(year_dir.glob("*.pdf"))
            for pdf in pdf_files:
                all_pdfs.append((pdf, year_dir.name))
    
    return all_pdfs

def save_progress_log():
    """Save processing log"""
    log_file = LOGS_DIR / f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'stats': stats.copy()
        }, f, indent=2)

def main():
    print("\n" + "="*70)
    print("SUPREME COURT JUDGMENTS - FULL SCALE EXTRACTION")
    print("Processing ALL 26,688 PDFs for Advanced RAG")
    print("="*70)
    
    # Setup
    setup_directories()
    
    # Get all PDFs
    print("\n[SCAN] Finding all PDF files...")
    all_pdfs = get_all_pdfs()
    stats['total'] = len(all_pdfs)
    print(f"[OK] Found {stats['total']:,} PDF files")
    
    # Process with progress bar
    print("\n[EXTRACT] Starting extraction...")
    start_time = time.time()
    
    with tqdm(total=len(all_pdfs), desc="Extracting PDFs", unit="file") as pbar:
        for pdf_path, year_name in all_pdfs:
            result = process_pdf(pdf_path, year_name)
            
            # Update stats
            if result['status'] == 'success':
                stats['success'] += 1
            elif result['status'] == 'failed':
                stats['failed'] += 1
            else:
                stats['skipped'] += 1
            stats['processed'] += 1
            
            pbar.update(1)
            pbar.set_postfix({
                'success': stats['success'],
                'failed': stats['failed'],
                'skipped': stats['skipped']
            })
            
            # Save progress periodically
            if stats['processed'] % BATCH_SIZE == 0:
                save_progress_log()
    
    # Final stats
    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)
    print(f"Total PDFs:        {stats['total']:,}")
    print(f"Processed:         {stats['processed']:,}")
    print(f"Successful:        {stats['success']:,} ({100*stats['success']/max(1,stats['total']):.1f}%)")
    print(f"Failed:            {stats['failed']:,}")
    print(f"Skipped:           {stats['skipped']:,}")
    print(f"Time:              {elapsed/60:.1f} minutes")
    print(f"Speed:             {stats['processed']/elapsed:.1f} files/sec")
    print("="*70)
    print(f"\n[OUTPUT] Text files: {TEXT_DIR}")
    print(f"[OUTPUT] Metadata:   {METADATA_DIR}")
    print(f"[OUTPUT] Chunks:     {CHUNKS_DIR}")
    
    # Save final log
    save_progress_log()
    
    print("\n[NEXT] Run: python scripts/ingest_sc_full.py")

if __name__ == "__main__":
    main()
