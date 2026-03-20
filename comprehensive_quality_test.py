"""
Comprehensive Chatbot Quality Assessment Framework
Tests LAW-GPT across multiple dimensions and identifies gaps
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import re

class ChatbotQualityTester:
    """Comprehensive quality testing for LAW-GPT chatbot"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.results = []
        self.test_categories = {
            "IPC_Sections": [],
            "Legal_Procedures": [],
            "Case_Laws": [],
            "Constitutional_Law": [],
            "Criminal_Law": [],
            "Civil_Law": [],
            "Family_Law": [],
            "Property_Law": [],
            "Corporate_Law": [],
            "Edge_Cases": [],
            "Multilingual": [],
            "Complex_Scenarios": []
        }
        
    def get_comprehensive_test_queries(self) -> List[Dict[str, Any]]:
        """Generate comprehensive test queries across all dimensions"""
        
        return [
            # ============ IPC SECTIONS (Basic) ============
            {
                "category": "IPC_Sections",
                "query": "What is IPC Section 302?",
                "expected_keywords": ["murder", "death", "life imprisonment", "intention"],
                "difficulty": "easy"
            },
            {
                "category": "IPC_Sections",
                "query": "Explain IPC 420 with examples",
                "expected_keywords": ["cheating", "dishonestly", "fraud", "deception"],
                "difficulty": "easy"
            },
            {
                "category": "IPC_Sections",
                "query": "What is the difference between IPC 302 and IPC 304?",
                "expected_keywords": ["murder", "culpable homicide", "intention", "knowledge"],
                "difficulty": "medium"
            },
            {
                "category": "IPC_Sections",
                "query": "What is IPC 498A?",
                "expected_keywords": ["cruelty", "husband", "relatives", "woman", "dowry"],
                "difficulty": "easy"
            },
            {
                "category": "IPC_Sections",
                "query": "Explain IPC 376 and its amendments",
                "expected_keywords": ["rape", "sexual assault", "consent", "punishment"],
                "difficulty": "medium"
            },
            
            # ============ LEGAL PROCEDURES ============
            {
                "category": "Legal_Procedures",
                "query": "How to file an FIR?",
                "expected_keywords": ["police station", "cognizable", "section 154", "crpc"],
                "difficulty": "easy"
            },
            {
                "category": "Legal_Procedures",
                "query": "What is the difference between FIR and complaint?",
                "expected_keywords": ["cognizable", "non-cognizable", "magistrate", "police"],
                "difficulty": "medium"
            },
            {
                "category": "Legal_Procedures",
                "query": "How does bail work in India?",
                "expected_keywords": ["bail", "crpc", "anticipatory", "regular", "surety"],
                "difficulty": "medium"
            },
            {
                "category": "Legal_Procedures",
                "query": "What is the process for filing a divorce in India?",
                "expected_keywords": ["petition", "grounds", "mutual consent", "contested"],
                "difficulty": "medium"
            },
            {
                "category": "Legal_Procedures",
                "query": "How to file a consumer complaint?",
                "expected_keywords": ["consumer forum", "goods", "services", "deficiency"],
                "difficulty": "easy"
            },
            
            # ============ CASE LAWS ============
            {
                "category": "Case_Laws",
                "query": "What is the Kesavananda Bharati case about?",
                "expected_keywords": ["basic structure", "constitution", "amendment", "supreme court"],
                "difficulty": "medium"
            },
            {
                "category": "Case_Laws",
                "query": "Explain Vishaka Guidelines",
                "expected_keywords": ["sexual harassment", "workplace", "women", "guidelines"],
                "difficulty": "medium"
            },
            {
                "category": "Case_Laws",
                "query": "What is Rarest of Rare doctrine?",
                "expected_keywords": ["death penalty", "bachan singh", "alternative", "life imprisonment"],
                "difficulty": "medium"
            },
            
            # ============ CONSTITUTIONAL LAW ============
            {
                "category": "Constitutional_Law",
                "query": "What are fundamental rights under Indian Constitution?",
                "expected_keywords": ["article", "equality", "freedom", "rights", "part iii"],
                "difficulty": "easy"
            },
            {
                "category": "Constitutional_Law",
                "query": "Explain Article 21 of Indian Constitution",
                "expected_keywords": ["life", "personal liberty", "right to life", "due process"],
                "difficulty": "easy"
            },
            {
                "category": "Constitutional_Law",
                "query": "What is the difference between Article 32 and Article 226?",
                "expected_keywords": ["writ", "supreme court", "high court", "remedy"],
                "difficulty": "hard"
            },
            
            # ============ CRIMINAL LAW ============
            {
                "category": "Criminal_Law",
                "query": "What is the difference between cognizable and non-cognizable offenses?",
                "expected_keywords": ["police", "arrest", "warrant", "magistrate"],
                "difficulty": "medium"
            },
            {
                "category": "Criminal_Law",
                "query": "What is anticipatory bail?",
                "expected_keywords": ["section 438", "arrest", "protection", "crpc"],
                "difficulty": "medium"
            },
            {
                "category": "Criminal_Law",
                "query": "Explain the concept of mens rea and actus reus",
                "expected_keywords": ["guilty mind", "criminal act", "intention", "essential"],
                "difficulty": "hard"
            },
            
            # ============ CIVIL LAW ============
            {
                "category": "Civil_Law",
                "query": "What is a civil suit?",
                "expected_keywords": ["dispute", "rights", "cpc", "plaintiff", "defendant"],
                "difficulty": "easy"
            },
            {
                "category": "Civil_Law",
                "query": "How to get injunction in civil cases?",
                "expected_keywords": ["order 39", "cpc", "temporary", "permanent", "interim"],
                "difficulty": "medium"
            },
            
            # ============ FAMILY LAW ============
            {
                "category": "Family_Law",
                "query": "What are the grounds for divorce under Hindu Marriage Act?",
                "expected_keywords": ["adultery", "cruelty", "desertion", "conversion"],
                "difficulty": "medium"
            },
            {
                "category": "Family_Law",
                "query": "What is Section 498A IPC about cruelty to women?",
                "expected_keywords": ["husband", "relatives", "cruelty", "harassment", "dowry"],
                "difficulty": "easy"
            },
            {
                "category": "Family_Law",
                "query": "What is the right to maintenance under Section 125 CrPC?",
                "expected_keywords": ["wife", "children", "parents", "maintenance", "monthly"],
                "difficulty": "medium"
            },
            
            # ============ PROPERTY LAW ============
            {
                "category": "Property_Law",
                "query": "What is the Transfer of Property Act?",
                "expected_keywords": ["sale", "mortgage", "lease", "gift", "transfer"],
                "difficulty": "easy"
            },
            {
                "category": "Property_Law",
                "query": "How does adverse possession work in India?",
                "expected_keywords": ["12 years", "continuous", "possession", "hostile", "title"],
                "difficulty": "hard"
            },
            
            # ============ CORPORATE LAW ============
            {
                "category": "Corporate_Law",
                "query": "What is Section 420 of Companies Act 2013?",
                "expected_keywords": ["company", "corporate", "provision"],
                "difficulty": "medium"
            },
            
            # ============ EDGE CASES ============
            {
                "category": "Edge_Cases",
                "query": "What is IPC 999?",  # Non-existent section
                "expected_keywords": ["not exist", "invalid", "no such section"],
                "difficulty": "easy",
                "should_identify_error": True
            },
            {
                "category": "Edge_Cases",
                "query": "Can I murder someone in self-defense?",
                "expected_keywords": ["self-defense", "exception", "ipc 100", "private defense"],
                "difficulty": "medium"
            },
            {
                "category": "Edge_Cases",
                "query": "xyz abc random question",
                "expected_keywords": ["clarify", "understand", "rephrase", "legal"],
                "difficulty": "easy",
                "should_handle_unclear": True
            },
            
            # ============ MULTILINGUAL ============
            {
                "category": "Multilingual",
                "query": "आईपीसी धारा 302 क्या है?",  # Hindi: What is IPC Section 302?
                "expected_keywords": ["murder", "हत्या"],
                "difficulty": "medium"
            },
            
            # ============ COMPLEX SCENARIOS ============
            {
                "category": "Complex_Scenarios",
                "query": "A person was arrested without warrant for a non-cognizable offense. What are his rights?",
                "expected_keywords": ["illegal", "arrest", "non-cognizable", "warrant", "rights"],
                "difficulty": "hard"
            },
            {
                "category": "Complex_Scenarios",
                "query": "Can a confessional statement made to police be used as evidence?",
                "expected_keywords": ["section 25", "evidence act", "inadmissible", "magistrate"],
                "difficulty": "hard"
            },
            {
                "category": "Complex_Scenarios",
                "query": "What happens if someone commits a crime while mentally ill?",
                "expected_keywords": ["section 84", "unsound mind", "insanity", "defense"],
                "difficulty": "hard"
            },
        ]
    
    def query_chatbot(self, question: str, category: str = "general") -> Dict[str, Any]:
        """Query the chatbot API"""
        try:
            response = requests.post(
                f"{self.api_url}/api/query",
                json={"question": question, "category": category},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_response_quality(self, query_data: Dict, response: Dict) -> Dict[str, Any]:
        """Analyze the quality of a single response"""
        
        analysis = {
            "query": query_data["query"],
            "category": query_data["category"],
            "difficulty": query_data["difficulty"],
            "timestamp": datetime.now().isoformat(),
            "response_received": "error" not in response,
            "metrics": {}
        }
        
        if "error" in response:
            analysis["error"] = response["error"]
            analysis["metrics"]["overall_score"] = 0
            return analysis
        
        # Extract answer text
        answer = ""
        if "response" in response and "answer" in response["response"]:
            answer = response["response"]["answer"]
        elif "answer" in response:
            answer = response["answer"]
        
        analysis["answer"] = answer
        analysis["latency"] = response.get("response", {}).get("latency", 0)
        
        # Metrics to evaluate
        metrics = {}
        
        # 1. Keyword Coverage (Are expected keywords present?)
        expected_keywords = query_data.get("expected_keywords", [])
        found_keywords = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        metrics["keyword_coverage"] = len(found_keywords) / len(expected_keywords) if expected_keywords else 0
        metrics["found_keywords"] = found_keywords
        metrics["missing_keywords"] = [kw for kw in expected_keywords if kw not in found_keywords]
        
        # 2. Answer Length (Is it substantial?)
        metrics["answer_length"] = len(answer)
        metrics["answer_length_adequate"] = len(answer) > 100  # At least 100 characters
        
        # 3. Structure Quality (Does it have proper formatting?)
        metrics["has_sections"] = bool(re.search(r'(Key|Section|Provision|Definition|Penalty|Related)', answer, re.I))
        metrics["has_citations"] = bool(re.search(r'(Section \d+|IPC|CrPC|Article|Act)', answer))
        
        # 4. Legal Accuracy Indicators
        metrics["has_legal_references"] = bool(re.search(r'(IPC|CrPC|Constitution|Act|Section|Article)', answer))
        metrics["has_case_law"] = bool(re.search(r'(v\.|vs\.|versus|Supreme Court|High Court)', answer))
        
        # 5. Completeness (Does it address the query comprehensively?)
        query_lower = query_data["query"].lower()
        if "what is" in query_lower or "explain" in query_lower:
            metrics["provides_definition"] = len(answer) > 50
        if "how to" in query_lower or "process" in query_lower:
            metrics["provides_procedure"] = "step" in answer.lower() or re.search(r'\d+\.', answer)
        if "difference" in query_lower:
            metrics["compares_concepts"] = answer.count("whereas") > 0 or answer.count("while") > 0
        
        # 6. Error Handling
        if query_data.get("should_identify_error"):
            metrics["identifies_error"] = any(word in answer.lower() for word in ["not exist", "invalid", "no such"])
        
        if query_data.get("should_handle_unclear"):
            metrics["handles_unclear"] = any(word in answer.lower() for word in ["clarify", "understand", "rephrase"])
        
        # 7. Response Time
        metrics["fast_response"] = analysis["latency"] < 5.0  # Under 5 seconds
        
        # Calculate Overall Score (0-100)
        score_components = []
        
        score_components.append(metrics["keyword_coverage"] * 30)  # 30% weight
        score_components.append(20 if metrics["answer_length_adequate"] else 0)  # 20% weight
        score_components.append(15 if metrics["has_legal_references"] else 0)  # 15% weight
        score_components.append(15 if metrics["has_sections"] else 0)  # 15% weight
        score_components.append(10 if metrics["has_citations"] else 0)  # 10% weight
        score_components.append(10 if metrics["fast_response"] else 5)  # 10% weight
        
        metrics["overall_score"] = sum(score_components)
        
        # Determine Pass/Fail (>70 is pass)
        metrics["verdict"] = "PASS" if metrics["overall_score"] >= 70 else "FAIL"
        
        analysis["metrics"] = metrics
        
        return analysis
    
    def run_comprehensive_test(self):
        """Run all tests and collect results"""
        
        print("="*80)
        print("COMPREHENSIVE CHATBOT QUALITY ASSESSMENT")
        print("="*80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        test_queries = self.get_comprehensive_test_queries()
        total_tests = len(test_queries)
        
        print(f"Total Test Cases: {total_tests}")
        print(f"API Endpoint: {self.api_url}")
        print()
        
        for idx, query_data in enumerate(test_queries, 1):
            print(f"[{idx}/{total_tests}] Testing: {query_data['query'][:60]}...")
            
            # Query the chatbot
            response = self.query_chatbot(query_data["query"], query_data["category"])
            
            # Analyze response
            analysis = self.analyze_response_quality(query_data, response)
            
            # Store result
            self.results.append(analysis)
            self.test_categories[query_data["category"]].append(analysis)
            
            # Print quick result
            if "metrics" in analysis:
                score = analysis["metrics"]["overall_score"]
                verdict = analysis["metrics"]["verdict"]
                print(f"   Score: {score:.1f}/100 | {verdict}")
            else:
                print(f"   ERROR: {analysis.get('error', 'Unknown error')}")
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
        
        print()
        print("="*80)
        print("Testing Complete!")
        print("="*80)
    
    def generate_report(self) -> str:
        """Generate comprehensive quality assessment report"""
        
        if not self.results:
            return "No test results available"
        
        report = []
        report.append("="*80)
        report.append("LAW-GPT CHATBOT QUALITY ASSESSMENT REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {len(self.results)}")
        report.append("")
        
        # Overall Statistics
        total_score = sum(r["metrics"]["overall_score"] for r in self.results if "metrics" in r)
        avg_score = total_score / len(self.results)
        passed = sum(1 for r in self.results if r.get("metrics", {}).get("verdict") == "PASS")
        failed = len(self.results) - passed
        
        report.append("OVERALL STATISTICS")
        report.append("-" * 80)
        report.append(f"Average Score: {avg_score:.2f}/100")
        report.append(f"Pass Rate: {(passed/len(self.results)*100):.1f}% ({passed}/{len(self.results)})")
        report.append(f"Failed Tests: {failed}")
        report.append("")
        
        # Category-wise Analysis
        report.append("CATEGORY-WISE PERFORMANCE")
        report.append("-" * 80)
        
        for category, tests in self.test_categories.items():
            if not tests:
                continue
            
            cat_avg = sum(t["metrics"]["overall_score"] for t in tests if "metrics" in t) / len(tests)
            cat_passed = sum(1 for t in tests if t.get("metrics", {}).get("verdict") == "PASS")
            
            report.append(f"{category:25} | Avg: {cat_avg:5.1f} | Pass: {cat_passed}/{len(tests)}")
        
        report.append("")
        
        # Key Issues Found
        report.append("KEY ISSUES IDENTIFIED")
        report.append("-" * 80)
        
        issues = []
        for result in self.results:
            if "metrics" not in result:
                continue
            
            metrics = result["metrics"]
            
            if metrics["overall_score"] < 70:
                issue = f"Low score ({metrics['overall_score']:.0f}): {result['query'][:50]}..."
                if metrics.get("missing_keywords"):
                    issue += f"\n  Missing: {', '.join(metrics['missing_keywords'][:3])}"
                issues.append(issue)
        
        if issues:
            for issue in issues[:10]:  # Top 10 issues
                report.append(f"• {issue}")
        else:
            report.append("No major issues identified!")
        
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 80)
        
        recommendations = []
        
        # Check keyword coverage
        avg_keyword_coverage = sum(r["metrics"].get("keyword_coverage", 0) for r in self.results if "metrics" in r) / len(self.results)
        if avg_keyword_coverage < 0.7:
            recommendations.append("• Improve keyword coverage in responses (currently {:.1%})".format(avg_keyword_coverage))
        
        # Check citation quality
        citation_rate = sum(1 for r in self.results if r.get("metrics", {}).get("has_citations", False)) / len(self.results)
        if citation_rate < 0.8:
            recommendations.append("• Increase legal citations in responses (currently {:.1%})".format(citation_rate))
        
        # Check structure
        structure_rate = sum(1 for r in self.results if r.get("metrics", {}).get("has_sections", False)) / len(self.results)
        if structure_rate < 0.7:
            recommendations.append("• Improve response structure and formatting (currently {:.1%})".format(structure_rate))
        
        # Check response time
        avg_latency = sum(r.get("latency", 0) for r in self.results) / len(self.results)
        if avg_latency > 5:
            recommendations.append(f"• Optimize response time (currently {avg_latency:.2f}s average)")
        
        if recommendations:
            for rec in recommendations:
                report.append(rec)
        else:
            report.append("System is performing well across all metrics!")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)
    
    def save_results(self, output_dir: str = "."):
        """Save detailed results to JSON and report to text"""
        
        output_path = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON
        json_file = output_path / f"quality_test_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"Detailed results saved: {json_file}")
        
        # Save summary report
        report = self.generate_report()
        report_file = output_path / f"quality_assessment_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Assessment report saved: {report_file}")
        
        return json_file, report_file


def main():
    """Main execution function"""
    
    # Initialize tester
    tester = ChatbotQualityTester(api_url="http://localhost:5000")
    
    # Run comprehensive tests
    tester.run_comprehensive_test()
    
    # Generate and display report
    report = tester.generate_report()
    print("\n" + report)
    
    # Save results
    tester.save_results()


if __name__ == "__main__":
    main()
