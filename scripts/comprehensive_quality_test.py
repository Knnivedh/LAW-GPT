import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:7860/api/query"

# Comprehensive Test Suite
TEST_QUERIES = [
    {
        "question": "What is IPC Section 302?",
        "category": "Criminal Law",
        "expected_keywords": ["murder", "302", "punishment", "death"],
        "complexity": "simple"
    },
    {
        "question": "Explain Article 21 of the Indian Constitution",
        "category": "Constitutional Law",
        "expected_keywords": ["life", "liberty", "personal", "fundamental"],
        "complexity": "medium"
    },
    {
        "question": "What are the essential elements of a valid contract?",
        "category": "Contract Law",
        "expected_keywords": ["offer", "acceptance", "consideration", "capacity"],
        "complexity": "medium"
    },
    {
        "question": "Explain the concept of adverse possession under property law",
        "category": "Property Law",
        "expected_keywords": ["possession", "title", "limitation", "12 years"],
        "complexity": "complex"
    },
    {
        "question": "What is the difference between IPC 304 and 304A?",
        "category": "Criminal Law",
        "expected_keywords": ["culpable homicide", "negligence", "intention"],
        "complexity": "complex"
    }
]

def analyze_response_quality(question, answer, expected_keywords, sources):
    """Analyze the quality of a response"""
    score = 0
    issues = []
    
    # Check 1: Non-empty response
    if not answer or len(answer.strip()) < 50:
        issues.append("Response too short or empty")
        return 0, issues
    
    score += 20  # Base score for having a response
    
    # Check 2: Keyword relevance
    keywords_found = sum(1 for kw in expected_keywords if kw.lower() in answer.lower())
    keyword_score = (keywords_found / len(expected_keywords)) * 30
    score += keyword_score
    
    if keyword_score < 15:
        issues.append(f"Low keyword relevance ({keywords_found}/{len(expected_keywords)} keywords found)")
    
    # Check 3: Source retrieval
    if sources and len(sources) > 0:
        score += 25
    else:
        issues.append("No sources retrieved from RAG")
    
    # Check 4: Response length (ideal: 200-1000 chars for quality)
    length = len(answer)
    if 200 <= length <= 1500:
        score += 15
    elif length < 200:
        issues.append(f"Response too brief ({length} chars)")
        score += 5
    else:
        score += 10  # Very long is okay but not ideal
    
    # Check 5: Professional formatting (paragraphs, structure)
    if '\n' in answer or '.' in answer:
        score += 10
    else:
        issues.append("Poor formatting - no paragraphs or sentences")
    
    return score, issues

def run_comprehensive_test():
    print("=" * 70)
    print("🧪 COMPREHENSIVE BACKEND QUALITY TEST")
    print("=" * 70)
    print(f"Testing API: {API_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Test Cases: {len(TEST_QUERIES)}\n")
    
    results = []
    total_score = 0
    all_issues = []
    
    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'─' * 70}")
        print(f"Test {i}/{len(TEST_QUERIES)}: {test['complexity'].upper()} Query")
        print(f"Question: {test['question']}")
        print(f"Category: {test['category']}")
        
        # Make API call
        start_time = time.time()
        try:
            response = requests.post(
                API_URL,
                json={
                    "question": test['question'],
                    "category": test['category']
                },
                timeout=60
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                
                # Analyze quality
                score, issues = analyze_response_quality(
                    test['question'],
                    answer,
                    test['expected_keywords'],
                    sources
                )
                
                # Display results
                print(f"\n⏱️  Response Time: {duration:.2f}s")
                print(f"📊 Quality Score: {score}/100")
                
                if score >= 80:
                    print(f"✅ Status: EXCELLENT")
                elif score >= 60:
                    print(f"⚠️  Status: ACCEPTABLE")
                else:
                    print(f"❌ Status: POOR")
                
                print(f"📝 Answer Length: {len(answer)} characters")
                print(f"📚 Sources Retrieved: {len(sources)}")
                
                if issues:
                    print(f"\n⚠️  Issues Found:")
                    for issue in issues:
                        print(f"   - {issue}")
                        all_issues.append(f"Test {i}: {issue}")
                
                # Show snippet of answer
                snippet = answer[:200] + "..." if len(answer) > 200 else answer
                print(f"\n📄 Answer Preview:\n{snippet}")
                
                results.append({
                    "test_num": i,
                    "question": test['question'],
                    "score": score,
                    "duration": duration,
                    "answer_length": len(answer),
                    "sources_count": len(sources),
                    "issues": issues
                })
                
                total_score += score
                
            else:
                print(f"❌ API Error: {response.status_code}")
                all_issues.append(f"Test {i}: API returned {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Request Timeout (> 60s)")
            all_issues.append(f"Test {i}: Response timeout")
        except Exception as e:
            print(f"❌ Error: {e}")
            all_issues.append(f"Test {i}: {str(e)}")
    
    # Final Report
    print(f"\n\n{'=' * 70}")
    print("📊 FINAL QUALITY REPORT")
    print(f"{'=' * 70}")
    
    avg_score = total_score / len(TEST_QUERIES) if TEST_QUERIES else 0
    print(f"\n🎯 Overall Quality Score: {avg_score:.1f}/100")
    
    if avg_score >= 80:
        print(f"✅ Status: PRODUCTION READY")
    elif avg_score >= 60:
        print(f"⚠️  Status: NEEDS MINOR IMPROVEMENTS")
    else:
        print(f"❌ Status: NEEDS MAJOR FIXES")
    
    print(f"\n📈 Statistics:")
    print(f"   - Tests Passed (>60): {sum(1 for r in results if r['score'] >= 60)}/{len(results)}")
    print(f"   - Average Response Time: {sum(r['duration'] for r in results)/len(results):.2f}s")
    print(f"   - Total Issues Found: {len(all_issues)}")
    
    if all_issues:
        print(f"\n⚠️  ALL ISSUES SUMMARY:")
        for issue in all_issues:
            print(f"   - {issue}")
    
    # Save detailed report
    report_file = f"quality_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "overall_score": avg_score,
            "results": results,
            "issues": all_issues
        }, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    print(f"\n{'=' * 70}\n")
    
    return avg_score, all_issues

if __name__ == "__main__":
    run_comprehensive_test()
