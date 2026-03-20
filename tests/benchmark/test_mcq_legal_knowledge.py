"""
T2 — Legal Knowledge Accuracy Test (MCQ / MMLU-style)
======================================================
50 multiple-choice questions across 5 categories of Indian law.
Scoring: regex extracts A/B/C/D from response; if not found, section-number
keyword fallback is used.

Accuracy = correct_answers / 50
Run:
    python tests/benchmark/test_mcq_legal_knowledge.py
    python tests/benchmark/test_mcq_legal_knowledge.py --url https://...
"""
from __future__ import annotations
import argparse, re, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import (
    BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD,
    call_api, save_json
)

# ── MCQ Dataset (50 questions) ─────────────────────────────────────────────
# Format: (question_text, options_dict, correct_letter, correct_keyword_fallback)
MCQ: list[tuple] = [
    # ── Criminal Law (IPC / BNS) ─────────────────────────────────────────
    (
        "Under which section of IPC is the punishment for cheating defined?",
        {"A": "302", "B": "420", "C": "376", "D": "124A"},
        "B", "420"
    ),
    (
        "IPC Section 302 deals with:",
        {"A": "Theft", "B": "Cheating", "C": "Murder", "D": "Sedition"},
        "C", "murder"
    ),
    (
        "The minimum punishment for rape under IPC Section 376 is:",
        {"A": "3 years", "B": "5 years", "C": "7 years", "D": "10 years"},
        "C", "seven"
    ),
    (
        "Which IPC section defines 'theft'?",
        {"A": "378", "B": "420", "C": "302", "D": "498A"},
        "A", "378"
    ),
    (
        "IPC Section 498A deals with:",
        {"A": "Kidnapping", "B": "Cruelty by husband or relatives", "C": "Robbery", "D": "Defamation"},
        "B", "498"
    ),
    (
        "Which section of BNS replaces IPC Section 302 (murder)?",
        {"A": "Section 99", "B": "Section 101", "C": "Section 103", "D": "Section 115"},
        "B", "101"
    ),
    (
        "What is the punishment for dacoity under IPC Section 395?",
        {"A": "Up to 3 years", "B": "Up to 7 years", "C": "Up to 10 years", "D": "Life imprisonment or up to 10 years"},
        "D", "ten"
    ),
    (
        "IPC Section 124A (sedition) has been replaced in BNS by which section?",
        {"A": "Section 148", "B": "Section 150", "C": "Section 152", "D": "Section 160"},
        "C", "152"
    ),
    (
        "Under IPC Section 379, what offence is defined?",
        {"A": "Extortion", "B": "Cheating", "C": "Theft (punishment)", "D": "Robbery"},
        "C", "theft"
    ),
    (
        "Culpable homicide not amounting to murder is covered under:",
        {"A": "IPC 299", "B": "IPC 302", "C": "IPC 304", "D": "IPC 307"},
        "C", "304"
    ),
    # ── Constitutional Law ────────────────────────────────────────────────
    (
        "Right to Equality is guaranteed under which Article of the Indian Constitution?",
        {"A": "Article 14", "B": "Article 19", "C": "Article 21", "D": "Article 32"},
        "A", "14"
    ),
    (
        "Article 21 of the Indian Constitution protects:",
        {"A": "Right to Education", "B": "Right to Life and Personal Liberty", "C": "Right to Property", "D": "Right to Vote"},
        "B", "life"
    ),
    (
        "The Right to Constitutional Remedies (writ jurisdiction) is under:",
        {"A": "Article 226", "B": "Article 32", "C": "Article 19", "D": "Article 44"},
        "B", "32"
    ),
    (
        "Which article abolishes untouchability?",
        {"A": "Article 15", "B": "Article 16", "C": "Article 17", "D": "Article 18"},
        "C", "17"
    ),
    (
        "Directive Principles of State Policy are in which Part of the Constitution?",
        {"A": "Part II", "B": "Part III", "C": "Part IV", "D": "Part V"},
        "C", "four"
    ),
    (
        "The Preamble of the Indian Constitution was amended to include 'Socialist' and 'Secular' by which Amendment?",
        {"A": "42nd", "B": "44th", "C": "52nd", "D": "73rd"},
        "A", "42"
    ),
    (
        "Article 370 (special status of J&K) was effectively abrogated in which year?",
        {"A": "2016", "B": "2018", "C": "2019", "D": "2020"},
        "C", "2019"
    ),
    (
        "Freedom of speech and expression is guaranteed under:",
        {"A": "Article 14", "B": "Article 19(1)(a)", "C": "Article 21", "D": "Article 25"},
        "B", "19"
    ),
    (
        "The concept of 'Basic Structure' doctrine was established in:",
        {"A": "Golaknath case", "B": "Kesavananda Bharati case", "C": "Maneka Gandhi case", "D": "Minerva Mills case"},
        "B", "kesavananda"
    ),
    (
        "Which article provides reservation for SCs and STs in public employment?",
        {"A": "Article 15(4)", "B": "Article 16(4)", "C": "Article 17", "D": "Article 46"},
        "B", "16"
    ),
    # ── Consumer Law ─────────────────────────────────────────────────────
    (
        "The Consumer Protection Act 2019 replaced which earlier Act?",
        {"A": "Consumer Act 1980", "B": "Consumer Protection Act 1986", "C": "Sale of Goods Act 1930", "D": "Trade Marks Act 1999"},
        "B", "1986"
    ),
    (
        "Under Consumer Protection Act 2019, the District Commission handles complaints up to:",
        {"A": "Rs 10 lakh", "B": "Rs 50 lakh", "C": "Rs 1 crore", "D": "Rs 2 crore"},
        "C", "crore"
    ),
    (
        "'Deficiency in service' under Consumer Protection Act means:",
        {"A": "Criminal negligence only", "B": "Any fault, imperfection, shortcoming or inadequacy in quality/nature/manner of service", "C": "Only physical product defects", "D": "Financial fraud only"},
        "B", "deficiency"
    ),
    (
        "The National Consumer Disputes Redressal Commission (NCDRC) handles cases above:",
        {"A": "Rs 1 crore", "B": "Rs 5 crore", "C": "Rs 10 crore", "D": "Rs 2 crore"},
        "C", "ten crore"
    ),
    (
        "E-commerce platforms are regulated under which rules under CPA 2019?",
        {"A": "E-Commerce Rules 2020", "B": "Consumer Protection (E-Commerce) Rules 2020", "C": "IT (Intermediary) Rules 2021", "D": "Digital Commerce Act 2020"},
        "B", "e-commerce"
    ),
    # ── Family Law ────────────────────────────────────────────────────────
    (
        "Hindu marriage is governed by which Act?",
        {"A": "Indian Marriage Act 1955", "B": "Hindu Marriage Act 1955", "C": "Special Marriage Act 1954", "D": "Family Courts Act 1984"},
        "B", "hindu marriage"
    ),
    (
        "Under Hindu Succession Act 1956 (amended 2005), daughters have equal coparcenary rights since which year?",
        {"A": "1956", "B": "1986", "C": "2005", "D": "2010"},
        "C", "2005"
    ),
    (
        "The Protection of Women from Domestic Violence Act was enacted in:",
        {"A": "2000", "B": "2003", "C": "2005", "D": "2007"},
        "C", "2005"
    ),
    (
        "Maintenance for wife after divorce (Hindu) is governed by which section of HMA?",
        {"A": "Section 13", "B": "Section 24", "C": "Section 25", "D": "Section 27"},
        "C", "25"
    ),
    (
        "Under Muslim personal law, Triple Talaq was declared unconstitutional in which case?",
        {"A": "Shah Bano case", "B": "Shayara Bano case", "C": "Danial Latifi case", "D": "Sarla Mudgal case"},
        "B", "shayara"
    ),
    # ── Procedural Law (CrPC / BNSS / CPC) ───────────────────────────────
    (
        "FIR stands for:",
        {"A": "Final Investigation Report", "B": "First Information Report", "C": "Formal Inquiry Record", "D": "Filed Investigation Record"},
        "B", "first information"
    ),
    (
        "Under CrPC Section 167, the maximum period of judicial remand for heinous offences is:",
        {"A": "30 days", "B": "60 days", "C": "90 days", "D": "180 days"},
        "C", "90"
    ),
    (
        "Bail in non-bailable offence is granted under CrPC Section:",
        {"A": "436", "B": "437", "C": "438", "D": "439"},
        "B", "437"
    ),
    (
        "Anticipatory bail in India is granted under CrPC Section:",
        {"A": "436", "B": "437", "C": "438", "D": "440"},
        "C", "438"
    ),
    (
        "The Bharatiya Nagarik Suraksha Sanhita (BNSS) replaced:",
        {"A": "IPC", "B": "CrPC", "C": "CPC", "D": "Evidence Act"},
        "B", "crpc"
    ),
    # ── Landmark Cases ─────────────────────────────────────────────────────
    (
        "The Vishaka guidelines on sexual harassment in workplace were laid down in:",
        {"A": "1990", "B": "1995", "C": "1997", "D": "2000"},
        "C", "1997"
    ),
    (
        "The POSH Act (Prevention of Sexual Harassment at Workplace) was enacted in:",
        {"A": "2010", "B": "2012", "C": "2013", "D": "2015"},
        "C", "2013"
    ),
    (
        "Right to Privacy was declared a fundamental right by Supreme Court in which year?",
        {"A": "2015", "B": "2016", "C": "2017", "D": "2018"},
        "C", "2017"
    ),
    (
        "Section 377 IPC (criminalising consensual same-sex acts) was struck down in:",
        {"A": "Naz Foundation case 2009", "B": "Suresh Kumar Koushal case 2013", "C": "Navtej Singh Johar case 2018", "D": "Both A and C"},
        "C", "navtej"
    ),
    (
        "The Maneka Gandhi case expanded the scope of which Article?",
        {"A": "Article 14", "B": "Article 19", "C": "Article 21", "D": "All of the above"},
        "D", "maneka"
    ),
    # ── Property / Contract Law ────────────────────────────────────────────
    (
        "The Transfer of Property Act governs transfers of immovable property in India since:",
        {"A": "1872", "B": "1882", "C": "1900", "D": "1925"},
        "B", "1882"
    ),
    (
        "A sale deed for immovable property must be:",
        {"A": "Written and attested only", "B": "Registered under Registration Act 1908", "C": "Witnessed by a magistrate", "D": "Notarised only"},
        "B", "register"
    ),
    (
        "The Indian Contract Act was enacted in:",
        {"A": "1860", "B": "1872", "C": "1882", "D": "1891"},
        "B", "1872"
    ),
    (
        "A contract with a minor in India is:",
        {"A": "Voidable at the option of minor", "B": "Valid", "C": "Void ab initio", "D": "Enforceable after majority"},
        "C", "void"
    ),
    (
        "RERA (Real Estate Regulatory Authority) was established under which Act?",
        {"A": "Housing Act 2005", "B": "Real Estate (Regulation and Development) Act 2016", "C": "Urban Land Ceiling Act 1976", "D": "Registration Act 1908"},
        "B", "rera"
    ),
    # ── Cyber / IT Law ────────────────────────────────────────────────────
    (
        "The Information Technology Act in India was enacted in:",
        {"A": "1998", "B": "2000", "C": "2002", "D": "2005"},
        "B", "2000"
    ),
    (
        "Section 66A of IT Act (offensive online messages) was struck down by SC in which case?",
        {"A": "Shreya Singhal", "B": "Anuradha Bhasin", "C": "Romesh Thappar", "D": "S Rangarajan"},
        "A", "shreya"
    ),
    (
        "The Digital Personal Data Protection Act (DPDPA) was enacted in:",
        {"A": "2020", "B": "2021", "C": "2023", "D": "2024"},
        "C", "2023"
    ),
    (
        "Cyberstalking in India is covered under:",
        {"A": "IT Act Section 66E", "B": "IT Act Section 67", "C": "IPC Section 354D / BNS Section 78", "D": "IPC Section 500"},
        "C", "354"
    ),
    (
        "The nodal agency for cybercrime in India is:",
        {"A": "CBI", "B": "RAW", "C": "Indian Cyber Crime Coordination Centre (I4C) under MHA", "D": "TRAI"},
        "C", "i4c"
    ),
    (
        "Under PMLA 2002, the Enforcement Directorate investigates:",
        {"A": "Tax evasion", "B": "Money laundering offences", "C": "Cyber fraud", "D": "Corruption"},
        "B", "money laundering"
    ),
]

# ── Letter extractor ----------------------------------------------------------
# Priority order: first-line lone letter → explicit label → reasoning conclusion
_LETTER_RE_LABEL = re.compile(
    r'(?:answer is|correct answer is|option is|answer:|correct:|is\s+option|is\s+letter|the\s+answer\s+is|correct\s+option\s+is)'
    r'\s*[:\-]?\s*\(?\b([A-D])\b\)?',
    re.IGNORECASE
)
_LETTER_RE_CONCLUSION = re.compile(
    r'\b(?:therefore|thus|hence|so),?\s*(?:the\s+)?(?:answer|option|correct)\s+(?:is\s+)?(?:letter\s+)?\(?([A-D])\)?',
    re.IGNORECASE
)

def extract_letter(answer: str) -> str | None:
    """Return the most-likely A/B/C/D letter from model answer.

    Search priority:
    1. First non-empty line that is a lone letter (e.g. "B" or "B.")
    2. Explicit label phrases ("The answer is B", "Correct option: C")
    3. Conclusion phrases ("Therefore the answer is D")
    4. Any standalone A-D letter following a colon, paren, or dash
    """
    # 1. Lone letter on its own line (model started with the letter as instructed)
    for line in answer.strip().splitlines():
        stripped = line.strip().rstrip('.):-').strip()
        if stripped.upper() in ('A', 'B', 'C', 'D'):
            return stripped.upper()

    # 2. Explicit label ("The correct answer is B")
    m = _LETTER_RE_LABEL.search(answer)
    if m:
        return m.group(1).upper()

    # 3. Conclusion phrase
    m = _LETTER_RE_CONCLUSION.search(answer)
    if m:
        return m.group(1).upper()

    # 4. Any letter after colon / paren in early part of answer
    early = answer[:400]
    m2 = re.search(r'[:(\-]\s*\(?([A-D])\b', early, re.IGNORECASE)
    if m2:
        return m2.group(1).upper()

    return None


def option_letter_from_keyword(answer: str, options: dict, fallback_kw: str) -> str | None:
    """Check if the correct answer text OR the fallback keyword appears in the answer."""
    ans_lower = answer.lower()
    if fallback_kw.lower() in ans_lower:
        return "KEYWORD_MATCH"
    return None


# ── Main test -----------------------------------------------------------------
def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold(f"\n{'='*60}"))
    print(C.bold("  T2 — Legal Knowledge Accuracy (MCQ)  50 questions"))
    print(C.bold(f"{'='*60}"))
    print(C.info(f"  Target: {base_url}\n"))

    correct = 0
    latencies: list[float] = []
    details: list[dict] = []

    for idx, (question, options, correct_letter, fallback_kw) in enumerate(MCQ, 1):
        option_text = "  ".join(f"{k}) {v}" for k, v in options.items())
        prompt = (
            f"{question}\n{option_text}\n\n"
            "IMPORTANT: Write ONLY the letter (A, B, C, or D) on the very first line, "
            "then explain your reasoning briefly. Example format:\nB\nExplanation: ..."
        )

        sid = f"t2-mcq-{uuid.uuid4().hex[:8]}"
        try:
            resp, lat = call_api(prompt, session_id=sid, base_url=base_url)
            latencies.append(lat)
            answer = resp["answer"]

            # --- Determine correctness ---
            extracted = extract_letter(answer)
            if extracted == correct_letter:
                passed = True
                method = "letter_match"
            elif extracted is None and fallback_kw.lower() in answer.lower():
                # Correct section/keyword present even if no explicit letter
                passed = True
                method = "keyword_fallback"
            else:
                # Check if the correct option's text is clearly in the answer
                correct_value = options[correct_letter].lower()
                if len(correct_value) > 4 and correct_value in answer.lower():
                    passed = True
                    method = "value_match"
                else:
                    passed = False
                    method = "miss"

            if passed:
                correct += 1
                badge = C.ok("PASS")
            else:
                badge = C.fail("FAIL")

            print(f"  Q{idx:02d} {badge}  lat={lat:.1f}s  got={extracted or '?'}  exp={correct_letter}  [{method}]")
            details.append({
                "q_num": idx,
                "question": question[:80],
                "correct_letter": correct_letter,
                "extracted_letter": extracted,
                "fallback_kw": fallback_kw,
                "method": method,
                "passed": passed,
                "latency": round(lat, 2),
                "answer_excerpt": answer[:200],
            })
        except Exception as e:
            print(C.warn(f"  Q{idx:02d} ERROR: {e}"))
            details.append({"q_num": idx, "passed": False, "error": str(e)})

        time.sleep(3)   # 3s gap to avoid Groq rate-limit on backend

    total = len(MCQ)
    accuracy = correct / total
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\n{C.bold('  Result:')}  {correct}/{total} correct  accuracy={accuracy*100:.1f}%  avg_lat={avg_lat:.1f}s")
    badge = C.ok("SUITE PASS") if accuracy >= PASS_THRESHOLD else C.fail("SUITE FAIL")
    print(f"  {badge}\n")

    result = BenchmarkResult(
        test_id="T2-MCQ",
        test_name="Legal Knowledge Accuracy (MCQ)",
        total=total,
        passed=correct,
        accuracy=accuracy,
        avg_latency_sec=round(avg_lat, 2),
        details=details,
    )
    path = save_json({"summary": result.__dict__, "details": details}, "t2_mcq")
    print(C.info(f"  Saved: {path}\n"))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    run(args.url)
