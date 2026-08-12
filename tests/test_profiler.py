import numpy as np
import pandas as pd
import pytest

from app.core.profiler import profile


def test_profile_shape_counts():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    prof = profile(df, name="mini")
    assert prof.rows == 3
    assert prof.columns == 2
    assert prof.duplicates == 0


def test_profile_detects_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    prof = profile(df)
    assert prof.duplicates == 1
    assert prof.duplicate_pct == pytest.approx(1 / 3, abs=1e-9)


def test_profile_null_counts():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
    prof = profile(df)
    assert prof.column_stats["a"].nulls == 1
    assert prof.column_stats["a"].null_pct == pytest.approx(1 / 3, abs=1e-9)


def test_profile_to_dict_json_safe():
    df = pd.DataFrame({"a": [1, 2], "b": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]})
    d = profile(df).to_dict()
    assert isinstance(d["column_stats"]["a"]["min"], int)
    assert isinstance(d["column_stats"]["b"]["min"], str)