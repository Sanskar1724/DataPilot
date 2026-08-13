"""Analyzer: orchestrates metadata → LLM → validated output."""

from __future__ import annotations

from typing import Any

from app.ai.client import Completion, OpenRouterClient
from app.ai.parser import Analysis, validate_analysis
from app.ai.prompts import build_analysis_messages, build_explanation_messages
from app.core.transformer import FixPlan
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Analyzer:
    """Runs metadata-only analysis through OpenRouter.

    Responsibilities (per the architecture):
    - explain data-quality problems
    - propose a structured fix plan
    It never receives or processes the raw dataset.
    """

    def __init__(self, client: OpenRouterClient | None = None) -> None:
        self.settings = get_settings()
        self.client = client or OpenRouterClient()

    # ------------------------------------------------------------------ #

    def explain(self, metadata: dict[str, Any]) -> str | None:
        """Return a short plain-language explanation of the quality issues."""
        messages = build_explanation_messages(metadata)
        completion = self.client.chat(messages, max_tokens=600)
        return completion.content.strip()

    def analyze_and_plan(
        self, metadata: dict[str, Any], guard_columns: set[str]
    ) -> tuple[Analysis, FixPlan, Completion]:
        """Ask the model for a structured analysis, validate it, build a FixPlan.

        Returns:
            (validated analysis, executable fix plan, raw completion).
        """
        from app.ai.client import UnsupportedFeatureError

        messages = build_analysis_messages(metadata)
        retries = 4
        try:
            completion = self.client.chat(
                messages,
                temperature=0.0,
                max_tokens=4000,
                response_format={"type": "json_object"},
                retries=retries,
            )
        except UnsupportedFeatureError:
            # Model/provider cannot do structured output; rely on prompt
            # instructions + defensive parser instead.
            logger.warning(
                "response_format unsupported; retrying without it "
                "(prompt-based JSON only)"
            )
            completion = self.client.chat(
                messages, temperature=0.0, max_tokens=4000, retries=retries
            )

        analysis = validate_analysis(completion.content, guard_columns)
        plan = analysis.to_fix_plan(guard_columns)
        logger.info(
            "AI analysis ok: %s issues, %s fix steps, %s tokens",
            len(analysis.issues),
            len(plan.steps),
            completion.total_tokens,
        )
        return analysis, plan, completion


def build_metadata(
    profile_dict: dict[str, Any],
    schema_dict: dict[str, Any],
    issues: list[Any],
) -> dict[str, Any]:
    """Assemble the compact metadata bundle that is sent to the model."""
    return {
        "profile": profile_dict,
        "schema": schema_dict,
        "issues": [issue.to_dict() for issue in issues],
    }