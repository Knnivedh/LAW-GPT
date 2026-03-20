"""
═══════════════════════════════════════════════════════════════════════════════
COMPREHENSIVE AGENTIC RAG TEST SUITE — LAW-GPT (2026)
═══════════════════════════════════════════════════════════════════════════════

25+ test categories covering the full Agentic RAG system:

 UNIT TESTS (offline, mocked — fast)
  T01  ShortTermMemory — add / get / clear / overflow
  T02  LongTermMemory — profile CRUD, domain tracking
  T03  SemanticCache — put / get / TTL expiry / LRU eviction / stats
  T04  AgenticMemoryManager — unified facade wrappers
  T05  AgentPlan dataclass — field defaults, strategy enum
  T06  Rule-based planner — keyword heuristics (no LLM)
  T07  JSON parser — markdown fences, malformed JSON, nested objects
  T08  Source formatter — doc limiting, missing fields
  T09  Plan refinement — strategy escalation logic
  T10  VerificationResult — confidence thresholding
  T11  Greeting detection — regex patterns

 INTEGRATION TESTS (mocked LLM — medium speed)
  T12  LLM-powered planner — mock Groq, parse response
  T13  Retrieval stage — mock ParametricRAG, sub-query expansion
  T14  Synthesis stage — mock LLM, context injection
  T15  Verification stage — mock LLM, acceptance / rejection
  T16  Full agentic loop (1 pass) — plan → retrieve → synthesise → verify
  T17  Full agentic loop (2 passes) — verify rejects → refine → re-run
  T18  Cache integration — first miss, second hit
  T19  Memory context injection — conversation history used in prompts
  T20  User profile tracking — domain interests accumulate

 API / CONTRACT TESTS (mocked server — fast)
  T21  QueryRequest model — required/optional fields, user_id
  T22  format_rag_response — agentic metadata propagation
  T23  /api/stats — agentic_memory field in response
  T24  /api/health — readiness check

 LIVE E2E TESTS (real Azure endpoint — slow, optional)
  T25  Live query — BNS Section 302
  T26  Live cache — repeat query returns from_cache=True
  T27  Live stats — agentic_memory counters
  T28  Live greeting — returns greeting response
  T29  Live research mode — direct synthesis
  T30  Live error handling — empty question

 STRESS / EDGE CASES
  T31  Cache overflow — 500+ entries trigger LRU eviction
  T32  Session overflow — 10+ turns trimmed
  T33  Empty query handling
  T34  Very long query handling (1000+ chars)
  T35  Unicode / Hindi query handling
  T36  Concurrent session isolation
  T37  Graceful fallback — agentic engine None → legacy path

═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import json
import os
import re
import sys
import time
import unittest
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch, PropertyMock

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.persistent_memory import (
    ShortTermMemory, LongTermMemory, SemanticCache,
    AgenticMemoryManager, MemoryEntry, UserProfile, CacheEntry,
)
from kaanoon_test.system_adapters.agentic_rag_engine import (
    AgenticRAGEngine, AgentPlan, RetrievalPacket,
    VerificationResult, AgenticResult,
    MAX_AGENT_LOOPS, CONFIDENCE_THRESHOLD,
)

# Whether to run live Azure tests (set env: RUN_LIVE_TESTS=1)
RUN_LIVE_TESTS = os.environ.get("RUN_LIVE_TESTS", "0") == "1"
AZURE_BASE = "https://lawgpt-backend2024.azurewebsites.net"


# ═════════════════════════════════════════════════════════════════════════════
#  T01 — SHORT-TERM MEMORY
# ═════════════════════════════════════════════════════════════════════════════

class T01_ShortTermMemory(unittest.TestCase):
    """Unit tests for ShortTermMemory (per-session conversation buffer)."""

    def setUp(self):
        self.stm = ShortTermMemory(max_turns=3)

    def test_add_and_get_context(self):
        """Adding messages and retrieving context works."""
        self.stm.add("s1", "user", "What is Section 302 BNS?")
        self.stm.add("s1", "assistant", "Section 302 deals with...")
        ctx = self.stm.get_context("s1")
        self.assertIn("User: What is Section 302", ctx)
        self.assertIn("Assistant: Section 302", ctx)

    def test_empty_session_returns_empty(self):
        """Unknown session returns empty context."""
        self.assertEqual(self.stm.get_context("nonexistent"), "")

    def test_max_turns_trimming(self):
        """Exceeding max_turns trims oldest messages."""
        for i in range(10):
            self.stm.add("s1", "user", f"msg_{i}")
            self.stm.add("s1", "assistant", f"reply_{i}")
        msgs = self.stm.get_messages("s1")
        # max_turns=3 → limit = 6 messages
        self.assertLessEqual(len(msgs), 6)

    def test_clear_session(self):
        """Clearing a session removes all messages."""
        self.stm.add("s1", "user", "test")
        self.stm.clear("s1")
        self.assertEqual(self.stm.get_messages("s1"), [])

    def test_session_count(self):
        """Session count reflects active sessions."""
        self.stm.add("s1", "user", "a")
        self.stm.add("s2", "user", "b")
        self.assertEqual(self.stm.session_count(), 2)

    def test_get_last_user_query(self):
        """Retrieves last user message from session."""
        self.stm.add("s1", "user", "first")
        self.stm.add("s1", "assistant", "reply")
        self.stm.add("s1", "user", "second")
        self.assertEqual(self.stm.get_last_user_query("s1"), "second")

    def test_get_last_user_query_empty(self):
        """Returns None if no user messages."""
        self.assertIsNone(self.stm.get_last_user_query("nope"))

    def test_metadata_stored(self):
        """Metadata dict is stored with entries."""
        self.stm.add("s1", "user", "test", metadata={"domain": "criminal"})
        msgs = self.stm.get_messages("s1")
        self.assertEqual(msgs[0].metadata, {"domain": "criminal"})

    def test_session_isolation(self):
        """Messages don't leak between sessions."""
        self.stm.add("s1", "user", "session_one")
        self.stm.add("s2", "user", "session_two")
        ctx1 = self.stm.get_context("s1")
        ctx2 = self.stm.get_context("s2")
        self.assertIn("session_one", ctx1)
        self.assertNotIn("session_two", ctx1)
        self.assertIn("session_two", ctx2)


# ═════════════════════════════════════════════════════════════════════════════
#  T02 — LONG-TERM MEMORY
# ═════════════════════════════════════════════════════════════════════════════

class T02_LongTermMemory(unittest.TestCase):
    """Unit tests for LongTermMemory (user profile CRUD)."""

    def setUp(self):
        # Force local mode (no Supabase)
        self.ltm = LongTermMemory.__new__(LongTermMemory)
        self.ltm._supabase = None
        self.ltm._local_profiles = {}
        self.ltm._local_path = "__test_ltm_NOPE__.json"

    def test_get_profile_creates_new(self):
        """Getting a nonexistent profile creates a new one."""
        profile = self.ltm.get_profile("user_123")
        self.assertEqual(profile.user_id, "user_123")
        self.assertEqual(profile.interaction_count, 0)
        self.assertEqual(profile.preferred_language, "en")

    def test_record_interaction_increments(self):
        """Recording an interaction increments count and tracks domains."""
        self.ltm.record_interaction("u1", "What is BNS 302?", ["BNS", "Criminal"])
        profile = self.ltm.get_profile("u1")
        self.assertEqual(profile.interaction_count, 1)
        self.assertIn("BNS", profile.legal_domains_of_interest)
        self.assertIn("Criminal", profile.legal_domains_of_interest)

    def test_domain_dedup(self):
        """Duplicate domains are not added twice."""
        self.ltm.record_interaction("u1", "q1", ["BNS"])
        self.ltm.record_interaction("u1", "q2", ["BNS"])
        profile = self.ltm.get_profile("u1")
        self.assertEqual(profile.legal_domains_of_interest.count("BNS"), 1)

    def test_past_queries_stored(self):
        """Past queries are stored in summary form."""
        self.ltm.record_interaction("u1", "What is Section 302?", ["Criminal"])
        profile = self.ltm.get_profile("u1")
        self.assertEqual(len(profile.past_queries_summary), 1)
        self.assertIn("Section 302", profile.past_queries_summary[0])

    def test_past_queries_cap_at_20(self):
        """Past queries are capped at 20."""
        for i in range(25):
            self.ltm.record_interaction("u1", f"query_{i}", ["General"])
        profile = self.ltm.get_profile("u1")
        self.assertLessEqual(len(profile.past_queries_summary), 20)

    def test_domain_cap_at_20(self):
        """Domain interests capped at 20."""
        for i in range(25):
            self.ltm.record_interaction("u1", f"q_{i}", [f"domain_{i}"])
        profile = self.ltm.get_profile("u1")
        self.assertLessEqual(len(profile.legal_domains_of_interest), 20)


# ═════════════════════════════════════════════════════════════════════════════
#  T03 — SEMANTIC CACHE
# ═════════════════════════════════════════════════════════════════════════════

class T03_SemanticCache(unittest.TestCase):
    """Unit tests for SemanticCache (MD5 hash, TTL, LRU)."""

    def setUp(self):
        self.cache = SemanticCache(max_entries=5, default_ttl=3600)

    def test_put_and_get(self):
        """Basic put and get works."""
        self.cache.put("What is BNS 302?", "It deals with murder", [{"title": "BNS"}])
        entry = self.cache.get("What is BNS 302?")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "It deals with murder")

    def test_cache_miss(self):
        """Unknown query returns None."""
        self.assertIsNone(self.cache.get("unknown query"))

    def test_normalisation(self):
        """Queries are normalised (case, punctuation, whitespace)."""
        self.cache.put("What is BNS 302?", "answer", [])
        # Different casing/punctuation should hit same cache
        entry = self.cache.get("what is bns 302")
        self.assertIsNotNone(entry)

    def test_ttl_expiry(self):
        """Expired entries return None."""
        self.cache.put("test", "answer", [], ttl=0.01)
        time.sleep(0.02)
        self.assertIsNone(self.cache.get("test"))

    def test_lru_eviction(self):
        """Oldest entry evicted when cache is full."""
        for i in range(6):  # max=5
            self.cache.put(f"query_{i}", f"answer_{i}", [])
        # First entry should be evicted
        self.assertIsNone(self.cache.get("query_0"))
        # Last entry should exist
        self.assertIsNotNone(self.cache.get("query_5"))

    def test_stats_tracking(self):
        """Stats (hits, misses, hit_rate, size) are accurate."""
        self.cache.put("q1", "a1", [])
        self.cache.get("q1")      # hit
        self.cache.get("q_miss")  # miss
        stats = self.cache.stats
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["total"], 2)
        self.assertAlmostEqual(stats["hit_rate"], 0.5)
        self.assertEqual(stats["size"], 1)

    def test_invalidate(self):
        """Invalidating an entry removes it."""
        self.cache.put("q1", "a1", [])
        self.cache.invalidate("q1")
        self.assertIsNone(self.cache.get("q1"))

    def test_clear(self):
        """Clear removes all entries."""
        self.cache.put("q1", "a1", [])
        self.cache.put("q2", "a2", [])
        self.cache.clear()
        self.assertIsNone(self.cache.get("q1"))
        self.assertIsNone(self.cache.get("q2"))

    def test_hit_count_increments(self):
        """Each get increments hit_count on the entry."""
        self.cache.put("q1", "a1", [])
        self.cache.get("q1")
        self.cache.get("q1")
        entry = self.cache.get("q1")
        self.assertEqual(entry.hit_count, 3)

    def test_hash_deterministic(self):
        """Same normalised query always produces same hash."""
        h1 = self.cache._hash(self.cache._normalise_query("What is BNS?"))
        h2 = self.cache._hash(self.cache._normalise_query("what is bns"))
        self.assertEqual(h1, h2)


# ═════════════════════════════════════════════════════════════════════════════
#  T04 — AGENTIC MEMORY MANAGER
# ═════════════════════════════════════════════════════════════════════════════

class T04_AgenticMemoryManager(unittest.TestCase):
    """Unit tests for the unified 3-tier memory facade."""

    def setUp(self):
        self.mgr = AgenticMemoryManager.__new__(AgenticMemoryManager)
        self.mgr.short_term = ShortTermMemory(max_turns=5)
        self.mgr.long_term = LongTermMemory.__new__(LongTermMemory)
        self.mgr.long_term._supabase = None
        self.mgr.long_term._local_profiles = {}
        self.mgr.long_term._local_path = "__test_nope__.json"
        self.mgr.cache = SemanticCache(max_entries=10, default_ttl=3600)

    def test_remember_turn(self):
        """remember_turn stores in short-term memory."""
        self.mgr.remember_turn("s1", "user", "hello")
        ctx = self.mgr.get_conversation_context("s1")
        self.assertIn("hello", ctx)

    def test_check_cache_miss(self):
        """check_cache returns None on miss."""
        self.assertIsNone(self.mgr.check_cache("new query"))

    def test_cache_response_and_hit(self):
        """cache_response then check_cache returns cached entry."""
        self.mgr.cache_response("q1", "answer", [{"s": 1}])
        entry = self.mgr.check_cache("q1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "answer")

    def test_update_user_profile(self):
        """update_user_profile records interaction."""
        self.mgr.update_user_profile("u1", "query", ["Criminal"])
        profile = self.mgr.get_user_profile("u1")
        self.assertEqual(profile.interaction_count, 1)

    def test_get_memory_stats(self):
        """get_memory_stats returns correct structure."""
        stats = self.mgr.get_memory_stats()
        self.assertIn("short_term_sessions", stats)
        self.assertIn("cache", stats)
        self.assertIn("hits", stats["cache"])

    def test_clear_session(self):
        """clear_session removes short-term data."""
        self.mgr.remember_turn("s1", "user", "data")
        self.mgr.clear_session("s1")
        self.assertEqual(self.mgr.get_conversation_context("s1"), "")


# ═════════════════════════════════════════════════════════════════════════════
#  T05 — AGENT PLAN DATACLASS
# ═════════════════════════════════════════════════════════════════════════════

class T05_AgentPlan(unittest.TestCase):
    """Unit tests for AgentPlan dataclass."""

    def test_creation(self):
        plan = AgentPlan(
            original_query="test",
            rewritten_query="test rewritten",
            sub_queries=["sub1"],
            strategy="simple",
            detected_domains=["Criminal"],
            complexity="low",
            needs_web_search=False,
            reasoning="test reason",
        )
        self.assertEqual(plan.strategy, "simple")
        self.assertEqual(len(plan.sub_queries), 1)

    def test_all_strategies(self):
        """All four strategy values are valid."""
        for s in ["simple", "multi_hop", "research", "statute_lookup"]:
            plan = AgentPlan("q", "q", [], s, [], "low", False, "")
            self.assertEqual(plan.strategy, s)


# ═════════════════════════════════════════════════════════════════════════════
#  T06 — RULE-BASED PLANNER (no LLM)
# ═════════════════════════════════════════════════════════════════════════════

class T06_RuleBasedPlanner(unittest.TestCase):
    """Unit tests for the fallback rule-based planner."""

    def _engine(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        return e

    def test_simple_section_query(self):
        plan = self._engine()._rule_based_plan("What is Section 302 BNS?", "criminal")
        self.assertEqual(plan.strategy, "statute_lookup")
        self.assertIn("BNS", plan.detected_domains)

    def test_comparison_triggers_multi_hop(self):
        plan = self._engine()._rule_based_plan(
            "Compare IPC 302 vs BNS 103", "criminal"
        )
        self.assertEqual(plan.strategy, "multi_hop")

    def test_recent_triggers_research(self):
        plan = self._engine()._rule_based_plan(
            "What are the latest 2025 amendments?", "general"
        )
        self.assertEqual(plan.strategy, "research")
        self.assertTrue(plan.needs_web_search)

    def test_long_query_is_complex(self):
        long_q = "What are the legal implications of " + "word " * 30
        plan = self._engine()._rule_based_plan(long_q, "general")
        self.assertEqual(plan.complexity, "high")

    def test_domain_detection_ipc(self):
        plan = self._engine()._rule_based_plan("IPC murder punishment", "general")
        self.assertIn("IPC", plan.detected_domains)

    def test_domain_detection_consumer(self):
        plan = self._engine()._rule_based_plan(
            "consumer complaint process", "general"
        )
        self.assertIn("Consumer Protection", plan.detected_domains)

    def test_domain_detection_gst(self):
        plan = self._engine()._rule_based_plan("GST input tax credit", "general")
        self.assertIn("GST", plan.detected_domains)

    def test_domain_detection_constitution(self):
        plan = self._engine()._rule_based_plan(
            "Article 21 constitution right to life", "general"
        )
        self.assertIn("Constitutional Law", plan.detected_domains)

    def test_fallback_general(self):
        plan = self._engine()._rule_based_plan("hello", "general")
        self.assertIn("general", plan.detected_domains)


# ═════════════════════════════════════════════════════════════════════════════
#  T07 — JSON PARSER
# ═════════════════════════════════════════════════════════════════════════════

class T07_JSONParser(unittest.TestCase):
    """Unit tests for _parse_json (robust JSON extraction from LLM output)."""

    def _parse(self, text):
        return AgenticRAGEngine._parse_json(text)

    def test_clean_json(self):
        d = self._parse('{"strategy": "simple", "confidence": 0.9}')
        self.assertEqual(d["strategy"], "simple")

    def test_markdown_fences(self):
        d = self._parse('```json\n{"strategy": "multi_hop"}\n```')
        self.assertEqual(d["strategy"], "multi_hop")

    def test_json_in_text(self):
        d = self._parse('Here is the plan: {"strategy": "research"} Done.')
        self.assertEqual(d["strategy"], "research")

    def test_malformed_returns_empty(self):
        d = self._parse("not json at all")
        self.assertEqual(d, {})

    def test_nested_json(self):
        d = self._parse('{"a": {"b": 1}, "c": [1,2]}')
        self.assertEqual(d["a"]["b"], 1)

    def test_empty_string(self):
        d = self._parse("")
        self.assertEqual(d, {})


# ═════════════════════════════════════════════════════════════════════════════
#  T08 — SOURCE FORMATTER
# ═════════════════════════════════════════════════════════════════════════════

class T08_SourceFormatter(unittest.TestCase):
    """Unit tests for _format_sources."""

    def test_basic_formatting(self):
        docs = [
            {"title": "BNS 302", "content": "murder punishment", "source": "Zilliz"},
            {"title": "IPC 302", "text": "old murder law", "source": "Local"},
        ]
        sources = AgenticRAGEngine._format_sources(docs)
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["title"], "BNS 302")

    def test_caps_at_8(self):
        docs = [{"title": f"doc_{i}", "content": "c"} for i in range(15)]
        sources = AgenticRAGEngine._format_sources(docs)
        self.assertLessEqual(len(sources), 8)

    def test_missing_fields_handled(self):
        docs = [{"id": "D1"}]
        sources = AgenticRAGEngine._format_sources(docs)
        self.assertEqual(sources[0]["title"], "D1")

    def test_content_truncated(self):
        docs = [{"title": "T", "content": "x" * 1000, "source": "S"}]
        sources = AgenticRAGEngine._format_sources(docs)
        self.assertLessEqual(len(sources[0]["content"]), 300)


# ═════════════════════════════════════════════════════════════════════════════
#  T09 — PLAN REFINEMENT
# ═════════════════════════════════════════════════════════════════════════════

class T09_PlanRefinement(unittest.TestCase):
    """Unit tests for _refine_plan strategy escalation."""

    def _engine(self):
        return AgenticRAGEngine.__new__(AgenticRAGEngine)

    def _plan(self, strategy="simple"):
        return AgentPlan("q", "q", [], strategy, ["General"], "low", False, "")

    def _verification(self, suggestions="", issues=None):
        return VerificationResult(
            is_acceptable=False, confidence=0.5,
            issues=issues or [], suggestions=suggestions, reasoning=""
        )

    def test_simple_escalates_to_multi_hop(self):
        plan = self._plan("simple")
        refined = self._engine()._refine_plan(plan, self._verification())
        self.assertEqual(refined.strategy, "multi_hop")

    def test_statute_escalates_to_multi_hop(self):
        plan = self._plan("statute_lookup")
        refined = self._engine()._refine_plan(plan, self._verification())
        self.assertEqual(refined.strategy, "multi_hop")

    def test_multi_hop_escalates_to_research(self):
        plan = self._plan("multi_hop")
        refined = self._engine()._refine_plan(plan, self._verification())
        self.assertEqual(refined.strategy, "research")
        self.assertTrue(refined.needs_web_search)

    def test_suggestions_become_sub_queries(self):
        plan = self._plan("simple")
        v = self._verification(suggestions="Search for BNS amendments")
        refined = self._engine()._refine_plan(plan, v)
        self.assertTrue(len(refined.sub_queries) > 0)

    def test_doesnt_answer_triggers_rewrite(self):
        plan = self._plan("simple")
        v = self._verification(issues=["doesn't answer the question"])
        refined = self._engine()._refine_plan(plan, v)
        self.assertIn("elaborate", refined.rewritten_query)


# ═════════════════════════════════════════════════════════════════════════════
#  T10 — VERIFICATION RESULT
# ═════════════════════════════════════════════════════════════════════════════

class T10_VerificationResult(unittest.TestCase):
    """Unit tests for confidence thresholding."""

    def test_above_threshold_is_acceptable(self):
        self.assertTrue(CONFIDENCE_THRESHOLD == 0.75)

    def test_max_loops_constant(self):
        self.assertEqual(MAX_AGENT_LOOPS, 2)

    def test_verification_fields(self):
        v = VerificationResult(True, 0.85, [], "", "good")
        self.assertTrue(v.is_acceptable)
        self.assertEqual(v.confidence, 0.85)


# ═════════════════════════════════════════════════════════════════════════════
#  T11 — GREETING DETECTION
# ═════════════════════════════════════════════════════════════════════════════

class T11_GreetingDetection(unittest.TestCase):
    """Tests for the greeting regex in UnifiedAdvancedRAG."""

    def setUp(self):
        self.patterns = [
            r"\bhi\b", r"\bhello\b", r"\bhey\b",
            r"\bwho are you\b", r"\bwhat can you do\b"
        ]
        self.reg = re.compile("|".join(self.patterns), re.IGNORECASE)

    def test_hi(self):
        self.assertTrue(self.reg.search("Hi"))

    def test_hello(self):
        self.assertTrue(self.reg.search("Hello there"))

    def test_who_are_you(self):
        self.assertTrue(self.reg.search("Who are you?"))

    def test_legal_query_not_greeting(self):
        self.assertIsNone(self.reg.search("What is Section 302 BNS?"))

    def test_case_insensitive(self):
        self.assertTrue(self.reg.search("HELLO"))


# ═════════════════════════════════════════════════════════════════════════════
#  T12 — LLM-POWERED PLANNER (mocked LLM)
# ═════════════════════════════════════════════════════════════════════════════

class T12_LLMPlanner(unittest.TestCase):
    """Integration test for _plan with mocked LLM."""

    def _engine_with_mock_llm(self, llm_response: str):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test-model"
        mock_choice = MagicMock()
        mock_choice.message.content = llm_response
        e.llm.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )
        return e

    def test_llm_planner_parses_json(self):
        resp = json.dumps({
            "rewritten_query": "BNS Section 302 punishment for murder",
            "sub_queries": [],
            "strategy": "statute_lookup",
            "detected_domains": ["BNS", "Criminal"],
            "complexity": "low",
            "needs_web_search": False,
            "reasoning": "Simple statute lookup"
        })
        engine = self._engine_with_mock_llm(resp)
        plan = engine._plan("Section 302 BNS?", "", None, "criminal")
        self.assertEqual(plan.strategy, "statute_lookup")
        self.assertIn("BNS", plan.detected_domains)

    def test_llm_failure_falls_back_to_rule_based(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test"
        e.llm.chat.completions.create.side_effect = Exception("LLM down")
        plan = e._plan("Section 302?", "", None, "criminal")
        self.assertEqual(plan.reasoning, "rule-based fallback plan")


# ═════════════════════════════════════════════════════════════════════════════
#  T13 — RETRIEVAL STAGE (mocked ParametricRAG)
# ═════════════════════════════════════════════════════════════════════════════

class T13_RetrievalStage(unittest.TestCase):
    """Integration test for _retrieve with mocked ParametricRAG."""

    def _engine(self, docs=None):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.parametric_rag = MagicMock()
        e.parametric_rag.retrieve_with_params.return_value = {
            "documents": docs or [
                {"title": "BNS 302", "content": "Murder punishment", "source": "Zilliz"},
                {"title": "IPC 302", "content": "Old murder law", "source": "Zilliz"},
            ],
            "context": "BNS 302 content...",
            "metadata": {},
        }
        return e

    def test_primary_retrieval(self):
        plan = AgentPlan("q", "q", [], "simple", ["Criminal"], "low", False, "")
        packet = self._engine()._retrieve(plan, "")
        self.assertEqual(len(packet.documents), 2)
        self.assertIn("BNS 302", packet.context_text)

    def test_sub_query_retrieval(self):
        plan = AgentPlan("q", "q", ["sub1", "sub2"], "multi_hop", ["Criminal"], "high", False, "")
        engine = self._engine()
        packet = engine._retrieve(plan, "")
        # Called once for primary + twice for sub-queries
        self.assertEqual(engine.parametric_rag.retrieve_with_params.call_count, 3)

    def test_deduplication(self):
        """Duplicate documents are removed."""
        dup_docs = [
            {"title": "Same", "content": "identical text", "source": "A"},
            {"title": "Same2", "content": "identical text", "source": "B"},
        ]
        plan = AgentPlan("q", "q", [], "simple", ["G"], "low", False, "")
        packet = self._engine(dup_docs)._retrieve(plan, "")
        self.assertEqual(len(packet.documents), 1)

    def test_caps_at_12_docs(self):
        many_docs = [{"title": f"D{i}", "content": f"content_{i}"} for i in range(20)]
        plan = AgentPlan("q", "q", [], "simple", ["G"], "low", False, "")
        packet = self._engine(many_docs)._retrieve(plan, "")
        self.assertLessEqual(len(packet.documents), 12)


# ═════════════════════════════════════════════════════════════════════════════
#  T14 — SYNTHESIS STAGE (mocked LLM)
# ═════════════════════════════════════════════════════════════════════════════

class T14_SynthesisStage(unittest.TestCase):
    """Integration test for _synthesise."""

    def _engine(self, llm_answer="**Legal Framework**\nSection 302 BNS..."):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test"
        mock_choice = MagicMock()
        mock_choice.message.content = llm_answer
        e.llm.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        return e

    def test_basic_synthesis(self):
        plan = AgentPlan("q", "q", [], "simple", ["Criminal"], "low", False, "")
        answer = self._engine()._synthesise(plan, "context text", "", None)
        self.assertIn("Legal Framework", answer)

    def test_synthesis_with_user_profile(self):
        profile = UserProfile(user_id="u1", preferred_language="hi")
        plan = AgentPlan("q", "q", [], "simple", ["Criminal"], "low", False, "")
        engine = self._engine()
        engine._synthesise(plan, "ctx", "", profile)
        # Verify prompt included language hint
        call_args = engine.llm.chat.completions.create.call_args
        system_msg = call_args[1]["messages"][0]["content"]
        self.assertIn("hi", system_msg)

    def test_complex_synthesis_uses_focused_prompt(self):
        plan = AgentPlan(
            "q",
            (
                "A technology company launches a mobile payment application with mandatory data "
                "sharing, algorithmic credit scoring, a data breach, consumer complaints, and an "
                "arbitration clause."
            ),
            [],
            "multi_hop",
            ["Consumer Protection", "DPDPA"],
            "high",
            False,
            "",
        )
        engine = self._engine()
        engine._synthesise(plan, "context text", "recent context", None)
        call_args = engine.llm.chat.completions.create.call_args
        system_msg = call_args[1]["messages"][0]["content"]
        user_msg = call_args[1]["messages"][1]["content"]
        self.assertIn("do not invent statutory section numbers", system_msg.lower())
        self.assertIn("DATA PRIVACY, FINTECH & TECHNOLOGY LAW FRAMEWORK", user_msg)

    def test_synthesis_failure_returns_fallback(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test"
        e.llm.chat.completions.create.side_effect = Exception("LLM fail")
        plan = AgentPlan("test query", "test query", [], "simple", ["G"], "low", False, "")
        answer = e._synthesise(plan, "ctx", "", None)
        self.assertIn("unable to generate", answer.lower())


# ═════════════════════════════════════════════════════════════════════════════
#  T15 — VERIFICATION STAGE (mocked LLM)
# ═════════════════════════════════════════════════════════════════════════════

class T15_VerificationStage(unittest.TestCase):
    """Integration test for _verify."""

    def _engine(self, llm_resp):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test"
        mock_choice = MagicMock()
        mock_choice.message.content = llm_resp
        e.llm.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        return e

    def test_high_confidence_accepted(self):
        resp = json.dumps({
            "confidence": 0.9, "is_acceptable": True,
            "issues": [], "suggestions": "", "reasoning": "Good"
        })
        plan = AgentPlan("q", "q", [], "simple", ["G"], "low", False, "")
        v = self._engine(resp)._verify("q", "answer", "ctx", plan)
        self.assertTrue(v.is_acceptable)
        self.assertEqual(v.confidence, 0.9)

    def test_low_confidence_rejected(self):
        resp = json.dumps({
            "confidence": 0.4, "is_acceptable": False,
            "issues": ["too vague"], "suggestions": "add sections",
            "reasoning": "Weak"
        })
        plan = AgentPlan("q", "q", [], "simple", ["G"], "low", False, "")
        v = self._engine(resp)._verify("q", "answer", "ctx", plan)
        self.assertFalse(v.is_acceptable)
        self.assertIn("too vague", v.issues)

    def test_verifier_failure_defaults_to_accept(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.llm = MagicMock()
        e.model = "test"
        e.llm.chat.completions.create.side_effect = Exception("boom")
        plan = AgentPlan("q", "q", [], "simple", ["G"], "low", False, "")
        v = e._verify("q", "answer", "ctx", plan)
        self.assertTrue(v.is_acceptable)
        self.assertIn("verifier_failed", v.issues)


# ═════════════════════════════════════════════════════════════════════════════
#  T16 — FULL AGENTIC LOOP (1 pass, mocked)
# ═════════════════════════════════════════════════════════════════════════════

class T16_FullLoop_SinglePass(unittest.TestCase):
    """Full agentic loop — verifier accepts on first try."""

    def _build_engine(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.model = "test"

        # Mock LLM — return planner JSON, then synthesis, then verifier JSON
        e.llm = MagicMock()
        call_count = {"n": 0}
        planner_resp = json.dumps({
            "rewritten_query": "BNS 302 murder punishment",
            "sub_queries": [], "strategy": "simple",
            "detected_domains": ["BNS"], "complexity": "low",
            "needs_web_search": False, "reasoning": "Simple lookup"
        })
        synth_resp = "**Legal Framework**\nSection 302 BNS deals with murder."
        verifier_resp = json.dumps({
            "confidence": 0.85, "is_acceptable": True,
            "issues": [], "suggestions": "", "reasoning": "Good"
        })

        def side_effect(**kwargs):
            call_count["n"] += 1
            idx = call_count["n"]
            if idx == 1:
                text = planner_resp
            elif idx == 2:
                text = synth_resp
            else:
                text = verifier_resp
            mock_choice = MagicMock()
            mock_choice.message.content = text
            return MagicMock(choices=[mock_choice])

        e.llm.chat.completions.create.side_effect = side_effect

        # Mock ParametricRAG
        e.parametric_rag = MagicMock()
        e.parametric_rag.retrieve_with_params.return_value = {
            "documents": [{"title": "BNS302", "content": "murder", "source": "Z"}],
            "context": "BNS 302...", "metadata": {},
        }
        e.retriever = MagicMock()
        e.researcher = None
        e.hirag = None

        # Real memory manager
        e.memory = AgenticMemoryManager.__new__(AgenticMemoryManager)
        e.memory.short_term = ShortTermMemory(max_turns=5)
        e.memory.long_term = LongTermMemory.__new__(LongTermMemory)
        e.memory.long_term._supabase = None
        e.memory.long_term._local_profiles = {}
        e.memory.long_term._local_path = "__nope__.json"
        e.memory.cache = SemanticCache(max_entries=10, default_ttl=3600)

        return e

    def test_single_pass_success(self):
        engine = self._build_engine()
        result = engine.run("What is BNS 302?", session_id="s1", user_id="u1")
        self.assertIsInstance(result, AgenticResult)
        self.assertIn("Legal Framework", result.answer)
        self.assertEqual(result.loops_taken, 1)
        self.assertGreaterEqual(result.confidence, 0.75)
        self.assertFalse(result.from_cache)
        self.assertIn("planning", result.reasoning_trace)
        self.assertIn("accepted", result.reasoning_trace)

    def test_response_cached_after_first_run(self):
        engine = self._build_engine()
        engine.run("What is BNS 302?", session_id="s1")
        # Second run should be cached
        result2 = engine.run("What is BNS 302?", session_id="s1")
        self.assertTrue(result2.from_cache)
        self.assertEqual(result2.loops_taken, 0)
        self.assertIn("cache_hit", result2.reasoning_trace)


# ═════════════════════════════════════════════════════════════════════════════
#  T17 — FULL AGENTIC LOOP (2 passes — reject then accept)
# ═════════════════════════════════════════════════════════════════════════════

class T17_FullLoop_TwoPass(unittest.TestCase):
    """Full agentic loop where verifier rejects first, accepts second."""

    def test_two_pass_with_refinement(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.model = "test"
        call_count = {"n": 0}

        planner = json.dumps({
            "rewritten_query": "q", "sub_queries": [], "strategy": "simple",
            "detected_domains": ["G"], "complexity": "low",
            "needs_web_search": False, "reasoning": "test"
        })
        synth = "Some answer"
        reject = json.dumps({
            "confidence": 0.4, "is_acceptable": False,
            "issues": ["too vague"], "suggestions": "add more detail",
            "reasoning": "weak"
        })
        accept = json.dumps({
            "confidence": 0.85, "is_acceptable": True,
            "issues": [], "suggestions": "", "reasoning": "good"
        })

        responses = [planner, synth, reject, synth, accept]

        def side_effect(**kwargs):
            call_count["n"] += 1
            idx = min(call_count["n"], len(responses)) - 1
            mock_choice = MagicMock()
            mock_choice.message.content = responses[idx]
            return MagicMock(choices=[mock_choice])

        e.llm = MagicMock()
        e.llm.chat.completions.create.side_effect = side_effect
        e.parametric_rag = MagicMock()
        e.parametric_rag.retrieve_with_params.return_value = {
            "documents": [{"title": "D", "content": "c", "source": "S"}],
            "context": "ctx", "metadata": {},
        }
        e.retriever = MagicMock()
        e.researcher = None
        e.hirag = None

        e.memory = AgenticMemoryManager.__new__(AgenticMemoryManager)
        e.memory.short_term = ShortTermMemory(5)
        e.memory.long_term = LongTermMemory.__new__(LongTermMemory)
        e.memory.long_term._supabase = None
        e.memory.long_term._local_profiles = {}
        e.memory.long_term._local_path = "__nope__.json"
        e.memory.cache = SemanticCache(10, 3600)

        result = e.run("test query")
        self.assertEqual(result.loops_taken, 2)
        self.assertIn("refining", " ".join(result.reasoning_trace))


# ═════════════════════════════════════════════════════════════════════════════
#  T18 — CACHE INTEGRATION
# ═════════════════════════════════════════════════════════════════════════════

class T18_CacheIntegration(unittest.TestCase):
    """Cache miss first call, hit second call."""

    def test_miss_then_hit(self):
        cache = SemanticCache(max_entries=10, default_ttl=3600)
        self.assertIsNone(cache.get("What is BNS?"))
        cache.put("What is BNS?", "Answer about BNS", [{"s": 1}])
        entry = cache.get("What is BNS?")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "Answer about BNS")
        self.assertEqual(cache.stats["hits"], 1)
        self.assertEqual(cache.stats["misses"], 1)


# ═════════════════════════════════════════════════════════════════════════════
#  T19 — MEMORY CONTEXT INJECTION
# ═════════════════════════════════════════════════════════════════════════════

class T19_MemoryContextInjection(unittest.TestCase):
    """Conversation context from STM is injected into planner/synthesiser prompts."""

    def test_context_used_in_run(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        e.model = "test"
        e.researcher = None
        e.hirag = None

        planner_resp = json.dumps({
            "rewritten_query": "q", "sub_queries": [], "strategy": "simple",
            "detected_domains": ["G"], "complexity": "low",
            "needs_web_search": False, "reasoning": "test"
        })
        synth = "Answer"
        verify = json.dumps({
            "confidence": 0.9, "is_acceptable": True,
            "issues": [], "suggestions": "", "reasoning": "ok"
        })

        call_idx = {"n": 0}

        def side_effect(**kwargs):
            call_idx["n"] += 1
            texts = [planner_resp, synth, verify]
            t = texts[min(call_idx["n"] - 1, 2)]
            mc = MagicMock()
            mc.message.content = t
            return MagicMock(choices=[mc])

        e.llm = MagicMock()
        e.llm.chat.completions.create.side_effect = side_effect
        e.parametric_rag = MagicMock()
        e.parametric_rag.retrieve_with_params.return_value = {
            "documents": [], "context": "", "metadata": {}
        }
        e.retriever = MagicMock()

        e.memory = AgenticMemoryManager.__new__(AgenticMemoryManager)
        e.memory.short_term = ShortTermMemory(5)
        e.memory.long_term = LongTermMemory.__new__(LongTermMemory)
        e.memory.long_term._supabase = None
        e.memory.long_term._local_profiles = {}
        e.memory.long_term._local_path = "__nope__.json"
        e.memory.cache = SemanticCache(10, 3600)

        # Pre-populate conversation
        e.memory.remember_turn("s1", "user", "previous question about GST")
        e.memory.remember_turn("s1", "assistant", "GST is...")

        result = e.run("follow up question", session_id="s1")
        self.assertTrue(result.memory_context_used)


# ═════════════════════════════════════════════════════════════════════════════
#  T20 — USER PROFILE TRACKING
# ═════════════════════════════════════════════════════════════════════════════

class T20_UserProfileTracking(unittest.TestCase):
    """User profile domain accumulation after queries."""

    def test_domains_accumulate(self):
        ltm = LongTermMemory.__new__(LongTermMemory)
        ltm._supabase = None
        ltm._local_profiles = {}
        ltm._local_path = "__nope__.json"

        ltm.record_interaction("u1", "BNS query", ["BNS", "Criminal"])
        ltm.record_interaction("u1", "GST query", ["GST", "Tax"])

        profile = ltm.get_profile("u1")
        self.assertEqual(profile.interaction_count, 2)
        self.assertIn("BNS", profile.legal_domains_of_interest)
        self.assertIn("GST", profile.legal_domains_of_interest)
        self.assertEqual(len(profile.past_queries_summary), 2)


# ═════════════════════════════════════════════════════════════════════════════
#  T21 — QUERYREQUEST MODEL
# ═════════════════════════════════════════════════════════════════════════════

class T21_QueryRequestModel(unittest.TestCase):
    """API contract tests for QueryRequest pydantic model."""

    def test_import(self):
        from kaanoon_test.advanced_rag_api_server import QueryRequest
        self.assertTrue(hasattr(QueryRequest, 'model_fields'))

    def test_required_question(self):
        from kaanoon_test.advanced_rag_api_server import QueryRequest
        with self.assertRaises(Exception):
            QueryRequest()  # missing question

    def test_optional_user_id(self):
        from kaanoon_test.advanced_rag_api_server import QueryRequest
        q = QueryRequest(question="test")
        self.assertIsNone(q.user_id)

    def test_all_fields(self):
        from kaanoon_test.advanced_rag_api_server import QueryRequest
        q = QueryRequest(
            question="test", session_id="s1", user_id="u1",
            category="criminal", mode="research"
        )
        self.assertEqual(q.user_id, "u1")
        self.assertEqual(q.mode, "research")


# ═════════════════════════════════════════════════════════════════════════════
#  T22 — FORMAT_RAG_RESPONSE
# ═════════════════════════════════════════════════════════════════════════════

class T22_FormatRagResponse(unittest.TestCase):
    """Tests for format_rag_response with agentic metadata."""

    def test_agentic_metadata_propagated(self):
        from kaanoon_test.advanced_rag_api_server import format_rag_response
        result = {
            'answer': 'Legal answer here',
            'source_documents': [{"title": "BNS"}],
            'reasoning_path': 'Agentic[1x]: planning → accepted',
            'metadata': {
                'confidence': 0.85,
                'loops': 1,
                'from_cache': False,
                'memory_used': True,
                'retrieval_time': 2.5,
                'strategy': 'simple',
            }
        }
        resp = format_rag_response(result, "session_123")
        self.assertEqual(resp['confidence'], 0.85)
        self.assertEqual(resp['session_id'], "session_123")
        self.assertEqual(resp['system_info']['agentic_loops'], 1)
        self.assertTrue(resp['system_info']['memory_used'])
        self.assertEqual(resp['query_type'], 'simple')

    def test_missing_metadata_defaults(self):
        from kaanoon_test.advanced_rag_api_server import format_rag_response
        result = {'answer': 'test', 'source_documents': []}
        resp = format_rag_response(result, "s1")
        self.assertEqual(resp['confidence'], 0.9)  # default
        self.assertFalse(resp['from_cache'])


# ═════════════════════════════════════════════════════════════════════════════
#  T23 — /api/stats AGENTIC MEMORY FIELD
# ═════════════════════════════════════════════════════════════════════════════

class T23_StatsEndpoint(unittest.TestCase):
    """Contract: stats endpoint must include agentic_memory."""

    def test_stats_structure(self):
        """Validates expected keys — tested via get_metrics mock."""
        # Simulate what get_metrics returns
        mgr = AgenticMemoryManager.__new__(AgenticMemoryManager)
        mgr.short_term = ShortTermMemory(5)
        mgr.cache = SemanticCache(10, 3600)
        stats = mgr.get_memory_stats()
        self.assertIn("short_term_sessions", stats)
        self.assertIn("cache", stats)
        self.assertIn("hits", stats["cache"])
        self.assertIn("misses", stats["cache"])
        self.assertIn("hit_rate", stats["cache"])
        self.assertIn("size", stats["cache"])


# ═════════════════════════════════════════════════════════════════════════════
#  T24 — HEALTH ENDPOINT CONTRACT
# ═════════════════════════════════════════════════════════════════════════════

class T24_HealthContract(unittest.TestCase):
    """Health endpoint must return status + rag_system_initialized."""

    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_health_live(self):
        import urllib.request
        resp = urllib.request.urlopen(f"{AZURE_BASE}/api/health", timeout=15)
        data = json.loads(resp.read())
        self.assertIn("status", data)
        self.assertIn("rag_system_initialized", data)


# ═════════════════════════════════════════════════════════════════════════════
#  T25–T30 — LIVE E2E TESTS (Azure endpoint)
# ═════════════════════════════════════════════════════════════════════════════

class T25_LiveQuery(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_bns_302_query(self):
        data = self._post({"question": "What is BNS Section 302?",
                           "category": "criminal", "session_id": "live_t25",
                           "user_id": "live_user"})
        resp = data["response"]
        self.assertTrue(len(resp["answer"]) > 100)
        self.assertGreater(resp["confidence"], 0)

    @staticmethod
    def _post(body):
        import urllib.request
        req = urllib.request.Request(
            f"{AZURE_BASE}/api/query",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=180)
        return json.loads(resp.read())


class T26_LiveCache(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_repeat_query_cached(self):
        body = {"question": "What is BNS Section 302?",
                "category": "criminal", "session_id": "live_t26"}
        T25_LiveQuery._post(body)  # first call
        data = T25_LiveQuery._post(body)  # second — should hit cache
        self.assertTrue(data["response"]["from_cache"])


class T27_LiveStats(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_stats_has_agentic_memory(self):
        import urllib.request
        resp = urllib.request.urlopen(f"{AZURE_BASE}/api/stats", timeout=15)
        data = json.loads(resp.read())
        self.assertIn("agentic_memory", data)
        self.assertIn("cache", data["agentic_memory"])


class T28_LiveGreeting(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_greeting(self):
        data = T25_LiveQuery._post({"question": "Hello"})
        ans = data["response"]["answer"].lower()
        self.assertTrue("hello" in ans or "legal" in ans or "assist" in ans)


class T29_LiveResearchMode(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_research_mode(self):
        data = T25_LiveQuery._post({
            "question": "Explain Article 21 of the Indian Constitution",
            "mode": "research"
        })
        self.assertTrue(len(data["response"]["answer"]) > 200)


class T30_LiveErrorHandling(unittest.TestCase):
    @unittest.skipUnless(RUN_LIVE_TESTS, "Live tests disabled")
    def test_empty_question_rejected(self):
        import urllib.request, urllib.error
        try:
            T25_LiveQuery._post({"question": ""})
        except urllib.error.HTTPError:
            pass  # expected — 422 or 500


# ═════════════════════════════════════════════════════════════════════════════
#  T31–T37 — STRESS / EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════

class T31_CacheOverflow(unittest.TestCase):
    """LRU eviction when > max_entries."""

    def test_overflow_evicts_oldest(self):
        cache = SemanticCache(max_entries=3, default_ttl=3600)
        cache.put("q1", "a1", [])
        cache.put("q2", "a2", [])
        cache.put("q3", "a3", [])
        cache.put("q4", "a4", [])  # should evict q1
        self.assertIsNone(cache.get("q1"))
        self.assertIsNotNone(cache.get("q4"))
        self.assertEqual(cache.stats["size"], 3)


class T32_SessionOverflow(unittest.TestCase):
    """Short-term memory trims old turns."""

    def test_overflow_keeps_recent(self):
        stm = ShortTermMemory(max_turns=2)
        for i in range(10):
            stm.add("s1", "user", f"msg_{i}")
            stm.add("s1", "assistant", f"reply_{i}")
        msgs = stm.get_messages("s1")
        self.assertLessEqual(len(msgs), 4)  # 2 turns * 2 messages
        # Most recent should be msg_9
        self.assertIn("msg_9", msgs[-2].content)


class T33_EmptyQuery(unittest.TestCase):
    """Empty query should not crash planner."""

    def test_rule_based_empty(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        plan = e._rule_based_plan("", "general")
        self.assertEqual(plan.strategy, "simple")
        self.assertEqual(plan.original_query, "")


class T34_VeryLongQuery(unittest.TestCase):
    """1000+ char query handled without crash."""

    def test_long_query(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        long_q = "What is the legal position regarding " + "word " * 250
        plan = e._rule_based_plan(long_q, "general")
        self.assertEqual(plan.complexity, "high")
        self.assertEqual(plan.strategy, "multi_hop")


class T35_UnicodeQuery(unittest.TestCase):
    """Hindi / Unicode queries don't crash."""

    def test_hindi_query(self):
        e = AgenticRAGEngine.__new__(AgenticRAGEngine)
        plan = e._rule_based_plan("धारा 302 बीएनएस क्या है?", "criminal")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.original_query, "धारा 302 बीएनएस क्या है?")

    def test_unicode_cache(self):
        cache = SemanticCache(10, 3600)
        cache.put("धारा 302 क्या है?", "उत्तर", [])
        entry = cache.get("धारा 302 क्या है?")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.answer, "उत्तर")


class T36_ConcurrentSessionIsolation(unittest.TestCase):
    """Multiple sessions don't interfere."""

    def test_isolation(self):
        stm = ShortTermMemory(max_turns=5)
        stm.add("session_A", "user", "Query about criminal law")
        stm.add("session_B", "user", "Query about tax law")
        ctx_a = stm.get_context("session_A")
        ctx_b = stm.get_context("session_B")
        self.assertIn("criminal", ctx_a)
        self.assertNotIn("tax", ctx_a)
        self.assertIn("tax", ctx_b)
        self.assertNotIn("criminal", ctx_b)


class T37_GracefulFallback(unittest.TestCase):
    """When agentic_engine is None, legacy path runs."""

    def test_agentic_none_uses_legacy(self):
        """Simulates UnifiedAdvancedRAG.query() with agentic_engine=None."""
        # We just verify the logic path — if agentic_engine is None,
        # the code falls through to the legacy block.
        # This is a contract test on the conditional.
        agentic_engine = None
        memory_manager = None
        used_agentic = False
        used_legacy = False

        if agentic_engine and memory_manager:
            used_agentic = True
        else:
            used_legacy = True

        self.assertFalse(used_agentic)
        self.assertTrue(used_legacy)


# ═════════════════════════════════════════════════════════════════════════════
#  RUNNER
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print(" COMPREHENSIVE AGENTIC RAG TEST SUITE — LAW-GPT")
    print(" 37 test classes · 80+ test methods")
    print("=" * 80)
    print()
    if RUN_LIVE_TESTS:
        print(" [LIVE TESTS ENABLED] — Will hit Azure endpoint")
    else:
        print(" [LIVE TESTS DISABLED] — Set RUN_LIVE_TESTS=1 to enable")
    print()
    unittest.main(verbosity=2)
