"""Small shared helpers."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def json_default(obj: Any) -> Any:
    """JSON encoder fallback for pandas/numpy/datetime values."""
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json_safe(obj: Any) -> str:
    """Serialize an object to a compact, safe JSON string."""
    return json.dumps(obj, default=json_default, ensure_ascii=False)


def ensure_dir(path: str | Path) -> Path:
    """Create a directory (recursively) if missing."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def human_number(value: float | int) -> str:
    """Format an integer number with thousand separators."""
    return f"{int(round(value)):,}"