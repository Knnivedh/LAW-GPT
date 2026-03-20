"""
ULTIMATE Multi-API RAG System - NVIDIA ONLY with DeepSeek
Optimized with strategic prompting for 80%+ accuracy
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
import time
import logging
import hashlib
from dotenv import load_dotenv

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from config/.env
load_dotenv(project_root / "config" / ".env")

from rag_system.core.hybrid_chroma_store import HybridChromaStore
from rag_system.core.enhanced_retriever import EnhancedRetriever
from rag_system.core.answer_validator import AnswerValidator
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NVIDIA API Configuration - Load from .env
NVIDIA_KEY = Config.get_nvidia_api_key()
if not NVIDIA_KEY:
    raise ValueError("NVIDIA_API_KEY not found in config/.env. Please set nvidia_api or NVIDIA_API_KEY")

print("="*80)
print(">>> LAW-GPT RAG SYSTEM - NVIDIA LLAMA 3.1 70B ONLY <<<")
print("="*80)

# Initialize hybrid store
print("\n[Initialization] Loading database...")
db_path = project_root / "chroma_db_hybrid"
vector_store = HybridChromaStore(
    persist_directory=str(db_path),
    collection_name="legal_db_hybrid",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)
print(f"[OK] Loaded {vector_store.count():,} documents")

# Initialize enhanced retriever
print("\n[Initialization] Loading enhanced retriever...")
try:
    enhanced_retriever = EnhancedRetriever(vector_store)
    print("[OK] Enhanced retriever with cross-encoder re-ranking")
except Exception as e:
    logger.warning(f"Enhanced retriever failed: {e}")
    enhanced_retriever = None

# Initialize answer validator
print("\n[Initialization] Loading answer validator...")
answer_validator = AnswerValidator()
print("[OK] Answer validator ready")

print("="*80)

# Configure NVIDIA API client
nvidia_client = OpenAI(
    base_url=Config.NVIDIA_BASE_URL,
    api_key=NVIDIA_KEY
)
print("[OK] NVIDIA API Connected - Llama 3.1 70B Instruct (FREE)")
print("="*80)


def extract_legal_citations(text):
    """Extract all legal citations from source text"""
    import re
    citations = set()
    
    # Extract IPC sections
    ipc_patterns = [
        r'Section\s+\d+[A-Z]?\s*,?\s*IPC',
        r'IPC\s+Section\s+\d+[A-Z]?',
        r'S\.\s*\d+[A-Z]?\s+IPC',
        r'\d+[A-Z]?\s+IPC'
    ]
    for pattern in ipc_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        citations.update(matches)
    
    # Extract Constitutional Articles
    const_patterns = [
        r'Article\s+\d+[A-Z]?\s*(?:\([^)]+\))?\s*(?:of\s+)?(?:the\s+)?Constitution',
        r'Art\.\s*\d+[A-Z]?',
        r'Articles?\s+\d+[A-Z]?(?:\s*,\s*\d+[A-Z]?)*'
    ]
    for pattern in const_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        citations.update(matches)
    
    # Extract Act names
    act_patterns = [
        r'[A-Z][a-zA-Z\s]+Act,?\s+\d{4}',
        r'(?:CrPC|CPC|IPC)\s*,?\s*\d{4}',
        r'Code\s+of\s+(?:Criminal|Civil)\s+Procedure,?\s+\d{4}'
    ]
    for pattern in act_patterns:
        matches = re.findall(pattern, text)
        citations.update(matches)
    
    # Extract case citations
    case_patterns = [
        r'[A-Z][a-zA-Z\s&.]+v\.?\s+[A-Z][a-zA-Z\s&.]+\(?\d{4}\)?',
        r'\([^\)]*\d{4}[^\)]*\)\s+\d+\s+[A-Z]+\s+\d+'
    ]
    for pattern in case_patterns:
        matches = re.findall(pattern, text)
        citations.update(matches)
    
    return list(citations)


def build_strategic_prompt(query, retrieved_docs):
    """Build ULTRA-ENHANCED prompt with explicit citation extraction"""
    
    # Extract ALL legal citations from sources
    all_citations = set()
    sources = []
    
    for i, doc in enumerate(retrieved_docs[:12], 1):  # Use 12 docs for more citations
        score = doc.get('score', 0)
        text = doc.get('text', '')
        
        # Extract citations from this doc
        doc_citations = extract_legal_citations(text)
        all_citations.update(doc_citations)
        
        sources.append(f"SOURCE #{i} [Relevance: {score:.2f}]:\n{text}")
    
    context = "\n\n" + "="*80 + "\n\n".join(sources)
    
    # Build citation list
    citation_list = "\n".join([f"  • {cite}" for cite in sorted(all_citations)])
    
    prompt = f"""You are a Senior Advocate of the Supreme Court of India with 30+ years of experience in all branches of Indian law.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR TASK: Provide a COMPREHENSIVE legal opinion with SPECIFIC citations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 EXTRACTED LEGAL CITATIONS FROM SOURCES (YOU MUST USE THESE):
{citation_list if citation_list else "  [No specific citations found - provide general legal principles]"}

PROVIDED LEGAL SOURCES:
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❓ QUESTION REQUIRING EXPERT LEGAL OPINION:
{query}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚖️ MANDATORY ANSWER FORMAT (FOLLOW EXACTLY):

1️⃣ DIRECT ANSWER (In 2-3 clear sentences, answer the specific question asked)

2️⃣ LEGAL BASIS & STATUTORY PROVISIONS
   • Cite EXACT sections from IPC/CrPC/CPC (e.g., "Section 302, IPC")
   • Reference Constitutional articles (e.g., "Article 21 of the Constitution")
   • Mention applicable Acts with years (e.g., "Limitation Act, 1963")
   • Include ALL relevant citations from the list above

3️⃣ CASE LAW & PRECEDENTS
   • Cite landmark Supreme Court/High Court judgments
   • Include case names with years (e.g., "Kesavananda Bharati v. State of Kerala (1973)")
   • Explain how precedents apply to this situation

4️⃣ LIMITATION PERIODS & TIME BARS
   • State specific time limits under Limitation Act, 1963
   • Mention adverse possession periods (if property-related)
   • Note any appeal or revision deadlines

5️⃣ PROCEDURAL REQUIREMENTS
   • Detail step-by-step legal procedure (CPC/CrPC)
   • Mention court fees, documentation, jurisdiction
   • Explain filing requirements and formalities

6️⃣ PRACTICAL GUIDANCE & ACTION STEPS
   • Provide CLEAR, ACTIONABLE steps the person should take
   • Mention what documents to prepare
   • Suggest timeline for action

7️⃣ EXCEPTIONS, CONDITIONS & LIMITATIONS
   • Note any special circumstances or exceptions
   • Mention burden of proof requirements
   • Explain conditions that must be met

8️⃣ FINAL RECOMMENDATION & CONCLUSION
   • Give DECISIVE, CLEAR guidance
   • Summarize key points
   • Recommend immediate next steps

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL INSTRUCTIONS (NON-NEGOTIABLE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ DO:
  • Use ONLY information from the provided sources
  • Include EVERY relevant citation from the extracted list above
  • Be SPECIFIC with section numbers, article numbers, case names, and years
  • Structure answer EXACTLY as shown in 8-part format
  • Provide practical, actionable advice
  • Mention specific time periods, costs, and procedural steps

❌ DO NOT:
  • Make up laws, sections, or cases NOT in the sources
  • Give vague or general answers without citations
  • Skip any of the 8 mandatory sections
  • Provide advice without legal basis from sources

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 YOUR DETAILED LEGAL OPINION (FOLLOW THE 8-PART FORMAT):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return prompt


# RESPONSE CACHE
response_cache = {}

def get_cache_key(query: str) -> str:
    """Generate cache key for query"""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


def query_nvidia(prompt):
    """Query NVIDIA with free Llama model - ULTRA-OPTIMIZED for legal citations"""
    try:
        response = nvidia_client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",  # Free NVIDIA Llama 3.1 70B
            messages=[
                {"role": "system", "content": """You are a Senior Advocate of the Supreme Court of India with 30+ years of experience in ALL branches of Indian law.

EXPERTISE AREAS:
• Criminal Law (IPC, CrPC, Evidence Act)
• Civil Law (CPC, Contract Act, Property Law)
• Constitutional Law (Fundamental Rights, DPSP, Constitutional Remedies)
• Property Law (Transfer of Property Act, Easement Act, Registration Act)
• Family Law (Hindu Marriage Act, Muslim Personal Law, etc.)
• Commercial Law (Companies Act, Arbitration, Negotiable Instruments)

YOUR RESPONSE STYLE:
✅ ALWAYS include specific section numbers, article numbers, and case citations
✅ Use EXACT legal terminology from statutes
✅ Cite landmark Supreme Court and High Court judgments with years
✅ Mention limitation periods, time bars, and procedural deadlines
✅ Structure answers in clear, numbered sections
✅ Provide both legal theory AND practical guidance
✅ Include specific costs, fees, documentation requirements
✅ Address counterarguments and exceptions

❌ NEVER make up laws, sections, or cases not in provided sources
❌ NEVER give vague answers without specific citations
❌ NEVER skip citing relevant provisions from sources
❌ NEVER provide advice without legal foundation

Remember: Your client depends on ACCURATE, SPECIFIC, ACTIONABLE legal guidance grounded in the law."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,  # Increased for comprehensive answers
            temperature=0.15,  # Even lower for maximum precision
            timeout=300  # 5 minutes for complex questions
        )
        return {
            'source': 'NVIDIA Llama 3.1 70B',
            'answer': response.choices[0].message.content,
            'success': True,
            'api_name': 'NVIDIA Llama 3.1 70B Instruct'
        }
    except Exception as e:
        logger.error(f"NVIDIA API error: {e}")
        return {
            'source': 'NVIDIA',
            'answer': None,
            'success': False,
            'error': str(e),
            'api_name': 'NVIDIA'
        }


def multi_api_query_ultimate(query_text, use_cache=True):
    """
    Query function using NVIDIA only
    """
    
    # Check cache first
    cache_key = get_cache_key(query_text)
    if use_cache and cache_key in response_cache:
        cached = response_cache[cache_key]
        cached['from_cache'] = True
        print("\n[CACHE HIT] Returning cached response")
        return cached
    
    print("\n" + "="*80)
    print(f"[QUERY] {query_text[:80]}...")
    print("="*80)
    
    query_start = time.time()
    
    # Step 1: Retrieve documents
    print("\n[1/5] Retrieving documents...")
    search_start = time.time()
    
    if enhanced_retriever:
        results = enhanced_retriever.retrieve(
            query_text,
            use_reranking=True,
            use_query_expansion=True
        )
        print(f"  [OK] Retrieved {len(results)} documents with re-ranking ({time.time() - search_start:.2f}s)")
    else:
        results = vector_store.hybrid_search(query_text, n_results=20)  # Increased for better context
        print(f"  [OK] Retrieved {len(results)} documents ({time.time() - search_start:.2f}s)")
    
    # Step 2: Build prompt
    print("\n[2/5] Building strategic prompt...")
    prompt = build_strategic_prompt(query_text, results)
    
    # Step 3: Query NVIDIA API
    print("\n[3/5] Querying NVIDIA API...")
    api_start = time.time()
    
    result = query_nvidia(prompt)
    
    print(f"  [OK] API call completed ({time.time() - api_start:.2f}s)")
    
    # Step 4: Check result
    print("\n[4/5] Validating response...")
    
    if not result['success']:
        print(f"  [ERROR] API failed: {result.get('error', 'Unknown error')}")
        return {
            'query': query_text,
            'final_answer': f"ERROR: API failed - {result.get('error', 'Unknown error')}",
            'success': False,
            'error': result.get('error', 'API failed')
        }
    
    final_answer = result['answer']
    print(f"  [OK] Got response from {result['source']}")
    
    # Step 5: Validate answer
    print("\n[5/5] Quality validation...")
    validation_start = time.time()
    
    validation = answer_validator.validate_answer(
        answer=final_answer,
        retrieved_docs=results
    )
    
    print(f"  [OK] Validation: {validation['overall_score']*100:.1f}/100 ({time.time() - validation_start:.2f}s)")
    
    query_time = time.time() - query_start
    print(f"\n{'='*80}")
    print(f"[TIME] Total: {query_time:.2f}s")
    print(f"{'='*80}")
    
    # Create result
    response = {
        'query': query_text,
        'search_results': results,
        'final_answer': final_answer,
        'validation': validation,
        'success': True,
        'from_cache': False,
        'total_time': query_time,
        'query_log': {'api_used': result['api_name']}
    }
    
    # Cache result
    if use_cache:
        response_cache[cache_key] = response.copy()
        print(f"  [OK] Response cached")
    
    return response


if __name__ == "__main__":
    test_query = "What is IPC Section 302?"
    
    print(f"\n[TEST] Test Query: {test_query}")
    print("-"*80)
    
    result = multi_api_query_ultimate(test_query)
    
    if result['success']:
        print("\n" + "="*80)
        print("[ANSWER]")
        print("="*80)
        print(result['final_answer'][:500])
        print("="*80)
