import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
from dotenv import load_dotenv
import logging
from openai import OpenAI

# Load environment from config/.env
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / "config" / ".env")
load_dotenv(project_root / ".env")

# Fix Windows console encoding for Unicode (₹ symbol etc.)
def _safe_reconfigure_stream(stream) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding='utf-8', errors='replace')


if sys.platform == 'win32':
    try:
        _safe_reconfigure_stream(sys.stdout)
        _safe_reconfigure_stream(sys.stderr)
    except:
        pass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directories to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# from rag_system.core.hybrid_chroma_store import HybridChromaStore  <-- MOVED TO LAZY IMPORT
from rag_system.core.enhanced_retriever import EnhancedRetriever
import rag_config
from kaanoon_test.system_adapters.ontology_grounded_rag import OntologyGroundedRAG
from kaanoon_test.system_adapters.hierarchical_thought_rag import HierarchicalThoughtRAG
from kaanoon_test.system_adapters.instruction_tuning_rag import InstructionTuningRAG
from kaanoon_test.system_adapters.parametric_rag_system import ParametricRAGSystem
from kaanoon_test.system_adapters.owl_judicial_workforce import OwlJudicialWorkforce
from kaanoon_test.utils.client_manager import GroqClientManager
from kaanoon_test.system_adapters.persistent_memory import AgenticMemoryManager
from kaanoon_test.system_adapters.agentic_rag_engine import AgenticRAGEngine

class UnifiedAdvancedRAG:
    """
    Unified Advanced RAG System that orchestrates:
    1. Dual-Store Retrieval (Statutes + Judgments)
    2. Ontology-Grounded Reasoning
    3. Hierarchical COT (HiRAG)
    4. Feedback-Optimized Instruction Tuning
    """
    
    def __init__(self):
        logger.info("\n" + "="*80)
        logger.info("INITIALIZING UNIFIED ADVANCED RAG SYSTEM")
        logger.info("="*80)
        
        # SPEED FIX: Use GroqClientManager for Rate Limit Bypass (Rotation)
        logger.info("[0/6] Initializing Groq Client Manager (Key Rotation Active)...")
        self.client_manager = GroqClientManager(request_limit=29)
        self.client = self.client_manager # Proxy client
        
        self.model = "llama-3.3-70b-versatile"  # Fast Groq model
        logger.info(f"  [TURBO] Using Groq LLM: {self.model} with Multi-Key Rotation")
        
        # Initialize base RAG components (Main Judgments)
        logger.info("[1/6] Initializing base retrieval systems (Main Store)...")
        try:
            if rag_config.CLOUD_MODE_ENABLED:
                from rag_system.core.milvus_store import CloudMilvusStore
                self.store = CloudMilvusStore()
                logger.info(f"  [☁️ CLOUD] Main Store connected to Zilliz Cloud")
            else:
                from rag_system.core.hybrid_chroma_store import HybridChromaStore
                self.store = HybridChromaStore(
                    persist_directory=str(rag_config.MAIN_DB_PATH),
                    collection_name=rag_config.MAIN_COLLECTION
                )
                logger.info(f"  [OK] Main Store loaded (Permanent: {rag_config.MAIN_DB_PATH})")
        except Exception as e:
            logger.error(f"  [CRITICAL] Failed to load Main Store: {e}")
            self.store = None
        
        # Initialize specialized statutes store
        logger.info("  -> Loading specialized Statutes store (CLOUD MODE)...")
        try:
            # USER REQUEST: "Cloud RAG 2 Both" -> Use Zilliz for Statutes too
            from rag_system.core.milvus_store import CloudMilvusStore
            self.statute_store = CloudMilvusStore(
                collection_name=rag_config.ZILLIZ_COLLECTION_NAME # Shared Cloud Brain
            )
            logger.info(f"  [☁️ CLOUD] Statutes Store linked to Zilliz Cloud")
        except Exception as e:
            logger.warning(f"  [WARN] Could not load Cloud Statutes store: {e}")
            self.statute_store = None
            
        # Ensure we have at least one store (RELAXED FOR VOICE TESTING)
        if not self.store and not self.statute_store:
            logger.error("!!! FAILED TO INITIALIZE ANY DATABASE STORES !!!")
            logger.info("  -> Falling back to Direct LLM Reasoning (Zero-Shot Legal Mode)")
            # No raise here, let it run with just the LLM
            
        self.retriever = EnhancedRetriever(self.store, statute_store=self.statute_store)
        
        # Initialize advanced components
        try:
            logger.info("[2/6] Loading Ontology-Grounded RAG...")
            self.ontology_rag = OntologyGroundedRAG()
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load Ontology RAG: {e}")
            self.ontology_rag = None
        
        try:
            logger.info("[3/6] Loading Hierarchical-Thought RAG (HiRAG)...")
            self.hirag = HierarchicalThoughtRAG(self.client)
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load HiRAG: {e}")
            self.hirag = None
        
        try:
            logger.info("[4/6] Loading Instruction-Tuning RAG...")
            self.instruction_tuning = InstructionTuningRAG()
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load Instruction Tuning: {e}")
            self.instruction_tuning = None
        
        try:
            logger.info("[5/6] Loading Parametric RAG with Advanced Retrieval...")
            self.parametric_rag = ParametricRAGSystem(
                main_store=self.store, 
                statute_store=self.statute_store,
                llm_client=self.client  # Pass LLM for multi-query + HyDE
            )
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load Parametric RAG: {e}")
            self.parametric_rag = None
        
        try:
            logger.info("[6/7] Initializing OWL Judicial Workforce agent...")
            self.reviewer = OwlJudicialWorkforce(client_manager=self.client_manager)
        except Exception as e:
            logger.warning(f"  [WARN] Failed to load OWL Reviewer: {e}")
            self.reviewer = None
        
        logger.info("[7/9] Initializing Deep Research Agent (Lazy Import Ready)...")
        self.researcher = None # Will be initialized on demand to save RAM if camel-ai is missing

        # ── AGENTIC RAG LAYER (NEW) ─────────────────────────────────────
        logger.info("[8/9] Initializing Agentic Memory Manager (3-tier)...")
        try:
            self.memory_manager = AgenticMemoryManager()
            logger.info("  [OK] Memory Manager: ShortTerm + LongTerm + SemanticCache")
        except Exception as e:
            logger.warning(f"  [WARN] Memory Manager failed: {e}")
            self.memory_manager = None

        # ── PageIndex Retriever (Vectorless Tree-Based Statute RAG) ─────────────
        logger.info("[8.5/9] Initializing PageIndex Retriever (vectorless statute RAG)...")
        try:
            from kaanoon_test.system_adapters.pageindex_retriever import PageIndexRetriever
            self.pageindex_retriever = PageIndexRetriever(
                llm_client=self.client_manager,
                model=self.model,
            )
            if self.pageindex_retriever.is_available:
                n_docs = len(self.pageindex_retriever.get_indexed_docs())
                logger.info(f"  [OK] PageIndex Retriever ready — {n_docs} statutes indexed")
            else:
                logger.info("  [INFO] PageIndex Retriever: PAGEINDEX_API_KEY not set — "
                            "add to config/.env to enable statute tree-search")
        except Exception as e:
            logger.warning(f"  [WARN] PageIndex Retriever failed to load: {e}")
            self.pageindex_retriever = None

        logger.info("[9/9] Initializing Agentic RAG Engine (Planning + Reflection)...")
        try:
            self.agentic_engine = AgenticRAGEngine(
                client_manager=self.client_manager,
                parametric_rag=self.parametric_rag,
                retriever=self.retriever,
                memory_manager=self.memory_manager,
                hirag=self.hirag,
                researcher=self.researcher,
                pageindex_retriever=self.pageindex_retriever,
            )
            logger.info("  [OK] Agentic RAG Engine ready (Plan → Retrieve → Synthesise → Reflect)")
        except Exception as e:
            logger.warning(f"  [WARN] Agentic Engine failed: {e}")
            self.agentic_engine = None

        self._init_greeting_detection()
        
        # In-memory telemetry (no external DB required)
        self._start_time = time.time()
        self._query_times: List[float] = []
        self._feedback_log: List[Dict] = []
        
        logger.info("\n[OK] UNIFIED ADVANCED RAG SYSTEM READY (AGENTIC MODE)")
        logger.info("="*80 + "\n")
    
    def _init_greeting_detection(self):
        """Initialize robust greeting detection using regex"""
        import re
        self.greeting_patterns = [
            r"\bhi\b", r"\bhello\b", r"\bhey\b", 
            r"\bwho are you\b", r"\bwhat can you do\b"
        ]
        self.reg = re.compile("|".join(self.greeting_patterns), re.IGNORECASE)

    @staticmethod
    def _is_stub_answer(answer: str, confidence: float = 0.0) -> bool:
        text = (answer or "").strip().lower()
        if not text:
            return True

        stub_markers = (
            "unable to generate",
            "unable to synthesize",
            "service issue",
            "service limitations",
            "please try again",
            "technical difficulty",
            "error occurred",
            "failed to retrieve",
        )
        if any(marker in text for marker in stub_markers):
            return True

        return len(text.split()) < 40 and confidence < 0.75

    def query(self, user_query: str, category: str = "general",
              chat_history: Optional[List[Dict[str, str]]] = None, *,
              session_id: str = "", user_id: str = "",
              simple_mode: bool = False) -> Dict[str, Any]:
        """Process a user query through the Agentic RAG pipeline.

        Pipeline: Greeting check → Agentic Engine (Plan → Retrieve → Synthesise → Reflect)
        Falls back to legacy HiRAG pipeline if the agentic engine is unavailable.

        Args:
            simple_mode: When True, use lightweight single-pass (8b model) for
                         factual queries. Avoids rate limiting the 70b model.
        """
        _t0 = time.time()

        # 1. Check for greetings (fast path)
        if self.reg.search(user_query):
            self._query_times.append(time.time() - _t0)
            return {
                'answer': "Hello! I am your Advanced Legal AI Assistant. I can help with complex Indian legal queries using statutes and case law.",
                'source_documents': [],
                'reasoning_path': "Greeting detected"
            }

        logger.info(f"Processing query: {user_query} [Category: {category}]")

        # ── AGENTIC PATH (preferred) ─────────────────────────────────────
        if self.agentic_engine and self.memory_manager:
            try:
                result = self.agentic_engine.run(
                    user_query,
                    session_id=session_id,
                    user_id=user_id,
                    category=category,
                    chat_history=chat_history,
                    simple_mode=simple_mode,
                )
                if self._is_stub_answer(result.answer, result.confidence):
                    raise RuntimeError("agentic engine returned stub/empty answer")
                _elapsed = time.time() - _t0
                self._query_times.append(_elapsed)
                return {
                    'answer': result.answer,
                    'source_documents': result.sources,
                    'reasoning_path': (f"Agentic[{result.loops_taken}x]: "
                                       f"{' → '.join(result.reasoning_trace[:6])}"),
                    'metadata': {
                        'confidence': result.confidence,
                        'loops': result.loops_taken,
                        'from_cache': result.from_cache,
                        'memory_used': result.memory_context_used,
                        'retrieval_time': _elapsed,
                        'strategy': result.plan.strategy if result.plan else 'n/a',
                    },
                }
            except Exception as e:
                logger.error(f"[AGENTIC] Engine failed, falling back to legacy: {e}")

        # ── LEGACY FALLBACK (HiRAG → Judicial Audit) ─────────────────────
        rag_params = {
            'search_domain': category, 
            'complexity': 'complex',
            'keywords': user_query.split()[:5]
        }
        
        if self.parametric_rag is not None:
            retrieval_results = self.parametric_rag.retrieve_with_params(user_query, rag_params)
        else:
            retrieval_results = {'documents': [], 'context': '', 'metadata': {}}
        
        dynamic_context = ""
        if self.researcher is not None and (len(user_query.split()) > 10 or not retrieval_results.get('documents')):
            logger.info("  [GENERALIZATION] Complex/Novel query. Triggering Deep Research...")
            try:
                dynamic_context = self.researcher.conduct_research(user_query)
                logger.info(f"  [RESEARCH] Discovered context: {len(dynamic_context)} chars")
            except Exception as e:
                logger.warning(f"  [WARN] Research failed: {e}")
        
        combined_context = retrieval_results.get('context', '') + ("\n\n" + dynamic_context if dynamic_context else "")
        try:
            if self.hirag is not None:
                answer_data = self.hirag.answer_with_hierarchy(
                    user_query,
                    combined_context,
                    domain_context=str(retrieval_results.get('metadata', {})),
                    chat_history=chat_history or []
                )
            else:
                answer_data = {'answer': ''}
        except Exception as e:
            logger.error(f"  [ERROR] HiRAG failed: {e}")
            answer_data = {'answer': ''}

        logger.info("  -> Performing Judicial Audit (legacy path)...")
        time.sleep(1.5)
        try:
            full_context = retrieval_results.get('context', '') + ("\n\n" + dynamic_context if dynamic_context else "")
            if self.reviewer is not None:
                final_opinion = self.reviewer.review_and_correct(
                    user_query, full_context, answer_data.get('answer', '')
                )
            else:
                final_opinion = answer_data
        except Exception as e:
            logger.error(f"  [ERROR] Judicial review failed: {e}")
            final_opinion = answer_data

        _elapsed = time.time() - _t0
        self._query_times.append(_elapsed)
        return {
            'answer': final_opinion.get('answer', answer_data.get('answer', 'Unable to generate answer')),
            'source_documents': retrieval_results.get('documents', []),
            'reasoning_path': "Legacy: HiRAG -> Deep Research -> Judicial Audit",
            'metadata': {**retrieval_results.get('metadata', {}), 'retrieval_time': _elapsed}
        }

    # ── Telemetry & Lifecycle helpers ──────────────────────────────────────

    def collect_feedback(self, query: str, answer: str, rating: int,
                         session_id: str, feedback_text: Optional[str] = None) -> None:
        """Store user feedback in-memory for the session duration."""
        self._feedback_log.append({
            'query': query[:200],
            'answer': answer[:200],
            'rating': rating,
            'session_id': session_id,
            'feedback_text': feedback_text,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        })
        logger.info(f"[FEEDBACK] session={session_id} rating={rating}/5")

    def get_metrics(self) -> Dict[str, Any]:
        """Return in-memory performance metrics + agentic cache stats."""
        n = len(self._query_times)
        avg = round(sum(self._query_times) / n, 3) if n > 0 else 0.0
        uptime = round(time.time() - self._start_time, 1)
        cache_stats = {}
        if self.memory_manager:
            cache_stats = self.memory_manager.get_memory_stats()
        return {
            'total_queries': n,
            'average_latency': avg,
            'cache_hit_rate': cache_stats.get('cache_hit_rate', 0.0),
            'uptime_seconds': uptime,
            'feedback_count': len(self._feedback_log),
            'agentic_memory': cache_stats,
        }

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Return summary statistics on collected feedback."""
        log = self._feedback_log
        if not log:
            return {'total': 0, 'average_rating': 0.0, 'ratings': {}}
        avg = round(sum(f['rating'] for f in log) / len(log), 2)
        dist = {}
        for f in log:
            dist[f['rating']] = dist.get(f['rating'], 0) + 1
        return {'total': len(log), 'average_rating': avg, 'ratings': dist}

    def clear_conversation(self, session_id: str) -> None:
        """Clear session memory and cached state."""
        if self.memory_manager:
            self.memory_manager.clear_session(session_id)
        logger.info(f"[CLEAR] conversation cleared: {session_id}")
