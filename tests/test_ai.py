"""Tests for the AI layer — all client calls are mocked, no network."""

import json

import pytest

from app.ai.client import Completion, MissingApiKeyError, OpenRouterClient
from app.ai.parser import (
    Analysis,
    FixStep,
    IssueAnalysis,
    validate_analysis,
)
from app.ai.prompts import TRANSFORM_CATALOG, build_analysis_messages


def test_build_analysis_messages_shape():
    messages = build_analysis_messages(
        {"profile": {"rows": 10}, "schema": {"columns": 2}, "issues": []}
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # Prompt must NOT embed raw data rows, only metadata
    assert "rows" in messages[1]["content"]


def test_validate_analysis_ok():
    content = json.dumps(
        {
            "explanation": "Some missing, negatives in revenue.",
            "issues": [
                {
                    "column": "revenue",
                    "problem": "negative_values",
                    "severity": "high",
                    "recommendation": "clip to zero",
                    "fix": {"name": "clip_negatives", "column": "revenue", "args": {}},
                }
            ],
            "cases_needing_review": ["check date column"],
        }
    )
    analysis = validate_analysis(content, guard_columns={"revenue", "order_date"})
    assert isinstance(analysis, Analysis)
    assert analysis.issues[0].severity == "high"
    assert analysis.issues[0].fix.name == "clip_negatives"
    plan = analysis.to_fix_plan({"revenue"})
    assert len(plan.steps) == 1
    assert plan.steps[0].name == "clip_negatives"


def test_validate_analysis_fenced_json():
    body = json.dumps({"issues": []})
    content = f"```json\n{body}\n```"
    analysis = validate_analysis(content, guard_columns=set())
    assert analysis.issues == []


def test_validate_analysis_unknown_transform_rejected():
    content = json.dumps(
        {
            "issues": [
                {"column": "a", "problem": "x", "fix": {"name": "rm -rf /"}}
            ]
        }
    )
    with pytest.raises(ValueError, match="Unknown transformation"):
        validate_analysis(content, guard_columns={"a"})


def test_validate_analysis_unknown_column_rejected():
    content = json.dumps(
        {
            "issues": [
                {
                    "column": "ghost_col",
                    "problem": "x",
                    "fix": {"name": "clip_negatives", "column": "ghost_col"},
                }
            ]
        }
    )
    with pytest.raises(ValueError, match="unknown column"):
        validate_analysis(content, guard_columns={"revenue"})


def test_validate_analysis_invalid_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        validate_analysis("not json at all", guard_columns=set())


def test_fix_plan_skips_unknown_guard_columns():
    # to_fix_plan drops steps whose column isn't in the schema guard set
    analysis = Analysis(
        issues=[
            IssueAnalysis(column="real", problem="x", fix=FixStep(name="drop_duplicates")),
            IssueAnalysis(column="fake", problem="y", fix=FixStep(name="drop_duplicates")),
        ]
    )
    plan = analysis.to_fix_plan({"real"})
    assert len(plan.steps) == 1
    assert plan.steps[0].column == "real"


class _FakeClient(OpenRouterClient):
    def __init__(self, content: str) -> None:
        self._content = content

    def chat(self, *args, **kwargs):
        return Completion(
            content=self._content,
            model="fake-model",
            latency_ms=10,
        )


def test_missing_api_key_raises():
    client = OpenRouterClient()
    client.settings.openrouter_api_key = ""
    with pytest.raises(MissingApiKeyError):
        client.chat([{"role": "user", "content": "hi"}])


def test_analyzer_returns_validated_plan():
    from app.ai.analyzer import Analyzer, build_metadata
    from app.core.validator import detect_missing_values
    import pandas as pd

    fake = _FakeClient(json.dumps({"issues": [], "cases_needing_review": []}))

    df = pd.DataFrame({"a": [1, 2]})
    prof = {"rows": 2}
    schema = {"columns": ["a"]}
    metadata = build_metadata(prof, schema, detect_missing_values(df))
    analyzer = Analyzer(client=fake)
    analysis, plan, completion = analyzer.analyze_and_plan(metadata, guard_columns={"a"})
    assert analysis.issues == []
    assert plan is not None
    assert completion.model == "fake-model"