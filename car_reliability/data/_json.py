"""JSON loading helpers for checked-in model data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_data(filename: str) -> Any:
    """Load one JSON file located next to this module."""
    path = Path(__file__).with_name(filename)
    return json.loads(path.read_text())
