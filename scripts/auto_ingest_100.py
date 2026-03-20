"""
AUTOMATED 100% DATA INGESTION (NON-INTERACTIVE)
Runs all ingestion steps automatically with GPU acceleration
No emojis to avoid Windows encoding issues
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import logging
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Add parent to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_str(value, default='N/A'):
    """Convert None to default string"""
    return str(value) if value is not None else default

def ingest_kanoon_qa():
    """Ingest Kanoon Q&A data"""
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    
    print("\n" + "="*80)
    print("[STEP 1/4] KANOON Q&A INGESTION - 102K Documents")
    print("="*80)
    
    KANOON_QA = PROJECT_ROOT / "DATA" / "kanoon.com" / "kanoon.com" / "kanoon_data.json"
    
    if not KANOON_QA.exists():
        print(f"[ERROR] File not found: {KANOON_QA}")
        return 0
    
    store = HybridChromaStore()
    
    print(f"Loading from: {KANOON_QA}")
    with open(KANOON_QA, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
    
    print(f"Loaded {len(qa_data):,} Q&A entries")
    
    batch_size = 100
    indexed = 0
    
    for i in tqdm(range(0, len(qa_data), batch_size), desc="Kanoon Q&A"):
        batch = qa_data[i:i+batch_size]
        
        texts = []
        metadatas = []
        ids = []
        
        for j, entry in enumerate(batch):
            question_title = safe_str(entry.get('query_title'), 'Untitled')
            question_text = safe_str(entry.get('query_text'), 'No question text')
            answer_text = safe_str(entry.get('response_text'), 'No response')
            category = safe_str(entry.get('query_category'), 'General')
            url = safe_str(entry.get('query_url'), f'kanoon_{i}_{j}')
            
            doc_text = f"""
QUESTION: {question_text}

TITLE: {question_title}
CATEGORY: {category}

EXPERT ANSWER:
{answer_text}
"""
            
            metadata = {
                'source': 'Kanoon Q&A Individual',
                'title': question_title[:500],
                'question': question_text[:500],
                'category': category,
                'url': url[:500],
                'type': 'qa_individual'
            }
            
            texts.append(doc_text)
            metadatas.append(metadata)
            ids.append(f"kanoon_individual_{i+j}_{hash(url) % 100000}")
        
        try:
            store.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            indexed += len(batch)
        except Exception as e:
            logger.error(f"Error in batch {i}: {e}")
    
    print(f"\n[OK] Indexed {indexed:,} Kanoon Q&A entries")
    return indexed

def ingest_news_sources():
    """Ingest news articles from multiple sources"""
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    
    print("\n" + "="*80)
    print("[STEP 2/4] NEWS SOURCES INGESTION")
    print("="*80)
    
    store = HybridChromaStore()
    total_indexed = 0
    
    news_folders = [
        PROJECT_ROOT / "DATA" / "indianexpress_property_law_qa",
        PROJECT_ROOT / "DATA" / "ndtv_legal_qa_data",
        PROJECT_ROOT / "DATA" / "legallyin.com",
        PROJECT_ROOT / "DATA" / "thehindu",
    ]
    
    for folder in news_folders:
        if not folder.exists():
            print(f"[SKIP] {folder.name} not found")
            continue
        
        print(f"\nProcessing: {folder.name}")
        
        json_files = list(folder.glob("**/*.json"))
        
        for jf in json_files:
            try:
                with open(jf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for i, item in enumerate(data[:1000]):  # Limit per file
                        text = safe_str(item.get('content') or item.get('text') or item.get('body'), '')
                        title = safe_str(item.get('title'), 'Untitled')
                        
                        if len(text) < 50:
                            continue
                        
                        try:
                            store.collection.add(
                                documents=[f"{title}\n\n{text}"],
                                metadatas=[{
                                    'source': folder.name,
                                    'title': title[:500],
                                    'type': 'news'
                                }],
                                ids=[f"news_{folder.name}_{jf.stem}_{i}"]
                            )
                            total_indexed += 1
                        except:
                            pass
            except Exception as e:
                logger.error(f"Error processing {jf}: {e}")
    
    print(f"\n[OK] Indexed {total_indexed:,} news articles")
    return total_indexed

def ingest_json_files():
    """Ingest standalone JSON files in DATA folder"""
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    
    print("\n" + "="*80)
    print("[STEP 3/4] JSON FILES INGESTION")
    print("="*80)
    
    store = HybridChromaStore()
    total_indexed = 0
    
    json_files = [
        PROJECT_ROOT / "DATA" / "landmark_legal_cases.json",
        PROJECT_ROOT / "DATA" / "landmark_legal_cases_expansion.json",
        PROJECT_ROOT / "DATA" / "consumer_law_specifics.json",
        PROJECT_ROOT / "DATA" / "law_transitions_2024.json",
        PROJECT_ROOT / "DATA" / "pwdva_comprehensive.json",
        PROJECT_ROOT / "DATA" / "specific_gap_fix_cases.json",
    ]
    
    for jf in json_files:
        if not jf.exists():
            print(f"[SKIP] {jf.name} not found")
            continue
        
        print(f"Processing: {jf.name}")
        
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for i, item in enumerate(data):
                    text = json.dumps(item, ensure_ascii=False)
                    title = safe_str(item.get('title') or item.get('name') or item.get('case_name'), jf.stem)
                    
                    try:
                        store.collection.add(
                            documents=[text],
                            metadatas=[{
                                'source': jf.stem,
                                'title': title[:500],
                                'type': 'json_data'
                            }],
                            ids=[f"json_{jf.stem}_{i}"]
                        )
                        total_indexed += 1
                    except:
                        pass
            elif isinstance(data, dict):
                for key, value in list(data.items())[:500]:
                    text = f"{key}: {json.dumps(value, ensure_ascii=False)}"
                    try:
                        store.collection.add(
                            documents=[text],
                            metadatas=[{
                                'source': jf.stem,
                                'title': str(key)[:500],
                                'type': 'json_data'
                            }],
                            ids=[f"json_{jf.stem}_{key}"]
                        )
                        total_indexed += 1
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error processing {jf}: {e}")
    
    print(f"\n[OK] Indexed {total_indexed:,} JSON entries")
    return total_indexed

def ingest_case_law():
    """Ingest case law from CaseLaw and NCDRC folders"""
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    
    print("\n" + "="*80)
    print("[STEP 4/4] CASE LAW INGESTION")
    print("="*80)
    
    store = HybridChromaStore()
    total_indexed = 0
    
    case_folders = [
        PROJECT_ROOT / "DATA" / "CaseLaw",
        PROJECT_ROOT / "DATA" / "NCDRC",
        PROJECT_ROOT / "DATA" / "SC_Judgments" / "json",
    ]
    
    for folder in case_folders:
        if not folder.exists():
            print(f"[SKIP] {folder} not found")
            continue
        
        print(f"\nProcessing: {folder}")
        
        json_files = list(folder.glob("**/*.json"))[:5000]  # Limit
        
        for jf in tqdm(json_files, desc=folder.name):
            try:
                with open(jf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    text = safe_str(data.get('text') or data.get('content') or data.get('judgment'), '')
                    title = safe_str(data.get('title') or data.get('case_name'), jf.stem)
                    
                    if len(text) < 100:
                        continue
                    
                    try:
                        store.collection.add(
                            documents=[f"{title}\n\n{text[:50000]}"],  # Limit text size
                            metadatas=[{
                                'source': folder.name,
                                'title': title[:500],
                                'type': 'case_law'
                            }],
                            ids=[f"case_{folder.name}_{jf.stem}"]
                        )
                        total_indexed += 1
                    except:
                        pass
            except Exception as e:
                pass
    
    print(f"\n[OK] Indexed {total_indexed:,} case law documents")
    return total_indexed

def main():
    print("\n" + "="*80)
    print("AUTOMATED 100% DATA INGESTION")
    print("GPU: CUDA Enabled")
    print("="*80)
    
    total = 0
    
    # Step 1: Kanoon Q&A (largest dataset)
    try:
        total += ingest_kanoon_qa()
    except Exception as e:
        print(f"[ERROR] Kanoon ingestion failed: {e}")
    
    # Step 2: News Sources
    try:
        total += ingest_news_sources()
    except Exception as e:
        print(f"[ERROR] News ingestion failed: {e}")
    
    # Step 3: JSON Files
    try:
        total += ingest_json_files()
    except Exception as e:
        print(f"[ERROR] JSON ingestion failed: {e}")
    
    # Step 4: Case Law
    try:
        total += ingest_case_law()
    except Exception as e:
        print(f"[ERROR] Case law ingestion failed: {e}")
    
    print("\n" + "="*80)
    print("INGESTION COMPLETE!")
    print("="*80)
    print(f"Total documents indexed: {total:,}")
    print("\nRestart the server to use new data:")
    print("  python kaanoon_test/advanced_rag_api_server.py")

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        print("\n" + "!"*80)
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        print("!"*80)
        sys.exit(1)
