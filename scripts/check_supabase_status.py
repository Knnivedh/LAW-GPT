from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv('config/.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

def check_db():
    print(f"Connecting to {url}...")
    supabase: Client = create_client(url, key)
    
    try:
        # Check count
        response = supabase.table("documents").select("id", count="exact").limit(1).execute()
        count = response.count
        print(f"✅ Document Count: {count}")
        
        if count > 0:
            # Fetch a sample
            # sample = supabase.table("documents").select("content, metadata").limit(1).execute()
            # print("📄 Sample Document:")
            # print(sample.data)
            
            # Test RPC
            print("🧪 Testing 'hybrid_search' RPC function...")
            try:
                params = {
                    "query_text": "test",
                    "query_embedding": [0.1] * 384, # Dummy vector
                    "match_count": 1,
                    "full_text_weight": 1.0,
                    "semantic_weight": 1.0,
                    "rrf_k": 50
                }
                rpc_res = supabase.rpc("hybrid_search", params).execute()
                print("✅ RPC Call Successful!")
            except Exception as e:
                print(f"❌ RPC Call Failed: {e}")
        else:
            print("⚠️ Database is EMPTY!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_db()
