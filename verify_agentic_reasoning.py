import sys
import os
import json
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, r"C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT")

from kaanoon_test.system_adapters.agentic_rag_engine import AgenticRAGEngine
from kaanoon_test.system_adapters.persistent_memory import AgenticMemoryManager
from rag_system.core.milvus_store import CloudMilvusStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFIER")

def test_agentic_reasoning():
    # Real dependencies for reasoning test
    from kaanoon_test.utils.client_manager import GroqClientManager
    client_manager = GroqClientManager()
    
    memory = AgenticMemoryManager()
    retriever = MagicMock() # Mock retriever to focus on planning logic
    parametric = MagicMock()
    
    # Initialize the engine
    engine = AgenticRAGEngine(
        client_manager=client_manager,
        parametric_rag=parametric,
        retriever=retriever,
        memory_manager=memory
    )
    
    # Test 1: Complex Scenario (The Data Privacy Case)
    complex_query = (
        "A technology company launches a mobile payment application... "
        "mandatory data-sharing policy... broad consent clause... "
        "What constitutional, statutory, contractual, and procedural issues must the High Court consider?"
    )
    logger.info("Running Complex Scenario Test...")
    
    result = engine.run(user_query=complex_query, session_id="test_complex_scenario")
    
    print("\n--- AGENTIC REASONING VERIFICATION ---")
    print(f"Confidence Score: {result.confidence}")
    print(f"Answer Title: {result.answer}")
    
    if "clarification" in " ".join(result.reasoning_trace):
        print("SUCCESS: Engine identified high complexity and asked for clarifications.")
        for i, q in enumerate(result.sources[0].get("questions", []), 1):
            print(f"Question {i}: {q}")
    else:
        print("FAILURE: Engine did not trigger clarification loop.")

if __name__ == "__main__":
    test_agentic_reasoning()
