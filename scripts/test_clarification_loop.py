import sys
import os
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestClarification")

def run_test():
    # Use Groq by default for testing as user provided those keys
    engine = ClarificationSession(provider="groq")
    
    # 1. Start Session
    query = "I want to divorce my wife who is cheating on me."
    logger.info(f"--- STARTING SESSION: '{query}' ---")
    
    state = engine.start_session(query)
    logger.info(f"Stage 1 Result: {state['status']}")
    logger.info(f"First Question: {state['first_question']}")
    
    # 2. Simulate User Responses (Loop)
    dummy_answers = [
        "We have been married for 5 years.",
        "Yes, I have proof of her WhatsApp chats.",
        "We have one daughter, age 4.",
        "I want full custody of my daughter.",
        "She is currently living with her parents."
    ]
    
    for i, ans in enumerate(dummy_answers):
        logger.info(f"\nUser Answer {i+1}: {ans}")
        state = engine.submit_answer(ans)
        
        if state['status'] == 'clarification_loop':
            logger.info(f"System Question {i+2}: {state['next_question']}")
        elif state['status'] == 'ready_for_synthesis':
            logger.info("Loop Complete. Ready for Synthesis.")
            
    # 3. Synthesis
    final_state = engine.synthesize_and_execute()
    logger.info("\n--- FINAL CONSOLIDATED MATRIX ---")
    logger.info(final_state['matrix'])
    
    logger.info("\nTEST COMPLETE")

if __name__ == "__main__":
    run_test()
