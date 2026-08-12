"""Pipeline orchestrator: ingestion → profiling → validation → (AI) → transform → report.

Stages are staged so the AI layer can later slot between Validation and
Transformation without touching deterministic code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.profiler import Profile, profile
from app.core.reporter import Report, build_report
from app.core.transformer import FixPlan
from app.core.validator import QualityIssue, validate
from app.data.loader import load_dataframe
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Everything produced by a single pipeline run."""

    source_name: str
    raw: pd.DataFrame
    profile: Profile
    issues: list[QualityIssue]
    cleaned: pd.DataFrame
    plan: FixPlan | None
    report: Report

    def summary(self) -> dict[str, Any]:
        return self.report.summary()


class Pipeline:
    """Deterministic data pipeline (Phase 1).

    The AI layer is intentionally *out* of this class: a caller runs
    `run_deterministic`, gets quality issues as metadata, asks the LLM for a
    FixPlan, then calls `apply_plan`. That keeps the LLM decoupled from data
    processing.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def run_deterministic(self, source: str | Path | pd.DataFrame) -> tuple[PipelineResult, pd.DataFrame]:
        """Run ingestion → profiling → validation.

        Returns the raw cleaned-so-far frame (identical to input until a plan
        is applied) plus a PipelineResult with issues and profile.
        """
        if isinstance(source, pd.DataFrame):
            df = source.copy()
            source_name = self.name
        else:
            df = load_dataframe(source)
            source_name = Path(source).stem

        logger.info("Pipeline '%s' starting for %s", self.name, source_name)
        prof = profile(df, name=source_name)
        issues = validate(df)

        report = build_report(prof, issues, transformations=[])
        result = PipelineResult(
            source_name=source_name,
            raw=df.copy(),
            profile=prof,
            issues=issues,
            cleaned=df.copy(),
            plan=None,
            report=report,
        )
        return result, df

    def apply_plan(self, result: PipelineResult, plan: FixPlan) -> PipelineResult:
        """Execute a validated FixPlan and rebuild the report."""
        cleaned = plan.apply(result.cleaned)
        transformations = [step.to_dict() for step in plan.steps]
        result.cleaned = cleaned
        result.plan = plan
        result.report = build_report(
            profile(cleaned, name=result.source_name),
            result.issues,
            transformations=transformations,
        )
        logger.info("Plan applied: %s transformations", len(plan.steps))
        return result

    def run_full(self, source: str | Path | pd.DataFrame, plan: FixPlan | None = None) -> PipelineResult:
        """Run everything deterministic, optionally applying a pre-built plan."""
        result, _ = self.run_deterministic(source)
        if plan is not None:
            result = self.apply_plan(result, plan)
        return result