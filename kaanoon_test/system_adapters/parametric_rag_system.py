"""
PARAMETRIC ADVANCED RAG SYSTEM
Accepts parameters from LLM router and optimizes retrieval accordingly

ADVANCED FEATURES:
- Multi-Query Retrieval (query variations)
- HyDE (Hypothetical Document Embeddings)
- Cloud Re-ranking with Cross-Encoder
- Metadata Filtering
- RRF Fusion
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Add parent directories to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# chromadb is disabled on cloud — guard it
try:
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    _CHROMADB_AVAILABLE = True
except ImportError:
    HybridChromaStore = None
    _CHROMADB_AVAILABLE = False

from rag_system.core.enhanced_retriever import EnhancedRetriever
try:
    from rag_system.core.advanced_retrieval import AdvancedRetrieval, get_advanced_retrieval
except ImportError:
    AdvancedRetrieval = None
    get_advanced_retrieval = None


class ParametricRAGSystem:
    """Advanced RAG with parameter-based optimization and state-of-the-art retrieval"""
    
    def __init__(self, main_store=None, statute_store=None, llm_client=None):
        """Initialize parametric RAG system with advanced retrieval"""
        print("[PARAMETRIC RAG] Initializing advanced retrieval system...")
        self.store = main_store
        self.statute_store = statute_store
        self.retriever = EnhancedRetriever(self.store, statute_store=self.statute_store)
        
        # Initialize advanced retrieval module
        self.advanced = AdvancedRetrieval(llm_client)
        self.llm_client = llm_client
        
        # Store reference to cross-encoder from enhanced retriever
        self.reranker = self.retriever.reranker if self.retriever.has_reranker else None
        
        print("[PARAMETRIC RAG] [OK] System ready with advanced retrieval")

    
    def retrieve_with_params(
        self,
        query: str,
        rag_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve documents using parameters from LLM router
        
        Args:
            query: User query
            rag_params: Parameters from router including:
                - search_domain: str (IPC, GST, DPDP, etc.)
                - specific_sections: List[str]
                - case_names: List[str]
                - keywords: List[str]
                - complexity: str (simple|medium|complex)
        
        Returns:
            {
                'documents': List[Dict],
                'context': str,
                'metadata': Dict
            }
        """
        start_time = time.time()
        
        # Extract parameters
        search_domain = rag_params.get('search_domain', 'general')
        specific_sections = rag_params.get('specific_sections', [])
        case_names = rag_params.get('case_names', [])
        keywords = rag_params.get('keywords', [])
        complexity = rag_params.get('complexity', 'medium')
        
        print(f"\n[PARAMETRIC RAG] Query: {query}")
        print(f"[PARAMETRIC RAG] Domain: {search_domain}")
        print(f"[PARAMETRIC RAG] Complexity: {complexity}")
        print(f"[PARAMETRIC RAG] Sections: {specific_sections}")
        print(f"[PARAMETRIC RAG] Keywords: {keywords}")
        
        # Build enhanced query with parameters
        enhanced_query = self._build_enhanced_query(
            query, search_domain, specific_sections, case_names, keywords
        )
        
        print(f"[PARAMETRIC RAG] Enhanced query: {enhanced_query}")
        
        # Determine retrieval count based on complexity
        retrieval_count = self._get_retrieval_count(complexity)
        
        # Execute retrieval - OPTIMIZED: Only use advanced pipeline for truly complex queries
        try:
            # PERFORMANCE FIX: Only use advanced retrieval for COMPLEX queries
            # Simple/Medium queries use direct search (MUCH faster)
            use_advanced = complexity == 'complex' and self.llm_client is not None
            
            if use_advanced and hasattr(self.store, 'advanced_search'):
                logger.info("[ADVANCED RAG] Using multi-query + HyDE + re-ranking pipeline (COMPLEX ONLY)")
                
                # Extract metadata filters from query (but don't force them)
                metadata_filter = self.advanced.extract_legal_metadata(query)
                
                # Define search function for advanced retrieval
                def cloud_search(q, n_results=10):
                    # First try WITH filters
                    if metadata_filter:
                        results = self.store.advanced_search(
                            q, 
                            n_results=n_results, 
                            metadata_filter=metadata_filter,
                            reranker=self.reranker
                        )
                        if results:
                            return results
                    
                    # Fallback: search WITHOUT filters
                    return self.store.advanced_search(
                        q, 
                        n_results=n_results, 
                        metadata_filter=None,  # No filter
                        reranker=self.reranker
                    )
                
                # Run advanced retrieval pipeline (ONLY for complex queries)
                results = self.advanced.advanced_retrieve(
                    query=enhanced_query,
                    search_func=cloud_search,
                    use_multi_query=True,  # Only for complex
                    use_hyde=True,  # Only for complex
                    use_compression=False,  # Disabled for speed
                    top_k=retrieval_count * 2
                )
                
                logger.info(f"[ADVANCED RAG] Retrieved {len(results)} documents via advanced pipeline")
                
            elif hasattr(self.store, 'hybrid_search'):
                # FAST PATH: Direct Milvus search for simple/medium queries
                # No multi-query, no HyDE, no slow LLM calls
                logger.info(f"[FAST RAG] Using direct Milvus search (complexity: {complexity})")
                results = self.store.hybrid_search(enhanced_query, n_results=retrieval_count * 2)
                logger.info(f"[FAST RAG] Retrieved {len(results)} documents directly")
                
            else:
                # Fallback to standard retriever
                results = self.retriever.retrieve(
                    enhanced_query,
                    use_reranking=(complexity == 'complex'),  # Only rerank complex
                    use_query_expansion=False  # Disabled for speed
                )
            
            # Filter results by domain if specified
            if search_domain != 'general':
                results = self._filter_by_domain(results, search_domain, specific_sections)
            
            # Limit to retrieval count
            results = results[:retrieval_count]
            
            # Build context from results
            context = self._build_context(results, query, rag_params)
            
            retrieval_time = time.time() - start_time
            
            print(f"[PARAMETRIC RAG] Retrieved {len(results)} documents in {retrieval_time:.2f}s")
            
            return {
                'documents': results,
                'context': context,
                'metadata': {
                    'retrieval_time': retrieval_time,
                    'document_count': len(results),
                    'search_domain': search_domain,
                    'complexity': complexity,
                    'enhanced_query': enhanced_query,
                    'advanced_mode': use_advanced if 'use_advanced' in dir() else False
                }
            }
            
        except Exception as e:
            print(f"[ERROR] Parametric retrieval failed: {e}")
            return {
                'documents': [],
                'context': '',
                'metadata': {
                    'error': str(e),
                    'retrieval_time': time.time() - start_time
                }
            }
    
    def _build_enhanced_query(
        self,
        original_query: str,
        domain: str,
        sections: List[str],
        cases: List[str],
        keywords: List[str]
    ) -> str:
        """Build enhanced query with parameters"""
        
        enhanced_parts = [original_query]
        
        # Add domain context
        if domain != 'general':
            enhanced_parts.append(domain)
        
        # Add specific sections
        if sections:
            enhanced_parts.append(' '.join(f"Section {s}" for s in sections))
        
        # Add case names
        if cases:
            enhanced_parts.append(' '.join(cases))
        
        # Add important keywords
        if keywords:
            # Filter out common words already in query
            new_keywords = [k for k in keywords if k.lower() not in original_query.lower()]
            if new_keywords:
                enhanced_parts.append(' '.join(new_keywords[:3]))  # Top 3 keywords
        
        return ' '.join(enhanced_parts)
    
    def _get_retrieval_count(self, complexity: str) -> int:
        """Determine document count based on complexity"""
        counts = {
            'simple': 2,    # Fast and focused
            'medium': 5,    # Balanced
            'complex': 8    # Comprehensive
        }
        return counts.get(complexity, 5)
    
    def _filter_by_domain(
        self,
        results: List[Dict],
        domain: str,
        sections: List[str]
    ) -> List[Dict]:
        """Filter results by legal domain using BOOST approach (80/20).

        Domain-relevant documents get boosted score (80% weight on domain match),
        but cross-domain documents are NEVER dropped — they get 20% base weight.
        This prevents missing constitutional/procedural cross-references.

        Uses expanded keywords from domain_specialist_profiles when available.
        """
        # Try to get expanded keywords from domain specialist module
        try:
            from kaanoon_test.system_adapters.domain_specialist_profiles import (
                get_domain_profile, get_expanded_filter_keywords
            )
            profile = get_domain_profile(domain)
            expanded_kw = get_expanded_filter_keywords(profile) if profile else []
        except ImportError:
            expanded_kw = []

        # Fallback domain keywords (legacy, used when domain_specialist_profiles not available)
        _legacy_domain_keywords = {
            'IPC': ['ipc', 'indian penal code', 'section', 'criminal', 'bns', 'penal'],
            'GST': ['gst', 'goods and services tax', 'tax', 'cgst', 'sgst', 'igst'],
            'DPDP': ['dpdp', 'dpdpa', 'data protection', 'privacy', 'personal data', 'it act'],
            'Contract': ['contract', 'agreement', 'indian contract act', 'breach', 'consideration'],
            'Property': ['property', 'ownership', 'transfer', 'land', 'rera', 'registration', 'deed'],
            'Criminal': ['criminal', 'offense', 'punishment', 'ipc', 'bns', 'fir', 'bail', 'arrest'],
            'Civil': ['civil', 'suit', 'damages', 'tort', 'negligence', 'injunction'],
            'Corporate': ['company', 'corporate', 'director', 'companies act', 'nclt', 'sebi', 'ibc'],
        }

        # Use expanded keywords if available, otherwise fallback
        keywords = expanded_kw if expanded_kw else _legacy_domain_keywords.get(domain, [])
        if not keywords:
            return results  # No filtering if domain not recognized

        # ── BOOST APPROACH: score ALL results, never drop any ──────────
        DOMAIN_WEIGHT = 0.80   # 80% weight for domain relevance
        BASE_WEIGHT   = 0.20   # 20% weight for original retrieval score

        for result in results:
            text = result.get('text', '').lower()
            original_score = result.get('score', 0.5)

            # Calculate domain keyword match count
            domain_hits = sum(1 for kw in keywords if kw in text)

            # Boost for specific section mentions
            section_bonus = 0
            if sections:
                for section in sections:
                    if section in text or f"section {section}" in text:
                        section_bonus += 3

            # Normalise domain score (0.0 – 1.0 range)
            max_possible = max(len(keywords), 1)
            domain_score = min((domain_hits + section_bonus) / max_possible, 1.0)

            # Combined boosted score: blend domain relevance + original relevance
            result['domain_score'] = domain_hits + section_bonus
            result['boosted_score'] = (
                DOMAIN_WEIGHT * domain_score + BASE_WEIGHT * original_score
            )

        # Sort by boosted score (domain-relevant docs bubble up)
        results.sort(key=lambda x: x.get('boosted_score', 0), reverse=True)

        return results  # ALWAYS return all results (boost, don't block)
    
    def _build_context(
        self,
        results: List[Dict],
        query: str,
        rag_params: Dict
    ) -> str:
        """Build context string from retrieved documents"""
        
        if not results:
            return ""
        
        context_parts = []
        
        # Add domain header if specific
        domain = rag_params.get('search_domain', 'general')
        if domain != 'general':
            context_parts.append(f"Legal Domain: {domain}\n")
        
        # Add each document
        for i, doc in enumerate(results, 1):
            text = doc.get('text', '')
            score = doc.get('score', 0)
            metadata = doc.get('metadata', {})
            
            # Truncate if too long
            if len(text) > 800:
                text = text[:800] + "..."
            
            context_parts.append(f"[Document {i}] (Relevance: {score:.2f})")
            context_parts.append(text)
            context_parts.append("")  # Empty line
        
        return '\n'.join(context_parts)
