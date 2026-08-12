"""Deterministic data profiling: statistics over a DataFrame."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.utils.helpers import to_json_safe
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnStats:
    """Statistics for one column."""

    name: str
    dtype: str
    nulls: int
    null_pct: float
    nunique: int
    min: Any = None
    max: Any = None
    mean: Any = None
    std: Any = None
    samples: list[Any] = field(default_factory=list)


@dataclass
class Profile:
    """Full dataset profile (metadata only, LLM-safe)."""

    name: str
    rows: int
    columns: int
    duplicates: int
    duplicate_pct: float
    memory_bytes: int
    column_stats: dict[str, ColumnStats]

    def to_dict(self) -> dict[str, Any]:
        """Return a compact JSON-safe dictionary for reporting / LLM input."""
        return {
            "name": self.name,
            "rows": self.rows,
            "columns": self.columns,
            "duplicates": self.duplicates,
            "duplicate_pct": round(self.duplicate_pct, 4),
            "memory_bytes": self.memory_bytes,
            "column_stats": {
                name: {
                    "dtype": s.dtype,
                    "nulls": s.nulls,
                    "null_pct": round(s.null_pct, 4),
                    "nunique": s.nunique,
                    "min": _safe(s.min),
                    "max": _safe(s.max),
                    "mean": _safe(s.mean),
                    "std": _safe(s.std),
                    "samples": _safe(s.samples[:10]),
                }
                for name, s in self.column_stats.items()
            },
        }

    def to_json(self) -> str:
        return to_json_safe(self.to_dict())


def _safe(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def profile(df: pd.DataFrame, name: str = "dataset") -> Profile:
    """Compute deterministic statistics for a DataFrame.

    Uses only vectorized pandas operations; designed to be cheap even on large
    frames because we never iterate over rows.
    """
    logger.info("Profiling %s: %s rows x %s cols", name, df.shape[0], df.shape[1])

    duplicate_mask = df.duplicated()
    n_duplicates = int(duplicate_mask.sum())
    rows = df.shape[0]
    duplicate_pct = n_duplicates / rows if rows else 0.0

    column_stats: dict[str, ColumnStats] = {}
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        nulls = int(series.isna().sum())
        col_stats = ColumnStats(
            name=str(col),
            dtype=str(series.dtype),
            nulls=nulls,
            null_pct=nulls / rows if rows else 0.0,
            nunique=int(series.nunique(dropna=True)),
            min=_safe(non_null.min()) if len(non_null) else None,
            max=_safe(non_null.max()) if len(non_null) else None,
            mean=_safe(non_null.mean()) if non_null.dtype.kind in "fiu" and len(non_null) else None,
            std=_safe(non_null.std()) if non_null.dtype.kind in "fiu" and len(non_null) else None,
            samples=[_safe(v) for v in non_null.head(6).tolist()],
        )
        column_stats[str(col)] = col_stats

    return Profile(
        name=name,
        rows=rows,
        columns=df.shape[1],
        duplicates=n_duplicates,
        duplicate_pct=duplicate_pct,
        memory_bytes=int(df.memory_usage(deep=True).sum()),
        column_stats=column_stats,
    )