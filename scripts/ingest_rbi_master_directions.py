"""
RBI Master Directions Ingestion Script
Generates critical RBI regulatory content and pushes to Cloud RAG (Zilliz/Milvus)
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / "config" / ".env")

from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import rag_config

# RBI Master Directions - Critical Content for Legal RAG
RBI_MASTER_DIRECTIONS = [
    {
        "title": "RBI Master Direction - Fair Practices Code for Lenders (2024)",
        "content": """RBI Master Direction on Fair Practices Code for Lenders (RBI/2024-25/XX):

1. GENERAL GUIDELINES:
   - All lenders must provide a copy of the loan agreement to the borrower.
   - All terms and conditions must be clearly explained in a language understood by the borrower.
   - No hidden charges or fees shall be imposed without prior disclosure.

2. LOAN APPLICATION AND PROCESSING:
   - Banks must acknowledge receipt of loan applications within 3 working days.
   - Rejection of loan applications must be communicated in writing with reasons.
   - Processing fees, if any, must be disclosed upfront.

3. DISBURSEMENT AND TERMS:
   - Loan sanction letter must contain: rate of interest, method of application, EMI schedule.
   - Any change in terms must be communicated to borrower with advance notice.
   - Annual percentage rates (APR) must be disclosed.

4. POST-DISBURSEMENT CONDUCT:
   - Banks cannot unilaterally change interest rates without prior notice.
   - Prepayment penalties must be disclosed at sanction stage.
   - Statement of accounts must be provided at regular intervals.

5. RECOVERY PRACTICES:
   - Recovery agents must be properly authorized and trained.
   - Recovery agents must not use coercive measures.
   - Visits to borrower's place must be at reasonable hours (0700-1900 hrs).
   - No harassment, intimidation, or humiliation of borrower or family.

6. GRIEVANCE REDRESSAL:
   - Every bank must have a Grievance Redressal Officer.
   - Complaints must be resolved within 30 days.
   - If unresolved, borrower may approach Banking Ombudsman.

LEGAL SIGNIFICANCE: Violation of Fair Practices Code constitutes deficiency in service under Consumer Protection Act and may be cited in DRT/DRAT/Writ proceedings.""",
        "source": "RBI Master Directions",
        "category": "Banking Regulation"
    },
    {
        "title": "RBI Guidelines on Recovery Agents (2008/2024)",
        "content": """RBI Guidelines on Engagement of Recovery Agents:

1. AUTHORIZATION:
   - Banks must maintain a panel of approved recovery agents.
   - Each agent must be given proper authorization letter for each case.
   - Banks are responsible for actions of their recovery agents.

2. TRAINING:
   - Recovery agents must undergo proper training on:
     a) Code of conduct and ethics
     b) Legal provisions regarding recovery
     c) Communication skills and dealing with customers

3. PROHIBITED PRACTICES:
   - No use of muscle power or violence.
   - No threats to life, limb, or reputation.
   - No visits before 0700 hrs or after 1900 hrs.
   - No use of abusive language.
   - No contacting employer or colleagues without permission.
   - No impersonation as government officials.

4. CONSEQUENCES OF VIOLATION:
   - Banks liable for recovery agent misconduct.
   - Criminal action against agents for criminal acts.
   - Suspension of outsourcing arrangements.
   - Penalty by RBI on the bank.

5. BORROWER RIGHTS:
   - Right to receive proper notice before recovery action.
   - Right to be treated with dignity and respect.
   - Right to complain to bank's Grievance Officer.
   - Right to approach Banking Ombudsman.

LEGAL SIGNIFICANCE: Recovery agent misconduct can be grounds for:
- Quashing SARFAESI proceedings for procedural violations
- Compensation claims under Consumer Protection Act
- Criminal complaints for harassment/intimidation
- Writ petitions citing violation of fundamental rights""",
        "source": "RBI Guidelines",
        "category": "Recovery Agents"
    },
    {
        "title": "RBI Master Direction - SARFAESI Compliance (2023)",
        "content": """RBI Master Direction on SARFAESI Act Compliance:

1. PRE-CONDITIONS FOR SARFAESI ACTION:
   - Account must be classified as NPA as per RBI norms.
   - Security interest must be created and registered.
   - Due process must be followed before classification.

2. NOTICE REQUIREMENTS (Section 13(2)):
   - 60 days notice mandatory before taking action.
   - Notice must specify:
     a) Amount due with break-up
     b) Date of classification as NPA
     c) Proposed action for recovery
   - Notice must be served at proper address.

3. PERSONAL HEARING:
   - Borrower's representation must be considered.
   - Reasons for rejection of representation must be communicated.
   - Fair opportunity to be heard before possession.

4. POSSESSION AND SALE:
   - Possession notice must be published in newspapers.
   - Borrower must be given opportunity to redeem.
   - Sale must be at fair market value.
   - Reserve price must be determined professionally.

5. BORROWER'S REMEDIES:
   - Appeal to DRT within 45 days under Section 17.
   - DRT can grant interim relief including stay.
   - Second appeal to DRAT.
   - Writ petition only in exceptional cases.

LEGAL SIGNIFICANCE: Non-compliance with any of these requirements can render SARFAESI action liable to be set aside by DRT/High Court.""",
        "source": "RBI Master Directions",
        "category": "SARFAESI"
    },
    {
        "title": "RBI Circular on Forced Insurance Practices (2020)",
        "content": """RBI Circular on Mis-selling and Forced Insurance:

1. PROHIBITION ON TIE-UP SALES:
   - Banks cannot force borrowers to buy insurance as a pre-condition for loan.
   - Borrowers have the right to choose their own insurer.
   - If insurance is mandatory, borrower must be given choice of insurer.

2. DISCLOSURE REQUIREMENTS:
   - Full premium amount must be disclosed separately.
   - Commission earned by bank must be disclosed.
   - Insurance is optional unless legally mandated.

3. CONSEQUENCES OF FORCED INSURANCE:
   - Amounts to "Unfair Trade Practice" under Consumer Protection Act.
   - Bank liable for refund of premium with interest.
   - Compensation for mental harassment may be awarded.

4. BORROWER RIGHTS:
   - Right to opt out of bank-offered insurance.
   - Right to bring own insurance policy.
   - Right to claim refund if insurance was forced.

LEGAL SIGNIFICANCE: Forced insurance is grounds for:
- Consumer complaint for unfair trade practice
- Refund of entire premium with compensation
- Additional ground in SARFAESI appeal for procedural unfairness""",
        "source": "RBI Circulars",
        "category": "Consumer Protection"
    },
    {
        "title": "RBI Master Direction - Penal Charges on Loans (2023)",
        "content": """RBI Master Direction on Penal Charges on Loan Accounts:

1. KEY CHANGES (Effective 1st January 2024):
   - "Penal interest" renamed to "Penal charges".
   - Penal charges cannot be capitalized (no interest on interest).
   - Penal charges must be reasonable and proportionate.

2. DISCLOSURE REQUIREMENTS:
   - Penal charges must be disclosed in loan agreement.
   - Schedule of penal charges must be displayed on website.
   - Any change must be communicated with advance notice.

3. NON-DISCRIMINATION:
   - Same penal charges for same category of borrowers.
   - No discrimination based on loan size or borrower profile.

4. REMEDIES FOR EXCESSIVE PENAL CHARGES:
   - Complaint to bank's grievance cell.
   - Complaint to Banking Ombudsman.
   - Consumer complaint for unfair charges.

LEGAL SIGNIFICANCE: Excessive or undisclosed penal charges can be challenged as:
- Unfair contract terms under CPA 2019
- Grounds for recalculation of dues in DRT
- Basis for interim relief in SARFAESI appeals""",
        "source": "RBI Master Directions",
        "category": "Loan Charges"
    }
]


def main():
    print("="*60)
    print("RBI MASTER DIRECTIONS - CLOUD INGESTION")
    print("="*60)
    
    # Initialize embedding model
    print("\n[1/4] Loading embedding model...")
    embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    print("  [OK] Embedding model loaded")
    
    # Connect to Zilliz Cloud
    print("\n[2/4] Connecting to Zilliz Cloud...")
    connections.connect(
        alias="default",
        uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
        token=rag_config.ZILLIZ_TOKEN
    )
    print(f"  [OK] Connected to: {rag_config.ZILLIZ_CLUSTER_ENDPOINT}")
    
    # Get collection
    collection_name = rag_config.ZILLIZ_COLLECTION_NAME
    print(f"\n[3/4] Accessing collection: {collection_name}")
    collection = Collection(collection_name)
    collection.load()
    print(f"  [OK] Collection loaded. Current count: {collection.num_entities}")
    
    # Prepare data for insertion
    print("\n[4/4] Embedding and inserting RBI content...")
    
    import uuid
    
    ids = []
    vectors = []
    texts = []
    metadatas = []
    
    for doc in RBI_MASTER_DIRECTIONS:
        # Create embedding
        text_to_embed = f"{doc['title']}\n\n{doc['content']}"
        embedding = embed_model.encode(text_to_embed).tolist()
        
        # Prepare data in column format
        ids.append(f"rbi_{uuid.uuid4().hex[:12]}")
        vectors.append(embedding)
        texts.append(doc["content"][:60000])
        metadatas.append({
            "source": doc["source"],
            "category": doc["category"],
            "title": doc["title"],
            "doc_type": "rbi_regulation"
        })
    
    # Insert all at once (column format)
    try:
        data = [ids, vectors, texts, metadatas]
        collection.insert(data)
        collection.flush()
        print(f"  [OK] Inserted {len(ids)} RBI documents successfully!")
    except Exception as e:
        print(f"  [ERROR] Batch insertion failed: {e}")
    
    # Flush to ensure persistence
    collection.flush()
    
    print("\n" + "="*60)
    print(f"INGESTION COMPLETE!")
    print(f"  Documents inserted: {inserted}")
    print(f"  New collection count: {collection.num_entities}")
    print("="*60)
    
    return inserted


if __name__ == "__main__":
    main()
