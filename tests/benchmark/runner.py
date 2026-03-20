"""
LAW-GPT Benchmark Suite — Master Runner
=========================================
Runs all 6 new benchmark modules + optionally wraps the 2 existing ones.
Produces:
  tests/results/benchmark_<ts>.json   — machine-readable combined results
  tests/results/benchmark_<ts>.html   — self-contained HTML dashboard

Usage:
    python tests/benchmark/runner.py
    python tests/benchmark/runner.py --url https://lawgpt-backend2024.azurewebsites.net
    python tests/benchmark/runner.py --tests T2,T5,T8     # run subset
    python tests/benchmark/runner.py --skip T6,T7         # skip slow tests
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.benchmark.shared import BenchmarkResult, C, DEFAULT_URL, PASS_THRESHOLD, save_json

# ── HTML template (self-contained) ───────────────────────────────────────────
_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>LAW-GPT Benchmark Report</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;padding:24px}
  h1{font-size:1.8rem;font-weight:700;color:#7c3aed;margin-bottom:4px}
  .sub{color:#94a3b8;font-size:.9rem;margin-bottom:24px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:32px}
  .card{background:#1e293b;border-radius:12px;padding:18px;border:1px solid #334155}
  .card-title{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;margin-bottom:6px}
  .card-val{font-size:2rem;font-weight:700;line-height:1}
  .card-sub{font-size:.8rem;color:#64748b;margin-top:4px}
  .pass{color:#22c55e}.fail{color:#ef4444}.warn{color:#f59e0b}
  table{width:100%;border-collapse:collapse;margin-bottom:32px}
  th{background:#1e293b;padding:10px 14px;text-align:left;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;border-bottom:1px solid #334155}
  td{padding:10px 14px;border-bottom:1px solid #1e293b;font-size:.88rem}
  tr:hover td{background:#1e293b}
  .badge{display:inline-block;border-radius:9999px;padding:2px 10px;font-size:.72rem;font-weight:600}
  .badge-pass{background:#14532d;color:#4ade80}.badge-fail{background:#450a0a;color:#f87171}
  details{margin-bottom:8px}
  summary{cursor:pointer;padding:8px 12px;background:#1e293b;border-radius:6px;font-size:.82rem;color:#a5b4fc;list-style:none}
  summary::-webkit-details-marker{display:none}
  .detail-body{background:#0f172a;border:1px solid #1e293b;border-top:none;border-radius:0 0 6px 6px;padding:12px;font-size:.78rem;line-height:1.6;white-space:pre-wrap;overflow-x:auto;max-height:300px;overflow-y:auto}
  .section-title{font-size:1.1rem;font-weight:600;color:#a5b4fc;margin:24px 0 12px}
  .meta{color:#64748b;font-size:.78rem}
  footer{margin-top:40px;text-align:center;color:#334155;font-size:.78rem}
</style>
</head>
<body>
"""

_HTML_FOOT = """\
<footer>LAW-GPT Benchmark Suite &mdash; generated {ts}</footer>
</body></html>
"""


def _badge(passed: bool) -> str:
    if passed:
        return '<span class="badge badge-pass">PASS</span>'
    return '<span class="badge badge-fail">FAIL</span>'


def build_html(results: list[BenchmarkResult], ts: str, url: str) -> str:
    total_tests = len(results)
    suite_passed = sum(1 for r in results if r.accuracy >= PASS_THRESHOLD)
    overall_acc = sum(r.accuracy for r in results) / total_tests if total_tests else 0
    avg_lat = sum(r.avg_latency_sec for r in results) / total_tests if total_tests else 0
    total_q = sum(r.total for r in results)
    total_p = sum(r.passed for r in results)

    html = _HTML_HEAD
    html += f"<h1>&#x2696;&#xfe0f; LAW-GPT Benchmark Report</h1>\n"
    html += f'<p class="sub">Endpoint: <code>{url}</code> &mdash; {ts}</p>\n'

    # ── KPI cards ─────────────────────────────────────────────────────────
    html += '<div class="grid">\n'
    kpis = [
        ("Suite Pass Rate", f"{suite_passed}/{total_tests}", f"{suite_passed/total_tests*100:.0f}%", suite_passed == total_tests),
        ("Overall Accuracy", f"{total_p}/{total_q}", f"{overall_acc*100:.1f}%", overall_acc >= PASS_THRESHOLD),
        ("Avg Latency", f"{avg_lat:.1f}s", "per query", avg_lat < 30),
        ("Questions Tested", str(total_q), "across all modules", True),
    ]
    for title, val, sub, ok in kpis:
        cls = "pass" if ok else "fail"
        html += f'<div class="card"><div class="card-title">{title}</div>'
        html += f'<div class="card-val {cls}">{val}</div><div class="card-sub">{sub}</div></div>\n'
    html += '</div>\n'

    # ── Summary table ─────────────────────────────────────────────────────
    html += '<p class="section-title">Module Summary</p>\n'
    html += "<table>\n<tr>"
    for h in ["Module ID", "Test Name", "Pass/Total", "Accuracy", "Avg Latency", "Status"]:
        html += f"<th>{h}</th>"
    html += "</tr>\n"
    for r in results:
        passed_flag = r.accuracy >= PASS_THRESHOLD
        acc_cls = "pass" if passed_flag else "fail"
        html += (
            f"<tr>"
            f"<td><b>{r.test_id}</b></td>"
            f"<td>{r.test_name}</td>"
            f"<td>{r.passed}/{r.total}</td>"
            f'<td class="{acc_cls}">{r.accuracy*100:.1f}%</td>'
            f"<td>{r.avg_latency_sec:.1f}s</td>"
            f"<td>{_badge(passed_flag)}</td>"
            f"</tr>\n"
        )
    html += "</table>\n"

    # ── Per-module detail accordions ──────────────────────────────────────
    html += '<p class="section-title">Per-Question Details</p>\n'
    for r in results:
        html += f'<p class="meta" style="margin:16px 0 6px"><b>{r.test_id}</b> — {r.test_name}</p>\n'
        for d in r.details[:60]:   # cap at 60 per module for readability
            q_text = (
                d.get("question") or d.get("base_question") or
                d.get("turn1_q") or d.get("id") or "?"
            )[:80]
            q_passed = d.get("passed", False)
            lat = d.get("latency", d.get("turn1_lat", 0))
            answer = (
                d.get("answer_excerpt") or d.get("turn1_answer") or ""
            )[:300]
            label = ("✓ " if q_passed else "✗ ") + q_text + f"  [{lat}s]"
            html += f"<details><summary>{label}</summary>"
            html += f'<div class="detail-body">{json.dumps(d, indent=2, ensure_ascii=False)[:1200]}</div>'
            html += "</details>\n"

    html += _HTML_FOOT.format(ts=ts)
    return html


# ── Module registry ───────────────────────────────────────────────────────────
def _load_modules():
    """Import test modules lazily to avoid import-time side effects."""
    from tests.benchmark import (
        test_mcq_legal_knowledge as t2,
        test_token_efficiency as t5,
        test_context_retention as t6,
        test_long_document as t7,
        test_safety_ethical as t8,
        test_routing_clarification as t11,
        test_robustness as t10,
        test_core_behaviors as t12,
        test_ui_response_contract as t13,
    )
    return {
        "T2": ("T2-MCQ",     t2.run),
        "T5": ("T5-TOKEN",   t5.run),
        "T6": ("T6-CTX",     t6.run),
        "T7": ("T7-LONGDOC", t7.run),
        "T8": ("T8-SAFETY",  t8.run),
        "T11": ("T11-ROUTE", t11.run),
        "T10": ("T10-ROBUST",t10.run),
        "T12": ("T12-CONV",  t12.run),
        "T13": ("T13-UI-DATA", t13.run),
    }


def _coerce_result(module_key: str, benchmark_id: str, raw_result: Any) -> BenchmarkResult:
    if isinstance(raw_result, BenchmarkResult):
        return raw_result

    if isinstance(raw_result, dict) and {"part_a", "part_b", "part_c"}.issubset(raw_result):
        details = []
        latencies = []
        part_counts: dict[str, dict[str, int]] = {}

        for part_name in ("part_a", "part_b", "part_c"):
            part_records = raw_result.get(part_name, []) or []
            part_total = len(part_records)
            part_passed = 0
            for record in part_records:
                detail = dict(record)
                detail.setdefault("phase", part_name)
                details.append(detail)

                if detail.get("passed"):
                    part_passed += 1

                latency = detail.get("lat")
                if isinstance(latency, (int, float)):
                    latencies.append(float(latency))

            part_counts[part_name] = {"total": part_total, "passed": part_passed}

        total = len(details)
        passed = sum(1 for detail in details if detail.get("passed"))
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return BenchmarkResult(
            test_id=benchmark_id,
            test_name="Routing & Clarification",
            total=total,
            passed=passed,
            accuracy=(passed / total) if total else 0.0,
            avg_latency_sec=avg_latency,
            extra={"module": module_key, **part_counts},
            details=details,
        )

    raise TypeError(f"Unsupported benchmark result type from {module_key}: {type(raw_result).__name__}")


def run_suite(
    base_url: str = DEFAULT_URL,
    include: list[str] | None = None,
    skip: list[str] | None = None,
) -> list[BenchmarkResult]:
    modules = _load_modules()
    selected_keys = [k for k in modules if
                     (include is None or k in include) and
                     (skip is None or k not in skip)]

    print(C.bold(f"\n{'='*65}"))
    print(C.bold("  LAW-GPT BENCHMARK SUITE"))
    print(C.bold(f"{'='*65}"))
    print(C.info(f"  Target  : {base_url}"))
    print(C.info(f"  Modules : {', '.join(selected_keys)}"))
    print(C.info(f"  Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    print(C.bold(f"{'='*65}\n"))

    results: list[BenchmarkResult] = []
    for key in selected_keys:
        benchmark_id, run_fn = modules[key]
        try:
            raw_result = run_fn(base_url)
            results.append(_coerce_result(key, benchmark_id, raw_result))
        except Exception as e:
            print(C.warn(f"  [{key}] FAILED WITH EXCEPTION: {e}"))

    return results


def main():
    ap = argparse.ArgumentParser(description="LAW-GPT Benchmark Suite Runner")
    ap.add_argument("--url",   default=DEFAULT_URL,  help="Backend base URL")
    ap.add_argument("--tests", default=None,          help="Comma-separated module IDs to run (e.g. T2,T5)")
    ap.add_argument("--skip",  default=None,          help="Comma-separated module IDs to skip")
    args = ap.parse_args()

    include = [t.strip().upper() for t in args.tests.split(",")] if args.tests else None
    skip    = [t.strip().upper() for t in args.skip.split(",")]   if args.skip  else None

    results = run_suite(args.url, include=include, skip=skip)

    if not results:
        print(C.warn("No results collected."))
        return

    # ── Final summary ─────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(C.bold(f"\n{'='*65}"))
    print(C.bold("  FINAL BENCHMARK SUMMARY"))
    print(C.bold(f"{'='*65}"))
    for r in results:
        print(f"  {r.summary_line()}")

    total_q  = sum(r.total  for r in results)
    total_p  = sum(r.passed for r in results)
    overall  = total_p / total_q if total_q else 0
    n_pass   = sum(1 for r in results if r.accuracy >= PASS_THRESHOLD)
    avg_lat  = sum(r.avg_latency_sec for r in results) / len(results)

    print(C.bold(f"{'─'*65}"))
    print(
        C.bold(f"  Overall  acc={overall*100:.1f}%  {total_p}/{total_q}  "
               f"suites={n_pass}/{len(results)} pass  avg_lat={avg_lat:.1f}s")
    )
    final_badge = C.ok("ALL PASS") if n_pass == len(results) else C.warn(f"{n_pass}/{len(results)} pass")
    print(f"  {final_badge}")
    print(C.bold(f"{'='*65}\n"))

    # ── Save JSON ────────────────────────────────────────────────────────
    combined = {
        "timestamp": ts,
        "target_url": args.url,
        "overall_accuracy": round(overall, 4),
        "total_questions": total_q,
        "total_passed": total_p,
        "suites_passed": n_pass,
        "suites_total": len(results),
        "avg_latency_sec": round(avg_lat, 2),
        "modules": [
            {
                "test_id": r.test_id,
                "test_name": r.test_name,
                "total": r.total,
                "passed": r.passed,
                "accuracy": round(r.accuracy, 4),
                "avg_latency_sec": r.avg_latency_sec,
                "suite_pass": r.accuracy >= PASS_THRESHOLD,
                "extra": r.extra,
            }
            for r in results
        ],
    }
    json_path = save_json(combined, "benchmark_combined")
    print(C.info(f"  JSON saved: {json_path}"))

    # ── Save HTML ────────────────────────────────────────────────────────
    html_content = build_html(results, ts, args.url)
    from tests.benchmark.shared import RESULTS_DIR
    html_path = RESULTS_DIR / f"benchmark_{ts}.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(C.info(f"  HTML saved: {html_path}"))
    print(C.bold(f"\n  Open report: start {html_path}\n"))


if __name__ == "__main__":
    main()
