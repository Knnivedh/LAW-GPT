"""
LAW-GPT Comprehensive Accuracy & Deployment Test Suite
Tests the deployed system end-to-end for correctness, latency, and quality.
"""

import requests
import json
import time
import sys
import io
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"
RESULTS = []

# ─────────────────────────────────────────────
# TEST CASES  (question, expected_keywords, domain)
# ─────────────────────────────────────────────
TEST_CASES = [
    # IPC / Criminal Law
    {
        "question": "What is the punishment for murder under IPC?",
        "expected_keywords": ["302", "death", "life imprisonment", "IPC"],
        "domain": "criminal_ipc",
        "critical": True,
    },
    {
        "question": "What are the provisions for rape under Indian law?",
        "expected_keywords": ["376", "IPC", "imprisonment", "rape"],
        "domain": "criminal_ipc",
        "critical": True,
    },
    {
        "question": "What is kidnapping under IPC section 361?",
        "expected_keywords": ["361", "kidnapping", "minor", "guardian"],
        "domain": "criminal_ipc",
        "critical": True,
    },
    {
        "question": "Define theft under Indian Penal Code.",
        "expected_keywords": ["378", "theft", "movable property", "dishonest"],
        "domain": "criminal_ipc",
        "critical": True,
    },
    # Property Law
    {
        "question": "What is adverse possession under Indian law?",
        "expected_keywords": ["limitation", "possession", "12 years", "title"],
        "domain": "property_law",
        "critical": True,
    },
    {
        "question": "What is the process to register a property in India?",
        "expected_keywords": ["registration", "stamp duty", "sub-registrar", "Transfer of Property Act"],
        "domain": "property_law",
        "critical": False,
    },
    # Consumer Law
    {
        "question": "What are consumer rights under the Consumer Protection Act 2019?",
        "expected_keywords": ["consumer", "protection", "deficiency", "complaint", "forum"],
        "domain": "consumer_law",
        "critical": True,
    },
    # Family / Personal Law
    {
        "question": "What are the grounds for divorce under Hindu Marriage Act?",
        "expected_keywords": ["cruelty", "desertion", "divorce", "Hindu Marriage Act", "13"],
        "domain": "family_law",
        "critical": True,
    },
    {
        "question": "What is maintenance under Section 125 CrPC?",
        "expected_keywords": ["125", "maintenance", "wife", "children", "CrPC"],
        "domain": "family_law",
        "critical": True,
    },
    # Constitutional Law
    {
        "question": "What are fundamental rights in India?",
        "expected_keywords": ["Article", "Constitution", "right", "equality", "freedom"],
        "domain": "constitutional_law",
        "critical": True,
    },
    {
        "question": "What is Article 21 of the Indian Constitution?",
        "expected_keywords": ["21", "life", "personal liberty", "fundamental right"],
        "domain": "constitutional_law",
        "critical": True,
    },
    # Contract Law
    {
        "question": "What are the essentials of a valid contract in India?",
        "expected_keywords": ["offer", "acceptance", "consideration", "Contract Act", "1872"],
        "domain": "contract_law",
        "critical": True,
    },
    # Labour Law
    {
        "question": "What are the provisions for maternity benefit in India?",
        "expected_keywords": ["Maternity Benefit Act", "26 weeks", "leave", "maternity"],
        "domain": "labour_law",
        "critical": False,
    },
    # Edge Cases / Robustness
    {
        "question": "Hello, how are you?",
        "expected_keywords": [],
        "domain": "greeting_edge_case",
        "critical": False,
        "is_greeting": True,
    },
    {
        "question": "What is 2+2?",
        "expected_keywords": [],
        "domain": "non_legal_edge_case",
        "critical": False,
    },
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def check_health():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        data = r.json()
        rag_ok = data.get("rag_system_initialized", False)
        print(f"  [HEALTH] Status={data.get('status')} | RAG initialized={rag_ok}")
        return r.status_code == 200 and rag_ok
    except Exception as e:
        print(f"  [HEALTH] FAILED: {e}")
        return False


def query_api(question: str, session_id: str = "test-session") -> dict:
    payload = {
        "question": question,
        "session_id": session_id,
        "stream": False,
        "web_search_mode": False,
    }
    r = requests.post(f"{BASE_URL}/api/query", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # API wraps response under "response" key
    if "response" in data and isinstance(data["response"], dict):
        return data["response"]
    return data


def score_response(answer: str, expected_keywords: list) -> tuple[float, list]:
    """Return (score_0_to_1, found_keywords)."""
    if not expected_keywords:
        return 1.0, []
    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    score = len(found) / len(expected_keywords)
    return score, found


def run_test(tc: dict, idx: int) -> dict:
    question = tc["question"]
    domain = tc["domain"]
    expected = tc.get("expected_keywords", [])
    critical = tc.get("critical", False)

    print(f"\n  [{idx+1:02d}] [{domain.upper()}]")
    print(f"       Q: {question[:80]}")

    start = time.time()
    try:
        resp = query_api(question)
        latency = time.time() - start

        answer = resp.get("answer", "")
        confidence = resp.get("confidence", 0.0)
        sources_count = len(resp.get("sources", []))
        from_cache = resp.get("from_cache", False)
        complexity = resp.get("complexity", "unknown")

        score, found_kw = score_response(answer, expected)
        passed = score >= 0.5 if expected else True

        status = "PASS" if passed else ("FAIL (CRITICAL)" if critical else "FAIL (WARN)")
        print(f"       Latency: {latency:.2f}s | Confidence: {confidence:.2f} | Sources: {sources_count}")
        print(f"       Score: {score:.0%} | Found: {found_kw}")
        print(f"       Status: {status}")
        if len(answer) > 0:
            print(f"       Preview: {answer[:120].strip()}...")

        return {
            "idx": idx + 1,
            "domain": domain,
            "question": question,
            "passed": passed,
            "critical": critical,
            "score": score,
            "latency": latency,
            "confidence": confidence,
            "sources_count": sources_count,
            "from_cache": from_cache,
            "complexity": complexity,
            "found_keywords": found_kw,
            "answer_length": len(answer),
            "error": None,
        }

    except Exception as e:
        latency = time.time() - start
        print(f"       ERROR: {e}")
        return {
            "idx": idx + 1,
            "domain": domain,
            "question": question,
            "passed": False,
            "critical": critical,
            "score": 0.0,
            "latency": latency,
            "confidence": 0.0,
            "sources_count": 0,
            "from_cache": False,
            "complexity": "error",
            "found_keywords": [],
            "answer_length": 0,
            "error": str(e),
        }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  LAW-GPT DEPLOYMENT ACCURACY TEST SUITE")
    print(f"  Target: {BASE_URL}")
    print(f"  Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Health check
    print("\n[1] HEALTH CHECK")
    if not check_health():
        print("  FATAL: Backend not healthy — aborting tests.")
        sys.exit(1)
    print("  Backend healthy ✓")

    # 2. Run test cases
    print(f"\n[2] RUNNING {len(TEST_CASES)} TEST CASES")
    results = []
    for i, tc in enumerate(TEST_CASES):
        r = run_test(tc, i)
        results.append(r)

    # 3. Summary
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed_critical = [r for r in results if not r["passed"] and r["critical"]]
    failed_warn = [r for r in results if not r["passed"] and not r["critical"]]
    errors = [r for r in results if r["error"]]
    avg_latency = sum(r["latency"] for r in results) / total
    avg_confidence = sum(r["confidence"] for r in results) / total
    avg_score = sum(r["score"] for r in results) / total

    print(f"\n  Total Tests   : {total}")
    print(f"  Passed        : {passed}/{total} ({passed/total:.0%})")
    print(f"  Failed (CRIT) : {len(failed_critical)}")
    print(f"  Failed (WARN) : {len(failed_warn)}")
    print(f"  Errors        : {len(errors)}")
    print(f"\n  Avg Latency   : {avg_latency:.2f}s")
    print(f"  Avg Confidence: {avg_confidence:.2f}")
    print(f"  Avg Keyword Score: {avg_score:.0%}")

    if failed_critical:
        print("\n  CRITICAL FAILURES:")
        for r in failed_critical:
            print(f"    - [{r['domain']}] {r['question'][:60]} | score={r['score']:.0%}")

    if errors:
        print("\n  ERRORS:")
        for r in errors:
            print(f"    - [{r['domain']}] {r['error']}")

    # 4. Accuracy rating
    print("\n" + "=" * 70)
    accuracy_pct = passed / total * 100
    if accuracy_pct >= 90:
        grade = "A+ EXCELLENT"
    elif accuracy_pct >= 80:
        grade = "A GOOD"
    elif accuracy_pct >= 70:
        grade = "B ACCEPTABLE"
    elif accuracy_pct >= 60:
        grade = "C NEEDS IMPROVEMENT"
    else:
        grade = "F FAILING"

    print(f"\n  OVERALL ACCURACY: {accuracy_pct:.1f}%  →  {grade}")
    print(f"  SYSTEM STATUS: {'DEPLOYMENT READY' if not failed_critical else 'NEEDS FIXES'}")
    print("=" * 70)

    # 5. Save JSON report
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "total": total,
        "passed": passed,
        "accuracy_pct": accuracy_pct,
        "grade": grade,
        "avg_latency_s": avg_latency,
        "avg_confidence": avg_confidence,
        "results": results,
    }
    report_path = "accuracy_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Detailed report saved to: {report_path}")

    sys.exit(0 if not failed_critical else 1)


if __name__ == "__main__":
    main()
