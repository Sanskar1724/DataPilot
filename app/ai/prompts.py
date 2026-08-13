"""Prompt builders.

The prompts send the LLM only metadata (schema, stats, issues, small samples),
never the full dataset — that is the core architectural rule of the project.
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """You are DataPilot's analysis engine. You never process raw datasets.
You receive metadata only: schema, statistics, and deterministic data-quality issues.
Your job is to reason about the metadata and return a structured fix plan.

Rules:
1. Only use the transformation names from the provided list. Never invent new ones.
2. Only reference columns that actually exist in the schema.
3. Output STRICT JSON only, no markdown fences, no commentary.
4. Explain each issue briefly but do not suggest dropping data unnecessarily.
"""

TRANSFORM_CATALOG = [
    {"name": "drop_duplicates", "description": "Remove exact duplicate rows."},
    {"name": "fill_missing", "description": "Handle missing values. strategies: drop, constant(value), mean, median, mode, fwd, bwd."},
    {"name": "standardize_dates", "description": "Parse a text column into datetime. Use for inconsistent date formats."},
    {"name": "parse_numeric", "description": "Parse a column that is stored as messy text (e.g. 'ERROR', 'UNKNOWN', 'N/A') into a proper numeric column."},
    {"name": "clip_negatives", "description": "Clip negative numeric values to 0. Use only for logically non-negative columns."},
    {"name": "flag_negatives", "description": "Add a 0/1 flag column marking negative values instead of changing data."},
    {"name": "standardize_strings", "description": "Normalize string case/whitespace. modes: strip, lower, title."},
]


def build_analysis_messages(metadata: dict[str, Any]) -> list[dict[str, str]]:
    """Build the OpenAI-style messages for a metadata-only analysis request."""
    user_payload = {
        "schema": metadata.get("schema"),
        "profile": metadata.get("profile"),
        "issues": metadata.get("issues"),
        "transform_catalog": TRANSFORM_CATALOG,
        "instructions": (
            "Return JSON with this exact shape:\n"
            '{"explanation": "<short summary of what is wrong>", '
            '"issues": [{"column": "...", "problem": "...", "severity": "low|medium|high", '
            '"recommendation": "...", "fix": {"name": "<transform>", "column": "<col|null>", "args": {}}}], '
            '"cases_needing_review": ["<short description>"]}'
            "\nOnly include a fix when a deterministic transform can safely solve the issue."
        ),
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _as_string(user_payload)},
    ]


def build_explanation_messages(metadata: dict[str, Any]) -> list[dict[str, str]]:
    """Build messages for a plain-language quality explanation (Phase 2)."""
    user_payload = {
        "schema": metadata.get("schema"),
        "profile": metadata.get("profile"),
        "issues": metadata.get("issues"),
        "instructions": (
            "Explain the data-quality problems in plain language. "
            "What looks wrong, roughly how widespread it is, and what the likely "
            "cause is. Keep it under 250 words."
        ),
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _as_string(user_payload)},
    ]


def _as_string(payload: Any) -> str:
    import json

    return json.dumps(payload, default=str, ensure_ascii=False)