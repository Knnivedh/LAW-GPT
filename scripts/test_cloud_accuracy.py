"""
CLOUD RAG ACCURACY TEST SUITE
Benchmarks the UnifiedAdvancedRAG system using live Zilliz Cloud data.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

class CloudAccuracyTester:
    def __init__(self):
        print("\n" + "="*60)
        print("🤖 INITIALIZING CLOUD RAG ACCURACY TESTER")
        print("="*60)
        self.rag = UnifiedAdvancedRAG()
        self.results = []
        
    def run_scenario(self, category: str, query: str, expected_keywords: List[str]):
        print(f"\n[TEST] Category: {category}")
        print(f"Query: {query}")
        
        start_time = time.time()
        try:
            response = self.rag.query(query, category=category)
            latency = time.time() - start_time
            
            answer = response.get('answer', '')
            docs = response.get('source_documents', [])
            
            # Basic validation
            has_sources = len(docs) > 0
            mentions_keywords = any(kw.lower() in answer.lower() for kw in expected_keywords)
            
            status = "✅ PASS" if has_sources and mentions_keywords else "⚠️ PARTIAL"
            if not has_sources: status = "❌ FAIL (No Sources)"
            
            print(f"Status: {status}")
            print(f"Latency: {latency:.2f}s")
            print(f"Sources Found: {len(docs)}")
            print(f"Answer Snippet: {answer[:150]}...")
            
            self.results.append({
                "category": category,
                "query": query,
                "status": status,
                "latency": latency,
                "num_sources": len(docs),
                "mentions_keywords": mentions_keywords,
                "answer": answer
            })
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            self.results.append({
                "category": category,
                "query": query,
                "status": "❌ ERROR",
                "error": str(e)
            })

    def run_full_suite(self):
        scenarios = [
            {
                "category": "Statutes",
                "query": "What does Section 47 of the Trade Marks Act 1999 say about removal from register?",
                "keywords": ["removal", "register", "non-use", "trademark"]
            },
            {
                "category": "Consumer",
                "query": "What is the liability of a hospital in case of medical negligence according to NCDRC?",
                "keywords": ["negligence", "liability", "compensation", "deficiency"]
            },
            {
                "category": "General",
                "query": "Can a power of attorney be used as a title document for selling property according to the Supreme Court?",
                "keywords": ["Supreme Court", "title", "POB", "registered sale deed"]
            },
            {
                "category": "Criminal",
                "query": "Explain the concept of 'Associate of People's Liberation Front of India' from legal context.",
                "keywords": ["Associate", "PLFI", "unlawful"]
            }
        ]
        
        for scene in scenarios:
            self.run_scenario(scene["category"], scene["query"], scene["keywords"])
            
        self.save_report()

    def save_report(self):
        report_path = PROJECT_ROOT / "cloud_accuracy_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=4)
        
        print("\n" + "="*60)
        print(f"📊 ACCURACY REPORT SAVED: {report_path}")
        
        passed = sum(1 for r in self.results if r["status"] == "✅ PASS")
        total = len(self.results)
        print(f"Final Score: {passed}/{total} ({(passed/total)*100:.1f}%)")
        print("="*60 + "\n")

if __name__ == "__main__":
    tester = CloudAccuracyTester()
    tester.run_full_suite()
