import os
import threading
from openai import OpenAI
import logging
from typing import List, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SmartCompletionsProxy:
    """Intercepts completion calls to handle provider-specific nuances (Model Mapping)"""
    def __init__(self, completions_interface, provider_type: str):
        self.interface = completions_interface
        self.provider_type = provider_type
    
    def create(self, **kwargs):
        # DYNAMIC MODEL MAPPING
        # Groq uses "llama-3.3-70b-versatile", Cerebras uses "llama3.1-70b"
        if self.provider_type == "cerebras":
            original_model = kwargs.get("model", "")
            if "llama" in original_model.lower() and "70b" in original_model.lower():
                # Map to Cerebras equivalent
                kwargs["model"] = "llama3.1-70b"
                # logger.info(f"  [🔀 BRIDGE] Mapped model '{original_model}' -> 'llama3.1-70b' for Cerebras")
            
        return self.interface.create(**kwargs)

class SmartChatProxy:
    """Wraps the chat interface"""
    def __init__(self, chat_interface, provider_type: str):
        self.chat_interface = chat_interface
        self.provider_type = provider_type
        self.completions = SmartCompletionsProxy(chat_interface.completions, provider_type)

class GroqClientManager:
    """
    Manages multiple API clients (Groq + Cerebras) with Rate Limit Bypass via Key Rotation.
    "The 29-Step Loop": Switches keys every 29 requests.
    """
    
    def __init__(self, request_limit: int = 29):
        self.request_limit = request_limit
        self.request_count = 0
        self.current_key_index = 0
        self._lock = threading.Lock()  # Thread-safe rotation
        
        # Load Keys — supports two naming styles:
        # Style A (standard): GROQ_API_KEY, GROQ_API_KEY_2 ... GROQ_API_KEY_5
        # Style B (legacy):   GROQ_API_KEY1, GROQ_API_KEY2  ... GROQ_API_KEY5
        self.api_keys = []

        # Style A — Key 1
        for var in ["GROQ_API_KEY", "groq_api", "GROQ_API_KEY1"]:
            v = os.getenv(var)
            if v and v not in self.api_keys:
                self.api_keys.append(v)
                break

        # Style A — Keys 2-5  |  Style B — Keys 2-5
        for i in range(2, 6):
            for var in [f"GROQ_API_KEY_{i}", f"GROQ_API_KEY{i}"]:
                v = os.getenv(var)
                if v and v not in self.api_keys:
                    self.api_keys.append(v)
                    break

        # Cerebras key (optional, ultra-fast inference)
        cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
        if cerebras_key and cerebras_key not in self.api_keys:
            self.api_keys.append(cerebras_key)

        if not self.api_keys:
            raise ValueError("No API Keys found! Set GROQ_API_KEY in env or .env file.")
            
        logger.info(f"⚡ ClientManager initialized with {len(self.api_keys)} keys. Rotation Limit: {self.request_limit}")
        
        # Initialize Clients & Types
        self.clients = []
        self.client_types = []
        
        for k in self.api_keys:
            if k.startswith("csk-"):
                # CEREBRAS
                self.clients.append(OpenAI(api_key=k, base_url="https://api.cerebras.ai/v1"))
                self.client_types.append("cerebras")
                logger.info("  -> Loaded CEREBRAS Client")
            else:
                # GROQ (Default)
                self.clients.append(OpenAI(api_key=k, base_url="https://api.groq.com/openai/v1"))
                self.client_types.append("groq")
                logger.info("  -> Loaded GROQ Client")

    def get_client(self):
        """Returns the current active client, rotating if necessary (thread-safe)"""
        with self._lock:
            self.request_count += 1
            if self.request_count >= self.request_limit:
                self._rotate_key()
        return self.clients[self.current_key_index]
    
    def get_current_provider_type(self):
        return self.client_types[self.current_key_index]
        
    def _rotate_key(self):
        """Switches to the next API key (call inside _lock)"""
        old_index = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.clients)
        self.request_count = 0
        new_provider = self.client_types[self.current_key_index]
        logger.info(f"🔄 ROTATING API KEY: {old_index} -> {self.current_key_index} (Provider: {new_provider}, total={len(self.clients)} keys)")

    @property
    def chat(self):
        """Proxy for chat completions to allow seamless drop-in replacement with model mapping"""
        current_client = self.get_client()
        provider_type = self.get_current_provider_type()
        return SmartChatProxy(current_client.chat, provider_type)
        
    def get_active_key(self) -> str:
        """Returns the currently active API Key string"""
        return self.api_keys[self.current_key_index]

    def force_rotation(self, reason: str = "Unknown"):
        """Forced rotation triggered by external error (e.g., 429 Rate Limit) — thread-safe"""
        with self._lock:
            logger.warning(f"⚠️ FORCED KEY ROTATION TRIGGERED: {reason} (key {self.current_key_index} -> next)")
            self._rotate_key()

    def key_count(self) -> int:
        """Returns number of loaded API keys"""
        return len(self.clients)
