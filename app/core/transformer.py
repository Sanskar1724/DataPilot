"""Safe, deterministic transformations.

Never executes arbitrary code. A transformation is selected from a fixed
registry by name and applied with validated arguments; anything unknown is a
hard error. This is the "Deterministic Execution" step of the architecture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

TTransform = Callable[[pd.DataFrame, str | None, dict[str, Any]], pd.DataFrame]


class UnknownTransformationError(ValueError):
    """Raised when a transformation name is not in the registry."""


@dataclass
class FixPlan:
    """A validated list of transformations to apply in order."""

    steps: list["TransformStep"] = field(default_factory=list)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        for step in self.steps:
            logger.info("Applying transformation '%s' on %s", step.name, step.column or "-")
            result = step.apply(result)
        return result


@dataclass
class TransformStep:
    """One transformation: name + optional column + args."""

    name: str
    column: str | None = None
    args: dict[str, Any] = field(default_factory=dict)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        fn = get_transformation(self.name)
        return fn(df, self.column, self.args)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "column": self.column, "args": self.args}


# --------------------------------------------------------------------------- #
# Transformations (registry)
# --------------------------------------------------------------------------- #


def _drop_duplicates(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    subset = args.get("subset") or None
    return df.drop_duplicates(subset=subset).reset_index(drop=True)


def _fill_missing(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    col = _require_column(df, column)
    strategy = args.get("strategy", "drop")
    if strategy == "drop":
        return df.dropna(subset=[col]).reset_index(drop=True)
    if strategy == "constant":
        fill_value = args["value"]
        if args.get("cast"):
            fill_value = _cast(fill_value, str(df[col].dtype))
        df[col] = df[col].fillna(fill_value)
        return df
    if strategy == "mean":
        df[col] = df[col].fillna(pd.to_numeric(df[col], errors="coerce").mean())
        return df
    if strategy == "median":
        df[col] = df[col].fillna(pd.to_numeric(df[col], errors="coerce").median())
        return df
    if strategy == "mode":
        series = df[col]
        mode = series.mode(dropna=True)
        if not mode.empty:
            df[col] = series.fillna(mode.iloc[0])
        return df
    if strategy == "fwd":
        return df.assign(**{col: df[col].ffill()})
    if strategy == "bwd":
        return df.assign(**{col: df[col].bfill()})
    raise UnknownTransformationError(f"Unknown fill strategy '{strategy}'")


def _standardize_dates(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    col = _require_column(df, column)
    series = df[col]
    if not pd.api.types.is_datetime64_any_dtype(series):
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.isna().mean() > 0.3:  # pandas>=3 defaults to ISO8601 only
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        series = parsed
    df[col] = series
    return df


def _clip_negatives(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    return _numeric_transform(df, column, lambda s: s.clip(lower=0))


def _flag_negatives(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    flag_col = args.get("flag_column", f"{column}_negative_flag")
    df[flag_col] = (pd.to_numeric(df[column], errors="coerce") < 0).astype(int)
    return df


def _standardize_strings(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    col = _require_column(df, column)
    mode = args.get("mode", "strip")
    series = df[col].astype("string")
    if mode == "strip":
        series = series.str.strip()
    elif mode == "lower":
        series = series.str.strip().str.lower()
    elif mode == "title":
        series = series.str.strip().str.title()
    df[col] = series
    return df


_NUMERIC_SENTINELS = {
    "error",
    "unknown",
    "n/a",
    "na",
    "none",
    "null",
    "nul",
    "-",
}


def _parse_numeric(df: pd.DataFrame, column: str | None, args: dict[str, Any]) -> pd.DataFrame:
    """Parse a column stored as messy strings into a proper numeric dtype.

    Sentinel tokens (ERROR, UNKNOWN, N/A, -, ...) become null and can then be
    handled by fill_missing. Cleaning is done from raw strings only; already
    numeric columns are left untouched.
    """
    col = _require_column(df, column)
    series = df[col]

    if pd.api.types.is_numeric_dtype(series):
        return df

    text = series.astype("string").str.strip()
    tokens_to_nan = (
        f'({")|(".join(re.escape(t) for t in sorted(_NUMERIC_SENTINELS))})'
    )
    text = text.str.replace(
        tokens_to_nan, "", case=False, regex=True, flags=re.IGNORECASE
    )

    parsed = pd.to_numeric(text, errors="coerce")
    mode = args.get("errors", "coerce")
    if mode == "drop":
        df = df[parsed.notna()].reset_index(drop=True)
        parsed = parsed[parsed.notna()]
    df[col] = parsed
    return df


def _numeric_transform(
    df: pd.DataFrame, column: str | None, fn: Callable[[pd.Series], pd.Series]
) -> pd.DataFrame:
    col = _require_column(df, column)
    df[col] = fn(pd.to_numeric(df[col], errors="coerce"))
    return df


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

TRANSFORMATIONS: dict[str, TTransform] = {
    "drop_duplicates": _drop_duplicates,
    "fill_missing": _fill_missing,
    "standardize_dates": _standardize_dates,
    "parse_numeric": _parse_numeric,
    "clip_negatives": _clip_negatives,
    "flag_negatives": _flag_negatives,
    "standardize_strings": _standardize_strings,
}


def get_transformation(name: str) -> TTransform:
    if name not in TRANSFORMATIONS:
        raise UnknownTransformationError(
            f"Unknown transformation '{name}'. Available: "
            f"{', '.join(sorted(TRANSFORMATIONS))}"
        )
    return TRANSFORMATIONS[name]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _require_column(df: pd.DataFrame, column: str | None) -> str:
    if not column or column not in df.columns:
        raise UnknownTransformationError(
            f"Column '{column}' does not exist or was not provided"
        )
    return column


def _cast(value: Any, dtype: str) -> Any:
    try:
        if "int" in dtype:
            return int(value)
        if "float" in dtype:
            return float(value)
        if "bool" in dtype or "bool" in str(type(value)).lower():
            return bool(value)
    except (TypeError, ValueError):
        pass
    return value