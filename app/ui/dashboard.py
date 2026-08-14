"""Dashboard — the mission-control view.

Purpose: turn the last pipeline run into a story someone can read in 10 seconds.
Hero status, KPI cards, the severity of the damage, and what we already cleaned.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui.state import get_result
from app.ui.theme import (
    apply_theme,
    hero,
    metric_row,
    panel,
    section,
    severity_badge,
)
from app.utils.helpers import human_number


def render() -> None:
    apply_theme()
    hero(
        "Dashboard",
        "Is your data ready to drive decisions?",
        "DataPilot inspects every file you bring in, surfaces what's broken "
        "with deterministic rules, and drafts the cleanup with an AI copilot — "
        "then you decide what ships.",
    )

    result = get_result()
    if result is None:
        panel(
            "🤔 No pipeline run yet."
            "**Give the machine something to chew on** — head to "
            "<b>Upload Data</b> to analyze your first file. "
            "It takes ~5 seconds and costs nothing."
        )
        return

    summary = result.report.summary()
    issues = result.issues
    by_sev = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        by_sev[issue.severity] = by_sev.get(issue.severity, 0) + 1

    metric_row(
        [
            {
                "label": "Rows processed",
                "value": human_number(summary["rows_processed"]),
                "sub": f"{result.profile.columns} columns · {result.source_name}",
            },
            {
                "label": "Issues found",
                "value": summary["issues_found"],
                "sub": f"{by_sev['high']} high · {by_sev['medium']} medium · {by_sev['low']} low",
                "tone": "danger" if by_sev["high"] else "warn",
            },
            {
                "label": "Auto-fixed",
                "value": summary["auto_fixed"],
                "sub": "transformations applied",
                "tone": "ok",
            },
            {
                "label": "Needs review",
                "value": summary["needs_review"],
                "sub": "still on your desk",
                "tone": "warn",
            },
        ]
    )

    section("What's broken, by severity")
    if not issues:
        panel("🏆 <b>Clean bill of health.</b> No deterministic issues detected."
              "Even so, run the AI copilot for a second opinion.")
    else:
        panels = []
        for issue in issues:
            badge_html = severity_badge(issue.severity)
            target = "the whole dataset" if not issue.column else f"`{issue.column}`"
            panels.append(
                f"<span style='color:#E8ECF4'>{badge_html}&nbsp; {target}: "
                f"<b>{issue.problem}</b></span> "
                f"<span style='color:#8A93A6'>· {human_number(issue.count)} "
                f"rows ({issue.pct:.1%})</span>"
            )
        panel("<br>".join(panels))

    if result.report.transformations:
        section("What we already fixed")
        rows = []
        for t in result.report.transformations:
            rows.append({"transformation": t.get("name", ""), "on column": t.get("column") or "—"})
        st.dataframe(pd.DataFrame(rows), width="stretch")

    section("Next move")
    panel(
        "👀 <b>Quality Report</b> · read the full forensics and the AI's story "
        "<br>🤖 <b>AI Fix Plan</b> · let the copilot draft the cleanup, then approve"
    )