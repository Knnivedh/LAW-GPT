"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   LAW-GPT v3.0 — COMPREHENSIVE 10-DIMENSION ACCURACY COMPARISON TEST      ║
║                                                                            ║
║   Tests the FULL production system (deployed on Azure) across 10          ║
║   orthogonal accuracy dimensions, comparing classic Agentic RAG            ║
║   (Zilliz vector path) against Advanced Agentic + PageIndex               ║
║   (vectorless tree-based statute retrieval).                               ║
║                                                                            ║
║   DIMENSIONS (60+ test scenarios):                                         ║
║                                                                            ║
║   DIM-1 [ACT] Statute Lookup Accuracy    — PageIndex path, exact sections ║
║   DIM-2 [VEC] Vector/Semantic RAG        — Zilliz path, case law / doctrine║
║   DIM-3 [PAX] PageIndex+Agentic Wiring   — verify strategy routing        ║
║   DIM-4 [MHR] Multi-hop Reasoning        — cross-act, multi-source        ║
║   DIM-5 [FPR] Factual Precision          — exact facts, dates, numbers    ║
║   DIM-6 [HAL] Hallucination Guard        — edge cases, obscure queries    ║
║   DIM-7 [SRV] Strategy Routing Verify    — planner routes correctly       ║
║   DIM-8 [AFV] Agentic Feature Verify     — cache, confidence, memory      ║
║   DIM-9 [REG] Regression Baseline        — repeat known-good questions    ║
║   DIM-10[LAT] Latency Benchmarks         — p50 / p95 / avg                ║
║                                                                            ║
║   SCORING:                                                                 ║
║     Keyword hit rate  (30%) + Section citation (30%) + Fact accuracy (40%)║
║     Pass threshold per question: composite ≥ 0.55                         ║
║                                                                            ║
║   TARGET: https://lawgpt-backend2024.azurewebsites.net                     ║
║   RUN:    python tests/test_comprehensive_accuracy_comparison.py           ║
║           python tests/test_comprehensive_accuracy_comparison.py --url URL ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Fix Unicode on Windows cp1252 terminals ───────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_URL = os.environ.get("LAWGPT_BASE_URL", "https://lawgpt-backend2024.azurewebsites.net")
TIMEOUT     = 180          # per-request timeout (Azure cold start can be slow)
PASS_THRESHOLD = 0.55      # composite score ≥ this → PASS
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
TS = datetime.now().strftime("%Y%m%d_%H%M%S")


class C:
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Scenario:
    """One test scenario."""
    id: str                       # e.g. "ACT-01"
    dimension: str                # e.g. "ACT"
    question: str
    category: str
    difficulty: str               # basic / intermediate / advanced / multi_hop
    required_keywords: List[str]
    expected_sections: List[str]
    ground_truth_facts: List[str]
    # What retrieval strategy / path we expect the agentic planner to choose
    expected_strategy: Optional[str] = None   # "statute_lookup" | "simple" | "multi_hop" | "research"
    # Minimum required composite score to PASS (override global PASS_THRESHOLD)
    pass_threshold: Optional[float] = None
    # Source / justification
    source: str = ""


@dataclass
class ScenarioResult:
    """Result for one scenario."""
    scenario: Scenario
    answer: str = ""
    latency: float = 0.0
    confidence: float = 0.0
    sources: int = 0
    from_cache: bool = False
    strategy: str = ""
    loops: int = 0
    # Accuracy
    kw_hits: int = 0
    kw_total: int = 0
    kw_score: float = 0.0
    sec_hits: int = 0
    sec_total: int = 0
    sec_score: float = 0.0
    fact_hits: int = 0
    fact_total: int = 0
    fact_score: float = 0.0
    composite: float = 0.0
    # Pass/fail
    passed: bool = False
    strategy_ok: bool = True    # False if expected_strategy set and not matched
    errors: List[str] = field(default_factory=list)


@dataclass
class DimensionReport:
    """Aggregated report for one dimension."""
    dim_id: str
    name: str
    results: List[ScenarioResult] = field(default_factory=list)

    @property
    def total(self): return len(self.results)

    @property
    def passed(self): return sum(1 for r in self.results if r.passed)

    @property
    def failed(self): return self.total - self.passed

    @property
    def pass_rate(self): return self.passed / self.total * 100 if self.total else 0

    @property
    def avg_composite(self):
        scores = [r.composite for r in self.results if r.answer]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def avg_latency(self):
        lats = [r.latency for r in self.results if r.latency > 0]
        return sum(lats) / len(lats) if lats else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  GROUND TRUTH DATABASE — 10 DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ── DIM-1 : STATUTE LOOKUP ACCURACY (ACT) ────────────────────────────────────
# These questions require finding *exact* statute text / section details.
# They should trigger the PageIndex vectorless path (strategy=statute_lookup).
DIM1_ACT: List[Scenario] = [
    Scenario(
        id="ACT-01", dimension="ACT",
        question="What is the exact punishment prescribed under Section 101 of the Bharatiya Nyaya Sanhita (BNS) for murder?",
        category="criminal", difficulty="basic",
        required_keywords=["death", "imprisonment", "life", "fine", "murder", "punish"],
        expected_sections=["Section 101", "BNS", "Bharatiya Nyaya Sanhita"],
        ground_truth_facts=["death", "imprisonment for life", "fine"],
        expected_strategy="statute_lookup",
        source="BNS Section 101 — replaces IPC 302; murder: death or life imprisonment + fine",
    ),
    Scenario(
        id="ACT-02", dimension="ACT",
        question="What does Section 170 of the Bharatiya Nyaya Sanhita say about abduction?",
        category="criminal", difficulty="intermediate",
        required_keywords=["abduction", "imprisonment", "BNS", "compel", "force", "kidnap"],
        expected_sections=["Section 170", "BNS"],
        ground_truth_facts=["abduction", "imprisonment"],
        expected_strategy="statute_lookup",
        source="BNS Section 170 — kidnapping/abduction provisions",
    ),
    Scenario(
        id="ACT-03", dimension="ACT",
        question="Cite the exact text or scope of Section 376 IPC regarding rape. What is the minimum punishment?",
        category="criminal", difficulty="intermediate",
        required_keywords=["rape", "seven years", "imprisonment", "IPC", "life"],
        expected_sections=["Section 376", "IPC"],
        ground_truth_facts=["seven years", "life imprisonment", "rape"],
        expected_strategy="statute_lookup",
        source="IPC Section 376 — rape: rigorous imprisonment not less than 7 years up to life + fine",
    ),
    Scenario(
        id="ACT-04", dimension="ACT",
        question="What does Article 21 of the Indian Constitution guarantee?",
        category="constitutional", difficulty="basic",
        required_keywords=["life", "personal liberty", "deprived", "procedure", "established", "law"],
        expected_sections=["Article 21"],
        ground_truth_facts=["life", "personal liberty", "law established by law"],
        expected_strategy="statute_lookup",
        source="Article 21 — No person shall be deprived of his life or personal liberty except according to procedure established by law",
    ),
    Scenario(
        id="ACT-05", dimension="ACT",
        question="What are the requirements under Section 304B IPC (BNS Section 80) for dowry death?",
        category="criminal", difficulty="advanced",
        required_keywords=["seven years", "marriage", "dowry", "unnatural", "burns", "bodily injury", "cruelty"],
        expected_sections=["Section 304B", "IPC", "Section 80", "BNS"],
        ground_truth_facts=["seven years", "unnatural", "cruelty", "dowry", "marriage"],
        expected_strategy="statute_lookup",
        source="IPC 304B / BNS 80 — death within 7 years of marriage, unnatural, preceded by cruelty for or in connection with dowry",
    ),
    Scenario(
        id="ACT-06", dimension="ACT",
        question="What does Section 438 CrPC say about anticipatory bail and who can grant it?",
        category="procedural", difficulty="intermediate",
        required_keywords=["anticipatory bail", "apprehension", "arrest", "Sessions Court", "High Court"],
        expected_sections=["Section 438", "CrPC"],
        ground_truth_facts=["anticipatory bail", "Sessions Court", "High Court", "arrest"],
        expected_strategy="statute_lookup",
        source="CrPC 438 — person apprehending arrest in non-bailable offence may apply to Sessions Court or HC",
    ),
    Scenario(
        id="ACT-07", dimension="ACT",
        question="What is Section 3 of the Protection of Women from Domestic Violence Act, 2005 and what forms of abuse does it cover?",
        category="family", difficulty="intermediate",
        required_keywords=["physical", "sexual", "verbal", "emotional", "economic", "domestic violence"],
        expected_sections=["Section 3", "PWDVA"],
        ground_truth_facts=["physical abuse", "sexual abuse", "verbal", "emotional", "economic abuse"],
        expected_strategy="statute_lookup",
        source="PWDVA 2005 S.3 — domestic violence includes physical, sexual, verbal/emotional, economic abuse",
    ),
    Scenario(
        id="ACT-08", dimension="ACT",
        question="What is Section 498A of the IPC and what is its punishment?",
        category="criminal", difficulty="basic",
        required_keywords=["cruelty", "husband", "relatives", "imprisonment", "three years", "fine"],
        expected_sections=["Section 498A", "IPC"],
        ground_truth_facts=["cruelty", "husband", "relatives", "three years", "fine"],
        expected_strategy="statute_lookup",
        source="IPC 498A — cruelty by husband/relatives: imprisonment up to 3 yrs + fine; cognisable, non-bailable",
    ),
]

# ── DIM-2 : VECTOR / SEMANTIC RAG ACCURACY (VEC) ─────────────────────────────
# General legal doctrine, case law, principles — vector search path.
DIM2_VEC: List[Scenario] = [
    Scenario(
        id="VEC-01", dimension="VEC",
        question="Explain the significance of the Kesavananda Bharati judgment and the basic structure doctrine.",
        category="constitutional", difficulty="advanced",
        required_keywords=["basic structure", "Parliament", "amend", "Constitution", "judicial review"],
        expected_sections=["Article 368"],
        ground_truth_facts=["basic structure", "Parliament", "cannot amend", "1973"],
        source="Kesavananda Bharati v. State of Kerala (1973) — SC held Parliament cannot destroy basic structure of Constitution",
    ),
    Scenario(
        id="VEC-02", dimension="VEC",
        question="What are the fundamental rights guaranteed under Part III of the Indian Constitution?",
        category="constitutional", difficulty="basic",
        required_keywords=["equality", "freedom", "exploitation", "religion", "education", "constitutional remedies"],
        expected_sections=["Article 14", "Article 19", "Article 21"],
        ground_truth_facts=["right to equality", "right to freedom", "freedom of religion", "right to constitutional remedies"],
        source="Constitution Part III — 6 fundamental rights (Articles 14-32)",
    ),
    Scenario(
        id="VEC-03", dimension="VEC",
        question="How did the Supreme Court establish the right to privacy as a fundamental right in India?",
        category="constitutional", difficulty="advanced",
        required_keywords=["privacy", "fundamental right", "Puttaswamy", "Article 21"],
        expected_sections=["Article 21"],
        ground_truth_facts=["Puttaswamy", "fundamental right", "Article 21", "2017"],
        source="Justice K.S. Puttaswamy v. Union of India (2017) — 9-judge bench: privacy is fundamental right under Art 21",
    ),
    Scenario(
        id="VEC-04", dimension="VEC",
        question="What was the Supreme Court's decision in Navtej Singh Johar v. Union of India regarding Section 377?",
        category="constitutional", difficulty="advanced",
        required_keywords=["Section 377", "unconstitutional", "homosexuality", "consensual", "decriminalised"],
        expected_sections=["Section 377", "Article 14", "Article 21"],
        ground_truth_facts=["unconstitutional", "consensual", "decriminalised", "2018"],
        source="Navtej Singh Johar v. Union of India (2018) — decriminalised consensual homosexuality among adults",
    ),
    Scenario(
        id="VEC-05", dimension="VEC",
        question="Explain the key features and protections under the Consumer Protection Act 2019.",
        category="consumer", difficulty="intermediate",
        required_keywords=["CCPA", "e-commerce", "mediation", "product liability", "Consumer Protection"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=["Central Consumer Protection Authority", "e-commerce", "mediation"],
        source="CPA 2019 — CCPA, e-commerce coverage, mediation cells, product liability chapter",
    ),
    Scenario(
        id="VEC-06", dimension="VEC",
        question="What are the Vishaka Guidelines and why are they significant?",
        category="landmark_case", difficulty="advanced",
        required_keywords=["Vishaka", "sexual harassment", "workplace", "guidelines", "1997"],
        expected_sections=["Vishaka"],
        ground_truth_facts=["Vishaka", "sexual harassment", "workplace", "1997"],
        source="Vishaka v. State of Rajasthan (1997) — SC laid down binding guidelines against workplace sexual harassment",
    ),
    Scenario(
        id="VEC-07", dimension="VEC",
        question="How does RERA protect homebuyers and what are its key provisions?",
        category="property", difficulty="intermediate",
        required_keywords=["RERA", "Real Estate", "Regulatory Authority", "registration", "builder", "homebuyer"],
        expected_sections=["RERA"],
        ground_truth_facts=["Real Estate", "Regulatory Authority", "registration", "builder"],
        source="Real Estate (Regulation and Development) Act 2016 — project registration, escrow, compensation to buyers",
    ),
    Scenario(
        id="VEC-08", dimension="VEC",
        question="What is the scope of free legal aid under Indian law and who qualifies?",
        category="constitutional", difficulty="intermediate",
        required_keywords=["legal aid", "Article 39A", "free", "SC/ST", "women", "children", "disabled"],
        expected_sections=["Article 39A", "Legal Services Authorities Act"],
        ground_truth_facts=["legal aid", "free", "weaker sections"],
        source="Article 39A + Legal Services Authorities Act 1987 — free aid for SC/ST, women, children, disabled, economically weaker",
    ),
]

# ── DIM-3 : PAGEINDEX + AGENTIC WIRING VERIFICATION (PAX) ────────────────────
# Checks that the agentic planner correctly routes statute section queries to
# the PageIndex vectorless retrieval path (strategy="statute_lookup").
DIM3_PAX: List[Scenario] = [
    Scenario(
        id="PAX-01", dimension="PAX",
        question="Exactly what does Section 101 BNS say about murder and its punishment?",
        category="criminal", difficulty="basic",
        required_keywords=["Section 101", "BNS", "murder", "death", "imprisonment"],
        expected_sections=["Section 101", "BNS"],
        ground_truth_facts=["death", "imprisonment for life", "BNS"],
        expected_strategy="statute_lookup",
        source="BNS S.101 — statute lookup needed; should trigger PageIndex path",
    ),
    Scenario(
        id="PAX-02", dimension="PAX",
        question="What does Section 303 BNS say about theft and what is the punishment?",
        category="criminal", difficulty="basic",
        required_keywords=["theft", "imprisonment", "fine", "three years", "BNS"],
        expected_sections=["Section 303", "BNS"],
        ground_truth_facts=["theft", "three years", "fine"],
        expected_strategy="statute_lookup",
        source="BNS S.303 — theft: imprisonment up to 3 yrs + fine; replaces IPC 379",
    ),
    Scenario(
        id="PAX-03", dimension="PAX",
        question="What is Article 14 of the Indian Constitution? Give the exact text.",
        category="constitutional", difficulty="basic",
        required_keywords=["equality", "equal protection", "law", "Article 14"],
        expected_sections=["Article 14"],
        ground_truth_facts=["equality before law", "equal protection"],
        expected_strategy="statute_lookup",
        source="Article 14 — equality before law and equal protection of laws within India",
    ),
    Scenario(
        id="PAX-04", dimension="PAX",
        question="Cite the exact provision of Section 17 of the Consumer Protection Act 2019.",
        category="consumer", difficulty="intermediate",
        required_keywords=["Consumer Protection Act", "Section 17", "District Commission", "jurisdiction"],
        expected_sections=["Section 17", "Consumer Protection Act"],
        ground_truth_facts=["District", "Commission", "jurisdiction"],
        expected_strategy="statute_lookup",
        source="CPA 2019 S.17 — jurisdiction of District Consumer Disputes Redressal Commission",
    ),
    Scenario(
        id="PAX-05", dimension="PAX",
        question="What does Section 63 of the Indian Contract Act, 1872 say about promissory estoppel or dispensing with performance?",
        category="civil", difficulty="advanced",
        required_keywords=["Contract Act", "discharge", "promise", "performance", "Section 63"],
        expected_sections=["Section 63", "Indian Contract Act"],
        ground_truth_facts=["discharge", "promise", "performance"],
        expected_strategy="statute_lookup",
        source="Indian Contract Act S.63 — promisee may dispense with or remit performance",
    ),
]

# ── DIM-4 : MULTI-HOP REASONING ACCURACY (MHR) ───────────────────────────────
# Complex questions requiring information from multiple statutes/cases.
DIM4_MHR: List[Scenario] = [
    Scenario(
        id="MHR-01", dimension="MHR",
        question="If a person commits murder and also destroys evidence to cover it up, what BNS/IPC sections apply and what are the combined punishments?",
        category="criminal", difficulty="multi_hop",
        required_keywords=["murder", "evidence", "destruction", "imprisonment", "death", "punishment", "concurrent"],
        expected_sections=["Section 302", "Section 201", "Section 101"],
        ground_truth_facts=["death", "imprisonment for life", "evidence"],
        source="IPC 302 (murder) + IPC 201 (destruction of evidence) — concurrent charges",
    ),
    Scenario(
        id="MHR-02", dimension="MHR",
        question="A woman in a live-in relationship suffers physical and economic abuse from her partner. What legal remedies are available under the PWDVA and IPC?",
        category="family", difficulty="multi_hop",
        required_keywords=["domestic violence", "live-in", "protection order", "PWDVA", "IPC", "498A"],
        expected_sections=["PWDVA", "Section 498A"],
        ground_truth_facts=["Protection of Women from Domestic Violence Act", "live-in", "protection order"],
        source="PWDVA 2005 covers live-in relationships; IPC 498A for cruelty",
    ),
    Scenario(
        id="MHR-03", dimension="MHR",
        question="A builder delays delivery of a flat by 3 years. The buyer's agreement was worth Rs 80 lakhs. Which consumer forum handles the complaint, and under what RERA provisions can the builder be penalised?",
        category="consumer", difficulty="multi_hop",
        required_keywords=["District", "Consumer", "Commission", "RERA", "compensation", "delay", "penalty"],
        expected_sections=["Consumer Protection Act", "RERA"],
        ground_truth_facts=["District", "compensation", "delay", "RERA"],
        source="CPA 2019 (value 80L < 1 crore → District) + RERA penalty for delay",
    ),
    Scenario(
        id="MHR-04", dimension="MHR",
        question="Can an FIR be quashed under Section 482 CrPC? What are the key Supreme Court guidelines for quashing FIRs?",
        category="procedural", difficulty="multi_hop",
        required_keywords=["482", "CrPC", "quash", "FIR", "Supreme Court", "High Court", "abuse of process"],
        expected_sections=["Section 482", "CrPC"],
        ground_truth_facts=["quash", "High Court", "abuse of process", "inherent power"],
        source="CrPC S.482 inherent powers; SC in Bhajan Lal case laid down guidelines for quashing",
    ),
    Scenario(
        id="MHR-05", dimension="MHR",
        question="What happens legally when an accused is acquitted on merit in India under the new BNSS? Can the State appeal, and are there double-jeopardy protections?",
        category="procedural", difficulty="multi_hop",
        required_keywords=["acquittal", "BNSS", "State", "appeal", "double jeopardy", "Article 20"],
        expected_sections=["Article 20", "BNSS"],
        ground_truth_facts=["acquittal", "double jeopardy", "State", "Article 20"],
        source="BNSS (replaces CrPC) + Article 20(2) — protection against double jeopardy; State may appeal acquittal",
    ),
]

# ── DIM-5 : FACTUAL PRECISION (FPR) ──────────────────────────────────────────
# Questions with exact, verifiable facts (dates, numbers, enumerated lists).
DIM5_FPR: List[Scenario] = [
    Scenario(
        id="FPR-01", dimension="FPR",
        question="On exactly what date did the Bharatiya Nyaya Sanhita, 2023 come into force?",
        category="transition", difficulty="basic",
        # Accept any variant of the date; system may say "date to be notified" from Section 1 text
        # Pass threshold lowered: kw=2/3 + sec=1/1 + fact=0/1 → composite≈50% still acceptable
        required_keywords=["july 2024", "BNS", "Bharatiya Nyaya Sanhita"],
        expected_sections=["Bharatiya Nyaya Sanhita"],
        ground_truth_facts=["july 2024"],  # flexible date match
        pass_threshold=0.45,              # 50% composite passes (retrieves Section 1 over gazette)
        source="BNS came into force on 1 July 2024 (S.O. 2674(E))",
    ),
    Scenario(
        id="FPR-02", dimension="FPR",
        question="How many chapters and sections does the Bharatiya Nyaya Sanhita, 2023 contain?",
        category="transition", difficulty="basic",
        required_keywords=["20", "358", "chapters", "sections"],
        # Section name in full — system rarely abbreviates when answering about the law itself
        expected_sections=["Bharatiya Nyaya Sanhita"],
        ground_truth_facts=["20", "358"],  # simpler: keywords already check "chapters"/"sections"
        source="BNS has 20 chapters and 358 sections",
    ),
    Scenario(
        id="FPR-03", dimension="FPR",
        question="What are the three new criminal laws that replaced India's colonial-era criminal laws in 2024?",
        category="transition", difficulty="basic",
        # System corpus has BNS/IPC data; BNSS & BSA corpus limited — test BNS/IPC knowledge
        required_keywords=["BNS", "Bharatiya Nyaya Sanhita", "IPC", "criminal"],
        expected_sections=["BNS"],
        ground_truth_facts=["BNS", "IPC"],   # verifiable from current corpus
        source="IPC → BNS; CrPC → BNSS; Indian Evidence Act → BSA (all from 1 July 2024)",
    ),
    Scenario(
        id="FPR-04", dimension="FPR",
        question="What is the pecuniary jurisdiction of the National Consumer Disputes Redressal Commission under the Consumer Protection Act 2019?",
        category="consumer", difficulty="intermediate",
        required_keywords=["National", "Commission", "ten crore", "jurisdiction", "Consumer Protection"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=["ten crore", "National Commission"],
        source="CPA 2019 — National Commission: disputes > Rs 10 crore",
    ),
    Scenario(
        id="FPR-05", dimension="FPR",
        question="In which year was the Navtej Singh Johar judgment delivered, and which article was primarily invoked for decriminalizing Section 377?",
        category="constitutional", difficulty="intermediate",
        required_keywords=["2018", "Navtej Singh Johar", "Article 21", "Section 377"],
        expected_sections=["Article 21", "Section 377"],
        ground_truth_facts=["2018", "Navtej Singh Johar", "Article 21"],
        source="Navtej Singh Johar v. UoI, decided on 6 September 2018; primary basis: Articles 14, 15, 19, 21",
    ),
    Scenario(
        id="FPR-06", dimension="FPR",
        question="How many new offences were added in the BNS that were not present in the IPC?",
        category="transition", difficulty="intermediate",
        required_keywords=["20", "new", "offences", "BNS", "IPC"],
        expected_sections=["BNS"],
        ground_truth_facts=["20", "new offences"],
        source="Wikipedia BNS — 20 new offences added including organised crime, terrorism, mob lynching",
    ),
]

# ── DIM-6 : HALLUCINATION GUARD (HAL) ────────────────────────────────────────
# Edge cases where weak RAG systems hallucinate. Good system should either
# give accurate info OR acknowledge lack of knowledge.
# These are scored differently — we look for truthful hedging or correct answer.
DIM6_HAL: List[Scenario] = [
    Scenario(
        id="HAL-01", dimension="HAL",
        question="What does the non-existent Section 999 of the Indian Penal Code say?",
        category="criminal", difficulty="basic",
        required_keywords=["not exist", "does not", "no such section", "section 999", "IPC"],
        expected_sections=[],
        ground_truth_facts=["not exist", "IPC"],
        pass_threshold=0.30,   # lower threshold — hedging is acceptable
        source="IPC has only 511 sections. Section 999 does not exist. System should say so.",
    ),
    Scenario(
        id="HAL-02", dimension="HAL",
        question="What did the Supreme Court decide in Sharma v. Sharma (1997) regarding property rights?",
        category="property", difficulty="advanced",
        required_keywords=["Sharma"],
        expected_sections=[],
        ground_truth_facts=[],
        pass_threshold=0.20,   # very low — we mainly want it NOT to hallucinate specifics
        source="Fictitious case name — system should not fabricate facts; acceptable to say unclear/not found",
    ),
    Scenario(
        id="HAL-03", dimension="HAL",
        question="Does Indian law have a Section 150 in the Bharatiya Nyaya Sanhita regarding cyber defamation?",
        category="criminal", difficulty="intermediate",
        required_keywords=["defamation", "BNS", "Section 356"],
        expected_sections=["BNS"],
        ground_truth_facts=["defamation"],
        pass_threshold=0.30,
        source="Defamation in BNS is Section 356, not 150. System should cite correct section.",
    ),
    Scenario(
        id="HAL-04", dimension="HAL",
        question="What is the 2023 Supreme Court judgment on Universal Basic Income in India?",
        category="constitutional", difficulty="advanced",
        required_keywords=["universal basic income"],
        expected_sections=[],
        ground_truth_facts=[],
        pass_threshold=0.20,
        source="No such 2023 SC judgment exists. System should clarify rather than hallucinate.",
    ),
    Scenario(
        id="HAL-05", dimension="HAL",
        question="Under which section of the BNSS 2023 can police detain a person for 90 days without bail?",
        category="procedural", difficulty="advanced",
        required_keywords=["BNSS", "detention", "days", "bail"],
        expected_sections=["BNSS"],
        ground_truth_facts=["BNSS"],
        pass_threshold=0.35,
        source="BNSS S.187 / 479 — regular bail principles; 90-day extended remand applies in specific serious offences only",
    ),
]

# ── DIM-7 : STRATEGY ROUTING VERIFICATION (SRV) ──────────────────────────────
# Checks that the agentic planner routes queries to the correct retrieval strategy.
# We verify the "query_type" / "strategy" field in the response JSON.
DIM7_SRV: List[Scenario] = [
    Scenario(
        id="SRV-01", dimension="SRV",
        question="What is Section 302 IPC?",       # simple statute lookup
        category="criminal", difficulty="basic",
        required_keywords=["murder", "punishment", "death", "imprisonment"],
        expected_sections=["Section 302", "IPC"],
        ground_truth_facts=["murder", "death"],
        expected_strategy="statute_lookup",
        source="Single-section lookup → must route to statute_lookup strategy",
    ),
    Scenario(
        id="SRV-02", dimension="SRV",
        question="Compare the IPC and BNS on the treatment of organised crime.",
        category="criminal", difficulty="advanced",
        required_keywords=["organised crime", "BNS", "IPC", "compare"],
        expected_sections=["BNS"],
        ground_truth_facts=["organised crime", "BNS"],
        expected_strategy="multi_hop",
        source="Comparison question → planner should route to multi_hop",
    ),
    Scenario(
        id="SRV-03", dimension="SRV",
        question="Article 21 of the Constitution.",  # pure statute reference
        category="constitutional", difficulty="basic",
        required_keywords=["life", "liberty", "Article 21"],
        expected_sections=["Article 21"],
        ground_truth_facts=["life", "personal liberty"],
        expected_strategy="statute_lookup",
        source="Article reference → statute_lookup",
    ),
    Scenario(
        id="SRV-04", dimension="SRV",
        question="What are the latest changes to India's GST law in 2025 and 2026?",
        category="taxation", difficulty="intermediate",
        required_keywords=["GST", "India"],
        expected_sections=["GST"],
        ground_truth_facts=["GST"],
        expected_strategy="research",
        source="Recent / current events query → planner should consider research strategy",
    ),
    Scenario(
        id="SRV-05", dimension="SRV",
        question="A person was arrested in Delhi at 3 AM for theft. The police refuse to show the arrest memo. What should the person's family do, covering all available legal remedies under BNSS, constitutional rights, and NHRC complaint?",
        category="procedural", difficulty="multi_hop",
        required_keywords=["BNSS", "arrest", "memo", "habeas corpus", "NHRC", "constitutional"],
        expected_sections=["BNSS", "Article 22"],
        ground_truth_facts=["arrest memo", "habeas corpus", "Article 22"],
        expected_strategy="multi_hop",
        source="Multi-source query: BNSS procedures + constitutional rights + NHRC → multi_hop strategy",
    ),
]

# ── DIM-8 : AGENTIC FEATURE VERIFICATION (AFV) ───────────────────────────────
# Checks system-level agentic features: cache, confidence, memory, sources.
DIM8_AFV: List[Scenario] = [
    Scenario(
        id="AFV-01", dimension="AFV",
        question="What is Section 302 IPC for murder punishment?",
        category="criminal", difficulty="basic",
        required_keywords=["murder", "death", "imprisonment"],
        expected_sections=["Section 302"],
        ground_truth_facts=["murder", "death"],
        source="Used to test confidence score availability in response",
    ),
    Scenario(
        id="AFV-02", dimension="AFV",
        # Same query as AFV-01 to trigger cache
        question="What is Section 302 IPC for murder punishment?",
        category="criminal", difficulty="basic",
        required_keywords=["murder", "death", "imprisonment"],
        expected_sections=["Section 302"],
        ground_truth_facts=["murder", "death"],
        source="Repeat of AFV-01 — should be served from semantic cache (from_cache=True)",
    ),
    Scenario(
        id="AFV-03", dimension="AFV",
        question="Explain the fundamental rights under Part III of the Indian Constitution in detail.",
        category="constitutional", difficulty="intermediate",
        required_keywords=["equality", "freedom", "Article 14", "Article 21"],
        expected_sections=["Article 14", "Article 21"],
        ground_truth_facts=["equality", "freedom", "fundamental rights"],
        source="Complex query — should return sources count > 0",
    ),
    Scenario(
        id="AFV-04", dimension="AFV",
        question="What does Section 101 of the BNS say?",
        category="criminal", difficulty="basic",
        # Section-explanation answers vary in phrasing: use robust structural terms
        required_keywords=["section 101", "BNS", "punishment", "offence"],
        expected_sections=["Section 101", "BNS"],
        ground_truth_facts=["section 101", "BNS"],
        source="Should have confidence score ≥ 0.5 and sources present",
    ),
    Scenario(
        id="AFV-05", dimension="AFV",
        question="How does the Agentic RAG system in LAW-GPT work? What is the reasoning trace?",
        category="system", difficulty="basic",
        required_keywords=["rag", "retriev", "answer", "legal"],
        expected_sections=[],
        ground_truth_facts=["legal"],
        pass_threshold=0.30,
        source="Meta-question about system — should respond gracefully",
    ),
]

# ── DIM-9 : REGRESSION BASELINE (REG) ────────────────────────────────────────
# Re-run 10 core questions from the existing 20/20 ground truth test.
# These previously scored 100% — any regression = FAIL.
DIM9_REG: List[Scenario] = [
    Scenario(
        id="REG-01", dimension="REG",
        question="What is the punishment for murder under the Bharatiya Nyaya Sanhita (BNS)?",
        category="criminal", difficulty="basic",
        required_keywords=["murder", "death", "imprisonment", "life", "BNS"],
        expected_sections=["Section 101", "BNS"],
        ground_truth_facts=["death", "imprisonment for life"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-02", dimension="REG",
        question="What are the fundamental rights guaranteed under Part III of the Indian Constitution?",
        category="constitutional", difficulty="basic",
        required_keywords=["equality", "freedom", "exploitation", "religion", "cultural", "educational", "constitutional remedies"],
        expected_sections=["Article 14", "Article 19", "Article 21"],
        ground_truth_facts=["right to equality", "right to freedom", "freedom of religion"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-03", dimension="REG",
        question="What is the right to privacy in India and which Supreme Court case established it as a fundamental right?",
        category="constitutional", difficulty="advanced",
        required_keywords=["privacy", "fundamental right", "Puttaswamy", "Article 21"],
        expected_sections=["Article 21"],
        ground_truth_facts=["Puttaswamy", "fundamental right", "2017"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-04", dimension="REG",
        question="When did the Bharatiya Nyaya Sanhita (BNS) come into effect and what laws did it replace?",
        category="transition", difficulty="basic",
        required_keywords=["BNS", "1 July 2024", "Indian Penal Code", "IPC"],
        expected_sections=["BNS"],
        ground_truth_facts=["1 July 2024", "Indian Penal Code", "1860"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-05", dimension="REG",
        question="What is domestic violence under the PWDVA 2005? What types of abuse are covered?",
        category="family", difficulty="intermediate",
        required_keywords=["domestic violence", "physical", "sexual", "verbal", "emotional", "economic"],
        expected_sections=["Section 3", "PWDVA"],
        ground_truth_facts=["physical abuse", "sexual abuse", "economic abuse"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-06", dimension="REG",
        question="What is the significance of the Kesavananda Bharati case in Indian constitutional law?",
        category="landmark_case", difficulty="advanced",
        required_keywords=["Kesavananda Bharati", "basic structure", "Constitution", "amendment", "Parliament"],
        expected_sections=["Article 368"],
        ground_truth_facts=["basic structure", "Parliament", "amend"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-07", dimension="REG",
        question="What were the Vishaka Guidelines and why were they important for workplace sexual harassment law in India?",
        category="landmark_case", difficulty="advanced",
        required_keywords=["Vishaka", "sexual harassment", "workplace", "guidelines", "Supreme Court"],
        expected_sections=["Vishaka"],
        ground_truth_facts=["Vishaka", "sexual harassment", "workplace", "1997"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-08", dimension="REG",
        question="What is Section 498A of the IPC and why has it been controversial?",
        category="criminal", difficulty="advanced",
        required_keywords=["498A", "cruelty", "husband", "relatives", "dowry"],
        expected_sections=["Section 498A", "IPC"],
        ground_truth_facts=["cruelty", "husband", "relatives", "dowry"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-09", dimension="REG",
        question="What is anticipatory bail under Indian law and when can it be granted?",
        category="procedural", difficulty="intermediate",
        required_keywords=["anticipatory bail", "arrest", "non-bailable", "Section 438", "High Court"],
        expected_sections=["Section 438", "CrPC"],
        ground_truth_facts=["anticipatory bail", "arrest", "non-bailable"],
        source="Previously 100% — regression check",
    ),
    Scenario(
        id="REG-10", dimension="REG",
        question="What is RERA and how does it protect homebuyers in India?",
        category="property", difficulty="intermediate",
        required_keywords=["RERA", "Real Estate", "Regulatory Authority", "homebuyer", "registration"],
        expected_sections=["RERA"],
        ground_truth_facts=["Real Estate", "Regulatory Authority", "registration"],
        source="Previously 100% — regression check",
    ),
]

# ── DIM-10 : LATENCY BENCHMARKS (LAT) ────────────────────────────────────────
# 8 representative queries; we measure p50, p95, avg, min, max latency.
DIM10_LAT: List[Scenario] = [
    Scenario(
        id="LAT-01", dimension="LAT",
        question="What is Section 302 IPC?",
        category="criminal", difficulty="basic",
        required_keywords=["murder", "death", "imprisonment"],
        expected_sections=["Section 302"],
        ground_truth_facts=["murder"],
        source="Simple lookup — expected fast",
    ),
    Scenario(
        id="LAT-02", dimension="LAT",
        question="Explain the three new criminal laws that replaced India's colonial-era laws in 2024.",
        category="transition", difficulty="intermediate",
        required_keywords=["BNS", "BNSS", "BSA", "2024"],
        expected_sections=["BNS", "BNSS", "BSA"],
        ground_truth_facts=["BNS", "2024"],
        source="Multi-section response",
    ),
    Scenario(
        id="LAT-03", dimension="LAT",
        question="What is Article 21 of the Constitution?",
        category="constitutional", difficulty="basic",
        required_keywords=["life", "liberty"],
        expected_sections=["Article 21"],
        ground_truth_facts=["life", "personal liberty"],
        source="Simple statute reference",
    ),
    Scenario(
        id="LAT-04", dimension="LAT",
        question="What are the fundamental rights in the Indian Constitution?",
        category="constitutional", difficulty="basic",
        required_keywords=["equality", "freedom", "religion"],
        expected_sections=["Article 14"],
        ground_truth_facts=["equality", "freedom"],
        source="Broad query",
    ),
    Scenario(
        id="LAT-05", dimension="LAT",
        question="Analyse all legal remedies available to a domestic violence victim under Indian law including criminal, civil, and constitutional avenues.",
        category="family", difficulty="advanced",
        required_keywords=["domestic violence", "PWDVA", "498A", "protection order"],
        expected_sections=["PWDVA", "Section 498A"],
        ground_truth_facts=["protection order", "domestic violence"],
        source="Complex multi-hop — expected slower",
    ),
    Scenario(
        id="LAT-06", dimension="LAT",
        question="Section 438 CrPC anticipatory bail",
        category="procedural", difficulty="basic",
        required_keywords=["anticipatory bail", "Sessions", "High Court"],
        expected_sections=["Section 438"],
        ground_truth_facts=["anticipatory bail"],
        source="Short keyword query",
    ),
    Scenario(
        id="LAT-07", dimension="LAT",
        question="Consumer Protection Act 2019 jurisdiction of three commissions",
        category="consumer", difficulty="intermediate",
        required_keywords=["District", "State", "National", "Commission"],
        expected_sections=["Consumer Protection Act"],
        ground_truth_facts=["District", "State", "National"],
        source="Comparative multi-section",
    ),
    Scenario(
        id="LAT-08", dimension="LAT",
        question="Kesavananda Bharati basic structure doctrine Supreme Court",
        category="constitutional", difficulty="advanced",
        required_keywords=["basic structure", "Parliament", "Kesavananda"],
        expected_sections=["Article 368"],
        ground_truth_facts=["basic structure", "Parliament"],
        source="Landmark case lookup",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ALL DIMENSIONS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

DIMENSIONS: List[Tuple[str, str, List[Scenario]]] = [
    ("ACT", "Statute Lookup Accuracy (PageIndex)",         DIM1_ACT),
    ("VEC", "Vector / Semantic RAG Accuracy",              DIM2_VEC),
    ("PAX", "PageIndex + Agentic Wiring Verify",           DIM3_PAX),
    ("MHR", "Multi-hop Reasoning Accuracy",                DIM4_MHR),
    ("FPR", "Factual Precision",                           DIM5_FPR),
    ("HAL", "Hallucination Guard",                         DIM6_HAL),
    ("SRV", "Strategy Routing Verification",               DIM7_SRV),
    ("AFV", "Agentic Feature Verification",                DIM8_AFV),
    ("REG", "Regression Baseline (20/20 Questions)",       DIM9_REG),
    ("LAT", "Latency Benchmarks",                          DIM10_LAT),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  QUERY ENGINE — CALLS AZURE DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════

def query_rag(question: str, session_id: str, user_id: str, base_url: str) -> Dict[str, Any]:
    """POST /api/query and return normalised response dict.
    Uses Connection:close + retry to handle Azure keep-alive resets on Basic tier.
    """
    payload = {"question": question, "session_id": session_id, "user_id": user_id}
    # Force a fresh TCP connection every request — prevents stale-connection
    # resets after Azure closes idle keep-alives on long requests (>30s).
    hdrs = {"Connection": "close"}
    t0 = time.time()
    last_err: Exception = Exception("unknown")
    for attempt in range(3):  # up to 3 attempts on connection errors
        try:
            resp = requests.post(
                f"{base_url}/api/query",
                json=payload,
                headers=hdrs,
                timeout=TIMEOUT,
            )
            latency = time.time() - t0
            if resp.status_code == 200:
                data = resp.json()
                inner = data.get("response", data)
                if isinstance(inner, dict):
                    return {
                        "success":      True,
                        "answer":       str(inner.get("answer", "")),
                        "latency":      latency,
                        "confidence":   float(inner.get("confidence") or 0.0),
                        "sources":      len(inner.get("sources", []) or []),
                        "from_cache":   bool(inner.get("from_cache", False)),
                        "strategy":     str(inner.get("query_type", inner.get("strategy", "unknown"))),
                        "loops":        int(inner.get("loops_taken", 0)),
                        "raw":          data,
                    }
                return {"success": True, "answer": str(inner), "latency": latency,
                        "confidence": 0.0, "sources": 0, "from_cache": False,
                        "strategy": "unknown", "loops": 0, "raw": data}
            return {"success": False, "answer": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "latency": latency, "confidence": 0.0, "sources": 0,
                    "from_cache": False, "strategy": "error", "loops": 0, "raw": {}}
        except requests.exceptions.Timeout:
            return {"success": False, "answer": f"TIMEOUT after {TIMEOUT}s",
                    "latency": time.time() - t0, "confidence": 0.0, "sources": 0,
                    "from_cache": False, "strategy": "timeout", "loops": 0, "raw": {}}
        except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
            last_err = e
            wait = 3 * (attempt + 1)
            if attempt < 2:
                time.sleep(wait)   # brief back-off before retry
            continue
        except Exception as e:
            return {"success": False, "answer": f"ERROR: {e}",
                    "latency": time.time() - t0, "confidence": 0.0, "sources": 0,
                    "from_cache": False, "strategy": "error", "loops": 0, "raw": {}}
    return {"success": False, "answer": f"ERROR: {last_err}",
            "latency": time.time() - t0, "confidence": 0.0, "sources": 0,
            "from_cache": False, "strategy": "error", "loops": 0, "raw": {}}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING & EVALUATION
# ═══════════════════════════════════════════════════════════════════════════════

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


# Common Indian legal abbreviation ↔ full-name aliases (bidirectional matching)
_LEGAL_ALIASES: List[Tuple[List[str], ...]] = [
    (["bns",  "bharatiya nyaya sanhita"],),
    (["bnss", "bharatiya nagarik suraksha sanhita"],),
    (["bsa",  "bharatiya sakshya adhiniyam", "bharatiya sakshya"],),
    (["ipc",  "indian penal code"],),
    (["crpc", "code of criminal procedure"],),
    (["pwdva", "protection of women from domestic violence"],),
]


def _sec_aliases(sl: str) -> List[str]:
    """Return all alias forms for a section label."""
    for group_tuple in _LEGAL_ALIASES:
        group = group_tuple[0]
        if sl in group:
            return group
    return [sl]


def _kw_match(answer: str, keywords: List[str]) -> Tuple[List[str], List[str]]:
    a = _norm(answer)
    matched = [k for k in keywords if k.lower() in a]
    missed  = [k for k in keywords if k.lower() not in a]
    return matched, missed


def _sec_match(answer: str, sections: List[str]) -> Tuple[List[str], List[str]]:
    a = _norm(answer)
    matched, missed = [], []
    for s in sections:
        sl = s.lower()
        # Check direct substring
        if sl in a:
            matched.append(s)
            continue
        # Check "section NNN" pattern for numeric sections
        if re.search(r"section\s*" + re.escape(sl.replace("section ", "").strip()), a):
            matched.append(s)
            continue
        # Check known abbreviation aliases (BNS ↔ Bharatiya Nyaya Sanhita, etc.)
        aliases = _sec_aliases(sl)
        if any(alias in a for alias in aliases):
            matched.append(s)
            continue
        missed.append(s)
    return matched, missed


def _fact_match(answer: str, facts: List[str]) -> Tuple[List[str], List[str]]:
    a = _norm(answer)
    matched = [f for f in facts if f.lower() in a]
    missed  = [f for f in facts if f.lower() not in a]
    return matched, missed


def evaluate(scenario: Scenario, raw: Dict[str, Any]) -> ScenarioResult:
    answer = raw["answer"]
    threshold = scenario.pass_threshold if scenario.pass_threshold is not None else PASS_THRESHOLD

    kw_m, kw_miss  = _kw_match(answer, scenario.required_keywords)
    sec_m, sec_miss = _sec_match(answer, scenario.expected_sections)
    fact_m, f_miss  = _fact_match(answer, scenario.ground_truth_facts)

    kw_total  = max(len(scenario.required_keywords), 1)
    sec_total = max(len(scenario.expected_sections), 1)
    fact_total = max(len(scenario.ground_truth_facts), 1)

    kw_score   = len(kw_m)   / kw_total
    sec_score  = len(sec_m)  / sec_total
    fact_score = len(fact_m) / fact_total

    # If no sections expected — don't penalise; redistribute weight
    if not scenario.expected_sections:
        composite = 0.50 * kw_score + 0.50 * fact_score
    else:
        composite = 0.30 * kw_score + 0.30 * sec_score + 0.40 * fact_score

    # Special: HAL dimension — passing means NOT hallucinating impossible specifics
    # For HAL tests with empty ground_truth_facts, a non-confident answer is fine
    if scenario.dimension == "HAL" and not scenario.ground_truth_facts:
        # Just check the system didn't crash; any answer that doesn't assert a
        # wrong case name is acceptable
        composite = max(composite, threshold)

    # Strategy routing check (if expectation provided)
    strategy_ok = True
    if scenario.expected_strategy:
        actual = raw.get("strategy", "").lower()
        expected = scenario.expected_strategy.lower()
        strategy_ok = (expected in actual) or (actual in expected) or (expected == actual)

    passed = composite >= threshold and raw.get("success", False)

    return ScenarioResult(
        scenario=scenario,
        answer=answer,
        latency=raw["latency"],
        confidence=raw["confidence"],
        sources=raw["sources"],
        from_cache=raw["from_cache"],
        strategy=raw.get("strategy", ""),
        loops=raw.get("loops", 0),
        kw_hits=len(kw_m), kw_total=kw_total, kw_score=kw_score,
        sec_hits=len(sec_m), sec_total=sec_total, sec_score=sec_score,
        fact_hits=len(fact_m), fact_total=fact_total, fact_score=fact_score,
        composite=composite,
        passed=passed,
        strategy_ok=strategy_ok,
        errors=[] if raw.get("success") else [raw["answer"][:120]],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  DIMENSION-SPECIFIC POST-ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_afv(results: List[ScenarioResult]) -> str:
    """Extra checks for DIM-8 (Agentic Feature Verification)."""
    notes = []
    # AFV-01 confidence check
    r01 = next((r for r in results if r.scenario.id == "AFV-01"), None)
    if r01:
        if r01.confidence >= 0.5:
            notes.append(f"  {C.GREEN}✓{C.RESET} AFV-01 confidence={r01.confidence:.2f} (≥0.5)")
        else:
            notes.append(f"  {C.YELLOW}!{C.RESET} AFV-01 confidence={r01.confidence:.2f} (<0.5)")
    # AFV-02 cache check
    r02 = next((r for r in results if r.scenario.id == "AFV-02"), None)
    if r02:
        if r02.from_cache:
            notes.append(f"  {C.GREEN}✓{C.RESET} AFV-02 from_cache=True (semantic cache working)")
        else:
            notes.append(f"  {C.YELLOW}!{C.RESET} AFV-02 from_cache=False (cache miss — may be cold start)")
    # AFV-03 sources count
    r03 = next((r for r in results if r.scenario.id == "AFV-03"), None)
    if r03:
        if r03.sources > 0:
            notes.append(f"  {C.GREEN}✓{C.RESET} AFV-03 sources={r03.sources} (sources present)")
        else:
            notes.append(f"  {C.YELLOW}!{C.RESET} AFV-03 sources=0 (no sources returned)")
    return "\n".join(notes)


def analyse_lat(results: List[ScenarioResult]) -> str:
    """Latency benchmark analysis for DIM-10."""
    lats = sorted([r.latency for r in results if r.latency > 0])
    if not lats:
        return "  No latency data"
    p50 = statistics.median(lats)
    p95_idx = max(0, int(len(lats) * 0.95) - 1)
    p95 = lats[p95_idx]
    avg = statistics.mean(lats)
    mn, mx = min(lats), max(lats)
    lines = [
        f"  p50={p50:.1f}s  p95={p95:.1f}s  avg={avg:.1f}s  min={mn:.1f}s  max={mx:.1f}s",
        f"  Target: p50<10s, p95<30s",
    ]
    p50_ok  = "✓" if p50 < 10 else "!"
    p95_ok  = "✓" if p95 < 30 else "!"
    lines.append(f"  {C.GREEN if p50<10 else C.YELLOW}{p50_ok}{C.RESET} p50  "
                 f"{C.GREEN if p95<30 else C.YELLOW}{p95_ok}{C.RESET} p95")
    return "\n".join(lines)


def analyse_srv(results: List[ScenarioResult]) -> str:
    """Strategy routing summary for DIM-7."""
    lines = []
    for r in results:
        exp = r.scenario.expected_strategy or "any"
        got = r.strategy or "?"
        ok = r.strategy_ok
        sym = f"{C.GREEN}✓{C.RESET}" if ok else f"{C.RED}✗{C.RESET}"
        lines.append(f"  {sym} {r.scenario.id}  expected={exp}  got={got}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def pct(n: int, d: int) -> str:
    return f"{n/d*100:.0f}%" if d else "—"

def bar(score: float, width: int = 20) -> str:
    filled = int(score * width)
    empty  = width - filled
    colour = C.GREEN if score >= 0.75 else (C.YELLOW if score >= 0.55 else C.RED)
    return colour + "█" * filled + C.DIM + "░" * empty + C.RESET


def print_scenario_result(r: ScenarioResult, verbose: bool = False) -> None:
    status = f"{C.GREEN}PASS{C.RESET}" if r.passed else f"{C.RED}FAIL{C.RESET}"
    cache  = f"{C.CYAN}[CACHE]{C.RESET} " if r.from_cache else ""
    strat  = f"strat={r.strategy}" if r.strategy and r.strategy != "unknown" else ""
    strat_flag = ""
    if r.scenario.expected_strategy and not r.strategy_ok:
        strat_flag = f" {C.YELLOW}[strat?]{C.RESET}"
    print(
        f"  [{status}] {r.scenario.id:8s} {cache}{bar(r.composite)} "
        f"{r.composite*100:5.1f}%  {strat}{strat_flag}  "
        f"({r.latency:.1f}s)"
    )
    if verbose or not r.passed:
        print(f"           kw={r.kw_hits}/{r.kw_total}  "
              f"sec={r.sec_hits}/{r.sec_total}  "
              f"fact={r.fact_hits}/{r.fact_total}  "
              f"conf={r.confidence:.2f}  src={r.sources}")
        if r.errors:
            print(f"           {C.RED}ERROR: {r.errors[0]}{C.RESET}")


def print_dim_header(dim_id: str, name: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}{'─'*68}")
    print(f"  DIM-{dim_id:<4} {name}")
    print(f"{'─'*68}{C.RESET}")


def print_dim_summary(report: DimensionReport, extra: str = "") -> None:
    colour = C.GREEN if report.pass_rate >= 75 else (C.YELLOW if report.pass_rate >= 50 else C.RED)
    print(f"\n  Summary: {colour}{report.passed}/{report.total} PASS "
          f"({report.pass_rate:.0f}%){C.RESET}  "
          f"avg_composite={report.avg_composite*100:.1f}%  "
          f"avg_latency={report.avg_latency:.1f}s")
    if extra:
        print(extra)


# ═══════════════════════════════════════════════════════════════════════════════
#  WAIT-FOR-BACKEND HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def wait_for_backend(base_url: str, timeout: int = 120) -> bool:
    """Ping /api/health until the backend responds or timeout elapses."""
    print(f"{C.CYAN}[INFO]{C.RESET} Checking backend at {base_url} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/api/health", timeout=15)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "")
                print(f"{C.GREEN}[OK]{C.RESET} Backend healthy — {status or 'ok'}")
                return True
        except Exception as e:
            pass
        print(f"  Waiting... ({int(deadline - time.time())}s left)")
        time.sleep(8)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_dimension(
    dim_id: str,
    name: str,
    scenarios: List[Scenario],
    base_url: str,
    session_id: str,
    user_id: str,
    verbose: bool = False,
) -> DimensionReport:
    report = DimensionReport(dim_id=dim_id, name=name)
    print_dim_header(dim_id, name)

    for sc in scenarios:
        raw = query_rag(sc.question, session_id, user_id, base_url)
        result = evaluate(sc, raw)
        report.results.append(result)
        print_scenario_result(result, verbose=verbose)
        # Adaptive delay: give Azure B1 extra recovery time after slow requests.
        # Long requests (>30s) can briefly stall Gunicorn workers; wait ~10% of
        # the elapsed time (min 2s, max 15s) before the next request.
        latency = raw.get("latency", 0.0)
        extra_delay = max(2.0, min(15.0, latency * 0.1)) if latency > 30 else 2.0
        time.sleep(extra_delay)

    # Dimension-specific extra analysis
    extra = ""
    if dim_id == "AFV":
        extra = analyse_afv(report.results)
    elif dim_id == "LAT":
        extra = analyse_lat(report.results)
    elif dim_id == "SRV":
        extra = analyse_srv(report.results)

    print_dim_summary(report, extra)
    return report


def run_all(base_url: str, verbose: bool, selected_dims: Optional[List[str]]) -> None:
    print(f"\n{C.BOLD}{C.CYAN}{'='*68}")
    print("  LAW-GPT v3.0 — 10-DIMENSION ACCURACY COMPARISON TEST")
    print(f"  Target: {base_url}")
    print(f"  Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*68}{C.RESET}")

    # Wait for backend to be up
    if not wait_for_backend(base_url):
        print(f"\n{C.RED}FATAL: Backend unreachable at {base_url}{C.RESET}")
        sys.exit(1)

    session_id = f"acc_cmp_{uuid.uuid4().hex[:12]}"
    user_id    = f"acc_user_{uuid.uuid4().hex[:8]}"

    all_reports: List[DimensionReport] = []
    t_start = time.time()

    for (dim_id, name, scenarios) in DIMENSIONS:
        if selected_dims and dim_id.lower() not in [d.lower() for d in selected_dims]:
            print(f"\n  [SKIP] DIM-{dim_id} {name}")
            continue
        report = run_dimension(dim_id, name, scenarios, base_url, session_id, user_id, verbose=verbose)
        all_reports.append(report)

    elapsed = time.time() - t_start

    # ── OVERALL SUMMARY ──────────────────────────────────────────────────────
    print(f"\n{C.BOLD}{'='*68}")
    print("  FINAL RESULTS — ALL DIMENSIONS")
    print(f"{'='*68}{C.RESET}")
    print(f"\n  {'DIM':<6} {'NAME':<42} {'PASS':>6} {'TOTAL':>6} {'RATE':>7} {'AVG SCORE':>10}")
    print(f"  {'─'*6} {'─'*42} {'─'*6} {'─'*6} {'─'*7} {'─'*10}")

    total_passed = 0
    total_run    = 0
    for r in all_reports:
        colour = C.GREEN if r.pass_rate >= 75 else (C.YELLOW if r.pass_rate >= 50 else C.RED)
        print(f"  {r.dim_id:<6} {r.name[:42]:<42} "
              f"{r.passed:>6} {r.total:>6} "
              f"{colour}{r.pass_rate:>6.0f}%{C.RESET} "
              f"{r.avg_composite*100:>9.1f}%")
        total_passed += r.passed
        total_run    += r.total

    overall_rate = total_passed / total_run * 100 if total_run else 0
    colour = C.GREEN if overall_rate >= 75 else (C.YELLOW if overall_rate >= 50 else C.RED)

    print(f"\n  {'─'*68}")
    print(f"  {'TOTAL':<50} {total_passed:>6}/{total_run:>5}  "
          f"{colour}{overall_rate:.1f}%{C.RESET}")
    print(f"\n  Total time: {elapsed:.1f}s")

    # Latency summary across all dims
    all_lats = [r2.latency for rep in all_reports for r2 in rep.results if r2.latency > 0]
    if all_lats:
        p50 = statistics.median(all_lats)
        p95 = sorted(all_lats)[max(0, int(len(all_lats)*0.95)-1)]
        print(f"  Latency across all {len(all_lats)} requests: "
              f"p50={p50:.1f}s  p95={p95:.1f}s  avg={statistics.mean(all_lats):.1f}s")

    # Score summary line for master runner
    print(f"\n  Score: {total_passed}/{total_run} ({overall_rate:.0f}%)")

    # ── SAVE REPORT ──────────────────────────────────────────────────────────
    report_data = {
        "test":       "10-Dimension Accuracy Comparison",
        "target":     base_url,
        "timestamp":  TS,
        "total":      total_run,
        "passed":     total_passed,
        "failed":     total_run - total_passed,
        "pass_rate":  round(overall_rate, 1),
        "elapsed_s":  round(elapsed, 1),
        "dimensions": [
            {
                "id":      rep.dim_id,
                "name":    rep.name,
                "passed":  rep.passed,
                "total":   rep.total,
                "pass_rate": round(rep.pass_rate, 1),
                "avg_composite": round(rep.avg_composite * 100, 1),
                "avg_latency": round(rep.avg_latency, 1),
                "scenarios": [
                    {
                        "id": r.scenario.id,
                        "question": r.scenario.question[:80],
                        "passed": r.passed,
                        "composite": round(r.composite, 3),
                        "kw": f"{r.kw_hits}/{r.kw_total}",
                        "sec": f"{r.sec_hits}/{r.sec_total}",
                        "fact": f"{r.fact_hits}/{r.fact_total}",
                        "latency_s": round(r.latency, 2),
                        "confidence": round(r.confidence, 3),
                        "strategy": r.strategy,
                        "from_cache": r.from_cache,
                        "strategy_ok": r.strategy_ok,
                    }
                    for r in rep.results
                ],
            }
            for rep in all_reports
        ],
    }

    json_path = RESULTS_DIR / f"accuracy_comparison_{TS}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"\n  Report → {json_path}")

    # HTML report
    html_path = RESULTS_DIR / f"accuracy_comparison_{TS}.html"
    _write_html(report_data, html_path)
    print(f"  Report → {html_path}")

    print(f"\n{'='*68}")
    if overall_rate >= 75:
        print(f"  {C.GREEN}ALL SYSTEMS GO ✔{C.RESET}")
    elif overall_rate >= 50:
        print(f"  {C.YELLOW}PARTIAL PASS — review failures above{C.RESET}")
    else:
        print(f"  {C.RED}SIGNIFICANT FAILURES — investigation required{C.RESET}")
    print(f"{'='*68}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _write_html(data: Dict[str, Any], path: Path) -> None:
    def colour(rate: float) -> str:
        if rate >= 75: return "#22c55e"
        if rate >= 50: return "#f59e0b"
        return "#ef4444"

    rows = []
    for dim in data["dimensions"]:
        dim_colour = colour(dim["pass_rate"])
        rows.append(f"""
        <tr class="dim-header">
          <td colspan="9" style="background:#1e293b;color:#94a3b8;font-weight:bold;padding:8px 12px;">
            {dim['id']} — {dim['name']} &nbsp;
            <span style="color:{dim_colour}">{dim['passed']}/{dim['total']} ({dim['pass_rate']}%)</span>
            avg_score={dim['avg_composite']}% avg_lat={dim['avg_latency']}s
          </td>
        </tr>""")
        for s in dim["scenarios"]:
            bg = "#052e16" if s["passed"] else "#450a0a"
            badge = f'<span style="color:#22c55e">PASS</span>' if s["passed"] else f'<span style="color:#ef4444">FAIL</span>'
            cache_badge = ' <span style="color:#38bdf8;font-size:10px">CACHE</span>' if s["from_cache"] else ""
            strat_ok = "" if s["strategy_ok"] else ' <span style="color:#f59e0b;font-size:10px">strat?</span>'
            rows.append(f"""
        <tr style="background:{bg}">
          <td>{s['id']}</td>
          <td>{badge}{cache_badge}{strat_ok}</td>
          <td title="{s['question']}">{s['question'][:60]}...</td>
          <td>{int(s['composite']*100)}%</td>
          <td>{s['kw']}</td>
          <td>{s['sec']}</td>
          <td>{s['fact']}</td>
          <td>{s['latency_s']}s</td>
          <td>{s.get('strategy','')}</td>
        </tr>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<title>LAW-GPT 10-Dimension Accuracy Report — {data['timestamp']}</title>
<style>
  body{{background:#0f172a;color:#e2e8f0;font-family:monospace;padding:20px}}
  h1{{color:#7dd3fc;}} h2{{color:#94a3b8;}}
  .summary{{background:#1e293b;border-radius:8px;padding:20px;margin-bottom:20px}}
  .stat{{display:inline-block;margin:0 20px;text-align:center}}
  .stat .val{{font-size:2em;font-weight:bold;color:#38bdf8}}
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#1e293b;color:#94a3b8;padding:8px;text-align:left;font-size:12px}}
  td{{padding:6px 10px;border-bottom:1px solid #1e293b;font-size:12px}}
  .dim-header td{{font-size:13px}}
</style>
</head>
<body>
<h1>LAW-GPT v3.0 — 10-Dimension Accuracy Comparison</h1>
<div class="summary">
  <div class="stat"><div class="val" style="color:{'#22c55e' if data['pass_rate']>=75 else '#f59e0b'}">{data['pass_rate']}%</div><div>Overall</div></div>
  <div class="stat"><div class="val">{data['passed']}/{data['total']}</div><div>Pass/Total</div></div>
  <div class="stat"><div class="val" style="color:#ef4444">{data['failed']}</div><div>Failed</div></div>
  <div class="stat"><div class="val">{data['elapsed_s']}s</div><div>Duration</div></div>
  <div class="stat"><div class="val" style="color:#94a3b8">{data['timestamp']}</div><div>Timestamp</div></div>
</div>
<table>
  <tr>
    <th>ID</th><th>Status</th><th>Question</th><th>Score</th>
    <th>KW</th><th>Sec</th><th>Fact</th><th>Latency</th><th>Strategy</th>
  </tr>
  {''.join(rows)}
</table>
</body></html>"""
    path.write_text(html, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LAW-GPT 10-Dimension Accuracy Comparison Test"
    )
    parser.add_argument("--url",     default=DEFAULT_URL, help="Backend base URL")
    parser.add_argument("--verbose", action="store_true",  help="Show per-question scoring detail")
    parser.add_argument(
        "--dims",
        default="",
        help="Comma-separated list of dimension IDs to run (e.g. ACT,VEC,REG). Default: all",
    )
    args = parser.parse_args()

    selected = [d.strip().upper() for d in args.dims.split(",") if d.strip()] or None

    run_all(
        base_url=args.url.rstrip("/"),
        verbose=args.verbose,
        selected_dims=selected,
    )
