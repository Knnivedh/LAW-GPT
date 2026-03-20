"""
Quick diagnostic + fix for PageIndex tree generation.
Tests API keys, finds the working one, and generates all trees.
"""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(str(ROOT / "config" / ".env"))

print("=" * 60)
print("PageIndex Tree Builder - API Diagnostics")
print("=" * 60)

# Test all available API keys with correct model names
providers = [
    ("Groq", os.getenv("groq_api"), "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    ("Cerebras", os.getenv("cerebras_api"), "https://api.cerebras.ai/v1", "qwen-3-235b-a22b-instruct-2507"),
]

working_provider = None

for name, key, url, model in providers:
    if not key:
        print(f"  {name}: NO KEY FOUND")
        continue
    print(f"\n  Testing {name} ({model})...")
    print(f"    Key: {key[:10]}...{key[-5:]}")
    print(f"    URL: {url}")
    try:
        import openai
        c = openai.OpenAI(api_key=key, base_url=url)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
            timeout=15,
        )
        resp = r.choices[0].message.content
        print(f"    RESULT: {resp}")
        print(f"    STATUS: ✅ WORKING!")
        working_provider = (name, key, url, model)
        break
    except Exception as e:
        print(f"    STATUS: ❌ FAILED - {e}")

if not working_provider:
    print("\n❌ No working API provider found! Cannot generate trees.")
    sys.exit(1)

pname, pkey, purl, pmodel = working_provider
print(f"\n✅ Using: {pname} ({pmodel})")

# Hardcode the working credentials directly into utils.py
utils_path = ROOT / "PageIndex" / "pageindex" / "utils.py"
utils_content = utils_path.read_text(encoding="utf-8")

new_lines = []
for line in utils_content.split("\n"):
    if line.strip().startswith("CEREBRAS_API_KEY") and "=" in line and ("os.getenv" in line or '"csk' in line):
        new_lines.append(f'CEREBRAS_API_KEY = "{pkey}"')
    elif line.strip().startswith("CEREBRAS_BASE_URL") and "=" in line:
        new_lines.append(f'CEREBRAS_BASE_URL = "{purl}"')
    else:
        new_lines.append(line)

utils_path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"  Patched utils.py with hardcoded {pname} credentials")

# Also update the model in build_pageindex_trees_local.py
builder_path = ROOT / "build_pageindex_trees_local.py"
builder_content = builder_path.read_text(encoding="utf-8")
builder_content = builder_content.replace(
    'GROQ_MODEL = "llama-3.3-70b"',
    f'GROQ_MODEL = "{pmodel}"'
)
builder_path.write_text(builder_content, encoding="utf-8")
print(f"  Patched build_pageindex_trees_local.py with model: {pmodel}")

# Clean old trees
import glob
old_trees = glob.glob(str(ROOT / "PERMANENT_RAG_FILES" / "PAGEINDEX_TREES" / "*_tree.json"))
for t in old_trees:
    os.remove(t)
    print(f"  Removed old tree: {os.path.basename(t)}")

# Now run the tree builder
print(f"\n{'=' * 60}")
print("Starting tree generation for all statutes...")
print(f"{'=' * 60}")

# Add PageIndex to path
sys.path.insert(0, str(ROOT / "PageIndex"))

# Force reimport of utils with new values
for mod_name in list(sys.modules.keys()):
    if "pageindex" in mod_name:
        del sys.modules[mod_name]

from build_pageindex_trees_local import process_all_statutes
process_all_statutes()
