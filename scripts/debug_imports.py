import sys
from pathlib import Path
import os

print("--- DEBUG: Starting Import Check ---")
try:
    # Resolve absolute path to be safe
    file_path = Path(__file__).resolve()
    print(f"File Path: {file_path}")
    
    project_root = file_path.parent.parent
    print(f"Project Root: {project_root}")
    
    sys.path.insert(0, str(project_root))
    print(f"sys.path[0]: {sys.path[0]}")
    
    print("Importing ClarificationSession...")
    from kaanoon_test.system_adapters.clarification_engine import ClarificationSession
    print("✓ ClarificationSession Imported")
    
    print("Importing UnifiedAdvancedRAG...")
    from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
    print("✓ UnifiedAdvancedRAG Imported")

    print("--- DEBUG: All Imports Successful ---")

except Exception as e:
    print(f"\n[CRITICAL ERROR] Import Failed: {e}")
    import traceback
    traceback.print_exc()
