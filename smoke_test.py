"""Quick smoke test for deployed simple_mode fixes."""
import requests, time, json

BASE = "https://lawgpt-backend2024.azurewebsites.net"

tests = [
    ("What is bail in Indian law?", "st-b01"),
    ("FIR kya hota h?", "st-h01"),
    ("What is FIR?", "st-f01"),
]

for q, sid in tests:
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/query", json={"question": q, "session_id": sid}, timeout=90)
        d = r.json()
        resp = d.get("response", d)
        ans = resp.get("answer", "")
        qtype = resp.get("system_info", {}).get("query_type", "?")
        elapsed = round(time.time() - t0, 1)
        words = len(ans.split())
        stub = "unable to generate" in ans.lower() or words < 30
        print(f"[{'STUB' if stub else 'OK':4s}] {elapsed:5.1f}s | {words:4d}w | {qtype:18s} | {q[:45]}")
        if stub:
            print(f"       -> {ans[:150]}")
    except Exception as e:
        print(f"[ERR ] {round(time.time()-t0,1):5.1f}s | {q[:45]} -> {e}")
    time.sleep(3)
