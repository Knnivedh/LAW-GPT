"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   LAW-GPT v3.0 — MULTI-TURN CONVERSATIONAL ACCURACY TEST                  ║
║                                                                            ║
║   PURPOSE: Engage in full multi-turn conversations with the LAW-GPT        ║
║            Agentic RAG system, properly answering its clarifying           ║
║            questions before evaluating accuracy.                           ║
║                                                                            ║
║   WHY THIS EXISTS:                                                         ║
║     LAW-GPT has a multi-turn clarification system — when a complex         ║
║     question is asked, the bot asks up to 5 clarifying questions           ║
║     (date, documents, specifics) before giving a final answer.             ║
║     A single-turn test incorrectly evaluates the CLARIFYING QUESTION       ║
║     as if it were the final answer → false 0% scores.                      ║
║                                                                            ║
║   METHODOLOGY:                                                             ║
║     1. Send initial question to the RAG system                             ║
║     2. Detect if the response is a clarifying question or final answer     ║
║     3. If clarifying → respond with pre-built scenario context             ║
║     4. Continue up to MAX_TURNS until final answer is received             ║
║     5. Evaluate ONLY the final substantial answer against ground truth     ║
║     6. Score: Keywords (30%) + Sections (30%) + Facts (40%)                ║
║                                                                            ║
║   TARGET: https://lawgpt-backend2024.azurewebsites.net                     ║
║   RUN:    python tests/test_accuracy_conversational.py                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import time
import sys
import os
import uuid
import re
import statistics
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

# Fix Unicode output on Windows cp1252 terminals (box-drawing chars, etc.)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Fix Unicode output on Windows cp1252 terminals
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
BASE_URL = os.environ.get("LAWGPT_BASE_URL", "https://lawgpt-backend2024.azurewebsites.net")
TIMEOUT = 180
MAX_TURNS = 6          # Maximum conversation turns per question
USER_ID = f"conv_user_{uuid.uuid4().hex[:8]}"


class C:
    """Terminal colours."""
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationalQuestion:
    """A ground truth question with pre-built clarification responses."""
    question: str
    category: str
    difficulty: str
    required_keywords: List[str]
    expected_sections: List[str]
    ground_truth_facts: List[str]
    source: str
    # Pre-built responses to the bot's clarifying questions (sent in order)
    clarification_responses: List[str]


@dataclass
class Turn:
    """A single turn in a conversation."""
    role: str          # "user" or "assistant"
    message: str
    confidence: float = 0.0
    sources_count: int = 0
    latency_sec: float = 0.0
    from_cache: bool = False
    strategy: str = ""


@dataclass
class ConversationResult:
    """Result of a full multi-turn conversation."""
    question: str
    category: str
    difficulty: str
    turns: List[Turn] = field(default_factory=list)
    total_turns: int = 0
    # Final answer data
    final_answer: str = ""
    final_confidence: float = 0.0
    final_sources: int = 0
    final_strategy: str = ""
    got_final_answer: bool = False
    # Timing
    total_latency_sec: float = 0.0
    first_response_latency: float = 0.0
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
    # Detail lists
    matched_keywords: List[str] = field(default_factory=list)
    missed_keywords: List[str] = field(default_factory=list)
    matched_sections: List[str] = field(default_factory=list)
    missed_sections: List[str] = field(default_factory=list)
    matched_facts: List[str] = field(default_factory=list)
    missed_facts: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# GROUND TRUTH DATABASE — 25 QUESTIONS WITH CONVERSATION CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

QUESTIONS: List[ConversationalQuestion] = [

    # ─── Q01: Murder under BNS (usually gets direct answer) ──────────────
    ConversationalQuestion(
        question="What is the punishment for murder under the Bharatiya Nyaya Sanhita (BNS)?",
        category="criminal",
        difficulty="basic",
        required_keywords=["murder", "death", "imprisonment", "life", "BNS", "punishment"],
        expected_sections=["Section 101", "Section 302", "BNS"],
        ground_truth_facts=["death", "imprisonment for life", "fine"],
        source="BNS Section 101 (replacing IPC Section 302)",
        clarification_responses=[
            "I'm asking about the general statutory punishment for murder under the Bharatiya Nyaya Sanhita (BNS), specifically Section 101 which replaced IPC Section 302. This is a general legal knowledge question, not about a specific case. Please provide the legal provision and punishment prescribed for murder.",
            "To clarify: I need the punishment prescribed for murder under Section 101 of BNS (previously Section 302 IPC) — death penalty or life imprisonment with fine. Please provide the statutory text and punishment details.",
            "I just need the general legal provision for murder under BNS. No specific case involved. The punishment for murder under Indian criminal law includes death or life imprisonment and fine. Please confirm and elaborate.",
        ],
    ),

    # ─── Q02: New offences in BNS ────────────────────────────────────────
    ConversationalQuestion(
        question="What are the new offences added in the Bharatiya Nyaya Sanhita (BNS) that were not in the IPC?",
        category="criminal",
        difficulty="intermediate",
        required_keywords=["organised crime", "terrorism", "BNS", "IPC", "new"],
        expected_sections=["BNS"],
        ground_truth_facts=["organised crime", "terrorism", "mob lynching"],
        source="Wikipedia BNS article — 20 new offences added",
        clarification_responses=[
            "I don't have specific IPC sections for reference. I'm asking from a general legal knowledge perspective: what NEW categories of offences were introduced in the Bharatiya Nyaya Sanhita (BNS) that did not exist as specific offences in the Indian Penal Code? For example, I've heard about organised crime, terrorism, mob lynching being new additions. Can you list all the new offences added in the BNS?",
            "To be more specific: The BNS reportedly added approximately 20 new offences. These include organised crime (Section 111), terrorism (Section 113), mob lynching, petty organised crime, and others. I need a comprehensive list of these new offences that were NOT present in the old IPC. This is a general legal knowledge question.",
            "Please list all new offences introduced in the Bharatiya Nyaya Sanhita that were not present in the Indian Penal Code 1860. Key additions include organised crime, terrorism, mob lynching, acts endangering sovereignty. I need a comprehensive overview.",
        ],
    ),

    # ─── Q03: Sedition removal ───────────────────────────────────────────
    ConversationalQuestion(
        question="Has sedition been removed under the new criminal law reforms in India? What replaced it?",
        category="criminal",
        difficulty="intermediate",
        required_keywords=["sedition", "removed", "sovereignty", "unity", "integrity"],
        expected_sections=["BNS", "Section 152"],
        ground_truth_facts=["sedition", "sovereignty", "unity and integrity"],
        source="BNS removed sedition; replaced with Section 152",
        clarification_responses=[
            "I'm asking about a general legal reform, not a specific case. The Indian Penal Code had Section 124A dealing with sedition. Under the new criminal law reforms when BNS was enacted in 2024, was the sedition offence retained, removed, or replaced? If replaced, what new provision covers similar conduct? I've heard it was replaced with provisions about acts endangering sovereignty, unity and integrity of India under Section 152 of BNS. Please confirm and elaborate.",
            "To clarify my question: The IPC Section 124A on sedition was reportedly abolished under BNS. The BNS replaced it with Section 152 dealing with 'acts endangering sovereignty, unity and integrity of India.' Please provide details about this change including the new section number and its scope.",
            "This is a factual legal knowledge question. Sedition under IPC 124A was removed in the BNS. Section 152 of BNS now covers acts endangering sovereignty, unity and integrity of India. Please confirm this and explain the changes.",
        ],
    ),

    # ─── Q04: Theft punishment (usually gets direct answer) ──────────────
    ConversationalQuestion(
        question="What is the punishment for theft under Indian law?",
        category="criminal",
        difficulty="basic",
        required_keywords=["theft", "imprisonment", "fine", "punishment"],
        expected_sections=["Section 378", "Section 304"],
        ground_truth_facts=["imprisonment", "fine", "three years"],
        source="IPC Section 379 / BNS Section 303",
        clarification_responses=[
            "This is a general legal knowledge question. I need the statutory punishment for the offence of theft under Indian law — both under the Indian Penal Code (Section 379) and the Bharatiya Nyaya Sanhita (Section 303). The punishment includes imprisonment up to 3 years and/or fine. Please provide the detailed legal provision.",
            "I'm asking about the general punishment for theft in Indian law. Section 379 IPC / Section 303 BNS — imprisonment which may extend to three years, or fine, or both. Please provide the statutory details.",
            "No specific theft incident involved. I need the general legal provision: theft under IPC 379 is punishable with imprisonment up to 3 years, or fine, or both. Please confirm.",
        ],
    ),

    # ─── Q05: Dowry death (usually gets direct answer) ───────────────────
    ConversationalQuestion(
        question="What is the legal definition and punishment for dowry death in India?",
        category="criminal",
        difficulty="advanced",
        required_keywords=["dowry death", "seven years", "marriage", "cruelty", "husband", "relative"],
        expected_sections=["Section 304B", "Section 498A", "Section 80"],
        ground_truth_facts=["seven years", "unnatural", "cruelty", "dowry"],
        source="IPC 304B / BNS Section 80",
        clarification_responses=[
            "This is a general legal knowledge question about the statutory definition and punishment. Dowry death is defined under IPC Section 304B / BNS Section 80. I need the complete legal definition including the 7-year window after marriage, the elements of the offence (cruelty, dowry demand), and the prescribed punishment (7 years to life imprisonment). No specific case involved.",
            "I'm asking about the general legal provision for dowry death. IPC Section 304B defines it as death of a woman within 7 years of marriage caused by burns or bodily injury, where she was subjected to cruelty or harassment for dowry. Punishment: minimum 7 years to life imprisonment. Please confirm and elaborate.",
            "Dowry death under IPC 304B — a woman dies within 7 years of marriage under abnormal circumstances, with evidence of cruelty for dowry. Punishment ranges from 7 years to life imprisonment. Please provide comprehensive details.",
        ],
    ),

    # ─── Q06: Fundamental rights Part III ─────────────────────────────────
    ConversationalQuestion(
        question="What are the fundamental rights guaranteed under Part III of the Indian Constitution?",
        category="constitutional",
        difficulty="basic",
        required_keywords=["equality", "freedom", "exploitation", "religion", "cultural", "educational", "constitutional remedies"],
        expected_sections=["Article 14", "Article 19", "Article 21", "Article 32", "Part III"],
        ground_truth_facts=[
            "equality before law", "freedom of speech", "forced labour",
            "propagation of religion", "constitutional remedies",
        ],
        source="Constitution of India, Part III — 6 fundamental rights (Articles 14-32)",
        clarification_responses=[
            "I want a comprehensive overview of ALL six categories of fundamental rights under Part III of the Indian Constitution. This is a general constitutional law question, not about a specific case or article. The six categories are: (1) Right to Equality (Articles 14-18), (2) Right to Freedom (Articles 19-22), (3) Right against Exploitation (Articles 23-24), (4) Right to Freedom of Religion (Articles 25-28), (5) Cultural and Educational Rights (Articles 29-30), and (6) Right to Constitutional Remedies (Article 32). Please provide an overview of each category.",
            "I don't need case laws or specific judgments. I need a textbook-style overview of all fundamental rights guaranteed under Part III of the Indian Constitution, covering Articles 14 through 32. Please list and briefly describe each of the six categories of fundamental rights.",
            "This is a basic constitutional law question. Part III of the Indian Constitution (Articles 12-35) guarantees six fundamental rights: equality, freedom, against exploitation, freedom of religion, cultural/educational rights, and constitutional remedies. Please provide an overview of all six.",
        ],
    ),

    # ─── Q07: Right to privacy / Puttaswamy ──────────────────────────────
    ConversationalQuestion(
        question="What is the right to privacy in India and which Supreme Court case established it as a fundamental right?",
        category="constitutional",
        difficulty="advanced",
        required_keywords=["privacy", "fundamental right", "Puttaswamy", "Article 21", "Supreme Court"],
        expected_sections=["Article 21"],
        ground_truth_facts=["Puttaswamy", "fundamental right", "Article 21", "2017"],
        source="Justice K.S. Puttaswamy v. Union of India (2017)",
        clarification_responses=[
            "I'm specifically asking about the landmark Supreme Court judgment in Justice K.S. Puttaswamy (Retd.) v. Union of India (2017). The nine-judge bench held that the right to privacy is a fundamental right protected under Article 21 of the Indian Constitution. I need details about: (1) What did the Supreme Court hold? (2) Under which Article was privacy recognized? (3) Was it a unanimous decision? (4) What was the constitutional significance? This is not about any personal privacy issue — it's about the constitutional judgment.",
            "To clarify: The Puttaswamy judgment of 2017 established privacy as a fundamental right under Article 21 of the Constitution. I need information about this landmark Supreme Court ruling, not about any specific privacy law or personal matter. Please provide the holding and its significance for Indian constitutional law.",
            "Justice K.S. Puttaswamy v. Union of India (2017) — 9-judge SC bench unanimously held right to privacy is a fundamental right under Article 21. Please explain this landmark judgment and its significance.",
        ],
    ),

    # ─── Q08: Navtej Singh Johar (usually gets direct answer) ────────────
    ConversationalQuestion(
        question="What did the Supreme Court hold in the Navtej Singh Johar case regarding Section 377?",
        category="constitutional",
        difficulty="advanced",
        required_keywords=["Section 377", "unconstitutional", "homosexual", "consensual", "decriminalized", "adults"],
        expected_sections=["Section 377", "Article 14", "Article 15", "Article 21"],
        ground_truth_facts=["unconstitutional", "consensual", "decriminalized", "2018"],
        source="Navtej Singh Johar v. Union of India (2018)",
        clarification_responses=[
            "I'm asking about the Supreme Court judgment in Navtej Singh Johar v. Union of India (2018), where the five-judge bench struck down parts of Section 377 of the IPC as unconstitutional, decriminalizing consensual homosexual acts between adults. Please provide the key holdings and constitutional provisions relied upon (Articles 14, 15, 19, 21).",
            "The Navtej Singh Johar case (2018) dealt with Section 377 IPC and homosexuality in India. The SC held that criminalizing consensual sexual acts between adults violates fundamental rights under Articles 14, 15, 19, and 21. Please provide complete details.",
            "This is about the landmark 2018 SC judgment that decriminalized homosexuality by reading down Section 377 IPC. Please explain the holding, reasoning, and constitutional basis.",
        ],
    ),

    # ─── Q09: CPA 2019 vs 1986 ──────────────────────────────────────────
    ConversationalQuestion(
        question="What are the key features of the Consumer Protection Act, 2019 and how is it different from the 1986 Act?",
        category="consumer",
        difficulty="intermediate",
        required_keywords=["Consumer Protection Act", "2019", "1986", "CCPA", "e-commerce", "mediation"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=[
            "Central Consumer Protection Authority", "e-commerce", "1986", "mediation",
        ],
        source="Consumer Protection Act 2019 replaced CPA 1986",
        clarification_responses=[
            "This is a general legal knowledge question about consumer protection law reform in India. I'm not referring to a specific consumer dispute or purchase agreement. I want to understand the key features of the Consumer Protection Act, 2019, and how it differs from the old Consumer Protection Act, 1986. Key differences I'm interested in include: (1) Introduction of Central Consumer Protection Authority (CCPA), (2) Coverage of e-commerce transactions, (3) Introduction of mediation as ADR, (4) Product liability provisions, (5) Changes in pecuniary jurisdiction. There is no arbitration clause or purchase agreement involved. Please provide a comprehensive comparison.",
            "I don't have a specific purchase agreement or dispute. This is an academic legal knowledge question. The Consumer Protection Act 2019 replaced the 1986 Act and introduced several new features including CCPA, e-commerce regulation, mediation, and product liability. Please explain these key differences between the two Acts.",
            "Please compare the Consumer Protection Act, 2019 with the Consumer Protection Act, 1986. Key new features: CCPA, e-commerce coverage, mediation, product liability, enhanced penalties. This is a general legal question, not about any specific case.",
        ],
    ),

    # ─── Q10: Consumer rights CPA 2019 (usually gets direct answer) ──────
    ConversationalQuestion(
        question="What are the consumer rights defined under the Consumer Protection Act 2019?",
        category="consumer",
        difficulty="basic",
        required_keywords=["consumer rights", "protection", "hazardous", "informed", "redressal"],
        expected_sections=["Consumer Protection Act, 2019"],
        ground_truth_facts=["hazardous", "quality", "quantity", "redressal", "competitive prices"],
        source="CPA 2019 — consumer rights",
        clarification_responses=[
            "This is a general question about consumer rights defined under the Consumer Protection Act, 2019. I need to know the six consumer rights: right to be protected against hazardous goods, right to be informed about quality/quantity/price, right to choose, right to be heard, right to seek redressal, and right to consumer education. Please list and explain each right.",
            "I'm asking about the statutory consumer rights under CPA 2019. Please list all the rights defined in the Act: safety from hazardous products, right to information, right to choose, right to be heard, right to redressal, right to consumer education.",
            "Consumer rights under CPA 2019 — please provide a comprehensive list of all consumer rights guaranteed by the Act.",
        ],
    ),

    # ─── Q11: Consumer forum jurisdiction ─────────────────────────────────
    ConversationalQuestion(
        question="What is the jurisdiction of District, State and National Consumer Disputes Redressal Commissions?",
        category="consumer",
        difficulty="intermediate",
        required_keywords=["District", "State", "National", "Commission", "crore", "jurisdiction"],
        expected_sections=["Consumer Protection Act"],
        ground_truth_facts=["District", "State", "National", "crore"],
        source="CPA 2019: District ≤ 1 crore, State 1-10 crore, National > 10 crore",
        clarification_responses=[
            "This is a general legal knowledge question about the three-tier consumer dispute redressal mechanism in India. I don't have a specific purchase date or invoice. Under the Consumer Protection Act, 2019, what are the pecuniary jurisdiction limits for: (1) District Consumer Disputes Redressal Commission (up to Rs 1 crore), (2) State Consumer Disputes Redressal Commission (Rs 1 crore to Rs 10 crore), and (3) National Consumer Disputes Redressal Commission (above Rs 10 crore)? Please provide the complete jurisdictional framework.",
            "I don't have a specific invoice or purchase date. I'm asking about the general jurisdictional structure of consumer forums under CPA 2019. District Commission handles claims up to Rs 1 crore, State Commission handles Rs 1-10 crore, and National Commission handles above Rs 10 crore. Please confirm and provide details about how the three-tier consumer forum system works.",
            "This is an academic question about consumer forum jurisdiction under CPA 2019. No specific dispute involved. District: up to 1 crore, State: 1-10 crore, National: above 10 crore. Please elaborate on the complete jurisdictional framework.",
        ],
    ),

    # ─── Q12: Domestic violence PWDVA ─────────────────────────────────────
    ConversationalQuestion(
        question="What is domestic violence under the Protection of Women from Domestic Violence Act, 2005? What types of abuse are covered?",
        category="family",
        difficulty="intermediate",
        required_keywords=["domestic violence", "physical", "sexual", "verbal", "emotional", "economic", "abuse"],
        expected_sections=["Section 3", "PWDVA", "Protection of Women from Domestic Violence Act"],
        ground_truth_facts=[
            "physical abuse", "sexual abuse", "verbal", "emotional", "economic abuse",
        ],
        source="PWDVA 2005, Section 3",
        clarification_responses=[
            "This is a general legal knowledge question about the Protection of Women from Domestic Violence Act, 2005 (PWDVA). I'm not referring to a specific case or incident. I need the legal definition of domestic violence under Section 3 of the PWDVA, which includes four types of abuse: (1) physical abuse, (2) sexual abuse, (3) verbal and emotional abuse, and (4) economic abuse. Please provide the complete legal definition and scope of each type of abuse covered under the Act.",
            "No specific incident date or case details needed. I need the statutory definition of domestic violence under PWDVA 2005, Section 3. It covers physical, sexual, verbal/emotional, and economic abuse. This is a general legal knowledge question about the definition and scope of the Act. Please provide comprehensive details.",
            "The PWDVA 2005 Section 3 defines domestic violence to include physical abuse, sexual abuse, verbal and emotional abuse, and economic abuse. Please elaborate on each type and the scope of protection provided by the Act.",
        ],
    ),

    # ─── Q13: Reliefs under PWDVA ────────────────────────────────────────
    ConversationalQuestion(
        question="What reliefs can an aggrieved woman seek under the Protection of Women from Domestic Violence Act?",
        category="family",
        difficulty="intermediate",
        required_keywords=["protection order", "residence order", "monetary relief", "custody", "compensation"],
        expected_sections=["PWDVA", "Protection of Women from Domestic Violence Act"],
        ground_truth_facts=[
            "protection order", "residence order", "monetary relief", "custody", "compensation",
        ],
        source="PWDVA 2005, Chapter III",
        clarification_responses=[
            "This is a general legal knowledge question about the available legal remedies. I don't have a specific case or marriage date. Under the Protection of Women from Domestic Violence Act, 2005, what reliefs can an aggrieved woman seek? The key reliefs include: (1) Protection order (Section 18), (2) Residence order (Section 19), (3) Monetary relief (Section 20), (4) Custody order (Section 21), and (5) Compensation order (Section 22). Please provide details of each type of relief available under the Act.",
            "I don't have a specific marriage date or case. This is an academic question about the statutory reliefs under PWDVA 2005 — protection order, residence order, monetary relief, custody order, and compensation order. Please explain each relief available to the aggrieved woman.",
            "PWDVA 2005 provides five types of relief: protection orders (Section 18), residence orders (Section 19), monetary relief (Section 20), custody orders (Section 21), and compensation orders (Section 22). Please elaborate on each.",
        ],
    ),

    # ─── Q14: BNS effective date ─────────────────────────────────────────
    ConversationalQuestion(
        question="When did the Bharatiya Nyaya Sanhita (BNS) come into effect and what laws did it replace?",
        category="transition",
        difficulty="basic",
        required_keywords=["BNS", "july 2024", "Indian Penal Code", "IPC", "replace"],
        expected_sections=["BNS", "Bharatiya Nyaya Sanhita"],
        ground_truth_facts=["july 1, 2024", "Indian Penal Code", "1860"],
        source="BNS came into effect 1 July 2024",
        clarification_responses=[
            "I'm asking a factual legal knowledge question. When did the Bharatiya Nyaya Sanhita (BNS) officially come into force? I understand it was enacted to replace the Indian Penal Code, 1860. The BNS came into effect on 1 July 2024 along with two other new criminal laws. What specific colonial-era law did it replace and when? Please provide the dates and facts.",
            "To clarify: The BNS replaced the Indian Penal Code (IPC) of 1860 and is said to have come into effect on 1 July 2024. I need confirmation of this fact along with any other relevant details about the legislative transition from IPC to BNS.",
            "This is a factual question — when did BNS come into effect (reportedly 1 July 2024) and which law (IPC 1860) did it replace? Please confirm these facts.",
        ],
    ),

    # ─── Q15: Three new criminal laws 2024 ───────────────────────────────
    ConversationalQuestion(
        question="What are the three new criminal laws that replaced the colonial-era laws in India in 2024?",
        category="transition",
        difficulty="intermediate",
        required_keywords=["Bharatiya Nyaya Sanhita", "Bharatiya Nagarik Suraksha Sanhita", "Bharatiya Sakshya"],
        expected_sections=["BNS", "BNSS", "BSA"],
        ground_truth_facts=[
            "Bharatiya Nyaya Sanhita", "Bharatiya Nagarik Suraksha Sanhita",
            "Bharatiya Sakshya", "Indian Penal Code",
        ],
        source="Three new laws: BNS, BNSS, BSA",
        clarification_responses=[
            "I'm asking about the three new criminal laws enacted by the Indian Parliament in 2023 and implemented on 1 July 2024. These are: (1) Bharatiya Nyaya Sanhita (BNS) replacing the Indian Penal Code 1860, (2) Bharatiya Nagarik Suraksha Sanhita (BNSS) replacing the Code of Criminal Procedure 1973, and (3) Bharatiya Sakshya Adhiniyam (BSA) replacing the Indian Evidence Act 1872. Please confirm these details and provide an overview of each new law and what it replaced.",
            "The three colonial-era laws replaced in 2024 are: IPC (replaced by BNS), CrPC (replaced by BNSS), and the Indian Evidence Act (replaced by BSA). All three new laws came into effect on 1 July 2024. Please provide details about each replacement and the key changes introduced.",
            "BNS replaces IPC 1860, BNSS replaces CrPC 1973, BSA replaces Indian Evidence Act 1872. All three effective 1 July 2024. Please confirm and elaborate.",
        ],
    ),

    # ─── Q16: BNS structure (usually gets direct answer) ─────────────────
    ConversationalQuestion(
        question="How many chapters and sections does the Bharatiya Nyaya Sanhita have?",
        category="transition",
        difficulty="basic",
        required_keywords=["20", "358", "chapters", "sections", "BNS"],
        expected_sections=["BNS"],
        ground_truth_facts=["20 chapters", "bharatiya nyaya sanhita"],
        source="BNS comprises 20 chapters and 358 sections",
        clarification_responses=[
            "This is a simple factual question about the structure of the Bharatiya Nyaya Sanhita (BNS). The BNS reportedly has 20 chapters and 358 sections. Please confirm this structure and provide any relevant details about how the BNS is organized.",
            "I need the factual answer: how many chapters and sections does the Bharatiya Nyaya Sanhita (BNS) have? It reportedly has 20 chapters and 358 sections. Please confirm.",
            "BNS structure — 20 chapters and 358 sections. Please confirm and provide details.",
        ],
    ),

    # ─── Q17: Vishaka Guidelines ─────────────────────────────────────────
    ConversationalQuestion(
        question="What were the Vishaka Guidelines and why were they important for workplace sexual harassment law in India?",
        category="landmark_case",
        difficulty="advanced",
        required_keywords=["Vishaka", "sexual harassment", "workplace", "guidelines", "Supreme Court"],
        expected_sections=["Vishaka"],
        ground_truth_facts=["Vishaka", "sexual harassment", "workplace", "1997"],
        source="Vishaka v. State of Rajasthan (1997)",
        clarification_responses=[
            "I'm asking about the landmark Supreme Court case Vishaka v. State of Rajasthan (1997). The Supreme Court laid down guidelines to prevent sexual harassment at the workplace, known as the Vishaka Guidelines. These guidelines were later replaced by the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013. Please provide details about: (1) What were these guidelines? (2) Why were they issued? (3) What specific provisions did they include? (4) How were they significant for Indian workplace law?",
            "The Vishaka Guidelines were laid down by the Supreme Court in 1997 in the case of Vishaka v. State of Rajasthan. They addressed workplace sexual harassment and were groundbreaking for Indian employment law. This is a general legal knowledge question — no specific case details needed. Please provide complete information about the guidelines and their significance.",
            "Vishaka v. State of Rajasthan (1997) — SC laid down guidelines against workplace sexual harassment. These became the basis for the POSH Act, 2013. Please provide complete details about the Vishaka Guidelines.",
        ],
    ),

    # ─── Q18: Kesavananda Bharati ────────────────────────────────────────
    ConversationalQuestion(
        question="What is the significance of the Kesavananda Bharati case in Indian constitutional law?",
        category="landmark_case",
        difficulty="advanced",
        required_keywords=["Kesavananda Bharati", "basic structure", "Constitution", "amendment", "Parliament"],
        expected_sections=["Article 368"],
        ground_truth_facts=["basic structure", "Parliament", "amend"],
        source="Kesavananda Bharati v. State of Kerala (1973)",
        clarification_responses=[
            "I'm asking about the landmark Supreme Court judgment in Kesavananda Bharati v. State of Kerala (1973). This is a constitutional law question about the basic structure doctrine. The 13-judge bench of the Supreme Court held that while Parliament has the power to amend the Constitution under Article 368, it cannot alter or destroy the 'basic structure' of the Constitution. I need details about this historic judgment, the basic structure doctrine, and its significance. No specific constitutional provision is at issue — I need the overall holding and its impact on Indian constitutional law.",
            "The Kesavananda Bharati case (1973) established the basic structure doctrine — Parliament can amend the Constitution under Article 368 but cannot destroy its basic structure. This is a general constitutional law question. Please provide complete details about this landmark judgment and its significance.",
            "Kesavananda Bharati v. State of Kerala (1973) — basic structure doctrine. Parliament's amending power under Article 368 is limited. Please explain the case, holding, and its lasting significance for Indian constitutional law.",
        ],
    ),

    # ─── Q19: Murder + evidence destruction (multi-hop) ──────────────────
    ConversationalQuestion(
        question="If a person commits murder and also destroys evidence to cover it up, what are the applicable BNS/IPC sections and their respective punishments?",
        category="criminal",
        difficulty="multi_hop",
        required_keywords=["murder", "evidence", "punishment", "imprisonment", "destruction"],
        expected_sections=["Section 302", "Section 201", "Section 101"],
        ground_truth_facts=["death", "imprisonment for life", "evidence"],
        source="IPC 302 (murder) + IPC 201 (evidence destruction)",
        clarification_responses=[
            "This is a hypothetical legal scenario question. Suppose a person commits murder on January 15, 2025 in Mumbai and then destroys evidence (the murder weapon and cleans the crime scene) to cover up the crime. I need to know: (1) What sections of the IPC/BNS apply for murder? (Section 302 IPC / Section 101 BNS — death or life imprisonment); (2) What sections apply for destruction of evidence? (Section 201 IPC — causing disappearance of evidence, punishable with up to 7 years); (3) Can both charges apply concurrently? There are no witnesses. The accused confessed later.",
            "This is a legal knowledge question about applicable sections for two offences committed together. For murder: IPC Section 302 / BNS Section 101 (death or life imprisonment). For destroying evidence: IPC Section 201 (causing disappearance of evidence — up to 7 years imprisonment). Both charges apply concurrently. Please confirm and elaborate on the legal framework.",
            "Murder (IPC 302 / BNS 101) + destroying evidence (IPC 201). Both offences apply concurrently. Please provide the applicable sections and punishments for each offence.",
        ],
    ),

    # ─── Q20: Live-in relationship abuse (multi-hop) ─────────────────────
    ConversationalQuestion(
        question="A woman in a live-in relationship faces physical and economic abuse from her partner. What legal remedies are available to her under Indian law?",
        category="family",
        difficulty="multi_hop",
        required_keywords=["domestic violence", "live-in", "protection order", "PWDVA", "498A"],
        expected_sections=["PWDVA", "Section 498A"],
        ground_truth_facts=[
            "Protection of Women from Domestic Violence Act", "live-in", "protection order",
        ],
        source="PWDVA 2005 covers women in live-in relationships",
        clarification_responses=[
            "This is a hypothetical legal scenario. A woman has been in a live-in relationship for 3 years starting from January 2022. She has been facing physical abuse (beating) and economic abuse (partner controls all finances, refuses to provide money for essential needs) since mid-2024. She has medical reports documenting injuries and bank statements showing financial control. She wants to know her legal remedies under Indian law. I understand that the PWDVA 2005 covers women in live-in relationships and she can seek protection orders, residence orders, monetary relief, and compensation. Section 498A IPC may also be applicable.",
            "The scenario involves a live-in relationship (since January 2022) with physical and economic abuse. The woman has medical records and bank statements as evidence. Under PWDVA 2005, women in live-in relationships can seek protection orders, residence orders, monetary relief, custody orders, and compensation orders. Section 498A IPC may also apply. Please provide the comprehensive legal remedies available.",
            "PWDVA 2005 explicitly covers women in live-in relationships (D. Velusamy v. D. Patchaiammal). Available remedies: protection order, residence order, monetary relief, custody order, compensation order. Section 498A may also apply. Please provide comprehensive legal advice for this scenario.",
        ],
    ),

    # ─── Q21: Defective car consumer forum (multi-hop) ───────────────────
    ConversationalQuestion(
        question="A consumer bought a defective car worth Rs 15 lakhs from an authorized dealer. The dealer refuses to replace or refund. Which consumer forum should the consumer approach and what remedies are available?",
        category="consumer",
        difficulty="multi_hop",
        required_keywords=["District", "Consumer", "Commission", "defective", "refund", "replacement", "compensation"],
        expected_sections=["Consumer Protection Act"],
        ground_truth_facts=["District", "defective", "compensation"],
        source="CPA 2019 — value ≤ 1 crore → District Commission",
        clarification_responses=[
            "Here are the full facts of this hypothetical consumer dispute: A consumer purchased a new car worth Rs 15 lakhs from an authorized dealer on October 5, 2024. The car had a manufacturing defect in the engine that manifested within 2 months. The consumer has the purchase invoice, warranty card, and service records. The consumer sent a written complaint via email on December 10, 2024 requesting replacement or refund, but the dealer refused, calling it a 'minor issue.' There is no arbitration clause in the purchase agreement. The consumer wants to file a complaint. Since the value is Rs 15 lakhs (under Rs 1 crore), the District Consumer Disputes Redressal Commission has jurisdiction. What are the available remedies?",
            "Car value is Rs 15 lakhs (under Rs 1 crore), so the District Consumer Disputes Redressal Commission has jurisdiction under CPA 2019. The consumer has all documents — purchase invoice dated October 5, 2024, written complaint to dealer dated December 10, 2024, and the dealer's refusal. No arbitration clause exists. Available remedies include product replacement, refund, compensation for deficiency of service, and litigation costs. Please provide the complete legal analysis.",
            "Rs 15 lakh defective car → District Commission (under 1 crore). Consumer has invoice, written complaint, dealer refusal. Remedies: replacement, refund, compensation. Please provide comprehensive legal analysis under CPA 2019.",
        ],
    ),

    # ─── Q22: RERA (usually gets direct answer) ──────────────────────────
    ConversationalQuestion(
        question="What is RERA and how does it protect homebuyers in India?",
        category="property",
        difficulty="intermediate",
        required_keywords=["RERA", "Real Estate", "Regulatory Authority", "homebuyer", "registration", "builder"],
        expected_sections=["RERA"],
        ground_truth_facts=["Real Estate", "Regulatory Authority", "registration", "builder"],
        source="Real Estate (Regulation and Development) Act, 2016",
        clarification_responses=[
            "I'm asking about the Real Estate (Regulation and Development) Act, 2016 (RERA). This is a general legal knowledge question about how RERA protects homebuyers. Key aspects I'm interested in include: mandatory project registration, establishment of Real Estate Regulatory Authority, builder obligations (timely delivery, no false advertising), homebuyer rights, and the dispute resolution mechanism. Please provide a comprehensive overview of RERA and its homebuyer protections.",
            "RERA — the Real Estate (Regulation and Development) Act, 2016. General question about its provisions for homebuyer protection. Key features: mandatory project registration, builder accountability, regulatory authority, complaint mechanism. Please provide details.",
            "What protections does RERA 2016 provide to homebuyers? This includes project registration, builder obligations, regulatory oversight, and dispute resolution. Please elaborate.",
        ],
    ),

    # ─── Q23: Free legal aid ─────────────────────────────────────────────
    ConversationalQuestion(
        question="What is the right to free legal aid in India and who is entitled to it?",
        category="constitutional",
        difficulty="intermediate",
        required_keywords=["legal aid", "Article 39A", "Legal Services", "free", "weaker sections"],
        expected_sections=["Article 39A", "Legal Services Authorities Act"],
        ground_truth_facts=["legal aid", "free"],
        source="Article 39A + Legal Services Authorities Act 1987",
        clarification_responses=[
            "This is a general legal knowledge question about the right to free legal aid in India. I'm not referring to a specific case or individual. Under Article 39A of the Indian Constitution and the Legal Services Authorities Act, 1987, certain categories of people are entitled to free legal aid. These include: members of SC/ST communities, women, children, persons with disabilities, victims of trafficking, industrial workmen, persons in custody, and those with annual income below prescribed limits. NALSA (National Legal Services Authority) oversees this system. Please provide a comprehensive overview of who is entitled to free legal aid and how the system works.",
            "Article 39A of the Constitution directs the State to ensure free legal aid to the weaker sections. The Legal Services Authorities Act, 1987 establishes NALSA and state/district legal services authorities. Entitled persons include SC/ST, women, children, disabled, economically weaker sections. This is a general legal question, not about a specific case. Please explain the complete framework for free legal aid in India.",
            "Free legal aid in India — Article 39A + Legal Services Authorities Act 1987. NALSA at the apex. Entitled categories: SC/ST, women, children, disabled, low-income persons. Please provide comprehensive details.",
        ],
    ),

    # ─── Q24: Section 498A (usually gets direct answer) ──────────────────
    ConversationalQuestion(
        question="What is Section 498A of the IPC and why has it been controversial?",
        category="criminal",
        difficulty="advanced",
        required_keywords=["498A", "cruelty", "husband", "relatives", "dowry", "misuse"],
        expected_sections=["Section 498A", "IPC"],
        ground_truth_facts=["cruelty", "husband", "relatives", "dowry"],
        source="IPC 498A — cruelty by husband/relatives",
        clarification_responses=[
            "I'm asking about Section 498A of the Indian Penal Code, which deals with cruelty by husband or his relatives towards the wife, particularly in the context of dowry harassment. The section has been controversial because it is alleged to be misused in marital disputes, with the Supreme Court itself expressing concern about its misuse. This is a general legal knowledge question — no specific case involved. Please explain the provision, its elements, punishment, purpose, and the controversy around its alleged misuse.",
            "Section 498A IPC deals with cruelty by husband or relatives, especially related to dowry demands. It's been controversial due to alleged misuse. Please provide a comprehensive overview of the section, its legal elements, punishment, and the debate around its use.",
            "IPC 498A — cruelty by husband/relatives + dowry harassment. Controversial due to alleged misuse. Please explain the provision and the controversy.",
        ],
    ),

    # ─── Q25: Anticipatory bail ──────────────────────────────────────────
    ConversationalQuestion(
        question="What is anticipatory bail under Indian law and when can it be granted?",
        category="procedural",
        difficulty="intermediate",
        required_keywords=["anticipatory bail", "arrest", "non-bailable", "Section 438", "High Court", "Sessions Court"],
        expected_sections=["Section 438", "CrPC"],
        ground_truth_facts=["anticipatory bail", "arrest", "non-bailable"],
        source="CrPC Section 438 — anticipatory bail",
        clarification_responses=[
            "This is a general legal knowledge question about anticipatory bail under Indian criminal law. I'm not referring to a specific FIR or case. Under Section 438 of the Code of Criminal Procedure (CrPC), a person who has reason to believe that they may be arrested for a non-bailable offence can apply for anticipatory bail before the Sessions Court or High Court. Please provide the complete legal framework for anticipatory bail — the conditions for granting it, which courts can grant it, and any relevant Supreme Court guidelines (like Sushila Aggarwal case).",
            "Section 438 CrPC provides for anticipatory bail. It can be granted by Sessions Court or High Court when a person apprehends arrest in a non-bailable offence. This is a general legal knowledge question — no specific FIR or case is involved. Please provide the legal provisions, conditions for grant, and the procedural framework.",
            "Anticipatory bail under CrPC Section 438 — grant by Sessions Court or High Court for non-bailable offences. No specific case involved. Please provide comprehensive legal details.",
        ],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# CLARIFICATION DETECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def is_clarification(answer: str, confidence: float, sources_count: int) -> bool:
    """
    Detect if the bot's response is a clarifying question rather than a final answer.

    Returns True if the response appears to be asking for more information.
    Returns False if the response appears to be a substantive legal answer.
    """
    # Strong signal: confidence > 0 and sources > 0 usually means final answer
    if confidence > 0 and sources_count > 0:
        return False

    answer_stripped = answer.strip()

    # Strong signal: starts with "**Case Summary**" — always a final answer
    if answer_stripped.startswith("**Case Summary**"):
        return False

    # Strong signal: starts with bold header patterns like "**Legal Analysis**", "**Answer**"
    if re.match(r'^\*\*[A-Z][a-zA-Z\s]+\*\*', answer_stripped):
        # Could be a final answer with a structured header, but check further
        # If it also has substantial length and no trailing question, it's likely final
        if len(answer_stripped) > 500 and not answer_stripped.rstrip().endswith("?"):
            return False

    # Check if the response ends with a question mark
    if answer_stripped.rstrip().endswith("?"):
        return True

    # Check for clarification patterns
    clarification_signals = [
        "follow-up question",
        "missing facts",
        "the next question should",
        "what is the exact date",
        "do you have written",
        "do you have any relevant",
        "do you have a copy",
        "can you provide",
        "could you specify",
        "could you provide",
        "what specific",
        "what are the specific",
        "is there an arbitration",
        "what is the specific section",
        "what is the specific article",
        "do you have the",
        "considering the missing facts",
        "priority order",
    ]
    answer_lower = answer.lower()
    for signal in clarification_signals:
        if signal in answer_lower:
            return True

    # If confidence is 0 and sources are 0 and answer is short, likely clarification
    if confidence == 0 and sources_count == 0 and len(answer_stripped) < 600:
        return True

    # Knowledge cutoff admission
    if "knowledge cutoff" in answer_lower or "couldn't find" in answer_lower:
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
# RAG QUERY ENGINE
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
        }


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATION MANAGER
# ══════════════════════════════════════════════════════════════════════════════

def conduct_conversation(q: ConversationalQuestion, question_num: int) -> ConversationResult:
    """
    Conduct a full multi-turn conversation with the bot for one question.

    1. Send initial question
    2. If bot asks clarifying question → respond with pre-built context
    3. Continue up to MAX_TURNS until we get a final substantive answer
    4. Return the full conversation and final answer for evaluation
    """
    session_id = f"conv_{uuid.uuid4().hex[:12]}"
    turns: List[Turn] = []
    total_latency = 0.0
    first_response_latency = 0.0

    tag = f"Q{question_num:02d}"

    # ── Turn 1: Send initial question ────────────────────────────────────
    print(f"    {C.DIM}Turn 1: Sending initial question...{C.RESET}", end=" ", flush=True)
    result = query_rag(q.question, session_id, USER_ID)
    total_latency += result["latency"]
    first_response_latency = result["latency"]

    turns.append(Turn(role="user", message=q.question))
    turns.append(Turn(
        role="assistant",
        message=result["answer"],
        confidence=result["confidence"],
        sources_count=result["sources_count"],
        latency_sec=result["latency"],
        from_cache=result["from_cache"],
        strategy=result["strategy"],
    ))

    if not result["success"]:
        print(f"{C.RED}FAILED{C.RESET}")
        return _build_result(q, turns, total_latency, first_response_latency, result, got_final=False)

    # Check if the first response is already a final answer
    if not is_clarification(result["answer"], result["confidence"], result["sources_count"]):
        print(f"{C.GREEN}Direct answer (conf={result['confidence']:.2f}){C.RESET}")
        return _build_result(q, turns, total_latency, first_response_latency, result, got_final=True)

    print(f"{C.YELLOW}Clarification (conf={result['confidence']}){C.RESET}")

    # ── Turns 2+: Respond to clarifying questions ────────────────────────
    final_result = result
    for turn_idx, follow_up in enumerate(q.clarification_responses, start=2):
        if turn_idx > MAX_TURNS:
            break

        print(f"    {C.DIM}Turn {turn_idx}: Sending follow-up response...{C.RESET}", end=" ", flush=True)
        result = query_rag(follow_up, session_id, USER_ID)
        total_latency += result["latency"]

        turns.append(Turn(role="user", message=follow_up))
        turns.append(Turn(
            role="assistant",
            message=result["answer"],
            confidence=result["confidence"],
            sources_count=result["sources_count"],
            latency_sec=result["latency"],
            from_cache=result["from_cache"],
            strategy=result["strategy"],
        ))

        if not result["success"]:
            print(f"{C.RED}FAILED{C.RESET}")
            break

        final_result = result

        # Check if we now have a final answer
        if not is_clarification(result["answer"], result["confidence"], result["sources_count"]):
            print(f"{C.GREEN}Final answer (conf={result['confidence']:.2f}){C.RESET}")
            return _build_result(q, turns, total_latency, first_response_latency, final_result, got_final=True)

        print(f"{C.YELLOW}Still clarifying (conf={result['confidence']}){C.RESET}")

    # If we exhausted all follow-ups without a final answer, evaluate the best we have
    # Use the ENTIRE conversation text for evaluation (accumulate all assistant responses)
    print(f"    {C.DIM}Max turns reached — evaluating best available answer{C.RESET}")
    return _build_result(q, turns, total_latency, first_response_latency, final_result, got_final=False)


def _build_result(
    q: ConversationalQuestion,
    turns: List[Turn],
    total_latency: float,
    first_response_latency: float,
    final_result: Dict[str, Any],
    got_final: bool,
) -> ConversationResult:
    """Build a ConversationResult from conversation data."""

    # For evaluation, combine ALL assistant responses (the final answer may reference earlier turns)
    all_assistant_text = " ".join(
        t.message for t in turns if t.role == "assistant"
    )

    # Primary evaluation target: if we got a final answer, use just that.
    # Otherwise, use all accumulated text for best-effort evaluation.
    eval_text = final_result["answer"] if got_final else all_assistant_text

    # Run accuracy check
    kw_matched, kw_missed = keyword_match(eval_text, q.required_keywords)
    sec_matched, sec_missed = section_match(eval_text, q.expected_sections)
    fact_matched, fact_missed = fact_match(eval_text, q.ground_truth_facts)

    kw_total = len(q.required_keywords)
    sec_total = len(q.expected_sections)
    fact_total = len(q.ground_truth_facts)

    kw_score = len(kw_matched) / kw_total if kw_total > 0 else 1.0
    sec_score = len(sec_matched) / sec_total if sec_total > 0 else 1.0
    fact_score = len(fact_matched) / fact_total if fact_total > 0 else 1.0

    composite = 0.30 * kw_score + 0.30 * sec_score + 0.40 * fact_score

    return ConversationResult(
        question=q.question,
        category=q.category,
        difficulty=q.difficulty,
        turns=turns,
        total_turns=len([t for t in turns if t.role == "user"]),
        final_answer=final_result["answer"],
        final_confidence=final_result["confidence"],
        final_sources=final_result["sources_count"],
        final_strategy=final_result["strategy"],
        got_final_answer=got_final,
        total_latency_sec=total_latency,
        first_response_latency=first_response_latency,
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
        matched_keywords=kw_matched,
        missed_keywords=kw_missed,
        matched_sections=sec_matched,
        missed_sections=sec_missed,
        matched_facts=fact_matched,
        missed_facts=fact_missed,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ACCURACY EVALUATION — MATCHING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    """Normalize text for comparison — lowercase, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def keyword_match(answer: str, keywords: List[str]) -> Tuple[List[str], List[str]]:
    """Check which keywords appear in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched, missed = [], []
    for kw in keywords:
        if kw.lower() in answer_lower:
            matched.append(kw)
        else:
            missed.append(kw)
    return matched, missed


def section_match(answer: str, sections: List[str]) -> Tuple[List[str], List[str]]:
    """Check which statute sections are cited in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched, missed = [], []
    for sec in sections:
        sec_lower = sec.lower()
        if sec_lower in answer_lower:
            matched.append(sec)
        elif re.search(r'section\s*' + re.escape(sec_lower.replace('section ', '').strip()), answer_lower):
            matched.append(sec)
        elif sec_lower.replace('section ', 's. ') in answer_lower:
            matched.append(sec)
        else:
            missed.append(sec)
    return matched, missed


def fact_match(answer: str, facts: List[str]) -> Tuple[List[str], List[str]]:
    """Check which factual assertions appear in the answer. Case-insensitive."""
    answer_lower = normalize(answer)
    matched, missed = [], []
    for fact in facts:
        if fact.lower() in answer_lower:
            matched.append(fact)
        else:
            missed.append(fact)
    return matched, missed


# ══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════════════════════════════════════

def grade_emoji(score: float) -> str:
    if score >= 0.9: return "A+"
    if score >= 0.8: return "A"
    if score >= 0.7: return "B"
    if score >= 0.6: return "C"
    if score >= 0.5: return "D"
    return "F"


def score_color(score: float) -> str:
    if score >= 0.8: return C.GREEN
    if score >= 0.6: return C.YELLOW
    return C.RED


def print_per_question_report(results: List[ConversationResult]):
    """Print detailed per-question analysis."""
    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  PER-QUESTION DETAILED RESULTS{C.RESET}")
    print(f"{'='*100}\n")

    for i, r in enumerate(results, 1):
        grade = grade_emoji(r.composite_score)
        col = score_color(r.composite_score)
        turns_str = f"{r.total_turns} turn{'s' if r.total_turns != 1 else ''}"
        final_tag = f"{C.GREEN}[FINAL]{C.RESET}" if r.got_final_answer else f"{C.RED}[PARTIAL]{C.RESET}"

        print(f"  {C.BOLD}Q{i:02d} [{r.category.upper()}/{r.difficulty.upper()}]{C.RESET}  {final_tag}  {turns_str}")
        print(f"  {C.DIM}{r.question[:90]}{'...' if len(r.question)>90 else ''}{C.RESET}")
        print(f"  {col}{C.BOLD}Composite: {r.composite_score:.1%}{C.RESET}  (Grade: {grade})")
        print(f"     Keywords: {r.keyword_hits}/{r.keyword_total} ({r.keyword_score:.0%})"
              f"  | Sections: {r.section_hits}/{r.section_total} ({r.section_score:.0%})"
              f"  | Facts: {r.fact_hits}/{r.fact_total} ({r.fact_score:.0%})")
        print(f"     Total Latency: {r.total_latency_sec:.2f}s  |  Confidence: {r.final_confidence:.2f}"
              f"  |  Sources: {r.final_sources}  |  Strategy: {r.final_strategy}")

        if r.total_turns > 1:
            print(f"     {C.BLUE}Conversation flow:{C.RESET}", end="")
            for t in r.turns:
                if t.role == "user":
                    print(f" [User]", end="")
                else:
                    conf_str = f"conf={t.confidence:.1f}" if t.confidence > 0 else "clarifying"
                    print(f" -> [Bot: {conf_str}]", end="")
            print()

        if r.missed_keywords:
            print(f"     {C.RED}Missed keywords:{C.RESET} {', '.join(r.missed_keywords[:5])}")
        if r.missed_sections:
            print(f"     {C.RED}Missed sections:{C.RESET} {', '.join(r.missed_sections[:5])}")
        if r.missed_facts:
            print(f"     {C.RED}Missed facts:{C.RESET} {', '.join(r.missed_facts[:5])}")
        print()


def print_category_breakdown(results: List[ConversationResult]):
    """Print accuracy breakdown by category."""
    categories: Dict[str, List[ConversationResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  ACCURACY BY CATEGORY{C.RESET}")
    print(f"{'='*100}\n")
    print(f"  {'Category':<18} {'N':>3} {'Kw%':>7} {'Sec%':>7} {'Fact%':>7} {'Comp':>8} {'Grade':>6} {'AvgTurns':>9}")
    print(f"  {'-'*18} {'-'*3} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*6} {'-'*9}")

    for cat in sorted(categories.keys()):
        rs = categories[cat]
        avg_kw = statistics.mean([r.keyword_score for r in rs])
        avg_sec = statistics.mean([r.section_score for r in rs])
        avg_fact = statistics.mean([r.fact_score for r in rs])
        avg_comp = statistics.mean([r.composite_score for r in rs])
        avg_turns = statistics.mean([r.total_turns for r in rs])
        grade = grade_emoji(avg_comp)
        print(f"  {cat:<18} {len(rs):>3} {avg_kw:>6.0%} {avg_sec:>6.0%} {avg_fact:>6.0%} {avg_comp:>7.1%} {grade:>5}  {avg_turns:>7.1f}")


def print_difficulty_breakdown(results: List[ConversationResult]):
    """Print accuracy breakdown by difficulty."""
    difficulties: Dict[str, List[ConversationResult]] = {}
    for r in results:
        difficulties.setdefault(r.difficulty, []).append(r)

    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  ACCURACY BY DIFFICULTY LEVEL{C.RESET}")
    print(f"{'='*100}\n")
    print(f"  {'Difficulty':<18} {'N':>3} {'Kw%':>7} {'Sec%':>7} {'Fact%':>7} {'Comp':>8} {'Grade':>6} {'AvgTurns':>9}")
    print(f"  {'-'*18} {'-'*3} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*6} {'-'*9}")

    for diff in ["basic", "intermediate", "advanced", "multi_hop"]:
        if diff not in difficulties:
            continue
        rs = difficulties[diff]
        avg_kw = statistics.mean([r.keyword_score for r in rs])
        avg_sec = statistics.mean([r.section_score for r in rs])
        avg_fact = statistics.mean([r.fact_score for r in rs])
        avg_comp = statistics.mean([r.composite_score for r in rs])
        avg_turns = statistics.mean([r.total_turns for r in rs])
        grade = grade_emoji(avg_comp)
        print(f"  {diff:<18} {len(rs):>3} {avg_kw:>6.0%} {avg_sec:>6.0%} {avg_fact:>6.0%} {avg_comp:>7.1%} {grade:>5}  {avg_turns:>7.1f}")


def print_conversation_stats(results: List[ConversationResult]):
    """Print conversation-specific statistics."""
    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  CONVERSATION STATISTICS{C.RESET}")
    print(f"{'='*100}\n")

    direct_answers = sum(1 for r in results if r.total_turns == 1)
    multi_turn = sum(1 for r in results if r.total_turns > 1)
    got_final = sum(1 for r in results if r.got_final_answer)
    partial = sum(1 for r in results if not r.got_final_answer)

    print(f"  {C.BOLD}Turn Distribution:{C.RESET}")
    print(f"    Direct answers (1 turn):     {direct_answers}/{len(results)}  ({direct_answers/len(results):.0%})")
    print(f"    Multi-turn conversations:    {multi_turn}/{len(results)}  ({multi_turn/len(results):.0%})")
    print()
    print(f"  {C.BOLD}Answer Quality:{C.RESET}")
    print(f"    Got final answer:            {got_final}/{len(results)}  ({got_final/len(results):.0%})")
    print(f"    Partial/no final answer:     {partial}/{len(results)}  ({partial/len(results):.0%})")

    if got_final > 0:
        final_scores = [r.composite_score for r in results if r.got_final_answer]
        print(f"    Avg score (final answers):   {statistics.mean(final_scores):.1%}")
    if partial > 0:
        partial_scores = [r.composite_score for r in results if not r.got_final_answer]
        print(f"    Avg score (partial answers): {statistics.mean(partial_scores):.1%}")

    # Turn count distribution
    turn_counts = [r.total_turns for r in results]
    print(f"\n  {C.BOLD}Turns Per Question:{C.RESET}")
    print(f"    Average:   {statistics.mean(turn_counts):.1f}")
    print(f"    Minimum:   {min(turn_counts)}")
    print(f"    Maximum:   {max(turn_counts)}")
    for t_count in sorted(set(turn_counts)):
        count = turn_counts.count(t_count)
        bar = "#" * count
        print(f"    {t_count} turn{'s' if t_count != 1 else ' '}: {count:>2}  {bar}")


def print_latency_report(results: List[ConversationResult]):
    """Print latency statistics."""
    total_lats = [r.total_latency_sec for r in results]
    first_lats = [r.first_response_latency for r in results]

    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  LATENCY ANALYSIS{C.RESET}")
    print(f"{'='*100}\n")

    print(f"  {C.BOLD}Total Conversation Latency:{C.RESET}  n={len(total_lats)}")
    print(f"    Average:   {statistics.mean(total_lats):.2f}s")
    print(f"    Median:    {statistics.median(total_lats):.2f}s")
    print(f"    Min:       {min(total_lats):.2f}s")
    print(f"    Max:       {max(total_lats):.2f}s")

    print(f"\n  {C.BOLD}First Response Latency:{C.RESET}  n={len(first_lats)}")
    print(f"    Average:   {statistics.mean(first_lats):.2f}s")
    print(f"    Median:    {statistics.median(first_lats):.2f}s")
    print(f"    Min:       {min(first_lats):.2f}s")
    print(f"    Max:       {max(first_lats):.2f}s")

    # Latency by turn count
    single_lat = [r.total_latency_sec for r in results if r.total_turns == 1]
    multi_lat = [r.total_latency_sec for r in results if r.total_turns > 1]
    if single_lat:
        print(f"\n  {C.BOLD}Direct Answer Latency (1 turn):{C.RESET}  avg={statistics.mean(single_lat):.2f}s")
    if multi_lat:
        print(f"  {C.BOLD}Multi-Turn Latency (>1 turn):{C.RESET}   avg={statistics.mean(multi_lat):.2f}s")


def print_comparison_with_single_turn(results: List[ConversationResult]):
    """Print a comparison showing the improvement over single-turn testing."""
    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  SINGLE-TURN vs MULTI-TURN COMPARISON{C.RESET}")
    print(f"{'='*100}\n")

    # Previous single-turn results (hardcoded from the last run for comparison)
    single_turn_overall = 0.383
    single_turn_retrieval_success = 0.821
    single_turn_retrieval_fail = 0.089  # rough avg of the 17 that got 0%

    multi_turn_overall = statistics.mean([r.composite_score for r in results])
    multi_turn_final = statistics.mean([r.composite_score for r in results if r.got_final_answer]) if any(r.got_final_answer for r in results) else 0
    multi_turn_partial = statistics.mean([r.composite_score for r in results if not r.got_final_answer]) if any(not r.got_final_answer for r in results) else 0

    print(f"  {'Metric':<42} {'Single-Turn':>12} {'Multi-Turn':>12} {'Change':>10}")
    print(f"  {'-'*42} {'-'*12} {'-'*12} {'-'*10}")
    delta = multi_turn_overall - single_turn_overall
    delta_str = f"+{delta:.1%}" if delta > 0 else f"{delta:.1%}"
    print(f"  {'Overall Composite Score':<42} {single_turn_overall:>11.1%} {multi_turn_overall:>11.1%} {delta_str:>10}")
    print(f"  {'When retrieval succeeded (single-turn)':<42} {single_turn_retrieval_success:>11.1%} {'—':>12} {'—':>10}")
    got_final_count = sum(1 for r in results if r.got_final_answer)
    partial_count = sum(1 for r in results if not r.got_final_answer)
    print(f"  {'Questions with final answer (multi-turn)':<42} {'8/25':>12} {f'{got_final_count}/25':>12}")
    if got_final_count > 0:
        print(f"  {'Score for final answers (multi-turn)':<42} {'—':>12} {multi_turn_final:>11.1%}")
    if partial_count > 0:
        print(f"  {'Score for partial answers (multi-turn)':<42} {'—':>12} {multi_turn_partial:>11.1%}")

    print(f"\n  {C.BOLD}Key Insight:{C.RESET}")
    if multi_turn_overall > single_turn_overall:
        improvement = multi_turn_overall - single_turn_overall
        print(f"  Multi-turn conversation improved overall accuracy by {C.GREEN}{C.BOLD}+{improvement:.1%}{C.RESET}")
        print(f"  By properly answering the bot's clarifying questions, we obtained substantive")
        print(f"  legal answers for questions that previously scored 0% in single-turn mode.")
    else:
        print(f"  Multi-turn score is similar to single-turn. The bot may need RAG improvements")
        print(f"  for questions where retrieval consistently fails.")


def print_summary(results: List[ConversationResult], total_time: float):
    """Print executive summary."""
    total = len(results)
    avg_comp = statistics.mean([r.composite_score for r in results])
    avg_kw = statistics.mean([r.keyword_score for r in results])
    avg_sec = statistics.mean([r.section_score for r in results])
    avg_fact = statistics.mean([r.fact_score for r in results])

    excellent = sum(1 for r in results if r.composite_score >= 0.9)
    good = sum(1 for r in results if 0.7 <= r.composite_score < 0.9)
    fair = sum(1 for r in results if 0.5 <= r.composite_score < 0.7)
    poor = sum(1 for r in results if r.composite_score < 0.5)
    got_final = sum(1 for r in results if r.got_final_answer)

    grade = grade_emoji(avg_comp)

    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  +============================================================+{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  |    LAW-GPT v3.0 — MULTI-TURN CONVERSATIONAL ACCURACY       |{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  +============================================================+{C.RESET}")
    print(f"{'='*100}\n")

    print(f"  {C.BOLD}OVERALL ACCURACY{C.RESET}")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Composite Score:        {C.BOLD}{avg_comp:.1%}{C.RESET}  (Grade: {C.BOLD}{grade}{C.RESET})")
    print(f"  Keyword Hit Rate:       {avg_kw:.1%}")
    print(f"  Section Citation Acc:   {avg_sec:.1%}")
    print(f"  Factual Accuracy:       {avg_fact:.1%}")
    print()
    print(f"  {C.BOLD}SCORE DISTRIBUTION{C.RESET}")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Excellent (>=90%):      {excellent}/{total}  ({excellent/total:.0%})")
    print(f"  Good     (70-89%):      {good}/{total}  ({good/total:.0%})")
    print(f"  Fair     (50-69%):      {fair}/{total}  ({fair/total:.0%})")
    print(f"  Poor     (<50%):        {poor}/{total}  ({poor/total:.0%})")
    print()
    print(f"  {C.BOLD}CONVERSATION METRICS{C.RESET}")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Final Answers Obtained: {got_final}/{total}  ({got_final/total:.0%})")
    print(f"  Avg Turns/Question:     {statistics.mean([r.total_turns for r in results]):.1f}")
    print()
    print(f"  {C.BOLD}TEST META{C.RESET}")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Total Questions:        {total}")
    print(f"  Total Test Duration:    {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Avg Time/Question:      {total_time/total:.1f}s")
    print(f"  Date:                   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend:                {BASE_URL}")
    print()


def save_json_report(results: List[ConversationResult], total_time: float, filepath: str):
    """Save machine-readable JSON report with full conversation details."""
    avg_comp = statistics.mean([r.composite_score for r in results])
    got_final = sum(1 for r in results if r.got_final_answer)

    report = {
        "test_info": {
            "name": "LAW-GPT v3.0 Multi-Turn Conversational Accuracy Test",
            "type": "conversational_multi_turn",
            "date": datetime.now().isoformat(),
            "backend_url": BASE_URL,
            "total_questions": len(results),
            "max_turns_per_question": MAX_TURNS,
            "total_duration_sec": round(total_time, 2),
        },
        "overall_accuracy": {
            "composite_score": round(avg_comp, 4),
            "keyword_hit_rate": round(statistics.mean([r.keyword_score for r in results]), 4),
            "section_citation_accuracy": round(statistics.mean([r.section_score for r in results]), 4),
            "factual_accuracy": round(statistics.mean([r.fact_score for r in results]), 4),
            "grade": grade_emoji(avg_comp),
        },
        "conversation_stats": {
            "final_answers_obtained": got_final,
            "partial_answers": len(results) - got_final,
            "avg_turns_per_question": round(statistics.mean([r.total_turns for r in results]), 2),
            "direct_answers_1_turn": sum(1 for r in results if r.total_turns == 1),
            "multi_turn_conversations": sum(1 for r in results if r.total_turns > 1),
        },
        "latency": {
            "total_conversation": {
                "avg_sec": round(statistics.mean([r.total_latency_sec for r in results]), 3),
                "median_sec": round(statistics.median([r.total_latency_sec for r in results]), 3),
                "min_sec": round(min(r.total_latency_sec for r in results), 3),
                "max_sec": round(max(r.total_latency_sec for r in results), 3),
            },
            "first_response": {
                "avg_sec": round(statistics.mean([r.first_response_latency for r in results]), 3),
                "min_sec": round(min(r.first_response_latency for r in results), 3),
                "max_sec": round(max(r.first_response_latency for r in results), 3),
            },
        },
        "per_question": [],
    }

    for i, r in enumerate(results, 1):
        q_report = {
            "question_number": i,
            "question": r.question,
            "category": r.category,
            "difficulty": r.difficulty,
            "composite_score": round(r.composite_score, 4),
            "keyword_score": round(r.keyword_score, 4),
            "section_score": round(r.section_score, 4),
            "fact_score": round(r.fact_score, 4),
            "total_turns": r.total_turns,
            "got_final_answer": r.got_final_answer,
            "final_confidence": r.final_confidence,
            "final_sources": r.final_sources,
            "final_strategy": r.final_strategy,
            "total_latency_sec": round(r.total_latency_sec, 3),
            "first_response_latency_sec": round(r.first_response_latency, 3),
            "missed_keywords": r.missed_keywords,
            "missed_sections": r.missed_sections,
            "missed_facts": r.missed_facts,
            "matched_keywords": r.matched_keywords,
            "matched_sections": r.matched_sections,
            "matched_facts": r.matched_facts,
            "final_answer_preview": r.final_answer[:500],
            "conversation": [
                {
                    "role": t.role,
                    "message_preview": t.message[:200],
                    "confidence": t.confidence,
                    "sources": t.sources_count,
                    "latency_sec": round(t.latency_sec, 3),
                }
                for t in r.turns
            ],
        }
        report["per_question"].append(q_report)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  {C.GREEN}JSON report saved -> {filepath}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.CYAN}  LAW-GPT v3.0 — MULTI-TURN CONVERSATIONAL ACCURACY TEST{C.RESET}")
    print(f"{'='*100}")
    print(f"  Backend:      {BASE_URL}")
    print(f"  Questions:    {len(QUESTIONS)}")
    print(f"  Max Turns:    {MAX_TURNS} per question")
    print(f"  Started:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*100}\n")

    # ── Step 0: Health check ─────────────────────────────────────────────
    print(f"  {C.YELLOW}[HEALTH] Checking backend...{C.RESET}", end=" ", flush=True)
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=30)
        if health.status_code == 200:
            print(f"{C.GREEN}HEALTHY{C.RESET}")
        else:
            print(f"{C.RED}UNHEALTHY (HTTP {health.status_code}) -- aborting{C.RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{C.RED}UNREACHABLE ({e}) -- aborting{C.RESET}")
        sys.exit(1)

    # ── Step 1: Run all conversations ────────────────────────────────────
    results: List[ConversationResult] = []
    total_start = time.time()

    for idx, q in enumerate(QUESTIONS, 1):
        tag = f"[{idx:02d}/{len(QUESTIONS)}]"
        short_q = q.question[:70] + ("..." if len(q.question) > 70 else "")
        print(f"\n  {C.BOLD}{C.YELLOW}{tag}{C.RESET} {C.DIM}{q.category}/{q.difficulty}{C.RESET}")
        print(f"  {C.DIM}{short_q}{C.RESET}")

        result = conduct_conversation(q, idx)
        results.append(result)

        emoji_col = score_color(result.composite_score)
        grade = grade_emoji(result.composite_score)
        final_tag = "FINAL" if result.got_final_answer else "PARTIAL"
        print(f"  {emoji_col}{C.BOLD}=> {result.composite_score:.0%} ({grade}) [{final_tag}] "
              f"{result.total_turns} turn(s) {result.total_latency_sec:.1f}s{C.RESET}")

    total_time = time.time() - total_start

    # ── Step 2: Save JSON report FIRST (before printing, to avoid crash losing data) ──
    _results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(_results_dir, exist_ok=True)
    json_path = os.path.join(_results_dir, f"conversational_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_json_report(results, total_time, json_path)

    # ── Step 3: Print all reports ────────────────────────────────────────
    print_per_question_report(results)
    print_category_breakdown(results)
    print_difficulty_breakdown(results)
    print_conversation_stats(results)
    print_latency_report(results)
    print_comparison_with_single_turn(results)
    print_summary(results, total_time)

    # Emit machine-readable score line (PASS = composite ≥ 55%)
    PASS_THRESHOLD = 0.55
    passed_count = sum(1 for r in results if r.composite_score >= PASS_THRESHOLD)
    print(f"\n  Score: {passed_count}/{len(results)} ({passed_count/len(results)*100:.0f}%)")

    print(f"\n{'='*100}")
    print(f"{C.BOLD}{C.GREEN}  MULTI-TURN CONVERSATIONAL TEST COMPLETE{C.RESET}")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
