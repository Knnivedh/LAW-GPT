import sys
import os
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kaanoon_test.system_adapters.clarification_prompts import (
    INTENT_ANALYSIS_PROMPT,
    QUESTION_GENERATION_PROMPT,
    CONTEXT_SYNTHESIS_PROMPT,
    LEGAL_SCOPE_CHECK_PROMPT
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClarificationEngine")

class ClarificationSession:
    """
    Manages the 6-Stage Clarification Loop State Machine.
    Supports GroqClientManager for automatic multi-key rotation.
    """
    def __init__(self, client: OpenAI = None, provider: str = "groq", retriever_callback=None,
                 client_manager=None):
        """
        Initialize with multi-provider support.
        Providers: 'groq', 'cerebras', 'nvidia'
        retriever_callback: Optional function(query) -> str (Context)
        """
        self.provider = provider.lower()
        self.retriever_callback = retriever_callback
        self._client_manager = client_manager  # GroqClientManager for multi-key rotation
        
        # Load keys from .env if not loaded
        from dotenv import load_dotenv
        load_dotenv()
        
        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
            # Use env override or prefer llama-3.3-70b-versatile; fallback to llama-3.1-8b-instant
            self.model = os.getenv("GROQ_CLARIFICATION_MODEL", "llama-3.3-70b-versatile")
            # Models to try in order if primary returns 404
            self._fallback_models = ["llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct"]
        elif self.provider == "cerebras":
            api_key = os.getenv("CEREBRAS_API_KEY")
            base_url = "https://api.cerebras.ai/v1"
            self.model = "llama3.1-70b"  # Cerebras uses llama3.1-70b (no hyphen before version)
        else: # Default to NVIDIA
            api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("nvidia_api")
            base_url = "https://integrate.api.nvidia.com/v1"
            self.model = os.getenv("NVIDIA_MODEL_NAME", "nvidia/llama-3.1-nemotron-70b-instruct")

        if not api_key and not client_manager:
            logger.warning(f"API Key for {self.provider} not found. Using dummy key.")
        
        self.client = client or OpenAI(
            api_key=api_key or "dummy_key",
            base_url=base_url
        )
        n_keys = client_manager.key_count() if client_manager else 1
        logger.info(f"Initialized ClarificationEngine with Provider: {self.provider.upper()}, Model: {self.model}, Keys: {n_keys}")
        
        # State Variables (Temporary Memory)
        self.stage = 0  # 0: Idle, 1: Intake, 2: Q1.. 6: Final
        self.user_query = ""
        self.initial_intent = None
        self.missing_facts = []
        self.qa_history = []  # List of {q: "...", a: "..."}
        self.max_questions = 5
        self.initial_legal_context = "No initial context retrieved." # PHASE 1 Context

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialize only the session state that must survive across workers."""
        return {
            "provider": self.provider,
            "model": getattr(self, "model", None),
            "stage": self.stage,
            "user_query": self.user_query,
            "initial_intent": self.initial_intent,
            "missing_facts": self.missing_facts,
            "qa_history": self.qa_history,
            "max_questions": self.max_questions,
            "initial_legal_context": self.initial_legal_context,
        }

    @classmethod
    def from_state_dict(
        cls,
        state: Dict[str, Any],
        *,
        retriever_callback=None,
        client_manager=None,
    ) -> "ClarificationSession":
        """Rebuild a session from persisted state."""
        session = cls(
            provider=state.get("provider", "groq"),
            retriever_callback=retriever_callback,
            client_manager=client_manager,
        )
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

    def _get_client(self):
        """Returns the active OpenAI-compatible client (uses GroqClientManager if available)"""
        if self._client_manager:
            return self._client_manager.get_client()
        return self.client

    def _call_llm(self, messages, max_tokens=800, temperature=0.3):
        """LLM call with automatic 429 retry via key rotation and 404 model fallback."""
        # Build model candidate list: primary + fallbacks for Groq provider
        _model_candidates = [self.model]
        if self.provider == "groq" and hasattr(self, "_fallback_models"):
            _model_candidates += self._fallback_models
        
        for model_candidate in _model_candidates:
            for attempt in range(3):
                try:
                    c = self._get_client()
                    resp = c.chat.completions.create(
                        model=model_candidate,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    # If primary model failed but fallback worked, remember the working model
                    if model_candidate != self.model:
                        logger.warning(f"[ClarificationEngine] Primary model {self.model} failed, "
                                       f"switched to fallback: {model_candidate}")
                        self.model = model_candidate  # use this model for rest of session
                    return resp
                except Exception as e:
                    err = str(e)
                    # 404 = model not found / no access → try next model candidate
                    if ("404" in err or "model_not_found" in err or "does not exist" in err):
                        logger.warning(f"[ClarificationEngine] Model {model_candidate} not available "
                                       f"(404), trying next fallback...")
                        break  # break inner loop, try next model_candidate
                    # 429 = rate limit → rotate key and retry same model
                    elif ("429" in err or "rate limit" in err.lower()) and self._client_manager and attempt < 2:
                        logger.warning(f"[ClarificationEngine] 429 on attempt {attempt+1}, rotating key...")
                        self._client_manager.force_rotation("429 in ClarificationEngine")
                    else:
                        raise
        # If all models exhausted, raise final error
        raise RuntimeError(f"[ClarificationEngine] All model candidates exhausted: {_model_candidates}")

    def _is_greeting(self, query: str) -> bool:
        """Zero-Token Check: Is this just a greeting?"""
        import re
        # Relaxed regex to catch "hi there", "hello bot", etc.
        # Matches if the start of the string is a greeting word
        pattern = r"^\s*(hi|hello|hey|good\s*morning|good\s*afternoon|good\s*evening|greetings|who\s*are\s*you|what\s*can\s*you\s*do).{0,20}$"
        return bool(re.match(pattern, query, re.IGNORECASE))

    def _has_personal_case_indicators(self, query: str) -> bool:
        """Detect whether a query is actually about the user's own dispute or incident."""
        import re

        query_lower = query.lower().strip()
        personal_patterns = [
            r'\bi\s+(am|was|have|had|bought|paid|filed|got|received|signed|suffered|faced|lost|need)\b',
            r'\bmy\s+(wife|husband|father|mother|brother|sister|boss|employer|landlord|tenant|neighbour|neighbor|daughter|son|family|property|salary|land|house|flat|car|money|account|loan|complaint|case|fir|job|employer)\b',
            r'\bwe\s+(are|were|have|had|bought|paid|filed|signed|received)\b',
            r'\b(help me|please help|guide me|advise me|what should i|what can i|how (can|do|should) i|can i file|should i file)\b',
            r'\b(was (arrested|terminated|cheated|harassed|threatened|assaulted|dismissed))\b',
            r'\b(got\s+(a\s+|an\s+)?(arrested|fired|terminated|cheated|notice|letter|summons|fir|bail))\b',
            r'\b(received\s+(a |an )?(notice|letter|summon|order|fir))\b',
            r'\b(filed\s+(a |an )?(fir|complaint|case|petition|suit))\b',
        ]
        return any(re.search(pattern, query_lower) for pattern in personal_patterns)

    def _has_explicit_direct_instruction(self, query: str) -> bool:
        """Detect prompts that explicitly ask for a single direct answer without follow-up."""
        query_lower = query.lower().strip()
        direct_markers = [
            'one-shot', 'single answer', 'without asking', 'without follow-up',
            'do not ask', 'dont ask', 'no follow-up', 'no follow up',
            'proper title', 'with heading', 'with headings', 'with bullet', 'with bullets',
            'structured answer', 'comprehensive answer', 'detailed answer', 'in points',
        ]
        return any(marker in query_lower for marker in direct_markers)

    def _is_academic_legal_analysis(self, query: str) -> bool:
        """Detect academic / moot-court multi-sub-question legal analysis queries.

        These look like rich law-school problems: a fact scenario followed by several
        numbered issues asking what a court/commission 'must consider'.  They are
        impersonal (no 'I'/'my'/'we') and should NOT enter the personal-case 5Q loop.
        Route directly to RAG with the comprehensive structured-response format.
        """
        import re

        query_lower = query.lower().strip()
        explicit_direct = self._has_explicit_direct_instruction(query)

        # Dense case matrices often still need the 5-question interview unless the
        # user explicitly asks for a one-shot answer.
        if self._looks_like_complex_case_matrix(query) and not explicit_direct:
            return False

        # Must have NO personal case pronouns
        if re.search(r'\b(i am|i was|i have|i had|my |mine |we are|we were|we have|our )\b', query_lower):
            return False

        # Academic framing patterns
        _academic_patterns = [
            r'issues?\s+must\s+.{0,40}consider',
            r'questions?\s+must\s+.{0,40}address',
            r'(court|commission|tribunal)\s+.{0,30}(decide|consider|address|adjudicate)',
            r'what\s+.{0,20}(constitutional|statutory|contractual|procedural)\s+issues?',
            r'legal\s+issues?\s+.{0,20}(deciding|adjudicating|determining)',
            r'(high\s+court|supreme\s+court|consumer\s+commission)\s+.{0,30}(consider|decide|hold)',
            r'rights?\s+and\s+.{0,20}(obligations?|liabilities?|duties?)',
            r'(analy[sz]e|discuss|examine)\s+separately',
            r'(five|5)\s+(distinct\s+)?issues?',
            r'use\s+(correct|exact)\s+indian\s+statutory\s+section',
            r'(constitutional|statutory|contractual|procedural)\s+(issues?|questions?)',
            r'effect\s+of\s+the\s+arbitration\s+clause',
            r'legal\s+effect\s+of\s+user\s+consent',
            r'deficiency\s+in\s+service\s+and\s+unfair\s+trade\s+practice',
        ]
        has_academic_framing = any(re.search(p, query_lower) for p in _academic_patterns)

        # Count numbered sub-questions: lines starting with a digit or "(1)"
        _numbered_count = len(re.findall(r'(?:^|\n)\s*\d+[\.\)]\s+\w', query))
        _inline_count = len(re.findall(r'\(\d+\)\s+\w', query))
        has_many_subquestions = (_numbered_count + _inline_count) >= 3

        colon_sections = query.count(':')
        semicolon_sections = query.count(';')
        issue_list_density = colon_sections >= 2 or semicolon_sections >= 4

        issue_keywords = [
            'privacy', 'data-protection', 'deficiency in service', 'unfair trade practice',
            'user consent', 'privacy clauses', 'pil maintainability', 'consumer jurisdiction',
            'arbitration clause', 'algorithmic credit scoring', 'high court', 'consumer commission',
        ]
        issue_keyword_hits = sum(1 for keyword in issue_keywords if keyword in query_lower)

        # Combined: academic framing OR many numbered sub-questions (and still no personal pronouns)
        return (
            has_academic_framing
            or has_many_subquestions
            or (issue_keyword_hits >= 4 and issue_list_density)
        )

    def _looks_like_complex_case_matrix(self, query: str) -> bool:
        """Detect long, fact-dense legal problem statements that should enter clarification."""
        query_lower = query.lower().strip()
        word_count = len(query_lower.split())
        if word_count < 80:
            return False

        scenario_markers = [
            'during registration', 'terms of service include', 'terms of service contain',
            'two years later', 'subsequently', 'meanwhile', 'the company argues',
            'file complaints', 'consumer commission', 'public interest litigation',
            'public interest group', 'high court', 'pil', 'alleging',
            'mandatory arbitration clause', 'arbitration clause', 'article 21',
            'cybersecurity safeguards', 'third-party marketing firms',
            'algorithmic credit scoring', 'auto-rejects', 'data breach',
            'database leak', 'privacy policy', 'digital payments company',
            'consumer credit', 'transaction metadata', 'location patterns',
            'device identifiers', 'aadhaar-linked', 'kyc details',
            'transaction histories', 'scoring logic',
        ]
        marker_hits = sum(1 for marker in scenario_markers if marker in query_lower)

        issue_markers = [
            'privacy', 'data protection', 'consumer protection', 'platform liability',
            'arbitration', 'maintainability of a pil', 'disclosure of the scoring logic',
            'injunctive relief', 'compensation', 'defenses under indian law',
        ]
        issue_hits = sum(1 for marker in issue_markers if marker in query_lower)

        # Also treat heavily structured chronology / issue-matrix prompts as complex.
        colon_count = query.count(':')
        newline_count = query.count('\n')
        has_timeline_shape = colon_count >= 3 or newline_count >= 6
        has_multi_party_proceedings = (
            ('consumer commission' in query_lower or 'commission' in query_lower)
            and ('high court' in query_lower or 'pil' in query_lower or 'arbitration' in query_lower)
        )
        has_dense_cross_domain_matrix = marker_hits >= 2 and issue_hits >= 4
        return (
            marker_hits >= 3
            or (marker_hits >= 2 and has_timeline_shape)
            or has_multi_party_proceedings
            or has_dense_cross_domain_matrix
        )

    def _is_simple_query(self, query: str) -> bool:
        """
        Detect queries that should be answered DIRECTLY without follow-up questions.
        This includes:
        - Simple definitional questions ("What is Section 302?")
        - General legal knowledge / academic queries
        - Statutory provision questions
        - Landmark case questions  
        - Legal concept / procedural questions
        - Legal reform / transition questions
        - Hypothetical scenario questions ("If a person commits murder...")

        Returns True → bypass clarification, go straight to RAG.
        Returns False → enter clarification loop (only for personal case consultations).
        """
        import re
        query_lower = query.lower().strip()
        explicit_direct = self._has_explicit_direct_instruction(query)
        complex_case_matrix = self._looks_like_complex_case_matrix(query)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP -1: ACADEMIC MULTI-QUESTION LEGAL ANALYSIS → DIRECT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Moot-court / law-school problems with several numbered sub-questions
        # (e.g. "What constitutional, statutory, contractual...issues must the
        # High Court consider?") are impersonal academic analyses. The personal-
        # case 5Q clarification loop is WRONG for these — it would ask irrelevant
        # questions like "What was the purchase date?" etc.
        # Route directly to RAG + comprehensive structured-response format.
        if self._is_academic_legal_analysis(query) and not self._has_personal_case_indicators(query):
            logger.info(f"Detected ACADEMIC LEGAL ANALYSIS → routing direct to RAG: {query[:70]}...")
            return True

        if complex_case_matrix and not explicit_direct:
            logger.info(f"Detected COMPLEX CASE MATRIX (needs clarification): {query[:60]}...")
            return False

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 0: KNOWLEDGE-SEEKING PHRASES → direct (informational intent)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Personal pronouns + knowledge-seeking verb = general knowledge request.
        # e.g. "I want to understand bail", "I need to know about FIR",
        # "I was wondering what section 302 means".
        # These must bypass the personal-case check below (which would wrongly
        # classify any sentence starting with "I" as a personal case consultation).
        _knowledge_seeking = (
            r'\b(want to (know|understand|learn|find out)|'
            r'need to know|'
            r'have a question (about|on|regarding)|'
            r'wondering (what|how|why|when|whether|if)|'
            r'trying to understand|'
            r'curious about)\b'
        )
        if re.search(_knowledge_seeking, query_lower):
            logger.info(f"Detected KNOWLEDGE-SEEKING phrase \u2192 routing direct: {query[:60]}...")
            return True

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 1: PERSONAL CASE INDICATORS → needs clarification
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # If the query describes a PERSONAL situation, it needs the
        # clarification loop to gather case details.
        if self._has_personal_case_indicators(query):
            logger.info(f"Detected PERSONAL CASE (needs clarification): {query[:60]}...")
            return False

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 1b: HINDI / ROMANIZED QUERIES → direct answer
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Romanized Hindi queries like "rti kya hota hai", "498a case kya hota hai bro",
        # "cheque bounce ho gaya 138 ka case kaise karo" — these are general knowledge or
        # procedural questions expressed in Hinglish.  The clarification LLM handles them
        # poorly and often returns needs_clarification even for factual intent.
        # Since STEP 1 (personal indicators) already caught personal Hindi cases, any
        # Hindi-marker query that reaches this point is safe to route directly to RAG.
        _hindi_markers = (
            r'\b(kya|hai|hota|hote|hoti|kaise|karo|kaisa|batao|bhai|yaar|mein|'
            r'ka\s+case|ke\s+case|ki\s+case|ka\s+matlab|dwara|patni|pati|zulm|'
            r'gaya|chalao|karein|bataiye|karte|karta|jaldi|bolo|samjhao)\b'
        )
        if re.search(_hindi_markers, query_lower):
            logger.info(f"Detected HINDI/ROMANIZED QUERY → routing direct to RAG: {query[:60]}...")
            return True

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 2: GENERAL KNOWLEDGE PATTERNS → direct answer
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Pattern A: "What is/are [legal concept]?"
        if re.match(r'^what\s+(is|are)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (what is/are): {query[:60]}...")
            return True

        # Pattern B: "What did [court/body] hold/decide/rule in [case]?"
        if re.match(r'^what\s+(did|does|do|has|have|was|were)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (what did): {query[:60]}...")
            return True

        # Pattern C: "How many/much/does/is [legal entity]?"
        if re.match(r'^how\s+(many|much|does|do|is|are|can)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (how): {query[:60]}...")
            return True

        # Pattern D: "When did [law/act] come into effect?"
        if re.match(r'^when\s+(did|does|was|were|is|will)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (when): {query[:60]}...")
            return True

        # Pattern E: "Who can/is/has [legal entity]?"
        if re.match(r'^who\s+(can|is|are|has|have|was|were|should)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (who): {query[:60]}...")
            return True

        # Pattern F: "Which [legal entity] [verb]?"
        if re.match(r'^which\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (which): {query[:60]}...")
            return True

        # Pattern G: Define/Explain/Describe/List
        if re.match(r'^(define|explain|describe|list|enumerate|outline|summarize|summarise|discuss|compare|differentiate|distinguish|clarify|tell\s+me\s+about)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (imperative): {query[:60]}...")
            return True

        # Pattern G2: Long-form informational instructions should still get a one-shot answer.
        if re.match(r'^(analyze|analyse|provide|prepare|draft|write|give)\s+', query_lower) and not complex_case_matrix:
            logger.info(f"Detected GENERAL KNOWLEDGE (long-form instructional query): {query[:60]}...")
            return True

        # Pattern H: Has/Is/Does/Can/Are [legal concept]?
        if re.match(r'^(has|is|does|do|can|are|was|were|will|shall|should|may)\s+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (yes/no question): {query[:60]}...")
            return True

        # Pattern I: Hypothetical scenarios ("If a person...", "A consumer bought...")
        if re.match(r'^(if\s+a\s+|suppose\s+|assuming\s+|a\s+(person|consumer|woman|man|buyer|seller|employee|employer|tenant|landlord|citizen|victim|accused|complainant)\s+)', query_lower) and not complex_case_matrix:
            logger.info(f"Detected GENERAL KNOWLEDGE (hypothetical): {query[:60]}...")
            return True

        # Pattern J: Section/Article references without personal context
        if re.match(r'^(section|article|rule|order|clause|schedule)\s+\d+', query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (section reference): {query[:60]}...")
            return True

        # Pattern K: Legal topic keywords without personal pronouns
        legal_knowledge_keywords = [
            'fundamental rights', 'right to privacy', 'basic structure', 'judicial review',
            'anticipatory bail', 'regular bail', 'consumer rights', 'consumer protection',
            'domestic violence', 'dowry', 'divorce', 'maintenance', 'alimony',
            'landmark case', 'landmark judgment', 'supreme court', 'high court',
            'vishaka', 'kesavananda', 'puttaswamy', 'navtej', 'maneka gandhi',
            'bharatiya nyaya sanhita', 'bns', 'bnss', 'bharatiya sakshya',
            'rera', 'consumer protection act', 'legal aid', 'legal services',
            'pwdva', 'protection of women', 'domestic violence act',
            'jurisdiction', 'pecuniary jurisdiction', 'territorial jurisdiction',
            'punishment for', 'penalty for', 'offence of', 'crime of',
            'reliefs', 'remedies', 'provisions', 'features', 'types of',
            'significance of', 'importance of', 'key features', 'main features',
            'difference between', 'comparison between', 'distinction between',
            'replaced', 'come into effect', 'enacted', 'implemented',
            'colonial', 'new criminal law', 'law reform', 'legal reform',
        ]
        for kw in legal_knowledge_keywords:
            if kw in query_lower:
                logger.info(f"Detected GENERAL KNOWLEDGE (keyword '{kw}'): {query[:60]}...")
                return True

        # Pattern L: Multi-part academic/legal analysis queries should not enter the
        # clarification loop just because they are long or detailed.
        informational_markers = [
            'with heading', 'with headings', 'with bullet', 'with bullets',
            'in points', 'one-shot', 'single answer', 'do not ask', 'without asking',
            'proper title', 'detailed answer', 'comprehensive answer', 'structured answer',
            'legal position', 'case law', 'statutory basis', 'constitutional basis',
            'remedies available', 'procedure to', 'difference between', 'compare',
        ]
        if any(marker in query_lower for marker in informational_markers) and not self._has_personal_case_indicators(query) and not complex_case_matrix:
            logger.info(f"Detected GENERAL KNOWLEDGE (structured informational query): {query[:60]}...")
            return True

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 3: FALLBACK — short questions → direct; long without personal → direct
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        word_count = len(query.split())

        # Short questions (≤15 words) ending with ? → likely informational
        if word_count <= 15 and query.strip().endswith('?'):
            logger.info(f"Detected GENERAL KNOWLEDGE (short question): {query[:60]}...")
            return True

        # Medium questions (≤30 words) without ANY personal pronouns → likely general knowledge
        personal_pronouns = r'\b(i|my|me|mine|we|our|us|ours)\b'
        if word_count <= 30 and not re.search(personal_pronouns, query_lower):
            logger.info(f"Detected GENERAL KNOWLEDGE (no personal pronouns): {query[:60]}...")
            return True

        # Longer legal-analysis questions without concrete personal-case indicators
        # should still be answered directly.
        if word_count > 30 and not self._has_personal_case_indicators(query) and not complex_case_matrix:
            logger.info(f"Detected GENERAL KNOWLEDGE (long non-personal legal query): {query[:60]}...")
            return True

        # Default: longer queries with some ambiguity → let LLM decide
        logger.info(f"Query not classified as simple: {query[:60]}...")
        return False

    def _check_legal_relevance(self, query: str) -> tuple[bool, str]:
        """Low-Token Check: Is this legally relevant? If not, get a brief answer."""
        try:
            response = self._call_llm(
                messages=[{"role": "user", "content": LEGAL_SCOPE_CHECK_PROMPT.format(query=query)}],
                max_tokens=60,
                temperature=0.0
            )
            content = response.choices[0].message.content.strip()
            
            # Robust JSON extraction
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                # Fallback if LLM failed JSON format
                return True, ""
                
            is_legal = data.get("is_legal", True)
            answer = data.get("answer", "I only handle Indian Legal matters.")
            logger.info(f"Legal Scope Check: is_legal={is_legal}")
            return is_legal, answer
        except Exception as e:
            logger.warning(f"Scope Check Failed ({e}). Defaulting to True.")
            return True, ""

    def start_session(self, query: str, category: str = "general") -> Dict[str, Any]:
        """Stage 1: Intake & Understanding (With Double RAG & Smart Gating)"""
        self.user_query = query
        self.stage = 1
        
        # --- 1. GREETING CHECK (Zero Cost) ---
        if self._is_greeting(query):
            logger.info("Detected Greeting. Asking RAG 1 to SKIP.")
            return {
                "status": "greeting",
                "message": "Namaste! 🙏 I am your AI Legal Assistant. Please describe your legal issue (e.g., 'I want a divorce' or 'Property dispute')."
            }

        # --- 1B. ACADEMIC / MOOT-STYLE COMPLEX ANALYSIS (Direct full RAG) ---
        # These should bypass the 5Q client-interview loop, but they still need the
        # full-depth analysis path rather than the lightweight simple-mode answerer.
        if (
            self._is_academic_legal_analysis(query)
            and not self._has_personal_case_indicators(query)
            and (
                self._has_explicit_direct_instruction(query)
                or not self._looks_like_complex_case_matrix(query)
            )
        ):
            logger.info("Detected ACADEMIC ANALYSIS QUERY. Bypassing clarification loop and using full RAG analysis.")
            return {
                "status": "academic_direct",
                "message": "Academic multi-issue legal analysis detected. Proceeding to full direct analysis.",
                "query": query,
                "skip_clarification": True,
            }

        # --- 2. SIMPLE QUERY CHECK (Zero LLM Cost — runs BEFORE scope check) ---
        # IMPORTANT: This must run before _check_legal_relevance() because the scope-check
        # LLM may incorrectly classify legal knowledge queries as "not legal" when they
        # mention recent events (e.g., 2024 criminal law reforms) that fall after the LLM's
        # training cutoff.  General knowledge / academic legal queries should ALWAYS bypass
        # scope check and go directly to RAG.
        if self._is_simple_query(query):
            logger.info("Detected SIMPLE QUERY. Bypassing scope check & clarification loop for direct RAG answer.")
            return {
                "status": "simple_direct",
                "message": "Simple factual query detected. Proceeding to direct answer.",
                "query": query,
                "skip_clarification": True
            }

        # --- 3. LEGAL RELEVANCE CHECK (Low Cost — only for non-simple queries) ---
        # At this point the query did NOT match simple-query patterns, so it may be a
        # personal case consultation or something genuinely off-topic.
        is_legal, helpful_answer = self._check_legal_relevance(query)
        if not is_legal:
            logger.info("Detected Non-Legal Query. Asking RAG 1 to SKIP.")
            # Add disclaimer to helpful answer
            final_msg = f"{helpful_answer}\n\n(Note: I am a specialized Legal AI for India. For other topics, my knowledge may be limited.)"
            return {
                "status": "irrelevant",
                "message": final_msg
            }
        
        # --- 4. DOUBLE RAG PHASE 1: PRE-LOOP RETRIEVAL (Full Cost) ---
        if self.retriever_callback:
            logger.info("Stage 0: Executing Pre-Loop RAG Search...")
            try:
                # OPTIONAL: Pass category to retrieval callback if supported
                self.initial_legal_context = self.retriever_callback(query) 
                logger.info(f"  [RAG 1] Retrieved {len(self.initial_legal_context)} chars of context")
            except Exception as e:
                logger.error(f"  [RAG 1] FAST RETRIEVAL FAILED: {e}")
                self.initial_legal_context = "Error retrieving initial context."
        else:
             logger.warning("  [RAG 1] Skipped (No callback provided)")
        # -----------------------------------------------
        
        logger.info(f"Stage 1: Analyzing Intent for: {query[:50]}... [Category: {category}]")
        
        try:
            response = self._call_llm(
                messages=[{
                    "role": "user", 
                    "content": INTENT_ANALYSIS_PROMPT.format(
                        query=query,
                        category=category,
                        initial_legal_context=self.initial_legal_context[:2000]
                    )
                }],
                temperature=0.2,
                max_tokens=512
            )
        except Exception as llm_exc:
            logger.error(f"Stage 1 LLM call failed: {llm_exc}. Returning fallback_direct.")
            return {"status": "fallback_direct", "message": str(llm_exc)}
        
        try:
            content = response.choices[0].message.content
            logger.info(f"  Raw LLM Response: {content}")
            
            # Robust JSON extraction
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                content_to_parse = json_match.group(0)
            else:
                 # Fallback: Try to clean markdown code blocks
                content_to_parse = content.replace("```json", "").replace("```", "").strip()
                # If it doesn't look like JSON, this will fail
            
            try:
                data = json.loads(content_to_parse)
            except json.JSONDecodeError:
                # Last ditch effort: Try to use a "json repair" heuristic or just fail gracefully
                logger.error("JSON Decode Error. Attempting naive repair...")
                # Sometimes models use single quotes
                content_to_parse = content_to_parse.replace("'", '"')
                data = json.loads(content_to_parse)

            self.initial_intent = data
            self.missing_facts = data.get("missing_facts", [])
            query_type = data.get("query_type", "case_consultation")
            ambiguity = data.get("ambiguity_score", 5)
            logger.info(f"  Intent: {data.get('intent')}")
            logger.info(f"  Query Type: {query_type}")
            logger.info(f"  Ambiguity: {ambiguity}")
            logger.info(f"  Missing: {len(self.missing_facts)} items")

            # SAFETY NET: If LLM classifies as general_knowledge or
            # hypothetical, bypass clarification even if _is_simple_query missed it
            if query_type in ("general_knowledge", "hypothetical_scenario") and not self._looks_like_complex_case_matrix(self.user_query):
                logger.info(f"  [BYPASS] LLM classified as '{query_type}' → direct RAG answer")
                return {
                    "status": "simple_direct",
                    "message": f"LLM classified query as {query_type}. Proceeding to direct answer.",
                    "query": self.user_query,
                    "skip_clarification": True
                }

            # Also bypass if ambiguity is very low (1-2) and no missing facts
            if ambiguity <= 2 and len(self.missing_facts) == 0:
                logger.info(f"  [BYPASS] Low ambiguity ({ambiguity}) + no missing facts → direct RAG")
                return {
                    "status": "simple_direct",
                    "message": "Low ambiguity query with no missing facts. Direct answer.",
                    "query": self.user_query,
                    "skip_clarification": True
                }

            # Final guardrail: the clarification loop should only start for real
            # personal-case consultations. If there are no concrete personal-case
            # indicators, answer directly even when the LLM over-predicts ambiguity.
            if not self._has_personal_case_indicators(self.user_query) and not self._looks_like_complex_case_matrix(self.user_query):
                logger.info("  [BYPASS] No concrete personal-case indicators → direct RAG answer")
                return {
                    "status": "simple_direct",
                    "message": "Informational legal query detected. Direct answer.",
                    "query": self.user_query,
                    "skip_clarification": True
                }

            return {
                "status": "needs_clarification",
                "intent": data,
                "first_question": self._generate_next_question()
            }
            
        except Exception as e:
            logger.error(f"Failed to parse intent: {e}")
            logger.error(f"Content was: {content}")
            return {"status": "error", "message": str(e)}

    def submit_answer(self, answer: str) -> Dict[str, Any]:
        """Stage 3: Response Collection & Stage 2: Next Gen"""
        # Store answer
        if self.qa_history:
            self.qa_history[-1]['a'] = answer
        
        logger.info(f"Received Answer: {answer[:30]}...")
        
        # Check loop condition
        if len(self.qa_history) < self.max_questions:
            next_q = self._generate_next_question()
            return {
                "status": "clarification_loop",
                "progress": f"{len(self.qa_history)}/{self.max_questions}",
                "next_question": next_q
            }
        else:
            # Stage 4: Consolidation
            return {
                "status": "ready_for_synthesis",
                "message": "Information collection complete. Synthesizing..."
            }

    def _generate_next_question(self) -> str:
        """Stage 2: Generate ONE targeted question"""
        step = len(self.qa_history) + 1
        remaining = self.max_questions - step + 1
        
        # Build context string
        context_str = f"INTENT: {self.initial_intent}\n\n"
        for i, item in enumerate(self.qa_history):
            context_str += f"Q{i+1}: {item['q']}\nA{i+1}: {item['a']}\n"
            
        last_ans = self.qa_history[-1]['a'] if self.qa_history else "N/A (First Question)"
        
        response = self._call_llm(
            messages=[{
                "role": "user",
                "content": QUESTION_GENERATION_PROMPT.format(
                    current_step=step,
                    remaining_steps=remaining,
                    context_matrix=context_str,
                    last_answer=last_ans
                )
            }],
            temperature=0.4
        )
        
        question = response.choices[0].message.content.strip()
        self.qa_history.append({"q": question, "a": None})
        return question

    def synthesize_and_execute(self) -> Dict[str, Any]:
        """Stage 4, 5, 6: Consolidate & RAG"""
        logger.info("Stage 4: Synthesizing Context...")
        
        transcript = "\n".join([f"Q: {x['q']}\nA: {x['a']}" for x in self.qa_history])
        
        # Pass Initial Context too so final matrix is complete
        response = self._call_llm(
            messages=[{
                "role": "user", 
                "content": CONTEXT_SYNTHESIS_PROMPT.format(
                    initial_intent=self.initial_intent,
                    transcript=transcript
                ) + f"\n\nINITIAL LEGAL CONTEXT FOUND:\n{self.initial_legal_context[:1000]}"
            }],
            temperature=0.2
        )
        
        consolidated_matrix = response.choices[0].message.content
        
        logger.info("Stage 5: RAG Activation with Matrix...")
        
        return {
            "status": "complete",
            "matrix": consolidated_matrix,
            "transcript": transcript
        }
