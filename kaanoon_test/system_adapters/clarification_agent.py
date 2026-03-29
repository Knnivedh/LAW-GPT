"""
CLARIFICATION AGENT — Interactive Logic for Complex Legal Scenarios
==================================================================

Identifies "Data Quality Gaps" and generates 5 clarifying questions 
before the final RAG synthesis.
"""

import logging
import json
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ClarificationAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def identify_gaps(self, query: str, context: str) -> Optional[List[str]]:
        """
        Analyzes the query and retrieved context to find missing critical facts.
        Returns a list of 5 questions if complexity is high & gaps exist.
        
        For complex multi-party scenarios (data breach + consumer commission +
        PIL + arbitration), this MUST always detect gaps — these scenarios
        invariably have missing jurisdictional, procedural, or factual details.
        """
        system_msg = (
            "You are a SENIOR LEGAL ANALYST specialising in Indian law with 25+ years of practice. "
            "Your task is to identify 'Fact Gaps' — missing information that would be ESSENTIAL "
            "for a precise, court-quality legal opinion.\n\n"
            "CRITICAL RULES:\n"
            "1. For scenarios involving MULTIPLE PARTIES, MULTIPLE LEGAL DOMAINS, or MULTIPLE "
            "   PROCEEDINGS (e.g., consumer commission + PIL + criminal complaint), you MUST "
            "   identify gaps. These scenarios ALWAYS have missing information.\n"
            "2. For each gap, generate a SPECIFIC, TARGETED question — not generic questions "
            "   like 'Can you provide more details?' but precise legal questions like "
            "   'What specific cybersecurity standards (e.g., ISO/IEC 27001) did the company "
            "   claim to follow before the breach?'\n"
            "3. You MUST generate EXACTLY 5 questions covering these dimensions:\n"
            "   Q1: Jurisdictional/procedural (forum, limitation period, standing)\n"
            "   Q2: Factual specifics (dates, amounts, evidence, contract terms)\n"
            "   Q3: Parties and relationships (roles, obligations, prior disputes)\n"
            "   Q4: Harm and damages (quantifiable loss, consequential harm, class size)\n"
            "   Q5: Prior proceedings or remedies attempted\n\n"
            "Output ONLY valid JSON:\n"
            '{"has_gaps": true, "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"], "reasoning": "..."}'
        )
        
        user_msg = (
            f"SCENARIO: {query}\n\n"
            f"CURRENT CONTEXT (Partial): {context[:2000]}\n\n"
            "Identify the missing data points (e.g., specific terms of the contract, types of harm, "
            "procedural status, jurisdictional details, quantifiable damages, evidence available, "
            "limitation periods) and generate the questions."
        )

        try:
            resp = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            
            if data.get("has_gaps") and len(data.get("questions", [])) >= 5:
                return data["questions"][:5]
            
            # FALLBACK: For long multi-domain queries, force gap detection
            # even if the LLM failed to identify gaps (false negative)
            if self._is_complex_multi_domain(query) and len(data.get("questions", [])) >= 3:
                logger.info("[CLARIFIER] Forcing gap detection for complex multi-domain query")
                return data["questions"][:5]
            
            return None
        except Exception as e:
            logger.error(f"[CLARIFIER] Failed to identify gaps: {e}")
            # For complex queries, return generic but useful questions rather than None
            if self._is_complex_multi_domain(query):
                logger.info("[CLARIFIER] Returning fallback questions for complex scenario")
                return self._fallback_questions(query)
            return None
    
    def _is_complex_multi_domain(self, query: str) -> bool:
        """Check if query involves multiple legal domains and is sufficiently complex."""
        query_lower = query.lower()
        word_count = len(query.split())
        if word_count < 80:
            return False
        
        domains = [
            'consumer protection', 'consumer commission', 'data privacy', 'data protection',
            'data breach', 'arbitration', 'pil', 'public interest', 'high court',
            'criminal', 'fir', 'it act', 'dpdpa', 'article 21', 'fundamental right',
            'unfair trade', 'deficiency in service',
        ]
        domain_hits = sum(1 for d in domains if d in query_lower)
        return domain_hits >= 3
    
    def _fallback_questions(self, query: str) -> List[str]:
        """Generate sensible fallback questions for complex scenarios."""
        return [
            "What is the specific jurisdiction and forum where proceedings have been initiated or are contemplated?",
            "What are the exact dates and timeline of key events (e.g., registration, breach discovery, complaint filing)?",
            "What specific contractual terms or clauses are being challenged, and do you have copies of the agreements?",
            "What is the nature and quantum of damages suffered — are there quantifiable financial losses or primarily non-pecuniary harm?",
            "Have any prior legal remedies been attempted (e.g., consumer complaint, police FIR, regulatory notice), and what was the outcome?",
        ]

