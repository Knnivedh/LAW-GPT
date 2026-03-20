import sys
import os
import logging
from pathlib import Path
import json

# Add project root to path
file_path = Path(__file__).resolve()
PROJECT_ROOT = file_path.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession
from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

# Setup Logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',
    filename='interactive_test.log',
    filemode='w'
)
# Console handler
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logging.getLogger('').addHandler(console)

def run_interactive_session():
    print("\n" + "="*80)
    print(" INTERACTIVE LEGAL AI: COMPLEX SCENARIO TEST ")
    print("="*80)
    
    # 1. Initialize
    print("\n[System] Initializing Engines (this may take a moment)...")
    try:
        # Use Groq as preferred/tested provider
        engine = ClarificationSession(provider="groq")
        rag = UnifiedAdvancedRAG()
        print("[System] Ready.")
    except Exception as e:
        print(f"\n[Error] Initialization Failed: {e}")
        print("Check your .env keys and internet connection.")
        return

    # 2. The Complex Scenario
    scenario = """A 24-year-old woman and a 26-year-old man from different religions marry under the Special Marriage Act, 1954.
After marriage:
The woman’s family files a habeas corpus petition alleging she was brainwashed and coerced.
They also file an FIR alleging forced religious conversion, cheating, and criminal conspiracy.
The woman appears before the court and states that she married voluntarily and has not converted.
Meanwhile, the State government issues a circular directing police to verify all interfaith marriages for “public order concerns”.

Question:
What are the constitutional, statutory, and procedural issues the High Court must consider while deciding:
The maintainability of the habeas corpus petition
The validity of the SMA marriage
The legality of the police verification and FIR"""

    print(f"\n[SCENARIO LOADED]:\n{scenario}\n")
    print("-" * 50)
    
    # 3. Start Session
    print("[AI] Analyzing scenario intent...")
    state = engine.start_session(scenario)
    
    if state['status'] == 'error':
        print(f"[Error] {state['message']}")
        return

    print(f"\n[AI DETECTED INTENT]: {state['intent'].get('intent')}")
    print(f"[MISSING FACTS]: {state['intent'].get('missing_facts')}")
    print("-" * 50)

    # 4. Interactive Loop
    current_q = state['first_question']
    
    while True:
        print(f"\n[AI ADVOCATE]: {current_q}")
        
        # HUMAN INPUT
        user_ans = input("\n[YOU]: ").strip()
        
        if not user_ans:
            print("[System] Please provide an answer.")
            continue
            
        step_result = engine.submit_answer(user_ans)
        
        if step_result['status'] == 'clarification_loop':
            current_q = step_result['next_question']
        elif step_result['status'] == 'ready_for_synthesis':
            print("\n" + "="*50)
            print(" [INFO] INTERVIEW COMPLETE. PREPARING LEGAL OPINION.")
            print("="*50)
            break
            
    # 5. RAG Execution
    final_context = engine.synthesize_and_execute()
    matrix = final_context['matrix']
    
    print(f"\n[CONSOLIDATED LEGAL MATRIX]:\n{matrix}")
    print("\n[AI] Drafting Final Opinion via RAG... (Please wait)\n")
    
    rag_query = f"""
    Based on the following Consolidated Facts, answer the legal questions regarding Habeas Corpus maintainability, SMA validity, and Police Circular legality:
    
    {matrix}
    """
    
    result = rag.query(rag_query)
    
    print("\n" + "#"*80)
    print(" 🏛️  FINAL LEGAL OPINION ")
    print("#"*80)
    print(result.get('answer'))
    
    print("\n[Sources Used]:")
    for doc in result.get('source_documents', [])[:5]:
        meta = doc.get('metadata', {})
        print(f"- {meta.get('act', 'Doc')} | Sec {meta.get('section_number', 'N/A')}")

if __name__ == "__main__":
    try:
        run_interactive_session()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Execution Crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n[Process Complete] Press Enter to exit...")
