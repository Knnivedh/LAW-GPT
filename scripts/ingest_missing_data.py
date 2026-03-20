import sys
import json
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_system.core.hybrid_chroma_store import HybridChromaStore

def ingest_constitution():
    """Ingest Constitution of India"""
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_path = Path("DATA/statutory/constitution_of_india.json")
    
    print(f"\n=== INGESTING: Constitution of India ===")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs_to_add = []
    
    # Handle different possible structures
    if isinstance(data, dict):
        # If it has 'articles' or 'parts'
        if 'articles' in data:
            for article in data['articles']:
                doc_id = f"const_art_{article.get('number', len(docs_to_add))}"
                text = f"CONSTITUTION OF INDIA\n\nArticle {article.get('number')}: {article.get('title', '')}\n\n{article.get('text', article.get('content', ''))}"
                metadata = {
                    'source': 'Constitution of India',
                    'type': 'constitution',
                    'article': str(article.get('number', '')),
                    'title': article.get('title', '')
                }
                docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
        elif 'parts' in data:
            for part in data['parts']:
                doc_id = f"const_part_{len(docs_to_add)}"
                text = f"CONSTITUTION OF INDIA\n\nPart {part.get('number')}: {part.get('title', '')}\n\n{part.get('text', part.get('content', ''))}"
                metadata = {
                    'source': 'Constitution of India',
                    'type': 'constitution',
                    'part': str(part.get('number', '')),
                    'title': part.get('title', '')
                }
                docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
        else:
            # Treat whole file as one document
            doc_id = "const_full"
            text = json.dumps(data, indent=2)
            metadata = {
                'source': 'Constitution of India',
                'type': 'constitution'
            }
            docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
    
    if docs_to_add:
        store.add_documents(docs_to_add, batch_size=50)
        print(f"DONE: Ingested {len(docs_to_add)} Constitution documents")
    
def ingest_case_law_collection(filename):
    """Ingest case law collections (property, criminal, constitutional)"""
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_path = Path(f"DATA/data_collection/case_law/{filename}")
    
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        return
    
    print(f"\n=== INGESTING: {filename} ===")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs_to_add = []
    cases = data.get('cases', [])
    domain = data.get('domain', filename.replace('_cases.json', '').replace('_', ' ').title())
    
    for case in cases:
        case_id = case.get('case_id', f"case_{len(docs_to_add)}")
        doc_id = f"{domain.lower().replace(' ', '_')}_{case_id}"
        
        # Build comprehensive text
        text = f"CASE: {case.get('case_name')}\n"
        text += f"CITATION: {case.get('citation')}\n"
        text += f"COURT: {case.get('court')}\n"
        text += f"YEAR: {case.get('year')}\n"
        text += f"CATEGORY: {case.get('category', domain)}\n\n"
        text += f"FACTS: {case.get('facts', '')}\n\n"
        text += f"ISSUES: {', '.join(case.get('issues', []))}\n\n"
        text += f"HELD: {case.get('held', '')}\n\n"
        text += f"JUDGMENT: {case.get('judgment', '')}\n\n"
        text += f"KEY PRINCIPLES: {', '.join(case.get('key_principles', []))}\n\n"
        text += f"SIGNIFICANCE: {case.get('significance', '')}"
        
        metadata = {
            'source': f'{domain} Cases',
            'type': 'case_law',
            'case_name': case.get('case_name'),
            'court': case.get('court'),
            'year': str(case.get('year', '')),
            'citation': case.get('citation', ''),
            'category': case.get('category', domain),
            'is_landmark': str(case.get('is_landmark', True))
        }
        
        docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
    
    if docs_to_add:
        store.add_documents(docs_to_add, batch_size=20)
        print(f"DONE: Ingested {len(docs_to_add)} {domain} cases")

def ingest_legal_domain(filename):
    """Ingest legal domain documents (tax, labour, IP, cyber)"""
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_path = Path(f"DATA/data_collection/legal_domains/{filename}")
    
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        return
    
    print(f"\n=== INGESTING: {filename} ===")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs_to_add = []
    documents = data.get('documents', [])
    domain_name = data.get('domain_name', filename.replace('.json', '').replace('_', ' ').title())
    
    for doc in documents:
        doc_id = doc.get('doc_id', f"domain_{len(docs_to_add)}")
        
        text = f"DOMAIN: {domain_name}\n"
        text += f"TITLE: {doc.get('title')}\n\n"
        text += doc.get('content', '')
        
        metadata = doc.get('metadata', {}).copy()
        metadata.update({
            'source': domain_name,
            'type': 'legal_domain',
            'title': doc.get('title')
        })
        
        docs_to_add.append({'id': f"{domain_name.lower().replace(' ', '_')}_{doc_id}", 'text': text, 'metadata': metadata})
    
    if docs_to_add:
        store.add_documents(docs_to_add, batch_size=10)
        print(f"DONE: Ingested {len(docs_to_add)} {domain_name} documents")

def ingest_landmark_expansion():
    """Ingest landmark_legal_cases_expansion.json"""
    store = HybridChromaStore(persist_directory="chroma_db_hybrid", collection_name="legal_db_hybrid")
    json_path = Path("DATA/landmark_legal_cases_expansion.json")
    
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        return
    
    print(f"\n=== INGESTING: landmark_legal_cases_expansion.json ===")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs_to_add = []
    
    # Handle different possible structures
    if isinstance(data, list):
        cases = data
    elif isinstance(data, dict) and 'cases' in data:
        cases = data['cases']
    else:
        cases = [data]
    
    for i, case in enumerate(cases):
        doc_id = f"landmark_exp_{i}"
        
        # Build text from case data
        text = f"LANDMARK CASE (Expansion Collection)\n\n"
        text += f"CASE: {case.get('case_name', case.get('title', 'Unnamed'))}\n"
        if 'citation' in case:
            text += f"CITATION: {case['citation']}\n"
        if 'court' in case:
            text += f"COURT: {case['court']}\n"
        if 'year' in case:
            text += f"YEAR: {case['year']}\n"
        text += f"\n{case.get('content', case.get('summary', case.get('facts', '')))}"
        
        metadata = {
            'source': 'landmark_legal_cases.json',
            'type': 'case_law',
            'case_name': case.get('case_name', case.get('title', '')),
            'year': str(case.get('year', ''))
        }
        
        docs_to_add.append({'id': doc_id, 'text': text, 'metadata': metadata})
    
    if docs_to_add:
        store.add_documents(docs_to_add, batch_size=20)
        print(f"DONE: Ingested {len(docs_to_add)} landmark expansion cases")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode in ["constitution", "all"]:
        ingest_constitution()
    
    if mode in ["cases", "all"]:
        print("\n" + "="*50)
        print("CASE LAW COLLECTIONS")
        print("="*50)
        ingest_case_law_collection("property_law_cases.json")
        ingest_case_law_collection("criminal_law_cases.json")
        ingest_case_law_collection("constitutional_law_cases.json")
    
    if mode in ["domains", "all"]:
        print("\n" + "="*50)
        print("LEGAL DOMAINS")
        print("="*50)
        ingest_legal_domain("tax_law.json")
        ingest_legal_domain("labour_law.json")
        ingest_legal_domain("ip_law.json")
        ingest_legal_domain("cyber_law.json")
    
    if mode in ["expansion", "all"]:
        ingest_landmark_expansion()
    
    print("\n" + "="*50)
    print("INGESTION COMPLETE")
    print("="*50)
