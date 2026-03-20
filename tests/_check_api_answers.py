"""Quick API check for failing questions."""
import requests
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "https://lawgpt-backend2024.azurewebsites.net"

CHECKS = [
    ("Q06 - Fundamental Rights", "What are the fundamental rights guaranteed under Part III of the Indian Constitution?"),
    ("Q15 - Three new laws", "What are the three new criminal laws that replaced the colonial-era laws in India in 2024?"),
    ("Q04 - Theft sections", "What is the punishment for theft under Indian law?"),
    ("Q16 - BNS structure", "How many chapters and sections does the Bharatiya Nyaya Sanhita have?"),
]

for label, question in CHECKS:
    print(f"\n{'='*60}")
    print(f"[{label}]")
    try:
        r = requests.post(f"{BASE_URL}/api/query",
            json={"question": question, "session_id": f"check_{label[:5]}", "user_id": "debug_check"},
            timeout=60)
        data = r.json()
        inner = data.get("response", data)
        answer = inner.get("answer", "") if isinstance(inner, dict) else str(inner)
        if not answer:
            answer = "NO ANSWER"
        conf = inner.get("confidence", 0) if isinstance(inner, dict) else 0
        print(f"Confidence: {conf}")
        print(f"Answer (first 1500 chars):")
        print(answer[:1500])
        print()
        # Check for key phrases
        al = answer.lower()
        checks = {
            "Q06": ["right to equality", "right to freedom", "right against exploitation",
                    "freedom of religion", "constitutional remedies", "equality", "freedom",
                    "exploitation", "religion"],
            "Q15": ["bharatiya nyaya sanhita", "bharatiya nagarik suraksha sanhita",
                    "bharatiya sakshya", "bns", "bnss", "bsa", "ipc"],
            "Q04": ["section 378", "section 379", "section 303", "379", "303"],
            "Q16": ["358", "20 chapters", "358 sections"],
        }
        for shortkey, phrases in checks.items():
            if shortkey.lower() in label.lower():
                print(f"KEY PHRASE HITS:")
                for p in phrases:
                    found = p.lower() in al
                    print(f"  {'[HIT]' if found else '[MISS]'} '{p}'")
    except Exception as e:
        print(f"ERROR: {e}")
