import os
from huggingface_hub import HfApi

# Configuration
REPO_ID = "wsdasdsd/law-gpt-backend"
TOKEN = os.getenv("HF_TOKEN", "your_hf_token_here")

# Secrets to set
SECRETS = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL", "https://your_supabase_url.supabase.co"),
    "SUPABASE_KEY": os.getenv("SUPABASE_KEY", "your_supabase_key_here"),
    "CEREBRAS_API_KEY": os.getenv("CEREBRAS_API_KEY", "your_cerebras_key_here"),
    "SERPER_API_KEY": os.getenv("SERPER_API_KEY", "your_serper_key_here"),
    "INDIAN_KANOON_API_TOKEN": os.getenv("INDIAN_KANOON_API_TOKEN", "your_kanoon_token_here")
}

def setup_secrets():
    print(f"🔐 Setting secrets for {REPO_ID}...")
    api = HfApi(token=TOKEN)
    
    for key, value in SECRETS.items():
        try:
            api.add_space_secret(repo_id=REPO_ID, key=key, value=value)
            print(f"   ✅ Set {key}")
        except Exception as e:
            print(f"   ❌ Failed to set {key}: {e}")
            
    print("\n🎉 Secrets configuration complete!")

if __name__ == "__main__":
    setup_secrets()
