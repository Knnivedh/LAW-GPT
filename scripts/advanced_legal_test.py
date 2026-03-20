"""
Advanced Legal RAG System Test Suite
Contains 10 complex legal scenarios provided by user for gap analysis
"""
import requests
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import statistics
from datetime import datetime

# Configuration
API_URL = "http://localhost:7860/api/query"
OUTPUT_FILE = f"advanced_legal_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# USER PROVIDED SCENARIOS
TEST_SCENARIOS = [
    {
        "id": "Q1",
        "category": "Constitutional Law + Preventive Detention",
        "complexity": "HIGH",
        "query": "A social activist is detained under a State preventive detention law for allegedly 'disturbing public order' due to online posts. The detention order supplies documents in English, while the detainee understands only Kannada. Representation is rejected within 48 hours. Is the detention valid? Examine Article 22 safeguards, language rights, and procedural compliance.",
        "expected_keywords": ["Article 22(5)", "communication of grounds", "language", "representation", "Harikisan v. State of Maharashtra"],
        "min_length": 300
    },
    {
        "id": "Q2",
        "category": "CPC + Res Judicata + Limitation",
        "complexity": "HIGH",
        "query": "A partition suit is dismissed on technical grounds without deciding shares. After 15 years, one legal heir files a fresh suit claiming ignorance of earlier proceedings. Is the fresh suit barred by res judicata or limitation? Can ignorance be a valid ground?",
        "expected_keywords": ["Res Judicata", "Section 11 CPC", "Limitation Act", "Order 2 Rule 2", "technical grounds", "merits"],
        "min_length": 300
    },
    {
        "id": "Q3",
        "category": "Criminal Law + Evidence + Hostile Witness",
        "complexity": "HIGH",
        "query": "In a murder trial, all eyewitnesses turn hostile. CCTV footage is partially unclear. The prosecution relies on call-detail records and recovery of weapon. Can conviction be sustained? Analyze circumstantial evidence and burden of proof.",
        "expected_keywords": ["Section 154 Evidence Act", "hostile witness", "circumstantial evidence", "chain of circumstances", "Sharad Birdhichand Sarda"],
        "min_length": 300
    },
    {
        "id": "Q4",
        "category": "Family Law + Constitutional Autonomy",
        "complexity": "HIGH",
        "query": "A 24-year-old woman converts religion and marries by choice. Her parents file a writ claiming 'psychological coercion' and seek custody. What will the court prioritize? Discuss personal liberty, consent, and parental rights.",
        "expected_keywords": ["Hadiya case", "Shafin Jahan", "Article 21", "right to choose partner", "parens patriae"],
        "min_length": 300
    },
    {
        "id": "Q5",
        "category": "Arbitration + Insolvency (IBC)",
        "complexity": "HIGH",
        "query": "A company initiates arbitration for recovery. During proceedings, the opposite party is admitted into CIRP under IBC. Does the arbitration continue? Analyze moratorium under Section 14 IBC and its impact.",
        "expected_keywords": ["Section 14 IBC", "Moratorium", "Alchemist Asset Reconstruction", "continuation of proceedings", "NCLT"],
        "min_length": 300
    },
    {
        "id": "Q6",
        "category": "Cyber Law + IT Act + Intermediary Liability",
        "complexity": "HIGH",
        "query": "A deepfake video goes viral causing reputational harm. The platform delays takedown citing 'content neutrality.' Is the platform liable? Examine safe-harbour, due diligence, and current IT Rules.",
        "expected_keywords": ["Section 79 IT Act", "Intermediary Guidelines", "Shreya Singhal", "safe harbour", "due diligence"],
        "min_length": 300
    },
    {
        "id": "Q7",
        "category": "NDPS + Bail + Delay in Trial",
        "complexity": "HIGH",
        "query": "An accused is in custody for 4 years under NDPS Act. Trial has not commenced due to forensic delays. Can constitutional bail override statutory restrictions? Discuss Article 21 jurisprudence.",
        "expected_keywords": ["Section 37 NDPS", "Article 21", "speedy trial", "Union of India v. K.A. Najeeb", "undue delay"],
        "min_length": 300
    },
    {
        "id": "Q8",
        "category": "Property Law + Adverse Possession",
        "complexity": "HIGH",
        "query": "A government authority claims adverse possession over private land used as a public road for 25 years without formal acquisition. Can the State claim adverse possession? Analyze constitutional limits and precedents.",
        "expected_keywords": ["Adverse Possession", "Article 300A", "Vidya Devi v. State of HP", "state claiming adverse possession"],
        "min_length": 300
    },
    {
        "id": "Q9",
        "category": "Service Law + Natural Justice",
        "complexity": "HIGH",
        "query": "A civil servant is compulsorily retired based on confidential reports never communicated to him. Is the action valid? Examine fairness, transparency, and judicial review scope.",
        "expected_keywords": ["Natural Justice", "uncommunicated ACRs", "Dev Dutt v. Union of India", "civil consequences", "arbitrariness"],
        "min_length": 300
    },
    {
        "id": "Q10",
        "category": "Medical Law + Criminal Negligence",
        "complexity": "HIGH",
        "query": "A doctor performs an emergency surgery without consent, leading to patient death. Relatives file FIR under Section 304A IPC. Does this amount to criminal negligence? Distinguish civil negligence from criminal liability.",
        "expected_keywords": ["Section 304A IPC", "Jacob Mathew v. State of Punjab", "gross negligence", "Bolam test", "medical negligence"],
        "min_length": 300
    }
]

def analyze_response(scenario: Dict, response: Dict, duration: float) -> Dict:
    """Analyze the quality of the response"""
    
    # Extract response text
    if isinstance(response, dict):
        answer = response.get('answer', '')
        sources = response.get('source_documents', [])
    else:
        answer = str(response)
        sources = []
        
    scores = {
        "completeness": 0,
        "legal_elements": 0,
        "case_laws": 0,
        "sources": 0,
        "structure": 0
    }
    
    gaps = []
    strengths = []
    
    # 1. Completeness (Max 25)
    if len(answer) > scenario['min_length']:
        scores['completeness'] = 25
        strengths.append("Comprehensive response length")
    elif len(answer) > scenario['min_length'] / 2:
        scores['completeness'] = 15
        gaps.append("Response too brief")
    else:
        scores['completeness'] = 5
        gaps.append("Response significantly too short")
        
    # 2. Key Legal Elements (Max 30)
    found_keywords = []
    for keyword in scenario['expected_keywords']:
        if keyword.lower() in answer.lower():
            found_keywords.append(keyword)
            
    keyword_score = (len(found_keywords) / len(scenario['expected_keywords'])) * 30
    scores['legal_elements'] = keyword_score
    
    if len(found_keywords) == 0:
        gaps.append("CRITICAL: Major legal elements missing")
    elif len(found_keywords) < len(scenario['expected_keywords']) / 2:
        gaps.append(f"Missing key concepts: {[k for k in scenario['expected_keywords'] if k not in found_keywords]}")
    
    # 3. Case Laws (Max 20)
    # Check if any specific case law from expectations was cited
    cited_cases = False
    for keyword in scenario['expected_keywords']:
        if " v. " in keyword or " vs. " in keyword or " case" in keyword.lower():
            if keyword.lower() in answer.lower():
                cited_cases = True
                scores['case_laws'] = 20
                strengths.append(f"Cited: {keyword}")
                break
    
    if not cited_cases:
        # Check generic case citation
        if " v. " in answer or " vs. " in answer or "AIR " in answer or "SCC" in answer:
            scores['case_laws'] = 10
            strengths.append("Cited general case law")
        else:
            scores['case_laws'] = 0
            gaps.append("No landmark case laws cited")
            
    # 4. Sources/Citations (Max 15)
    if sources and len(sources) > 0:
        scores['sources'] = 15
        strengths.append(f"Retrieved {len(sources)} sources")
    else:
        scores['sources'] = 5
        gaps.append("Limited source retrieval")
        
    # 5. Structure (Max 10)
    if "Conclusion" in answer or "Summary" in answer:
        scores['structure'] += 5
    if "\n" in answer and ("1." in answer or "-" in answer):
        scores['structure'] += 5
        
    total_score = sum(scores.values())
    
    # Determine Grade
    if total_score >= 80: grade = "A - Excellent"
    elif total_score >= 70: grade = "B - Good"
    elif total_score >= 60: grade = "C - Acceptable"
    elif total_score >= 40: grade = "D - Poor"
    else: grade = "F - Failed"
    
    return {
        "test_id": scenario['id'],
        "title": scenario['category'],
        "scores": scores,
        "gaps": gaps,
        "strengths": strengths,
        "critical_issues": [g for g in gaps if "CRITICAL" in g],
        "total_score": total_score,
        "grade": grade,
        "duration": round(duration, 2)
    }

def run_test_scenario(scenario):
    """Run a single test scenario"""
    print(f"\n📋 Question: {scenario['category']}")
    print(f"   {scenario['query'][:100]}...")
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json={"question": scenario['query'], "category": scenario['category']}, timeout=60)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            analysis = analyze_response(scenario, result, duration)
            print(f"   ✅ Answered in {duration:.1f}s | Score: {analysis['total_score']} | Grade: {analysis['grade']}")
            return analysis
        else:
            print(f"   ❌ API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
        return None

def main():
    print("=" * 80)
    print("🏛️  USER-SPECIFIED GAP ANALYSIS TEST")
    print("=" * 80)
    
    results = []
    
    # Run tests sequentially to avoid overloading backend
    for scenario in TEST_SCENARIOS:
        result = run_test_scenario(scenario)
        if result:
            results.append(result)
        time.sleep(2)
    
    # Calculate Overall Stats
    if not results:
        print("No results collected.")
        return

    avg_score = statistics.mean([r['total_score'] for r in results])
    passed = len([r for r in results if r['total_score'] >= 60])
    failed = len(results) - passed
    
    overall_grade = "F - NOT READY"
    if avg_score >= 90: overall_grade = "A+ - WORLD CLASS"
    elif avg_score >= 80: overall_grade = "A - PRODUCTION READY"
    elif avg_score >= 70: overall_grade = "B - GOOD"
    elif avg_score >= 60: overall_grade = "C - ACCEPTABLE"
    
    # Save Report
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_score": round(avg_score, 2),
        "overall_grade": overall_grade,
        "results": results,
        "statistics": {
            "total_tests": len(TEST_SCENARIOS),
            "completed": len(results),
            "passed": passed,
            "failed": failed
        }
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
        
    print("\n" + "=" * 80)
    print(f"📊 FINAL SCORE: {avg_score:.1f}/100 ({overall_grade})")
    print(f"✅ Passed: {passed}/{len(TEST_SCENARIOS)}")
    print(f"💾 Report saved to: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
