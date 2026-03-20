import sys
from pathlib import Path
import time
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the professional RAG adapter
from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

def run_comprehensive_test():
    """
    Runs a 10-question complex legal scenario audit on the RAG system.
    Evaluates:
    - Dual-store retrieval (Statutes + Judgments)
    - Legal reasoning and synthesis
    - Accuracy of 'Bare Act' citations
    """
    
    scenarios = [
        {
            "id": "SCENARIO_1",
            "category": "Consumer Protection",
            "query": "I bought a premium laptop worth Rs. 1.2 Lakh from an e-commerce site. It has a motherboard defect, and the seller refuses to replace it. Where should I file my complaint, and can I hold the e-commerce platform jointly liable under the 2019 Act?"
        },
        {
            "id": "SCENARIO_2",
            "category": "Domestic Violence (PWDVA)",
            "query": "A woman is being harassed by her husband and in-laws in their shared household. She wants to know if she has a legal right to stay in the house even if it's owned only by her father-in-law, and can she get interim custody of her 5-year-old son immediately?"
        },
        {
            "id": "SCENARIO_3",
            "category": "Insolvency (IBC)",
            "query": "An operational creditor has not been paid a debt of Rs. 1.5 Crore for 6 months. What is the procedure to initiate CIRP under the IBC 2016, and what are the recent Supreme Court views on the maintainability of such petitions?"
        },
        {
            "id": "SCENARIO_4",
            "category": "New Criminal Laws (BNS)",
            "query": "Compare the offense of 'Cruelty by husband or relatives' under the old Section 498A IPC with the corresponding provision in the new Bharatiya Nyaya Sanhita (BNS). Have any procedural requirements for filing an FIR changed?"
        },
        {
            "id": "SCENARIO_5",
            "category": "Property Law / RERA",
            "query": "A builder has delayed possession of a flat by 2 years. Can the buyer approach both the Real Estate Regulatory Authority (RERA) and the Consumer Court simultaneously, or is one forum's jurisdiction barred by the other?"
        },
        {
            "id": "SCENARIO_6",
            "category": "Corporate Law (Companies Act)",
            "query": "Under the Companies Act 2013, what is the personal liability of a director if the company fails to disclose related-party transactions in the annual financial statements? Cite relevant sections."
        },
        {
            "id": "SCENARIO_7",
            "category": "Competition Law",
            "query": "A dominant tech platform is favoring its own products in search results. Analyze this scenario under Section 4 of the Competition Act 2002 regarding 'Abuse of Dominant Position'. What are the penalties for such conduct?"
        },
        {
            "id": "SCENARIO_8",
            "category": "Evidence / BSA",
            "query": "How has the Bharatiya Sakshya Adhiniyam (BSA) changed the admissibility requirements for electronic evidence (like WhatsApp chats) compared to Section 65B of the old Indian Evidence Act?"
        },
        {
            "id": "SCENARIO_9",
            "category": "Partnership Act",
            "query": "Three partners have a dispute where one partner is siphoning off funds. Can the other partners sue him for accounts without dissolving the firm, according to the Indian Partnership Act 1932 and relevant precedents?"
        },
        {
            "id": "SCENARIO_10",
            "category": "Limitation / Civil Law",
            "query": "If a trial court passes a decree in a civil suit, what is the limitation period for filing an appeal in the High Court? Can delay be condoned if the lawyer was unwell, citing Section 5 of the Limitation Act?"
        }
    ]

    print("\n" + "="*80)
    print("STARTING COMPREHENSIVE LEGAL SYSTEM AUDIT")
    print("="*80)
    
    # Initialize the system
    try:
        rag = UnifiedAdvancedRAG()
    except Exception as e:
        import traceback
        print(f"FAILED TO INITIALIZE RAG: {e}")
        traceback.print_exc()
        return

    results = []
    
    for i, scenario in enumerate(scenarios):
        print(f"\n[TEST {i+1}/10] {scenario['category']}")
        print(f"Question: {scenario['query']}")
        
        start_time = time.time()
        try:
            # Run the RAG query
            response = rag.query(scenario['query'])
            duration = time.time() - start_time
            
            # Extract statistics for scoring if available
            source_count = len(response.get('source_documents', []))
            has_statutes = any(doc.get('metadata', {}).get('domain') == 'statutes' for doc in response.get('source_documents', []))
            
            print(f"Time Taken: {duration:.2f}s | Sources Found: {source_count} | Statute Hit: {'YES' if has_statutes else 'NO'}")
            
            # Store full record for report
            results.append({
                "scenario": scenario,
                "answer": response.get('answer', 'No Answer Found'),
                "sources": [
                    {
                        "content": doc.get('page_content', '')[:200] + "...",
                        "metadata": doc.get('metadata', {})
                    } for doc in response.get('source_documents', [])
                ],
                "reasoning": response.get('reasoning_path', 'N/A'),
                "metadata": {
                    "duration": duration,
                    "statute_hit": has_statutes
                }
            })
            
        except Exception as e:
            import traceback
            print(f"ERROR DURING QUERY: {e}")
            traceback.print_exc()
            results.append({
                "scenario": scenario,
                "error": str(e)
            })

    # Save results to a file for review
    report_file = Path("evaluation_results.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("\n" + "="*80)
    print(f"DONE. RESULTS SAVED TO: {report_file}")
    print("="*80)

if __name__ == "__main__":
    run_comprehensive_test()
