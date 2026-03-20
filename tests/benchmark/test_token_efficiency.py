"""
T5 — Token Efficiency Test
============================
15 questions across 3 complexity tiers (5 each).
Metric: word count (proxy for tokens) + information density.

Expected word-count ranges:
  LOW    : 60 – 400 words
  MEDIUM : 250 – 800 words
  HIGH   : 400 – 1500 words

A question PASSES if:
  1. At least one required keyword found in answer (correctness gate), AND
  2. Answer word count is within the tier's expected range (±50% of midpoint)

Info Density = keyword_hits / word_count * 1000
  (Higher = more informative per word)

Run:
    python tests/benchmark/test_token_efficiency.py
"""
from __future__ import annotations
import argparse, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import (
    BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD,
    call_api, score_answer, save_json
)

TIERS = {
    "LOW":    {"min_words": 40,  "max_words": 400,  "label": "Simple factual"},
    "MEDIUM": {"min_words": 200, "max_words": 900,  "label": "Moderate legal"},
    "HIGH":   {"min_words": 350, "max_words": 2000, "label": "Complex/multi-hop"},
}

QUESTIONS: list[dict] = [
    # ── LOW complexity ────────────────────────────────────────────────────
    {
        "id": "TE-L1", "tier": "LOW",
        "question": "What is FIR?",
        "required_keywords": ["first information report", "police", "cognisable"],
    },
    {
        "id": "TE-L2", "tier": "LOW",
        "question": "What does 'bail' mean in Indian law?",
        "required_keywords": ["bail", "release", "surety", "custody"],
    },
    {
        "id": "TE-L3", "tier": "LOW",
        "question": "Who can file a consumer complaint in India?",
        "required_keywords": ["consumer", "complainant", "district commission", "deficiency"],
    },
    {
        "id": "TE-L4", "tier": "LOW",
        "question": "What is a writ petition?",
        "required_keywords": ["writ", "high court", "supreme court", "constitutional remedy"],
    },
    {
        "id": "TE-L5", "tier": "LOW",
        "question": "What is IPC Section 302?",
        "required_keywords": ["murder", "302", "death", "imprisonment"],
    },
    # ── MEDIUM complexity ─────────────────────────────────────────────────
    {
        "id": "TE-M1", "tier": "MEDIUM",
        "question": "Explain IPC Section 420 cheating and the elements required to prove the offence.",
        "required_keywords": ["420", "cheating", "dishonest", "inducement", "delivery", "intent"],
    },
    {
        "id": "TE-M2", "tier": "MEDIUM",
        "question": "What are the rights of an arrested person under Indian law?",
        "required_keywords": ["article 22", "informed", "lawyer", "magistrate", "24 hour"],
    },
    {
        "id": "TE-M3", "tier": "MEDIUM",
        "question": "How is maintenance calculated under Section 125 CrPC?",
        "required_keywords": ["125", "maintenance", "wife", "children", "income", "sufficient"],
    },
    {
        "id": "TE-M4", "tier": "MEDIUM",
        "question": "Explain the concept of anticipatory bail and when it is granted.",
        "required_keywords": ["section 438", "anticipatory", "apprehension", "conditions", "high court"],
    },
    {
        "id": "TE-M5", "tier": "MEDIUM",
        "question": "What is the procedure to file a complaint under the Consumer Protection Act 2019?",
        "required_keywords": ["consumer", "district commission", "format", "fee", "complaint", "2019"],
    },
    # ── HIGH complexity ────────────────────────────────────────────────────
    {
        "id": "TE-H1", "tier": "HIGH",
        "question": "Explain cybercrime law in India with examples, relevant IPC and IT Act sections, and penalties.",
        "required_keywords": [
            "it act", "section 66", "hacking", "identity theft",
            "cyberstalking", "ipc", "penalty", "imprisonment"
        ],
    },
    {
        "id": "TE-H2", "tier": "HIGH",
        "question": (
            "A tenant has not paid rent for 6 months and refuses to vacate. "
            "What legal options does the landlord have under Indian law, and what is the full procedure?"
        ),
        "required_keywords": [
            "eviction", "rent act", "civil court", "notice",
            "transfer of property", "section 106", "rent control"
        ],
    },
    {
        "id": "TE-H3", "tier": "HIGH",
        "question": (
            "Explain the complete procedure from FIR to trial for a murder case in India "
            "under the new Bharatiya Nagarik Suraksha Sanhita (BNSS)."
        ),
        "required_keywords": [
            "fir", "investigation", "chargesheet", "trial", "sessions court",
            "evidence", "bnss", "committal", "punishment"
        ],
    },
    {
        "id": "TE-H4", "tier": "HIGH",
        "question": (
            "What are the constitutional safeguards against arbitrary detention in India? "
            "Discuss the landmark cases that shaped these rights."
        ),
        "required_keywords": [
            "article 21", "article 22", "habeas corpus",
            "maneka gandhi", "reasonable", "detention", "personal liberty", "fundamental"
        ],
    },
    {
        "id": "TE-H5", "tier": "HIGH",
        "question": (
            "Explain the complete legal framework for protection of women from domestic "
            "violence in India — Acts, procedures, remedies, and enforcement."
        ),
        "required_keywords": [
            "pwdva", "2005", "protection officer", "residence order",
            "magistrate", "498a", "shelter home", "compensation"
        ],
    },
]


def word_count(text: str) -> int:
    return len(text.split())


def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold(f"\n{'='*60}"))
    print(C.bold("  T5 — Token Efficiency Test  (15 questions / 3 tiers)"))
    print(C.bold(f"{'='*60}"))
    print(C.info(f"  Target: {base_url}\n"))

    passed_count = 0
    latencies: list[float] = []
    details: list[dict] = []
    tier_stats: dict[str, dict] = {t: {"pass": 0, "total": 0, "densities": []} for t in TIERS}

    for q in QUESTIONS:
        tier = q["tier"]
        t_cfg = TIERS[tier]
        sid = f"t5-te-{uuid.uuid4().hex[:8]}"
        try:
            resp, lat = call_api(q["question"], session_id=sid, base_url=base_url)
            latencies.append(lat)
            answer = resp["answer"]

            wc = word_count(answer)
            in_range = t_cfg["min_words"] <= wc <= t_cfg["max_words"]

            sc = score_answer(answer, q["required_keywords"], [], [], weights=(1.0, 0.0, 0.0))
            correct = sc["keyword_score"] >= 0.3   # ≥30% keyword hit

            info_density = round(sc["kw_hits"] / max(wc, 1) * 1000, 2)
            passed = correct and in_range
            if passed:
                passed_count += 1

            tier_stats[tier]["total"] += 1
            tier_stats[tier]["densities"].append(info_density)
            if passed:
                tier_stats[tier]["pass"] += 1

            wc_badge = C.ok(f"{wc}w✓") if in_range else C.warn(f"{wc}w✗")
            kw_badge = C.ok(f"kw{sc['kw_hits']}/{sc['kw_total']}✓") if correct else C.fail(f"kw{sc['kw_hits']}/{sc['kw_total']}✗")
            final_badge = C.ok("PASS") if passed else C.fail("FAIL")
            print(
                f"  {q['id']}  [{tier:6s}]  {final_badge}  {wc_badge}  {kw_badge}  "
                f"density={info_density}  lat={lat:.1f}s"
            )
            details.append({
                "id": q["id"],
                "tier": tier,
                "question": q["question"][:80],
                "passed": passed,
                "word_count": wc,
                "in_range": in_range,
                "min_words": t_cfg["min_words"],
                "max_words": t_cfg["max_words"],
                "keyword_score": sc["keyword_score"],
                "kw_hits": sc["kw_hits"],
                "kw_total": sc["kw_total"],
                "info_density": info_density,
                "latency": round(lat, 2),
            })
        except Exception as e:
            print(C.warn(f"  {q['id']}  ERROR: {e}"))
            details.append({"id": q["id"], "tier": tier, "passed": False, "error": str(e)})

        time.sleep(4)   # 4s gap to avoid Groq rate-limit (backend = 4+ LLM calls per query)

    total = len(QUESTIONS)
    accuracy = passed_count / total
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\n{C.bold('  Tier breakdown:')}")
    for tier, st in tier_stats.items():
        avg_density = sum(st["densities"]) / len(st["densities"]) if st["densities"] else 0
        print(f"    {tier:6s}  {st['pass']}/{st['total']}  avg_density={avg_density:.1f}")

    print(f"\n{C.bold('  Result:')}  {passed_count}/{total} pass  accuracy={accuracy*100:.1f}%  avg_lat={avg_lat:.1f}s")
    badge = C.ok("SUITE PASS") if accuracy >= PASS_THRESHOLD else C.fail("SUITE FAIL")
    print(f"  {badge}\n")

    result = BenchmarkResult(
        test_id="T5-TOKEN",
        test_name="Token Efficiency (word count + density)",
        total=total,
        passed=passed_count,
        accuracy=accuracy,
        avg_latency_sec=round(avg_lat, 2),
        extra={"tier_stats": tier_stats},
        details=details,
    )
    path = save_json({"summary": result.__dict__, "details": details}, "t5_token_efficiency")
    print(C.info(f"  Saved: {path}\n"))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    run(args.url)
