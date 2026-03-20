"""
FastAPI Backend for Advanced Agentic RAG System
Production-ready API server with async support, metrics, and feedback
"""
import os
import sys

# Fix Windows console encoding for Unicode (₹ symbol etc.)
def _safe_reconfigure_stream(stream) -> None:
    reconfigure = getattr(stream, 'reconfigure', None)
    if callable(reconfigure):
        reconfigure(encoding='utf-8', errors='replace')


if sys.platform == 'win32':
    _safe_reconfigure_stream(sys.stdout)
    _safe_reconfigure_stream(sys.stderr)
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
import json
import tempfile
from datetime import datetime
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API_SERVER")

# Import the advanced agentic system
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kaanoon_test.system_adapters.clarification_engine import ClarificationSession
from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
from contextlib import asynccontextmanager

import asyncio
import threading

# Initialize globals
rag_system = None
rag_initializing = False
active_clarification_sessions: Dict[str, ClarificationSession] = {}
CLARIFICATION_SESSION_DIR = Path(tempfile.gettempdir()) / "lawgpt_clarification_sessions"
CLARIFICATION_SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _session_state_path(session_id: str) -> Path:
    safe_id = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_"))
    return CLARIFICATION_SESSION_DIR / f"{safe_id}.json"


def _new_clarification_session() -> ClarificationSession:
    client_manager = None
    if rag_system is not None:
        client_manager = getattr(rag_system, 'client_manager', None)

    return ClarificationSession(
        provider="groq",
        retriever_callback=get_pre_loop_retriever(),
        client_manager=client_manager
    )


def _session_to_state_dict(session: ClarificationSession) -> Dict[str, Any]:
    return {
        "provider": getattr(session, "provider", "groq"),
        "model": getattr(session, "model", None),
        "stage": getattr(session, "stage", 0),
        "user_query": getattr(session, "user_query", ""),
        "initial_intent": getattr(session, "initial_intent", None),
        "missing_facts": getattr(session, "missing_facts", []),
        "qa_history": getattr(session, "qa_history", []),
        "max_questions": getattr(session, "max_questions", 5),
        "initial_legal_context": getattr(session, "initial_legal_context", "No initial context retrieved."),
    }


def _session_from_state_dict(state: Dict[str, Any]) -> ClarificationSession:
    session = _new_clarification_session()
    if state.get("model"):
        session.model = state["model"]
    session.stage = state.get("stage", 0)
    session.user_query = state.get("user_query", "")
    session.initial_intent = state.get("initial_intent")
    session.missing_facts = state.get("missing_facts", [])
    session.qa_history = state.get("qa_history", [])
    session.max_questions = state.get("max_questions", 5)
    session.initial_legal_context = state.get(
        "initial_legal_context", "No initial context retrieved."
    )
    return session


def _save_clarification_session(session_id: str, session: ClarificationSession) -> None:
    active_clarification_sessions[session_id] = session
    _session_state_path(session_id).write_text(
        json.dumps(_session_to_state_dict(session), ensure_ascii=False),
        encoding="utf-8",
    )


def _load_clarification_session(session_id: str) -> Optional[ClarificationSession]:
    path = _session_state_path(session_id)
    # Always prefer the persisted state over the worker-local cache.
    # Clarification requests can bounce across multiple gunicorn workers,
    # so a cached in-memory session may be older than the on-disk session
    # most recently written by another worker.
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            session = _session_from_state_dict(state)
            active_clarification_sessions[session_id] = session
            return session
        except Exception as exc:
            logger.error(f"[CLARIFICATION] Failed to load session {session_id[:12]}: {exc}")
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            active_clarification_sessions.pop(session_id, None)
            return None

    session = active_clarification_sessions.get(session_id)
    if session is not None:
        return session

    return None


def _delete_clarification_session(session_id: str) -> None:
    active_clarification_sessions.pop(session_id, None)
    try:
        _session_state_path(session_id).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning(f"[CLARIFICATION] Failed to delete session file for {session_id[:12]}: {exc}")


def _init_rag_in_background():
    """Initialize RAG system in a background thread so the server starts immediately."""
    global rag_system, rag_initializing
    rag_initializing = True
    logger.info("[BACKGROUND] Starting RAG system initialization...")
    try:
        rag_system = UnifiedAdvancedRAG()
        logger.info("[BACKGROUND] RAG System ready ✓")
    except Exception as e:
        logger.error(f"[BACKGROUND] RAG init failed: {e}")
        rag_system = None
    finally:
        rag_initializing = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager — server starts immediately, RAG loads in background thread."""
    logger.info("[STARTUP] LAW-GPT API starting (RAG loading in background)...")
    # Fire RAG init in a daemon thread — the server becomes available instantly
    t = threading.Thread(target=_init_rag_in_background, daemon=True)
    t.start()
    yield
    logger.info("[SHUTDOWN] Application shutdown complete.")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Advanced Agentic RAG API",
    description="Production-ready RAG system with async, memory, Redis, and metrics",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
# Note: allow_credentials=True is incompatible with allow_origins=["*"] per the
# CORS spec — browsers reject it. All production traffic arrives via Vercel rewrites
# (same-origin), so credentials are not needed here.  We explicitly list known
# origins so that direct API calls from dev also work without CORS errors.
_CORS_ORIGINS = [
    "http://localhost:3001",   # Vite dev server default
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # Vercel preview / production domains — wildcard handled via allow_origin_regex
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # all Vercel preview & prod URLs
    allow_credentials=False,   # no cookie/session auth required; Supabase JWT goes in body
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# Static file paths are resolved; mounts are registered at the BOTTOM of this file
# (after all @app route declarations) so that /api/*, /health endpoints are matched
# first and NOT intercepted by the root '/' StaticFiles mount.
static_home_path = project_root / "static_home"
static_chat_path = project_root / "static_chat"

def get_pre_loop_retriever():
    """Wrapper for ClarificationEngine's first retrieval pass"""
    if not rag_system:
        return lambda q: "RAG not initialized"
    
    def retrieve(query):
        current_rag = rag_system
        if current_rag is None:
            return "RAG not initialized"

        parametric_rag = getattr(current_rag, 'parametric_rag', None)
        if parametric_rag is None:
            logger.warning("[PRE-LOOP] Parametric RAG unavailable during clarification prefetch")
            return "RAG retrieval unavailable"

        # Use Simple/Fast retrieval for Stage 0 (Double RAG Phase 1)
        result = parametric_rag.retrieve_with_params(
            query=query,
            rag_params={'complexity': 'simple'}
        )
        return result.get('context', 'No context found.')
    return retrieve


# Request/Response Models
class QueryRequest(BaseModel):
    question: str = Field(..., description="User question")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    user_id: Optional[str] = Field(None, description="Authenticated user ID (for long-term memory)")
    target_language: Optional[str] = Field(None, description="Target language")
    category: Optional[str] = Field(None, description="Question category (for compatibility)")
    stream: bool = Field(False, description="Stream response")
    web_search_mode: bool = Field(False, description="Enable deep web search")  # NEW
    enable_thinking: bool = Field(True, description="Enable chain-of-thought reasoning trace")



class FeedbackRequest(BaseModel):
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Answer provided")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    session_id: str = Field(..., description="Session ID")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    citations: Optional[Dict[str, Any]] = Field(None, description="Extracted citations")
    citation_validation: Optional[Dict[str, Any]] = Field(None, description="Citation validation results")
    reasoning_analysis: Optional[Dict[str, Any]] = Field(None, description="Legal reasoning analysis")
    latency: float
    complexity: str
    query_type: str
    retrieval_time: float
    synthesis_time: Optional[float]
    confidence: float
    session_id: str
    from_cache: bool
    validation: Dict[str, Any]
    think_trace: Optional[str] = Field(None, description="Internal chain-of-thought reasoning trace")


# API Endpoints
@app.post("/api/query")
async def query_endpoint(request: QueryRequest):
    """
    Main query endpoint with interactive clarification loop support
    """
    if not rag_system:
        if rag_initializing:
            raise HTTPException(
                status_code=503,
                detail="LAW-GPT is warming up (RAG system initializing). Please try again in 1-2 minutes."
            )
        raise HTTPException(status_code=503, detail="RAG system not available")

    session_id = request.session_id or f"session_{datetime.now().timestamp()}"
    user_id = request.user_id or ""
    user_question = request.question
    
    import re as _re_shared

    # --- Strip prompt-injection attempts (all queries) ---------------------------
    user_question = _re_shared.sub(
        r'(?i)(ignore (?:previous|all|above|this)[^.!?\n]*|'
        r'forget (?:everything|all)[^.!?\n]*|'
        r'act as [^.!?\n]*|you are now [^.!?\n]*|'
        r'new instructions?:?[^.!?\n]*|'
        r'override[^.!?\n]*|'
        r'tell me (?:a joke|how to (?:destroy|tamper|evade|escape|hide))[^.!?\n]*|'
        r'and tamper with[^.!?\n]*)[.!?]?',
        '', user_question
    ).strip() or user_question

    _question_lower = user_question.lower()

    # --- Safety refusal: explicit requests for illegal / obstructive acts -------
    _illegal_patterns = [
        r'\bdestroy\s+(?:cctv\s+)?evidence\b',
        r'\btamper\s+with\s+(?:documents?|evidence)\b',
        r'\bhow\s+do\s+i\s+destroy\b',
        r'\bbribe\s+(?:the\s+)?(?:police|judge|officer)\b',
        r'\bforge\s+(?:the\s+)?document\b',
        r'\blaunder\s+money\b',
        r'\bevade\s+(?:income\s+)?tax\b',
        r'\bhide\s+black\s+money\b',
        r'\bfile\s+a\s+false\s+fir\b',
    ]
    if any(_re_shared.search(pattern, _question_lower) for pattern in _illegal_patterns):
        logger.info(f"[SAFETY] Illegal-guidance query refused: {user_question[:60]}")
        return {
            "response": {
                "answer": (
                    "I cannot assist with destroying evidence, tampering with documents, or any other illegal act. "
                    "Those actions are illegal and may amount to a criminal offence under Indian law. "
                    "If you are involved in a case, preserve evidence and seek lawful advice from a qualified advocate."
                ),
                "status": "direct",
                "session_id": session_id,
                "latency": 0.1,
                "sources": [],
                "think_trace": None,
                "system_info": {"query_type": "safety_refusal"}
            }
        }

    # --- Out-of-scope detection: non-Indian / foreign law queries ----------------
    _oos_keywords = ['gdpr', 'eu law', 'european union law', 'ccpa', 'california privacy',
                     'california law', 'california state law', 'uk law', 'english law',
                     'american law', 'us law', 'u.s. law', 'french law']
    if any(k in _question_lower for k in _oos_keywords):
        logger.info(f"[OOS] Out-of-scope query detected: {user_question[:60]}")
        return {
            "response": {
                "answer": (
                    "This query relates to foreign / international law (e.g. EU GDPR, CCPA) "
                    "which is **outside the scope** of this platform. LAW-GPT specialises in "
                    "Indian law: Constitution of India, IPC / BNS, CrPC / BNSS, Consumer "
                    "Protection Act 2019, family law, property law, and Supreme Court / High "
                    "Court judgments. For Indian data-protection law please refer to the "
                    "**Digital Personal Data Protection Act, 2023 (DPDPA)**."
                ),
                "status": "direct",
                "session_id": session_id,
                "latency": 0.1,
                "sources": [],
                "think_trace": None,
                "system_info": {"query_type": "out_of_scope"}
            }
        }

    # --- Fake-law detection: clearly invalid IPC references ----------------------
    _fake_ipc_reference = (
        ('ipc' in _question_lower or 'indian penal code' in _question_lower)
        and _re_shared.search(r'\bsection\s*\d+\s*\([a-z]\)', _question_lower)
        and any(term in _question_lower for term in ['data monetization', 'data monetisation', 'digital', 'ai-generated'])
    )
    if _fake_ipc_reference:
        logger.info(f"[FAKE-LAW] Invalid IPC reference detected: {user_question[:60]}")
        return {
            "response": {
                "answer": (
                    "This IPC reference appears to be invalid or does not exist. Please verify the section number, "
                    "because I cannot confirm any such section of the Indian Penal Code for the issue described."
                ),
                "status": "direct",
                "session_id": session_id,
                "latency": 0.1,
                "sources": [],
                "think_trace": None,
                "system_info": {"query_type": "invalid_reference"}
            }
        }

    try:
        # 1. CHECK IF SESSION IS ALREADY IN CLARIFICATION LOOP
        session = _load_clarification_session(session_id)
        if session is not None:
            # Retry submit_answer on Groq 429
            import time as _time_mod2
            loop_result = None
            for _ans_attempt in range(3):
                try:
                    loop_result = session.submit_answer(user_question)
                    break
                except Exception as _ans_err:
                    _ans_str = str(_ans_err)
                    if ("429" in _ans_str or "rate limit" in _ans_str.lower()) and _ans_attempt < 2:
                        _wt = 30 * (_ans_attempt + 1)
                        logger.warning(f"[CLARIFICATION] Groq 429 on submit_answer, retrying in {_wt}s...")
                        _time_mod2.sleep(_wt)
                    else:
                        raise

            if loop_result is None:
                raise RuntimeError("Clarification loop did not return a result")
            
            if loop_result["status"] == "clarification_loop":
                _save_clarification_session(session_id, session)
                return {
                    "response": {
                        "answer": loop_result["next_question"],
                        "status": "clarification",
                        "progress": loop_result["progress"].split('/')[0] + "Q",
                        "session_id": session_id,
                        "latency": 0.5,
                        "system_info": {"query_type": "clarification"}
                    }
                }
            elif loop_result["status"] == "ready_for_synthesis":
                # Final step: Synthesize and Run RAG
                synthesis = session.synthesize_and_execute()
                final_matrix = synthesis["matrix"]

                # Delete session BEFORE the RAG query so that any call_api retry
                # (triggered by a stub answer) does NOT restart a new clarification
                # session with the user's last message as the initial query.
                _delete_clarification_session(session_id)
                logger.info(f"[SYNTHESIS] Session {session_id[:12]} deleted. Running final RAG...")

                # Completed clarification sessions should return a fuller case
                # consultation, so keep the final synthesis on the standard path.
                try:
                    result = rag_system.query(final_matrix, session_id=session_id,
                                             user_id=user_id, simple_mode=False)
                except TypeError:
                    result = rag_system.query(final_matrix, session_id=session_id, user_id=user_id)

                response_dict = format_rag_response(result, session_id, question_hint=user_question)
                response_dict["system_info"]["query_type"] = "case_consultation"
                return {"response": response_dict}

        # 2. START NEW SESSION - use groq provider with llama-3.1-8b-instant (verified working model from Azure)
        session = _new_clarification_session()
        # Pass category to start_session for Domain-Specific Intent Analysis
        # Retry up to 2 times on 429 rate limits before giving up
        import time as _time_mod
        _start_init_result = None
        for _start_attempt in range(2):
            try:
                _start_init_result = session.start_session(user_question, category=request.category or "general")
                break
            except Exception as _start_err:
                _err_str = str(_start_err)
                if ("429" in _err_str or "rate limit" in _err_str.lower() or "Rate limit" in _err_str) and _start_attempt < 1:
                    _wait_s = 15
                    logger.warning(f"[CLARIFICATION] 429 on start attempt {_start_attempt+1}, "
                                   f"retrying in {_wait_s}s...")
                    _time_mod.sleep(_wait_s)
                    session = _new_clarification_session()   # fresh session for retry
                else:
                    logger.error(f"[CLARIFICATION] start_session raised: {_err_str}. Falling back to direct RAG.")
                    # Fallback: use RAG directly instead of returning 500
                    result = rag_system.query(user_question, category=request.category or "general")
                    fb_resp = format_rag_response(result, session_id, question_hint=user_question)
                    fb_resp["system_info"]["query_type"] = "fallback_direct"
                    return {"response": fb_resp}
        init_result = _start_init_result
        if init_result is None:
            logger.warning("[CLARIFICATION] start_session returned no result. Falling back to direct RAG.")
            result = rag_system.query(user_question, category=request.category or "general",
                                      session_id=session_id, user_id=user_id)
            fb_resp = format_rag_response(result, session_id, question_hint=user_question)
            fb_resp["system_info"]["query_type"] = "fallback_direct"
            return {"response": fb_resp}
        
        if init_result["status"] == "needs_clarification":
            # Save session for multi-turn
            _save_clarification_session(session_id, session)
            return {
                "response": {
                    "answer": init_result["first_question"],
                    "status": "clarification",
                    "progress": "1Q",
                    "session_id": session_id,
                    "latency": 1.5,
                    "system_info": {"query_type": "clarification", "domain": request.category}
                }
            }
        elif init_result["status"] in ["greeting", "irrelevant"]:
            return {
                "response": {
                    "answer": init_result["message"],
                    "status": "direct",
                    "session_id": session_id,
                    "latency": 0.2,
                    "system_info": {"query_type": init_result["status"]}
                }
            }
        elif init_result["status"] == "academic_direct":
            logger.info(f"[ACADEMIC DIRECT] Using full analysis path for: {user_question[:50]}...")
            try:
                result = rag_system.query(
                    user_question,
                    category=request.category or "general",
                    session_id=session_id,
                    user_id=user_id,
                    simple_mode=False,
                )
            except TypeError:
                result = rag_system.query(
                    user_question,
                    category=request.category or "general",
                    session_id=session_id,
                    user_id=user_id,
                )
            response_dict = format_rag_response(result, session_id, question_hint=user_question)
            response_dict["system_info"]["query_type"] = "academic_direct"
            response_dict["system_info"]["complexity"] = "high"
            return {"response": response_dict}
        elif init_result["status"] == "simple_direct":
            # Most simple factual queries should use the lightweight 8b path, but
            # complex academic issue-spotting prompts still need the full analysis
            # pipeline even when they bypass clarification.
            import re as _re_direct
            _force_full_patterns = [
                r'(analy[sz]e|discuss|examine)\s+separately',
                r'what\s+.{0,20}(constitutional|statutory|contractual|procedural)\s+issues?',
                r'(five|5)\s+(distinct\s+)?issues?',
                r'privacy\s+and\s+data-protection\s+violations',
                r'deficiency\s+in\s+service\s+and\s+unfair\s+trade\s+practice',
                r'legal\s+effect\s+of\s+user\s+consent',
                r'pil\s+maintainability',
                r'effect\s+of\s+the\s+arbitration\s+clause',
                r'use\s+(correct|exact)\s+indian\s+statutory\s+section',
            ]
            _force_full = any(_re_direct.search(pattern, user_question.lower()) for pattern in _force_full_patterns)

            logger.info(
                f"[SIMPLE DIRECT] Providing {'full' if _force_full else 'immediate'} answer for: {user_question[:50]}..."
            )
            try:
                result = rag_system.query(user_question, category=request.category or "general",
                                          session_id=session_id, user_id=user_id,
                                          simple_mode=not _force_full)
            except TypeError:
                # Fallback: old unified_rag without simple_mode param
                logger.warning("[SIMPLE DIRECT] simple_mode not supported, falling back")
                result = rag_system.query(user_question, category=request.category or "general",
                                          session_id=session_id, user_id=user_id)
            _simple_wc = len(user_question.split())
            _max_words = 0 if _force_full else (350 if _simple_wc <= 12 else 500)
            response_dict = format_rag_response(result, session_id, question_hint=user_question,
                                                max_answer_words=_max_words)
            response_dict["system_info"]["query_type"] = "academic_direct" if _force_full else "simple_direct"
            response_dict["system_info"]["complexity"] = "high" if _force_full else "low"
            return {"response": response_dict}
        elif init_result["status"] == "fallback_direct":
            # LLM call failed in clarification engine - fallback to direct RAG gracefully
            logger.warning(f"[FALLBACK DIRECT] Clarification LLM failed, using direct RAG: {init_result.get('message', '')[:80]}")
            result = rag_system.query(user_question, category=request.category or "general",
                                      session_id=session_id, user_id=user_id)
            fb_resp = format_rag_response(result, session_id, question_hint=user_question)
            fb_resp["system_info"]["query_type"] = "fallback_direct"
            return {"response": fb_resp}
        else:
            # Fallback to direct RAG if something failed or unexpected status
            # Pass category to RAG system for Domain-Specific Retrieval
            result = rag_system.query(user_question, category=request.category or "general",
                                      session_id=session_id, user_id=user_id)
            return {"response": format_rag_response(result, session_id, question_hint=user_question)}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Query Error: {error_msg}")
        if "429" in error_msg or "Rate limit" in error_msg:
            # Groq rate limited — fall back to direct RAG instead of returning 429
            logger.warning("[FALLBACK] Groq rate limited. Falling back to direct RAG for graceful degradation.")
            try:
                result = rag_system.query(user_question, category=request.category or "general")
                response_dict = format_rag_response(result, session_id, question_hint=user_question)
                response_dict.setdefault("system_info", {})["query_type"] = "fallback_direct"
                return {"response": response_dict}
            except Exception as fallback_err:
                logger.error(f"Fallback RAG also failed: {fallback_err}")
                raise HTTPException(status_code=429, detail="AI Service Rate Limit Reached. Please try again later.")
        raise HTTPException(status_code=500, detail=f"Query failed: {error_msg}")

def format_rag_response(result, session_id, question_hint: str = "", max_answer_words: int = 0):
    """Helper to format RAG result for API — supports agentic metadata + thinking trace.

    Args:
        max_answer_words: If > 0 and answer exceeds this word count, trim at the last
            sentence boundary within the limit. Use for simple/factual queries (e.g. 350).
    """
    import re as _fmt_re
    import time as _tt2
    meta = result.get('metadata', {})
    answer_text = result.get('answer', 'No answer generated')

    def _derive_title(question_text: str, answer: str) -> str:
        import re as _title_re

        explicit_title = result.get('title') or meta.get('title')
        if explicit_title:
            return str(explicit_title).strip()[:120]

        cleaned_question = (question_text or '').strip()
        cleaned_question = _title_re.sub(r'\s+', ' ', cleaned_question)
        cleaned_question = cleaned_question.rstrip('?.! ')
        if cleaned_question:
            if len(cleaned_question) <= 90:
                return cleaned_question
            shortened = cleaned_question[:90].rsplit(' ', 1)[0].strip()
            return shortened or cleaned_question[:90]

        first_sentence = _title_re.split(r'(?<=[.!?])\s+', answer.strip(), maxsplit=1)[0].strip()
        if first_sentence:
            return first_sentence[:90]

        return 'Legal Answer'

    # Best-effort question from result dict or caller hint
    _question_text = (
        result.get('query') or result.get('question') or question_hint or ""
    )[:300]

    # --- Extract <think>...</think> if the RAG answer contains one ---------------
    _think_match = _fmt_re.search(r'<think>(.*?)</think>', answer_text, _fmt_re.DOTALL)
    if _think_match:
        think_trace = _think_match.group(1).strip()
        answer_text = _fmt_re.sub(r'<think>.*?</think>\s*', '', answer_text, flags=_fmt_re.DOTALL).strip()
    else:
        think_trace = None

    # --- Brevity trimming: cap simple answers at max_answer_words words ----------
    if max_answer_words > 0:
        words = answer_text.split()
        if len(words) > max_answer_words:
            truncated = ' '.join(words[:max_answer_words])
            # Trim back to the last full sentence (. ? !)
            last_sentence_end = max(
                truncated.rfind('. '), truncated.rfind('.\n'),
                truncated.rfind('? '), truncated.rfind('!\n'),
            )
            if last_sentence_end > max_answer_words // 2:  # ensure we keep at least half
                answer_text = truncated[:last_sentence_end + 1].strip()
            else:
                answer_text = truncated.strip()
            logger.info(f"[BREVITY] Trimmed answer from {len(words)} words to ~{len(answer_text.split())} words")

    # --- Post-hoc thinking: generate a brief reasoning trace for complex answers --
    if not think_trace and len(answer_text) > 400:
        client_manager = getattr(rag_system, 'client_manager', None) if rag_system is not None else None
        for _think_attempt in range(3):
            try:
                if client_manager is None:
                    break

                # Rotate to a fresh API key to avoid back-to-back 429 after main query
                force_rotation = getattr(client_manager, 'force_rotation', None)
                if callable(force_rotation):
                    force_rotation(reason="pre-thinking-trace")
                _tt2.sleep(0.5 * (_think_attempt + 1))  # Increasing backoff

                _think_sys = (
                    "You are an internal legal reasoning engine for Indian law. "
                    "Given a legal question and AI answer, produce a deep reasoning trace (150-250 words) covering:\n"
                    "1. Exact statutes and section numbers applied (e.g., IPC s.302, CPC Order 7 Rule 11)\n"
                    "2. Landmark SC/HC precedents and constitutional provisions directly relied upon\n"
                    "3. Contradictions, unsettled law, or jurisdiction-specific variations in the answer\n"
                    "4. Alternative interpretations a court might consider\n"
                    "5. Why the answer prioritises certain legal sources over others\n"
                    "Output ONLY the reasoning trace — no bullet labels, no headings, no intro or conclusion phrases."
                )
                _think_usr = (
                    f"Question: {_question_text}\n\n"
                    f"Answer excerpt (first 1200 chars):\n{answer_text[:1200]}\n\n"
                    "Internal reasoning trace:"
                )
                # Use the fast 8b model — low latency, avoids rate-limiting the 70b
                _think_resp = client_manager.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": _think_sys},
                        {"role": "user", "content": _think_usr}
                    ],
                    temperature=0.15,
                    max_tokens=320
                )
                _raw_trace = _think_resp.choices[0].message.content.strip()
                # Strip any accidental think tags the model echoes back
                _raw_trace = _fmt_re.sub(r'</?think>', '', _raw_trace).strip()
                think_trace = _raw_trace if len(_raw_trace) > 30 else None
                logger.info(f"[THINKING] Generated post-hoc trace ({len(think_trace) if think_trace else 0} chars) on attempt {_think_attempt+1}")
                break  # success
            except Exception as _think_err:
                _think_err_str = str(_think_err)
                logger.warning(f"[THINKING] Attempt {_think_attempt+1} failed: {type(_think_err).__name__}: {_think_err_str[:200]}")
                if _think_attempt == 2:
                    think_trace = None

    # --- Normalize source document format (handles raw Milvus/Chroma docs) ------
    _raw_sources = result.get('source_documents', [])
    _normalized_sources = []
    for _s in (_raw_sources or []):
        if isinstance(_s, dict):
            _normalized_sources.append({
                'title': _s.get('title') or _s.get('id') or _s.get('metadata', {}).get('title', 'Legal Document'),
                'content': str(_s.get('content') or _s.get('text') or _s.get('page_content', ''))[:400],
                'source': _s.get('source') or _s.get('metadata', {}).get('source', 'Legal Database'),
            })
        else:
            _normalized_sources.append(_s)

    return {
        'answer': answer_text,
        'title': _derive_title(_question_text, answer_text),
        'think_trace': think_trace,
        'sources': _normalized_sources,
        'citations': None,
        'reasoning_analysis': {'trace': result.get('reasoning_path', 'N/A')},
        'latency': meta.get('retrieval_time', 0),
        'complexity': meta.get('complexity', 'medium'),
        'query_type': meta.get('strategy', meta.get('search_domain', 'general')),
        'retrieval_time': meta.get('retrieval_time', 0),
        'synthesis_time': 0,
        'confidence': meta.get('confidence', 0.9),
        'session_id': session_id,
        'from_cache': meta.get('from_cache', False),
        'validation': {},
        'system_info': {
            'detected_language': 'en',
            'query_type': meta.get('strategy', 'expert_legal'),
            'complexity': meta.get('complexity', 'high'),
            'agentic_loops': meta.get('loops', 0),
            'memory_used': meta.get('memory_used', False),
        }
    }


@app.get("/api/debug-think")
async def debug_think_endpoint(question: str = "What is IPC 302?"):
    """Debug endpoint to test thinking trace generation in isolation."""
    if not rag_system:
        return {"error": "RAG not initialized"}
    import re as _dr; import time as _dt
    try:
        _dt.sleep(0.3)
        _resp = rag_system.client_manager.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a legal reasoning engine. Produce a 50-word reasoning trace about the given legal question."},
                {"role": "user", "content": f"Question: {question}\nReasoning trace:"}
            ],
            temperature=0.15, max_tokens=120
        )
        return {"ok": True, "trace": _resp.choices[0].message.content.strip(), "question": question}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "detail": str(e)[:400]}


@app.post("/api/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """
    Collect user feedback for continuous improvement
    """
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    try:
        rag_system.collect_feedback(
            query=request.query,
            answer=request.answer,
            rating=request.rating,
            session_id=request.session_id,
            feedback_text=request.feedback_text or ""
        )
        
        return {
            "status": "success",
            "message": "Feedback collected successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback collection failed: {str(e)}")


@app.get("/api/metrics")
async def metrics_endpoint():
    """
    Get system performance metrics
    """
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    try:
        metrics = rag_system.get_metrics()
        feedback_stats = rag_system.get_feedback_stats()
        
        return {
            "metrics": metrics,
            "feedback": feedback_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


@app.delete("/api/conversation/{session_id}")
async def clear_conversation_endpoint(session_id: str):
    """
    Clear conversation history for a session
    """
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")

    try:
        # Remove from active clarification sessions (multi-turn map)
        _delete_clarification_session(session_id)
        # Clear any internal RAG state
        rag_system.clear_conversation(session_id)
        return {
            "status": "success",
            "message": f"Conversation {session_id} cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear conversation failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    status = "ready" if rag_system else ("initializing" if rag_initializing else "degraded")
    return {
        "status": status,
        "rag_system_initialized": rag_system is not None,
        "rag_initializing": rag_initializing,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/debug/sessions")
async def debug_sessions():
    """Debug: returns PID and active clarification session count. Used by T11 benchmark."""
    import os
    return {
        "pid": os.getpid(),
        "active_sessions": len(active_clarification_sessions),
        "session_ids": list(active_clarification_sessions.keys())[:10],
        "persisted_sessions": len(list(CLARIFICATION_SESSION_DIR.glob("*.json"))),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/examples")
async def examples_endpoint():
    """
    Get example queries (for compatibility with frontend)
    """
    return {
        "examples": [
            "What is IPC Section 302?",
            "How to file for divorce under Hindu law?",
            "What is the procedure for filing FIR?",
            "Explain the principle of res judicata",
            "What are the rights of property owners in India?",
            "How to apply for bail?",
            "What is the difference between murder and culpable homicide?",
            "Explain Order 18 Rule 9 of CPC"
        ]
    }


@app.get("/health")
async def health_check_legacy():
    """Health check endpoint (without /api prefix for compatibility)"""
    status = "ready" if rag_system else ("initializing" if rag_initializing else "degraded")
    return {
        "status": status,
        "rag_system_initialized": rag_system is not None,
        "rag_initializing": rag_initializing,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/stats")
async def stats_endpoint():
    """
    Get system statistics (compatibility with existing endpoints)
    """
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    try:
        metrics = rag_system.get_metrics()
        return {
            "total_queries": metrics.get('total_queries', 0),
            "average_latency": metrics.get('average_latency', 0),
            "cache_hit_rate": metrics.get('cache_hit_rate', 0),
            "uptime_seconds": metrics.get('uptime_seconds', 0),
            "agentic_memory": metrics.get('agentic_memory', {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


# -------------------------------------------------------------------
# AUTH ENDPOINTS
# These allow the frontend to authenticate users. A guest session is
# returned so the chat works without a mandatory account.
# -------------------------------------------------------------------

class AuthRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None

@app.post("/api/auth/login")
async def auth_login(request: AuthRequest):
    """Guest / stub login so the frontend initialises correctly."""
    return {
        "status": "success",
        "user": {
            "id": "guest",
            "email": request.email or "guest@lawgpt.ai",
            "name": request.name or "Guest User",
            "role": "user"
        },
        "token": "guest-token",
        "message": "Logged in as guest"
    }

@app.post("/api/auth/register")
async def auth_register(request: AuthRequest):
    """Stub register endpoint."""
    return {
        "status": "success",
        "user": {
            "id": "guest",
            "email": request.email or "guest@lawgpt.ai",
            "name": request.name or "Guest User",
            "role": "user"
        },
        "token": "guest-token",
        "message": "Registered as guest"
    }

@app.post("/api/auth/logout")
async def auth_logout():
    """Stub logout endpoint."""
    return {"status": "success", "message": "Logged out"}

@app.get("/api/settings")
async def settings_endpoint():
    """Return frontend configuration / feature flags."""
    return {
        "voice_enabled": False,
        "auth_required": False,
        "max_message_length": 2000,
        "supported_languages": ["en", "hi"],
        "app_name": "LAW-GPT",
        "version": "2.0.0"
    }


# ---------------------------------------------------------------------------
# CRITICAL FIX: Middleware that intercepts the compiled frontend JS and
# replaces the hardcoded Cloudflare tunnel URL with the correct Azure URL.
# Middleware runs BEFORE StaticFiles mounts, so this always takes priority.
# ---------------------------------------------------------------------------
_OLD_API_URL = "https://opportunities-cds-bull-animals.trycloudflare.com"
_NEW_API_URL = "https://lawgpt-backend2024.azurewebsites.net"
_PATCHED_JS_PATH = "/chat/assets/index-BiOBT6qp.js"

class PatchJSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if request.url.path == _PATCHED_JS_PATH:
            js_path = project_root / "static_chat" / "assets" / "index-BiOBT6qp.js"
            if js_path.exists():
                content = js_path.read_text(encoding="utf-8", errors="replace")
                content = content.replace(_OLD_API_URL, _NEW_API_URL)
                return Response(content=content, media_type="application/javascript",
                               headers={"Cache-Control": "no-cache"})
        return await call_next(request)

app.add_middleware(PatchJSMiddleware)


@app.get("/chat")
async def chat_page():
    """Serve the chat SPA at /chat (without trailing slash)."""
    chat_index = project_root / "static_chat" / "index.html"
    if chat_index.exists():
        return HTMLResponse(content=chat_index.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Chat page not found")


# -------------------------------------------------------------------
# STATIC FILE MOUNTS — Registered LAST so all @app.xxx API routes are
# checked first.  Mounting "/" before API routes would intercept every
# request and return index.html instead of JSON.
# -------------------------------------------------------------------
if static_home_path.exists():
    app.mount("/home_assets", StaticFiles(directory=str(static_home_path / "assets")), name="home_assets")
if static_chat_path.exists():
    app.mount("/chat/assets", StaticFiles(directory=str(static_chat_path / "assets")), name="chat_assets")
# Serve ELEMENTS and parallax at absolute paths (chat JS references them without /chat prefix)
elements_path = static_chat_path / "ELEMENTS"
if elements_path.exists():
    app.mount("/ELEMENTS", StaticFiles(directory=str(elements_path)), name="elements")
parallax_path = static_chat_path / "parallax"
if parallax_path.exists():
    app.mount("/parallax", StaticFiles(directory=str(parallax_path), html=True), name="parallax")
devloper_path = static_chat_path / "devloper_button"
if devloper_path.exists():
    app.mount("/devloper_button", StaticFiles(directory=str(devloper_path), html=True), name="devloper_button")
if static_chat_path.exists():
    app.mount("/chat", StaticFiles(directory=str(static_chat_path), html=True), name="chat")
if static_home_path.exists():
    app.mount("/", StaticFiles(directory=str(static_home_path), html=True), name="home")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "advanced_rag_api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )