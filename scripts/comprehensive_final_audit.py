import sys
from pathlib import Path
import json
import time
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force ASCII logging to avoid UnicodeEncodeError in terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG

SCENARIOS = [
    {
        "id": "SCENARIO_1_CONSTITUTIONAL_MEDIA",
        "domain": "Constitutional + Criminal + Media Trial",
        "query": """A journalist publishes leaked WhatsApp chats of a sitting High Court judge allegedly coordinating with a senior police officer to influence the outcome of a politically sensitive criminal trial. The chats were obtained by hacking the judge's personal phone by an anonymous source. 
        After publication: 1. The judge files a contempt of court petition. 2. The police register an FIR against the journalist under the IT Act and IPC. 3. A PIL is filed seeking the judge's impeachment and a CBI probe.
        
        Analyze: 
        1. Conflict between Article 19(1)(a) and contempt of court.
        2. Can illegally obtained evidence be published in public interest?
        3. Is impeachment the correct constitutional remedy?
        4. Can the journalist claim protection as a whistleblower?
        5. Is prior restraint on media justified here?"""
    },
    {
        "id": "SCENARIO_2_CONTRACT_CORPORATE_IBC",
        "domain": "Contract + Corporate + Insolvency",
        "query": """A startup enters into a Shareholders' Agreement (SHA) with a foreign VC fund. The SHA contains: A non-compete clause for 5 years post-exit, Arbitration seated in Singapore, Liquidated damages clause worth Rs. 50 crore. 
        The startup later: Goes into CIRP under IBC, Promoters start a similar business, The VC invokes arbitration and claims damages.
        
        Analyze: 
        1. Is the non-compete clause enforceable under Section 27 of the Contract Act?
        2. Does IBC override the arbitration clause?
        3. Can liquidated damages be enforced during moratorium?
        4. Can promoters be restrained during CIRP?
        5. Which law prevails: IBC or Arbitration Act?"""
    },
    {
        "id": "SCENARIO_3_CRIMINAL_GENDER_EVIDENCE",
        "domain": "Criminal Law + Gender Law + Evidence",
        "query": """A married woman dies by suicide within 3 years of marriage. Her suicide note accuses: Husband of emotional abuse, Mother-in-law of constant taunts, Employer of workplace harassment. 
        The husband claims: The suicide note is forged, The woman was under depression, No physical cruelty ever occurred.
        
        Analyze:
        1. Can Section 498A IPC and Section 306 IPC both apply?
        2. What is the evidentiary value of a suicide note?
        3. How does presumption under Section 113A Evidence Act operate?
        4. Can employer be prosecuted under criminal law?
        5. Is mental cruelty alone sufficient for conviction?"""
    },
    {
        "id": "SCENARIO_4_CYBER_PRIVACY_SECURITY",
        "domain": "Cyber Law + Privacy + National Security",
        "query": """A government agency uses AI-based facial recognition software at airports without any specific legislation backing it. A citizen is wrongfully detained due to false match, his biometric data is stored indefinitely, and data later leaks online. The government argues national security.
        
        Analyze:
        1. Does this violate Article 21 (Right to Privacy)?
        2. Is executive action sufficient without legislation?
        3. Apply the Puttaswamy proportionality test.
        4. Who is liable for the data breach?
        5. Can damages be claimed against the State?"""
    },
    {
        "id": "SCENARIO_5_PROPERTY_FAMILY_CONSTITUTIONAL",
        "domain": "Property + Family Law + Constitutional Challenge",
        "query": """A Hindu man dies intestate leaving behind: A self-acquired property, Two daughters, One son, A second wife from a live-in relationship (not legally married). The second woman claims: Maintenance, Share in property, Protection under Article 14.
        
        Analyze:
        1. Are daughters entitled to equal share?
        2. Does a live-in partner have inheritance rights?
        3. Can Article 14 override personal law?
        4. Applicability of Protection of Women from Domestic Violence Act.
        5. Can courts read constitutional morality into succession law?"""
    }
]

def run_comprehensive_audit():
    print("="*80)
    print("      LAW-GPT COMPREHENSIVE MULTI-DOMAIN LEGAL AUDIT (5 SCENARIOS)")
    print("="*80)
    
    try:
        rag = UnifiedAdvancedRAG()
        print("\n[OK] RAG System Initialized.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to initialize RAG: {e}")
        import traceback
        traceback.print_exc()
        return

    results = []
    
    for i, scenario in enumerate(SCENARIOS):
        print(f"\n[{i+1}/5] Processing Scenario: {scenario['domain']}")
        print(f"Query: {scenario['query'][:100]}...")
        
        start_time = time.time()
        try:
            output = rag.query(scenario['query'])
            duration = time.time() - start_time
            
            result_item = {
                "scenario_id": scenario['id'],
                "domain": scenario['domain'],
                "query": scenario['query'],
                "answer": output.get('answer'),
                "reasoning_path": output.get('reasoning_path'),
                "source_documents": output.get('source_documents', []),
                "metadata": output.get('metadata', {}),
                "duration": duration
            }
            results.append(result_item)
            
            print(f"      Status: SUCCESS (Time: {duration:.2f}s)")
            print(f"      Sources Found: {len(output.get('source_documents', []))}")
            
        except Exception as e:
            print(f"      Status: FAILED | Error: {e}")
            results.append({
                "scenario_id": scenario['id'],
                "query": scenario['query'],
                "error": str(e)
            })

    # Save final results
    output_path = "comprehensive_audit_results.json"
    print(f"\n[FINISHED] Saving all results to {output_path}...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("="*80)
    print("AUDIT EXECUTION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    run_comprehensive_audit()
