import numpy as np
import pandas as pd
import pytest

from app.core.transformer import (
    FixPlan,
    TransformStep,
    UnknownTransformationError,
    get_transformation,
)


def test_drop_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    result = TransformStep("drop_duplicates").apply(df)
    assert len(result) == 2


def test_fill_missing_constant():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
    result = TransformStep("fill_missing", column="a", args={"strategy": "constant", "value": 0}).apply(df)
    assert result["a"].isna().sum() == 0
    assert result["a"].iloc[1] == 0.0


def test_fill_missing_drop():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
    result = TransformStep("fill_missing", column="a", args={"strategy": "drop"}).apply(df)
    assert len(result) == 2


def test_standardize_dates():
    df = pd.DataFrame({"d": ["2024-01-01", "01/02/2024", "bad"]})
    result = TransformStep("standardize_dates", column="d").apply(df)
    assert str(result["d"].dtype).startswith("datetime")
    assert result["d"].isna().sum() == 1


def test_clip_negatives():
    df = pd.DataFrame({"revenue": [-5.0, 10.0, -2.0]})
    result = TransformStep("clip_negatives", column="revenue").apply(df)
    assert (result["revenue"] >= 0).all()


def test_unknown_transformation_raises():
    with pytest.raises(UnknownTransformationError):
        get_transformation("eval_everything")


def test_unknown_column_raises():
    with pytest.raises(UnknownTransformationError):
        TransformStep("fill_missing", column="nope", args={"strategy": "drop"}).apply(pd.DataFrame({"a": [1]}))


def test_fixplan_applies_in_order():
    df = pd.DataFrame({"a": [1.0, np.nan, 1.0, 2.0], "r": [-1.0, 2.0, -3.0, 4.0]})
    plan = FixPlan(
        steps=[
            TransformStep("drop_duplicates"),
            TransformStep("fill_missing", column="a", args={"strategy": "constant", "value": 0}),
            TransformStep("clip_negatives", column="r"),
        ]
    )
    result = plan.apply(df)
    assert result["a"].isna().sum() == 0
    assert (result["r"] >= 0).all()


def test_parse_numeric_handles_sentinels():
    df = pd.DataFrame({"Total Spent": ["4.0", "ERROR", "UNKNOWN", "10.5", "N/A", "3"]})
    result = TransformStep("parse_numeric", column="Total Spent").apply(df)
    assert pd.api.types.is_numeric_dtype(result["Total Spent"])
    assert result["Total Spent"].isna().sum() == 3
    assert result["Total Spent"].notna().sum() == 3
    assert (result["Total Spent"].dropna() > 0).all()


def test_parse_numeric_ignores_numeric_column():
    df = pd.DataFrame({"qty": pd.Series([1, 2, 3], dtype="int64")})
    result = TransformStep("parse_numeric", column="qty").apply(df)
    assert list(result["qty"]) == [1, 2, 3]


def test_parse_numeric_drop_errors():
    df = pd.DataFrame({"Total Spent": ["4.0", "ERROR", "10.5"]})
    result = TransformStep(
        "parse_numeric", column="Total Spent", args={"errors": "drop"}
    ).apply(df)
    assert len(result) == 2
    assert (result["Total Spent"] > 0).all()