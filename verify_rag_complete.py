"""
COMPREHENSIVE RAG DATA VERIFICATION SYSTEM
Verifies ALL data from DATA folder is indexed, tagged, and retrievable

This script:
1. Checks database completeness
2. Validates metadata quality
3. Tests actual retrieval for known cases
4. Generates detailed connectivity report
"""

import chromadb
import json
from pathlib import Path
from collections import defaultdict

print("="*80)
print("🔍 COMPREHENSIVE RAG DATA VERIFICATION")
print("="*80)

# Initialize
db_path = Path("chroma_db_hybrid").absolute()
DATA_DIR = Path("DATA").absolute()

# Expected data sources and counts
EXPECTED_DATA = {
    "Supreme Court Kaggle": {
        "source_path": DATA_DIR / "processed_kaggle",
        "expected_docs": 26688,
        "tolerance": 100,  # Allow ±100 variance
        "file_type": "JSON batches",
        "key_fields": ["case_name", "citation", "date"]
    },
    "Indian Case Studies 50K": {
        "source_path": DATA_DIR / "Indian_Case_Studies_50K ORG",
        "expected_docs": 50000,
        "tolerance": 0,
        "file_type": "Single JSON",
        "key_fields": ["case_name", "court", "date"]
    },
    "consumer_law_specifics.json": {
        "source_path": DATA_DIR / "consumer_law_specifics.json",
        "expected_docs": 6,
        "tolerance": 0,
        "file_type": "Knowledge file",
        "key_fields": ["category"]
    },
    "law_transitions_2024.json": {
        "source_path": DATA_DIR / "law_transitions_2024.json",
        "expected_docs": 5,
        "tolerance": 0,
        "file_type": "Knowledge file",
        "key_fields": ["category"]
    },
    "pwdva_comprehensive.json": {
        "source_path": DATA_DIR / "pwdva_comprehensive.json",
        "expected_docs": 4,
        "tolerance": 0,
        "file_type": "Knowledge file",
        "key_fields": ["category"]
    },
    "specific_gap_fix_cases.json": {
        "source_path": DATA_DIR / "specific_gap_fix_cases.json",
        "expected_docs": 3,
        "tolerance": 0,
        "file_type": "Knowledge file",
        "key_fields": []
    },
    "landmark_legal_cases.json": {
        "source_path": DATA_DIR / "landmark_legal_cases.json",
        "expected_docs": 15,
        "tolerance": 5,
        "file_type": "Knowledge file",
        "key_fields": []
    },
    "landmark_legal_cases_expansion.json": {
        "source_path": DATA_DIR / "landmark_legal_cases_expansion.json",
        "expected_docs": 10,
        "tolerance": 5,
        "file_type": "Knowledge file",
        "key_fields": []
    }
}

# Test queries for known landmark cases
TEST_QUERIES = [
    {
        "name": "Hadiya Case",
        "keywords": ["Hadiya", "marriage", "autonomy"],
        "expected_source": "Supreme Court Kaggle",
        "min_results": 1
    },
    {
        "name": "Vidya Devi (Adverse Possession)",
        "keywords": ["Vidya Devi", "adverse possession", "government"],
        "expected_source": "Indian Case Studies 50K",
        "min_results": 1
    },
    {
        "name": "Alchemist IBC",
        "keywords": ["Alchemist", "Section 14", "IBC"],
        "expected_source": "Supreme Court Kaggle",
        "min_results": 1
    },
    {
        "name": "Consumer Law",
        "keywords": ["consumer", "complaint", "forum"],
        "expected_source": "consumer_law_specifics.json",
        "min_results": 1
    }
]

class RAGVerifier:
    """Comprehensive RAG verification"""
    
    def __init__(self):
        self.results = {
            "database_exists": False,
            "total_documents": 0,
            "sources_found": {},
            "metadata_quality": {},
            "retrieval_tests": {},
            "issues": [],
            "warnings": []
        }
    
    def verify_database_exists(self):
        """Check if database exists"""
        print("\n1️⃣ Checking Database Existence...")
        
        if not db_path.exists():
            self.results["issues"].append("❌ Database does not exist!")
            print("   ❌ Database NOT FOUND at:", db_path)
            return False
        
        size_mb = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file()) / (1024*1024)
        print(f"   ✅ Database exists: {size_mb:.2f} MB")
        self.results["database_exists"] = True
        self.results["database_size_mb"] = size_mb
        return True
    
    def verify_document_counts(self):
        """Check document counts per source"""
        print("\n2️⃣ Verifying Document Counts...")
        
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_collection(name="legal_db_hybrid")
        
        total = collection.count()
        self.results["total_documents"] = total
        print(f"   Total documents in DB: {total:,}")
        
        # Get all documents with metadata (in batches)
        print("   Analyzing sources...")
        source_counts = defaultdict(int)
        batch_size = 1000
        offset = 0
        
        while offset < total:
            batch = collection.get(
                limit=min(batch_size, total - offset),
                offset=offset,
                include=['metadatas']
            )
            
            for meta in batch['metadatas']:
                source = meta.get('source', 'Unknown')
                source_counts[source] += 1
            
            offset += batch_size
            if offset % 10000 == 0:
                print(f"   ...processed {offset:,}/{total:,}")
        
        # Compare with expected
        print("\n   📊 Source-by-Source Verification:")
        for source_name, expected_info in EXPECTED_DATA.items():
            actual_count = source_counts.get(source_name, 0)
            expected_count = expected_info['expected_docs']
            tolerance = expected_info['tolerance']
            
            self.results["sources_found"][source_name] = actual_count
            
            diff = abs(actual_count - expected_count)
            
            if actual_count == 0:
                status = "❌ MISSING"
                self.results["issues"].append(f"Source '{source_name}' has 0 documents")
            elif diff <= tolerance:
                status = "✅ OK"
            else:
                status = f"⚠️ COUNT MISMATCH"
                self.results["warnings"].append(
                    f"Source '{source_name}': expected {expected_count}, got {actual_count} (diff: {diff})"
                )
            
            print(f"   {status:15} | {source_name:40} | {actual_count:6,} / {expected_count:6,}")
        
        # Check for Unknown source
        unknown_count = source_counts.get('Unknown', 0)
        if unknown_count > 0:
            self.results["issues"].append(f"⚠️ {unknown_count:,} documents with source='Unknown'")
            print(f"   ❌ CORRUPTED  | Unknown (corrupted metadata)              | {unknown_count:6,}")
        
        return source_counts
    
    def verify_metadata_quality(self, client):
        """Check metadata field completeness"""
        print("\n3️⃣ Verifying Metadata Quality...")
        
        collection = client.get_collection(name="legal_db_hybrid")
        
        # Sample 1000 random documents
        sample = collection.get(limit=1000, include=['metadatas'])
        
        field_stats = defaultdict(lambda: {"present": 0, "none": 0, "na": 0})
        
        for meta in sample['metadatas']:
            for field, value in meta.items():
                if value is None:
                    field_stats[field]["none"] += 1
                elif value == 'N/A':
                    field_stats[field]["na"] += 1
                else:
                    field_stats[field]["present"] += 1
        
        print("   Field Quality (sample of 1000 docs):")
        for field, stats in field_stats.items():
            total = stats['present'] + stats['none'] + stats['na']
            present_pct = (stats['present'] / total * 100) if total > 0 else 0
            
            if stats['none'] > 0:
                status = "❌ HAS NONE"
                self.results["issues"].append(f"Field '{field}' has {stats['none']} None values")
            else:
                status = "✅ OK"
            
            print(f"   {status:12} | {field:20} | Present: {present_pct:5.1f}% | None: {stats['none']:4} | N/A: {stats['na']:4}")
        
        self.results["metadata_quality"] = dict(field_stats)
    
    def test_retrieval(self, client):
        """Test actual retrieval for known cases"""
        print("\n4️⃣ Testing Retrieval for Known Cases...")
        
        collection = client.get_collection(name="legal_db_hybrid")
        
        for test in TEST_QUERIES:
            print(f"\n   Testing: {test['name']}")
            
            # Search by text
            query_text = " ".join(test['keywords'])
            results = collection.query(
                query_texts=[query_text],
                n_results=5,
                include=['metadatas', 'distances']
            )
            
            found_count = len(results['ids'][0])
            
            test_result = {
                "query": query_text,
                "found_count": found_count,
                "expected_min": test['min_results'],
                "sources": []
            }
            
            if found_count >= test['min_results']:
                print(f"      ✅ Found {found_count} results")
                
                # Check sources
                for meta in results['metadatas'][0]:
                    source = meta.get('source', 'Unknown')
                    test_result["sources"].append(source)
                
                # Verify expected source is present
                if test['expected_source'] in test_result["sources"]:
                    print(f"      ✅ Contains expected source: {test['expected_source']}")
                else:
                    print(f"      ⚠️ Expected source '{test['expected_source']}' not in results")
                    print(f"         Found sources: {set(test_result['sources'])}")
                    self.results["warnings"].append(
                        f"Query '{test['name']}' didn't return expected source"
                    )
            else:
                print(f"      ❌ Only found {found_count} results (expected >= {test['min_results']})")
                self.results["issues"].append(
                    f"Query '{test['name']}' returned {found_count} results (expected >= {test['min_results']})"
                )
            
            self.results["retrieval_tests"][test['name']] = test_result
    
    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "="*80)
        print("📋 VERIFICATION REPORT")
        print("="*80)
        
        # Overall status
        if len(self.results["issues"]) == 0:
            print("\n✅ STATUS: ALL CHECKS PASSED")
            overall_status = "PASS"
        elif len(self.results["issues"]) > 0 and len(self.results["warnings"]) == 0:
            print("\n❌ STATUS: CRITICAL ISSUES FOUND")
            overall_status = "FAIL"
        else:
            print("\n⚠️ STATUS: WARNINGS FOUND (but operational)")
            overall_status = "WARNING"
        
        print(f"\nTotal Documents: {self.results['total_documents']:,}")
        print(f"Database Size: {self.results.get('database_size_mb', 0):.2f} MB")
        
        # Issues
        if self.results["issues"]:
            print(f"\n❌ CRITICAL ISSUES ({len(self.results['issues'])}):")
            for issue in self.results["issues"]:
                print(f"   - {issue}")
        
        # Warnings
        if self.results["warnings"]:
            print(f"\n⚠️ WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"   - {warning}")
        
        # Save JSON report
        report_file = Path("rag_verification_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        print("="*80)
        
        return overall_status
    
    def run_full_verification(self):
        """Run complete verification suite"""
        if not self.verify_database_exists():
            print("\n❌ Cannot proceed - database not found!")
            return "FAIL"
        
        client = chromadb.PersistentClient(path=str(db_path))
        
        self.verify_document_counts()
        self.verify_metadata_quality(client)
        self.test_retrieval(client)
        
        return self.generate_report()


if __name__ == "__main__":
    verifier = RAGVerifier()
    status = verifier.run_full_verification()
    
    # Exit code based on status
    if status == "PASS":
        exit(0)
    elif status == "WARNING":
        exit(1)
    else:
        exit(2)
