"""
Comprehensive Chatbot Audit for LAW-GPT
- Loads 4 Kaanoon datasets (raw, cleaned, summary, expanded)
- Runs queries (EN + HI/TA when available) through EnhancedRAGSystem
- Computes metrics with MetricsCalculator
- Detects gaps: semantic, keywords, key points, citations, language, length
- Outputs: JSON report, CSV summary, Markdown gap analysis
"""

import sys
import json
import csv
import re
import time
from pathlib import Path
from typing import Dict, Any, List

# Add parent
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from testing_framework import MetricsCalculator
from enhanced_rag_with_caching import EnhancedRAGSystem

DATA_FILES = {
    "raw": "kaanoon_qa_dataset.json",
    "cleaned": "kaanoon_qa_dataset_cleaned.json",
    "summary": "kaanoon_qa_summary.json",
    "expanded": "kaanoon_qa_expanded.json",
}

OUTPUT_JSON = "chatbot_audit_report.json"
OUTPUT_CSV = "chatbot_audit_report.csv"
OUTPUT_MD = "chatbot_audit_summary.md"

# Utility

def load_json(file_path: Path) -> Any:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def normalize_text(s: str) -> str:
    return (s or "").strip()


def extract_key_terms_from_points(points: List[str]) -> List[str]:
    key_terms: List[str] = []
    for p in points or []:
        pl = p.lower()
        if any(k in pl for k in ["section", "order", "rule", "article", "act", "ipc", "cpc"]):
            key_terms.append(p)
        if any(k in pl for k in ["year", "years", "month", "months", "days"]):
            key_terms.append(p)
        if any(k in pl for k in ["adverse possession", "limitation", "mandatory", "supreme court", "cbse"]):
            key_terms.append(p)
    # Dedup while preserving order
    seen = set()
    deduped: List[str] = []
    for t in key_terms:
        if t not in seen:
            deduped.append(t)
            seen.add(t)
    return deduped


def detect_language_code(text: str) -> str:
    # Simple heuristic: presence of Devanagari/Tamil letters
    if re.search(r"[\u0900-\u097F]", text or ""):
        return "hi"
    if re.search(r"[\u0B80-\u0BFF]", text or ""):
        return "ta"
    return "en"


def main():
    root = Path(__file__).parent

    # Load datasets
    datasets = {}
    for name, rel in DATA_FILES.items():
        datasets[name] = load_json(root / rel)

    # Build canonical items by id
    # Prefer fields from cleaned/expanded/summary when available
    by_id: Dict[str, Dict[str, Any]] = {}

    def merge_item(item: Dict[str, Any]):
        i = item.copy()
        _id = i.get("id") or i.get("qa_id") or i.get("QA_id")
        if not _id:
            return
        base = by_id.get(_id, {})
        base.update(i)
        by_id[_id] = base

    for name in ["raw", "cleaned", "summary", "expanded"]:
        data = datasets.get(name)
        if not data:
            continue
        if isinstance(data, list):
            for it in data:
                merge_item(it)
        elif isinstance(data, dict):
            for it in data.get("items", []):
                merge_item(it)

    # Prepare test cases (include multilingual variants if present)
    test_cases: List[Dict[str, Any]] = []
    for _id, it in by_id.items():
        q_en = normalize_text(it.get("question"))
        if not q_en:
            continue
        tc_base = {
            "id": _id,
            "category": it.get("category", ""),
            "topic": it.get("topic", ""),
            "question": q_en,
            "expected": normalize_text(it.get("short_answer", it.get("answer_summary", ""))),
            "key_points": it.get("key_points", []),
        }
        # English
        test_cases.append({**tc_base, "lang": "en", "question_lang": q_en})
        # Hindi
        if it.get("question_hindi"):
            test_cases.append({**tc_base, "lang": "hi", "question_lang": normalize_text(it.get("question_hindi"))})
        # Tamil
        if it.get("question_tamil"):
            test_cases.append({**tc_base, "lang": "ta", "question_lang": normalize_text(it.get("question_tamil"))})

    # Initialize systems
    metrics_calc = MetricsCalculator()
    system = EnhancedRAGSystem()

    results: List[Dict[str, Any]] = []

    # Run audit
    for i, tc in enumerate(test_cases, 1):
        q = tc["question_lang"]
        expected = tc["expected"]
        if not expected:
            continue

        t0 = time.time()
        resp = system.query(q, category=tc.get("category") or "kaanoon", target_language=tc["lang"])
        latency = time.time() - t0

        actual = resp.get("answer", "")
        metrics = metrics_calc.calculate_all_metrics(actual, expected, [])

        # Gap analysis
        issues: List[str] = []
        # 1) Semantic similarity
        if metrics["semantic_similarity"] < 0.75:
            issues.append("LOW_SEMANTIC_SIMILARITY")
        # 2) Keywords
        if metrics["keyword_overlap_f1"] < 0.30:
            issues.append("LOW_KEYWORD_MATCH")
        # 3) Language match
        if tc["lang"] != detect_language_code(actual):
            issues.append("LANGUAGE_MISMATCH")
        # 4) Length (too verbose > 600 chars)
        if len(actual) > 600:
            issues.append("TOO_VERBOSE")
        # 5) Citations presence if expected seems to imply legal specifics
        expects_citations = any(k in expected.lower() for k in ["section", "order", "rule", "article", "act", "ipc", "cpc"])
        has_citation = bool(re.search(r"(Section\s+\d+|Order\s+\d+|Rule\s+\d+|Article\s+\d+|IPC|CPC)", actual))
        if expects_citations and not has_citation:
            issues.append("MISSING_CITATIONS")
        # 6) Missing key points
        key_terms = extract_key_terms_from_points(tc.get("key_points") or [])
        missing_terms = []
        for term in key_terms[:5]:
            if term and (term.lower().split(":")[0] not in actual.lower()):
                missing_terms.append(term)
        if missing_terms:
            issues.append(f"MISSING_KEY_POINTS:{len(missing_terms)}")

        results.append({
            "id": tc["id"],
            "lang": tc["lang"],
            "category": tc["category"],
            "topic": tc["topic"],
            "question": q,
            "expected": expected,
            "actual": actual,
            "latency_s": round(latency, 2),
            "metrics": metrics,
            "issues": issues,
            "missing_key_points": missing_terms,
            "used_kaanoon": resp.get("used_kaanoon", False),
            "extraction_method": resp.get("extraction_method", "unknown")
        })

    # Save JSON report
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_tests": len(results),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)

    # Save CSV summary
    csv_fields = [
        "id", "lang", "category", "topic", "latency_s",
        "semantic_similarity", "keyword_overlap_f1", "accuracy_score",
        "issues", "used_kaanoon", "extraction_method"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(csv_fields)
        for r in results:
            w.writerow([
                r["id"], r["lang"], r["category"], r["topic"], r["latency_s"],
                round(r["metrics"]["semantic_similarity"], 3),
                round(r["metrics"]["keyword_overlap_f1"], 3),
                round(r["metrics"]["accuracy_score"], 3),
                ";".join(r["issues"]), r["used_kaanoon"], r["extraction_method"]
            ])

    # Markdown summary: highlight gaps
    total = len(results)
    low_sem = sum(1 for r in results if "LOW_SEMANTIC_SIMILARITY" in r["issues"])
    low_kw = sum(1 for r in results if "LOW_KEYWORD_MATCH" in r["issues"])
    lang_mismatch = sum(1 for r in results if "LANGUAGE_MISMATCH" in r["issues"])
    verbose = sum(1 for r in results if "TOO_VERBOSE" in r["issues"])
    missing_cit = sum(1 for r in results if "MISSING_CITATIONS" in r["issues"])

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Chatbot Comprehensive Audit - Summary\n\n")
        f.write(f"- Total tests: {total}\n")
        f.write(f"- LOW_SEMANTIC_SIMILARITY: {low_sem}\n")
        f.write(f"- LOW_KEYWORD_MATCH: {low_kw}\n")
        f.write(f"- LANGUAGE_MISMATCH: {lang_mismatch}\n")
        f.write(f"- TOO_VERBOSE: {verbose}\n")
        f.write(f"- MISSING_CITATIONS: {missing_cit}\n\n")
        f.write("## Top 10 Problematic Cases\n\n")
        worst = sorted(results, key=lambda r: r["metrics"]["accuracy_score"])[:10]
        for r in worst:
            f.write(f"### {r['id']} ({r['lang']}) - Acc: {r['metrics']['accuracy_score']:.2f}\n\n")
            f.write(f"Question: {r['question']}\n\n")
            f.write(f"Expected: {r['expected']}\n\n")
            f.write(f"Actual: {r['actual'][:400]}...\n\n")
            f.write(f"Issues: {', '.join(r['issues']) or 'None'}\n\n")
            if r["missing_key_points"]:
                f.write("Missing key points (examples):\n")
                for kp in r["missing_key_points"][:3]:
                    f.write(f"- {kp}\n")
                f.write("\n")

    print("\n=== COMPREHENSIVE AUDIT COMPLETE ===")
    print(f"JSON report: {OUTPUT_JSON}")
    print(f"CSV summary: {OUTPUT_CSV}")
    print(f"Markdown summary: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
