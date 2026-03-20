import json, time, logging
from kaanoon_test.utils.client_manager import GroqClientManager
from kaanoon_test.system_adapters.agentic_rag_engine import AgenticRAGEngine
from kaanoon_test.system_adapters.persistent_memory import AgenticMemoryManager
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("STRESS_TEST")

def run_stress_test():
    # Load scenarios
    from stress_test_scenarios import scenarios
    
    # Initialize Engine
    client_manager = GroqClientManager()
    memory = AgenticMemoryManager()
    retriever = MagicMock() # Mocked to focus on reasoning/clarification logic
    parametric = MagicMock()
    
    engine = AgenticRAGEngine(
        client_manager=client_manager,
        parametric_rag=parametric,
        retriever=retriever,
        memory_manager=memory
    )
    
    results = []
    
    print("\n" + "="*80)
    print("LAW-GPT v3.0 STRESS TEST: INTERACTIVE REASONING AUDIT")
    print("="*80 + "\n")
    
    for i, s in enumerate(scenarios, 1):
        print(f"[{i}/10] Testing: {s['title']}")
        logger.info(f"Running scenario {i}: {s['title']}")
        
        t0 = time.time()
        # Simple Mode disabled to force agentic loop
        result = engine.run(user_query=s['query'], session_id=f"stress_test_{i}")
        duration = time.time() - t0
        
        # Check if clarification was triggered
        trace = result.reasoning_trace
        triggered = "needs_clarification" in trace
        
        questions = []
        if triggered and result.sources:
            questions = result.sources[0].get("questions", [])
        
        status = "PASSED (Clarification Triggered)" if triggered and len(questions) == 5 else "FAILED"
        if not triggered:
            status = "FAILED (No clarification asked)"
        elif len(questions) != 5:
            status = f"FAILED (Asked {len(questions)} questions instead of 5)"
            
        print(f"Status: {status}")
        print(f"Time Taken: {duration:.2f}s")
        
        if triggered:
            print(f"Sample Question: {questions[0] if questions else 'N/A'}")
        
        results.append({
            "id": i,
            "title": s['title'],
            "status": status,
            "duration": duration,
            "questions_asked": len(questions),
            "triggered": triggered
        })
        print("-" * 40)
        time.sleep(2) # Prevent rate limits
        
    # Summary
    passed = sum(1 for r in results if "PASSED" in r['status'])
    accuracy = (passed / len(scenarios)) * 100
    
    print("\n" + "="*80)
    print(f"FINAL AUDIT RESULTS: {accuracy}% Accuracy")
    print(f"Passed: {passed} | Failed: {len(scenarios) - passed}")
    print("="*80 + "\n")
    
    with open("stress_test_report.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_stress_test()
