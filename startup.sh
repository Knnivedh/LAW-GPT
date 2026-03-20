#!/bin/bash
# LAW-GPT Hot-Patch Startup Script
# Copies updated .py files from wwwroot to the Oryx-extracted temp dir
# Oryx has already activated the venv before this script runs

echo "[HOTPATCH] Starting..."

ANTENV=$(find /tmp -maxdepth 2 -name antenv -type d 2>/dev/null | head -1)
if [ -n "$ANTENV" ]; then
    EDIR=$(dirname "$ANTENV")
    echo "[HOTPATCH] Found extracted dir: $EDIR"

    # ── Install pageindex package if not already present ─────────────────
    if ! "$ANTENV/bin/python" -c "import pageindex" 2>/dev/null; then
        echo "[HOTPATCH] Installing pageindex package..."
        "$ANTENV/bin/pip" install pageindex --quiet && echo "[HOTPATCH] pageindex installed OK" || echo "[HOTPATCH] pageindex install failed (graceful degradation active)"
    else
        echo "[HOTPATCH] pageindex already installed"
    fi

    if [ -d "$EDIR/kaanoon_test/system_adapters" ]; then
        cp /home/site/wwwroot/kaanoon_test/system_adapters/clarification_engine.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched clarification_engine.py"
        cp /home/site/wwwroot/kaanoon_test/system_adapters/clarification_prompts.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched clarification_prompts.py"
        cp /home/site/wwwroot/kaanoon_test/system_adapters/pageindex_retriever.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched pageindex_retriever.py"
        cp /home/site/wwwroot/kaanoon_test/system_adapters/agentic_rag_engine.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched agentic_rag_engine.py"
        cp /home/site/wwwroot/kaanoon_test/system_adapters/persistent_memory.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched persistent_memory.py"
        cp /home/site/wwwroot/kaanoon_test/system_adapters/unified_advanced_rag.py "$EDIR/kaanoon_test/system_adapters/" 2>/dev/null && echo "[HOTPATCH] Patched unified_advanced_rag.py"
        # Also patch advanced_rag_api_server.py (contains session management logic)
        cp /home/site/wwwroot/kaanoon_test/advanced_rag_api_server.py "$EDIR/kaanoon_test/" 2>/dev/null && echo "[HOTPATCH] Patched advanced_rag_api_server.py"
        find "$EDIR" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
        echo "[HOTPATCH] Cleared __pycache__"
    fi
else
    echo "[HOTPATCH] No extracted dir found, running from wwwroot"
fi

# ── Clear stale Python bytecache from previous deployments ───────────────────
echo "[HOTPATCH] Clearing stale __pycache__ in wwwroot..."
find /home/site/wwwroot -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find /home/site/wwwroot -name "*.pyc" -delete 2>/dev/null || true
echo "[HOTPATCH] Bytecache cleared."

# ── Restore runtime dependencies on App Service ─────────────────────────────
echo "[HOTPATCH] Installing Python runtime dependencies from requirements.txt..."
python3 -m pip install --no-cache-dir -r /home/site/wwwroot/requirements.txt || {
    echo "[HOTPATCH] requirements install failed"
    exit 1
}
echo "[HOTPATCH] Runtime packages installed"

# ── Diagnostic: verify deployed unified_advanced_rag.py has simple_mode ──────
python3 -c "
import sys; sys.path.insert(0, '/home/site/wwwroot')
try:
    import inspect
    from kaanoon_test.system_adapters.unified_advanced_rag import UnifiedAdvancedRAG
    sig = str(inspect.signature(UnifiedAdvancedRAG.query))
    has_sm = 'simple_mode' in sig
    print(f'[DIAG] unified_rag file: {UnifiedAdvancedRAG.__module__}')
    print(f'[DIAG] query sig: {sig[:120]}')
    print(f'[DIAG] HAS simple_mode: {has_sm}')
except Exception as ex:
    print(f'[DIAG] Error: {ex}')
" 2>&1 || true

echo "[HOTPATCH] Starting gunicorn on port ${PORT:-8000}..."
# Single worker: clarification sessions are stored in-process memory;
# multiple workers would lose sessions across requests hitting different workers.
# UvicornWorker handles async concurrency internally (event-loop), so -w 1 is sufficient.
exec python3 -m gunicorn -w 1 -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8000}" --timeout 600 --chdir /home/site/wwwroot main:app