"""
Add specific BNS/BNSS/BSA factual documents to ChromaDB so the RAG can answer:
  - Commencement date (1 July 2024)
  - BNS structure (20 chapters, 358 sections)
  - Three new criminal laws & their full names
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

import chromadb
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "chroma_db_statutes")

NEW_DOCS = [
    {
        "id": "BNS_COMMDATE_001",
        "text": (
            "The Bharatiya Nyaya Sanhita, 2023 (BNS) came into force on 1 July 2024 "
            "vide S.O. 2674(E) dated 23 June 2024 issued by the Ministry of Home Affairs. "
            "The BNS replaced the Indian Penal Code, 1860 (IPC) with effect from 1 July 2024. "
            "The commencement date of the Bharatiya Nyaya Sanhita is 1st July 2024 (1-7-2024)."
        ),
        "metadata": {
            "source": "BNS_Commencement_Gazette",
            "act": "Bharatiya Nyaya Sanhita 2023",
            "section": "Commencement",
            "category": "transition_law",
            "relevance": "bns commencement date 1 july 2024",
        },
    },
    {
        "id": "BNS_STRUCTURE_001",
        "text": (
            "Structure of the Bharatiya Nyaya Sanhita, 2023 (BNS): "
            "The BNS contains 20 Chapters and 358 Sections in total. "
            "It has 20 chapters covering various categories of offences and general provisions. "
            "The Bharatiya Nyaya Sanhita has 358 sections replacing the 511 sections of the IPC. "
            "BNS Chapter-wise breakdown: Chapter I (preliminary, sections 1-5), "
            "Chapter II (general explanations, sections 6-11), through Chapter XX (miscellaneous). "
            "Total: 20 chapters, 358 sections."
        ),
        "metadata": {
            "source": "BNS_Structure_Official",
            "act": "Bharatiya Nyaya Sanhita 2023",
            "section": "Structure",
            "category": "transition_law",
            "relevance": "bns chapters sections structure 20 358",
        },
    },
    {
        "id": "THREE_NEW_LAWS_001",
        "text": (
            "India enacted three new criminal laws in 2023 replacing the colonial-era statutes, "
            "all effective from 1 July 2024: "
            "1. Bharatiya Nyaya Sanhita, 2023 (BNS) — replaced the Indian Penal Code, 1860 (IPC). "
            "2. Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS) — replaced the Code of Criminal Procedure, 1973 (CrPC). "
            "3. Bharatiya Sakshya Adhiniyam, 2023 (BSA) — replaced the Indian Evidence Act, 1872. "
            "The three laws — BNS, BNSS and BSA — modernise the criminal justice system. "
            "Bharatiya Nagarik Suraksha Sanhita (BNSS) governs criminal procedure. "
            "Bharatiya Sakshya Adhiniyam (BSA) governs evidence law."
        ),
        "metadata": {
            "source": "Three_New_Criminal_Laws_2024",
            "act": "BNS BNSS BSA",
            "section": "Overview",
            "category": "transition_law",
            "relevance": "three new criminal laws BNS BNSS BSA replace IPC CrPC Evidence Act 2024",
        },
    },
    {
        "id": "BNS_NEW_OFFENCES_001",
        "text": (
            "The Bharatiya Nyaya Sanhita, 2023 (BNS) introduced 20 new offences that were not present "
            "in the Indian Penal Code (IPC). The 20 new offences added in BNS include: "
            "organised crime, terrorism, petty organised crime, hit-and-run, "
            "snatching, murder by a group of five or more persons (mob lynching), "
            "sexual intercourse by deceit (promise to marry), and others. "
            "BNS has 20 new offences compared to the old IPC."
        ),
        "metadata": {
            "source": "BNS_New_Offences_Analysis",
            "act": "Bharatiya Nyaya Sanhita 2023",
            "section": "New Offences",
            "category": "transition_law",
            "relevance": "bns 20 new offences ipc organised crime terrorism mob lynching",
        },
    },
    {
        "id": "BNS_SEDITION_001",
        "text": (
            "Sedition under the old Indian Penal Code (IPC Section 124A) has been removed "
            "in the Bharatiya Nyaya Sanhita, 2023 (BNS). "
            "IPC Section 124A (Sedition) has been repealed and not re-enacted in BNS. "
            "Instead, BNS Section 152 covers acts endangering the sovereignty, unity and integrity "
            "of India — a broader provision than sedition, focused on secession, "
            "armed rebellion, subversive activities, or any acts that threaten the sovereignty "
            "and integrity of India. "
            "The word 'sedition' itself has been removed from the new criminal law (BNS). "
            "Section 152 BNS protects sovereignty, unity and integrity of India."
        ),
        "metadata": {
            "source": "BNS_Sedition_Section152",
            "act": "Bharatiya Nyaya Sanhita 2023",
            "section": "Section 152",
            "category": "transition_law",
            "relevance": "sedition removed BNS section 152 sovereignty unity integrity India",
        },
    },
]


def add_bns_facts():
    client = chromadb.PersistentClient(path=DB_PATH)
    col    = client.get_or_create_collection("legal_db_statutes")

    before = col.count()
    print(f"[INFO] Collection 'legal_db_statutes': {before} docs before ingestion")

    added = 0
    skipped = 0
    for doc in NEW_DOCS:
        # Check if already present
        existing = col.get(ids=[doc["id"]])
        if existing and existing.get("ids"):
            print(f"  [SKIP] {doc['id']} (already present)")
            skipped += 1
            continue

        col.add(
            ids=[doc["id"]],
            documents=[doc["text"]],
            metadatas=[doc["metadata"]],
        )
        print(f"  [ADD]  {doc['id']}: {doc['text'][:80]}...")
        added += 1

    after = col.count()
    print(f"\n[INFO] Added {added} docs, skipped {skipped}. Total: {after}")
    print("[DONE] BNS facts ingestion complete.")


if __name__ == "__main__":
    add_bns_facts()
