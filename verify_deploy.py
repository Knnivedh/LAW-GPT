import requests, json, time

BASE = "https://lawgpt-backend2024.azurewebsites.net"

tests = [
    ("bail",        "What does bail mean in Indian law?"),
    ("fir",         "What is a first information report in India?"),
    ("s302",        "What is IPC Section 302 punishment for murder?"),
    ("consumer",    "Who can file a consumer complaint in India?"),
    ("hindi-fir",   "fir kya hota hai bro, FIR matlab kya hai Indian law mein"),
    ("hindi-498a",  "498a IPC husband cruelty kya hota hai"),
]

for tid, q in tests:
    sid = f"verify-{tid}-{int(time.time())}"
    r = requests.post(f"{BASE}/api/query", json={"question": q, "session_id": sid}, timeout=120)
    d = r.json()["response"]
    wc = len(d["answer"].split())
    qt = d["system_info"].get("query_type", "?")
    fc = d.get("from_cache", False)
    ok = "OK" if wc >= 50 else "FAIL(short)"
    error = "ERROR(stub)" if "unable to generate" in d["answer"].lower() else ""
    print(f"{tid:12s}  {ok}  words={wc:4d}  type={qt}  cache={fc}  {error}")
    print(f"  >> {d['answer'][:120]}")
    time.sleep(5)

print("\nDone.")
