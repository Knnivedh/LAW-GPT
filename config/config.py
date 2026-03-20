"""
Configuration file for Legal Chatbot RAG System
"""
import os
from dotenv import load_dotenv

# Load environment variables from config/.env
load_dotenv("config/.env")

from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

class Config:
    """Main configuration class"""
    
    # ==================== API CONFIGURATION ====================
    # Cerebras API (PRIMARY - FREE 1M tokens/day, VERY FAST)
    CEREBRAS_API_KEY = os.getenv("cerebras_api") or os.getenv("CEREBRAS_API_KEY")
    CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
    CEREBRAS_MODEL = "llama-3.3-70b"  # Very fast inference
    
    # Groq API (BACKUP - FREE, ULTRA FAST)
    GROQ_API_KEY = os.getenv("groq_api") or os.getenv("GROQ_API_KEY")
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_MODEL = "llama-3.3-70b-versatile"  # Single best model for accuracy
    
    # Web Search Configuration
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    # NVIDIA API Keys (FALLBACK)
    NVIDIA_API_KEY = os.getenv("nvidia_api") or os.getenv("NVIDIA_API_KEY")
    NVIDIA_API_KEY_2 = os.getenv("nvidia_api_2") or os.getenv("NVIDIA_API_KEY_2")
    NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"
    
    # LLM Configuration
    TEMPERATURE = 0.15  # Low temperature for precise legal answers
    MAX_TOKENS = 4000  # Increased for comprehensive legal responses
    
    # Provider Priority (1=highest)
    LLM_PROVIDERS = [
        {"name": "cerebras", "priority": 1, "speed": "very_fast"},
        {"name": "groq", "priority": 2, "speed": "ultra_fast"},
        {"name": "nvidia", "priority": 3, "speed": "moderate"}
    ]
    
    # ==================== DATA PATHS ====================
    DATA_DIR = str(PROJECT_ROOT / "DATA")
    CHROMA_DB_DIR = str(PROJECT_ROOT / "chroma_db")
    COLLECTION_NAME = "legal_db_full"
    
    # Domain Paths
    DOMAIN_PATHS = {
        "case_studies": "Indian_Case_Studies_50K ORG/Indian_Case_Studies_50K ORG.json",
        "indian_express": "indianexpress_property_law_qa/indianexpress_property_law_qa.json",
        "kanoon": "kanoon.com/kanoon.com/kanoon_data.json",
        "legallyin": "legallyin.com/legallyin.com.json",
        "ndtv": "ndtv_legal_qa_data/ndtv_legal_qa_data.json",
        "hindu": "thehindu/thehindu.json",
        "wikipedia": "wikipedia.org/wikipedia.org.json"
    }
    
    # ==================== RAG SETTINGS ====================
    # Embedding Model
    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # Small, fast, accurate
    
    # Retrieval Settings
    TOP_K_RESULTS = 5           # Number of documents to retrieve
    SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score
    
    # Chunking Settings (if needed)
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # ==================== PROCESSING SETTINGS ====================
    BATCH_SIZE = 1000           # Batch size for loading data
    MAX_WORKERS = 4             # Parallel processing threads
    
    # ==================== API SETTINGS ====================
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_RELOAD = True           # Auto-reload on code changes
    
    # ==================== UI SETTINGS ====================
    UI_TITLE = "⚖️ Indian Legal Assistant"
    UI_SUBTITLE = "156K+ Legal Records • NVIDIA Llama 3.1 70B • Free & Fast"
    
    # Categories for filtering
    LEGAL_CATEGORIES = [
        "All",
        "Property Law",
        "Criminal Law",
        "Family Law",
        "Corporate Law",
        "Corruption",
        "Murder",
        "Rape",
        "Fraud",
        "Terrorism"
    ]
    
    # ==================== SYSTEM SETTINGS ====================
    DEBUG = True
    LOG_LEVEL = "INFO"
    CACHE_ENABLED = True
    CACHE_SIZE = 1000
    
    # ==================== VALIDATION ====================
    @classmethod
    def get_llm_config(cls, provider: str = "cerebras"):
        """Get LLM configuration for specified provider"""
        configs = {
            "cerebras": {
                "api_key": cls.CEREBRAS_API_KEY,
                "base_url": cls.CEREBRAS_BASE_URL,
                "model": cls.CEREBRAS_MODEL,
                "name": "Cerebras"
            },
            "groq": {
                "api_key": cls.GROQ_API_KEY,
                "base_url": cls.GROQ_BASE_URL,
                "model": cls.GROQ_MODEL,
                "name": "Groq"
            },
            "nvidia": {
                "api_key": cls.NVIDIA_API_KEY,
                "base_url": cls.NVIDIA_BASE_URL,
                "model": cls.NVIDIA_MODEL,
                "name": "NVIDIA"
            }
        }
        return configs.get(provider, configs["cerebras"])
    
    @classmethod
    def get_available_provider(cls):
        """Get first available LLM provider"""
        if cls.CEREBRAS_API_KEY:
            return "cerebras"
        elif cls.GROQ_API_KEY:
            return "groq"
        elif cls.NVIDIA_API_KEY:
            return "nvidia"
        return None
    
    @classmethod
    def get_nvidia_api_key(cls, use_backup: bool = False):
        """Get NVIDIA API key with failover support (deprecated, use get_llm_config)"""
        if use_backup and cls.NVIDIA_API_KEY_2:
            return cls.NVIDIA_API_KEY_2
        return cls.NVIDIA_API_KEY
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        if not cls.NVIDIA_API_KEY:
            errors.append("NVIDIA_API_KEY (nvidia_api) not set in config/.env")
        
        if not os.path.exists(cls.DATA_DIR):
            errors.append(f"DATA directory not found: {cls.DATA_DIR}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("="*60)
        print("LEGAL CHATBOT CONFIGURATION")
        print("="*60)
        print(f"NVIDIA API Key 1: {cls.NVIDIA_API_KEY[:20] if cls.NVIDIA_API_KEY else 'NOT SET'}...")
        print(f"NVIDIA API Key 2: {cls.NVIDIA_API_KEY_2[:20] if cls.NVIDIA_API_KEY_2 else 'NOT SET'}...")
        print(f"NVIDIA Model: {cls.NVIDIA_MODEL}")
        print(f"NVIDIA Base URL: {cls.NVIDIA_BASE_URL}")
        print(f"Temperature: {cls.TEMPERATURE}")
        print(f"Max Tokens: {cls.MAX_TOKENS}")
        print(f"Data Directory: {cls.DATA_DIR}")
        print(f"ChromaDB Directory: {cls.CHROMA_DB_DIR}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL}")
        print(f"Top K Results: {cls.TOP_K_RESULTS}")
        print("="*60)


# Validate on import
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"WARNING - Configuration: {e}")
