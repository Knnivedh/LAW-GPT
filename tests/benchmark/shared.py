"""
shared.py — Common utilities for LAW-GPT Benchmark Suite.

All benchmark modules import from here:
  - call_api()       : POST /api/query and return normalised response dict
  - BenchmarkResult  : dataclass for per-module aggregate result
  - save_json()      : write results JSON to tests/results/
  - C                : ANSI colour helpers
  - score_answer()   : keyword + section + fact composite scorer
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Unicode safety on Windows -------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── Paths & constants ---------------------------------------------------------
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DEFAULT_URL = os.environ.get(
    "LAWGPT_BASE_URL", "https://lawgpt-backend2024.azurewebsites.net"
)
TIMEOUT = 180       # per-request timeout seconds (70b model can take 90-120s under load)
PASS_THRESHOLD = 0.55


# ── ANSI colours --------------------------------------------------------------
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

    @staticmethod
    def ok(s):  return f"{C.GREEN}{s}{C.RESET}"
    @staticmethod
    def fail(s): return f"{C.RED}{s}{C.RESET}"
    @staticmethod
    def warn(s): return f"{C.YELLOW}{s}{C.RESET}"
    @staticmethod
    def info(s): return f"{C.CYAN}{s}{C.RESET}"
    @staticmethod
    def bold(s): return f"{C.BOLD}{s}{C.RESET}"


# ── Data structures -----------------------------------------------------------
@dataclass
class BenchmarkResult:
    test_id: str          # e.g. "T2-MCQ"
    test_name: str
    total: int
    passed: int
    accuracy: float       # 0-1
    avg_latency_sec: float
    extra: Dict[str, Any] = field(default_factory=dict)   # test-specific extras
    details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def failed(self): return self.total - self.passed

    def summary_line(self) -> str:
        badge = C.ok("PASS") if self.accuracy >= PASS_THRESHOLD else C.fail("FAIL")
        return (
            f"[{self.test_id}] {self.test_name:<38} "
            f"acc={self.accuracy*100:5.1f}%  "
            f"pass={self.passed}/{self.total}  "
            f"lat={self.avg_latency_sec:.1f}s  {badge}"
        )


# ── API helper ----------------------------------------------------------------
def call_api(
    question: str,
    session_id: Optional[str] = None,
    category: str = "general",
    base_url: str = DEFAULT_URL,
    retries: int = 2,
) -> Tuple[Dict[str, Any], float]:
    """
    POST /api/query.  Returns (response_dict, latency_sec).
    response_dict keys guaranteed: answer, think_trace, sources, system_info,
                                   confidence, from_cache, latency, status
    Raises on unrecoverable error.
    """
    sid = session_id or f"bench_{uuid.uuid4().hex[:10]}"
    payload = {
        "question": question,
        "session_id": sid,
        "category": category,
        "target_language": "en",
        "web_search_mode": False,
    }
    url = f"{base_url.rstrip('/')}/api/query"
    _STUB_PHRASES = ("unable to generate", "service issue", "please try again")
    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
            latency = time.time() - t0
            resp.raise_for_status()
            data = resp.json()
            r = data.get("response", data)
            # Normalise missing keys
            r.setdefault("answer", "")
            r.setdefault("think_trace", None)
            r.setdefault("sources", [])
            r.setdefault("system_info", {})
            r.setdefault("confidence", 0.0)
            r.setdefault("from_cache", False)
            r.setdefault("latency", latency)
            r.setdefault("status", "direct")
            # Retry if answer is empty or a stub error message
            ans = r.get("answer", "")
            _is_stub = not ans.strip() or any(p in ans.lower() for p in _STUB_PHRASES)
            if _is_stub and attempt < retries:
                wait = 6 * (attempt + 1)
                print(f"    [retry {attempt+1}] stub/empty answer — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            return r, latency
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"API call failed after {retries+1} attempts: {last_err}")


# ── Scorer --------------------------------------------------------------------
def score_answer(
    answer: str,
    required_keywords: List[str],
    expected_sections: List[str],
    ground_truth_facts: List[str],
    weights: Tuple[float, float, float] = (0.30, 0.30, 0.40),
) -> Dict[str, Any]:
    """
    Returns dict with:
        keyword_score, section_score, fact_score, composite,
        kw_hits, sec_hits, fact_hits, missed_kw, missed_sec, missed_fact
    """
    ans_lower = answer.lower()

    def hit(phrase: str) -> bool:
        return phrase.lower() in ans_lower

    kw_hits   = [k for k in required_keywords  if hit(k)]
    sec_hits  = [s for s in expected_sections  if hit(s)]
    fact_hits = [f for f in ground_truth_facts if hit(f)]

    kw_score   = len(kw_hits)  / max(len(required_keywords),  1)
    sec_score  = len(sec_hits) / max(len(expected_sections),  1)
    fact_score = len(fact_hits) / max(len(ground_truth_facts), 1)

    w_kw, w_sec, w_fact = weights
    composite = w_kw * kw_score + w_sec * sec_score + w_fact * fact_score

    return {
        "keyword_score": round(kw_score, 3),
        "section_score": round(sec_score, 3),
        "fact_score": round(fact_score, 3),
        "composite": round(composite, 3),
        "kw_hits": len(kw_hits),
        "kw_total": len(required_keywords),
        "sec_hits": len(sec_hits),
        "sec_total": len(expected_sections),
        "fact_hits": len(fact_hits),
        "fact_total": len(ground_truth_facts),
        "missed_kw": [k for k in required_keywords  if not hit(k)],
        "missed_sec": [s for s in expected_sections  if not hit(s)],
        "missed_fact": [f for f in ground_truth_facts if not hit(f)],
    }


# ── JSON saver ----------------------------------------------------------------
def save_json(data: Dict[str, Any], prefix: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"{prefix}_{ts}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
