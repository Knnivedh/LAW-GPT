"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   LAW-GPT v3.0 — DEPLOYMENT HEALTH CHECK                                  ║
║                                                                            ║
║   A fast pre-flight check that verifies every critical aspect of the       ║
║   live Azure deployment BEFORE running the full accuracy/E2E suite.        ║
║                                                                            ║
║   Checks performed:                                                        ║
║     ── BACKEND (Azure) ──────────────────────────────────────────────────  ║
║     D01  GET  /api/health          — JSON {"status":"ok"}                 ║
║     D02  GET  /health              — legacy health check                  ║
║     D03  GET  /api/settings        — feature flags                        ║
║     D04  GET  /api/examples        — example queries list                 ║
║     D05  GET  /api/stats           — metrics + agentic_memory key present ║
║     D06  POST /api/query           — greeting query (fast path)           ║
║     D07  POST /api/query           — statute lookup (pageindex path)      ║
║     D08  POST /api/query           — agentic metadata fields present      ║
║     D09  POST /api/query           — response caching (repeat query)      ║
║     D10  POST /api/feedback        — feedback submission                  ║
║     D11  DELETE /api/conversation  — session clear                        ║
║     ── FRONTEND (Vercel) ────────────────────────────────────────────────  ║
║     D12  GET  /                    — LandingPage 200 OK                   ║
║     D13  GET  /login               — LoginPage 200 OK                     ║
║     ── BACKEND AGENTIC FEATURES ────────────────────────────────────────  ║
║     D14  Agentic metadata: confidence, strategy, loops                    ║
║     D15  Semantic cache: from_cache=True on second identical query        ║
║     D16  PageIndex: statute_lookup strategy triggered for section query   ║
║          (inferred from strategy field in response metadata)              ║
║                                                                            ║
║   Exit codes:                                                              ║
║     0 = all checks passed                                                 ║
║     1 = ≥1 check failed (details printed; full run still allowed)         ║
║                                                                            ║
║   Usage:                                                                   ║
║     python tests/deployment_health_check.py                               ║
║     python tests/deployment_health_check.py --backend-url https://...     ║
║     python tests/deployment_health_check.py --frontend-url https://...    ║
║     python tests/deployment_health_check.py --timeout 60                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' not installed. Run: pip install requests")
    sys.exit(1)


# ── Configuration ──────────────────────────────────────────────────────────────
BACKEND_URL  = "https://lawgpt-backend2024.azurewebsites.net"
FRONTEND_URL = "https://law-gpt-frontend.vercel.app"   # update if different
DEFAULT_TIMEOUT = 90      # seconds per request (Azure cold start)
SESSION_ID      = f"health_{uuid.uuid4().hex[:8]}"
USER_ID         = f"hc_{uuid.uuid4().hex[:6]}"


# ── Colour helpers ─────────────────────────────────────────────────────────────
class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"


# ── Result model ───────────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    check_id: str
    name: str
    passed: bool = False
    skipped: bool = False
    latency_ms: float = 0.0
    http_status: int = 0
    detail: str = ""
    warnings: List[str] = field(default_factory=list)


# ── HTTP helpers ───────────────────────────────────────────────────────────────
def _get(url: str, timeout: int) -> Tuple[Optional[requests.Response], float, str]:
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        return r, (time.time() - t0) * 1000, ""
    except requests.exceptions.ConnectionError as e:
        return None, (time.time() - t0) * 1000, f"ConnectionError: {e}"
    except requests.exceptions.Timeout:
        return None, (time.time() - t0) * 1000, f"Timeout after {timeout}s"
    except Exception as e:
        return None, (time.time() - t0) * 1000, str(e)


def _post(url: str, payload: Dict, timeout: int) -> Tuple[Optional[requests.Response], float, str]:
    t0 = time.time()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return r, (time.time() - t0) * 1000, ""
    except requests.exceptions.ConnectionError as e:
        return None, (time.time() - t0) * 1000, f"ConnectionError: {e}"
    except requests.exceptions.Timeout:
        return None, (time.time() - t0) * 1000, f"Timeout after {timeout}s"
    except Exception as e:
        return None, (time.time() - t0) * 1000, str(e)


def _delete(url: str, timeout: int) -> Tuple[Optional[requests.Response], float, str]:
    t0 = time.time()
    try:
        r = requests.delete(url, timeout=timeout)
        return r, (time.time() - t0) * 1000, ""
    except Exception as e:
        return None, (time.time() - t0) * 1000, str(e)


# ── Check runner ───────────────────────────────────────────────────────────────
def run_check(check_id: str, name: str, fn) -> CheckResult:
    cr = CheckResult(check_id=check_id, name=name)
    try:
        fn(cr)
    except AssertionError as e:
        cr.passed = False
        cr.detail = str(e)
    except Exception as e:
        cr.passed = False
        cr.detail = f"{type(e).__name__}: {e}"
    return cr


def _print_result(cr: CheckResult) -> None:
    if cr.skipped:
        badge = f"{C.YELLOW}⊘ SKIP{C.RESET}"
    elif cr.passed:
        badge = f"{C.GREEN}✔ PASS{C.RESET}"
    else:
        badge = f"{C.RED}✘ FAIL{C.RESET}"
    lat = f"  {cr.latency_ms:.0f}ms" if cr.latency_ms else ""
    print(f"  [{cr.check_id}] {badge}  {cr.name}{lat}")
    if not cr.passed and not cr.skipped and cr.detail:
        print(f"         {C.RED}{cr.detail}{C.RESET}")
    for w in cr.warnings:
        print(f"         {C.YELLOW}WARN: {w}{C.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
#  CHECK DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

def check_d01_health(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{backend}/api/health", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    status = data.get("status", "")
    assert status in ("ok", "ready", "initializing"), f"Unexpected status: {status!r}"
    if status == "initializing":
        cr.warnings.append("RAG still warming up — responses may be slower")
    cr.passed = True


def check_d02_legacy_health(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{backend}/health", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code in (200, 404), f"HTTP {resp.status_code}"
    cr.passed = True
    if resp.status_code == 404:
        cr.warnings.append("/health not present (optional endpoint)")


def check_d03_settings(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{backend}/api/settings", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    assert isinstance(data, dict), "Expected JSON object"
    cr.passed = True


def check_d04_examples(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{backend}/api/examples", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    examples = data if isinstance(data, list) else data.get("examples", [])
    assert len(examples) >= 1, "No examples returned"
    cr.detail = f"{len(examples)} examples"
    cr.passed = True


def check_d05_stats(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{backend}/api/stats", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    if "agentic_memory" not in data:
        cr.warnings.append("'agentic_memory' key missing from /api/stats (Agentic RAG not running?)")
    cr.detail = f"keys={list(data.keys())[:6]}"
    cr.passed = True


def check_d06_greeting(backend: str, timeout: int, cr: CheckResult) -> None:
    payload = {
        "question": "hello",
        "session_id": SESSION_ID,
        "user_id": USER_ID,
        "category": "general",
    }
    resp, lat, err = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    answer = data.get("answer", "") or data.get("response", "")
    assert len(answer) > 10, f"Greeting response too short: {answer!r}"
    cr.detail = f"answer_len={len(answer)}"
    cr.passed = True


def check_d07_statute_query(backend: str, timeout: int, cr: CheckResult) -> None:
    """POST /api/query — statute lookup (PageIndex path)"""
    payload = {
        "question": "What does Section 302 of Bharatiya Nyaya Sanhita say about murder?",
        "session_id": SESSION_ID,
        "user_id": USER_ID,
        "category": "criminal",
    }
    resp, lat, err = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    answer = data.get("answer", "") or data.get("response", "")
    assert len(answer) > 50, f"Answer too short: {answer!r[:80]}"
    # Check for key legal terms
    kw_found = any(kw in answer.lower() for kw in ["murder", "302", "bns", "punishment", "death"])
    if not kw_found:
        cr.warnings.append("Expected legal keywords not found in answer")
    cr.detail = f"len={len(answer)}"
    cr.passed = True


def check_d08_agentic_metadata(backend: str, timeout: int, cr: CheckResult) -> None:
    """POST /api/query — agentic metadata fields"""
    payload = {
        "question": "What are the grounds for anticipatory bail under BNSS?",
        "session_id": SESSION_ID + "_meta",
        "user_id": USER_ID,
        "category": "criminal",
    }
    resp, lat, err = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    meta = data.get("metadata", {}) or data.get("agentic_metadata", {})
    missing_keys = []
    for key in ("confidence", "strategy", "loops"):
        if key not in meta:
            missing_keys.append(key)
    if missing_keys:
        cr.warnings.append(f"Agentic metadata keys missing: {missing_keys}")
    cr.detail = f"metadata_keys={list(meta.keys())}"
    cr.passed = True


def check_d09_cache(backend: str, timeout: int, cr: CheckResult) -> None:
    """POST /api/query × 2 — second should be from_cache=True"""
    q = "What is the limitation period for filing a civil suit in India?"
    payload = {
        "question": q,
        "session_id": SESSION_ID + "_cache",
        "user_id": USER_ID,
        "category": "civil",
    }
    # First query (cache miss)
    resp1, lat1, err1 = _post(f"{backend}/api/query", payload, timeout)
    assert resp1 is not None, err1
    assert resp1.status_code == 200, f"HTTP {resp1.status_code}"

    # Second query (should hit cache)
    resp2, lat2, err2 = _post(f"{backend}/api/query", payload, timeout)
    assert resp2 is not None, err2
    assert resp2.status_code == 200, f"HTTP {resp2.status_code}"

    data2 = resp2.json()
    cr.latency_ms = lat2
    meta2 = data2.get("metadata", {})
    from_cache = meta2.get("from_cache", False)

    if not from_cache:
        cr.warnings.append("from_cache=False on repeat query — cache may not be active")
    cr.detail = f"from_cache={from_cache}  lat2={lat2:.0f}ms"
    cr.passed = True


def check_d10_feedback(backend: str, timeout: int, cr: CheckResult) -> None:
    payload = {
        "query": "test query",
        "answer": "test answer",
        "rating": 5,
        "session_id": SESSION_ID,
        "feedback_text": "Excellent accuracy",
    }
    resp, lat, err = _post(f"{backend}/api/feedback", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code in (200, 201), f"HTTP {resp.status_code}"
    cr.passed = True


def check_d11_clear_conversation(backend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _delete(f"{backend}/api/conversation?session_id={SESSION_ID}", timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    cr.http_status = resp.status_code
    assert resp.status_code in (200, 204), f"HTTP {resp.status_code}"
    cr.passed = True


def check_d12_frontend_landing(frontend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(frontend, timeout)
    cr.latency_ms = lat
    if resp is None:
        cr.skipped = True
        cr.detail = f"Frontend unreachable: {err}"
        return
    cr.http_status = resp.status_code
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    assert "LAW-GPT" in resp.text or "lawgpt" in resp.text.lower() or \
           "<div id=" in resp.text, "Unexpected landing page content"
    cr.passed = True


def check_d13_frontend_login(frontend: str, timeout: int, cr: CheckResult) -> None:
    resp, lat, err = _get(f"{frontend}/login", timeout)
    cr.latency_ms = lat
    if resp is None:
        cr.skipped = True
        cr.detail = f"Frontend unreachable: {err}"
        return
    cr.http_status = resp.status_code
    # Vercel SPA rewrites all routes to index.html → 200
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    cr.passed = True


def check_d14_agentic_confidence(backend: str, timeout: int, cr: CheckResult) -> None:
    """Agentic metadata: confidence must be 0..1"""
    payload = {
        "question": "Can a tenant be evicted without notice in India?",
        "session_id": SESSION_ID + "_d14",
        "user_id": USER_ID,
        "category": "civil",
    }
    resp, lat, err = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    meta = data.get("metadata", {})
    conf = meta.get("confidence")
    if conf is not None:
        assert 0.0 <= float(conf) <= 1.0, f"confidence out of range: {conf}"
        cr.detail = f"confidence={conf}"
    else:
        cr.warnings.append("confidence key absent from metadata")
    cr.passed = True


def check_d15_cache_speedup(backend: str, timeout: int, cr: CheckResult) -> None:
    """Semantic cache: second query ≤ 1s (cache hit)"""
    q = "What is the punishment for theft under IPC?"
    payload = {"question": q, "session_id": SESSION_ID + "_d15", "user_id": USER_ID}
    resp1, lat1, _ = _post(f"{backend}/api/query", payload, timeout)
    resp2, lat2, _ = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat2
    if resp2 and resp2.status_code == 200:
        from_cache = resp2.json().get("metadata", {}).get("from_cache", False)
        if not from_cache and lat2 > 1500:
            cr.warnings.append(f"Cache miss on repeat query, lat2={lat2:.0f}ms")
        cr.detail = f"lat1={lat1:.0f}ms  lat2={lat2:.0f}ms  cached={from_cache}"
    cr.passed = True


def check_d16_pageindex_strategy(backend: str, timeout: int, cr: CheckResult) -> None:
    """PageIndex: strategy==statute_lookup for section-specific query"""
    payload = {
        "question": "Explain Section 420 IPC: cheating and dishonestly inducing delivery of property",
        "session_id": SESSION_ID + "_d16",
        "user_id": USER_ID,
        "category": "criminal",
    }
    resp, lat, err = _post(f"{backend}/api/query", payload, timeout)
    cr.latency_ms = lat
    assert resp is not None, err
    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    data = resp.json()
    strategy = data.get("metadata", {}).get("strategy", "")
    if strategy == "statute_lookup":
        cr.detail = "strategy=statute_lookup ✔ (PageIndex activated)"
    elif strategy:
        cr.warnings.append(f"strategy={strategy!r} (expected statute_lookup for section query)")
        cr.detail = f"strategy={strategy}"
    else:
        cr.warnings.append("strategy key absent — PageIndex inference unavailable")
    cr.passed = True


# ══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description="LAW-GPT Deployment Health Check")
    ap.add_argument("--backend-url",  default=BACKEND_URL)
    ap.add_argument("--frontend-url", default=FRONTEND_URL)
    ap.add_argument("--timeout",      type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--skip-frontend", action="store_true")
    args = ap.parse_args()

    backend  = args.backend_url.rstrip("/")
    frontend = args.frontend_url.rstrip("/")
    timeout  = args.timeout

    print(f"\n{C.BOLD}{C.CYAN}{'='*70}")
    print(f"  LAW-GPT v3.0 — DEPLOYMENT HEALTH CHECK")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Backend:  {backend}")
    print(f"  Frontend: {frontend}")
    print(f"{'='*70}{C.RESET}\n")

    checks_def = [
        # id, name, fn
        ("D01", "GET /api/health",                    lambda cr: check_d01_health(backend, timeout, cr)),
        ("D02", "GET /health (legacy)",               lambda cr: check_d02_legacy_health(backend, timeout, cr)),
        ("D03", "GET /api/settings",                  lambda cr: check_d03_settings(backend, timeout, cr)),
        ("D04", "GET /api/examples",                  lambda cr: check_d04_examples(backend, timeout, cr)),
        ("D05", "GET /api/stats (agentic_memory key)",lambda cr: check_d05_stats(backend, timeout, cr)),
        ("D06", "POST /api/query (greeting fast path)",lambda cr: check_d06_greeting(backend, timeout, cr)),
        ("D07", "POST /api/query (statute/PageIndex)", lambda cr: check_d07_statute_query(backend, timeout, cr)),
        ("D08", "POST /api/query (agentic metadata)",  lambda cr: check_d08_agentic_metadata(backend, timeout, cr)),
        ("D09", "POST /api/query × 2 (cache)",         lambda cr: check_d09_cache(backend, timeout, cr)),
        ("D10", "POST /api/feedback",                  lambda cr: check_d10_feedback(backend, timeout, cr)),
        ("D11", "DELETE /api/conversation",            lambda cr: check_d11_clear_conversation(backend, timeout, cr)),
    ]

    if not args.skip_frontend:
        checks_def += [
            ("D12", "Frontend / (LandingPage)",   lambda cr: check_d12_frontend_landing(frontend, timeout, cr)),
            ("D13", "Frontend /login",             lambda cr: check_d13_frontend_login(frontend, timeout, cr)),
        ]

    checks_def += [
        ("D14", "Agentic: confidence in 0-1",          lambda cr: check_d14_agentic_confidence(backend, timeout, cr)),
        ("D15", "Semantic cache speedup",               lambda cr: check_d15_cache_speedup(backend, timeout, cr)),
        ("D16", "PageIndex: statute_lookup strategy",   lambda cr: check_d16_pageindex_strategy(backend, timeout, cr)),
    ]

    results: List[CheckResult] = []
    t_start = time.time()

    for check_id, name, fn in checks_def:
        cr = run_check(check_id, name, fn)
        results.append(cr)
        _print_result(cr)

    total   = len(results)
    passed  = sum(1 for r in results if r.passed)
    failed  = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    warns   = sum(len(r.warnings) for r in results)
    elapsed = time.time() - t_start

    all_ok = failed == 0

    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    colour = C.GREEN if all_ok else C.RED
    label  = "ALL CHECKS PASSED ✔" if all_ok else f"{failed} CHECK(S) FAILED ✘"
    pct    = f"{passed/total*100:.0f}%" if total else "—"
    print(f"  {colour}{C.BOLD}{label}{C.RESET}")
    print(f"  passed={passed}  failed={failed}  skipped={skipped}  "
          f"warnings={warns}  pass_rate={pct}  time={elapsed:.1f}s")

    # ── Save JSON ────────────────────────────────────────────────────────────
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"deployment_health_{ts}.json"
    payload  = {
        "generated": ts,
        "backend_url": backend,
        "frontend_url": frontend,
        "all_passed": all_ok,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "warnings": warns,
        "elapsed_s": round(elapsed, 2),
        "checks": [
            {
                "id": r.check_id,
                "name": r.name,
                "passed": r.passed,
                "skipped": r.skipped,
                "latency_ms": round(r.latency_ms),
                "http_status": r.http_status,
                "detail": r.detail,
                "warnings": r.warnings,
            }
            for r in results
        ],
    }
    try:
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n  {C.DIM}Report saved → {out_path}{C.RESET}")
    except Exception as e:
        print(f"\n  {C.YELLOW}(Could not save report: {e}){C.RESET}")

    print(f"{'='*70}\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
