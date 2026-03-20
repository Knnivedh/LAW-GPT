"""
T7 — Long Document Processing Test
=====================================
10 tests.  Each embeds a real SC judgment excerpt (300-600 chars) into the
prompt and asks the model to summarise / extract verdict / list sections.

Scoring (per test):
  - Key term hits (petitioner name, year, court, holding) — 50%
  - Sections / provisions extracted — 30%
  - Verdict direction correct (upheld / struck down / allowed) — 20%

Composite ≥ 0.55 → PASS

Run:
    python tests/benchmark/test_long_document.py
"""
from __future__ import annotations
import argparse, sys, time, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import (
    BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD,
    call_api, score_answer, save_json
)

# ── Judgment excerpts & tasks ─────────────────────────────────────────────────
TESTS: list[dict] = [
    {
        "id": "LD-01",
        "task": "summarize",
        "excerpt": (
            "In Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225, "
            "a 13-judge bench of the Supreme Court of India held by a 7:6 majority "
            "that Parliament can amend any provision of the Constitution including "
            "Fundamental Rights, but cannot alter its 'basic structure'. "
            "The Court upheld the validiry of the 24th and 25th Constitutional Amendments "
            "in part, striking down only the clause that excluded judicial review of "
            "constitutional amendments. The basic structure doctrine was articulated for "
            "the first time, establishing that supremacy of the Constitution, republican "
            "and democratic form of government, and secularism are inviolable features."
        ),
        "question": "Summarise this Supreme Court judgment excerpt and identify the key legal principle established.",
        "required_keywords": ["kesavananda", "basic structure", "parliament", "amend", "fundamental rights"],
        "expected_sections": ["article 368", "24th amendment", "25th amendment"],
        "ground_truth_facts": ["basic structure", "7:6", "1973", "judicial review"],
        "verdict_kw": ["upheld", "basic structure", "cannot alter"],
    },
    {
        "id": "LD-02",
        "task": "extract_verdict",
        "excerpt": (
            "In Maneka Gandhi v. Union of India AIR 1978 SC 597, the Supreme Court "
            "expanded the interpretation of Article 21 (right to life and personal liberty). "
            "The Court held that the procedure established by law under Article 21 must be "
            "fair, just and reasonable — not arbitrary, fanciful or oppressive. "
            "The passport of the petitioner had been impounded without giving her reasons. "
            "The Court held this violated Articles 14, 19 and 21 read together. "
            "Justice Bhagwati observed that the golden triangle of Articles 14, 19 and 21 "
            "must be read conjunctively."
        ),
        "question": "Extract the verdict and the constitutional principle from this judgment.",
        "required_keywords": ["maneka gandhi", "article 21", "fair", "just", "reasonable", "passport"],
        "expected_sections": ["article 14", "article 19", "article 21"],
        "ground_truth_facts": ["fair just and reasonable", "passport", "1978", "golden triangle"],
        "verdict_kw": ["violated", "fair", "just and reasonable"],
    },
    {
        "id": "LD-03",
        "task": "list_sections",
        "excerpt": (
            "In Vishaka v. State of Rajasthan 1997 (6) SCC 241, the Supreme Court laid down "
            "guidelines to prevent sexual harassment of women at the workplace in the absence "
            "of enacted legislation. The Court invoked Articles 14, 15, 19(1)(g) and 21 of "
            "the Constitution and CEDAW (Convention on Elimination of All Forms of "
            "Discrimination Against Women). The guidelines required every employer to "
            "constitute a Complaints Committee, prohibit sexual harassment and provide a "
            "safe working environment. These guidelines had the force of law until the "
            "POSH Act 2013 was enacted."
        ),
        "question": "List all constitutional provisions and international instruments cited in this judgment excerpt.",
        "required_keywords": ["vishaka", "sexual harassment", "workplace", "guidelines", "complaints committee"],
        "expected_sections": ["article 14", "article 15", "article 19", "article 21", "cedaw"],
        "ground_truth_facts": ["1997", "posh", "2013", "employer"],
        "verdict_kw": ["guidelines", "force of law"],
    },
    {
        "id": "LD-04",
        "task": "summarize",
        "excerpt": (
            "In Navtej Singh Johar v. Union of India (2018) 10 SCC 1, a five-judge "
            "constitutional bench unanimously read down Section 377 of the IPC insofar "
            "as it criminalised consensual sexual acts between adults of the same sex. "
            "The Court held that treating LGBTQ+ persons as criminals violated Articles "
            "14 (equality), 15 (non-discrimination), 19 (expression) and 21 (dignity). "
            "The earlier bench decision in Suresh Kumar Koushal v. Naz Foundation (2013) "
            "was expressly overruled. Chief Justice Misra led the majority."
        ),
        "question": "Summarise this judgment and state which earlier precedent was overruled.",
        "required_keywords": ["navtej", "section 377", "consensual", "lgbtq", "overruled"],
        "expected_sections": ["section 377", "article 14", "article 15", "article 19", "article 21"],
        "ground_truth_facts": ["2018", "koushal", "overruled", "five-judge"],
        "verdict_kw": ["read down", "struck down", "overruled"],
    },
    {
        "id": "LD-05",
        "task": "extract_verdict",
        "excerpt": (
            "In K.S. Puttaswamy v. Union of India (2017) 10 SCC 1, a nine-judge bench "
            "of the Supreme Court unanimously held that privacy is a fundamental right "
            "guaranteed under Article 21 of the Constitution. The judgment overruled "
            "the earlier eight-judge bench decisions in M.P. Sharma (1954) and Kharak Singh "
            "(1964) to the extent they held that there was no fundamental right to privacy. "
            "The bench also held that privacy includes bodily integrity, personal choices, "
            "informational self-determination and dignity."
        ),
        "question": "What is the verdict in this case and which prior decisions were overruled?",
        "required_keywords": ["puttaswamy", "privacy", "fundamental right", "article 21", "nine-judge"],
        "expected_sections": ["article 21"],
        "ground_truth_facts": ["2017", "m.p. sharma", "kharak singh", "overruled", "nine-judge"],
        "verdict_kw": ["fundamental right", "privacy", "overruled"],
    },
    {
        "id": "LD-06",
        "task": "summarize",
        "excerpt": (
            "In Indra Sawhney v. Union of India AIR 1993 SC 477 (Mandal Commission case), "
            "a nine-judge bench upheld the recommendation of 27% reservation for Other "
            "Backward Classes (OBCs) in central government jobs. The Court held that "
            "reservations cannot exceed 50% in total (the '50% ceiling rule'), and "
            "excluded the 'creamy layer' of OBCs from the benefit of reservation. "
            "Economic criterion alone cannot be the basis for reservation. "
            "Articles 16(4) and 16(4A) were analysed extensively."
        ),
        "question": "Summarise the Mandal Commission case and state the key limitations on reservation imposed.",
        "required_keywords": ["mandal", "reservation", "obc", "50%", "creamy layer"],
        "expected_sections": ["article 16", "article 16(4)"],
        "ground_truth_facts": ["27%", "50%", "creamy layer", "1993"],
        "verdict_kw": ["50%", "ceiling", "creamy layer excluded"],
    },
    {
        "id": "LD-07",
        "task": "list_sections",
        "excerpt": (
            "In Shah Bano Begum v. Mohd Ahmed Khan AIR 1985 SC 945, the Supreme Court "
            "held that a Muslim woman was entitled to maintenance from her former husband "
            "beyond the Iddat period under Section 125 CrPC, which is a secular provision "
            "applicable to all. The Court invoked Articles 14 and 15 to emphasise "
            "gender equality. The judgment led to the Muslim Women (Protection of Rights "
            "on Divorce) Act 1986 being enacted, which the Court later interpreted in "
            "Danial Latifi v. Union of India 2001."
        ),
        "question": "List all legal provisions and Acts mentioned in this judgment excerpt.",
        "required_keywords": ["shah bano", "maintenance", "section 125", "iddat", "muslim women"],
        "expected_sections": ["section 125", "crpc", "article 14", "article 15", "1986 act"],
        "ground_truth_facts": ["1985", "iddat", "danial latifi", "1986"],
        "verdict_kw": ["entitled", "maintenance", "secular"],
    },
    {
        "id": "LD-08",
        "task": "extract_verdict",
        "excerpt": (
            "In Shreya Singhal v. Union of India (2015) 5 SCC 1, the Supreme Court "
            "struck down Section 66A of the Information Technology Act 2000 as "
            "unconstitutional, finding it vague, overbroad and violative of Article 19(1)(a) "
            "(freedom of speech and expression). The Court held that restrictions on free "
            "speech must clearly fall within the categories permissible under Article 19(2). "
            "Section 69A (blocking of websites) and Rules 2009 were upheld with guidelines."
        ),
        "question": "What was struck down and what was upheld in this judgment?",
        "required_keywords": ["shreya singhal", "section 66a", "struck down", "article 19", "freedom of speech"],
        "expected_sections": ["section 66a", "it act", "article 19(1)(a)", "article 19(2)", "section 69a"],
        "ground_truth_facts": ["2015", "vague", "overbroad", "section 69a upheld"],
        "verdict_kw": ["struck down", "unconstitutional", "upheld"],
    },
    {
        "id": "LD-09",
        "task": "summarize",
        "excerpt": (
            "In Olga Tellis v. Bombay Municipal Corporation AIR 1986 SC 180, the Supreme "
            "Court upheld the rights of pavement dwellers in Bombay. The Court held that "
            "the right to livelihood is an integral part of the right to life under Article 21. "
            "Eviction of pavement dwellers without notice and without offering alternative "
            "accommodation would violate Article 21. Reasonable notice must be given before "
            "eviction and the State should rehabilitate homeless citizens."
        ),
        "question": "Summarise this case and explain what right was recognised.",
        "required_keywords": ["olga tellis", "livelihood", "article 21", "eviction", "pavement"],
        "expected_sections": ["article 21"],
        "ground_truth_facts": ["1986", "livelihood", "reasonable notice", "rehabilitation"],
        "verdict_kw": ["right to livelihood", "article 21"],
    },
    {
        "id": "LD-10",
        "task": "extract_sections",
        "excerpt": (
            "In Aruna Shanbaug v. Union of India (2011) 4 SCC 454, the Supreme Court "
            "laid down guidelines on passive euthanasia and living wills. The Court held "
            "that the right to die with dignity is part of the right to life under Article 21. "
            "Withdrawal of life support with court permission is lawful. Active euthanasia "
            "remains illegal. The judgment was later affirmed and expanded in Common Cause "
            "v. Union of India (2018) which recognised advance medical directives."
        ),
        "question": "Extract the key legal provisions and principles from this judgment.",
        "required_keywords": ["aruna shanbaug", "euthanasia", "article 21", "dignity", "living will"],
        "expected_sections": ["article 21"],
        "ground_truth_facts": ["2011", "passive euthanasia", "advance directive", "common cause 2018"],
        "verdict_kw": ["right to die with dignity", "lawful", "passive euthanasia"],
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────
def run(base_url: str = DEFAULT_URL) -> BenchmarkResult:
    print(C.bold(f"\n{'='*60}"))
    print(C.bold("  T7 — Long Document Processing  (10 SC judgment excerpts)"))
    print(C.bold(f"{'='*60}"))
    print(C.info(f"  Target: {base_url}\n"))

    passed_count = 0
    latencies: list[float] = []
    details: list[dict] = []

    for t in TESTS:
        prompt = (
            f"Read the following Supreme Court judgment excerpt carefully:\n\n"
            f"{t['excerpt']}\n\n"
            f"Task: {t['question']}"
        )
        sid = f"t7-ld-{uuid.uuid4().hex[:8]}"
        try:
            resp, lat = call_api(prompt, session_id=sid, base_url=base_url)
            latencies.append(lat)
            answer = resp["answer"]

            sc = score_answer(
                answer,
                t["required_keywords"],
                t["expected_sections"],
                t["ground_truth_facts"],
                weights=(0.40, 0.30, 0.30),
            )
            # Bonus: verdict direction check
            verdict_hit = any(v.lower() in answer.lower() for v in t["verdict_kw"])
            # blend verdict bonus into composite
            composite = sc["composite"] * 0.85 + (0.15 if verdict_hit else 0.0)

            passed = composite >= PASS_THRESHOLD
            if passed:
                passed_count += 1

            badge = C.ok("PASS") if passed else C.fail("FAIL")
            print(
                f"  {t['id']}  {badge}  comp={composite:.2f}  "
                f"kw={sc['kw_hits']}/{sc['kw_total']}  "
                f"sec={sc['sec_hits']}/{sc['sec_total']}  "
                f"verdict={'✓' if verdict_hit else '✗'}  lat={lat:.1f}s"
            )
            details.append({
                "id": t["id"],
                "task": t["task"],
                "passed": passed,
                "composite": round(composite, 3),
                "keyword_score": sc["keyword_score"],
                "section_score": sc["section_score"],
                "fact_score": sc["fact_score"],
                "verdict_hit": verdict_hit,
                "latency": round(lat, 2),
                "answer_excerpt": answer[:300],
                "missed_kw": sc["missed_kw"],
                "missed_sec": sc["missed_sec"],
            })
        except Exception as e:
            print(C.warn(f"  {t['id']}  ERROR: {e}"))
            details.append({"id": t["id"], "passed": False, "error": str(e)})

        time.sleep(2)

    total = len(TESTS)
    accuracy = passed_count / total
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"\n{C.bold('  Result:')}  {passed_count}/{total} pass  accuracy={accuracy*100:.1f}%  avg_lat={avg_lat:.1f}s")
    badge = C.ok("SUITE PASS") if accuracy >= PASS_THRESHOLD else C.fail("SUITE FAIL")
    print(f"  {badge}\n")

    result = BenchmarkResult(
        test_id="T7-LONGDOC",
        test_name="Long Document Processing (SC judgments)",
        total=total,
        passed=passed_count,
        accuracy=accuracy,
        avg_latency_sec=round(avg_lat, 2),
        details=details,
    )
    path = save_json({"summary": result.__dict__, "details": details}, "t7_longdoc")
    print(C.info(f"  Saved: {path}\n"))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    run(args.url)
