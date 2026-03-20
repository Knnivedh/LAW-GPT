"""
Adds BNS/BNSS/BSA factual documents to Zilliz Cloud (used by Azure deployment).
Mirrors the same content already added to local chroma_db_statutes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

import requests as http_requests

# ── Connection config ──────────────────────────────────────────────────────────
ENDPOINT   = "https://in03-65ed7b9f7b575b6.serverless.aws-eu-central-1.cloud.zilliz.com"
TOKEN      = os.environ.get("ZILLIZ_TOKEN",
             "ada8bb03741493623646430a71a3ce56453c4146d62e37e1376d89f0846de8b6a3"
             "cc4637c3de2884cd270225b3b991c8060c4651")
COLLECTION = "legal_rag_cloud"
NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY",
             "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")
NVIDIA_MDL = "nvidia/llama-3.2-nv-embedqa-1b-v2"

# ── Documents to inject ────────────────────────────────────────────────────────
NEW_DOCS = [
    {
        "id": "BNS_COMMDATE_001",
        "text": (
            "The Bharatiya Nyaya Sanhita, 2023 (BNS) came into force on 1 July 2024 "
            "vide S.O. 2674(E) dated 23 June 2024 issued by the Ministry of Home Affairs. "
            "The BNS replaced the Indian Penal Code, 1860 (IPC) with effect from 1 July 2024. "
            "The commencement date of the Bharatiya Nyaya Sanhita is 1st July 2024 (1-7-2024)."
        ),
        "metadata": {"source": "BNS_Commencement_Gazette", "act": "Bharatiya Nyaya Sanhita 2023",
                     "section": "Commencement", "category": "transition_law"},
    },
    {
        "id": "BNS_STRUCTURE_001",
        "text": (
            "Structure of the Bharatiya Nyaya Sanhita, 2023 (BNS): "
            "The BNS contains 20 Chapters and 358 Sections in total. "
            "It has 20 chapters covering various categories of offences and general provisions. "
            "The Bharatiya Nyaya Sanhita has 358 sections replacing the 511 sections of the IPC. "
            "Total: 20 chapters, 358 sections."
        ),
        "metadata": {"source": "BNS_Structure_Official", "act": "Bharatiya Nyaya Sanhita 2023",
                     "section": "Structure", "category": "transition_law"},
    },
    {
        "id": "THREE_NEW_LAWS_001",
        "text": (
            "India enacted three new criminal laws in 2023 replacing the colonial-era statutes, "
            "all effective from 1 July 2024: "
            "1. Bharatiya Nyaya Sanhita, 2023 (BNS) replaced the Indian Penal Code, 1860 (IPC). "
            "2. Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) replaced the Code of Criminal Procedure, 1973 (CrPC). "
            "3. Bharatiya Sakshya Adhiniyam, 2023 (BSA) replaced the Indian Evidence Act, 1872. "
            "The three laws BNS, BNSS and BSA modernise the criminal justice system. "
            "Bharatiya Nagarik Suraksha Sanhita (BNSS) governs criminal procedure. "
            "Bharatiya Sakshya Adhiniyam (BSA) governs evidence law."
        ),
        "metadata": {"source": "Three_New_Criminal_Laws_2024", "act": "BNS BNSS BSA",
                     "section": "Overview", "category": "transition_law"},
    },
    {
        "id": "BNS_NEW_OFFENCES_001",
        "text": (
            "The Bharatiya Nyaya Sanhita, 2023 (BNS) introduced 20 new offences not present in the IPC. "
            "The 20 new offences added in BNS include: organised crime, terrorism, petty organised crime, "
            "hit-and-run, snatching, murder by a group of five or more persons (mob lynching), "
            "sexual intercourse by deceit (promise to marry), and others. "
            "BNS has 20 new offences compared to the old IPC."
        ),
        "metadata": {"source": "BNS_New_Offences_Analysis", "act": "Bharatiya Nyaya Sanhita 2023",
                     "section": "New Offences", "category": "transition_law"},
    },
    {
        "id": "BNS_SEDITION_001",
        "text": (
            "Sedition under the old Indian Penal Code (IPC Section 124A) has been removed "
            "in the Bharatiya Nyaya Sanhita, 2023 (BNS). "
            "IPC Section 124A (Sedition) has been repealed and not re-enacted in BNS. "
            "Instead, BNS Section 152 covers acts endangering the sovereignty, unity and integrity of India. "
            "The word sedition has been removed from the new criminal law (BNS). "
            "Section 152 BNS protects sovereignty, unity and integrity of India."
        ),
        "metadata": {"source": "BNS_Sedition_Section152", "act": "Bharatiya Nyaya Sanhita 2023",
                     "section": "Section 152", "category": "transition_law"},
    },
    {
        "id": "BNS_RERA_001",
        "text": (
            "The Real Estate (Regulation and Development) Act, 2016 (RERA) is a central legislation "
            "that regulates the real estate sector in India. RERA established the Real Estate Regulatory Authority "
            "in each state. Key features: mandatory registration of projects above 500 sqm or 8 apartments, "
            "70% of funds to be kept in escrow account, strict timelines for project completion, "
            "grievance redressal through RERA authority and Appellate Tribunal. "
            "RERA protects homebuyers from fraudulent builders. Penalty up to 10% of project cost for violations. "
            "Section 18 RERA provides for refund and interest to homebuyers on delay."
        ),
        "metadata": {"source": "RERA_2016_Overview", "act": "Real Estate Regulation Development Act 2016",
                     "section": "Overview", "category": "property_law"},
    },
    {
        "id": "IPC_CPC_LIMITATION_001",
        "text": (
            "The Limitation Act, 1963 prescribes limitation periods for filing suits and appeals in India. "
            "Key periods: 3 years for money recovery suits, 12 years for suits related to immovable property, "
            "1 year for suits relating to torts, 90 days for appeals to High Court from decrees. "
            "Section 5 of Limitation Act allows condonation of delay for sufficient cause. "
            "Under the Consumer Protection Act 2019, the limitation period is 2 years from cause of action. "
            "The National Consumer Disputes Redressal Commission (NCDRC) has jurisdiction over disputes above Rs 10 crore. "
            "State Consumer Disputes Redressal Commission handles disputes between Rs 1 crore and Rs 10 crore."
        ),
        "metadata": {"source": "Limitation_Consumer_Law", "act": "Limitation Act 1963",
                     "section": "Limitation Periods", "category": "procedural_law"},
    },
]


def get_embeddings(texts):
    hdrs = {"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"}
    payload = {"input": texts, "model": NVIDIA_MDL, "input_type": "passage", "encoding_format": "float"}
    r = http_requests.post("https://integrate.api.nvidia.com/v1/embeddings", headers=hdrs, json=payload, timeout=60)
    r.raise_for_status()
    return [item["embedding"] for item in r.json()["data"]]


def main():
    from pymilvus import connections, Collection, utility

    print("[CONNECT] Connecting to Zilliz Cloud...")
    connections.connect(alias="default", uri=ENDPOINT, token=TOKEN)
    print("[OK] Connected")

    if not utility.has_collection(COLLECTION):
        print(f"[ERROR] Collection '{COLLECTION}' not found!")
        sys.exit(1)

    col = Collection(COLLECTION)
    col.load()
    count_before = col.num_entities
    print(f"[INFO] Collection '{COLLECTION}': {count_before} entities before injection")

    # Check which IDs already exist
    ids_to_add = [d["id"] for d in NEW_DOCS]
    existing = col.query(
        expr=f"id in {ids_to_add}",
        output_fields=["id"],
        limit=len(ids_to_add),
    )
    existing_ids = {r["id"] for r in existing}
    docs_to_add = [d for d in NEW_DOCS if d["id"] not in existing_ids]

    if not docs_to_add:
        print("[INFO] All documents already exist in Zilliz. Nothing to add.")
        return

    print(f"[INFO] Adding {len(docs_to_add)} new documents (skipping {len(existing_ids)} already present)")

    texts = [d["text"] for d in docs_to_add]
    print("[EMBED] Generating NVIDIA embeddings...")
    vectors = get_embeddings(texts)
    print(f"[OK] Got {len(vectors)} embeddings (dim={len(vectors[0])})")

    data = [
        [d["id"]      for d in docs_to_add],
        vectors,
        [d["text"]    for d in docs_to_add],
        [d["metadata"] for d in docs_to_add],
    ]
    col.upsert(data)
    col.flush()

    count_after = col.num_entities
    print(f"[OK] Upserted {len(docs_to_add)} docs. Total: {count_after}")
    print("[DONE] Zilliz BNS facts injection complete.")


if __name__ == "__main__":
    main()
