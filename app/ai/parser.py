"""Pydantic models + parsing for structured LLM responses.

The model output is validated here before anything is executed. Invalid output
is an error, never a silent pass-through to the transformer.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.transformer import (
    TRANSFORMATIONS,
    FixPlan,
    TransformStep,
    UnknownTransformationError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

Severity = Literal["low", "medium", "high"]


class FixStep(BaseModel):
    """A single transformation recommendation."""

    name: str
    column: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_known(self) -> "FixStep":
        if self.name not in TRANSFORMATIONS:
            raise ValueError(
                f"Unknown transformation '{self.name}'. Allowed: "
                f"{', '.join(sorted(TRANSFORMATIONS))}"
            )
        return self


class IssueAnalysis(BaseModel):
    """Structured analysis of one quality issue."""

    column: str | None = None
    problem: str
    severity: Severity = "medium"
    recommendation: str = ""
    fix: FixStep | None = None


class Analysis(BaseModel):
    """Validated full response from the model."""

    explanation: str = ""
    issues: list[IssueAnalysis] = Field(default_factory=list)
    cases_needing_review: list[str] = Field(default_factory=list)

    def to_fix_plan(self, guard_columns: set[str]) -> FixPlan:
        """Convert validated issues into an executable, column-safe FixPlan."""
        steps: list[TransformStep] = []
        for issue in self.issues:
            fix = issue.fix
            if fix is None:
                continue
            column = fix.column or issue.column
            if column is not None and column not in guard_columns:
                logger.warning("Skipping fix on unknown column %s", column)
                continue
            # Canonicalize the step name from the registry, not the LLM string.
            steps.append(TransformStep(name=fix.name, column=column, args=fix.args))
        return FixPlan(steps=steps)


def parse_json(content: str) -> dict[str, Any]:
    """Extract a JSON object from a model response (tolerates fences)."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned invalid JSON: {exc}") from exc


def validate_analysis(content: str, guard_columns: set[str]) -> Analysis:
    """Parse raw model content into a validated Analysis.

    Args:
        content: Raw text from the LLM.
        guard_columns: Allowed column names (from the actual schema).

    Raises:
        ValueError: if the JSON is invalid or the response fails Pydantic validation.
    """
    raw = parse_json(content)
    analysis = Analysis.model_validate(raw)  # may raise ValidationError
    for issue in analysis.issues:
        column = issue.fix.column if issue.fix else issue.column
        if column is not None and column not in guard_columns:
            raise ValueError(
                f"Model referenced unknown column '{column}'. "
                f"Known columns: {sorted(guard_columns)}"
            )
    return analysis


def analysis_to_fix_plan(analysis: Analysis, guard_columns: set[str]) -> FixPlan:
    return analysis.to_fix_plan(guard_columns)