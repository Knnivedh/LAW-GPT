"""
CLARIFICATION AGENT — Interactive Logic for Complex Legal Scenarios
==================================================================

Identifies "Data Quality Gaps" and generates 5 clarifying questions 
before the final RAG synthesis.
"""

import logging
import json
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ClarificationAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def identify_gaps(self, query: str, context: str) -> Optional[List[str]]:
        """
        Analyzes the query and retrieved context to find missing critical facts.
        Returns a list of 5 questions if complexity is high & gaps exist.
        """
        system_msg = (
            "You are a SENIOR LEGAL ANALYST. Your task is to identify 'Fact Gaps' "
            "in a complex legal scenario. If the information provided is insufficient "
            "for a definitive legal opinion, generate exactly 5 clarifying questions.\n\n"
            "Output ONLY valid JSON:\n"
            '{"has_gaps": true, "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"], "reasoning": "..."}'
        )
        
        user_msg = (
            f"SCENARIO: {query}\n\n"
            f"CURRENT CONTEXT (Partial): {context[:2000]}\n\n"
            "Identify the missing data points (e.g., specific terms of the contract, types of harm, "
            "procedural status) and generate the questions."
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
            return None
        except Exception as e:
            logger.error(f"[CLARIFIER] Failed to identify gaps: {e}")
            return None
