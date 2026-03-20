"""
Migrate Specific Gap Fix Cases
Injects 6 high-impact cases to fix user-identified gaps
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / 'config' / '.env')

from rag_system.core.supabase_store import SupabaseHybridStore

def migrate_gap_fix():
    print("=" * 80)
    print("🚀 MIGRATING GAP FIX CASES (Hadiya, Dev Dutt, Najeeb...)")
    print("=" * 80)
    
    # Load cases
    data_path = project_root / "DATA" / "specific_gap_fix_cases.json"
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    store = SupabaseHybridStore()
    documents = []
    
    for case in data['cases']:
        print(f"  • Processing: {case['case_name']}")
        
        case_text = f"""
LANDMARK CASE: {case['case_name']}

Citation: {case['citation']}
Year: {case['year']}
Domain: {case['domain']}
Importance: {case['importance']}

LEGAL PRINCIPLE:
{case['legal_principle']}

KEY HOLDINGS:
{chr(10).join(['• ' + holding for holding in case['key_holdings']])}

STATUTORY PROVISIONS:
{', '.join(case.get('relevant_sections', []))}
"""
        metadata = {
            "source": "Gap Fix Expansion",
            "type": "landmark_case",
            "case_name": case['case_name'],
            "citation": case['citation'],
            "year": case['year'],
            "domain": case['domain'],
            "importance": case['importance']
        }
        
        documents.append({
            "text": case_text.strip(),
            "metadata": metadata
        })
        
    # Migrate
    print(f"\n📤 Uploading {len(documents)} critical cases...")
    texts = [d['text'] for d in documents]
    metas = [d['metadata'] for d in documents]
    
    try:
        store.add_documents(texts, metas)
        print("✅ SUCCESS! Cases injected into RAG memory.")
    except Exception as e:
        print(f"❌ Error: {e}")
        
    print("=" * 80)

if __name__ == "__main__":
    migrate_gap_fix()
