"""Deploy clarification_engine.py + clarification_prompts.py to Azure via Kudu VFS API"""
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

# ─── Files to upload ─────────────────────────────────────────────────────────
FILES = {
    "kaanoon_test/system_adapters/clarification_engine.py":
        fr"{BASE_LOCAL}\kaanoon_test\system_adapters\clarification_engine.py",
    "kaanoon_test/system_adapters/clarification_prompts.py":
        fr"{BASE_LOCAL}\kaanoon_test\system_adapters\clarification_prompts.py",
}

# ─── Upload ──────────────────────────────────────────────────────────────────
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
            print(f"  ✓ Uploaded — HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"  ✗ FAILED HTTP {e.code}: {body[:300]}")
        all_ok = False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        all_ok = False

if not all_ok:
    print("\n[ERROR] Upload failed. Aborting.")
    sys.exit(1)

# ─── Clear pycache ───────────────────────────────────────────────────────────
print("\n[CLEAN] Clearing pycache for system_adapters...")
KUDU_CMD = f"{KUDU}/api/command"
clean_cmds = [
    "rm -rf /home/site/wwwroot/kaanoon_test/system_adapters/__pycache__ 2>/dev/null; echo OK",
    "rm -rf /home/site/wwwroot/kaanoon_test/__pycache__ 2>/dev/null; echo OK",
    "find /home/site/wwwroot -name '*.pyc' -delete 2>/dev/null; echo OK",
]
for cmd in clean_cmds:
    try:
        body = json.dumps({"command": cmd, "dir": "/home/site/wwwroot"}).encode()
        req = urllib.request.Request(KUDU_CMD, data=body, headers=H_JSON, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            print(f"  {cmd[:60]} → {result.get('Output','').strip()}")
    except Exception as e:
        print(f"  ⚠ Clean cmd failed: {e}")

# ─── Restart ─────────────────────────────────────────────────────────────────
print("\n[RESTART] Restarting Azure App Service...")
restart_url = (
    f"https://management.azure.com/subscriptions/{SUB}"
    f"/resourceGroups/lawgpt-rg/providers/Microsoft.Web/sites"
    f"/lawgpt-backend2024/restart?api-version=2022-03-01"
)
req = urllib.request.Request(restart_url, data=b"", headers=H_JSON, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"  ✓ Restart triggered — HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"  Restart HTTP {e.code}")

# ─── Wait for startup ─────────────────────────────────────────────────────────
print("\n[WAIT] Waiting 75s for app to restart and hot-patch to apply...")
for i in range(75, 0, -15):
    print(f"  {i}s remaining...")
    time.sleep(15)

# ─── Health check ─────────────────────────────────────────────────────────────
print("\n[VERIFY] Health check...")
health_url = "https://lawgpt-backend2024.azurewebsites.net/api/health"
try:
    req = urllib.request.Request(health_url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
        print(f"  ✓ Status: {data.get('status')} | Version: {data.get('version','?')}")
except Exception as e:
    print(f"  ⚠ Health check error: {e}")

# ─── Spot-test Q15 fix ────────────────────────────────────────────────────────
print("\n[TEST] Spot-testing Q15 fix (new laws 2024)...")
import urllib.parse
test_url = "https://lawgpt-backend2024.azurewebsites.net/api/query"
payload = json.dumps({
    "question": "What are the three new criminal laws that replaced the colonial-era laws in India in 2024?",
    "session_id": "deploy_verify_q15",
    "user_id": "deploy_check"
}).encode()
try:
    req = urllib.request.Request(test_url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    inner = d.get("response", d)
    answer = inner.get("answer", "") if isinstance(inner, dict) else str(inner)
    status = inner.get("status", "")
    print(f"  Status: {status}")
    print(f"  Answer preview: {answer[:500]}")
    bns_hit = "bharatiya nyaya sanhita" in answer.lower() or "bns" in answer.lower()
    print(f"  BNS mentioned: {'✓' if bns_hit else '✗'}")
    if status in ("direct", "clarification", "simple_direct"):
        print(f"  ✓ Q15 no longer blocked (was: scope-check blocking)")
    elif "couldn't find" in answer.lower() or "knowledge cutoff" in answer.lower():
        print(f"  ⚠ Q15 still blocked — scope check may not have refreshed yet")
except Exception as e:
    print(f"  ⚠ Test failed: {e}")

print("\n[DONE] Deployment complete!")
