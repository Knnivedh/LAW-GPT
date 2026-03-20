"""Test web search functionality"""
import sys
sys.path.insert(0, 'kaanoon_test')

from system_adapters.rag_system_adapter_ULTIMATE import SimpleWebSearchClient

# Create client and test
client = SimpleWebSearchClient()
print("Testing web search...")
print("-" * 60)

# Test search
results = client.search_duckduckgo('latest news India', max_results=3)
print(f"\nResults: {len(results)} found")
print("-" * 60)

for i, r in enumerate(results, 1):
    print(f"\n{i}. {r.get('title', 'N/A')}")
    print(f"   URL: {r.get('url', 'N/A')}")
    snippet = r.get('snippet', 'N/A')
    print(f"   Snippet: {snippet[:100]}...")
    print()

print("=" * 60)
print("Test completed!")
