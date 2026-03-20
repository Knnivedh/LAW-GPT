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

def test_owl_single():
    """Run a SINGLE scenario (Insurance) to verify OWL integration without rate limits"""
    
    print("\n" + "="*80)
    print("⚖️ STARTING SINGLE-SHOT OWL AGENT VERIFICATION")
    print("="*80)
    
    try:
        rag = UnifiedAdvancedRAG()
        
        scenario = {
            "name": "Insurance & Estoppel",
            "query": """A health insurer repudiates a claim citing non-disclosure of a pre-existing disease, 
            relying on a discharge summary that allegedly contains an incorrect medical history recorded by a duty doctor. 
            The insured had earlier received claim approval for the same condition, and the policy was renewed without exclusions.
            Question: What statutory, contractual, and evidentiary issues must the Consumer Commission consider while deciding 
            whether the repudiation amounts to deficiency in service, bad faith, and unfair trade practice, and how does the doctrine of estoppel apply?"""
        }
        
        print(f"\n🚀 Running Scenario: {scenario['name']}...")
        result = rag.query(scenario['query'])
        answer = result.get('answer', '')
        
        print("\n" + "="*40)
        print("✅ FINAL GENERATED OPINION")
        print("="*40)
        print(answer)
        
        # Verify markers
        markers = ["Manmohan Nanda", "Section 45", "Estoppel"]
        found = [m for m in markers if m.lower() in answer.lower()]
        
        print("\n" + "="*40)
        print(f"🎯 MARKER CHECK: Found {len(found)}/{len(markers)}")
        print(f"   Markers: {found}")
        print("="*40)

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_owl_single()
