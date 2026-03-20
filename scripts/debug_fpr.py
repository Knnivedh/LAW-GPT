"""Debug FPR-01 and FPR-03 responses from localhost."""
import urllib.request, json

BASE = "http://localhost:8000"

def ask(q):
    payload = json.dumps({"question": q, "session_id": "debug", "user_id": "debugger"}).encode()
    req = urllib.request.Request(BASE + "/api/query", data=payload,
                                  headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=90)
    d = json.loads(r.read())
    inner = d.get("response", d)
    ans = inner.get("answer", str(inner)) if isinstance(inner, dict) else str(inner)
    return ans

# ── FPR-01 ─────────────────────────────────────────────────────────────────
print("=== FPR-01: BNS commencement date ===")
a1 = ask("On exactly what date did the Bharatiya Nyaya Sanhita, 2023 come into force?").lower()
for kw in ["july 2024", "1 july", "1st july", "bns", "bharatiya nyaya sanhita"]:
    hit = kw in a1
    print(f"  [{'OK' if hit else 'MISS'}] {kw!r}")
print("ANSWER:", a1[:600])
print()

# ── FPR-03 ─────────────────────────────────────────────────────────────────
print("=== FPR-03: Three new criminal laws ===")
a3 = ask(
    "What are the three new criminal laws that replaced India's colonial-era criminal laws in 2024?"
).lower()
for kw in ["bns", "bnss", "bsa", "bharatiya nyaya sanhita",
           "bharatiya nagarik suraksha sanhita", "bharatiya sakshya"]:
    hit = kw in a3
    print(f"  [{'OK' if hit else 'MISS'}] {kw!r}")
print("ANSWER:", a3[:700])
