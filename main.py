import sys
import os
import uvicorn

# Ensure the project root is on sys.path so 'kaanoon_test' is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from kaanoon_test.advanced_rag_api_server import app  # noqa: E402

if __name__ == "__main__":
    # Azure App Service sets the PORT env var; default to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
