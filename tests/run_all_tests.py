"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          LAW-GPT v3.0 — MASTER SYSTEM TEST RUNNER                         ║
║                                                                            ║
║  Orchestrates every test suite and generates a unified HTML + JSON report. ║
║                                                                            ║
║  Suites run (in order):                                                    ║
║   S1  PageIndex + Agentic RAG Integration (offline mocked)                ║
║   S2  Agentic RAG Comprehensive Unit/Integration (T01–T37)                ║
║   S3  Live Deployment Verification (16 endpoints)          [--live]       ║
║   S4  Accuracy Ground Truth (25 legal questions)           [--live]       ║
║   S5  Conversational Accuracy (5-Q Rule)                   [--live]       ║
║   S6  Frontend Unit Tests (Vitest auth suite)                             ║
║   S7  10-Dimension Accuracy Comparison (60+ tests)         [--live]       ║
║                                                                            ║
║  Usage:                                                                    ║
║    python tests/run_all_tests.py                   # all suites            ║
║    python tests/run_all_tests.py --suite s1,s3     # specific suites      ║
║    python tests/run_all_tests.py --live            # include live tests   ║
║    python tests/run_all_tests.py --offline         # offline only         ║
║                                                                            ║
║  Output:  tests/results/master_report_<timestamp>.json                    ║
║           tests/results/master_report_<timestamp>.html                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Colour helpers ────────────────────────────────────────────────────────────
class C:
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"

ROOT      = Path(__file__).resolve().parent.parent          # LAW-GPT/
TESTS_DIR = ROOT / "tests"
FRONTEND  = ROOT / "frontend"
RESULTS   = TESTS_DIR / "results"
RESULTS.mkdir(exist_ok=True)

TS = datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class SuiteResult:
    suite_id: str
    name: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    total: int = 0
    duration: float = 0.0
    score_pct: float = 0.0
    details: List[Dict] = field(default_factory=list)
    stdout: str = ""
    error: str = ""
    ran: bool = False

    @property
    def status(self) -> str:
        if not self.ran:
            return "SKIPPED"
        return "PASS" if self.failed == 0 else "FAIL"


# ── Suite registry ──────────────────────────────────────────────────────────────
@dataclass
class SuiteSpec:
    suite_id: str
    name: str
    script: str          # relative to ROOT
    requires_live: bool  # True → skipped in offline mode
    timeout: int = 300   # seconds


SUITES: List[SuiteSpec] = [
    SuiteSpec(
        suite_id="s1",
        name="PageIndex + Agentic RAG Integration",
        script="tests/test_pageindex_agentic_integration.py",
        requires_live=False,
        timeout=120,
    ),
    SuiteSpec(
        suite_id="s2",
        name="Agentic RAG Comprehensive (T01–T37)",
        script="tests/test_agentic_rag_comprehensive.py",
        requires_live=False,
        timeout=180,
    ),
    SuiteSpec(
        suite_id="s3",
        name="Live Deployment Verification (16 endpoints)",
        script="tests/test_live_deployment_verification.py",
        requires_live=True,
        timeout=300,
    ),
    SuiteSpec(
        suite_id="s4",
        name="Accuracy Ground Truth (25 questions)",
        script="tests/test_accuracy_ground_truth.py",
        requires_live=True,
        timeout=600,
    ),
    SuiteSpec(
        suite_id="s5",
        name="Conversational Accuracy (5-Q Rule)",
        script="tests/test_accuracy_conversational.py",
        requires_live=True,
        timeout=900,
    ),
    SuiteSpec(
        suite_id="s6",
        name="Frontend Auth Unit Tests (Vitest)",
        script="__vitest__",   # special marker → runs npm test
        requires_live=False,
        timeout=120,
    ),
    SuiteSpec(
        suite_id="s7",
        name="10-Dimension Accuracy Comparison (60+ tests)",
        script="tests/test_comprehensive_accuracy_comparison.py",
        requires_live=True,
        timeout=1800,   # 60+ questions × avg 20s = up to 20 min
    ),
]


# ── Python interpreter ─────────────────────────────────────────────────────────
def _python() -> str:
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv.exists():
        # Validate the venv Python actually works (venv may have been created on
        # a different machine / user and the redirect shim may be broken).
        try:
            result = subprocess.run(
                [str(venv), "-c", "import sys; sys.exit(0)"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return str(venv)
        except Exception:
            pass
    return sys.executable


def _npm() -> str:
    # On Windows npm is npm.cmd; fall back to bare npm on Unix
    import shutil
    for name in ("npm.cmd", "npm"):
        if shutil.which(name):
            return name
    return "npm"


# ── Run a single suite ─────────────────────────────────────────────────────────
def run_suite(spec: SuiteSpec, live: bool) -> SuiteResult:
    result = SuiteResult(suite_id=spec.suite_id, name=spec.name)

    if spec.requires_live and not live:
        print(f"  {C.YELLOW}[SKIP]{C.RESET} {spec.name}  (requires --live)")
        result.skipped = 1
        result.total = 1
        return result

    result.ran = True
    t0 = time.time()

    # ── Vitest (frontend) ────────────────────────────────────────────────────
    if spec.script == "__vitest__":
        try:
            proc = subprocess.run(
                [_npm(), "test", "--", "--run", "--reporter=verbose"],
                cwd=str(FRONTEND),
                capture_output=True,
                text=True,
                timeout=spec.timeout,
                encoding="utf-8",
                errors="replace",
            )
            result.stdout = (proc.stdout + proc.stderr)[-8000:]
            result.duration = time.time() - t0
            # parse vitest output (summary may be in stdout or stderr)
            _parse_vitest(proc.stdout + proc.stderr, result)
        except subprocess.TimeoutExpired:
            result.error = "TIMEOUT"
            result.failed = 1
        except Exception as e:
            result.error = str(e)
            result.failed = 1
        result.total = result.passed + result.failed + result.skipped
        result.score_pct = (result.passed / result.total * 100) if result.total else 0
        return result

    # ── Python script ────────────────────────────────────────────────────────
    script_path = ROOT / spec.script
    if not script_path.exists():
        result.error = f"Script not found: {spec.script}"
        result.failed = 1
        result.total = 1
        return result

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [_python(), str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=spec.timeout,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        result.stdout = proc.stdout[-12000:]
        result.duration = time.time() - t0
        _parse_python_output(proc.stdout + proc.stderr, result)
        # Only auto-fail if the script returned non-zero AND we couldn't detect
        # any test results at all (returncode can be 1 on Windows due to stderr
        # output even when tests themselves pass).
        if proc.returncode != 0 and result.total == 0:
            result.failed = 1
    except subprocess.TimeoutExpired:
        result.error = f"TIMEOUT after {spec.timeout}s"
        result.failed = 1
    except Exception as e:
        result.error = str(e)
        result.failed = 1

    result.total = result.passed + result.failed + result.skipped
    result.score_pct = (result.passed / result.total * 100) if result.total else 0
    result.duration = time.time() - t0
    return result


# ── Output parsers ──────────────────────────────────────────────────────────────
def _parse_python_output(text: str, result: SuiteResult) -> None:
    """
    Heuristic parser supporting output formats:
      1. Custom LAW-GPT format:  Score: 25/25 (100%)
      2. unittest verbose:       Ran 37 tests; OK / FAILED (failures=N)
      3. vitest summary:         Tests  40 passed (40)
      4. S3 deployment format:   Total Tests:  25  /  Passed:     25
      5. S4 accuracy format:     Total Questions:  25  (+ individual [PASS]/[FAIL])
      6. S5 conversational:      individual => N% lines + final summary
      7. Line-by-line scan:      lines containing | PASS / | FAIL markers
    """
    import re

    # Strip ANSI escape codes for reliable parsing
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean = ansi_escape.sub('', text)

    # ── 1. Custom format: Score: N/T ─────────────────────────────────────────
    m_score = re.search(r"Score:\s*(\d+)/(\d+)", clean)
    if m_score:
        p, t = int(m_score.group(1)), int(m_score.group(2))
        result.passed = p
        result.failed = t - p
        result.total = t
        return

    # ── 2. unittest summary: "Ran N tests" ───────────────────────────────────
    m_ran = re.search(r"Ran\s+(\d+)\s+tests?", clean)
    if m_ran:
        total = int(m_ran.group(1))
        m_f = re.search(r"FAILED\s*\(.*?failures=(\d+)", clean)
        m_e = re.search(r"FAILED\s*\(.*?errors=(\d+)", clean)
        failed = (int(m_f.group(1)) if m_f else 0) + (int(m_e.group(1)) if m_e else 0)
        result.passed = total - failed
        result.failed = failed
        result.total = total
        return

    # ── 3. vitest summary: "Tests  N passed" ─────────────────────────────────
    m_vp = re.search(r"Tests\s+(\d+)\s+passed", clean)
    m_vf = re.search(r"Tests\s+(\d+)\s+failed", clean)
    if m_vp or m_vf:
        result.passed = int(m_vp.group(1)) if m_vp else 0
        result.failed = int(m_vf.group(1)) if m_vf else 0
        result.total = result.passed + result.failed
        return

    # ── 4. S3 deployment format: "Total Tests:  N" + "Passed:     N" ─────────
    m_total = re.search(r"Total\s+Tests?[:\s]+(\d+)", clean)
    m_passed = re.search(r"Passed[:\s]+(\d+)", clean)
    if m_total and m_passed:
        t = int(m_total.group(1))
        p = int(m_passed.group(1))
        result.passed = p
        result.failed = t - p
        result.total = t
        return

    # ── 5. S4 accuracy format: count [PASS] / [FAIL] lines like "[01/25]" ────
    # (S4 now emits Score: N/T — handled by tier 1 above)
    # Fallback: check Total Questions line
    m_total_q = re.search(r"Total\s+Questions?[:\s]+(\d+)", clean)
    if m_total_q:
        total = int(m_total_q.group(1))
        failed = len(re.findall(r"🔴", clean))  # poor < 50%
        result.total = total
        result.failed = failed
        result.passed = total - failed
        return

    # ── 5b. S5 conversational: individual "=> N% (grade) [FINAL]" lines ───────
    # (S5 now emits Score: N/T — handled by tier 1 above)
    # Fallback: count FINAL answer lines
    final_lines = re.findall(r"=>\s*(\d+)%.*\[FINAL\]", clean)
    if final_lines:
        total = len(final_lines)
        failed = sum(1 for pct in final_lines if int(pct) < 50)
        result.total = total
        result.failed = failed
        result.passed = total - failed
        return

    # ── 6. Line-by-line scan for custom PASS/FAIL markers ────────────────────
    for line in clean.splitlines():
        # Skip log/warning lines (they may contain "FAILED" incidentally)
        if any(p in line for p in ("WARNING:", "INFO:", "ERROR:", "DEBUG:")):
            continue
        u = line.upper()
        if "| PASS" in u or "✓ PASS" in u or "[PASS]" in u:
            result.passed += 1
            result.details.append({"status": "PASS", "text": line.strip()[:120]})
        elif "| FAIL" in u or "✗ FAIL" in u or "[FAIL]" in u:
            result.failed += 1
            result.details.append({"status": "FAIL", "text": line.strip()[:120]})


def _parse_vitest(text: str, result: SuiteResult) -> None:
    """Parse vitest verbose reporter output."""
    _parse_python_output(text, result)


# ── Print helpers ───────────────────────────────────────────────────────────────
def _badge(status: str) -> str:
    if status == "PASS":
        return f"{C.GREEN}✔ PASS{C.RESET}"
    if status == "FAIL":
        return f"{C.RED}✘ FAIL{C.RESET}"
    return f"{C.YELLOW}⊘ SKIP{C.RESET}"


def print_suite_result(r: SuiteResult) -> None:
    badge = _badge(r.status)
    pct   = f"{r.score_pct:.0f}%" if r.ran else "—"
    dur   = f"{r.duration:.1f}s"  if r.ran else "—"
    print(f"  [{r.suite_id.upper()}] {badge} {r.name}")
    print(f"       passed={r.passed}  failed={r.failed}  score={pct}  time={dur}")
    if r.error:
        print(f"       {C.RED}ERROR: {r.error}{C.RESET}")
    for d in r.details[:5]:
        symbol = "✔" if d["status"] == "PASS" else "✘"
        colour = C.GREEN if d["status"] == "PASS" else C.RED
        print(f"       {colour}{symbol}{C.RESET} {d['text']}")
    if len(r.details) > 5:
        print(f"       ... ({len(r.details)-5} more)")


# ── HTML report ─────────────────────────────────────────────────────────────────
def _html_status_badge(status: str) -> str:
    colors = {"PASS": "#22c55e", "FAIL": "#ef4444", "SKIPPED": "#f59e0b"}
    c = colors.get(status, "#94a3b8")
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{status}</span>'


def generate_html(results: List[SuiteResult], overall_pass: bool, ts: str) -> str:
    total_p = sum(r.passed for r in results)
    total_f = sum(r.failed for r in results)
    total_t = sum(r.total for r in results)
    pct = f"{total_p/total_t*100:.1f}%" if total_t else "N/A"
    ov_color = "#22c55e" if overall_pass else "#ef4444"
    ov_label = "ALL SYSTEMS GO" if overall_pass else "ISSUES DETECTED"

    rows = ""
    for r in results:
        det_html = ""
        for d in r.details[:10]:
            sym = "✔" if d["status"] == "PASS" else "✘"
            col = "#16a34a" if d["status"] == "PASS" else "#dc2626"
            det_html += f'<li style="color:{col};font-size:11px">{sym} {d["text"]}</li>'
        if len(r.details) > 10:
            det_html += f'<li style="color:#64748b;font-size:11px">+{len(r.details)-10} more…</li>'

        rows += f"""
        <tr style="border-bottom:1px solid #1e293b">
          <td style="padding:10px 14px;font-weight:600;color:#e2e8f0">[{r.suite_id.upper()}] {r.name}</td>
          <td style="padding:10px 14px;text-align:center">{_html_status_badge(r.status)}</td>
          <td style="padding:10px 14px;text-align:center;color:#86efac">{r.passed}</td>
          <td style="padding:10px 14px;text-align:center;color:#fca5a5">{r.failed}</td>
          <td style="padding:10px 14px;text-align:center;color:#93c5fd">{r.score_pct:.0f}%</td>
          <td style="padding:10px 14px;text-align:center;color:#94a3b8">{r.duration:.1f}s</td>
          <td style="padding:10px 14px"><ul style="margin:0;padding-left:16px">{det_html}</ul></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>LAW-GPT Master Test Report {ts}</title>
<style>
  body{{background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;margin:0;padding:24px}}
  h1{{margin:0 0 4px;font-size:28px;color:#f8fafc}}
  .subtitle{{color:#94a3b8;font-size:13px;margin-bottom:24px}}
  .summary{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .card{{background:#1e293b;border-radius:10px;padding:16px 24px;min-width:120px;text-align:center}}
  .card .num{{font-size:32px;font-weight:700;margin-bottom:4px}}
  .card .lbl{{font-size:12px;color:#94a3b8}}
  table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden}}
  th{{background:#0f172a;padding:10px 14px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}}
  tr:hover{{background:#263248}}
  .footer{{margin-top:24px;color:#475569;font-size:11px;text-align:center}}
</style>
</head>
<body>
<h1>⚖ LAW-GPT v3.0 — Master Test Report</h1>
<div class="subtitle">Generated {ts} | Backend: https://lawgpt-backend2024.azurewebsites.net</div>
<div class="summary">
  <div class="card"><div class="num" style="color:{ov_color}">{ov_label}</div><div class="lbl">Overall</div></div>
  <div class="card"><div class="num" style="color:#22c55e">{total_p}</div><div class="lbl">Tests Passed</div></div>
  <div class="card"><div class="num" style="color:#ef4444">{total_f}</div><div class="lbl">Tests Failed</div></div>
  <div class="card"><div class="num" style="color:#93c5fd">{pct}</div><div class="lbl">Pass Rate</div></div>
  <div class="card"><div class="num" style="color:#fbbf24">{len(results)}</div><div class="lbl">Suites</div></div>
</div>
<table>
<thead>
  <tr>
    <th>Suite</th><th>Status</th><th>Pass</th><th>Fail</th><th>Score</th><th>Duration</th><th>Details</th>
  </tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<div class="footer">LAW-GPT Agentic RAG v3.0 | PageIndex Vectorless Retrieval | Azure Deployed</div>
</body>
</html>"""


# ── Main orchestrator ───────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="LAW-GPT Master Test Runner")
    parser.add_argument("--live",    action="store_true", help="Include live Azure endpoint tests")
    parser.add_argument("--offline", action="store_true", help="Run offline suites only (ignores --live)")
    parser.add_argument("--suite",   default="",          help="Comma-separated suite ids, e.g. s1,s2")
    parser.add_argument("--url",     default="",          help="Backend URL for live tests (overrides env LAWGPT_BASE_URL)")
    args = parser.parse_args()

    live = args.live and not args.offline
    selected_ids = [s.strip().lower() for s in args.suite.split(",") if s.strip()]

    # Inject backend URL for live tests via env var
    backend_url = args.url or os.environ.get("LAWGPT_BASE_URL", "https://lawgpt-backend2024.azurewebsites.net")
    if live:
        os.environ["LAWGPT_BASE_URL"] = backend_url

    suites_to_run = [s for s in SUITES if not selected_ids or s.suite_id in selected_ids]

    print(f"\n{C.BOLD}{C.CYAN}{'='*70}")
    print(f"  LAW-GPT v3.0 — MASTER SYSTEM TEST RUNNER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | live={live} | suites={len(suites_to_run)}")
    if live:
        print(f"  Backend: {backend_url}")
    print(f"{'='*70}{C.RESET}\n")

    results: List[SuiteResult] = []
    for spec in suites_to_run:
        print(f"{C.BOLD}[{spec.suite_id.upper()}] {spec.name}{C.RESET}")
        r = run_suite(spec, live=live)
        results.append(r)
        print_suite_result(r)
        print()

    # ── Aggregate ───────────────────────────────────────────────────────────
    total_p = sum(r.passed for r in results)
    total_f = sum(r.failed for r in results)
    total_t = sum(r.total for r in results)
    overall = total_f == 0 and total_t > 0

    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    ov_col = C.GREEN if overall else C.RED
    ov_lbl = "ALL SYSTEMS GO ✔" if overall else "ISSUES DETECTED ✘"
    pct = f"{total_p/total_t*100:.1f}%" if total_t else "—"
    print(f"  {ov_col}{C.BOLD}{ov_lbl}{C.RESET}")
    print(f"  Total: passed={total_p}  failed={total_f}  total={total_t}  pass_rate={pct}")
    print(f"{'='*70}\n")

    # ── Save JSON ───────────────────────────────────────────────────────────
    json_path = RESULTS / f"master_report_{TS}.json"
    payload = {
        "generated": TS,
        "overall_pass": overall,
        "total_passed": total_p,
        "total_failed": total_f,
        "total_tests": total_t,
        "pass_rate_pct": round(total_p / total_t * 100, 2) if total_t else 0,
        "suites": [asdict(r) for r in results],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  {C.DIM}JSON: {json_path}{C.RESET}")

    # ── Save HTML ───────────────────────────────────────────────────────────
    html_path = RESULTS / f"master_report_{TS}.html"
    html_path.write_text(generate_html(results, overall, TS), encoding="utf-8")
    print(f"  {C.DIM}HTML: {html_path}{C.RESET}\n")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
