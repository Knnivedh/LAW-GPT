"""
TEST ADVANCED RAG - Verify new retrieval features
"""
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

def test_advanced_rag():
    print("\n" + "="*70)
    print("ADVANCED RAG TEST - Multi-Query + HyDE + Re-ranking")
    print("="*70)
    
    from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
    
    print("\n[1/3] Initializing Advanced RAG System...")
    rag = UnifiedAdvancedRAG()
    
    # Test queries with different complexities
    test_cases = [
        {
            "query": "What are the grounds for divorce under Hindu law?",
            "category": "Family",
            "complexity": "complex"  # Should trigger multi-query + HyDE
        },
        {
            "query": "Consumer Protection Act 2019 complaint procedure",
            "category": "Consumer", 
            "complexity": "medium"  # Should trigger re-ranking
        },
        {
            "query": "Section 302 IPC punishment",
            "category": "Criminal",
            "complexity": "simple"  # Standard retrieval
        }
    ]
    
    print("\n[2/3] Running Advanced Retrieval Tests...\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {case['query'][:50]}...")
        print(f"Complexity: {case['complexity']}")
        print('='*60)
        
        start = time.time()
        
        try:
            response = rag.query(case['query'], category=case['category'])
            latency = time.time() - start
            
            # Check results
            answer = response.get('answer', '')[:200]
            sources = response.get('source_documents', [])
            metadata = response.get('metadata', {})
            
            print(f"\nLatency: {latency:.2f}s")
            print(f"Sources Retrieved: {len(sources)}")
            print(f"Advanced Mode: {metadata.get('advanced_mode', 'N/A')}")
            print(f"\nAnswer Preview:\n{answer}...")
            
            # Check for advanced features
            if metadata.get('advanced_mode'):
                print("\n[OK] Advanced retrieval was used!")
            else:
                print("\n[INFO] Standard retrieval was used")
                
        except Exception as e:
            print(f"\n[ERROR] {e}")
    
    print("\n[3/3] Test Complete!")
    print("="*70)

if __name__ == "__main__":
    test_advanced_rag()
