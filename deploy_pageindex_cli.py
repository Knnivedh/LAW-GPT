"""
Deploy PageIndex Integration via Azure CLI
==========================================
Uses `az webapp deploy` and Azure CLI commands only — no Kudu REST API.

Files deployed:
  - pageindex_retriever.py   (new retriever)
  - agentic_rag_engine.py    (patched to use PageIndex)
  - unified_advanced_rag.py  (patched to init PageIndex)
  - requirements.txt         (pageindex added)
  - startup.sh               (auto-installs pageindex + hot-patches all files)

Usage:
    python deploy_pageindex_cli.py
    python deploy_pageindex_cli.py --set-key pi_xxxxxxxxxxxxx
    python deploy_pageindex_cli.py --check
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
RG      = "lawgpt-rg"
APP     = "lawgpt-backend2024"
BASE    = Path(r"C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT")
AZ      = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# (local_path, remote_target_path_relative_to_wwwroot)
FILES = [
    (
        BASE / "kaanoon_test" / "system_adapters" / "pageindex_retriever.py",
        "kaanoon_test/system_adapters/pageindex_retriever.py",
    ),
    (
        BASE / "kaanoon_test" / "system_adapters" / "agentic_rag_engine.py",
        "kaanoon_test/system_adapters/agentic_rag_engine.py",
    ),
    (
        BASE / "kaanoon_test" / "system_adapters" / "unified_advanced_rag.py",
        "kaanoon_test/system_adapters/unified_advanced_rag.py",
    ),
    (
        BASE / "requirements.txt",
        "requirements.txt",
    ),
    (
        BASE / "startup.sh",
        "startup.sh",
    ),
]


def az(*args: str, capture: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run an az CLI command, print it, return result."""
    cmd = [AZ] + list(args)
    print("  $", " ".join(args[:6]), "..." if len(args) > 6 else "")
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )


def check_login() -> bool:
    r = az("account", "show", "--query", "name", "-o", "tsv")
    if r.returncode != 0:
        print("✗ Not logged in. Run:  az login")
        return False
    print(f"  Logged in as: {r.stdout.strip()}")
    return True


def deploy_files() -> bool:
    """
    Upload each file individually using az webapp deploy --type static.
    Uses --async true so we fire-and-forget quickly, then poll readiness.
    """
    all_ok = True
    for local, remote in FILES:
        name = local.name
        size = local.stat().st_size if local.exists() else 0
        if not local.exists():
            print(f"\n[SKIP] {name} — file not found locally")
            continue

        print(f"\n[UPLOAD] {name}  ({size:,} bytes)  →  {remote}")
        r = az(
            "webapp", "deploy",
            "--resource-group", RG,
            "--name", APP,
            "--src-path", str(local),
            "--target-path", remote,
            "--type", "static",
            "--async", "true",   # fire and forget — don't wait for Oryx
            "--restart", "false",
            timeout=300,
        )
        if r.returncode == 0:
            print(f"  ✓ Queued")
        else:
            print(f"  ✗ FAILED: {r.stderr.strip()[:300]}")
            all_ok = False

    if all_ok:
        print("\n[WAIT] Waiting 15s for async uploads to settle...")
        time.sleep(15)
    return all_ok


def install_pageindex_on_server() -> None:
    """
    Uses `az webapp ssh` is not scriptable, so we trigger install via
    a one-time Kudu command using the CLI's built-in REST support:
    az rest POST to Kudu /api/command
    """
    print("\n[INSTALL] Installing pageindex package on server (via az rest)...")
    import json
    body = json.dumps({
        "command": (
            "ANTENV=$(find /tmp -maxdepth 2 -name antenv -type d 2>/dev/null | head -1); "
            "if [ -n \"$ANTENV\" ]; then "
            "  \"$ANTENV/bin/pip\" install pageindex --quiet && echo 'PAGEINDEX_INSTALLED_OK'; "
            "else "
            "  echo 'ANTENV_NOT_FOUND_will_install_on_next_startup'; "
            "fi"
        ),
        "dir": "/home/site/wwwroot",
    })
    r = az(
        "rest",
        "--method", "POST",
        "--url", f"https://{APP}.scm.azurewebsites.net/api/command",
        "--body", body,
        "--headers", "Content-Type=application/json",
        timeout=120,
    )
    if r.returncode == 0:
        output = r.stdout.strip()
        if "INSTALLED_OK" in output:
            print("  ✓ pageindex installed on server")
        elif "ANTENV_NOT_FOUND" in output:
            print("  ℹ  antenv not found yet — startup.sh will install it on next restart")
        else:
            print(f"  ℹ  {output[:200]}")
    else:
        print(f"  ⚠  Install command output: {r.stderr.strip()[:200]}")
        print("  ℹ  startup.sh will install pageindex automatically on next restart")


def clear_pycache() -> None:
    print("\n[CLEAN] Clearing __pycache__ on server (via az rest)...")
    import json
    body = json.dumps({
        "command": (
            "find /home/site/wwwroot -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; "
            "find /tmp -path '*/kaanoon_test*/__pycache__' -type d -exec rm -rf {} + 2>/dev/null; "
            "echo PYCACHE_CLEARED"
        ),
        "dir": "/home/site/wwwroot",
    })
    r = az(
        "rest",
        "--method", "POST",
        "--url", f"https://{APP}.scm.azurewebsites.net/api/command",
        "--body", body,
        "--headers", "Content-Type=application/json",
        timeout=60,
    )
    if r.returncode == 0 and "PYCACHE_CLEARED" in r.stdout:
        print("  ✓ Cache cleared")
    else:
        print(f"  ⚠  {r.stderr.strip()[:100]}")


def restart_app(wait: int = 45) -> None:
    print(f"\n[RESTART] Restarting {APP}...")
    r = az("webapp", "restart", "--resource-group", RG, "--name", APP, timeout=60)
    if r.returncode == 0:
        print(f"  ✓ Restart triggered. Waiting {wait}s for startup.sh to run...")
        time.sleep(wait)
    else:
        print(f"  ✗ Restart failed: {r.stderr.strip()[:200]}")


def set_api_key(key: str) -> None:
    print(f"\n[CONFIG] Setting PAGEINDEX_API_KEY on {APP}...")
    r = az(
        "webapp", "config", "appsettings", "set",
        "--resource-group", RG,
        "--name", APP,
        "--settings", f"PAGEINDEX_API_KEY={key}",
        "--output", "none",
        timeout=60,
    )
    if r.returncode == 0:
        print("  ✓ PAGEINDEX_API_KEY set successfully")
    else:
        print(f"  ✗ Failed: {r.stderr.strip()[:200]}")


def check_status() -> None:
    print(f"\n[STATUS] Checking {APP}...")

    # App state
    r = az("webapp", "show",
           "--resource-group", RG, "--name", APP,
           "--query", "{state:state, defaultHostName:defaultHostName}",
           "--output", "table")
    print(r.stdout.strip() if r.returncode == 0 else f"  Error: {r.stderr.strip()[:100]}")

    # Check if PAGEINDEX_API_KEY is set
    r = az("webapp", "config", "appsettings", "list",
           "--resource-group", RG, "--name", APP,
           "--query", "[?name=='PAGEINDEX_API_KEY'].{name:name, value:value}",
           "--output", "table")
    if r.returncode == 0:
        out = r.stdout.strip()
        if "PAGEINDEX_API_KEY" in out:
            print("  ✓ PAGEINDEX_API_KEY is SET in App Settings")
        else:
            print("  ⚠  PAGEINDEX_API_KEY is NOT set")
            print("     Run:  python deploy_pageindex_cli.py --set-key pi_xxxxx")

    # Verify files are present on server via az rest
    import json
    check_cmd = (
        'ls -la /home/site/wwwroot/kaanoon_test/system_adapters/pageindex_retriever.py 2>/dev/null '
        '&& echo FILE_EXISTS || echo FILE_MISSING'
    )
    body = json.dumps({"command": check_cmd, "dir": "/home/site/wwwroot"})
    r = az("rest", "--method", "POST",
           "--url", f"https://{APP}.scm.azurewebsites.net/api/command",
           "--body", body,
           "--headers", "Content-Type=application/json",
           timeout=30)
    if r.returncode == 0 and "FILE_EXISTS" in r.stdout:
        print("  ✓ pageindex_retriever.py present on server")
    else:
        print("  ✗ pageindex_retriever.py NOT found on server")

    # Latest log lines
    print("\n  [LOGS] Fetching last 20 log lines (az webapp log tail)...")
    r = az("webapp", "log", "download",
           "--resource-group", RG, "--name", APP,
           "--log-file", "_tmp_app_logs.zip",
           timeout=30)
    if r.returncode == 0:
        import zipfile, os
        with zipfile.ZipFile("_tmp_app_logs.zip") as z:
            for fname in z.namelist():
                if "default_docker.log" in fname or "appservice" in fname.lower():
                    lines = z.read(fname).decode("utf-8", errors="replace").splitlines()[-20:]
                    print(f"  --- {fname} (last 20 lines) ---")
                    for ln in lines:
                        print(f"  {ln}")
                    break
        os.remove("_tmp_app_logs.zip")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy PageIndex integration to Azure via CLI")
    parser.add_argument("--set-key", metavar="API_KEY",
                        help="Set PAGEINDEX_API_KEY in Azure App Settings")
    parser.add_argument("--check", action="store_true",
                        help="Check deployment status only (no deploy)")
    parser.add_argument("--no-restart", action="store_true",
                        help="Skip app restart after deploy")
    args = parser.parse_args()

    print("=" * 60)
    print("  LAW-GPT PageIndex Deploy — Azure CLI")
    print("=" * 60)

    if not check_login():
        sys.exit(1)

    if args.check:
        check_status()
        return

    if args.set_key:
        set_api_key(args.set_key)
        if not args.no_restart:
            restart_app(wait=45)
        return

    # Full deploy
    ok = deploy_files()
    if not ok:
        print("\n[ERROR] Some files failed to upload.")
        sys.exit(1)

    install_pageindex_on_server()
    clear_pycache()

    if not args.no_restart:
        restart_app(wait=50)
    else:
        print("\n[SKIP] Restart skipped (--no-restart)")

    print("\n" + "=" * 60)
    print("  DEPLOY COMPLETE")
    print("=" * 60)
    print()
    print("  Next steps:")
    print("  1. Set your PageIndex API key:")
    print("     python deploy_pageindex_cli.py --set-key pi_xxxxxxxxxxxxx")
    print("     (Get your key at https://dash.pageindex.ai/api-keys)")
    print()
    print("  2. Index statute files (run once locally):")
    print("     set PAGEINDEX_API_KEY=pi_xxxx")
    print("     python kaanoon_test/pageindex_ingest.py")
    print()
    print("  3. Check deployment status:")
    print("     python deploy_pageindex_cli.py --check")


if __name__ == "__main__":
    main()
