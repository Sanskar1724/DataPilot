import numpy as np
import pandas as pd

from app.core.validator import (
    detect_constant_columns,
    detect_dates,
    detect_duplicates,
    detect_missing_values,
    detect_negatives,
    detect_non_numeric_strings,
    detect_outliers,
    validate,
)


def test_detect_missing_values():
    df = pd.DataFrame({"a": [1.0, np.nan, np.nan, 4.0], "b": [1, 2, 3, 4]})
    issues = detect_missing_values(df)
    assert len(issues) == 1
    assert issues[0].column == "a"
    assert issues[0].problem == "missing_values"
    assert issues[0].count == 2


def test_detect_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    issues = detect_duplicates(df)
    assert len(issues) == 1
    assert issues[0].problem == "duplicate_rows"
    assert issues[0].count == 1


def test_detect_negatives_in_revenue():
    df = pd.DataFrame({"revenue": [-50.0, 10.0, -5.0, 20.0]})
    issues = detect_negatives(df)
    assert len(issues) == 1
    assert issues[0].count == 2
    assert issues[0].severity == "high"


def test_detect_negatives_ignores_unrelated():
    df = pd.DataFrame({"balance": [-50.0, 10.0]})
    assert detect_negatives(df) == []


def test_detect_dates_inconsistent():
    df = pd.DataFrame({"order_date": ["2024-01-01", "01/02/2024", "not-a-date", "2024-06-30"]})
    issues = detect_dates(df)
    assert len(issues) == 1
    assert issues[0].problem == "inconsistent_date_formats"


def test_detect_constant_columns():
    df = pd.DataFrame({"k": ["x", "x", "x"], "v": [1, 2, 3]})
    issues = detect_constant_columns(df)
    assert len(issues) == 1
    assert issues[0].column == "k"


def test_detect_outliers():
    values = [1] * 90 + [1] * 9 + [5000]
    df = pd.DataFrame({"amount": values})
    issues = detect_outliers(df, zscore_threshold=4.0)
    assert len(issues) == 1
    assert issues[0].count >= 1


def test_detect_non_numeric_strings():
    df = pd.DataFrame({"Total Spent": ["4.0", "ERROR", "10.5", "UNKNOWN", "N/A"]})
    issues = detect_non_numeric_strings(df)
    assert len(issues) == 1
    assert issues[0].problem == "non_numeric_strings"
    assert issues[0].count == 3


def test_detect_non_numeric_ignores_missing_only():
    df = pd.DataFrame({"total": [1.0, None, 3.0]})
    assert detect_non_numeric_strings(df) == []


def test_validate_sorted_by_severity():
    df = pd.DataFrame(
        {
            "revenue": [-5.0, 10.0],
            "a": [1.0, np.nan],
            "k": ["x", "x"],
        }
    )
    issues = validate(df)
    severities = [i.severity for i in issues]
    rank = {"high": 0, "medium": 1, "low": 2}
    assert [rank[s] for s in severities] == sorted(rank[s] for s in severities)