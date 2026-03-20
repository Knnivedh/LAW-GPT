import sys
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

def run_direct_eval():
    print("Initializing UnifiedAdvancedRAG for direct evaluation...")
    rag = UnifiedAdvancedRAG()
    
    query = """I am a homebuyer who booked a luxury apartment in Noida in 2019. The possession was due in 2022 but is delayed. 
    The builder is now undergoing Corporate Insolvency Resolution Process (CIRP) initiated by a bank under Section 7 of IBC. 
    I want to withdraw from the project and claim a full refund with 18% interest.
    
    1. Can I still file a consumer complaint in NCDRC for refund now that CIRP has started, or does the Moratorium bar it?
    2. What is my exact status as a homebuyer under IBC 2016 following the 'Pioneer Urban Land' judgment - am I a financial creditor or operational creditor?
    3. If the liquidation happens, where do I stand in the priority of distribution (waterfall mechanism)?"""
    
    print("\n[QUERYING RAG SYSTEM...]")
    results = rag.query(query)
    
    print("\n" + "="*80)
    print("RAG ANSWER")
    print("="*80)
    print(results.get('answer'))
    
    print("\n" + "="*80)
    print("SOURCES USED")
    print("="*80)
    for i, doc in enumerate(results.get('source_documents', [])):
        meta = doc.get('metadata', {})
        print(f"[{i+1}] {meta.get('source', 'Unknown')} | {meta.get('act_name', 'N/A')} Section {meta.get('section', 'N/A')}")
        print(f"    Excerpt: {doc.get('page_content', '')[:100]}...")
    
    # Save to file for LLM to read and analyze
    with open("direct_eval_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_direct_eval()
