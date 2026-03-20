"""
MIGRATE TO SUPABASE SCRIPT
Reads kaanoon_qa_dataset_cleaned.json and uploads to Supabase.
"""

import sys
import json
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.core.supabase_store import SupabaseHybridStore
from dotenv import load_dotenv

# Load env vars
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

def migrate():
    print("="*80)
    print("STARTING SUPABASE MIGRATION")
    print("="*80)
    
    # Initialize Store
    try:
        store = SupabaseHybridStore()
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("Make sure SUPABASE_URL and SUPABASE_KEY are in config/.env")
        return

    # Load Data
    dataset_path = Path(__file__).parent.parent / "kaanoon_test" / "kaanoon_qa_dataset_cleaned.json"
    if not dataset_path.exists():
        print(f"❌ Dataset not found at {dataset_path}")
        return
        
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"✅ Loaded {len(data)} items from dataset")
    
    # Prepare documents
    documents = []
    for item in data:
        # Construct text representation for embedding (Q + A)
        text = f"Question: {item.get('question_summary', '')}\nAnswer: {item.get('answer_summary', '')}"
        
        doc = {
            "text": text,
            "metadata": {
                "id": item.get('id'),
                "category": item.get('category', 'general'),
                "question": item.get('question_summary', ''),
                "answer": item.get('answer_summary', '') # Store answer in metadata for retrieval display
            }
        }
        documents.append(doc)
        
    # Upload
    print(f"🚀 Uploading {len(documents)} documents to Supabase...")
    store.add_documents(documents, batch_size=50)
    print("\n✅ MIGRATION COMPLETE!")

if __name__ == "__main__":
    migrate()
