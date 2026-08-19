"""
Run Pipeline Studio
====================
Starts the FastAPI backend server (backend/server.py) on port 8000.

  Backend:  http://127.0.0.1:8000  (API endpoints)
  Frontend: http://127.0.0.1:5173  (Vite React dev server)

Usage:
  1. Terminal A:  python run_studio.py
  2. Terminal B:  cd studio-react && npm run dev
     Then open:   http://localhost:5173
"""

import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  Pipeline Studio Backend - Starting on http://127.0.0.1:8000")
    print("  React Frontend dev server: cd studio-react && npm run dev")
    print("=" * 65 + "\n")
    try:
        import uvicorn
        from backend.server import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi"])
        import uvicorn
        from backend.server import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
