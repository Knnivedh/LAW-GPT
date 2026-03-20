"""
Verify Retrieval of New Cases
Checks if Hadiya and Dev Dutt cases are actually retrievable
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / 'config' / '.env')

from rag_system.core.supabase_store import SupabaseHybridStore

def check_retrieval():
    print("=" * 80)
    print("🕵️ VERIFYING RETRIEVAL FOR NEW CASES")
    print("=" * 80)
    
    store = SupabaseHybridStore()
    
    # 1. Test Hadiya Case
    query = "Hadiya marriage conversion case Shafin Jahan"
    print(f"\n🔍 Query: {query}")
    
    # Use hybrid_search and handle dict results
    results = store.hybrid_search(query, n_results=5)
    
    found = False
    for i, doc in enumerate(results):
        meta = doc.get('metadata', {})
        print(f"  Result {i+1}: {meta.get('case_name', 'Unknown')}")
        if 'Hadiya' in doc['text'] or 'Shafin' in doc['text']:
            found = True
            print("  ✅ FOUND HADIYA CASE!")
            
    if not found:
        print("  ❌ Hadiya case NOT found in top 5 results")

    # 2. Test Dev Dutt Case
    query = "Dev Dutt uncommunicated ACR confidential report"
    print(f"\n🔍 Query: {query}")
    
    results = store.hybrid_search(query, n_results=5)
    
    found = False
    for i, doc in enumerate(results):
        meta = doc.get('metadata', {})
        print(f"  Result {i+1}: {meta.get('case_name', 'Unknown')}")
        if 'Dev Dutt' in doc['text']:
            found = True
            print("  ✅ FOUND DEV DUTT CASE!")
            
    if not found:
        print("  ❌ Dev Dutt case NOT found in top 5 results")

if __name__ == "__main__":
    check_retrieval()
