
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
import rag_config

def verify_rag_layers():
    print("="*60)
    print("VERIFYING RAG LAYERS (Small Local + Large Cloud)")
    print("="*60)
    
    print(f"Cloud Mode Enabled: {rag_config.CLOUD_MODE_ENABLED}")
    print(f"Zilliz Endpoint: {rag_config.ZILLIZ_CLUSTER_ENDPOINT[:20]}...")
    
    print("\n[1/3] Initializing System...")
    rag = UnifiedAdvancedRAG()
    
    query = "procedure for filing consumer complaint for defective goods"
    print(f"\n[2/3] Running Test Query: '{query}'")
    
    # Run retrieval only to check sources
    # accessing the internal retriever directly for inspection
    results = rag.parametric_rag.retrieve_with_params(
        query, 
        rag_params={'complexity': 'medium', 'search_domain': 'Consumer'}
    )
    
    documents = results.get('documents', [])
    
    print(f"\n[3/3] Analyzing {len(documents)} Retrieved Documents:")
    
    local_count = 0
    cloud_count = 0
    
    print(f"{'ID':<15} | {'SOURCE':<20} | {'SCORE':<10} | {'SNIPPET'}")
    print("-" * 100)
    
    for doc in documents:
        source = doc.get('source', 'unknown')
        doc_id = str(doc.get('id', 'N/A'))[:12]
        score = doc.get('score', 0)
        snippet = doc.get('text', '')[:50].replace('\n', ' ')
        
        print(f"{doc_id:<15} | {source:<20} | {score:.4f}     | {snippet}...")
        
        if 'cloud' in source.lower() or 'milvus' in source.lower():
            cloud_count += 1
        elif 'vector' in source.lower() or 'bm25' in source.lower():
            local_count += 1
            
    print("-" * 100)
    print(f"\nSUMMARY:")
    print(f"Local Documents (Small RAG): {local_count}")
    print(f"Cloud Documents (Large RAG): {cloud_count}")
    
    if local_count == 0 and cloud_count > 0:
        print("\n✅ SUCCESS: CLOUD ONLY MODE ACTIVE (User Request Satisfied)")
    elif local_count > 0 and cloud_count > 0:
        print("\n⚠️  WARNING: HYBRID MODE STILL ACTIVE (Local Docs Found)")
    elif local_count > 0:
        print("\n❌ FAILED: ONLY LOCAL ACTIVE")
    else:
        print("\n❌ FAILED: NO DOCUMENTS RETRIEVED")

if __name__ == "__main__":
    verify_rag_layers()
