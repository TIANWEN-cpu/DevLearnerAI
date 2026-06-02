"""Backward-compatible shim -- all logic has moved to app/ai/.

This module re-exports every public name so that existing imports like
``from app.ai_mentor import AIMentorDock, AIMentorPanel`` continue to work
unchanged.  New code should import directly from ``app.ai`` submodules.
"""

from app.ai.chat_handler import AIMentorDock, AIMentorPanel  # noqa: F401

__all__ = [
    "AIMentorPanel",
    "AIMentorDock",
]
