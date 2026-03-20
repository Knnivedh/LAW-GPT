"""
RAG BENCHMARK — 20-Strategy Accuracy Test for LAW-GPT
=========================================================
Runs all 20 RAG strategies against 30 legal test cases (20 existing + 10 new hard),
measures 8 metrics per strategy, and produces ranked comparison reports.

Usage:
    python scripts/rag_benchmark.py                    # all strategies, all tests
    python scripts/rag_benchmark.py --strategies hybrid_rag,naive_rag
    python scripts/rag_benchmark.py --strategies all --tests all --output-dir results
    python scripts/rag_benchmark.py --list-strategies
"""

import sys
import os
import json
import csv
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "deployment_bundle" / "kaanoon_test"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Test Suite — 30 legal questions with expected keywords
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    category: str
    difficulty: str   # easy | medium | hard
    question: str
    expected_keywords: List[str]
    expected_citations: List[str]   # IPC sections, acts, case names
    description: str = ""


TEST_SUITE: List[TestCase] = [
    # ── CATEGORY 1: IPC Sections (5 tests) ─────────────────────────────────
    TestCase("IPC_01", "IPC Sections", "easy",
             "What is the punishment for murder under IPC?",
             ["death", "life imprisonment", "fine", "murder"],
             ["IPC 302", "Section 302"]),
    TestCase("IPC_02", "IPC Sections", "easy",
             "What does Section 420 of IPC cover?",
             ["cheating", "dishonestly", "inducing", "property"],
             ["IPC 420", "Section 420"]),
    TestCase("IPC_03", "IPC Sections", "medium",
             "What is the difference between IPC 302 and IPC 304?",
             ["murder", "culpable homicide", "intention", "knowledge"],
             ["IPC 302", "IPC 304"]),
    TestCase("IPC_04", "IPC Sections", "medium",
             "Explain Section 498A of IPC regarding dowry harassment.",
             ["husband", "cruelty", "dowry", "harassment", "cognizable"],
             ["IPC 498A", "Section 498A"]),
    TestCase("IPC_05", "IPC Sections", "hard",
             "When can culpable homicide be reduced to a lesser offence under IPC?",
             ["sudden fight", "provocation", "Exception", "culpable homicide"],
             ["IPC 300", "IPC 304"]),

    # ── CATEGORY 2: Legal Procedures (5 tests) ──────────────────────────────
    TestCase("PROC_01", "Legal Procedures", "easy",
             "What is the procedure to file an FIR?",
             ["police station", "cognizable offence", "written", "free"],
             ["CrPC 154", "Section 154"]),
    TestCase("PROC_02", "Legal Procedures", "easy",
             "What are the grounds for granting bail in India?",
             ["bail", "sureties", "discretion", "non-bailable"],
             ["CrPC 436", "CrPC 437", "bail"]),
    TestCase("PROC_03", "Legal Procedures", "medium",
             "How does one file a consumer complaint in India?",
             ["Consumer Forum", "District Commission", "complaint", "30 days"],
             ["Consumer Protection Act", "NCDRC"]),
    TestCase("PROC_04", "Legal Procedures", "medium",
             "What is the limitation period for filing a civil suit in India?",
             ["3 years", "12 years", "Limitation Act", "prescribed period"],
             ["Limitation Act 1963"]),
    TestCase("PROC_05", "Legal Procedures", "hard",
             "Explain the procedure for anticipatory bail under CrPC.",
             ["anticipatory bail", "High Court", "Sessions Court", "arrest"],
             ["CrPC 438", "Section 438"]),

    # ── CATEGORY 3: Case Laws (3 tests) ─────────────────────────────────────
    TestCase("CASE_01", "Case Laws", "medium",
             "What was the significance of Kesavananda Bharati case?",
             ["basic structure", "constitution", "Parliament", "amend"],
             ["Kesavananda Bharati", "Article 368"]),
    TestCase("CASE_02", "Case Laws", "medium",
             "What guidelines were established in the Vishaka case?",
             ["sexual harassment", "workplace", "guidelines", "employer"],
             ["Vishaka v. State of Rajasthan", "POSH"]),
    TestCase("CASE_03", "Case Laws", "hard",
             "What is the 'rarest of rare' doctrine in death penalty cases?",
             ["rarest of rare", "death penalty", "Bachan Singh", "extraordinary"],
             ["Bachan Singh v. State of Punjab"]),

    # ── CATEGORY 4: Constitutional Law (3 tests) ─────────────────────────────
    TestCase("CONST_01", "Constitutional Law", "easy",
             "What does Article 21 of the Indian Constitution guarantee?",
             ["life", "personal liberty", "procedure established by law"],
             ["Article 21"]),
    TestCase("CONST_02", "Constitutional Law", "medium",
             "What is a Public Interest Litigation (PIL) in India?",
             ["public interest", "Supreme Court", "High Court", "any person"],
             ["PIL", "Article 32", "Article 226"]),
    TestCase("CONST_03", "Constitutional Law", "hard",
             "Explain the Doctrine of Basic Structure in Indian constitutional law.",
             ["basic structure", "Kesavananda", "Parliament", "unamendable"],
             ["Article 368", "Kesavananda Bharati"]),

    # ── CATEGORY 5: Family Law (3 tests) ─────────────────────────────────────
    TestCase("FAM_01", "Family Law", "easy",
             "What are the legal grounds for divorce under the Hindu Marriage Act?",
             ["cruelty", "desertion", "adultery", "grounds"],
             ["Hindu Marriage Act 1955", "Section 13"]),
    TestCase("FAM_02", "Family Law", "medium",
             "How is maintenance determined for a wife under Section 125 CrPC?",
             ["maintenance", "wife", "neglect", "sufficient means"],
             ["CrPC 125", "Section 125"]),
    TestCase("FAM_03", "Family Law", "hard",
             "What protections does the Domestic Violence Act provide to women?",
             ["protection", "residence", "monetary relief", "domestic relationship"],
             ["Protection of Women from Domestic Violence Act", "PWDVA 2005"]),

    # ── CATEGORY 6: Property Law (3 tests) ───────────────────────────────────
    TestCase("PROP_01", "Property Law", "easy",
             "What documents are required for property registration in India?",
             ["sale deed", "stamp duty", "Sub-Registrar", "identity proof"],
             ["Registration Act 1908", "Transfer of Property Act"]),
    TestCase("PROP_02", "Property Law", "medium",
             "What is adverse possession under Indian law?",
             ["12 years", "continuous", "hostile possession", "title"],
             ["Limitation Act", "adverse possession"]),
    TestCase("PROP_03", "Property Law", "hard",
             "Explain the concept of easement rights over property in India.",
             ["easement", "dominant", "servient", "right of way"],
             ["Easements Act 1882", "Indian Easements Act"]),

    # ── CATEGORY 7: Criminal Law (2 tests) ───────────────────────────────────
    TestCase("CRIM_01", "Criminal Law", "medium",
             "What are the rights of an arrested person in India?",
             ["inform", "grounds of arrest", "legal aid", "Magistrate", "24 hours"],
             ["Article 22", "CrPC 50", "D.K. Basu"]),
    TestCase("CRIM_02", "Criminal Law", "hard",
             "Under what circumstances can the police conduct a search without a warrant?",
             ["without warrant", "reasonable grounds", "urgency", "Section 165"],
             ["CrPC 165", "CrPC 100"]),

    # ── CATEGORY 8: Corporate Law (2 tests) ──────────────────────────────────
    TestCase("CORP_01", "Corporate Law", "medium",
             "What is the procedure to incorporate a private limited company in India?",
             ["MCA", "SPICe", "Directors", "Memorandum", "Articles"],
             ["Companies Act 2013", "MCA portal"]),
    TestCase("CORP_02", "Corporate Law", "hard",
             "What are the fiduciary duties of directors under the Companies Act 2013?",
             ["fiduciary", "bona fide", "conflict of interest", "good faith"],
             ["Companies Act 2013", "Section 166"]),

    # ─────────────────────────────────────────────────────────────────────────
    # NEW HARD TESTS (multi-hop, cross-statute reasoning)
    # ─────────────────────────────────────────────────────────────────────────
    TestCase("HARD_01", "Multi-hop", "hard",
             "A person is accused of cheating and also found in possession of stolen goods. "
             "Which IPC sections apply and what would be the cumulative punishment?",
             ["IPC 420", "IPC 411", "cheating", "stolen property", "punishment"],
             ["IPC 420", "IPC 411"]),
    TestCase("HARD_02", "Multi-hop", "hard",
             "What are an employee's remedies if dismissed without notice and without cause "
             "under both the Industrial Disputes Act and the Shops and Establishments Act?",
             ["unfair dismissal", "reinstatement", "compensation", "notice period"],
             ["Industrial Disputes Act 1947", "Shops and Establishments Act"]),
    TestCase("HARD_03", "Statute Interpretation", "hard",
             "How do courts interpret the phrase 'proved beyond reasonable doubt' "
             "differently in civil vs criminal proceedings in India?",
             ["beyond reasonable doubt", "balance of probabilities", "civil", "criminal", "standard"],
             ["Indian Evidence Act", "Section 3"]),
    TestCase("HARD_04", "Conflicting Precedents", "hard",
             "Is marital rape a criminal offence in India? What do courts say?",
             ["marital rape", "exception", "IPC 375", "criminalized", "judicial"],
             ["IPC 375", "Exception 2"]),
    TestCase("HARD_05", "Constitutional + Criminal", "hard",
             "Can a person be detained under the National Security Act without trial "
             "and what constitutional remedies are available against such detention?",
             ["preventive detention", "habeas corpus", "Article 22", "NSA", "3 months"],
             ["National Security Act", "Article 22", "Article 32", "Article 226"]),
    TestCase("HARD_06", "Tax + Corporate", "hard",
             "What are the GST implications when a company transfers a going concern to another entity?",
             ["going concern", "GST", "exemption", "transfer", "CGST"],
             ["CGST Act 2017", "Schedule II CGST"]),
    TestCase("HARD_07", "Cybercrime", "hard",
             "What sections of the IT Act 2000 apply to online fraud and identity theft "
             "and what is the punishment?",
             ["Section 66C", "Section 66D", "identity theft", "impersonation", "3 years"],
             ["IT Act 2000", "Section 66C", "Section 66D"]),
    TestCase("HARD_08", "Intellectual Property", "hard",
             "What is the difference between trademark infringement and passing off under Indian IP law?",
             ["registered trademark", "passing off", "goodwill", "Trade Marks Act"],
             ["Trade Marks Act 1999", "passing off"]),
    TestCase("HARD_09", "Environmental + Constitutional", "hard",
             "What legal remedies are available to citizens against industrial pollution "
             "causing harm to a neighbourhood?",
             ["PIL", "NGT", "polluter pays", "Article 21", "environment"],
             ["National Green Tribunal Act", "Environment Protection Act 1986"]),
    TestCase("HARD_10", "Multi-statute Chain", "hard",
             "If a tenant refuses to vacate after lease expiry and the landlord uses "
             "force to evict, what legal remedies does the tenant have?",
             ["eviction", "unlawful eviction", "trespass", "Rent Control Act", "injunction"],
             ["Transfer of Property Act", "Rent Control Act"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def keyword_accuracy(answer: str, expected_keywords: List[str]) -> float:
    """Fraction of expected keywords found in the answer (case-insensitive)."""
    if not expected_keywords:
        return 1.0
    answer_lower = answer.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return found / len(expected_keywords)


def citation_accuracy(answer: str, expected_citations: List[str]) -> float:
    """Fraction of expected citations found in the answer."""
    if not expected_citations:
        return 1.0
    answer_lower = answer.lower()
    found = sum(1 for c in expected_citations if c.lower() in answer_lower)
    return found / len(expected_citations)


def hallucination_score(answer: str, docs_text: str) -> float:
    """
    Simple hallucination proxy: penalise if answer contains legal numbers/acts
    not present in retrieved context. Returns 0.0 (high hallucination) to 1.0 (clean).
    """
    import re
    # Detect IPC section numbers cited in answer
    cited_in_answer = set(re.findall(r'\b(?:IPC|Section|Article|Act)\s+[\d\w]+', answer, re.IGNORECASE))
    if not cited_in_answer:
        return 1.0  # No citations = no hallucination by this measure
    found_in_ctx = sum(
        1 for c in cited_in_answer
        if c.lower() in docs_text.lower()
    )
    return found_in_ctx / len(cited_in_answer)


def faithfulness_score(answer: str, context: str) -> float:
    """
    Bidirectional n-gram overlap between answer and context.
    Proxy for how much the answer is grounded in retrieved evidence.
    """
    if not context or not answer:
        return 0.0
    a_words = set(answer.lower().split())
    c_words = set(context.lower().split())
    if not c_words:
        return 0.0
    overlap = len(a_words & c_words) / max(len(a_words), 1)
    return min(overlap * 3, 1.0)   # Scale up since overlap is naturally low


def reasoning_depth_score(answer: str) -> float:
    """
    Heuristic score for reasoning depth (0-1).
    Checks presence of reasoning indicators.
    """
    indicators = [
        r'\bSection\b', r'\bAct\b', r'\bArticle\b',
        r'\bHeld\b', r'\btherefore\b', r'\bhowever\b',
        r'\bfirst\b.*\bsecond\b', r'\bStep\b', r'\bprovided\b',
        r'\bpursuant to\b', r'\bnotwithstanding\b',
    ]
    import re
    found = sum(1 for p in indicators if re.search(p, answer, re.IGNORECASE))
    len_score = min(len(answer.split()) / 150, 1.0)   # longer = more depth
    return min((found / max(len(indicators), 1)) * 0.5 + len_score * 0.5, 1.0)


def context_relevance(docs: List[Any], question: str) -> float:
    """Fraction of retrieved docs that share at least 2 keywords with the question."""
    if not docs:
        return 0.0
    q_words = set(question.lower().split())
    relevant = 0
    for d in docs:
        text = getattr(d, "text", str(d)).lower()
        overlap = sum(1 for w in q_words if w in text)
        if overlap >= 2:
            relevant += 1
    return relevant / len(docs)


@dataclass
class StrategyResult:
    strategy_name: str
    test_id: str
    category: str
    difficulty: str
    keyword_acc: float
    citation_acc: float
    hallucination: float
    faithfulness: float
    reasoning_depth: float
    context_relevance: float
    latency_ms: float
    answer_length: int
    composite_score: float
    answer_snippet: str   # First 200 chars
    error: str = ""


def compute_composite(r: StrategyResult) -> float:
    """Weighted composite score."""
    return (
        r.keyword_acc       * 0.30 +
        r.faithfulness      * 0.20 +
        r.citation_acc      * 0.15 +
        r.hallucination     * 0.15 +
        r.reasoning_depth   * 0.10 +
        r.context_relevance * 0.10
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared store + client initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_shared_components():
    """Initialise vector store and LLM client once for all strategies."""
    store = None
    client = None
    config = None

    try:
        from rag_system.core.hybrid_chroma_store import HybridChromaStore
        store = HybridChromaStore(
            persist_directory=str(PROJECT_ROOT / "chroma_db_hybrid"),
            collection_name="legal_db_hybrid",
        )
        logger.info(f"[Benchmark] Vector store loaded: {store.count():,} docs")
    except Exception as e:
        logger.warning(f"[Benchmark] Vector store not available: {e}")

    try:
        from config.config import Config
        config = Config
        from openai import OpenAI

        for provider in [
            ("groq", Config.GROQ_API_KEY, Config.GROQ_BASE_URL),
            ("cerebras", Config.CEREBRAS_API_KEY, Config.CEREBRAS_BASE_URL),
            ("nvidia", Config.NVIDIA_API_KEY, Config.NVIDIA_BASE_URL),
        ]:
            name, key, base_url = provider
            if key:
                try:
                    client = OpenAI(api_key=key, base_url=base_url)
                    logger.info(f"[Benchmark] LLM client: {name}")
                    break
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"[Benchmark] LLM client not available: {e}")

    return store, client, config


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark(
    strategies: List[str],
    tests: List[TestCase],
    store,
    client,
    config,
    verbose: bool = False,
) -> List[StrategyResult]:
    """Run all strategies against all tests and return flat results list."""
    from system_adapters.adapters.rag_registry import create_rag

    all_results: List[StrategyResult] = []

    for strat_name in strategies:
        print(f"\n{'─'*60}")
        print(f"Strategy: {strat_name}")
        print(f"{'─'*60}")

        # Instantiate strategy
        try:
            rag = create_rag(strat_name, hybrid_store=store, llm_client=client, config=config)
        except Exception as e:
            print(f"[SKIP] Could not create '{strat_name}': {e}")
            continue

        strategy_scores = []

        for test in tests:
            print(f"  [{test.id}] {test.question[:60]}...", end=" ", flush=True)

            try:
                t0 = time.time()
                response = rag.query(test.question, session_id=f"bench_{test.id}")
                elapsed = (time.time() - t0) * 1000

                answer = response.answer
                docs = response.documents
                docs_text = " ".join([getattr(d, "text", str(d))[:300] for d in docs])

                kw_acc   = keyword_accuracy(answer, test.expected_keywords)
                cit_acc  = citation_accuracy(answer, test.expected_citations)
                hall     = hallucination_score(answer, docs_text)
                faith    = faithfulness_score(answer, docs_text)
                reason   = reasoning_depth_score(answer)
                ctx_rel  = context_relevance(docs, test.question)

                r = StrategyResult(
                    strategy_name=strat_name,
                    test_id=test.id,
                    category=test.category,
                    difficulty=test.difficulty,
                    keyword_acc=round(kw_acc, 3),
                    citation_acc=round(cit_acc, 3),
                    hallucination=round(hall, 3),
                    faithfulness=round(faith, 3),
                    reasoning_depth=round(reason, 3),
                    context_relevance=round(ctx_rel, 3),
                    latency_ms=round(elapsed, 1),
                    answer_length=len(answer.split()),
                    composite_score=0.0,
                    answer_snippet=answer[:200],
                )
                r.composite_score = round(compute_composite(r), 3)
                all_results.append(r)
                strategy_scores.append(r.composite_score)

                status = "PASS" if kw_acc >= 0.5 and hall >= 0.5 else "FAIL"
                print(f"{status}  kw={kw_acc:.2f}  cit={cit_acc:.2f}  score={r.composite_score:.3f}  {elapsed:.0f}ms")

                if verbose:
                    print(f"    Answer: {answer[:150]}...")

            except Exception as e:
                print(f"ERROR: {e}")
                r = StrategyResult(
                    strategy_name=strat_name,
                    test_id=test.id, category=test.category, difficulty=test.difficulty,
                    keyword_acc=0.0, citation_acc=0.0, hallucination=0.0, faithfulness=0.0,
                    reasoning_depth=0.0, context_relevance=0.0,
                    latency_ms=0.0, answer_length=0, composite_score=0.0,
                    answer_snippet="", error=str(e),
                )
                all_results.append(r)

        if strategy_scores:
            avg = sum(strategy_scores) / len(strategy_scores)
            print(f"\n  → {strat_name} average composite: {avg:.3f}")

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────

def build_summary(results: List[StrategyResult]) -> List[Dict]:
    """Aggregate results per strategy."""
    from collections import defaultdict
    strategy_data = defaultdict(list)
    for r in results:
        strategy_data[r.strategy_name].append(r)

    summary = []
    for strat, rows in strategy_data.items():
        valid = [r for r in rows if not r.error]
        if not valid:
            continue
        summary.append({
            "strategy": strat,
            "tests_run": len(rows),
            "tests_passed": sum(1 for r in rows if r.keyword_acc >= 0.5),
            "avg_composite": round(sum(r.composite_score for r in valid) / len(valid), 3),
            "avg_keyword_acc": round(sum(r.keyword_acc for r in valid) / len(valid), 3),
            "avg_citation_acc": round(sum(r.citation_acc for r in valid) / len(valid), 3),
            "avg_hallucination": round(sum(r.hallucination for r in valid) / len(valid), 3),
            "avg_faithfulness": round(sum(r.faithfulness for r in valid) / len(valid), 3),
            "avg_reasoning_depth": round(sum(r.reasoning_depth for r in valid) / len(valid), 3),
            "avg_context_relevance": round(sum(r.context_relevance for r in valid) / len(valid), 3),
            "avg_latency_ms": round(sum(r.latency_ms for r in valid) / len(valid), 1),
        })

    summary.sort(key=lambda x: x["avg_composite"], reverse=True)
    return summary


def save_results(results: List[StrategyResult], summary: List[Dict], output_dir: str):
    """Save full results + summary CSV + markdown report."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Full JSON
    json_path = out / f"rag_benchmark_{ts}.json"
    with open(json_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nFull results   → {json_path}")

    # 2. Summary CSV
    csv_path = out / f"rag_benchmark_{ts}_summary.csv"
    if summary:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
            writer.writeheader()
            writer.writerows(summary)
    print(f"Summary CSV    → {csv_path}")

    # 3. Markdown report
    md_path = out / f"rag_benchmark_{ts}_report.md"
    with open(md_path, "w") as f:
        f.write(f"# LAW-GPT 20-RAG Benchmark Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Strategy Rankings (by Composite Score)\n\n")
        f.write("| Rank | Strategy | Composite | Keyword | Citation | Hallucination | Faithfulness | Latency(ms) |\n")
        f.write("|------|----------|-----------|---------|----------|---------------|--------------|-------------|\n")
        for i, s in enumerate(summary, 1):
            f.write(
                f"| {i} | {s['strategy']} | **{s['avg_composite']:.3f}** | {s['avg_keyword_acc']:.3f} | "
                f"{s['avg_citation_acc']:.3f} | {s['avg_hallucination']:.3f} | "
                f"{s['avg_faithfulness']:.3f} | {s['avg_latency_ms']:.0f} |\n"
            )
        f.write(f"\n## Composite Score Formula\n")
        f.write("```\ncomposite = keyword_acc×0.30 + faithfulness×0.20 + citation_acc×0.15\n"
                "           + hallucination×0.15 + reasoning_depth×0.10 + context_relevance×0.10\n```\n")
        f.write(f"\n## Test Suite Summary\n")
        f.write(f"- Total test cases: 30 (20 standard + 10 new hard cases)\n")
        f.write(f"- Strategies tested: {len(summary)}\n")
        f.write(f"- Total queries executed: {len(results)}\n")
    print(f"Markdown report→ {md_path}")

    return json_path, csv_path, md_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LAW-GPT 20-RAG Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategies", default="all",
        help="Comma-separated strategy names or 'all'. E.g. 'hybrid_rag,naive_rag'",
    )
    parser.add_argument(
        "--tests", default="all",
        help="Comma-separated test IDs or 'all' or 'easy' or 'hard'",
    )
    parser.add_argument(
        "--output-dir", default=str(PROJECT_ROOT / "results"),
        help="Directory to save results",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--list-strategies", action="store_true")
    args = parser.parse_args()

    # List strategies
    if args.list_strategies:
        from system_adapters.adapters.rag_registry import list_strategies, ALL_STRATEGY_NAMES
        print(f"\nAvailable RAG strategies ({len(ALL_STRATEGY_NAMES)} total):\n")
        for name, desc in list_strategies():
            print(f"  {name:35s} {desc}")
        print()
        return

    from system_adapters.adapters.rag_registry import ALL_STRATEGY_NAMES

    # Resolve strategies
    if args.strategies == "all":
        strategies = ALL_STRATEGY_NAMES
    else:
        strategies = [s.strip() for s in args.strategies.split(",")]

    # Resolve tests
    if args.tests == "all":
        tests = TEST_SUITE
    elif args.tests in ("easy", "medium", "hard"):
        tests = [t for t in TEST_SUITE if t.difficulty == args.tests]
    else:
        ids = {s.strip() for s in args.tests.split(",")}
        tests = [t for t in TEST_SUITE if t.id in ids]

    print(f"\n{'='*60}")
    print(f"LAW-GPT 20-RAG BENCHMARK")
    print(f"{'='*60}")
    print(f"Strategies: {len(strategies)}")
    print(f"Test cases: {len(tests)}")
    print(f"Total queries: {len(strategies) * len(tests)}")
    print(f"Output dir: {args.output_dir}")
    print(f"{'='*60}\n")

    # Init
    store, client, config = init_shared_components()

    if store is None:
        print("[WARNING] Vector store not available — retrieval-heavy tests will fail.")
    if client is None:
        print("[WARNING] LLM client not available — generation tests will fail.")

    # Run
    results = run_benchmark(strategies, tests, store, client, config, verbose=args.verbose)

    # Summary
    summary = build_summary(results)

    print(f"\n{'='*60}")
    print("FINAL RANKINGS")
    print(f"{'='*60}")
    for i, s in enumerate(summary[:10], 1):
        print(f"  {i:2d}. {s['strategy']:35s} score={s['avg_composite']:.3f}  kw={s['avg_keyword_acc']:.2f}  cit={s['avg_citation_acc']:.2f}")

    # Save
    save_results(results, summary, args.output_dir)
    print(f"\nBenchmark complete! Best strategy: {summary[0]['strategy'] if summary else 'N/A'}")


if __name__ == "__main__":
    main()
