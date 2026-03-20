import sys
from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / "config" / ".env")

print("--- Minimal Initialization Test ---")
try:
    from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
    print("Import successful")
    
    rag = UnifiedAdvancedRAG()
    print("Initialization successful")
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
