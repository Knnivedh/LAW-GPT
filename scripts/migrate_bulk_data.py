"""
BULK MIGRATION SCRIPT
Scans CONSUMER_DATA_COLLECTION and uploads all JSON datasets to Supabase.
Handles various file formats.
"""

import sys
import json
import os
import glob
from pathlib import Path
import re

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.core.supabase_store import SupabaseHybridStore
from dotenv import load_dotenv

# Load env vars
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

def find_json_files(root_dir):
    json_files = []
    # Recursively find all json files
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def clean_text(text):
    if not text: return ""
    # Basic HTML scrubbing
    text = re.sub('<[^<]+?>', '', str(text))
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_and_parse_json(filepath):
    print(f"Loading {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

    docs = []
    
    # helper to process a single item
    def process_item(item, source_tag):
        if not isinstance(item, dict): return None
        
        # Check if this item is actually a container for more documents
        if 'documents' in item and isinstance(item['documents'], list):
            nested_docs = []
            for sub_item in item['documents']:
                d = process_item(sub_item, source_tag)
                if d: nested_docs.append(d)
            return nested_docs if nested_docs else None
            
        text_content = ""
        metadata = {"source": source_tag, "file": Path(filepath).name}
        
        # Try different keys for text content
        if 'text' in item: text_content = item['text']
        elif 'content' in item: text_content = item['content']
        elif 'summary' in item: text_content = item['summary']
        elif 'query_text' in item and 'response_text' in item:
            text_content = f"Q: {item['query_text']}\nA: {item['response_text']}"
            if 'query_title' in item: metadata['title'] = item['query_title']
            if 'query_category' in item: metadata['category'] = item['query_category']
        elif 'question' in item and 'answer' in item:
            text_content = f"Q: {item['question']}\nA: {item['answer']}"
        elif 'Question' in item and 'Answer' in item:
            text_content = f"Q: {item['Question']}\nA: {item['Answer']}"
        elif 'body' in item: text_content = item['body']
        
        # Specific handling for Case Studies (50k dataset)
        elif 'case_title' in item and 'case_description' in item:
             text_content = f"Case: {item['case_title']}\nDescription: {item['case_description']}\nVerdict: {item.get('verdict', 'N/A')}\n"
             if 'legal_aspects' in item:
                 text_content += f"Legal Aspects: {json.dumps(item['legal_aspects'])}"
             metadata['case_id'] = item.get('case_id')
             metadata['title'] = item.get('case_title')
             metadata['type'] = item.get('case_type')
        
        # Metadata extraction
        for k in ['title', 'url', 'id', 'category', 'year', 'link', 'section', 'doc_id', 'case_id', 'case_type']:
            if k in item: metadata[k] = item[k]
        
        # Add metadata from parent if available (not implemented generically here but kept simple)
            
        if text_content and len(str(text_content)) > 50: # Skip very short snippets
            return {
                "text": clean_text(text_content),
                "metadata": metadata
            }
        return None

    all_docs = []
    
    # Generic recursive finder
    def find_docs(data_obj):
        if isinstance(data_obj, list):
            for i in data_obj:
                find_docs(i)
        elif isinstance(data_obj, dict):
            # Try to process as a document
            res = process_item(data_obj, "data_collection")
            if isinstance(res, list): # it was a container returning a list
                all_docs.extend(res)
            elif res: # it was a single doc
                all_docs.append(res)
            
            # Continue search in values if it's a dict (in case of nested structures we missed)
            for k, v in data_obj.items():
                if isinstance(v, (list, dict)):
                    find_docs(v)
    
    find_docs(data)
    return all_docs

def migrate_bulk():
    print("="*80)
    print("🚀 STARTING BULK DATA MIGRATION TO SUPABASE")
    print("="*80)
    
    # 1. Connect to Supabase
    try:
        store = SupabaseHybridStore(
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_key=os.environ.get("SUPABASE_KEY")
        )
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return

    # 2. Find all JSON files in CONSUMER and DATA directories
    base_dirs = [
        Path("CONSUMER_DATA_COLLECTION"),
        Path("DATA")
    ]
    
    all_files = []
    for d in base_dirs:
        if d.exists():
            all_files.extend(find_json_files(d))
            
    print(f"📍 Found {len(all_files)} potential data files.")
    
    total_uploaded = 0
    
    for filepath in all_files:
        print(f"\n📂 Processing: {filepath}")
        docs = load_and_parse_json(filepath)
        print(f"   found {len(docs)} documents.")
        
        if docs:
            # Upload in batches
            batch_size = 100
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i+batch_size]
                try:
                    store.add_documents(batch)
                    print(f"   Uploaded batch {i//batch_size + 1}/{len(docs)//batch_size + 1}")
                    total_uploaded += len(batch)
                except Exception as e:
                    print(f"   ❌ Error uploading batch: {e}")
                    # Continue to next batch
                    
    print("\n" + "="*80)
    print(f"🎉 MIGRATION COMPLETE. Total documents uploaded: {total_uploaded}")
    print("="*80)

if __name__ == "__main__":
    migrate_bulk()
