"""
Comprehensive Chatbot Testing Script
Tests all fixes and optimizations
"""
import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:5000"

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_test(name, status, details=""):
    status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
    print(f"{status_symbol} {name} {details}")

def test_fast_lookup():
    """Test 1: Fast Lookup (IPC Sections)"""
    print_header("TEST 1: Fast Lookup (IPC Sections)")
    
    queries = [
        "What is IPC Section 302?",
        "What is IPC 304?",
        "What is IPC 498A?"
    ]
    
    results = []
    for q in queries:
        try:
            start = time.time()
            response = requests.post(
                f"{API_BASE}/api/query",
                json={"question": q, "category": "general"},
                timeout=10
            )
            elapsed = time.time() - start
            data = response.json()
            
            answer_len = len(data['response']['answer'])
            status = "PASS" if elapsed < 1.0 else "WARN"
            print_test(f"{q[:30]}...", status, f"{elapsed:.3f}s - {answer_len} chars")
            results.append((q, elapsed, answer_len, status == "PASS"))
        except Exception as e:
            print_test(f"{q[:30]}...", "FAIL", str(e))
            results.append((q, 0, 0, False))
    
    return results

def test_simple_queries():
    """Test 2: Simple Queries (Ultra-Fast Mode)"""
    print_header("TEST 2: Simple Queries (Optimized)")
    
    queries = [
        "What is FIR?",
        "What is divorce?",
        "What is property?"
    ]
    
    results = []
    for q in queries:
        try:
            start = time.time()
            response = requests.post(
                f"{API_BASE}/api/query",
                json={"question": q, "category": "general"},
                timeout=60
            )
            elapsed = time.time() - start
            data = response.json()
            
            answer_len = len(data['response']['answer'])
            if elapsed < 5:
                status = "PASS"
            elif elapsed < 10:
                status = "WARN"
            else:
                status = "FAIL"
            
            print_test(f"{q[:30]}...", status, f"{elapsed:.2f}s - {answer_len} chars")
            results.append((q, elapsed, answer_len, status == "PASS"))
            time.sleep(0.5)
        except Exception as e:
            print_test(f"{q[:30]}...", "FAIL", str(e))
            results.append((q, 0, 0, False))
    
    return results

def test_complex_query():
    """Test 3: Complex Multi-Part Query"""
    print_header("TEST 3: Complex Multi-Part Query")
    
    query = """Questions on CPC Procedures: Q1: In a Civil Suit, after the plaintiff provides the evidence, what occurs as the next stage in the process, 'cross-examination of the plaintiff' or the 'cross-examination of defendant', which comes first? Q2: I am appearing party-in-person (as plaintiff) for a case before a quasi-judicial body. The chairperson insists on recording the evidences in Tamil eventhough I asked it to be taken in English. I would like to know what is the current scenario in lower courts and quasi-judicial bodies in Tamil Nadu state with regards to the language to be used in recording evidence in the proceedings?"""
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/query",
            json={"question": query, "category": "general"},
            timeout=60
        )
        elapsed = time.time() - start
        data = response.json()
        
        answer_len = len(data['response']['answer'])
        if elapsed < 15:
            status = "PASS"
        elif elapsed < 30:
            status = "WARN"
        else:
            status = "FAIL"
        
        print_test("Multi-part CPC question", status, f"{elapsed:.2f}s - {answer_len} chars")
        if answer_len > 1500:
            print("  [PASS] Answer is comprehensive")
        
        return (query, elapsed, answer_len, status == "PASS")
    except Exception as e:
        print_test("Multi-part CPC question", "FAIL", str(e))
        return (query, 0, 0, False)

def test_api_endpoints():
    """Test 4: API Endpoints"""
    print_header("TEST 4: API Endpoints")
    
    results = []
    
    # Test /api/stats
    try:
        response = requests.get(f"{API_BASE}/api/stats", timeout=5)
        print_test("/api/stats", "PASS", f"Status: {response.status_code}")
        results.append(("stats", True))
    except Exception as e:
        print_test("/api/stats", "FAIL", str(e))
        results.append(("stats", False))
    
    # Test /api/examples
    try:
        response = requests.get(f"{API_BASE}/api/examples", timeout=5)
        data = response.json()
        count = len(data.get('examples', []))
        print_test("/api/examples", "PASS", f"{count} examples")
        results.append(("examples", True))
    except Exception as e:
        print_test("/api/examples", "FAIL", str(e))
        results.append(("examples", False))
    
    return results

def test_response_quality():
    """Test 5: Response Quality"""
    print_header("TEST 5: Response Quality")
    
    query = "Property ownership rights in India"
    
    try:
        response = requests.post(
            f"{API_BASE}/api/query",
            json={"question": query, "category": "general"},
            timeout=60
        )
        data = response.json()
        answer = data['response']['answer']
        
        checks = []
        if len(answer) > 500:
            checks.append(("Length > 500 chars", True))
            print_test("Length check", "PASS", f"{len(answer)} chars")
        else:
            checks.append(("Length > 500 chars", False))
            print_test("Length check", "FAIL", f"Only {len(answer)} chars")
        
        import re
        if re.search(r'Section|Article|Act|IPC|CPC|CrPC', answer):
            checks.append(("Legal citations", True))
            print_test("Legal citations", "PASS", "Found")
        else:
            checks.append(("Legal citations", False))
            print_test("Legal citations", "FAIL", "Not found")
        
        if re.search(r'\n|##|###|[-*]', answer):
            checks.append(("Structured format", True))
            print_test("Structured format", "PASS", "Found")
        else:
            checks.append(("Structured format", False))
            print_test("Structured format", "FAIL", "Not found")
        
        return checks
    except Exception as e:
        print_test("Response quality", "FAIL", str(e))
        return []

def main():
    print("\n" + "="*60)
    print("  COMPREHENSIVE CHATBOT TESTING")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {
        "fast_lookup": test_fast_lookup(),
        "simple_queries": test_simple_queries(),
        "complex_query": test_complex_query(),
        "api_endpoints": test_api_endpoints(),
        "response_quality": test_response_quality()
    }
    
    # Summary
    print_header("TEST SUMMARY")
    
    total_tests = 0
    passed_tests = 0
    
    # Fast lookup
    fast_passed = sum(1 for r in all_results["fast_lookup"] if r[3])
    fast_total = len(all_results["fast_lookup"])
    print(f"Fast Lookup: {fast_passed}/{fast_total} passed")
    total_tests += fast_total
    passed_tests += fast_passed
    
    # Simple queries
    simple_passed = sum(1 for r in all_results["simple_queries"] if r[3])
    simple_total = len(all_results["simple_queries"])
    print(f"Simple Queries: {simple_passed}/{simple_total} passed")
    total_tests += simple_total
    passed_tests += simple_passed
    
    # Complex query
    complex_passed = 1 if all_results["complex_query"][3] else 0
    print(f"Complex Query: {complex_passed}/1 passed")
    total_tests += 1
    passed_tests += complex_passed
    
    # API endpoints
    api_passed = sum(1 for r in all_results["api_endpoints"] if r[1])
    api_total = len(all_results["api_endpoints"])
    print(f"API Endpoints: {api_passed}/{api_total} passed")
    total_tests += api_total
    passed_tests += api_passed
    
    # Response quality
    quality_passed = sum(1 for r in all_results["response_quality"] if r[1])
    quality_total = len(all_results["response_quality"])
    print(f"Response Quality: {quality_passed}/{quality_total} checks passed")
    total_tests += quality_total
    passed_tests += quality_passed
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({passed_tests*100//total_tests}%)")
    
    print("\n" + "="*60)
    print("  KEY METRICS")
    print("="*60)
    print("  - Fast Lookups: Should be <1s")
    print("  - Simple Queries: Should be <10s (optimized)")
    print("  - Complex Queries: Should be <60s (timeout)")
    print("  - Response Quality: Should be comprehensive")
    print("\nNext: Test UI features in browser at http://localhost:3001")
    print("="*60)

if __name__ == "__main__":
    main()

