"""
RAG SYSTEM CONFIGURATION - PERMANENT STORAGE
Centralized paths to ensure data is never lost.
"""

from pathlib import Path
import os

# 1. Base Project Directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# 2. Permanent Storage Root
# Change this to a different drive (e.g., D: or E:) if you want even more safety
PERMANENT_ROOT = PROJECT_ROOT / "PERMANENT_RAG_FILES"

# 3. Database Sub-paths
MAIN_DB_PATH = PERMANENT_ROOT / "MAIN_DATABASE"
STATUTES_DB_PATH = PERMANENT_ROOT / "STATUTE_DATABASE"
BACKUP_PATH = PERMANENT_ROOT / "BACKUPS"

# 4. Collection Names
MAIN_COLLECTION = "legal_db_hybrid_prod"
STATUTES_COLLECTION = "legal_db_statutes_prod"

# 5. Cloud Hosting (Zilliz Cloud / Milvus)
# Fill these in to go live!
ZILLIZ_CLUSTER_ENDPOINT = "https://in03-65ed7b9f7b575b6.serverless.aws-eu-central-1.cloud.zilliz.com"
ZILLIZ_TOKEN = os.getenv("ZILLIZ_TOKEN", "your_zilliz_token_here")
ZILLIZ_COLLECTION_NAME = "legal_rag_cloud"
CLOUD_MODE_ENABLED = True

# Ensure directories exist
for p in [MAIN_DB_PATH, STATUTES_DB_PATH, BACKUP_PATH]:
    p.mkdir(parents=True, exist_ok=True)

print(f"RAG Storage initialized at: {PERMANENT_ROOT}")
