import sys
import os
import logging
from pathlib import Path
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from kaanoon_test.utils.client_manager import GroqClientManager

def test_rotation_logic():
    """Simulate 60 requests to verify Key Rotation logic (without hitting real API 60 times)"""
    
    print("\n" + "="*80)
    print("🔄 TESTING GROQ KEY ROTATION MANAGER")
    print("="*80)
    
    try:
        # Initialize Manager with limit of 5 for testing (instead of 29)
        manager = GroqClientManager(request_limit=5)
        
        print(f"Keys loaded: {len(manager.api_keys)}")
        print(f"Rotation Limit: {manager.request_limit}")
        
        current_key_idx = manager.current_key_index
        print(f"\n[START] Active Key Index: {current_key_idx}")
        
        # Simulate 12 requests (Should rotate twice: at 5 and 10)
        for i in range(1, 13):
            client = manager.get_client()
            new_idx = manager.current_key_index
            
            status = "SAME"
            if new_idx != current_key_idx:
                status = "ROTATED 🔀"
                current_key_idx = new_idx
                
            print(f"Req {i}: Key Index {new_idx} | Requests: {manager.request_count}/{manager.request_limit} | {status}")
            
        print("\n" + "="*80)
        print("✅ ROTATION TEST COMPLETE")
        print("="*80)

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_rotation_logic()
