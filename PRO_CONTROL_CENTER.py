"""
⚖️ LEGAL RAG PRO CONTROL CENTER
The master dashboard to manage 100% data connectivity, 
permanent storage, and cloud hosting.
"""

import os
import sys
import time
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

import rag_config
from rag_system.core.hybrid_chroma_store import HybridChromaStore

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_db_stats():
    """Get real-time stats from the permanent store"""
    try:
        # We use a fresh client to avoid locks
        store = HybridChromaStore()
        count = store.collection.count()
        return count
    except Exception:
        return "Calculating..."

def run_backup():
    print("\n📦 Starting Backup...")
    os.system("python backup_rag.py")
    input("\nPress Enter to return...")

def run_ingestion():
    print("\n🚀 Starting Universal Crawler (3L+ Documents)...")
    print("This will connect 100% of your DATA folder.")
    os.system("python scripts/universal_crawl_ingest.py")
    input("\nPress Enter to return...")

def run_cloud_setup():
    clear_screen()
    print("="*80)
    print("☁️  ZILLIZ CLOUD SETUP - GO LIVE")
    print("="*80)
    print("\n1. Go to https://cloud.zilliz.com")
    print("2. Create a FREE cluster and get your Public Endpoint.")
    print("3. Generate an API Key (Token).")
    
    endpoint = input("\nEnter Public Endpoint: ").strip()
    token = input("Enter API Key (Token): ").strip()
    
    if endpoint and token:
        with open("rag_config.py", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        with open("rag_config.py", "w", encoding="utf-8") as f:
            for line in lines:
                if 'ZILLIZ_CLUSTER_ENDPOINT =' in line:
                    f.write(f'ZILLIZ_CLUSTER_ENDPOINT = "{endpoint}"\n')
                elif 'ZILLIZ_TOKEN =' in line:
                    f.write(f'ZILLIZ_TOKEN = "{token}"\n')
                else:
                    f.write(line)
        print("\n✅ Credentials saved to rag_config.py!")
    else:
        print("\n❌ Setup canceled or incomplete.")
    input("\nPress Enter to return...")

def run_cloud_sync():
    clear_screen()
    print("="*80)
    print("🛰️  CLOUD SYNCHRONIZATION (Local -> Zilliz)")
    print("="*80)
    
    import rag_config
    if not rag_config.CLOUD_MODE_ENABLED:
        print("❌ Cloud mode not configured. Please run 'Cloud Setup' first.")
        input("\nPress Enter to return...")
        return

    from rag_system.core.milvus_store import CloudMilvusStore
    from rag_system.core.hybrid_chroma_store import HybridChromaStore
    
    try:
        print("Connecting to Local DB...")
        local = HybridChromaStore()
        print("Connecting to Zilliz Cloud...")
        cloud = CloudMilvusStore()
        
        if not cloud.is_connected:
            print("❌ Could not connect to Cloud. Check your credentials.")
            input("\nPress Enter to return...")
            return

        print("\nFetching labels from local DB...")
        data = local.collection.get()
        docs = data['documents']
        metas = data['metadatas']
        ids = data['ids']
        
        print(f"Syncing {len(docs)} documents to the cloud...")
        # Batch upload to avoid timeouts
        batch_size = 100
        for i in range(0, len(docs), batch_size):
            end = min(i + batch_size, len(docs))
            cloud.add(docs[i:end], metas[i:end], ids[i:end])
            print(f"  [{end}/{len(docs)}] Documents uploaded...")
            
        print("\n✅ CLOUD SYNC COMPLETE!")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        
    input("\nPress Enter to return...")

def show_menu():
    import rag_config
    clear_screen()
    print("="*80)
    print("⚖️  LEGAL RAG PRO CONTROL CENTER - [PERMANENT VERSION]")
    print("="*80)
    print(f"📍 Storage: {rag_config.PERMANENT_ROOT}")
    print(f"📊 Live Docs: {get_db_stats()}")
    status = "READY ✅" if rag_config.CLOUD_MODE_ENABLED else "LOCAL ONLY 🏠"
    print(f"☁️  Cloud Status: {status}")
    print("-" * 80)
    print("1. [INGEST]  Connect all 3L+ documents (Universal Crawler)")
    print("2. [BACKUP]  Create permanent ZIP backup")
    print("3. [HEALTH]  Check Database & GPU Status")
    print("4. [CLOUD]   Setup Zilliz Cloud Hosting")
    print("5. [SYNC]    Sync Local Data to Cloud (Go Live!)")
    print("6. [RESTART] Reboot API Server")
    print("0. [EXIT]    Close Control Center")
    print("-" * 80)

def main():
    while True:
        show_menu()
        choice = input("\nSelect Action: ")
        
        if choice == '1':
            run_ingestion()
        elif choice == '2':
            run_backup()
        elif choice == '3':
            clear_screen()
            print("🔍 SYSTEM HEALTH CHECK")
            os.system("python scripts/debug_statutes_health.py")
            os.system("python scripts/debug_chroma_crash.py")
            input("\nPress Enter to return...")
        elif choice == '4':
            run_cloud_setup()
        elif choice == '5':
            run_cloud_sync()
        elif choice == '6':
            print("\n🔄 Restarting API Server...")
            os.system("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq API_SERVER\"")
            print("Server rebooted. Check terminal for logs.")
            time.sleep(2)
        elif choice == '0':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")
            time.sleep(1)

if __name__ == "__main__":
    main()
