"""Deploy PageIndex integration to Azure via Kudu VFS API.

Files uploaded:
  - pageindex_retriever.py  (new)
  - agentic_rag_engine.py   (patched - accepts pageindex_retriever)
  - unified_advanced_rag.py (patched - initialises PageIndexRetriever)
  - requirements.txt        (updated - pageindex added)

Also installs the pageindex package on the server.
"""
import subprocess, json, urllib.request, time, sys

az = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
print("[AUTH] Getting Azure token...")
raw = subprocess.check_output(
    [az, "account", "get-access-token", "--resource", "https://management.azure.com/"],
    text=True, stderr=subprocess.DEVNULL
)
token = json.loads(raw)["accessToken"]
H_JSON = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
H_PUT  = {"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream", "If-Match": "*"}

KUDU = "https://lawgpt-backend2024.scm.azurewebsites.net"
SUB  = "2a38c188-3c90-4700-bb9b-83822b96a381"
BASE_LOCAL = r"C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT"

FILES = {
    "kaanoon_test/system_adapters/pageindex_retriever.py":
        fr"{BASE_LOCAL}\kaanoon_test\system_adapters\pageindex_retriever.py",
    "kaanoon_test/system_adapters/agentic_rag_engine.py":
        fr"{BASE_LOCAL}\kaanoon_test\system_adapters\agentic_rag_engine.py",
    "kaanoon_test/system_adapters/unified_advanced_rag.py":
        fr"{BASE_LOCAL}\kaanoon_test\system_adapters\unified_advanced_rag.py",
    "requirements.txt":
        fr"{BASE_LOCAL}\requirements.txt",
}

all_ok = True
for remote_path, local_path in FILES.items():
    print(f"\n[UPLOAD] {remote_path}")
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        print(f"  Local file: {len(data)} bytes")
        url = f"{KUDU}/api/vfs/site/wwwroot/{remote_path}"
        req = urllib.request.Request(url, data=data, headers=H_PUT, method="PUT")
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"  OK Uploaded - HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"  FAILED HTTP {e.code}: {body[:300]}")
        all_ok = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_ok = False

if not all_ok:
    print("\n[ERROR] Upload failed.")
    sys.exit(1)

KUDU_CMD = f"{KUDU}/api/command"

def run_cmd(cmd, label=""):
    try:
        body = json.dumps({"command": cmd, "dir": "/home/site/wwwroot"}).encode()
        req = urllib.request.Request(KUDU_CMD, data=body, headers=H_JSON, method="POST")
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            out = result.get("Output", "").strip()
            err = result.get("Error", "").strip()
            print(f"  [{label or cmd[:40]}] out={out[:200]} err={err[:100]}")
            return out
    except Exception as e:
        print(f"  CMD FAILED: {e}")
        return ""

print("\n[INSTALL] Installing pageindex package on server...")
run_cmd("pip install pageindex --quiet 2>&1 | tail -3", "pip install pageindex")

print("\n[CLEAN] Clearing pycache...")
clean_cmds = [
    "rm -rf /home/site/wwwroot/kaanoon_test/system_adapters/__pycache__ 2>/dev/null; echo OK",
    "rm -rf /home/site/wwwroot/kaanoon_test/__pycache__ 2>/dev/null; echo OK",
    "find /home/site/wwwroot -name '*.pyc' -delete 2>/dev/null; echo OK",
]
for cmd in clean_cmds:
    run_cmd(cmd, "clean")

print("\n[RESTART] Restarting Azure App Service...")
restart_url = (
    f"https://management.azure.com/subscriptions/{SUB}"
    f"/resourceGroups/lawgpt-rg/providers/Microsoft.Web/sites"
    f"/lawgpt-backend2024/restart?api-version=2022-03-01"
)
req = urllib.request.Request(restart_url, data=b"", headers=H_JSON, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"  Restart triggered - HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"  Restart HTTP {e.code}")

print("\n[WAIT] Waiting 40s for app to restart...")
time.sleep(40)
print("\n[DONE] PageIndex integration deployed to Azure.")
print("Next step: set PAGEINDEX_API_KEY in Azure App Service -> Configuration -> App Settings")
print("Then run: python kaanoon_test/pageindex_ingest.py  (to index statutes)")