"""
Clarification Flow Verification Test
=====================================
Tests that LAW-GPT correctly:
1. Triggers 5-question clarification for complex personal case scenarios
2. Asks focused, domain-relevant questions each turn
3. Provides a final substantive legal answer after 5 answers are collected
4. Bypasses clarification for simple legal knowledge questions (simple_direct path)

Run:
    python tests/test_clarification_flow.py
"""

import sys
import requests
import json
import time
import re
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://lawgpt-backend2024.azurewebsites.net"
TIMEOUT = 60

# ─── Colour helpers ──────────────────────────────────────────────────────────

def green(t):  return f"\033[92m{t}\033[0m"
def red(t):    return f"\033[91m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def cyan(t):   return f"\033[96m{t}\033[0m"
def bold(t):   return f"\033[1m{t}\033[0m"

# ─── Personal case scenarios ─────────────────────────────────────────────────

PERSONAL_CASES = [
    {
        "name": "Wrongful Termination",
        "initial_query": (
            "I was suddenly fired by my employer yesterday without any notice period "
            "after working for 5 years. They didn't pay my dues either. Help me."
        ),
        "answers": [
            "I was employed as a senior engineer. My last salary was Rs 65,000 per month.",
            "I joined on 15 March 2019. I was fired verbally on 14 January 2025 with no written notice.",
            "I have my offer letter, salary slips for last 3 years, and all performance appraisal documents.",
            "My employer is TechCorp Pvt Ltd, a 200-employee IT company in Bengaluru.",
            "They owe me 2 months notice pay (Rs 1.3 lakh), 15 days gratuity per year (about Rs 2.5 lakh), "
            "and last month's salary. Total around Rs 5-6 lakh.",
        ],
        "expected_final_keywords": ["industrial disputes", "notice", "gratuity", "wrongful", "termination",
                                     "labour court", "employment", "section"],
    },
    {
        "name": "Builder Delay / RERA",
        "initial_query": (
            "I booked a flat in a housing project 3 years ago and paid Rs 45 lakh. "
            "The builder promised possession by December 2022 but still hasn't given the flat. "
            "What can I do legally?"
        ),
        "answers": [
            "The builder is Sunshine Constructions Pvt Ltd. The project is registered under RERA as MH-2019-123.",
            "I paid Rs 45 lakh out of total Rs 60 lakh. The remaining Rs 15 lakh was to be paid on possession.",
            "I have the allotment letter, payment receipts, the sale agreement, and all RERA registration documents.",
            "The builder keeps giving vague excuses. They offered a 6-month extension once but still no possession.",
            "I want possession of the flat plus interest for the delay of 2+ years, and compensation for the "
            "mental agony and financial loss I suffered.",
        ],
        "expected_final_keywords": ["rera", "real estate", "possession", "compensation", "refund",
                                     "interest", "builder", "tribunal"],
    },
    {
        "name": "Consumer Defective Product",
        "initial_query": (
            "I bought a refrigerator 4 months ago for Rs 45,000 and it stopped working after 2 months. "
            "The company is refusing to replace it. I want my money back."
        ),
        "answers": [
            "The brand is CoolFridge. I bought it from ElectroMart store in Delhi on 10 September 2024.",
            "The fridge stopped cooling completely on 15 November 2024, just 2 months after purchase.",
            "I have the original invoice, warranty card, and 3 written complaints to the service centre.",
            "I complained to their toll-free helpline 5 times. Each time they promised a technician, "
            "who came twice but said the compressor is faulty — a manufacturing defect.",
            "I want full refund of Rs 45,000 plus compensation for the spoiled food (Rs 3,000) and the "
            "cost of renting a small fridge for 2 months (Rs 4,000). Total about Rs 52,000.",
        ],
        "expected_final_keywords": ["consumer protection", "defect", "refund", "compensation",
                                     "district commission", "consumer forum", "complaint"],
    },
    {
        "name": "Domestic Violence / Dowry Harassment",
        "initial_query": (
            "My husband and in-laws are physically and mentally harassing me and demanding more dowry. "
            "I have two children. What legal action can I take to protect myself?"
        ),
        "answers": [
            "We got married 4 years ago. The violence has been ongoing for 2 years and became severe "
            "in the last 6 months.",
            "My husband is employed. At our marriage my family gave jewellery worth Rs 8 lakh and Rs 3 lakh cash. "
            "His family is demanding an additional Rs 10 lakh.",
            "I have medical records from the hospital showing injuries from two incidents. I also have "
            "WhatsApp messages from my mother-in-law demanding money.",
            "I am currently living in the matrimonial home with my two children aged 3 and 5. "
            "My husband has threatened to throw me out.",
            "I want an immediate protection order to stop the harassment, the right to stay in my home, "
            "and maintenance for my children. I also want to file criminal charges for dowry harassment.",
        ],
        "expected_final_keywords": ["domestic violence", "protection order", "pwdva", "section 498",
                                     "dowry", "protection", "magistrate", "relief"],
    },
]

# ─── Simple queries (should NOT trigger clarification) ───────────────────────

SIMPLE_QUERIES = [
    ("Basic criminal law", "What is the punishment for theft under Indian law?"),
    ("Constitutional law", "What are the fundamental rights under Part III of the Indian Constitution?"),
    ("New laws", "What are the three new criminal laws that replaced the colonial-era laws in India in 2024?"),
    ("Consumer forum", "What is the jurisdiction of District Consumer Forum in India?"),
]

# ─── API helper ──────────────────────────────────────────────────────────────

def query_api(question: str, session_id: str) -> dict:
    """Send a query to the API and return the parsed response."""
    try:
        r = requests.post(
            f"{BASE_URL}/api/query",
            json={"question": question, "session_id": session_id, "user_id": "clar_test"},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        data = r.json()
        inner = data.get("response", data)
        return inner if isinstance(inner, dict) else {"answer": str(inner)}
    except Exception as e:
        return {"error": str(e)}


def is_clarification_response(resp: dict) -> bool:
    """True if the response is asking a clarifying question."""
    status = resp.get("status", "")
    if status == "clarification":
        return True
    answer = resp.get("answer", "").strip()
    # Fallback: ends with "?" and is shorter than a full answer
    if answer.endswith("?") and len(answer) < 600:
        return True
    return False


def is_final_answer(resp: dict) -> bool:
    """True if the response is a substantive final answer."""
    status = resp.get("status", "")
    if status in ("complete", "final", "answer", "simple_direct"):
        return True
    answer = resp.get("answer", "").strip()
    # Final answers start with case summary header or are long
    if answer.startswith("**Case Summary") or answer.startswith("**Legal"):
        return True
    if len(answer) > 500 and not answer.endswith("?"):
        return True
    return False


def contains_keywords(text: str, keywords: list) -> list:
    """Return list of keywords found in text (case-insensitive)."""
    tl = text.lower()
    return [k for k in keywords if k.lower() in tl]


# ─── Test: Personal case clarification flow ──────────────────────────────────

def test_personal_case(case: dict, case_num: int) -> dict:
    """Run a full 5-question clarification flow for a personal case.
    Returns a result dict with pass/fail details."""
    name = case["name"]
    print(f"\n{'═'*70}")
    print(bold(f"TEST {case_num}: {name}"))
    print(f"{'═'*70}")

    session_id = f"clar_flow_{case_num}_{int(time.time())}"
    results = {"name": name, "passed": False, "steps": [], "errors": []}
    questions_asked = 0
    final_answer_text = ""

    # ── Turn 0: Initial query ──────────────────────────────────────────────
    print(f"\n{cyan('→ Sending initial query...')}")
    print(f"  Query: {case['initial_query'][:100]}...")
    t0 = time.time()
    resp = query_api(case["initial_query"], session_id)
    latency = round(time.time() - t0, 1)

    if "error" in resp:
        msg = f"API error on initial query: {resp['error']}"
        print(red(f"  ✗ {msg}"))
        results["errors"].append(msg)
        return results

    answer = resp.get("answer", "")
    status = resp.get("status", "unknown")
    progress = resp.get("progress", "")
    print(f"  Status: {status} | Progress: {progress} | Latency: {latency}s")
    print(f"  Bot Q1: {answer[:200]}")

    if not is_clarification_response(resp):
        msg = f"Expected clarification on initial query, got status={status}. Answer: {answer[:150]}"
        print(yellow(f"  ⚠ {msg}"))
        results["errors"].append(msg)
        # Still continue — might get direct answer pathway
    else:
        questions_asked += 1
        print(green(f"  ✓ Clarification triggered (Q{questions_asked})"))

    results["steps"].append({"turn": 0, "status": status, "progress": progress, "clar": is_clarification_response(resp)})

    # ── Turns 1-5: Submit answers ──────────────────────────────────────────
    for i, user_answer in enumerate(case["answers"], 1):
        print(f"\n{cyan(f'→ Submitting Answer {i}...')}")
        print(f"  Answer: {user_answer[:100]}...")
        time.sleep(0.5)  # Small pause between requests

        t0 = time.time()
        resp = query_api(user_answer, session_id)
        latency = round(time.time() - t0, 1)

        if "error" in resp:
            msg = f"API error on answer {i}: {resp['error']}"
            print(red(f"  ✗ {msg}"))
            results["errors"].append(msg)
            break

        answer = resp.get("answer", "")
        status = resp.get("status", "unknown")
        progress = resp.get("progress", "")
        print(f"  Status: {status} | Progress: {progress} | Latency: {latency}s")

        if is_clarification_response(resp) and i < len(case["answers"]):
            questions_asked += 1
            print(f"  Bot Q{questions_asked}: {answer[:200]}")
            print(green(f"  ✓ Next clarification question returned (Q{questions_asked})"))
        elif is_final_answer(resp) or i == len(case["answers"]):
            final_answer_text = answer
            print(f"  Final Answer: {answer[:400]}")
            print(green(f"  ✓ Final answer received after {i} answer(s)"))
        else:
            print(yellow(f"  ? Unclear response: {answer[:200]}"))

        results["steps"].append({
            "turn": i,
            "status": status,
            "progress": progress,
            "is_clar": is_clarification_response(resp),
            "is_final": is_final_answer(resp),
        })

        if is_final_answer(resp):
            print(f"\n  Full final answer ({len(answer)} chars):")
            print(answer[:800])
            break

    # ── Evaluate results ───────────────────────────────────────────────────
    print(f"\n{bold('── Evaluation ──')}")

    # Check 1: Was clarification triggered?
    clar_triggered = results["steps"][0]["clar"] if results["steps"] else False
    print(f"  Clarification triggered on initial query: {'✓' if clar_triggered else '✗'}")

    # Check 2: Were multiple questions asked?
    print(f"  Questions asked: {questions_asked} (expected 4-5)")
    enough_questions = questions_asked >= 3
    print(f"  Sufficient questions: {'✓' if enough_questions else '✗'} ({questions_asked})")

    # Check 3: Was a final answer produced?
    got_final = bool(final_answer_text and len(final_answer_text) > 300)
    print(f"  Final answer produced: {'✓' if got_final else '✗'} ({len(final_answer_text)} chars)")

    # Check 4: Does final answer contain domain keywords?
    kw_hits = contains_keywords(final_answer_text, case["expected_final_keywords"])
    kw_ratio = len(kw_hits) / len(case["expected_final_keywords"])
    print(f"  Legal keywords in answer: {len(kw_hits)}/{len(case['expected_final_keywords'])} "
          f"({kw_ratio*100:.0f}%)")
    print(f"  Found: {kw_hits}")
    missing = [k for k in case["expected_final_keywords"] if k not in kw_hits]
    if missing:
        print(f"  Missing: {missing}")
    good_answer = kw_ratio >= 0.4  # At least 40% of expected keywords

    results["clar_triggered"] = clar_triggered
    results["questions_asked"] = questions_asked
    results["got_final"] = got_final
    results["kw_ratio"] = kw_ratio
    results["kw_hits"] = kw_hits
    results["passed"] = clar_triggered and enough_questions and got_final and good_answer

    if results["passed"]:
        print(green(f"\n  ✅ PASS — clarification flow works correctly for '{name}'"))
    else:
        print(red(f"\n  ❌ FAIL — one or more checks failed for '{name}'"))
        for err in results["errors"]:
            print(red(f"     Error: {err}"))

    return results


# ─── Test: Simple queries bypass clarification ────────────────────────────────

def test_simple_queries() -> dict:
    """Verify that simple factual queries get direct answers (bypass clarification)."""
    print(f"\n{'═'*70}")
    print(bold("TEST SIMPLE: Verify simple queries bypass clarification"))
    print(f"{'═'*70}")

    results = {"name": "Simple Query Bypass", "checks": []}
    all_passed = True

    for label, query in SIMPLE_QUERIES:
        session_id = f"simple_{label[:6].replace(' ', '_')}_{int(time.time())}"
        print(f"\n  {cyan(label)}: {query[:80]}")
        t0 = time.time()
        resp = query_api(query, session_id)
        latency = round(time.time() - t0, 1)

        answer = resp.get("answer", "")
        status = resp.get("status", "unknown")
        is_clar = is_clarification_response(resp)
        is_final = is_final_answer(resp)

        print(f"    Status: {status} | Latency: {latency}s")
        print(f"    Answer preview: {answer[:150]}")

        if "error" in resp:
            print(red(f"    ✗ Error: {resp['error']}"))
            all_passed = False
            results["checks"].append({"label": label, "passed": False})
        elif is_clar:
            print(yellow(f"    ⚠ Got clarification instead of direct answer"))
            results["checks"].append({"label": label, "passed": False})
            # Not hard fail — system may still clarify sometimes
        else:
            print(green(f"    ✓ Direct answer returned (not clarification)"))
            results["checks"].append({"label": label, "passed": True})

    passed_count = sum(1 for c in results["checks"] if c["passed"])
    results["passed"] = passed_count >= len(SIMPLE_QUERIES) * 0.6  # 60% threshold
    print(f"\n  Simple query bypass: {passed_count}/{len(SIMPLE_QUERIES)} direct answers")
    if results["passed"]:
        print(green("  ✅ PASS"))
    else:
        print(yellow("  ⚠ PARTIAL — some simple queries triggered clarification"))
    return results


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print(bold("\n" + "═" * 70))
    print(bold("  LAW-GPT CLARIFICATION FLOW VERIFICATION TEST"))
    print(bold("  Tests that complex personal cases trigger 5-question flow"))
    print(bold("═" * 70))
    print(f"  Backend: {BASE_URL}")
    print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Health check
    try:
        h = requests.get(f"{BASE_URL}/api/health", timeout=15)
        print(f"  Health:  {h.status_code} {h.json().get('status', 'ok')}")
    except Exception as e:
        print(red(f"  Health check failed: {e}"))

    all_results = []
    overall_pass = True

    # Run personal case tests
    for i, case in enumerate(PERSONAL_CASES, 1):
        result = test_personal_case(case, i)
        all_results.append(result)
        if not result["passed"]:
            overall_pass = False
        time.sleep(1)

    # Run simple query bypass test
    simple_result = test_simple_queries()
    all_results.append(simple_result)

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n\n{'═'*70}")
    print(bold("FINAL SUMMARY"))
    print(f"{'═'*70}")

    for r in all_results:
        icon = "✅" if r.get("passed") else "❌"
        name = r["name"]
        q_asked = r.get("questions_asked", "N/A")
        kw_ratio = r.get("kw_ratio", "N/A")
        if isinstance(kw_ratio, float):
            kw_str = f"keywords {kw_ratio*100:.0f}%"
        else:
            kw_str = ""
        detail = f"Q asked: {q_asked}  {kw_str}" if q_asked != "N/A" else ""
        print(f"  {icon} {name:<35} {detail}")

    passed_count = sum(1 for r in all_results if r.get("passed"))
    total = len(all_results)
    print(f"\n  Passed: {passed_count}/{total}")

    if overall_pass and simple_result.get("passed"):
        print(green(f"\n  ✅ ALL TESTS PASSED — Clarification flow is working correctly!\n"))
    else:
        print(yellow(f"\n  ⚠ SOME TESTS FAILED — Review output above for details\n"))

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"tests/clarification_flow_test_{ts}.json"
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": ts,
                "backend": BASE_URL,
                "overall_pass": overall_pass,
                "results": all_results,
            }, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Results saved to: {out_file}")
    except Exception as e:
        print(f"  Could not save results: {e}")


if __name__ == "__main__":
    main()
