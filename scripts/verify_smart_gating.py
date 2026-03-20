import sys
import os
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession

# Verify Smart Gating Logic
def test_smart_gating():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger("SmartGatingTest")
    
    # Mock Retriever (Should NOT be called for greetings/irrelevant)
    def mock_retriever(query):
        logger.warning(f"!!! RAG RETRIEVER CALLED FOR: {query} !!!")
        return "Legal Context Content"

    engine = ClarificationSession(provider="groq", retriever_callback=mock_retriever)
    
    test_cases = [
        ("Hi there", "greeting"),
        ("Hello, who are you?", "greeting"),
        ("Why is the sky blue?", "irrelevant"),
        ("Write a python script for binary search", "irrelevant"),
        ("I want a divorce from my husband", "needs_clarification"), # Should trigger RAG
        ("My neighbor built a wall on my property", "needs_clarification") # Should trigger RAG
    ]
    
    print("\n" + "="*60)
    print("RUNNING SMART GATING VERIFICATION")
    print("="*60)
    
    passed = 0
    for query, expected_status in test_cases:
        print(f"\nQUERY: '{query}'")
        result = engine.start_session(query)
        status = result.get('status')
        message = result.get('message', '')
        print(f"  -> Result Status: {status}")
        if status == "irrelevant":
            print(f"  -> Helpful Answer: {message[:100]}...")
        
        if status == expected_status or (expected_status == "needs_clarification" and "clarification" in status):
            print("  [PASS] Correct Status")
            passed += 1
        else:
            print(f"  [FAIL] Expected '{expected_status}', got '{status}'")
            
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed}/{len(test_cases)} Passed")
    print("="*60)

if __name__ == "__main__":
    test_smart_gating()
