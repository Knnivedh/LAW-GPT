"""
MIGRATE LAW DOCS TO SUPABASE
Reads indian_kanoon_collection.json (33MB), cleans HTML, and uploads to Supabase.
"""

import sys
import json
import os
import re
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.core.supabase_store import SupabaseHybridStore
from dotenv import load_dotenv

# Load env vars
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

def clean_html(raw_html):
    """Remove HTML tags and clean whitespace"""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return ' '.join(cleantext.split())

def migrate_law_docs():
    print("="*80)
    print("STARTING LAW DOCS MIGRATION (Indian Kanoon)")
    print("="*80)
    
    # Initialize Store
    try:
        store = SupabaseHybridStore()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Load Data
    dataset_path = Path(__file__).parent.parent / "kaanoon_test" / "indian_kanoon_collection.json"
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        return
        
    print("Loading JSON (this may take a moment)...")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    docs_list = data.get('documents', [])
    print(f"✅ Loaded {len(docs_list)} documents from {dataset_path.name}")
    
    # Prepare documents
    documents = []
    print("Processing and cleaning documents...")
    
    for item in docs_list:
        title = item.get('title', 'Unknown')
        raw_text = item.get('text', '')
        cleaned_text = clean_html(raw_text)
        
        if not cleaned_text:
            continue
            
        # If text is too long, we might need to chunk it. 
        # For now, let's truncate to 4000 chars to stay safe for embeddings/token limits if needed, 
        # but all-MiniLM can handle large context by truncation internally. 
        # Supabase vector col doesn't care content length, but embedding model does.
        # We'll let the text go in, but embedding model will truncate.
        
        doc = {
            "text": cleaned_text,
            "metadata": {
                "id": item.get('id'),
                "title": title,
                "citation": item.get('citation'),
                "year": item.get('year'),
                "source": "indian_kanoon",
                "original_url": f"https://indiankanoon.org/doc/{item.get('id', '').replace('indiankanoon_', '')}/"
            }
        }
        documents.append(doc)
        
    print(f"🚀 Prepared {len(documents)} documents. Starting upload...")
    
    # Upload in batches
    store.add_documents(documents, batch_size=20)
    print("\n✅ LAW DOCS MIGRATION COMPLETE!")

if __name__ == "__main__":
    migrate_law_docs()
