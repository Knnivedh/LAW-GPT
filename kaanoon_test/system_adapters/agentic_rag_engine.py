"""
AGENTIC RAG ENGINE — Next-Generation Legal AI (2025-2026 Era)
==============================================================

Transforms LAW-GPT from a linear retrieve→generate pipeline into a
dynamic, goal-oriented **agentic loop** controlled by an LLM agent.

Architecture Overview:
┌─────────────────────────────────────────────────────────┐
│                   AGENTIC RAG ENGINE                     │
│                                                          │
│  User Query                                              │
│     │                                                    │
│     ▼                                                    │
│  ┌────────────┐    ┌───────────┐    ┌──────────────┐    │
│  │ 1. PLANNER │───►│ 2. ROUTER │───►│ 3. RETRIEVER │    │
│  │ (Decompose)│    │ (Strategy)│    │ (Multi-hop)  │    │
│  └────────────┘    └───────────┘    └──────┬───────┘    │
│                                            │             │
│     ┌─────────────┐    ┌──────────┐        ▼             │
│     │ 5. VERIFIER │◄───│ 4. SYNTH │◄── Contexts         │
│     │ (Reflect)   │    │ (Answer) │                      │
│     └──────┬──────┘    └──────────┘                      │
│            │                                             │
│       PASS?─── NO ──► Loop back to PLANNER (max 2)      │
│            │                                             │
│           YES                                            │
│            ▼                                             │
│      Final Answer + Sources + Reasoning Trace            │
│                                                          │
│  Memory: ShortTerm ←→ LongTerm ←→ SemanticCache         │
└─────────────────────────────────────────────────────────┘

Core Capabilities (maps to Agentic RAG concepts):
1. Planning & Decomposition — break complex queries into sub-tasks
2. Query Rewriting & Routing — rewrite poor queries, pick optimal strategy
3. Iterative Multi-hop Retrieval — retrieve → evaluate → re-retrieve
4. Tool Use — RAG + web search + statute lookup + calculator
5. Reflection & Self-Critique — verify answer quality before returning
6. Persistent Memory — short-term + long-term + semantic cache
7. Dynamic Workflow Orchestration — agent decides flow per query
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from kaanoon_test.system_adapters.focused_legal_prompts import (
    build_focused_legal_prompt,
    detect_legal_frameworks_needed,
)
from kaanoon_test.system_adapters.clarification_agent import ClarificationAgent

logger = logging.getLogger(__name__)

# Maximum number of reflection loops before returning best answer
MAX_AGENT_LOOPS = 2
# Confidence threshold: if verifier scores >= this, stop looping
CONFIDENCE_THRESHOLD = 0.75


def _is_stub_answer(answer: str, error_phrases: Tuple[str, ...]) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True
    if any(phrase in text for phrase in error_phrases):
        return True
    return len(text.split()) < 40


# ─── Data Types ──────────────────────────────────────────────────────────────

@dataclass
class AgentPlan:
    """Output of the Planner stage."""
    original_query: str
    rewritten_query: str
    sub_queries: List[str]
    strategy: str            # 'simple' | 'multi_hop' | 'research' | 'statute_lookup'
    detected_domains: List[str]
    complexity: str          # 'low' | 'medium' | 'high'
    needs_web_search: bool
    reasoning: str


@dataclass
class RetrievalPacket:
    """Output of one retrieval pass."""
    documents: List[Dict]
    context_text: str
    source_labels: List[str]
    retrieval_method: str
    retrieval_time: float


@dataclass
class VerificationResult:
    """Output of the Verifier / Reflection stage."""
    is_acceptable: bool
    confidence: float        # 0.0 – 1.0
    issues: List[str]
    suggestions: str         # what to improve if looping
    reasoning: str


@dataclass
class AgenticResult:
    """Final output of the Agentic RAG Engine."""
    answer: str
    sources: List[Dict]
    reasoning_trace: List[str]
    confidence: float
    loops_taken: int
    plan: Optional[AgentPlan]
    total_time: float
    from_cache: bool
    memory_context_used: bool


# ─── Agentic RAG Engine ─────────────────────────────────────────────────────

class AgenticRAGEngine:
    """
    The brain of the Agentic RAG system.
    Orchestrates planning, retrieval, synthesis, and reflection.
    """

    def __init__(self, *, client_manager, parametric_rag, retriever,
                 memory_manager, hirag=None, researcher=None,
                 pageindex_retriever=None):
        """
        Args:
            client_manager: GroqClientManager (key-rotating LLM proxy)
            parametric_rag: ParametricRAGSystem (handles advanced retrieval)
            retriever: EnhancedRetriever (direct search)
            memory_manager: AgenticMemoryManager (3-tier memory)
            hirag: HierarchicalThoughtRAG (optional, used for synthesis)
            researcher: DeepResearchAgent (optional, for web search fallback)
            pageindex_retriever: PageIndexRetriever (optional, vectorless
                                 tree-based statute retrieval)
        """
        self.llm = client_manager
        self.parametric_rag = parametric_rag
        self.retriever = retriever
        self.memory = memory_manager
        self.hirag = hirag
        self.researcher = researcher
        self.pageindex_retriever = pageindex_retriever
        self.clarifier = ClarificationAgent(client_manager)
        self.model = "llama-3.3-70b-versatile"
        pi_status = "enabled" if (pageindex_retriever and getattr(pageindex_retriever, "is_available", False)) else "disabled"
        logger.info(f"[AgenticRAGEngine] Initialised with all components (PageIndex: {pi_status})")

    # ═══════════════════════════════════════════════════════════════════════
    #  PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════

    def run(self, user_query: str, *,
            session_id: str = "",
            user_id: str = "",
            category: str = "general",
            chat_history: Optional[List[Dict]] = None,
            simple_mode: bool = False,
            ) -> AgenticResult:
        """
        Main entry point. Runs the full agentic loop.

        Args:
            simple_mode: When True, skip Plan→Verify loop and use a lightweight
                         single-pass retrieval+synthesis. Used for simple factual
                         queries to avoid rate-limiting the 70b model.
        """
        t0 = time.time()
        trace: List[str] = []

        # ── 0. MEMORY: record user turn & check cache ────────────────────
        if session_id:
            self.memory.remember_turn(session_id, "user", user_query)

        # Error phrases that indicate a stale/failed cached response
        _ERROR_PHRASES = (
            "unable to generate", "service issue", "please try again",
            "technical difficulty", "try again later", "error occurred",
            "i encountered an error", "failed to retrieve",
        )

        cached = self.memory.check_cache(user_query)
        if cached:
            _is_stale = (
                len(cached.answer.split()) < 50
                or any(p in cached.answer.lower() for p in _ERROR_PHRASES)
            )
            if _is_stale:
                # Evict the bad cached entry by overwriting with None (or just skip)
                logger.warning("[AGENT] Cached answer is a stub/error — skipping cache")
            else:
                trace.append("cache_hit")
                logger.info("[AGENT] Cache hit — returning cached answer")
                return AgenticResult(
                    answer=cached.answer, sources=cached.sources,
                    reasoning_trace=trace, confidence=0.95,
                    loops_taken=0, plan=None,
                    total_time=time.time() - t0, from_cache=True,
                    memory_context_used=False,
                )

        # ── Conversation context from short-term memory ──────────────────
        conv_context = ""
        if session_id:
            conv_context = self.memory.get_conversation_context(session_id)

        # ── User profile from long-term memory ───────────────────────────
        user_profile = None
        if user_id:
            user_profile = self.memory.get_user_profile(user_id)

        # ── SIMPLE MODE: lightweight single-pass for factual queries ─────
        if simple_mode:
            trace.append("simple_mode")
            logger.info(f"[AGENT] Simple mode: skipping Plan/Verify loop for '{user_query[:60]}'")
            try:
                simple_result = self._simple_mode_answer(user_query, category, session_id)
                if simple_result and len(simple_result.split()) >= 40:
                    if session_id:
                        self.memory.remember_turn(session_id, "assistant", simple_result[:500])
                    if len(simple_result.split()) >= 50:
                        self.memory.cache_response(user_query, simple_result, [])
                    return AgenticResult(
                        answer=simple_result, sources=[],
                        reasoning_trace=trace + ["simple_direct_answer"],
                        confidence=0.80, loops_taken=1, plan=None,
                        total_time=time.time() - t0, from_cache=False,
                        memory_context_used=bool(conv_context),
                    )
            except Exception as e:
                logger.warning(f"[AGENT] Simple mode failed: {e} — falling back to full agentic loop")
            # Fall through to full agentic loop if simple mode fails

        # ── 1. PLAN ──────────────────────────────────────────────────────
        trace.append("planning")
        plan = self._plan(user_query, conv_context, user_profile, category)
        trace.append(f"strategy={plan.strategy}")
        trace.append(f"sub_queries={len(plan.sub_queries)}")
        logger.info(f"[AGENT] Plan: strategy={plan.strategy}, "
                     f"complexity={plan.complexity}, subs={len(plan.sub_queries)}")

        # ── 1b. INTERACTIVE CLARIFICATION (NEW for v3.0) ──────────────────
        # If complexity is high, check for fact gaps before proceeding to RAG
        # NOTE: Removed `not chat_history` constraint — complex scenarios need
        # clarification even in ongoing conversations.
        if plan.complexity == "high":
            trace.append("checking_for_gaps")
            # We use the initial plan reasoned by the LLM as 'pre-retrieval context'
            gaps = self.clarifier.identify_gaps(user_query, plan.reasoning)
            if gaps:
                trace.append("needs_clarification")
                logger.info(f"[AGENT] High complexity detected. Pausing for 5 clarifying questions.")
                return AgenticResult(
                    answer="This is a complex legal scenario. To provide a precise analysis, please clarify the following 5 points:",
                    sources=[{"type": "clarification_needed", "questions": gaps}],
                    reasoning_trace=trace,
                    confidence=0.1,
                    loops_taken=1,
                    plan=plan,
                    total_time=time.time() - t0,
                    from_cache=False,
                    memory_context_used=bool(conv_context),
                )

        # ── AGENTIC LOOP ─────────────────────────────────────────────────
        best_answer = ""
        best_sources: List[Dict] = []
        best_confidence = 0.0
        loops_taken = 0

        for loop_idx in range(MAX_AGENT_LOOPS + 1):
            loops_taken = loop_idx + 1
            trace.append(f"loop_{loop_idx}")

            # ── 2. RETRIEVE ──────────────────────────────────────────────
            retrieval = self._retrieve(plan, conv_context)
            trace.append(f"retrieved_{len(retrieval.documents)}_docs")

            # Merge web research if plan says so
            web_context = ""
            if plan.needs_web_search and self.researcher:
                try:
                    trace.append("web_search")
                    web_context = self.researcher.conduct_research(
                        plan.rewritten_query
                    )
                    logger.info(f"[AGENT] Web research returned {len(web_context)} chars")
                except Exception as e:
                    logger.warning(f"[AGENT] Web research failed: {e}")

            # ── 3. SYNTHESISE ────────────────────────────────────────────
            full_context = retrieval.context_text
            if web_context:
                full_context += "\n\n--- Web Research ---\n" + web_context[:2000]

            answer = self._synthesise(
                plan, full_context, conv_context, user_profile
            )
            trace.append("synthesised")

            # ── 4. VERIFY / REFLECT ──────────────────────────────────────
            if _is_stub_answer(answer, _ERROR_PHRASES):
                trace.append("stub_answer_detected")
                verification = VerificationResult(
                    is_acceptable=False,
                    confidence=0.0,
                    issues=["stub_or_empty_answer"],
                    suggestions="Regenerate with a complete grounded answer and preserve the required legal structure.",
                    reasoning="Synthesiser returned an empty or service-stub answer.",
                )
            else:
                verification = self._verify(
                    user_query, answer, full_context, plan
                )
            trace.append(f"confidence={verification.confidence:.2f}")
            logger.info(f"[AGENT] Loop {loop_idx}: confidence={verification.confidence:.2f}, "
                        f"acceptable={verification.is_acceptable}")

            # Track best
            if verification.confidence > best_confidence:
                best_answer = answer
                best_sources = self._format_sources(retrieval.documents)
                best_confidence = verification.confidence

            if verification.is_acceptable:
                trace.append("accepted")
                break

            # ── NOT ACCEPTABLE → ADAPT PLAN ──────────────────────────────
            if loop_idx < MAX_AGENT_LOOPS:
                trace.append(f"refining: {verification.suggestions[:60]}")
                plan = self._refine_plan(plan, verification)
            else:
                trace.append("max_loops_reached_returning_best")

        # ── 5. POST-PROCESS: Memory updates ──────────────────────────────
        if session_id:
            self.memory.remember_turn(session_id, "assistant", best_answer[:1000])
        if user_id and plan:
            self.memory.update_user_profile(
                user_id, user_query, plan.detected_domains
            )
        # Cache the response — only if answer is substantive (skip error stubs)
        _is_error_answer = any(p in best_answer.lower() for p in _ERROR_PHRASES)
        if not _is_error_answer and len(best_answer.split()) >= 50:
            self.memory.cache_response(user_query, best_answer, best_sources)

        total_time = time.time() - t0
        logger.info(f"[AGENT] Done in {total_time:.1f}s, {loops_taken} loop(s), "
                     f"confidence={best_confidence:.2f}")

        return AgenticResult(
            answer=best_answer,
            sources=best_sources,
            reasoning_trace=trace,
            confidence=best_confidence,
            loops_taken=loops_taken,
            plan=plan,
            total_time=total_time,
            from_cache=False,
            memory_context_used=bool(conv_context),
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  SIMPLE MODE: fast single-pass answer for factual queries
    # ═══════════════════════════════════════════════════════════════════════

    def _simple_mode_answer(self, query: str, category: str, session_id: str = "") -> str:
        """One-shot lightweight answer: retrieve → synthesise with 8b model.

        Uses a single parametric RAG retrieval + llama-3.1-8b-instant prompt.
        Avoids Plan→Verify overhead and conserves 70b TPM quota.
        """
        recent_context = ""
        retrieval_query = query
        if session_id:
            recent_messages = self.memory.get_messages(session_id)
            previous_user_queries = [
                msg.content for msg in recent_messages[:-1]
                if msg.role == "user" and msg.content.strip()
            ]
            previous_assistant_turns = [
                msg.content for msg in recent_messages[:-1]
                if msg.role == "assistant" and msg.content.strip()
            ]
            if previous_user_queries or previous_assistant_turns:
                recent_parts = []
                if previous_user_queries:
                    recent_parts.append(f"Previous user question: {previous_user_queries[-1]}")
                if previous_assistant_turns:
                    recent_parts.append(f"Previous assistant answer: {previous_assistant_turns[-1][:500]}")
                recent_context = "\n".join(recent_parts)

            is_follow_up = bool(re.search(
                r"\b(it|its|that|this|they|them|those|these|there|here)\b|\bunder\s+it\b|\bfor\s+it\b",
                query.lower(),
            ))
            if is_follow_up and recent_context:
                retrieval_query = f"{recent_context}\nFollow-up question: {query}"

        # Retrieve relevant context
        try:
            rag_params = {
                "search_domain": category,
                "complexity": "simple",
                "keywords": retrieval_query.split()[:12],
            }
            retrieval = self.parametric_rag.retrieve_with_params(retrieval_query, rag_params)
            context = retrieval.get("context", "")[:3000]
        except Exception as e:
            logger.warning(f"[SIMPLE] Retrieval failed: {e} — answering from training")
            context = ""

        system_msg = (
            "You are a highly capable Indian legal expert assistant. Answer the question accurately in 150-350 words. "
            "Cite the specific section/article number and act. Mention 1-2 key cases if relevant. "
            "CRITICAL INSTRUCTIONS:\n"
            "1. NEVER use conversational filler like 'Based on the provided context', 'According to the context', or 'I could not find it in the context'. Answer directly with authority.\n"
            "2. If the user asks for a specific statute (e.g. IPC Section 302) and its exact text is missing from the retrieved context, rely on your robust training data for major Indian laws to provide the accurate description. NEVER conflate different sections (e.g., do NOT confuse IPC 301 or 304A with IPC 302).\n"
            "3. End with a one-line ⚠️ Disclaimer that this is general information only."
        )
        user_msg = (
            f"Question: {query}\n\n"
            + (f"Recent conversation context:\n{recent_context}\n\n" if recent_context else "")
            + (f"Retrieved legal context:\n{context}\n\n" if context else "No additional context retrieved. Please use your robust legal knowledge.\n\n")
            + "Answer directly as a legal expert. If the question refers to an earlier topic using words like 'it' or 'that', stay grounded in that earlier legal topic."
        )
        # Use 8b model directly — fast, generous TPM limit
        resp = self.llm.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.15,
            max_tokens=700,
        )
        return resp.choices[0].message.content.strip()

    # ═══════════════════════════════════════════════════════════════════════
    #  STAGE 1: PLANNER — decompose + route + rewrite
    # ═══════════════════════════════════════════════════════════════════════

    def _plan(self, query: str, conv_context: str,
              user_profile: Optional[Any], category: str) -> AgentPlan:
        """
        LLM-powered planner that analyses the query and decides strategy.
        """
        profile_hint = ""
        if user_profile and user_profile.legal_domains_of_interest:
            profile_hint = (
                f"User's areas of interest: {', '.join(user_profile.legal_domains_of_interest[:5])}. "
                f"Interaction count: {user_profile.interaction_count}."
            )

        conv_hint = ""
        if conv_context:
            conv_hint = f"Recent conversation:\n{conv_context[-500:]}\n"

        system_msg = (
            "You are a legal query PLANNER for an Indian law AI system. "
            "Analyse the user query and output a JSON plan.\n\n"
            "Output ONLY valid JSON with these fields:\n"
            "{\n"
            '  "rewritten_query": "<improved, unambiguous version of the query>",\n'
            '  "sub_queries": ["<sub-question 1>", ...],  // empty if simple\n'
            '  "strategy": "<one of: simple | multi_hop | research | statute_lookup>",\n'
            '  "detected_domains": ["<legal domain 1>", ...],\n'
            '  "complexity": "<low | medium | high>",\n'
            '  "needs_web_search": true/false,\n'
            '  "reasoning": "<1-2 sentence explanation>"\n'
            "}\n\n"
            "Strategy guide:\n"
            "- simple: factual / single-section lookup (Section 302 BNS, etc.)\n"
            "- statute_lookup: requires precise statute section text\n"
            "- multi_hop: needs information from multiple sources / acts / cases\n"
            "- research: broad / comparative / opinion / recent developments\n\n"
            "Rewrite ambiguous queries to be specific to Indian law.\n"
            "Detect all relevant legal domains (IPC/BNS, CrPC/BNSS, CPA, GST, IT Act, etc.).\n"
            "Set needs_web_search=true only for very recent events or topics not in law databases."
        )

        user_msg = f"{conv_hint}{profile_hint}\nUser query: {query}\nCategory hint: {category}"

        try:
            resp = self._llm_call(system_msg, user_msg, temperature=0.1, max_tokens=600)
            data = self._parse_json(resp)
            return AgentPlan(
                original_query=query,
                rewritten_query=data.get("rewritten_query", query),
                sub_queries=data.get("sub_queries", []),
                strategy=data.get("strategy", "simple"),
                detected_domains=data.get("detected_domains", [category]),
                complexity=data.get("complexity", "medium"),
                needs_web_search=data.get("needs_web_search", False),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.warning(f"[PLANNER] LLM planner failed: {e}. Using rule-based fallback.")
            return self._rule_based_plan(query, category)

    def _rule_based_plan(self, query: str, category: str) -> AgentPlan:
        """Fallback planner using regex heuristics."""
        q_lower = query.lower()
        strategy = "simple"
        complexity = "low"
        needs_web = False
        sub_queries = []
        domains = [category] if category != "general" else []

        # Detect domains
        domain_map = {
            "ipc": "IPC", "bns": "BNS", "crpc": "CrPC", "bnss": "BNSS",
            "consumer": "Consumer Protection", "gst": "GST", "income tax": "Income Tax",
            "dpdp": "DPDPA", "property": "Property Law", "family": "Family Law",
            "constitution": "Constitutional Law", "contract": "Contract Act",
            "motor vehicle": "Motor Vehicle Act", "arbitration": "Arbitration Act",
        }
        for keyword, domain in domain_map.items():
            if keyword in q_lower and domain not in domains:
                domains.append(domain)

        # Strategy detection
        word_count = len(query.split())
        if word_count > 25 or " and " in q_lower:
            strategy = "multi_hop"
            complexity = "high"
        elif any(k in q_lower for k in ["section", "article", "rule"]):
            strategy = "statute_lookup"
            complexity = "low"
        elif any(k in q_lower for k in ["compare", "difference", "vs", "versus"]):
            strategy = "multi_hop"
            complexity = "medium"
        elif any(k in q_lower for k in ["latest", "recent", "2025", "2026", "new law"]):
            strategy = "research"
            needs_web = True
            complexity = "medium"

        return AgentPlan(
            original_query=query,
            rewritten_query=query,
            sub_queries=sub_queries,
            strategy=strategy,
            detected_domains=domains or ["general"],
            complexity=complexity,
            needs_web_search=needs_web,
            reasoning="rule-based fallback plan",
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  STAGE 2: RETRIEVER — multi-hop, sub-query expansion
    # ═══════════════════════════════════════════════════════════════════════

    def _retrieve(self, plan: AgentPlan, conv_context: str) -> RetrievalPacket:
        """Execute retrieval based on plan strategy."""
        t0 = time.time()
        all_docs: List[Dict] = []

        # Primary retrieval
        rag_params = {
            "search_domain": plan.detected_domains[0] if plan.detected_domains else "general",
            "complexity": plan.complexity,
            "keywords": plan.rewritten_query.split()[:5],
        }

        try:
            primary = self.parametric_rag.retrieve_with_params(
                plan.rewritten_query, rag_params
            )
            primary_docs = primary.get("documents", [])
            all_docs.extend(primary_docs)
        except Exception as e:
            logger.warning(f"[RETRIEVER] Primary retrieval failed: {e}")

        # Sub-query retrieval (multi-hop)
        if plan.strategy in ("multi_hop", "research") and plan.sub_queries:
            for sq in plan.sub_queries[:3]:  # cap at 3 sub-queries
                try:
                    sq_params = {**rag_params, "keywords": sq.split()[:5]}
                    sq_result = self.parametric_rag.retrieve_with_params(sq, sq_params)
                    sq_docs = sq_result.get("documents", [])
                    all_docs.extend(sq_docs)
                except Exception as e:
                    logger.warning(f"[RETRIEVER] Sub-query retrieval failed: {e}")

        # Deduplicate by content hash
        seen = set()
        unique_docs = []
        for doc in all_docs:
            content = str(doc.get("content", doc.get("text", "")))[:200]
            h = hash(content)
            if h not in seen:
                seen.add(h)
                unique_docs.append(doc)

        # Build context string
        context_parts = []
        source_labels = []
        for i, doc in enumerate(unique_docs[:12]):  # cap at 12 docs
            title = doc.get("title", doc.get("id", f"Document {i+1}"))
            content = str(doc.get("content", doc.get("text", "")))[:600]
            source = doc.get("source", "Legal Database")
            context_parts.append(f"[Document {i+1}: {title}]\n{content}\n")
            source_labels.append(f"{title} ({source})")

        retrieval_time = time.time() - t0
        vector_context = "\n".join(context_parts)

        # ── PageIndex Statute Retrieval (vectorless tree-based reasoning) ──────────
        # Activated when: plan.strategy == 'statute_lookup', OR statutory
        # keywords detected in the query (e.g. "Section 302 BNS").
        pi_context = ""
        try:
            from kaanoon_test.system_adapters.pageindex_retriever import PageIndexRetriever  # noqa
            pi = self.pageindex_retriever
            if pi and getattr(pi, "is_available", False):
                should_activate = (
                    plan.strategy == "statute_lookup"
                    or PageIndexRetriever.should_activate(plan.rewritten_query)
                )
                if should_activate:
                    logger.info("[RETRIEVER] PageIndex activated for statute lookup")
                    pi_context = pi.retrieve(plan.rewritten_query)
                    if pi_context:
                        logger.info(f"[RETRIEVER] PageIndex returned {len(pi_context)} chars")
        except Exception as _pi_exc:
            logger.warning(f"[RETRIEVER] PageIndex retrieval failed (non-fatal): {_pi_exc}")

        # Merge: PageIndex (higher precision) prepended before vector context
        if pi_context:
            merged_context = pi_context + "\n\n[VECTOR DB RETRIEVAL]\n" + vector_context
        else:
            merged_context = vector_context

        return RetrievalPacket(
            documents=unique_docs[:12],
            context_text=merged_context,
            source_labels=source_labels,
            retrieval_method=f"{plan.strategy}{'_+pageindex' if pi_context else ''}",
            retrieval_time=retrieval_time,
        )

    # ═══════════════════════════════════════════════════════════════════════
    #  STAGE 3: SYNTHESISER — generate answer from context
    # ═══════════════════════════════════════════════════════════════════════

    def _synthesise(self, plan: AgentPlan, context: str,
                    conv_context: str, user_profile: Optional[Any]) -> str:
        """Generate the answer using LLM with structured legal prompt."""

        # Personalisation hints
        lang_hint = ""
        if user_profile and user_profile.preferred_language != "en":
            lang_hint = f"\nUser prefers responses in: {user_profile.preferred_language}"

        history_hint = ""
        if conv_context:
            history_hint = (
                f"\n\nConversation history (for context continuity):\n"
                f"{conv_context[-400:]}\n"
            )

        framework_ids = detect_legal_frameworks_needed(plan.rewritten_query)
        should_use_focused_prompt = bool(
            framework_ids
            or plan.strategy in ("multi_hop", "research")
            or plan.complexity == "high"
            or len(plan.rewritten_query.split()) > 40
        )

        if should_use_focused_prompt:
            system_msg = (
                "You are an expert Indian legal AI assistant. Follow the provided legal-analysis "
                "instructions exactly, preserve issue-by-issue structure, and do not invent statutory "
                "section numbers or case names. If an exact citation is uncertain, say so rather than "
                "hallucinating it."
                f"{lang_hint}"
            )
            user_msg = build_focused_legal_prompt(
                question=plan.rewritten_query,
                context=(context + history_hint)[:4500],
                query_analysis={
                    "strategy": plan.strategy,
                    "complexity": plan.complexity,
                    "domains": plan.detected_domains,
                    "frameworks": framework_ids,
                },
                conversation_context=conv_context[-400:] if conv_context else "",
            )
        else:
            system_msg = (
                "You are an expert Indian legal AI assistant with encyclopaedic knowledge "
                "of Indian statutes, constitutional law, and Supreme Court / High Court judgments.\n\n"
                "Structure every answer:\n"
                "**Case Summary** → **Legal Framework** (cite specific sections/articles) → "
                "**Key Precedents** (cite actual case names & years) → "
                "**Legal Reasoning** (step-by-step) → **Practical Advice** → **Conclusion**\n\n"
                "Rules:\n"
                "- Cite SPECIFIC sections (e.g., Section 302 BNS, Article 21 Constitution)\n"
                "- Name REAL landmark cases with years\n"
                "- If the retrieved documents don't contain enough info, supplement from your training\n"
                "- For comparative questions, present BOTH sides\n"
                "- If you cannot verify a case name exists, say so explicitly\n"
                "- Aim for 800-1500 words\n"
                "- NEVER use conversational filler like 'Based on the provided context' or 'According to the context'.\n"
                "- NEVER hallucinate the text of a statute. If describing a major section (like IPC 302), provide its true meaning from memory if the retrieved context does not contain its exact wording.\n"
                "- End with ⚠️ Disclaimer"
                f"{lang_hint}"
            )

            user_msg = (
                f"Question: {plan.rewritten_query}\n\n"
                f"Retrieved legal documents:\n{context[:4000]}\n"
                f"{history_hint}\n"
                "Provide a comprehensive legal analysis."
            )

        try:
            answer = self._llm_call(system_msg, user_msg,
                                    temperature=0.3, max_tokens=2500)
            return answer
        except Exception as e:
            logger.error(f"[SYNTHESISER] Primary LLM synthesis failed: {e}. Trying fast fallback...")
            # ── Fallback: use lighter model + shorter prompt ─────────────
            try:
                fallback_usr = (
                    f"You are an Indian law expert. Answer this question based on the context below.\n\n"
                    f"Question: {plan.original_query}\n\n"
                    f"Context (legal documents):\n{context[:2000]}\n\n"
                    f"Give a clear, concise answer in 150-400 words. "
                    f"Cite specific sections and case law where relevant, and do not invent uncertain citations."
                )
                resp = self.llm.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a concise Indian law assistant."},
                        {"role": "user", "content": fallback_usr},
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                fallback_answer = resp.choices[0].message.content.strip()
                if len(fallback_answer.split()) >= 30:
                    logger.info(f"[SYNTHESISER] Fallback model succeeded ({len(fallback_answer.split())} words)")
                    return fallback_answer
            except Exception as e2:
                logger.error(f"[SYNTHESISER] Fallback model also failed: {e2}")
            return (
                f"I was unable to generate a complete answer due to a service issue. "
                f"Based on the retrieved documents, your question about "
                f"'{plan.original_query[:100]}' relates to Indian law. Please try again."
            )

    # ═══════════════════════════════════════════════════════════════════════
    #  STAGE 4: VERIFIER — self-critique / reflection
    # ═══════════════════════════════════════════════════════════════════════

    def _verify(self, original_query: str, answer: str,
                context: str, plan: AgentPlan) -> VerificationResult:
        """
        LLM-powered self-critique.
        Checks: completeness, accuracy, hallucination risk, relevance.
        """
        system_msg = (
            "You are a LEGAL ANSWER VERIFIER. You review AI-generated legal answers "
            "for quality. Output ONLY valid JSON:\n"
            "{\n"
            '  "confidence": <float 0.0-1.0>,\n'
            '  "is_acceptable": <true/false>,\n'
            '  "issues": ["<issue 1>", ...],\n'
            '  "suggestions": "<what to improve if not acceptable>",\n'
            '  "reasoning": "<brief explanation>"\n'
            "}\n\n"
            "Check:\n"
            "1. Does it answer the actual question asked?\n"
            "2. Are cited sections/cases plausible for Indian law?\n"
            "3. Is the answer substantive (not just filler)?\n"
            "4. Is the structure clear (Framework → Precedents → Reasoning)?\n"
            "5. Any obvious hallucinated case names or fabricated sections?\n\n"
            "Set confidence >= 0.75 if answer is good enough to serve.\n"
            "Set is_acceptable = true if confidence >= 0.75."
        )

        user_msg = (
            f"ORIGINAL QUESTION: {original_query}\n\n"
            f"GENERATED ANSWER (first 2000 chars):\n{answer[:2000]}\n\n"
            f"STRATEGY USED: {plan.strategy}\n"
            f"DOMAINS: {', '.join(plan.detected_domains)}"
        )

        try:
            resp = self._llm_call(system_msg, user_msg,
                                  temperature=0.1, max_tokens=400)
            data = self._parse_json(resp)
            confidence = float(data.get("confidence", 0.5))
            return VerificationResult(
                is_acceptable=data.get("is_acceptable", confidence >= CONFIDENCE_THRESHOLD),
                confidence=confidence,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", ""),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.warning(f"[VERIFIER] Verification failed: {e}. Defaulting to accept.")
            # If verifier itself fails, accept the answer (don't block user)
            return VerificationResult(
                is_acceptable=True, confidence=0.7,
                issues=["verifier_failed"], suggestions="",
                reasoning=f"Verifier error: {e}",
            )

    # ═══════════════════════════════════════════════════════════════════════
    #  PLAN REFINEMENT (between loops)
    # ═══════════════════════════════════════════════════════════════════════

    def _refine_plan(self, plan: AgentPlan,
                     verification: VerificationResult) -> AgentPlan:
        """Adapt the plan based on verification feedback."""
        logger.info(f"[AGENT] Refining plan: {verification.suggestions[:80]}")

        # Escalate strategy
        if plan.strategy == "simple":
            plan.strategy = "multi_hop"
        elif plan.strategy == "statute_lookup":
            plan.strategy = "multi_hop"
        elif plan.strategy == "multi_hop":
            plan.needs_web_search = True
            plan.strategy = "research"

        # Add sub-queries from verifier suggestions
        if verification.suggestions and not plan.sub_queries:
            plan.sub_queries = [verification.suggestions[:200]]

        # Rewrite query if issues found
        if "doesn't answer" in " ".join(verification.issues).lower():
            plan.rewritten_query = f"{plan.original_query} (elaborate with sections and cases)"

        return plan

    # ═══════════════════════════════════════════════════════════════════════
    #  LLM UTILITIES
    # ═══════════════════════════════════════════════════════════════════════

    def _llm_call(self, system_msg: str, user_msg: str, *,
                  temperature: float = 0.3, max_tokens: int = 1500) -> str:
        """Call LLM with retry + key rotation + fast model fallback."""
        # Model cascade: start with 70b, fall back to 8b on rate-limit
        _model_cascade = [
            (self.model,             max_tokens),          # primary: 70b
            ("llama-3.1-8b-instant", min(max_tokens, 1200)),  # fallback: 8b fast
        ]
        last_exc = None
        for model_name, m_tokens in _model_cascade:
            for attempt in range(2):  # 2 attempts per model
                try:
                    resp = self.llm.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                        temperature=temperature,
                        max_tokens=m_tokens,
                    )
                    if model_name != self.model:
                        logger.info(f"[LLM] Fallback model '{model_name}' succeeded")
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    last_exc = e
                    err_str = str(e)
                    logger.warning(f"[LLM] {model_name} attempt {attempt+1} failed: {err_str[:120]}")
                    if "429" in err_str or "rate_limit" in err_str.lower():
                        # Key rotation on rate-limit
                        if hasattr(self.llm, "force_rotation"):
                            self.llm.force_rotation(reason=err_str[:60])
                        sleep_t = 1.5 if attempt == 0 else 0  # short sleep only on first retry
                        if sleep_t:
                            time.sleep(sleep_t)
                    else:
                        time.sleep(1.0)
        raise RuntimeError(f"LLM call failed for all models. Last error: {last_exc}")

    @staticmethod
    def _parse_json(text: str) -> Dict:
        """Extract JSON from LLM output (handles markdown fences)."""
        # Strip markdown code fences
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try finding JSON object in text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"[JSON] Could not parse: {text[:200]}")
        return {}

    @staticmethod
    def _format_sources(documents: List[Dict]) -> List[Dict]:
        """Format source documents for API response."""
        sources = []
        for doc in documents[:8]:
            sources.append({
                "title": doc.get("title", doc.get("id", "Legal Document")),
                "content": str(doc.get("content", doc.get("text", "")))[:300],
                "source": doc.get("source", "Legal Database"),
            })
        return sources
