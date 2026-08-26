"""
api/index.py — Vercel serverless entry point.

Vercel's @vercel/python builder looks for an `app` variable here.
We ensure the project root is on sys.path so that `from backend.xxx`
imports work correctly in the serverless environment.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `from backend.xxx` works.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.main import app  # noqa: E402, F401 — re-export for Vercel
