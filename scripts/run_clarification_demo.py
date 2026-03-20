import sys
import os
import logging
from pathlib import Path
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession
from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ClarificationDemo")

def run_full_demo():
    print("\n" + "="*80)
    print(" ADVANCED LEGAL CLARIFICATION SYSTEM DEMO (Unified RAG Integration)")
    print("="*80)
    
    # 1. Initialize Engines
    # Use "groq" as it was verified to work with the user's key
    provider = "groq" 
    print(f"\n[1] Initializing Clarification Engine (Provider: {provider.upper()})...")
    clarification_engine = ClarificationSession(provider=provider)
    
    # Initialize RAG (assuming it works with default or env settings)
    # The UnifiedAdvancedRAG might fail if its own keys aren't set, 
    # but we will try to instantiate it.
    try:
        print("[2] Initializing Unified RAG System...")
        rag_system = UnifiedAdvancedRAG()
    except Exception as e:
        logger.error(f"Failed to load RAG system: {e}")
        return

    # 2. Intake
    query = "I want to divorce my wife because of cruelty."
    print(f"\n[USER QUERY]: {query}")
    
    state = clarification_engine.start_session(query)
    if state['status'] == 'error':
        logger.error(f"Intake failed: {state['message']}")
        return
        
    print(f"\n[SYSTEM INTENT]: {state['intent'].get('intent')}")
    print(f"[MISSING FACTS]: {state['intent'].get('missing_facts')}")
    
    # 3. Clarification Loop (Simulated)
    # In a real UI, this would be interactive. Here we provide dummy answers.
    simulated_answers = [
        "We have been married for 3 years.",
        "She constantly insults me in front of my friends and has physically hit me twice.",
        "We have no children.",
        "We live in Mumbai.",
        "I just want a peaceful separation, no alimony if possible."
    ]
    
    current_question = state['first_question']
    
    for i, ans in enumerate(simulated_answers):
        print(f"\n--- Turn {i+1}/5 ---")
        print(f"[AI QUESTION]: {current_question}")
        print(f"[USER ANSWER]: {ans}")
        
        step_result = clarification_engine.submit_answer(ans)
        
        if step_result['status'] == 'clarification_loop':
            current_question = step_result['next_question']
        elif step_result['status'] == 'ready_for_synthesis':
            print("\n[INFO] Clarification Complete. Synthesizing...")
            break
            
    # 4. Synthesis
    final_context = clarification_engine.synthesize_and_execute()
    matrix = final_context['matrix']
    print(f"\n[CONSOLIDATED MATRIX]:\n{matrix}")
    
    # 5. RAG Execution
    print("\n" + "="*40)
    print(" EXECUTING FINAL RAG QUERY ")
    print("="*40)
    
    # We construct a rich query from the matrix
    rag_query = f"""
    Based on the following facts, provide a legal opinion under Indian Law:
    {matrix}
    """
    
    result = rag_system.query(rag_query)
    
    print("\n[FINAL LEGAL OPINION]:")
    print(result.get('answer'))
    print("\n[SOURCES]:")
    for doc in result.get('source_documents', [])[:3]:
        print(f"- {doc.get('metadata', {}).get('act', 'Unknown Act')} (Sec {doc.get('metadata', {}).get('section_number')})")

if __name__ == "__main__":
    run_full_demo()
