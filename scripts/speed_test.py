"""
SPEED TEST - Verify Sub-10s Response Time
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

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

def speed_test():
    print("\n" + "="*60)
    print("SPEED TEST - Target: Sub-10 Second Response")
    print("="*60)
    
    rag = UnifiedAdvancedRAG()
    
    test_queries = [
        ("Simple", "What is bail?"),
        ("Medium", "What are consumer rights under CPA 2019?"),
    ]
    
    for complexity, query in test_queries:
        print(f"\n[{complexity}] Query: {query}")
        
        start = time.time()
        response = rag.query(query, category="General")
        latency = time.time() - start
        
        status = "PASS" if latency < 10 else "FAIL"
        print(f"Latency: {latency:.2f}s [{status}]")
        print(f"Answer: {response['answer'][:100]}...")

if __name__ == "__main__":
    speed_test()
