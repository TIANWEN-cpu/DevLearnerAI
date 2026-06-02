"""Shared fixtures for DevLearnerAI tests."""

import sys
from pathlib import Path

# Ensure the project root is importable so `from app import ...` works
# regardless of how pytest is invoked.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
