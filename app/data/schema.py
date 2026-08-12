"""Schema introspection and inference for DataFrames."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ColumnInfo:
    """Metadata about a single column."""

    name: str
    dtype: str
    num_unique: int
    num_nulls: int
    min_value: Any
    max_value: Any
    mean_value: Any = None
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class SchemaInfo:
    """Schema-level summary of a DataFrame."""

    rows: int
    columns: int
    dtypes: dict[str, str]
    columns_info: dict[str, ColumnInfo]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict embedding (schema + stats) for an LLM prompt."""
        return {
            "rows": self.rows,
            "columns": self.columns,
            "dtypes": self.dtypes,
            "columns_info": {
                name: {
                    "dtype": info.dtype,
                    "num_unique": info.num_unique,
                    "num_nulls": info.num_nulls,
                    "min": _json_safe(info.min_value),
                    "max": _json_safe(info.max_value),
                    "mean": _json_safe(info.mean_value),
                    "sample_values": _json_safe(info.sample_values[:10]),
                }
                for name, info in self.columns_info.items()
            },
        }


def _json_safe(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def infer_schema(df: pd.DataFrame, sample_size: int = 10) -> SchemaInfo:
    """Infer a lightweight schema + statistics for a DataFrame.

    This is metadata only (never sampled rows for processing); it is what gets
    sent to the LLM later, so it must stay compact.
    """
    logger.info("Inferring schema for %s rows x %s cols", df.shape[0], df.shape[1])

    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    columns_info: dict[str, ColumnInfo] = {}

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        info = ColumnInfo(
            name=str(col),
            dtype=str(series.dtype),
            num_unique=int(series.nunique(dropna=True)) if len(non_null) else 0,
            num_nulls=int(series.isna().sum()),
            min_value=_json_safe(non_null.min()) if len(non_null) else None,
            max_value=_json_safe(non_null.max()) if len(non_null) else None,
            mean_value=(
                _json_safe(non_null.mean()) if non_null.dtype.kind in "fiu" else None
            ),
            sample_values=[_json_safe(v) for v in non_null.head(sample_size).tolist()],
        )
        columns_info[str(col)] = info

    return SchemaInfo(rows=df.shape[0], columns=df.shape[1], dtypes=dtypes, columns_info=columns_info)