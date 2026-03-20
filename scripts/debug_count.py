from dotenv import load_dotenv
from pathlib import Path
import os
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_system.core.supabase_store import SupabaseHybridStore

load_dotenv(project_root / "config" / ".env")

store = SupabaseHybridStore()
info = store.get_collection_info()
count = info['count']

with open("supabase_count.txt", "w") as f:
    f.write(str(count))
