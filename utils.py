"""Utility helpers used across the application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

PRESET_DIR = Path(".streamlit/score_presets")
PRESET_DIR.mkdir(parents=True, exist_ok=True)


def save_preset(
    name: str,
    weights_pillars: Dict[str, float],
    weights_core: Dict[str, float],
    filters: Dict[str, float],
) -> None:
    """Save preset ``name`` containing weights and filters.

    The preset is stored as a single JSON object with three keys:
    ``weights_pillars``, ``weights_core`` and ``filters``.
    """
    path = PRESET_DIR / f"{name}.json"
    data = {
        "weights_pillars": weights_pillars,
        "weights_core": weights_core,
        "filters": filters,
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def load_preset(name: str) -> Dict[str, Dict[str, float]]:
    """Load a preset by ``name``.

    Returns an empty dictionary if the preset does not exist.
    """
    path = PRESET_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
