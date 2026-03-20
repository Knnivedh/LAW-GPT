"""
Build LAW-GPT deployment zip (excluding chroma_db, node_modules, etc.)
Output: deploy_azure.zip in project root
"""
import os, zipfile, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
ZIP  = os.path.join(ROOT, "deploy_azure.zip")

EXCLUDE_DIRS = {
    ".git", ".github", ".vscode", ".venv", "venv",
    "chroma_db_statutes", "chroma_db_hybrid", "chroma_db_cases",
    "DATA", "PERMANENT_RAG_FILES",
    "CONSUMER_DATA_COLLECTION",
    "frontend", "node_modules",
    "testsprite_tests", "TEST", "TEST_SPRIT", "tmp",
    "__pycache__", "deployment_bundle",
    "azure_logs", "azure_build_logs", "azure_latest_logs",
    "advance_rag_upcoming_idea",
    "azure_deploy_logs", ".agent", ".clinerules", ".trae",
    "results",
}

EXCLUDE_EXTS = {".pyc", ".pyo", ".bin", ".dll", ".db"}

EXCLUDE_FILES = {
    "cloudflared.exe", "cloudflared.log", "nul",
    "indian_kanoon_collection.json",
    "deploy_azure.zip", "deployment.zip",
    "deploy_package.zip", "deploy_package_light.zip",
    "deploy_package_v2.zip", "deploy_full_20260303_005019.zip",
}

added = 0
skipped = 0

print(f"Building {ZIP} ...")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Prune excluded dirs in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith("tmpclaude-")
        ]

        for fname in filenames:
            if fname in EXCLUDE_FILES:
                skipped += 1
                continue
            _, ext = os.path.splitext(fname)
            if ext in EXCLUDE_EXTS:
                skipped += 1
                continue
            if fname.endswith(".zip") or fname.endswith(".exe") or fname.endswith(".log"):
                skipped += 1
                continue

            abs_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(abs_path, ROOT).replace("\\", "/")

            # Skip any path component that is in excluded dirs
            parts = rel_path.split("/")
            if any(p in EXCLUDE_DIRS or p.startswith("tmpclaude-") for p in parts):
                skipped += 1
                continue

            try:
                zf.write(abs_path, rel_path)
                added += 1
            except Exception as e:
                print(f"  SKIP {rel_path}: {e}")
                skipped += 1

size_mb = os.path.getsize(ZIP) / (1024 * 1024)
print(f"Done: {added} files added, {skipped} skipped.")
print(f"Size: {size_mb:.1f} MB")
print(f"Path: {ZIP}")

if size_mb > 1900:
    print("ERROR: zip too large for Azure (>1900 MB)")
    sys.exit(1)

sys.exit(0)
