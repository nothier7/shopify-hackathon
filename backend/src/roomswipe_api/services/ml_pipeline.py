"""Adapter between the FastAPI app and the repository's standalone ML module."""

from pathlib import Path
import sys
from typing import Any


def recommend_room(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the ML-selected room and its budget-capped product intents."""
    repository_root = Path(__file__).resolve().parents[4]
    root = str(repository_root)
    if root not in sys.path:
        sys.path.insert(0, root)

    from ML.payload import recommend_payload

    return recommend_payload(candidates)
