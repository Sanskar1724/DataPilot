"""Deterministic validation: quality rules run against a DataFrame.

Every detector is vectorized (no row iteration) and returns a list of
QualityIssue objects. This module is where the "Quality Engine" rules live.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import pandas as pd

from app.utils.helpers import to_json_safe
from app.utils.logger import get_logger

logger = get_logger(__name__)

Severity = Literal["low", "medium", "high"]


@dataclass
class QualityIssue:
    """A single detected data-quality problem."""

    column: str | None
    problem: str
    severity: Severity
    count: int
    pct: float
    detail: str = ""
    samples: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "problem": self.problem,
            "severity": self.severity,
            "count": self.count,
            "pct": round(self.pct, 4),
            "detail": self.detail,
            "samples": [str(s) for s in self.samples[:10]],
        }

    def to_json(self) -> str:
        return to_json_safe(self.to_dict())


def _samples(series: pd.Series, mask: pd.Series, n: int = 10) -> list[Any]:
    return series[mask].dropna().head(n).tolist()


def _base_issue(
    column: str,
    problem: str,
    severity: Severity,
    count: int,
    rows: int,
    detail: str,
    samples: list[Any],
) -> QualityIssue:
    return QualityIssue(
        column=column,
        problem=problem,
        severity=severity,
        count=int(count),
        pct=count / rows if rows else 0.0,
        detail=detail,
        samples=samples,
    )


# --------------------------------------------------------------------------- #
# Detectors
# --------------------------------------------------------------------------- #


def detect_missing_values(df: pd.DataFrame, threshold: float = 0.0) -> list[QualityIssue]:
    """Flag any column with missing values (rate above threshold)."""
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    for col in df.columns:
        null_mask = df[col].isna()
        count = int(null_mask.sum())
        if count and count / rows > threshold:
            issues.append(
                _base_issue(
                    str(col),
                    "missing_values",
                    "high" if count / rows > 0.2 else ("medium" if count / rows > 0.05 else "low"),
                    count,
                    rows,
                    f"{count} missing ({count / rows:.1%})",
                    _samples(df[col], null_mask),
                )
            )
    return issues


def detect_duplicates(df: pd.DataFrame) -> list[QualityIssue]:
    """Flag exact duplicate rows."""
    mask = df.duplicated(keep="first")
    count = int(mask.sum())
    if not count:
        return []
    return [
        _base_issue(
            None,
            "duplicate_rows",
            "medium" if count / df.shape[0] > 0.1 else "low",
            count,
            df.shape[0],
            f"{count} duplicate rows ({count / df.shape[0]:.1%})",
            [],
        )
    ]


def detect_negatives(df: pd.DataFrame, numeric_cols: list[str] | None = None) -> list[QualityIssue]:
    """Flag negative values in logical non-negative numeric columns.

    Only checks columns whose name hints negativity is impossible
    (count, qty, amount, revenue, price, total, cost, age, ...) or that the
    user explicitly whitelists via numeric_cols.
    """
    hints = ("count", "qty", "quantity", "amount", "revenue", "price", "total", "cost", "age", "unit")
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    candidates = numeric_cols or [
        col
        for col in df.columns
        if any(h in str(col).lower() for h in hints) and pd.api.types.is_numeric_dtype(df[col])
    ]
    for col in candidates:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        mask = series < 0
        count = int(mask.sum())
        if count:
            issues.append(
                _base_issue(
                    str(col),
                    "negative_values",
                    "high",
                    count,
                    rows,
                    f"{count} negative values ({count / rows:.1%})",
                    _samples(series, mask),
                )
            )
    return issues


def _date_signature(value: str) -> str:
    """Normalize a date-ish string to a format signature.

    Digits become 'N', the rest stays (separators, letters). Used to detect
    mixed date formats regardless of the exact values.
    """
    import re as _re

    return _re.sub(r"[0-9]+", "N", value.strip())


def detect_dates(df: pd.DataFrame, min_share: float = 0.005) -> list[QualityIssue]:
    """Flag columns that look like dates but mix several formats.

    Heuristic: for non-datetime columns whose name hints a date, build a
    format signature per non-null value and parse-check each one. If several
    distinct signatures are substantially present, the column is inconsistent.
    """
    date_hints = ("date", "time", "day", "month", "year", "created", "updated", "timestamp")
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    for col in df.columns:
        lowered = str(col).lower()
        if not any(h in lowered for h in date_hints):
            continue
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            continue

        strings = non_null.astype(str)
        uniques = strings.drop_duplicates()

        # Evaluate format signatures on unique values only, so the cost scales
        # with cardinality, not with the number of rows.
        uniq_sig = {}
        for value in uniques.astype(object).head(5000).tolist():
            try:
                pd.to_datetime(value)
                uniq_sig[value] = _date_signature(str(value))
            except (ValueError, TypeError):
                uniq_sig[value] = "unparseable:" + _date_signature(str(value))

        if len(set(uniq_sig.values())) < 2:
            continue

        signatures = strings.map(uniq_sig)
        seen = set(signatures)
        if len(seen) < 2:
            continue

        sig_counts = signatures.value_counts().to_dict()
        dominant = max(sig_counts, key=sig_counts.get)
        if sig_counts[dominant] / rows >= (1.0 - min_share):
            continue  # one format dominates (~consistent)

        bad_mask = signatures != dominant
        bad = strings[bad_mask].tolist()
        count = int(bad_mask.sum())
        if not count:
            continue
        issues.append(
            _base_issue(
                str(col),
                "inconsistent_date_formats",
                "medium",
                count,
                rows,
                f"{count} values don't match dominant format '{dominant}' ({count / rows:.1%})",
                bad[:10],
            )
        )
    return issues


def detect_constant_columns(df: pd.DataFrame) -> list[QualityIssue]:
    """Flag columns where every row has the same value (no cardinality)."""
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    for col in df.columns:
        nunique = df[col].nunique(dropna=True)
        if nunique <= 1:
            issues.append(
                _base_issue(
                    str(col),
                    "constant_column",
                    "low",
                    rows,
                    rows,
                    "column has a single distinct value",
                    list(df[col].dropna().unique())[:5],
                )
            )
    return issues


def detect_outliers(df: pd.DataFrame, zscore_threshold: float = 5.0) -> list[QualityIssue]:
    """Flag numeric columns with values far outside the mean (robust z-score)."""
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce")
        if not pd.api.types.is_numeric_dtype(series):
            continue
        non_null = series.dropna()
        if len(non_null) < 10:
            continue
        median = non_null.median()
        mad = (non_null - median).abs().median()
        if mad == 0 or pd.isna(mad):
            std = non_null.std()
            if std == 0 or pd.isna(std):
                continue
            z = (non_null - non_null.mean()) / std
            mask = z.abs() > zscore_threshold
        else:
            robust_z = 0.6745 * (non_null - median) / mad
            mask = robust_z.abs() > zscore_threshold
        count = int(mask.sum())
        if count:
            issues.append(
                _base_issue(
                    str(col),
                    "outliers",
                    "medium",
                    count,
                    rows,
                    f"{count} values exceed robust z-score of {zscore_threshold}",
                    _samples(series, mask),
                )
            )
    return issues


# Sentinel strings commonly used in place of a real number.


def detect_non_numeric_strings(df: pd.DataFrame) -> list[QualityIssue]:
    """Flag text values living inside columns that should be numeric.

    Heuristic: columns whose name hints a number (price, total, qty, amount,
    units, revenue, cost, spent, ...) but that contain non-numeric strings
    such as 'ERROR', 'UNKNOWN', 'N/A', '-'.
    """
    hints = ("price", "total", "qty", "quantity", "amount", "revenue", "cost", "spent", "count", "unit", "fee", "rating")
    issues: list[QualityIssue] = []
    rows = df.shape[0]
    for col in df.columns:
        lowered = str(col).lower()
        if not any(h in lowered for h in hints):
            continue
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            continue
        non_null = series.dropna().astype("string").str.strip()
        if non_null.empty:
            continue
        parsed = pd.to_numeric(non_null, errors="coerce")
        bad_mask = parsed.isna()
        if not bad_mask.any():
            continue
        bad = non_null[bad_mask].tolist()
        count = bad_mask.sum()
        issues.append(
            _base_issue(
                str(col),
                "non_numeric_strings",
                "medium",
                count,
                rows,
                f"{count} values are non-numeric strings e.g. {sorted(set(bad))[:4]} ({count / rows:.1%})",
                bad[:10],
            )
        )
    return issues


# --------------------------------------------------------------------------- #
# Registry / orchestrator
# --------------------------------------------------------------------------- #

Detector = Callable[[pd.DataFrame], list[QualityIssue]]

DETECTORS: list[Detector] = [
    detect_missing_values,
    detect_duplicates,
    detect_negatives,
    detect_dates,
    detect_constant_columns,
    detect_outliers,
    detect_non_numeric_strings,
]


def validate(df: pd.DataFrame, detectors: list[Detector] | None = None) -> list[QualityIssue]:
    """Run all quality detectors and return the combined, sorted issue list.

    Ordering: severity (high > medium > low), then by share of rows affected.
    """
    logger.info("Running %s validation detectors", len(detectors or DETECTORS))
    issues: list[QualityIssue] = []
    for detector in detectors or DETECTORS:
        try:
            issues.extend(detector(df))
        except Exception as exc:  # detector failure should not kill the pipeline
            logger.warning("Detector %s raised %s", getattr(detector, "__name__", detector), exc)

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda i: (severity_rank.get(i.severity, 3), -i.pct))
    return issues