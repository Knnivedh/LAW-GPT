"""Test SC Judgments search"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

print("Loading ChromaDB store...")
store = HybridChromaStore()

print(f"\nTotal documents in store: {store.count()}")

print("\n" + "="*70)
print("TESTING SC JUDGMENTS SEARCH")
print("="*70)

query = "UAPA sanction timeline validity prosecution"
print(f"\nQuery: {query}")
print("-"*70)

results = store.hybrid_search(query, n_results=5)

for i, r in enumerate(results, 1):
    meta = r.get('metadata', {})
    domain = meta.get('domain', 'unknown')
    if domain == 'supreme_court_judgments':
        print(f"\n[{i}] SC JUDGMENT FOUND!")
        print(f"    Case: {meta.get('case_name', 'N/A')}")
        print(f"    Section: {meta.get('section', 'N/A')}")
        print(f"    Priority: {meta.get('priority', 'N/A')}")
        print(f"    Date: {meta.get('judgment_date', 'N/A')}")
        print(f"    RRF Score: {r.get('rrf_score', 0):.4f}")
        text_preview = r.get('text', '')[:200].replace('\n', ' ')
        print(f"    Preview: {text_preview}...")
    else:
        print(f"\n[{i}] Other domain: {domain}")
        print(f"    Score: {r.get('rrf_score', 0):.4f}")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
