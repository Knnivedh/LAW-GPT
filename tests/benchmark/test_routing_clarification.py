"""
T11 — Routing & Clarification Test Suite
=========================================
Three parts:
    Part A (6 cases) : simple/informational queries → must route to simple_direct
    Part B (5 cases) : complex consultation / case-matrix queries → must trigger clarification (returns Q1)
  Part C (1 loop)  : full 5-turn clarification loop → 5 questions + final answer

Usage:
    python tests/benchmark/test_routing_clarification.py
    python tests/benchmark/test_routing_clarification.py --url https://lawgpt-backend2024.azurewebsites.net
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.benchmark.shared import C, DEFAULT_URL, save_json, call_api

# ─────────────────────────────────────────────────────────────────────────────
# Part A: simple queries — expected route: simple_direct
# Each entry: (id, question, min_words, max_words, required_keywords)
# ─────────────────────────────────────────────────────────────────────────────
SIMPLE_CASES = [
    (
        "RC-S01",
        "What is FIR?",
        60, 450,
        ["first information report", "police", "cognisable"],
    ),
    (
        "RC-S02",
        "What is anticipatory bail in India?",
        60, 450,
        ["anticipatory bail", "438", "arrest"],
    ),
    (
        "RC-S03",
        "Explain fundamental rights under Indian Constitution",
        80, 500,
        ["fundamental rights", "article", "part iii"],
    ),
    (
        "RC-S04",
        "What is IPC section 302?",
        50, 450,
        ["murder", "302", "punishment"],
    ),
    (
        "RC-S05",
        "I want to understand what cognisable offence means",
        # "I want to understand" is a knowledge-seeking phrase — should be simple_direct
        50, 450,
        ["cognisable", "police", "warrant"],
    ),
    (
        "RC-S06",
        "fir kya hota hai",
        # Hindi/romanized — should be simple_direct
        50, 450,
        ["first information", "police"],
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Part B: personal-case queries — expected route: clarification
# First response must be a question (ends with ?)
# ─────────────────────────────────────────────────────────────────────────────
COMPLEX_CASES = [
    (
        "RC-C01",
        "I was fired from my job last week without notice, what can I do?",
    ),
    (
        "RC-C02",
        "My landlord is refusing to return my security deposit, help me",
    ),
    (
        "RC-C03",
        "I got a notice from the court about a cheque bounce case, what should I do?",
        # "got a notice" — tests the article-fix (Bug 1)
    ),
    (
        "RC-C04",
        "I want to file a divorce case, my husband is abusive and harassing me",
        # "I want to file" — personal action, NOT knowledge-seeking, must still clarify
    ),
    (
        "RC-C05",
        """A technology company launches a mobile payment application that allows users to store money, make payments, and access instant micro-loans. During registration: Users must accept a mandatory data-sharing policy allowing the company to collect location data, contact lists, browsing behavior, and financial transaction history. The terms of service include a broad consent clause for sharing data with partner institutions, a clause allowing algorithmic credit scoring without explanation, and a mandatory arbitration clause with seat in another state. Two years later, a major data breach exposes personal and financial data of several users, users begin receiving unsolicited loan offers and phishing attempts, and a cybersecurity researcher discovers that user data was shared with third-party marketing firms. Subsequently, affected users file complaints before the Consumer Commission and a PIL is filed before the High Court. The company argues consent, external hacking, arbitration, and lack of PIL maintainability.""",
        # Long structured case matrix — should trigger clarification, not one-shot direct answer.
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Part C: full 5-turn loop
# ─────────────────────────────────────────────────────────────────────────────
LOOP_QUERY = (
    "I was cheated by an online seller who took payment but never delivered the product"
)
LOOP_ANSWERS = [
    "I ordered a mobile phone worth 15000 rupees on an e-commerce platform",
    "I paid via UPI, the order showed delivered but I never received the product",
    "The seller stopped responding and the platform says they cannot help",
    "I have the payment receipt, chat screenshots, and the delivery proof that says delivered",
    "I want full refund of 15000 rupees and compensation for the mental harassment",
]
LOOP_FINAL_KEYWORDS = ["consumer", "complaint", "protection", "refund", "forum"]
LOOP_FINAL_MIN_WORDS = 250


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _query_type(r: dict) -> str:
    return r.get("system_info", {}).get("query_type", r.get("status", "unknown"))


def _looks_like_question(text: str) -> bool:
    """True if the response text ends with a question mark (possibly in last 50 chars)."""
    return "?" in text[-80:] if text else False


def _kw_hits(answer: str, keywords: list[str]) -> tuple[int, int]:
    ans_lower = answer.lower()
    hits = sum(1 for k in keywords if k.lower() in ans_lower)
    return hits, len(keywords)


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def run(base_url: str) -> dict:
    print("\n" + "=" * 66)
    print("  T11 — Routing & Clarification Test")
    print("  Part A: 6 simple queries  |  Part B: 5 complex  |  Part C: 5-turn loop")
    print("=" * 66)
    print(f"  Target: {base_url}\n")

    results = {"part_a": [], "part_b": [], "part_c": []}
    total_pass = 0
    total_cases = 0

    # ── Part A: Simple routing ────────────────────────────────────────────────
    print("  ── Part A: Simple Routing (expect simple_direct) ──────────────────")
    a_pass = 0
    for case_id, question, min_w, max_w, keywords in SIMPLE_CASES:
        time.sleep(2)
        try:
            r, lat = call_api(question, base_url=base_url, retries=1)
        except Exception as e:
            print(f"  {C.fail(case_id)}  ERROR: {e}")
            results["part_a"].append({"id": case_id, "passed": False, "error": str(e)})
            total_cases += 1
            continue

        qtype   = _query_type(r)
        answer  = r.get("answer", "")
        wc      = len(answer.split())
        kw_h, kw_t = _kw_hits(answer, keywords)

        passed = (
            qtype == "simple_direct"
            and min_w <= wc <= max_w
            and kw_h >= max(1, kw_t // 2)          # at least half keywords present
        )

        badge  = C.ok("PASS") if passed else C.fail("FAIL")
        issues = []
        if qtype != "simple_direct":
            issues.append(f"type={qtype}")
        if not (min_w <= wc <= max_w):
            issues.append(f"words={wc}({min_w}-{max_w})")
        if kw_h < max(1, kw_t // 2):
            issues.append(f"kw={kw_h}/{kw_t}")
        issue_str = "  «" + ", ".join(issues) + "»" if issues else ""

        print(f"  {badge}  {case_id}  type={qtype}  {wc}w  kw={kw_h}/{kw_t}  lat={lat:.1f}s{issue_str}")

        if passed:
            a_pass += 1
        total_pass += int(passed)
        total_cases += 1
        results["part_a"].append({
            "id": case_id, "passed": passed, "query_type": qtype,
            "words": wc, "kw_hits": kw_h, "kw_total": kw_t, "lat": round(lat, 2),
        })

    print(f"\n  Part A result: {a_pass}/{len(SIMPLE_CASES)}\n")

    # ── Part B: Complex routing ───────────────────────────────────────────────
    print("  ── Part B: Complex Routing (expect clarification) ──────────────────")
    b_pass = 0
    for case_id, question in COMPLEX_CASES:
        time.sleep(3)
        try:
            r, lat = call_api(question, base_url=base_url, retries=1)
        except Exception as e:
            print(f"  {C.fail(case_id)}  ERROR: {e}")
            results["part_b"].append({"id": case_id, "passed": False, "error": str(e)})
            total_cases += 1
            continue

        qtype  = _query_type(r)
        answer = r.get("answer", "")
        is_q   = _looks_like_question(answer)

        passed = qtype == "clarification" and is_q

        badge  = C.ok("PASS") if passed else C.fail("FAIL")
        issues = []
        if qtype != "clarification":
            issues.append(f"type={qtype}")
        if not is_q:
            issues.append("answer has no '?'")
        issue_str = "  «" + ", ".join(issues) + "»" if issues else ""
        preview = answer[:80].replace("\n", " ")

        print(f"  {badge}  {case_id}  type={qtype}  lat={lat:.1f}s  '{preview}...'{issue_str}")

        if passed:
            b_pass += 1
        total_pass += int(passed)
        total_cases += 1
        results["part_b"].append({
            "id": case_id, "passed": passed, "query_type": qtype,
            "is_question": is_q, "lat": round(lat, 2), "preview": preview,
        })

    print(f"\n  Part B result: {b_pass}/{len(COMPLEX_CASES)}\n")

    # ── Part C: Full 5-turn loop ──────────────────────────────────────────────
    print("  ── Part C: Full 5-Turn Loop ─────────────────────────────────────────")
    loop_sid   = f"t11_loop_{uuid.uuid4().hex[:8]}"
    loop_pass  = 0
    loop_total = len(LOOP_ANSWERS) + 1   # 5 clarification turns + 1 final
    loop_lats  = []
    c_records  = []

    # Turn 0: initial complex query
    time.sleep(3)
    try:
        r0, lat0 = call_api(LOOP_QUERY, session_id=loop_sid, base_url=base_url, retries=1)
    except Exception as e:
        print(f"  {C.fail('TURN-0')}  ERROR sending initial query: {e}")
        results["part_c"] = [{"turn": 0, "passed": False, "error": str(e)}]
        total_cases += 1
        _print_summary(total_pass, total_cases, a_pass, b_pass, 0, results, base_url)
        return results

    t0_type = _query_type(r0)
    t0_pass = t0_type == "clarification" and _looks_like_question(r0.get("answer", ""))
    loop_lats.append(lat0)
    if t0_pass:
        loop_pass += 1
    badge0 = C.ok("PASS") if t0_pass else C.fail("FAIL")
    print(f"  {badge0}  TURN-0 (initial)  type={t0_type}  lat={lat0:.1f}s  '{r0.get('answer','')[:70]}...'")
    c_records.append({"turn": 0, "passed": t0_pass, "query_type": t0_type, "lat": round(lat0, 2)})

    # Turns 1-4: intermediate answers → expect clarification
    for i, answer_text in enumerate(LOOP_ANSWERS[:-1], start=1):
        time.sleep(3)
        try:
            ri, lati = call_api(answer_text, session_id=loop_sid, base_url=base_url, retries=1)
        except Exception as e:
            print(f"  {C.fail(f'TURN-{i}')}  ERROR: {e}")
            c_records.append({"turn": i, "passed": False, "error": str(e)})
            loop_lats.append(0)
            continue

        ti_type = _query_type(ri)
        ti_pass = ti_type == "clarification" and _looks_like_question(ri.get("answer", ""))
        loop_lats.append(lati)
        if ti_pass:
            loop_pass += 1
        badge_i = C.ok("PASS") if ti_pass else C.fail("FAIL")
        print(f"  {badge_i}  TURN-{i}           type={ti_type}  lat={lati:.1f}s  '{ri.get('answer','')[:70]}...'")
        c_records.append({"turn": i, "passed": ti_pass, "query_type": ti_type, "lat": round(lati, 2)})

    # Turn 5: final answer → expect non-clarification + ≥250 words + keywords
    # Use retries=0 here: a retry on a stub/short answer would hit a NEW session
    # (old one was deleted after synthesis) and wrongly return type=clarification.
    time.sleep(3)
    try:
        rf, latf = call_api(LOOP_ANSWERS[-1], session_id=loop_sid, base_url=base_url, retries=0)
    except Exception as e:
        print(f"  {C.fail('TURN-5 (final)')}  ERROR: {e}")
        c_records.append({"turn": 5, "passed": False, "error": str(e)})
        rf = {}
        latf = 0.0

    tf_type  = _query_type(rf)
    tf_ans   = rf.get("answer", "")
    tf_wc    = len(tf_ans.split())
    kw_h_f, kw_t_f = _kw_hits(tf_ans, LOOP_FINAL_KEYWORDS)
    tf_pass  = (
        tf_type != "clarification"
        and tf_wc >= LOOP_FINAL_MIN_WORDS
        and kw_h_f >= 3
    )
    loop_lats.append(latf)
    if tf_pass:
        loop_pass += 1
    badge_f = C.ok("PASS") if tf_pass else C.fail("FAIL")
    issues_f = []
    if tf_type == "clarification":
        issues_f.append("still in clarification loop")
    if tf_wc < LOOP_FINAL_MIN_WORDS:
        issues_f.append(f"only {tf_wc}w (need {LOOP_FINAL_MIN_WORDS})")
    if kw_h_f < 3:
        issues_f.append(f"kw={kw_h_f}/{kw_t_f}")
    issue_str_f = "  «" + ", ".join(issues_f) + "»" if issues_f else ""
    print(f"  {badge_f}  TURN-5 (final)    type={tf_type}  {tf_wc}w  kw={kw_h_f}/{kw_t_f}  lat={latf:.1f}s{issue_str_f}")

    c_records.append({
        "turn": 5, "passed": tf_pass, "query_type": tf_type,
        "words": tf_wc, "kw_hits": kw_h_f, "lat": round(latf, 2),
    })
    results["part_c"] = c_records

    avg_loop_lat = sum(loop_lats) / max(len(loop_lats), 1)
    print(f"\n  Part C result: {loop_pass}/{loop_total}  avg_lat={avg_loop_lat:.1f}s\n")

    total_pass  += loop_pass
    total_cases += loop_total

    _print_summary(total_pass, total_cases, a_pass, b_pass, loop_pass, results, base_url)
    return results


def _print_summary(total_pass, total_cases, a_pass, b_pass, c_pass, results, base_url):
    pct = 100 * total_pass / max(total_cases, 1)
    suite_pass = total_pass == total_cases
    badge = C.ok("SUITE PASS") if suite_pass else C.fail("SUITE FAIL")

    print("=" * 66)
    print(f"  Part A (simple routing):  {a_pass}/{len(SIMPLE_CASES)}")
    print(f"  Part B (complex routing): {b_pass}/{len(COMPLEX_CASES)}")
    loop_total = len(LOOP_ANSWERS) + 1
    print(f"  Part C (5-turn loop):     {c_pass}/{loop_total}")
    print(f"\n  Total: {total_pass}/{total_cases}  accuracy={pct:.1f}%  {badge}")
    print("=" * 66 + "\n")

    out = {
        "test_id": "T11",
        "base_url": base_url,
        "total_pass": total_pass,
        "total_cases": total_cases,
        "accuracy": round(pct / 100, 4),
        "part_a": results.get("part_a", []),
        "part_b": results.get("part_b", []),
        "part_c": results.get("part_c", []),
    }
    path = save_json(out, "t11_routing_clarification")
    print(f"  Saved: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T11 Routing & Clarification Benchmark")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    args = parser.parse_args()
    run(args.url)
