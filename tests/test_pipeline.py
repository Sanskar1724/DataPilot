"""End-to-end pipeline tests (Phase 1)."""

import pandas as pd

from app.core.pipeline import Pipeline
from app.core.transformer import FixPlan, TransformStep


def test_pipeline_deterministic_run(tmp_path):
    p = tmp_path / "sales.csv"
    p.write_text(
        "order_id,revenue,region\n"
        "O1,-10,North\n"
        "O2,20,South\n"
        "O3,,North\n"
        "O1,-10,North\n",
        encoding="utf-8",
    )
    pipe = Pipeline(name="test")
    result, _ = pipe.run_deterministic(p)

    assert result.profile.rows == 4
    assert result.profile.duplicates == 1
    assert any(i.problem == "duplicate_rows" for i in result.issues)
    assert any(i.problem == "negative_values" for i in result.issues)
    assert any(i.problem == "missing_values" for i in result.issues)


def test_pipeline_apply_plan(tmp_path):
    p = tmp_path / "sales.csv"
    p.write_text(
        "order_id,revenue,region\n"
        "O1,-10,North\n"
        "O2,20,South\n"
        "O3,,North\n"
        "O1,-10,North\n",
        encoding="utf-8",
    )
    pipe = Pipeline(name="test")
    result, _ = pipe.run_deterministic(p)

    plan = FixPlan(
        steps=[
            TransformStep("drop_duplicates"),
            TransformStep("fill_missing", column="region", args={"strategy": "constant", "value": "Unknown"}),
            TransformStep("clip_negatives", column="revenue"),
        ]
    )
    result = pipe.apply_plan(result, plan)

    assert len(result.cleaned) == 3
    assert (result.cleaned["revenue"].dropna() >= 0).all()
    assert result.cleaned["region"].isna().sum() == 0
    assert result.report.auto_fixed_count == 3
    assert result.report.summary()["rows_processed"] == 3


def test_pipeline_run_full_with_dataframe():
    pipe = Pipeline(name="inline")
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    result = pipe.run_full(df)
    assert result.profile.duplicates == 1


def test_pipeline_on_sample_dataset():
    from pathlib import Path

    sample = Path("data/sample/sales_dirty.csv")
    if not sample.exists():
        return

    pipe = Pipeline(name="sample")
    result, raw = pipe.run_deterministic(sample)

    assert result.profile.rows == 12005
    assert result.profile.columns == 7
    problems = {i.problem for i in result.issues}
    assert "missing_values" in problems
    assert "duplicate_rows" in problems
    assert "negative_values" in problems
    assert "inconsistent_date_formats" in problems
    assert len(result.report.summary()) > 0
    assert len(raw) == len(result.cleaned)