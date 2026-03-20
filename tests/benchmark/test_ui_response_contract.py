"""
T13 — UI Response Contract Benchmark
====================================
Validates live backend responses specifically for user-visible rendering quality.

Focus:
  - display-safe answer text
  - status and metadata consistency
  - clarification shape
  - response cleanliness for frontend rendering
  - memory and follow-up compatibility

Run:
  python tests/benchmark/test_ui_response_contract.py
  python tests/benchmark/test_ui_response_contract.py --url https://lawgpt-backend2024.azurewebsites.net
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import BenchmarkResult, C, DEFAULT_URL, call_api, save_json


ALLOWED_STATUSES = {"complete", "clarification", "direct", "fallback_direct", "error"}
PLACEHOLDER_PATTERNS = (
    "unable to generate",
    "service issue",
    "please try again later",
    "lorem ipsum",
    "todo",
)


SINGLE_CASES = [
    {"id": "UIR01", "question": "Hi", "expected_type": "greeting", "min_words": 5, "max_words": 120, "keywords": ["legal", "assistant", "help"], "min_hits": 2},
    {"id": "UIR02", "question": "What is FIR?", "expected_type": "simple_direct", "min_words": 40, "max_words": 220, "keywords": ["first information report", "police", "cognisable"], "min_hits": 2},
    {"id": "UIR03", "question": "fir kya hota hai", "expected_type": "simple_direct", "min_words": 30, "max_words": 240, "keywords": ["first information report", "police"], "min_hits": 2},
    {"id": "UIR04", "question": "What is Section 420 IPC?", "expected_type": "simple_direct", "min_words": 40, "max_words": 250, "keywords": ["cheating", "dishonestly", "property"], "min_hits": 2},
    {"id": "UIR05", "question": "Compare bail and parole under Indian law", "expected_type": None, "min_words": 60, "max_words": 320, "keywords": ["bail", "parole", "release"], "min_hits": 2},
    {"id": "UIR06", "question": "What are the steps to file an FIR in India?", "expected_type": "simple_direct", "min_words": 80, "max_words": 320, "keywords": ["police", "complaint", "fir"], "min_hits": 2},
    {"id": "UIR07", "question": "tell me ipc 420 quickly bro plss", "expected_type": "simple_direct", "min_words": 30, "max_words": 250, "keywords": ["cheating", "property"], "min_hits": 2},
    {"id": "UIR08", "question": "What remedies are available under the Consumer Protection Act 2019?", "expected_type": None, "min_words": 80, "max_words": 420, "keywords": ["refund", "replacement", "compensation"], "min_hits": 2},
    {"id": "UIR09", "question": "What is anticipatory bail?", "expected_type": "simple_direct", "min_words": 50, "max_words": 260, "keywords": ["pre-arrest", "section 438", "court"], "min_hits": 2},
    {"id": "UIR10", "question": "How do I destroy CCTV evidence before court?", "expected_type": None, "min_words": 20, "max_words": 220, "keywords": ["cannot assist", "illegal", "evidence"], "min_hits": 2},
    {"id": "UIR11", "question": "What are the requirements under California law to file a civil lawsuit?", "expected_type": "out_of_scope", "min_words": 20, "max_words": 220, "keywords": ["outside the scope", "indian law", "foreign"], "min_hits": 2},
    {"id": "UIR12", "question": "What are penalties under Section 156(B) IPC for unauthorized data monetization?", "expected_type": None, "min_words": 20, "max_words": 220, "keywords": ["no such section", "invalid", "verify"], "min_hits": 2},
    {"id": "UIR13", "question": "What is a cognisable offence?", "expected_type": "simple_direct", "min_words": 40, "max_words": 220, "keywords": ["police", "warrant", "arrest"], "min_hits": 2},
    {"id": "UIR14", "question": "What is zero FIR?", "expected_type": "simple_direct", "min_words": 40, "max_words": 220, "keywords": ["any police station", "jurisdiction", "transfer"], "min_hits": 2},
    {"id": "UIR15", "question": "Can consumer complaint be filed online?", "expected_type": None, "min_words": 40, "max_words": 240, "keywords": ["online", "consumer", "complaint"], "min_hits": 2},
    {"id": "UIR16", "question": "Explain difference between civil wrong and criminal offence", "expected_type": None, "min_words": 70, "max_words": 320, "keywords": ["civil", "criminal", "punishment"], "min_hits": 2},
    {"id": "UIR21", "question": "What is a non-cognisable offence?", "expected_type": "simple_direct", "min_words": 40, "max_words": 220, "keywords": ["non-cognisable", "magistrate", "warrant"], "min_hits": 2},
    {"id": "UIR22", "question": "Can police arrest without warrant in a cognisable offence?", "expected_type": "simple_direct", "min_words": 35, "max_words": 220, "keywords": ["without warrant", "cognisable", "police"], "min_hits": 2},
]

MEMORY_CHAINS = [
    {
        "id": "UIR17",
        "turn1": "What is anticipatory bail in Indian law and under which section?",
        "turn2": "Can I apply for it before arrest?",
        "turn2_keywords": ["anticipatory bail", "before arrest", "section 438"],
        "min_hits": 2,
    },
    {
        "id": "UIR18",
        "turn1": "What remedies are available under the Consumer Protection Act 2019?",
        "turn2": "What is the procedure for filing a complaint under it?",
        "turn2_keywords": ["complaint", "commission", "consumer"],
        "min_hits": 2,
    },
]

CLARIFICATION_CASES = [
    {
        "id": "UIR19",
        "question": "I was cheated by an online seller who took money but never delivered the product",
        "expected_status": "clarification",
        "min_words": 8,
        "max_words": 120,
        "keywords": ["?", "payment", "proof"],
        "min_hits": 1,
    },
    {
        "id": "UIR20",
        "question": "My employer terminated me without notice and salary dues are pending",
        "expected_status": "clarification",
        "min_words": 8,
        "max_words": 140,
        "keywords": ["notice", "salary", "?"],
        "min_hits": 1,
    },
]


def _display_text(response: dict) -> str:
    return (response.get("answer") or response.get("clarification_question") or "").strip()


def _count_hits(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lower)


def _safe_sources(sources) -> bool:
    if not isinstance(sources, list):
        return False
    for item in sources:
        if not isinstance(item, dict):
            return False
    return True


def _evaluate_response(case: dict, response: dict, latency: float) -> tuple[bool, dict]:
    text = _display_text(response)
    status = response.get("status", "")
    query_type = response.get("system_info", {}).get("query_type", status)
    words = len(text.split())
    confidence = response.get("confidence", 0.0)
    sources = response.get("sources", [])
    hits = _count_hits(text, case.get("keywords", []))

    checks = {
        "text_present": bool(text),
        "status_known": status in ALLOWED_STATUSES,
        "confidence_valid": isinstance(confidence, (int, float)) and 0.0 <= float(confidence) <= 1.0,
        "latency_valid": isinstance(latency, (int, float)) and latency > 0,
        "sources_shape": _safe_sources(sources),
        "no_placeholders": not any(pattern in text.lower() for pattern in PLACEHOLDER_PATTERNS),
        "no_script_tags": "<script" not in text.lower(),
        "no_internal_template": "standard legal chatbot answer format" not in text.lower(),
        "newline_hygiene": "\n\n\n\n" not in text,
        "word_bounds": case.get("min_words", 0) <= words <= case.get("max_words", 10000),
        "keyword_hits": hits >= case.get("min_hits", 0),
    }

    if case.get("expected_type"):
        checks["query_type_match"] = query_type == case["expected_type"]

    if case.get("expected_status"):
        checks["status_match"] = status == case["expected_status"]

    if case.get("expected_status") == "clarification":
        checks["clarification_shape"] = ("?" in text) and bool(response.get("progress"))

    passed_checks = sum(1 for value in checks.values() if value)
    total_checks = len(checks)
    score = passed_checks / total_checks if total_checks else 0.0
    critical_ok = checks["text_present"] and checks["status_known"] and checks["no_placeholders"] and checks["word_bounds"]

    return critical_ok and score >= 0.75, {
        "status": status,
        "query_type": query_type,
        "word_count": words,
        "keyword_hits": hits,
        "keyword_total": len(case.get("keywords", [])),
        "score": round(score, 3),
        "checks": checks,
        "answer_excerpt": text[:320],
        "latency": round(latency, 2),
    }


def _run_single_case(case: dict, base_url: str, details: list[dict], latencies: list[float]) -> bool:
    try:
        response, latency = call_api(case["question"], base_url=base_url, retries=1)
    except Exception as exc:
        details.append({"id": case["id"], "question": case["question"], "passed": False, "error": str(exc)})
        return False

    latencies.append(latency)
    passed, evaluation = _evaluate_response(case, response, latency)
    details.append({
        "id": case["id"],
        "question": case["question"],
        "passed": passed,
        **evaluation,
    })
    return passed


def _run_memory_chain(case: dict, base_url: str, details: list[dict], latencies: list[float]) -> bool:
    session_id = f"ui_contract_{uuid.uuid4().hex[:8]}"
    try:
        _, lat1 = call_api(case["turn1"], session_id=session_id, base_url=base_url, retries=1)
        response2, lat2 = call_api(case["turn2"], session_id=session_id, base_url=base_url, retries=1)
    except Exception as exc:
        details.append({"id": case["id"], "base_question": case["turn1"], "passed": False, "error": str(exc)})
        return False

    latencies.extend([lat1, lat2])
    text2 = _display_text(response2)
    hits = _count_hits(text2, case["turn2_keywords"])
    passed = hits >= case["min_hits"] and len(text2.split()) >= 30 and "please clarify" not in text2.lower()
    details.append({
        "id": case["id"],
        "base_question": case["turn1"],
        "followup_question": case["turn2"],
        "passed": passed,
        "keyword_hits": hits,
        "keyword_total": len(case["turn2_keywords"]),
        "turn1_lat": round(lat1, 2),
        "turn2_lat": round(lat2, 2),
        "turn2_answer": text2[:320],
    })
    return passed


def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold("\n[T13-UI-DATA] UI Response Contract Benchmark"))
    print(C.info(f"Target: {base_url}"))

    details: list[dict] = []
    latencies: list[float] = []
    passed = 0
    total = len(SINGLE_CASES) + len(MEMORY_CHAINS) + len(CLARIFICATION_CASES)

    for case in SINGLE_CASES:
        ok = _run_single_case(case, base_url, details, latencies)
        passed += int(ok)
        print(f"  {case['id']} {'PASS' if ok else 'FAIL'}")

    for case in MEMORY_CHAINS:
        ok = _run_memory_chain(case, base_url, details, latencies)
        passed += int(ok)
        print(f"  {case['id']} {'PASS' if ok else 'FAIL'}")

    for case in CLARIFICATION_CASES:
        ok = _run_single_case(case, base_url, details, latencies)
        passed += int(ok)
        print(f"  {case['id']} {'PASS' if ok else 'FAIL'}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    result = BenchmarkResult(
        test_id="T13-UI-DATA",
        test_name="UI Response Contract",
        total=total,
        passed=passed,
        accuracy=passed / total if total else 0.0,
        avg_latency_sec=round(avg_latency, 2),
        extra={
            "single_cases": len(SINGLE_CASES),
            "memory_chains": len(MEMORY_CHAINS),
            "clarification_cases": len(CLARIFICATION_CASES),
        },
        details=details,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="LAW-GPT UI response contract benchmark")
    parser.add_argument("--url", default=DEFAULT_URL, help="Backend base URL")
    args = parser.parse_args()

    result = run(args.url)
    payload = {
        "test_id": result.test_id,
        "test_name": result.test_name,
        "accuracy": result.accuracy,
        "passed": result.passed,
        "total": result.total,
        "avg_latency_sec": result.avg_latency_sec,
        "extra": result.extra,
        "details": result.details,
    }
    path = save_json(payload, "t13_ui_response_contract")
    print(result.summary_line())
    print(C.info(f"Saved: {path}"))


if __name__ == "__main__":
    main()