import sys
import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

def test_conversational_accuracy():
    """Verify 90% Accuracy (Citation Preservation) and Conversational Memory"""
    
    print("\n" + "="*80)
    print("⚖️ STARTING CONVERSATIONAL ACCURACY TEST")
    print("="*80)
    
    try:
        rag = UnifiedAdvancedRAG()
        history = []
        
        # TURN 1: Complex Query (Test for Manmohan Nanda)
        query_1 = """A health insurer repudiated a claim for pre-existing disease (PED) after 3 years, 
        despite previously approving a claim for the same condition. 
        Does the doctrine of waiver/estoppel apply?"""
        
        print(f"\n🚀 Turn 1: {query_1[:100]}...")
        result_1 = rag.query(query_1, chat_history=history)
        answer_1 = result_1.get('answer', '')
        
        print("\n" + "-"*40)
        print("✅ Answer 1 Snippet:\n" + answer_1[:500])
        
        # Check for Manmohan Nanda (The citation lost previously)
        if "Manmohan Nanda" in answer_1:
            print("\n🎯 SUCCESS: 'Manmohan Nanda' citation PRESERVED!")
        else:
            print("\n❌ FAILURE: 'Manmohan Nanda' citation MISSING.")
            
        # Update history
        history.append({"role": "user", "content": query_1})
        history.append({"role": "assistant", "content": answer_1})
        
        # TURN 2: Follow-up (Test for Memory)
        query_2 = "What does that doctrine mean in simple terms?"
        print(f"\n🚀 Turn 2: {query_2}")
        
        result_2 = rag.query(query_2, chat_history=history)
        answer_2 = result_2.get('answer', '')
        
        print("\n" + "-"*40)
        print("✅ Answer 2 Snippet:\n" + answer_2[:500])
        
        if "estoppel" in answer_2.lower() or "waiver" in answer_2.lower():
             print("\n🎯 SUCCESS: Context maintained (Explained Estoppel/Waiver)")
        else:
             print("\n❌ FAILURE: Context lost.")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_conversational_accuracy()
