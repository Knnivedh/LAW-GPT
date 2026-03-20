"""
T6 — Context Retention Test
============================
20 two-turn conversation chains.  Turn 1 establishes context; Turn 2 is a
follow-up that can only be answered correctly if the bot remembers Turn 1.

Same session_id is reused across both turns so the clarification engine /
memory layer has full context.

Scoring per chain (max 2 points):
  Turn 1 passes (keywords in answer) → 1 pt
  Turn 2 passes (context-dependent keywords in answer) → 1 pt

Context Accuracy = chains where BOTH turns pass / total chains

Run:
    python tests/benchmark/test_context_retention.py
"""
from __future__ import annotations
import argparse, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import (
    BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD,
    call_api, score_answer, save_json
)

# ── Conversation chains ──────────────────────────────────────────────────────
# Each entry: (turn1_question, turn1_required_kw, turn2_question, turn2_required_kw)
CHAINS: list[tuple] = [
    (
        "Explain IPC Section 420 cheating.",
        ["420", "cheatin", "dishonest", "inducement"],
        "What is the maximum sentence for that offence?",
        ["seven year", "imprisonment", "fine"],
    ),
    (
        "What is the Prevention of Money Laundering Act?",
        ["pmla", "money laundering", "enforcement"],
        "Which agency enforces it?",
        ["enforcement directorate", "ed"],
    ),
    (
        "What is IPC Section 302?",
        ["murder", "death", "imprisonment"],
        "What is the equivalent section in the new BNS?",
        ["101", "bns", "bharatiya nyaya"],
    ),
    (
        "Explain the Hindu Marriage Act 1955.",
        ["hindu marriage", "1955", "valid"],
        "What are the grounds for divorce under it?",
        ["adultery", "cruelty", "desertion", "section 13"],
    ),
    (
        "What is the Consumer Protection Act 2019?",
        ["consumer", "2019", "district commission"],
        "What is the pecuniary limit of the District Commission?",
        ["crore", "one crore"],
    ),
    (
        "What is anticipatory bail?",
        ["anticipatory", "bail", "section 438", "apprehension"],
        "Under which code is it granted in the new criminal law?",
        ["bnss", "nagarik suraksha", "bail"],
    ),
    (
        "What is the Right to Information Act?",
        ["rti", "right to information", "public authority", "2005"],
        "Within how many days must a public authority respond?",
        ["30 days", "thirty"],
    ),
    (
        "Explain Section 498A of IPC.",
        ["498a", "cruelty", "husband", "dowry"],
        "Is the offence cognisable and non-bailable?",
        ["cognisable", "non-bailable"],
    ),
    (
        "What is the Vishaka case about?",
        ["vishaka", "sexual harassment", "workplace", "1997"],
        "What legislation followed from those guidelines?",
        ["posh", "prevention of sexual harassment", "2013"],
    ),
    (
        "Explain Article 21 of the Indian Constitution.",
        ["article 21", "life", "personal liberty", "fundamental"],
        "How did the Maneka Gandhi case expand its scope?",
        ["maneka", "procedure established by law", "due process", "fair"],
    ),
    (
        "What is IPC Section 376 about?",
        ["rape", "376", "imprisonment"],
        "What is the minimum sentence for rape?",
        ["seven year", "minimum", "10 year"],
    ),
    (
        "What is the Dowry Prohibition Act?",
        ["dowry", "1961", "prohibition"],
        "What is the maximum penalty for giving or taking dowry?",
        ["five year", "imprisonment", "15000"],
    ),
    (
        "What is the Motor Vehicles Act 1988?",
        ["motor vehicle", "1988", "driving licence", "transport"],
        "What is the penalty for drunk driving under it?",
        ["drunk", "6 month", "10000", "fine"],
    ),
    (
        "Explain the law on cyberstalking in India.",
        ["cyberstalking", "354d", "78", "monitor"],
        "Which Act covers it primarily — IPC or IT Act?",
        ["ipc", "354", "criminal"],
    ),
    (
        "What is RERA and what does it protect?",
        ["rera", "real estate", "buyer", "developer", "2016"],
        "What is the penalty for a developer who delays registration?",
        ["10%", "penalty", "project cost"],
    ),
    (
        "What are the fundamental rights in the Indian Constitution?",
        ["part iii", "article 12", "fundamental right", "enforceable"],
        "Which of those rights can be suspended during a national emergency?",
        ["article 19", "emergency", "suspend", "article 358"],
    ),
    (
        "What is the Negotiable Instruments Act and cheque bounce?",
        ["negotiable instrument", "cheque", "138", "dishonour"],
        "What is the prescribed time limit to file a complaint under Section 138?",
        ["30 day", "15 day", "one month", "30"],
    ),
    (
        "Explain Section 304B of IPC — dowry death.",
        ["dowry death", "304b", "seven year", "presumption"],
        "What is the evidentiary presumption under this section?",
        ["presume", "presumption", "accused", "burden"],
    ),
    (
        "What is the Protection of Children from Sexual Offences (POCSO) Act?",
        ["pocso", "child", "sexual offence", "2012"],
        "What is the minimum age a child is protected under POCSO?",
        ["18", "18 year", "below 18", "minor"],
    ),
    (
        "What is Section 124A IPC (sedition)?",
        ["sedition", "124a", "government", "disaffection"],
        "Has sedition been retained in the new BNS?",
        ["removed", "152", "bns", "sovereignty", "replaced"],
    ),
]

# ── Runner ────────────────────────────────────────────────────────────────────
def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold(f"\n{'='*60}"))
    print(C.bold("  T6 — Context Retention Test  (20 two-turn chains)"))
    print(C.bold(f"{'='*60}"))
    print(C.info(f"  Target: {base_url}\n"))

    chain_passed = 0
    latencies: list[float] = []
    details: list[dict] = []

    for idx, (q1, kw1, q2, kw2) in enumerate(CHAINS, 1):
        sid = f"t6-ctx-{uuid.uuid4().hex[:8]}"

        # ── Turn 1 ────────────────────────────────────────────────────────
        t1_pass = False
        t2_pass = False
        try:
            r1, lat1 = call_api(q1, session_id=sid, base_url=base_url)
            latencies.append(lat1)
            a1 = r1["answer"].lower()
            t1_pass = any(k.lower() in a1 for k in kw1)
            t1_badge = C.ok("T1✓") if t1_pass else C.fail("T1✗")
        except Exception as e:
            t1_badge = C.warn(f"T1-ERR({e})")
            lat1 = 0.0
            a1 = ""

        time.sleep(2)   # short pause before follow-up

        # ── Turn 2 (follow-up — same session) ─────────────────────────────
        try:
            r2, lat2 = call_api(q2, session_id=sid, base_url=base_url)
            latencies.append(lat2)
            a2 = r2["answer"].lower()
            t2_pass = any(k.lower() in a2 for k in kw2)
            t2_badge = C.ok("T2✓") if t2_pass else C.fail("T2✗")
        except Exception as e:
            t2_badge = C.warn(f"T2-ERR({e})")
            lat2 = 0.0
            a2 = ""

        both_pass = t1_pass and t2_pass
        if both_pass:
            chain_passed += 1

        overall_badge = C.ok("CHAIN-PASS") if both_pass else C.fail("CHAIN-FAIL")
        print(f"  Chain {idx:02d}  {t1_badge}  {t2_badge}  {overall_badge}  (lat {lat1:.1f}s+{lat2:.1f}s)")

        details.append({
            "chain": idx,
            "turn1_q": q1,
            "turn1_pass": t1_pass,
            "turn1_lat": round(lat1, 2),
            "turn2_q": q2,
            "turn2_pass": t2_pass,
            "turn2_lat": round(lat2, 2),
            "chain_pass": both_pass,
            "turn1_answer": a1[:200],
            "turn2_answer": a2[:200],
        })

        time.sleep(2)

    total = len(CHAINS)
    accuracy = chain_passed / total
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\n{C.bold('  Result:')}  {chain_passed}/{total} chains fully pass  context_acc={accuracy*100:.1f}%  avg_lat={avg_lat:.1f}s")
    badge = C.ok("SUITE PASS") if accuracy >= PASS_THRESHOLD else C.fail("SUITE FAIL")
    print(f"  {badge}\n")

    result = BenchmarkResult(
        test_id="T6-CTX",
        test_name="Context Retention (2-turn chains)",
        total=total,
        passed=chain_passed,
        accuracy=accuracy,
        avg_latency_sec=round(avg_lat, 2),
        details=details,
    )
    path = save_json({"summary": result.__dict__, "details": details}, "t6_context")
    print(C.info(f"  Saved: {path}\n"))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    run(args.url)
