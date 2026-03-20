"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   LAW-GPT v3.0 — COMPREHENSIVE ACCURACY & LATENCY GROUND TRUTH TEST       ║
║                                                                            ║
║   PURPOSE: Measure RAG accuracy against verified ground truth answers      ║
║            and profile latency across diverse Indian legal questions        ║
║                                                                            ║
║   METHODOLOGY:                                                             ║
║     1. 25 complex, real-world Indian legal questions with verified          ║
║        ground truth (from statutes, landmark SC judgments, wiki, etc.)      ║
║     2. Each question has:                                                  ║
║        - Query text                                                        ║
║        - Category (criminal, constitutional, consumer, family, etc.)       ║
║        - Ground truth keywords/sections that MUST appear in answer         ║
║        - Ground truth facts (factual assertions that must be accurate)     ║
║        - Difficulty level (basic, intermediate, advanced, multi-hop)       ║
║     3. Scoring:                                                            ║
║        - Keyword Hit Rate: % of ground truth keywords found in answer      ║
║        - Section Citation Accuracy: Did it cite correct statute/section?   ║
║        - Factual Accuracy: Are key facts correct?                          ║
║        - Composite Score: Weighted average of above                        ║
║     4. Latency: p50, p95, avg, min, max across all queries                ║
║                                                                            ║
║   TARGET: https://lawgpt-backend2024.azurewebsites.net                     ║
║   DATE:   February 2026                                                    ║
║                                                                            ║
║   RUN:    python tests/test_accuracy_ground_truth.py                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import requests
import json
import time
import sys
import uuid
import re
import statistics
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
BASE_URL = os.environ.get("LAWGPT_BASE_URL", "https://lawgpt-backend2024.azurewebsites.net")
TIMEOUT = 180  # generous for complex queries
SESSION_ID = f"accuracy_test_{uuid.uuid4().hex[:12]}"
USER_ID = f"accuracy_user_{uuid.uuid4().hex[:8]}"


class C:
    """Terminal colours."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GroundTruth:
    """Ground truth for a single legal question."""
    question: str
    category: str                    # criminal, constitutional, consumer, family, property, procedural, landmark_case, transition
    difficulty: str                  # basic, intermediate, advanced, multi_hop
    # Keywords that should appear in a correct answer (case-insensitive)
    required_keywords: List[str]     # MUST find at least some of these
    # Specific statute sections that should be cited
    expected_sections: List[str]     # e.g. ["Section 302", "BNS", "Section 100"]
    # Factual assertions — each is a substring that should be findable
    ground_truth_facts: List[str]    # key factual phrases
    # Research source / justification for the ground truth
    source: str


@dataclass
class QueryResult:
    """Result from querying the RAG system."""
    question: str
    answer: str
    latency_sec: float
    confidence: float
    sources_count: int
    from_cache: bool
    strategy: str
    # Accuracy metrics
    keyword_hits: int = 0
    keyword_total: int = 0
    keyword_score: float = 0.0
    section_hits: int = 0
    section_total: int = 0
    section_score: float = 0.0
    fact_hits: int = 0
    fact_total: int = 0
    fact_score: float = 0.0
    composite_score: float = 0.0
    category: str = ""
    difficulty: str = ""
    # Details
    matched_keywords: List[str] = field(default_factory=list)
    missed_keywords: List[str] = field(default_factory=list)
    matched_sections: List[str] = field(default_factory=list)
    missed_sections: List[str] = field(default_factory=list)
    matched_facts: List[str] = field(default_factory=list)
    missed_facts: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# GROUND TRUTH DATABASE — 25 COMPLEX LEGAL QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
# Sources: Wikipedia, Indian Kanoon, PRS Legislative Research, Gazette of India,
#          Supreme Court judgments, statutory text of BNS/IPC/CrPC/CPA/PWDVA

GROUND_TRUTH_QUESTIONS: List[GroundTruth] = [

    # ─── CATEGORY 1: CRIMINAL LAW (BNS / IPC) ────────────────────────────

    GroundTruth(
        question="What is the punishment for murder under the Bharatiya Nyaya Sanhita (BNS)?",
        category="criminal",
        difficulty="basic",
        required_keywords=["murder", "death", "imprisonment", "life", "BNS", "punishment"],
        expected_sections=["Section 101", "Section 302", "BNS"],
        ground_truth_facts=[
            "death",
            "imprisonment for life",
            "fine",
        ],
        source="BNS Section 101 (replacing IPC Section 302) — murder punishable by death or life imprisonment"
    ),

    GroundTruth(
        question="What are the new offences added in the Bharatiya Nyaya Sanhita (BNS) that were not in the IPC?",
        category="criminal",
        difficulty="intermediate",
        required_keywords=["organised crime", "terrorism", "BNS", "IPC", "new"],
        expected_sections=["BNS"],
        ground_truth_facts=[
            "organised crime",
            "terrorism",
            "mob lynching",
        ],
        source="Wikipedia BNS article — 20 new offences added including organised crime, terrorism, mob lynching"
    ),

    GroundTruth(
        question="Has sedition been removed under the new criminal law reforms in India? What replaced it?",
        category="criminal",
        difficulty="intermediate",
        required_keywords=["sedition", "removed", "sovereignty", "unity", "integrity"],
        expected_sections=["BNS", "Section 152"],
        ground_truth_facts=[
            "sedition",
            "sovereignty",
            "unity and integrity",
        ],
        source="BNS removed sedition; replaced with offence for 'acts endangering sovereignty, unity and integrity of India'"
    ),

    GroundTruth(
        question="What is the punishment for theft under Indian law?",
        category="criminal",
        difficulty="basic",
        required_keywords=["theft", "imprisonment", "fine", "punishment"],
        expected_sections=["Section 303", "Section 379"],
        ground_truth_facts=[
            "imprisonment",
            "fine",
            "three years",
        ],
        source="IPC Section 379 / BNS Section 303 — theft punishable with imprisonment up to 3 years plus fine"
    ),

    GroundTruth(
        question="What is the legal definition and punishment for dowry death in India?",
        category="criminal",
        difficulty="advanced",
        required_keywords=["dowry death", "seven years", "marriage", "cruelty", "husband", "relative"],
        expected_sections=["Section 304B", "Section 498A", "Section 80"],
        ground_truth_facts=[
            "seven years",
            "unnatural",
            "cruelty",
            "dowry",
        ],
        source="IPC 304B / BNS Section 80 — dowry death within 7 years of marriage; punishment: min 7 yrs to life imprisonment"
    ),

    # ─── CATEGORY 2: CONSTITUTIONAL LAW ──────────────────────────────────

    GroundTruth(
        question="What are the fundamental rights guaranteed under Part III of the Indian Constitution?",
        category="constitutional",
        difficulty="basic",
        required_keywords=["equality", "freedom", "exploitation", "religion", "cultural", "educational", "constitutional remedies"],
        expected_sections=["Article 14", "Article 19", "Article 21", "Article 32", "Part III"],
        ground_truth_facts=[
            "right to equality",
            "right to freedom",
            "right against exploitation",
            "freedom of religion",
            "right to constitutional remedies",
        ],
        source="Constitution of India, Part III — 6 fundamental rights (Articles 14-32)"
    ),

    GroundTruth(
        question="What is the right to privacy in India and which Supreme Court case established it as a fundamental right?",
        category="constitutional",
        difficulty="advanced",
        required_keywords=["privacy", "fundamental right", "Puttaswamy", "Article 21", "Supreme Court"],
        expected_sections=["Article 21"],
        ground_truth_facts=[
            "Puttaswamy",
            "fundamental right",
            "Article 21",
            "2017",
        ],
        source="Justice K.S. Puttaswamy v. Union of India (2017) — SC held right to privacy is fundamental right under Art 21"
    ),

    GroundTruth(
        question="What did the Supreme Court hold in the Navtej Singh Johar case regarding Section 377?",
        category="constitutional",
        difficulty="advanced",
        required_keywords=["Section 377", "unconstitutional", "homosexuality", "consensual", "decriminalised", "adults"],
        expected_sections=["Section 377", "Article 14", "Article 15", "Article 21"],
        ground_truth_facts=[
            "unconstitutional",
            "consensual",
            "decriminalised",
            "2018",
        ],
        source="Navtej Singh Johar v. Union of India (2018) — SC decriminalised consensual homosexual acts between adults"
    ),

    # ─── CATEGORY 3: CONSUMER PROTECTION ─────────────────────────────────

    GroundTruth(
        question="What are the key features of the Consumer Protection Act, 2019 and how is it different from the 1986 Act?",
        category="consumer",
        difficulty="intermediate",
        required_keywords=["Consumer Protection Act", "2019", "1986", "CCPA", "e-commerce", "mediation"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=[
            "Central Consumer Protection Authority",
            "e-commerce",
            "1986",
            "mediation",
        ],
        source="Consumer Protection Act 2019 replaced CPA 1986; introduces CCPA, e-commerce rules, mediation, product liability"
    ),

    GroundTruth(
        question="What are the consumer rights defined under the Consumer Protection Act 2019?",
        category="consumer",
        difficulty="basic",
        required_keywords=["consumer rights", "protection", "hazardous", "informed", "redressal"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=[
            "hazardous",
            "quality",
            "quantity",
            "redressal",
            "competitive prices",
        ],
        source="CPA 2019 — right to safety, right to be informed, right to choose, right to seek redressal"
    ),

    GroundTruth(
        question="What is the jurisdiction of District, State and National Consumer Disputes Redressal Commissions?",
        category="consumer",
        difficulty="intermediate",
        required_keywords=["District", "State", "National", "Commission", "crore", "jurisdiction"],
        expected_sections=["Consumer Protection Act"],
        ground_truth_facts=[
            "District",
            "State",
            "National",
            "crore",
        ],
        source="CPA 2019: District ≤ 1 crore, State 1-10 crore, National > 10 crore (pecuniary jurisdiction)"
    ),

    # ─── CATEGORY 4: DOMESTIC VIOLENCE / WOMEN PROTECTION ────────────────

    GroundTruth(
        question="What is domestic violence under the Protection of Women from Domestic Violence Act, 2005? What types of abuse are covered?",
        category="family",
        difficulty="intermediate",
        required_keywords=["domestic violence", "physical", "sexual", "verbal", "emotional", "economic", "abuse"],
        expected_sections=["Section 3", "PWDVA", "Protection of Women from Domestic Violence Act"],
        ground_truth_facts=[
            "physical abuse",
            "sexual abuse",
            "verbal",
            "emotional",
            "economic abuse",
        ],
        source="PWDVA 2005, Section 3 — domestic violence includes physical, sexual, verbal/emotional, and economic abuse"
    ),

    GroundTruth(
        question="What reliefs can an aggrieved woman seek under the Protection of Women from Domestic Violence Act?",
        category="family",
        difficulty="intermediate",
        required_keywords=["protection order", "residence order", "monetary relief", "custody", "compensation"],
        expected_sections=["PWDVA", "Protection of Women from Domestic Violence Act"],
        ground_truth_facts=[
            "protection order",
            "residence order",
            "monetary relief",
            "custody",
            "compensation",
        ],
        source="PWDVA 2005, Chapter III — protection order, residence order, monetary relief, custody order, compensation order"
    ),

    # ─── CATEGORY 5: IPC TO BNS TRANSITION ───────────────────────────────

    GroundTruth(
        question="When did the Bharatiya Nyaya Sanhita (BNS) come into effect and what laws did it replace?",
        category="transition",
        difficulty="basic",
        required_keywords=["BNS", "1 July 2024", "Indian Penal Code", "IPC", "replace"],
        expected_sections=["BNS", "Bharatiya Nyaya Sanhita"],
        ground_truth_facts=[
            "1 July 2024",
            "Indian Penal Code",
            "1860",
        ],
        source="BNS came into effect on 1 July 2024, replacing the Indian Penal Code of 1860"
    ),

    GroundTruth(
        question="What are the three new criminal laws that replaced the colonial-era laws in India in 2024?",
        category="transition",
        difficulty="intermediate",
        required_keywords=["Bharatiya Nyaya Sanhita", "Bharatiya Nagarik Suraksha Sanhita", "Bharatiya Sakshya"],
        expected_sections=["BNS", "BNSS", "BSA"],
        ground_truth_facts=[
            "Bharatiya Nyaya Sanhita",
            "Bharatiya Nagarik Suraksha Sanhita",
            "Bharatiya Sakshya",
            "Indian Penal Code",
        ],
        source="Three new laws: BNS (replaces IPC), BNSS (replaces CrPC), BSA (replaces Indian Evidence Act)"
    ),

    GroundTruth(
        question="How many chapters and sections does the Bharatiya Nyaya Sanhita have?",
        category="transition",
        difficulty="basic",
        required_keywords=["20", "358", "chapters", "sections", "BNS"],
        expected_sections=["BNS"],
        ground_truth_facts=[
            "20 chapters",
            "358 sections",
        ],
        source="BNS comprises 20 chapters and 358 sections (Wikipedia BNS Structure)"
    ),

    # ─── CATEGORY 6: LANDMARK SUPREME COURT CASES ────────────────────────

    GroundTruth(
        question="What were the Vishaka Guidelines and why were they important for workplace sexual harassment law in India?",
        category="landmark_case",
        difficulty="advanced",
        required_keywords=["Vishaka", "sexual harassment", "workplace", "guidelines", "Supreme Court"],
        expected_sections=["Vishaka"],
        ground_truth_facts=[
            "Vishaka",
            "sexual harassment",
            "workplace",
            "1997",
        ],
        source="Vishaka v. State of Rajasthan (1997) — SC laid down guidelines against workplace sexual harassment"
    ),

    GroundTruth(
        question="What is the significance of the Kesavananda Bharati case in Indian constitutional law?",
        category="landmark_case",
        difficulty="advanced",
        required_keywords=["Kesavananda Bharati", "basic structure", "Constitution", "amendment", "Parliament"],
        expected_sections=["Article 368"],
        ground_truth_facts=[
            "basic structure",
            "Parliament",
            "amend",
        ],
        source="Kesavananda Bharati v. State of Kerala (1973) — SC established basic structure doctrine"
    ),

    # ─── CATEGORY 7: MULTI-HOP REASONING QUESTIONS ──────────────────────

    GroundTruth(
        question="If a person commits murder and also destroys evidence to cover it up, what are the applicable BNS/IPC sections and their respective punishments?",
        category="criminal",
        difficulty="multi_hop",
        required_keywords=["murder", "evidence", "punishment", "imprisonment", "destruction"],
        expected_sections=["Section 302", "Section 201", "Section 101"],
        ground_truth_facts=[
            "death",
            "imprisonment for life",
            "evidence",
        ],
        source="IPC 302 (murder) + IPC 201 (causing disappearance of evidence) — both apply concurrently"
    ),

    GroundTruth(
        question="A woman in a live-in relationship faces physical and economic abuse from her partner. What legal remedies are available to her under Indian law?",
        category="family",
        difficulty="multi_hop",
        required_keywords=["domestic violence", "live-in", "protection order", "PWDVA", "498A"],
        expected_sections=["PWDVA", "Section 498A"],
        ground_truth_facts=[
            "Protection of Women from Domestic Violence Act",
            "live-in",
            "protection order",
        ],
        source="PWDVA 2005 covers women in live-in relationships; they can seek protection orders, residence orders, monetary relief"
    ),

    GroundTruth(
        question="A consumer bought a defective car worth Rs 15 lakhs from an authorized dealer. The dealer refuses to replace or refund. Which consumer forum should the consumer approach and what remedies are available?",
        category="consumer",
        difficulty="multi_hop",
        required_keywords=["District", "Consumer", "Commission", "defective", "refund", "replacement", "compensation"],
        expected_sections=["Consumer Protection Act"],
        ground_truth_facts=[
            "District",
            "defective",
            "compensation",
        ],
        source="CPA 2019 — value ≤ 1 crore → District Commission; remedies include replace, refund, compensation"
    ),

    # ─── CATEGORY 8: PROPERTY & PROCEDURAL LAW ──────────────────────────

    GroundTruth(
        question="What is RERA and how does it protect homebuyers in India?",
        category="property",
        difficulty="intermediate",
        required_keywords=["RERA", "Real Estate", "Regulatory Authority", "homebuyer", "registration", "builder"],
        expected_sections=["RERA"],
        ground_truth_facts=[
            "Real Estate",
            "Regulatory Authority",
            "registration",
            "builder",
        ],
        source="Real Estate (Regulation and Development) Act, 2016 — mandatory project registration, protects homebuyers"
    ),

    GroundTruth(
        question="What is the right to free legal aid in India and who is entitled to it?",
        category="constitutional",
        difficulty="intermediate",
        required_keywords=["legal aid", "Article 39A", "Legal Services", "free", "weaker sections"],
        expected_sections=["Article 39A", "Legal Services Authorities Act"],
        ground_truth_facts=[
            "legal aid",
            "free",
        ],
        source="Article 39A + Legal Services Authorities Act 1987 — free legal aid for SC/ST, women, children, disabled, economically weaker"
    ),

    # ─── CATEGORY 9: SPECIFIC LEGAL SCENARIO ────────────────────────────

    GroundTruth(
        question="What is Section 498A of the IPC and why has it been controversial?",
        category="criminal",
        difficulty="advanced",
        required_keywords=["498A", "cruelty", "husband", "relatives", "dowry", "misuse"],
        expected_sections=["Section 498A", "IPC"],
        ground_truth_facts=[
            "cruelty",
            "husband",
            "relatives",
            "dowry",
        ],
        source="IPC 498A — cruelty by husband or relatives; controversial due to alleged misuse in marital disputes"
    ),

    GroundTruth(
        question="What is anticipatory bail under Indian law and when can it be granted?",
        category="procedural",
        difficulty="intermediate",
        required_keywords=["anticipatory bail", "arrest", "non-bailable", "Section 438", "High Court", "Sessions Court"],
        expected_sections=["Section 438", "CrPC"],
        ground_truth_facts=[
            "anticipatory bail",
            "arrest",
            "non-bailable",
        ],
        source="CrPC Section 438 — anticipatory bail for apprehension of arrest in non-bailable offence; granted by Sessions/HC"
    ),

]


# ══════════════════════════════════════════════════════════════════════════════
# ACCURACY EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    """Normalize text for comparison — lowercase, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def keyword_match(answer: str, keywords: List[str]) -> Tuple[List[str], List[str]]:
    """Check which keywords appear in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched = []
    missed = []
    for kw in keywords:
        if kw.lower() in answer_lower:
            matched.append(kw)
        else:
            missed.append(kw)
    return matched, missed


def section_match(answer: str, sections: List[str]) -> Tuple[List[str], List[str]]:
    """Check which statute sections are cited in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched = []
    missed = []
    for sec in sections:
        # Flexible matching: "Section 302" or "S. 302" or "Sec. 302" or "302"
        sec_lower = sec.lower()
        # Try exact match first
        if sec_lower in answer_lower:
            matched.append(sec)
        # Try just the number if it's "Section XXX"
        elif re.search(r'section\s*' + re.escape(sec_lower.replace('section ', '').strip()), answer_lower):
            matched.append(sec)
        # Try abbreviation
        elif sec_lower.replace('section ', 's. ') in answer_lower:
            matched.append(sec)
        else:
            missed.append(sec)
    return matched, missed


def fact_match(answer: str, facts: List[str]) -> Tuple[List[str], List[str]]:
    """Check which factual assertions appear in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched = []
    missed = []
    for fact in facts:
        if fact.lower() in answer_lower:
            matched.append(fact)
        else:
            missed.append(fact)
    return matched, missed


def compute_composite_score(kw_score: float, sec_score: float, fact_score: float) -> float:
    """
    Weighted composite:
      - Keyword Hit Rate:       30%
      - Section Citation:       30%
      - Factual Accuracy:       40%
    """
    return 0.30 * kw_score + 0.30 * sec_score + 0.40 * fact_score


# ══════════════════════════════════════════════════════════════════════════════
# QUERY ENGINE — SENDS QUESTIONS TO LIVE RAG
# ══════════════════════════════════════════════════════════════════════════════

def query_rag(question: str, session_id: str, user_id: str) -> Dict[str, Any]:
    """Send a question to the live RAG system and return the response + timing."""
    payload = {
        "question": question,
        "session_id": session_id,
        "user_id": user_id,
    }
    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/api/query",
            json=payload,
            timeout=TIMEOUT,
        )
        latency = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            # API returns: {"response": {"answer": "...", "confidence": ..., "sources": [...], ...}}
            inner = data.get("response", data)
            if isinstance(inner, dict):
                answer_text = str(inner.get("answer", ""))
                confidence = inner.get("confidence", 0.0)
                sources = inner.get("sources", [])
                from_cache = inner.get("from_cache", False)
                strategy = inner.get("query_type", inner.get("strategy", "unknown"))
            else:
                answer_text = str(inner)
                confidence = 0.0
                sources = []
                from_cache = False
                strategy = "unknown"
            return {
                "success": True,
                "answer": answer_text,
                "latency": latency,
                "confidence": confidence if confidence else 0.0,
                "sources_count": len(sources) if isinstance(sources, list) else 0,
                "from_cache": from_cache if from_cache else False,
                "strategy": strategy if strategy else "unknown",
                "raw": data,
            }
        else:
            return {
                "success": False,
                "answer": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "latency": latency,
                "confidence": 0.0,
                "sources_count": 0,
                "from_cache": False,
                "strategy": "error",
                "raw": {},
            }
    except Exception as e:
        latency = time.time() - start
        return {
            "success": False,
            "answer": f"ERROR: {str(e)}",
            "latency": latency,
            "confidence": 0.0,
            "sources_count": 0,
            "from_cache": False,
            "strategy": "error",
            "raw": {},
        }


# ══════════════════════════════════════════════════════════════════════════════
# SCORING: EVALUATE A SINGLE RESULT
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_result(gt: GroundTruth, rag_result: Dict[str, Any]) -> QueryResult:
    """Evaluate a RAG response against ground truth."""
    answer = rag_result["answer"]

    # Keyword matching
    kw_matched, kw_missed = keyword_match(answer, gt.required_keywords)
    kw_total = len(gt.required_keywords)
    kw_score = len(kw_matched) / kw_total if kw_total > 0 else 1.0

    # Section citation matching
    sec_matched, sec_missed = section_match(answer, gt.expected_sections)
    sec_total = len(gt.expected_sections)
    sec_score = len(sec_matched) / sec_total if sec_total > 0 else 1.0

    # Factual accuracy matching
    fact_matched, fact_missed = fact_match(answer, gt.ground_truth_facts)
    fact_total = len(gt.ground_truth_facts)
    fact_score = len(fact_matched) / fact_total if fact_total > 0 else 1.0

    # Composite
    composite = compute_composite_score(kw_score, sec_score, fact_score)

    return QueryResult(
        question=gt.question,
        answer=answer,
        latency_sec=rag_result["latency"],
        confidence=rag_result["confidence"],
        sources_count=rag_result["sources_count"],
        from_cache=rag_result["from_cache"],
        strategy=rag_result["strategy"],
        keyword_hits=len(kw_matched),
        keyword_total=kw_total,
        keyword_score=kw_score,
        section_hits=len(sec_matched),
        section_total=sec_total,
        section_score=sec_score,
        fact_hits=len(fact_matched),
        fact_total=fact_total,
        fact_score=fact_score,
        composite_score=composite,
        category=gt.category,
        difficulty=gt.difficulty,
        matched_keywords=kw_matched,
        missed_keywords=kw_missed,
        matched_sections=sec_matched,
        missed_sections=sec_missed,
        matched_facts=fact_matched,
        missed_facts=fact_missed,
    )


# ══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════════════════════════════════════

def grade_emoji(score: float) -> str:
    if score >= 0.9:
        return "🟢"
    elif score >= 0.7:
        return "🟡"
    elif score >= 0.5:
        return "🟠"
    else:
        return "🔴"


def grade_letter(score: float) -> str:
    if score >= 0.9:
        return "A+"
    elif score >= 0.8:
        return "A"
    elif score >= 0.7:
        return "B"
    elif score >= 0.6:
        return "C"
    elif score >= 0.5:
        return "D"
    else:
        return "F"


def print_per_question_report(results: List[QueryResult]):
    """Print detailed per-question analysis."""
    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  PER-QUESTION DETAILED RESULTS{C.RESET}")
    print(f"{'='*90}\n")

    for i, r in enumerate(results, 1):
        emoji = grade_emoji(r.composite_score)
        grade = grade_letter(r.composite_score)
        cache_tag = f" {C.DIM}[CACHED]{C.RESET}" if r.from_cache else ""

        print(f"{C.BOLD}  Q{i:02d} [{r.category.upper()}/{r.difficulty.upper()}]{C.RESET}{cache_tag}")
        print(f"  {C.DIM}{r.question[:85]}{'...' if len(r.question)>85 else ''}{C.RESET}")
        print(f"  {emoji} Composite: {C.BOLD}{r.composite_score:.1%}{C.RESET}  (Grade: {grade})")
        print(f"     Keywords: {r.keyword_hits}/{r.keyword_total} ({r.keyword_score:.0%})"
              f"  | Sections: {r.section_hits}/{r.section_total} ({r.section_score:.0%})"
              f"  | Facts: {r.fact_hits}/{r.fact_total} ({r.fact_score:.0%})")
        print(f"     Latency: {r.latency_sec:.2f}s  |  Confidence: {r.confidence:.2f}"
              f"  |  Sources: {r.sources_count}  |  Strategy: {r.strategy}")

        if r.missed_keywords:
            print(f"     {C.RED}Missed keywords:{C.RESET} {', '.join(r.missed_keywords[:5])}")
        if r.missed_sections:
            print(f"     {C.RED}Missed sections:{C.RESET} {', '.join(r.missed_sections[:5])}")
        if r.missed_facts:
            print(f"     {C.RED}Missed facts:{C.RESET} {', '.join(r.missed_facts[:5])}")
        print()


def print_category_breakdown(results: List[QueryResult]):
    """Print accuracy breakdown by category."""
    categories: Dict[str, List[QueryResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  ACCURACY BY CATEGORY{C.RESET}")
    print(f"{'='*90}\n")
    print(f"  {'Category':<20} {'Count':>5} {'Kw%':>7} {'Sec%':>7} {'Fact%':>7} {'Composite':>10} {'Grade':>6}")
    print(f"  {'-'*20} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*10} {'-'*6}")

    for cat in sorted(categories.keys()):
        rs = categories[cat]
        avg_kw = statistics.mean([r.keyword_score for r in rs])
        avg_sec = statistics.mean([r.section_score for r in rs])
        avg_fact = statistics.mean([r.fact_score for r in rs])
        avg_comp = statistics.mean([r.composite_score for r in rs])
        grade = grade_letter(avg_comp)
        print(f"  {cat:<20} {len(rs):>5} {avg_kw:>6.0%} {avg_sec:>6.0%} {avg_fact:>6.0%} {avg_comp:>9.1%}  {grade:>5}")


def print_difficulty_breakdown(results: List[QueryResult]):
    """Print accuracy breakdown by difficulty."""
    difficulties: Dict[str, List[QueryResult]] = {}
    for r in results:
        difficulties.setdefault(r.difficulty, []).append(r)

    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  ACCURACY BY DIFFICULTY LEVEL{C.RESET}")
    print(f"{'='*90}\n")
    print(f"  {'Difficulty':<20} {'Count':>5} {'Kw%':>7} {'Sec%':>7} {'Fact%':>7} {'Composite':>10} {'Grade':>6}")
    print(f"  {'-'*20} {'-'*5} {'-'*7} {'-'*7} {'-'*7} {'-'*10} {'-'*6}")

    order = ["basic", "intermediate", "advanced", "multi_hop"]
    for diff in order:
        if diff not in difficulties:
            continue
        rs = difficulties[diff]
        avg_kw = statistics.mean([r.keyword_score for r in rs])
        avg_sec = statistics.mean([r.section_score for r in rs])
        avg_fact = statistics.mean([r.fact_score for r in rs])
        avg_comp = statistics.mean([r.composite_score for r in rs])
        grade = grade_letter(avg_comp)
        print(f"  {diff:<20} {len(rs):>5} {avg_kw:>6.0%} {avg_sec:>6.0%} {avg_fact:>6.0%} {avg_comp:>9.1%}  {grade:>5}")


def print_latency_report(results: List[QueryResult]):
    """Print latency statistics."""
    latencies = [r.latency_sec for r in results if not r.from_cache]
    cached_latencies = [r.latency_sec for r in results if r.from_cache]

    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  LATENCY ANALYSIS{C.RESET}")
    print(f"{'='*90}\n")

    if latencies:
        latencies_sorted = sorted(latencies)
        p50_idx = int(len(latencies_sorted) * 0.50)
        p95_idx = min(int(len(latencies_sorted) * 0.95), len(latencies_sorted) - 1)

        print(f"  {C.BOLD}Fresh Queries (non-cached):{C.RESET}  n={len(latencies)}")
        print(f"    Average:  {statistics.mean(latencies):.2f}s")
        print(f"    Median:   {statistics.median(latencies):.2f}s")
        print(f"    P50:      {latencies_sorted[p50_idx]:.2f}s")
        print(f"    P95:      {latencies_sorted[p95_idx]:.2f}s")
        print(f"    Min:      {min(latencies):.2f}s")
        print(f"    Max:      {max(latencies):.2f}s")
        if len(latencies) > 1:
            print(f"    Std Dev:  {statistics.stdev(latencies):.2f}s")
    else:
        print(f"  No fresh (non-cached) queries recorded.")

    if cached_latencies:
        print(f"\n  {C.BOLD}Cached Queries:{C.RESET}  n={len(cached_latencies)}")
        print(f"    Average:  {statistics.mean(cached_latencies):.2f}s")
        print(f"    Min:      {min(cached_latencies):.2f}s")
        print(f"    Max:      {max(cached_latencies):.2f}s")

    # Latency by category
    cat_latencies: Dict[str, List[float]] = {}
    for r in results:
        if not r.from_cache:
            cat_latencies.setdefault(r.category, []).append(r.latency_sec)

    if cat_latencies:
        print(f"\n  {C.BOLD}Latency by Category (non-cached):{C.RESET}")
        print(f"  {'Category':<20} {'Count':>5} {'Avg':>8} {'Min':>8} {'Max':>8}")
        print(f"  {'-'*20} {'-'*5} {'-'*8} {'-'*8} {'-'*8}")
        for cat in sorted(cat_latencies.keys()):
            lats = cat_latencies[cat]
            print(f"  {cat:<20} {len(lats):>5} {statistics.mean(lats):>7.2f}s {min(lats):>7.2f}s {max(lats):>7.2f}s")


def print_summary(results: List[QueryResult], total_time: float):
    """Print executive summary."""
    total = len(results)
    avg_composite = statistics.mean([r.composite_score for r in results])
    avg_kw = statistics.mean([r.keyword_score for r in results])
    avg_sec = statistics.mean([r.section_score for r in results])
    avg_fact = statistics.mean([r.fact_score for r in results])

    excellent = sum(1 for r in results if r.composite_score >= 0.9)
    good = sum(1 for r in results if 0.7 <= r.composite_score < 0.9)
    fair = sum(1 for r in results if 0.5 <= r.composite_score < 0.7)
    poor = sum(1 for r in results if r.composite_score < 0.5)

    overall_grade = grade_letter(avg_composite)

    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  ╔══════════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  ║          LAW-GPT v3.0 — ACCURACY & LATENCY REPORT           ║{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  ╚══════════════════════════════════════════════════════════════╝{C.RESET}")
    print(f"{'='*90}\n")

    print(f"  {C.BOLD}OVERALL ACCURACY{C.RESET}")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Composite Score:        {C.BOLD}{avg_composite:.1%}{C.RESET}  (Grade: {C.BOLD}{overall_grade}{C.RESET})")
    print(f"  Keyword Hit Rate:       {avg_kw:.1%}")
    print(f"  Section Citation Acc:   {avg_sec:.1%}")
    print(f"  Factual Accuracy:       {avg_fact:.1%}")
    print()
    print(f"  {C.BOLD}SCORE DISTRIBUTION{C.RESET}")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  🟢 Excellent (≥90%):    {excellent}/{total}  ({excellent/total:.0%})")
    print(f"  🟡 Good     (70-89%):   {good}/{total}  ({good/total:.0%})")
    print(f"  🟠 Fair     (50-69%):   {fair}/{total}  ({fair/total:.0%})")
    print(f"  🔴 Poor     (<50%):     {poor}/{total}  ({poor/total:.0%})")
    print()
    print(f"  {C.BOLD}TEST META{C.RESET}")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  Total Questions:        {total}")
    print(f"  Total Test Duration:    {total_time:.1f}s")
    print(f"  Avg Time/Question:      {total_time/total:.1f}s")
    print(f"  Date:                   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend:                {BASE_URL}")
    print()


def save_json_report(results: List[QueryResult], total_time: float, filepath: str):
    """Save machine-readable JSON report."""
    avg_composite = statistics.mean([r.composite_score for r in results])
    latencies = [r.latency_sec for r in results if not r.from_cache]

    report = {
        "test_info": {
            "name": "LAW-GPT v3.0 Accuracy & Latency Ground Truth Test",
            "date": datetime.now().isoformat(),
            "backend_url": BASE_URL,
            "total_questions": len(results),
            "total_duration_sec": round(total_time, 2),
        },
        "overall_accuracy": {
            "composite_score": round(avg_composite, 4),
            "keyword_hit_rate": round(statistics.mean([r.keyword_score for r in results]), 4),
            "section_citation_accuracy": round(statistics.mean([r.section_score for r in results]), 4),
            "factual_accuracy": round(statistics.mean([r.fact_score for r in results]), 4),
            "grade": grade_letter(avg_composite),
        },
        "latency": {
            "fresh_queries": {
                "count": len(latencies),
                "avg_sec": round(statistics.mean(latencies), 3) if latencies else 0,
                "median_sec": round(statistics.median(latencies), 3) if latencies else 0,
                "min_sec": round(min(latencies), 3) if latencies else 0,
                "max_sec": round(max(latencies), 3) if latencies else 0,
                "p95_sec": round(sorted(latencies)[min(int(len(latencies)*0.95), len(latencies)-1)], 3) if latencies else 0,
            },
        },
        "per_question": [],
    }

    for r in results:
        report["per_question"].append({
            "question": r.question,
            "category": r.category,
            "difficulty": r.difficulty,
            "composite_score": round(r.composite_score, 4),
            "keyword_score": round(r.keyword_score, 4),
            "section_score": round(r.section_score, 4),
            "fact_score": round(r.fact_score, 4),
            "latency_sec": round(r.latency_sec, 3),
            "confidence": r.confidence,
            "sources_count": r.sources_count,
            "from_cache": r.from_cache,
            "strategy": r.strategy,
            "missed_keywords": r.missed_keywords,
            "missed_sections": r.missed_sections,
            "missed_facts": r.missed_facts,
            "answer_preview": r.answer[:300],
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  {C.GREEN}JSON report saved → {filepath}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.CYAN}  LAW-GPT v3.0 — COMPREHENSIVE ACCURACY & LATENCY GROUND TRUTH TEST{C.RESET}")
    print(f"{'='*90}")
    print(f"  Backend:    {BASE_URL}")
    print(f"  Questions:  {len(GROUND_TRUTH_QUESTIONS)}")
    print(f"  Session:    {SESSION_ID}")
    print(f"  Started:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*90}\n")

    # ── Step 0: Health check ─────────────────────────────────────────────
    print(f"  {C.YELLOW}[0/25] Checking backend health...{C.RESET}", end=" ", flush=True)
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=30)
        if health.status_code == 200:
            print(f"{C.GREEN}HEALTHY ✓{C.RESET}")
        else:
            print(f"{C.RED}UNHEALTHY (HTTP {health.status_code}) — aborting{C.RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{C.RED}UNREACHABLE ({e}) — aborting{C.RESET}")
        sys.exit(1)

    # ── Step 1: Run all questions ────────────────────────────────────────
    results: List[QueryResult] = []
    total_start = time.time()

    for idx, gt in enumerate(GROUND_TRUTH_QUESTIONS, 1):
        tag = f"[{idx:02d}/{len(GROUND_TRUTH_QUESTIONS)}]"
        short_q = gt.question[:65] + ("..." if len(gt.question) > 65 else "")
        print(f"  {C.YELLOW}{tag}{C.RESET} {C.DIM}{gt.category}/{gt.difficulty}{C.RESET} — {short_q}", end=" ", flush=True)

        # Use a UNIQUE session_id per question to avoid conversation memory contamination
        isolated_session = f"accuracy_{uuid.uuid4().hex[:12]}"
        rag_result = query_rag(gt.question, isolated_session, USER_ID)

        if rag_result["success"]:
            result = evaluate_result(gt, rag_result)
            results.append(result)
            emoji = grade_emoji(result.composite_score)
            print(f"→ {emoji} {result.composite_score:.0%} ({result.latency_sec:.1f}s)")
        else:
            print(f"→ {C.RED}FAILED{C.RESET} ({rag_result['latency']:.1f}s) — {rag_result['answer'][:60]}")
            # Add a zero-score result so it counts
            results.append(QueryResult(
                question=gt.question,
                answer=rag_result["answer"],
                latency_sec=rag_result["latency"],
                confidence=0.0,
                sources_count=0,
                from_cache=False,
                strategy="error",
                category=gt.category,
                difficulty=gt.difficulty,
            ))

    total_time = time.time() - total_start

    # ── Step 2: Print reports ────────────────────────────────────────────
    print_per_question_report(results)
    print_category_breakdown(results)
    print_difficulty_breakdown(results)
    print_latency_report(results)
    print_summary(results, total_time)

    # ── Step 3: Save JSON report ─────────────────────────────────────────
    _results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(_results_dir, exist_ok=True)
    json_path = os.path.join(_results_dir, f"accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_json_report(results, total_time, json_path)

    # Emit machine-readable score line (PASS = composite ≥ 55%)
    PASS_THRESHOLD = 0.55
    passed_count = sum(1 for r in results if r.composite_score >= PASS_THRESHOLD)
    print(f"\n  Score: {passed_count}/{len(results)} ({passed_count/len(results)*100:.0f}%)")

    print(f"\n{'='*90}")
    print(f"{C.BOLD}{C.GREEN}  TEST COMPLETE{C.RESET}")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
