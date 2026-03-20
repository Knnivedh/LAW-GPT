"""
Case Law Citation Extractor
Extracts and validates Indian legal case citations from text
"""

import re
import json
from typing import List, Dict, Optional
from datetime import datetime


class CaseLawExtractor:
    """Extract Indian case law citations from legal text"""
    
    def __init__(self):
        # Common Indian courts
        self.courts = [
            "Supreme Court", "SC", "SCC",
            "High Court", "HC",
            "District Court", "Sessions Court",
            "AIR", "All India Reporter"
        ]
        
        # Citation patterns
        self.patterns = {
            'vs_pattern': r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'scc_pattern': r'\((\d{4})\)\s+(\d+)\s+SCC\s+(\d+)',
            'air_pattern': r'AIR\s+(\d{4})\s+(SC|[A-Z]{2,})\s+(\d+)',
            'in_re_pattern': r'In\s+re:?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'state_vs_pattern': r'(State\s+of\s+[A-Z][a-z]+)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        }
    
    def extract_all_cases(self, text: str) -> List[Dict]:
        """
        Extract all case citations from text
        
        Returns: List of case dictionaries with metadata
        """
        cases = []
        
        # Extract v/vs cases
        vs_matches = re.findall(self.patterns['vs_pattern'], text)
        for petitioner, respondent in vs_matches:
            case = {
                'type': 'vs_case',
                'petitioner': petitioner.strip(),
                'respondent': respondent.strip(),
                'full_name': f"{petitioner.strip()} v. {respondent.strip()}",
                'citation': None,
                'year': None,
                'court': None
            }
            
            # Try to find citation nearby
            case_context = self._get_context(text, petitioner, 100)
            citation = self._extract_citation(case_context)
            if citation:
                case.update(citation)
            
            cases.append(case)
        
        # Extract "In re" cases
        in_re_matches = re.findall(self.patterns['in_re_pattern'], text)
        for party in in_re_matches:
            cases.append({
                'type': 'in_re',
                'party': party.strip(),
                'full_name': f"In re {party.strip()}",
                'citation': None,
                'year': None,
                'court': None
            })
        
        # Extract State vs cases
        state_matches = re.findall(self.patterns['state_vs_pattern'], text)
        for state, accused in state_matches:
            cases.append({
                'type': 'state_vs',
                'petitioner': state.strip(),
                'respondent': accused.strip(),
                'full_name': f"{state.strip()} v. {accused.strip()}",
                'citation': None,
                'year': None,
                'court': None
            })
        
        return self._deduplicate_cases(cases)
    
    def _extract_citation(self, text: str) -> Optional[Dict]:
        """Extract SCC or AIR citation"""
        # SCC citation
        scc_match = re.search(self.patterns['scc_pattern'], text)
        if scc_match:
            year, volume, page = scc_match.groups()
            return {
                'citation': f"({year}) {volume} SCC {page}",
                'year': year,
                'court': 'Supreme Court',
                'citation_type': 'SCC'
            }
        
        # AIR citation
        air_match = re.search(self.patterns['air_pattern'], text)
        if air_match:
            year, court, page = air_match.groups()
            return {
                'citation': f"AIR {year} {court} {page}",
                'year': year,
                'court': 'Supreme Court' if court == 'SC' else f'{court} High Court',
                'citation_type': 'AIR'
            }
        
        return None
    
    def _get_context(self, text: str, keyword: str, chars: int = 100) -> str:
        """Get text context around keyword"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - chars)
        end = min(len(text), idx + len(keyword) + chars)
        return text[start:end]
    
    def _deduplicate_cases(self, cases: List[Dict]) -> List[Dict]:
        """Remove duplicate cases"""
        seen = set()
        unique = []
        for case in cases:
            key = case.get('full_name', '')
            if key and key not in seen:
                seen.add(key)
                unique.append(case)
        return unique
    
    def extract_landmark_cases(self, text: str) -> List[str]:
        """
        Extract landmark case names (commonly cited)
        """
        landmark_cases = [
            "Kesavananda Bharati", "Maneka Gandhi", "Minerva Mills",
            "Bachan Singh", "Machhi Singh", "Vishaka",
            "Nirbhaya", "Shreya Singhal", "Puttaswamy",
            "Navtej Singh Johar", "Sabarimala", "Ayodhya",
            "Shah Bano", "Lily Thomas", "Common Cause"
        ]
        
        found = []
        for case in landmark_cases:
            if case.lower() in text.lower():
                found.append(case)
        
        return found
    
    def format_case_citation(self, case: Dict) -> str:
        """Format case for display"""
        if case.get('citation'):
            return f"{case['full_name']} {case['citation']}"
        else:
            return case['full_name']
    
    def to_json(self, cases: List[Dict]) -> str:
        """Convert cases to JSON"""
        return json.dumps(cases, indent=2, ensure_ascii=False)


# Landmark Indian Cases Database (JSON)
LANDMARK_CASES_DB = {
    "criminal_law": [
        {
            "name": "Bachan Singh v. State of Punjab",
            "citation": "(1980) 2 SCC 684",
            "year": "1980",
            "court": "Supreme Court",
            "significance": "Rarest of rare doctrine for death penalty",
            "sections": ["IPC 302"]
        },
        {
            "name": "Machhi Singh v. State of Punjab",
            "citation": "(1983) 3 SCC 470",
            "year": "1983",
            "court": "Supreme Court",
            "significance": "Guidelines for rarest of rare cases",
            "sections": ["IPC 302"]
        },
        {
            "name": "State of Maharashtra v. Madhukar Narayan Mardikar",
            "citation": "(1991) 1 SCC 57",
            "year": "1991",
            "court": "Supreme Court",
            "significance": "Confession to police not admissible",
            "sections": ["Evidence Act 25"]
        }
    ],
    "constitutional_law": [
        {
            "name": "Kesavananda Bharati v. State of Kerala",
            "citation": "(1973) 4 SCC 225",
            "year": "1973",
            "court": "Supreme Court",
            "significance": "Basic structure doctrine",
            "sections": ["Article 368"]
        },
        {
            "name": "Maneka Gandhi v. Union of India",
            "citation": "(1978) 1 SCC 248",
            "year": "1978",
            "court": "Supreme Court",
            "significance": "Expanded Article 21 - Right to life",
            "sections": ["Article 21"]
        }
    ],
    "property_law": [
        {
            "name": "T. Anjanappa v. Somalingappa",
            "citation": "(2006) 7 SCC 570",
            "year": "2006",
            "court": "Supreme Court",
            "significance": "Adverse possession requirements",
            "sections": ["Limitation Act"]
        }
    ],
    "corruption": [
        {
            "name": "P.V. Narasimha Rao v. State",
            "citation": "(1998) 4 SCC 626",
            "year": "1998",
            "court": "Supreme Court",
            "significance": "Bribery and corruption of public servants",
            "sections": ["IPC 120B", "IPC 409", "Prevention of Corruption Act"]
        }
    ]
}


def get_relevant_cases(ipc_sections: List[str]) -> List[Dict]:
    """Get relevant landmark cases for IPC sections"""
    relevant = []
    for category, cases in LANDMARK_CASES_DB.items():
        for case in cases:
            if any(sec in case.get('sections', []) for sec in ipc_sections):
                relevant.append(case)
    return relevant


def save_cases_to_json(cases: List[Dict], filename: str):
    """Save extracted cases to JSON file"""
    data = {
        'extracted_at': datetime.now().isoformat(),
        'total_cases': len(cases),
        'cases': cases
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Test
    extractor = CaseLawExtractor()
    
    test_text = """
    In Bachan Singh v. State of Punjab (1980) 2 SCC 684, the Supreme Court 
    established the 'rarest of rare' doctrine. Similarly, in Machhi Singh v. 
    State of Punjab (1983) 3 SCC 470, guidelines were provided. The case of 
    Kesavananda Bharati established the basic structure doctrine.
    """
    
    print("="*80)
    print("CASE LAW EXTRACTOR - TEST RESULTS")
    print("="*80)
    
    cases = extractor.extract_all_cases(test_text)
    print(f"\nExtracted {len(cases)} cases:")
    print(extractor.to_json(cases))
    
    print("\n" + "="*80)
    print("LANDMARK CASES DATABASE")
    print("="*80)
    print(json.dumps(LANDMARK_CASES_DB, indent=2))

