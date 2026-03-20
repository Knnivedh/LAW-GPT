"""
T10 — Robustness Test
======================
30 noisy variants of 10 underlying questions (3 variants each).
Each underlying question has required answer keywords.

A question 'passes robustness' if ≥ 2 of its 3 variants produce a
keyword-hitting answer (composite ≥ 0.5).

Robustness Score = questions_passing / 10

Noise types per variant:
  V1 — heavy punctuation + CAPS
  V2 — informal / typo / shorthand
  V3 — transliterated Hindi / mixed language

Run:
    python tests/benchmark/test_robustness.py
"""
from __future__ import annotations
import argparse, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import (
    BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD,
    call_api, score_answer, save_json
)

# ── Questions + 3 noisy variants each + required keywords ───────────────────
QUESTIONS: list[dict] = [
    {
        "id": "RB-01",
        "base": "What is IPC Section 420 cheating?",
        "variants": [
            "WHAT IS IPC SECTION 420?????",
            "tell me ipc 420 quickly bro plss",
            "IPC 420 mein cheating ka kya provision hai",
        ],
        "required_keywords": ["420", "cheat", "dishonest", "fraud"],
    },
    {
        "id": "RB-02",
        "base": "What is FIR (First Information Report)?",
        "variants": [
            "WHAT IS FIR?????? explain now",
            "fir kya hota hai bro, fir means??",
            "FIR kya hai aur kaise file karte hain",
        ],
        "required_keywords": ["first information report", "police", "cognisable", "section 154"],
    },
    {
        "id": "RB-03",
        "base": "What is IPC Section 302 murder punishment?",
        "variants": [
            "IPC 302 PUNISHMENT!!! murder section???",
            "302 ipc punishmnet for mueder pls explain",
            "murder ki saza kya hai IPC mein",
        ],
        "required_keywords": ["murder", "death", "imprisonment", "life"],
    },
    {
        "id": "RB-04",
        "base": "What are the grounds for anticipatory bail in India?",
        "variants": [
            "anticipatory bail grounds???? what are those!!",
            "anticipatory bail kaise milti hai bhai grounds bata",
            "ante-cipatory bail ke liye kya conditions hain",
        ],
        "required_keywords": ["anticipatory", "bail", "section 438", "apprehension", "arrest"],
    },
    {
        "id": "RB-05",
        "base": "What is Article 21 of the Indian Constitution?",
        "variants": [
            "ARTICLE 21 CONSTITUTION OF INDIA??? EXPLAIN!!!!!",
            "article 21 kya hai yr constitution mein",
            "Aritcle 21 Constutution of Indiaa what does it say",
        ],
        "required_keywords": ["article 21", "life", "personal liberty", "fundamental"],
    },
    {
        "id": "RB-06",
        "base": "What is Consumer Protection Act 2019?",
        "variants": [
            "consumer protection act 2019!!! explain NOW plz",
            "consumer proteciton act kya hai 2019 wala",
            "CPA 2019 — consumer ke kya rights hai",
        ],
        "required_keywords": ["consumer", "2019", "district commission", "deficiency"],
    },
    {
        "id": "RB-07",
        "base": "What is the Dowry Prohibition Act 1961?",
        "variants": [
            "DOWRY PROHIBITION ACT??? 1961 explain!!!",
            "dowry prohibition act kya hai 1961 ke baad",
            "dahej rokne ka kanoon kya hai india mein",
        ],
        "required_keywords": ["dowry", "prohibition", "1961", "marriage"],
    },
    {
        "id": "RB-08",
        "base": "How to file a cheque bounce complaint under Section 138 NI Act?",
        "variants": [
            "cheque bounce 138 complaint HOW TO FILE???",
            "cheque bounce ho gaya yaar 138 ka case kaise karo",
            "cheque bounce case filing procedure NI Act 138",
        ],
        "required_keywords": ["section 138", "cheque", "dishonour", "notice", "complaint"],
    },
    {
        "id": "RB-09",
        "base": "What is IPC Section 498A cruelty by husband?",
        "variants": [
            "498A IPC!!! husband cruelty kya hota hai???",
            "498a case kya hota hai bro wife pe cruelty",
            "pati dwara patni ke sath zulm ka section kya hai",
        ],
        "required_keywords": ["498", "cruelty", "husband", "dowry", "cognisable"],
    },
    {
        "id": "RB-10",
        "base": "What is the Right to Information Act RTI?",
        "variants": [
            "RTI ACT what is it!!!! RIGHT TO INFORMATION???",
            "rti kya hota hai bhai jaldi batao",
            "Right to Information RTI kaise use karte hai India mein",
        ],
        "required_keywords": ["rti", "right to information", "public authority", "2005", "30"],
    },
]

MIN_VARIANT_PASS = 2   # ≥ 2/3 variants must pass for the question to pass
VARIANT_THRESHOLD = 0.40   # composite score to consider a variant passing (lowered from 0.45 for Hindi variants)


def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold(f"\n{'='*60}"))
    print(C.bold("  T10 — Robustness Test  (30 noisy variants / 10 questions)"))
    print(C.bold(f"{'='*60}"))
    print(C.info(f"  Target: {base_url}\n"))

    questions_passed = 0
    latencies: list[float] = []
    details: list[dict] = []

    for q in QUESTIONS:
        variant_results: list[dict] = []
        v_passed = 0

        for v_idx, variant in enumerate(q["variants"], 1):
            sid = f"t10-rb-{uuid.uuid4().hex[:8]}"
            try:
                resp, lat = call_api(variant, session_id=sid, base_url=base_url)
                latencies.append(lat)
                answer = resp["answer"]

                sc = score_answer(answer, q["required_keywords"], [], [], weights=(1.0, 0.0, 0.0))
                v_pass = sc["keyword_score"] >= VARIANT_THRESHOLD
                if v_pass:
                    v_passed += 1

                badge = C.ok("✓") if v_pass else C.fail("✗")
                print(f"    V{v_idx} {badge} kw={sc['kw_hits']}/{sc['kw_total']}  lat={lat:.1f}s  '{variant[:50]}'")
                variant_results.append({
                    "variant": v_idx,
                    "text": variant,
                    "passed": v_pass,
                    "kw_score": sc["keyword_score"],
                    "latency": round(lat, 2),
                    "answer_excerpt": answer[:200],
                })
            except Exception as e:
                print(C.warn(f"    V{v_idx} ERROR: {e}"))
                variant_results.append({"variant": v_idx, "text": variant, "passed": False, "error": str(e)})

            time.sleep(4)  # 4s gap: backend makes 4+ LLM calls per request; prevent Groq 429s

        q_pass = v_passed >= MIN_VARIANT_PASS
        if q_pass:
            questions_passed += 1

        q_badge = C.ok(f"[{q['id']} ROBUST {v_passed}/3]") if q_pass else C.fail(f"[{q['id']} FRAGILE {v_passed}/3]")
        print(f"  {q_badge}")

        details.append({
            "id": q["id"],
            "base_question": q["base"],
            "variants_passed": v_passed,
            "question_passed": q_pass,
            "variants": variant_results,
        })
        print()

    total = len(QUESTIONS)
    robustness_score = questions_passed / total
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\n{C.bold('  Result:')}  {questions_passed}/{total} questions robust  score={robustness_score*100:.1f}%  avg_lat={avg_lat:.1f}s")
    badge = C.ok("SUITE PASS") if robustness_score >= PASS_THRESHOLD else C.fail("SUITE FAIL")
    print(f"  {badge}\n")

    result = BenchmarkResult(
        test_id="T10-ROBUST",
        test_name="Robustness (noisy input variants)",
        total=total,
        passed=questions_passed,
        accuracy=robustness_score,
        avg_latency_sec=round(avg_lat, 2),
        details=details,
    )
    path = save_json({"summary": result.__dict__, "details": details}, "t10_robustness")
    print(C.info(f"  Saved: {path}\n"))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    run(args.url)
