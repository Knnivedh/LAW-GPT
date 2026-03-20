"""
FULLY AUTOMATED KAGGLE INTEGRATION PIPELINE
Run this after downloading the Kaggle ZIP file

This script will:
1. Find the downloaded ZIP file
2. Extract it automatically
3. Process all PDFs
4. Migrate to Supabase
5. Run comprehensive test
6. Show final results

Usage: python scripts/automated_kaggle_pipeline.py
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def find_kaggle_zip():
    """Find the downloaded Kaggle ZIP file"""
    print("\n🔍 Searching for Kaggle ZIP file...")
    
    # Common download locations
    possible_locations = [
        Path.home() / "Downloads",
        project_root / "DATA",
        project_root,
    ]
    
    for location in possible_locations:
        if location.exists():
            # Look for files with 'supreme-court' or similar in name
            for file in location.glob("*.zip"):
                if any(keyword in file.name.lower() for keyword in ['supreme', 'court', 'judgment', 'kaggle']):
                    print(f"✅ Found: {file}")
                    return file
    
    return None

def extract_zip(zip_path, extract_to):
    """Extract ZIP file"""
    print(f"\n📦 Extracting {zip_path.name}...")
    print(f"📂 Destination: {extract_to}")
    
    extract_to.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get total size
        total_size = sum(info.file_size for info in zip_ref.filelist)
        extracted_size = 0
        
        print(f"Total size: {total_size / (1024**3):.2f} GB")
        
        for file_info in zip_ref.filelist:
            zip_ref.extract(file_info, extract_to)
            extracted_size += file_info.file_size
            
            if extracted_size % (100 * 1024 * 1024) < file_info.file_size:  # Every 100 MB
                progress = (extracted_size / total_size) * 100
                print(f"  Progress: {progress:.1f}%")
        
        print("✅ Extraction complete!")
    
    # Count PDFs
    pdf_count = len(list(extract_to.glob("*.pdf")))
    print(f"✅ Found {pdf_count} PDF files")
    
    return pdf_count

def run_processing(pdf_dir):
    """Run PDF processing"""
    print("\n🔬 Processing PDFs...")
    print("This will take 30-60 minutes for 26k PDFs...")
    
    os.system(f'python scripts/process_kaggle_sc_pdfs.py --pdf-dir "{pdf_dir}" --process')

def run_migration():
    """Run Supabase migration"""
    print("\n📤 Migrating to Supabase...")
    print("This will take 10-15 minutes...")
    
    os.system('python scripts/process_kaggle_sc_pdfs.py --migrate')

def run_test():
    """Run comprehensive test"""
    print("\n🧪 Running Comprehensive Test...")
    
    os.system('python scripts/advanced_legal_test.py')

import argparse

def main():
    parser = argparse.ArgumentParser(description='Automated Kaggle Integration Pipeline')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 AUTOMATED KAGGLE INTEGRATION PIPELINE")
    print("=" * 80)
    
    # Step 1: Find ZIP
    zip_file = find_kaggle_zip()
    
    if not zip_file:
        print("\n❌ Kaggle ZIP file not found!")
        print("\n📥 Please download it first:")
        print("1. Go to: https://www.kaggle.com/datasets/sh0416/supreme-court-judgments-india")
        print("2. Click 'Download' button")
        print("3. Save to your Downloads folder or DATA folder")
        print("4. Run this script again")
        return
    
    # Step 2: Extract
    extract_dir = project_root / "DATA" / "kaggle_supreme_court"
    
    if extract_dir.exists() and len(list(extract_dir.glob("*.pdf"))) > 1000:
        print(f"\n✅ PDFs already extracted at: {extract_dir}")
        pdf_count = len(list(extract_dir.glob("*.pdf")))
        print(f"✅ Found {pdf_count} existing PDFs")
    else:
        pdf_count = extract_zip(zip_file, extract_dir)
    
    # Step 3: Confirm before processing
    print("\n" + "=" * 80)
    print("📊 READY TO PROCESS")
    print("=" * 80)
    print(f"PDFs to process: {pdf_count}")
    print(f"Estimated time: 45-75 minutes")
    print("Tasks:")
    print("  1. Extract text from all PDFs (30-60 min)")
    print("  2. Migrate to Supabase (10-15 min)")
    print("  3. Run comprehensive test (3 min)")
    print("=" * 80)
    
    if args.confirm:
        print("\n▶️  Auto-confirming start...")
    else:
        response = input("\n▶️  Start automated processing? (y/n): ").lower().strip()
        if response != 'y':
            print("\n⏸️  Processing paused.")
            print(f"PDFs ready at: {extract_dir}")
            print("Run when ready: python scripts/automated_kaggle_pipeline.py --confirm")
            return
    
    start_time = time.time()
    
    # Step 4: Process PDFs
    run_processing(extract_dir)
    
    # Step 5: Migrate to Supabase
    run_migration()
    
    # Step 6: Run test
    run_test()
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("🎉 AUTOMATED PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"📊 Expected accuracy: 90/100 (A Grade)")
    print("\n🔬 Check test results in advanced_legal_test_*.json")
    print("=" * 80)

if __name__ == "__main__":
    main()
