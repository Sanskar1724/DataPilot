"""Quality Report — the forensic findings.

Deterministic issues first (the ground truth), then the AI's plain-language
story on top. The report is reproducible: same file, same rules, same numbers —
every single time.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ai.analyzer import Analyzer, build_metadata
from app.data.schema import infer_schema
from app.ui.state import get_result
from app.ui.theme import (
    ai_callout,
    apply_theme,
    hero,
    panel,
    section,
    severity_badge,
)
from app.utils.config import get_settings
from app.utils.helpers import human_number


def _run_ai_explanation(result) -> str | None:
    st.session_state.setdefault("ai_explanation", {})
    cache_key = result.source_name
    if cache_key in st.session_state["ai_explanation"]:
        return st.session_state["ai_explanation"][cache_key]

    settings = get_settings()
    if not settings.ai_enabled:
        return "AI is switched off in `.env` (`DATAPILOT_AI_ENABLED=false`). " \
               "Flip it on to get a narrative on top of the forensics."
    if not settings.has_api_key:
        return "Add `OPENROUTER_API_KEY` to `.env` to unlock the AI explainer."

    schema = infer_schema(result.raw)
    metadata = build_metadata(result.profile.to_dict(), schema.to_dict(), result.issues)
    with st.spinner("Reading the tea leaves…"):
        try:
            text = Analyzer().explain(metadata)
        except Exception as exc:  # network/model hiccups should never crash the page
            st.warning(f"The AI explainer hit a snag: {exc}. The deterministic "
                       "report below is still fully valid.")
            return None

    st.session_state["ai_explanation"][cache_key] = text
    return text


def render() -> None:
    apply_theme()
    hero(
        "Step 2 · Forensics",
        "What's wrong with your data?",
        "Every finding below is the output of reproducible rules — no ›black box‹, "
        "no vibes. The AI layer then translates these findings into plain language "
        "and a fix plan you stay in control of.",
    )

    result = get_result()
    if result is None:
        panel("🤔 Nothing to report yet. "
              "**Analyze a file first** on the <b>Upload Data</b> page.")
        return

    if not result.issues:
        panel("🏆 <b>Clean bill of health.</b> No deterministic issues detected. "
              "Rare — celebrate appropriately.")
    else:
        section("Deterministic findings")
        rows = []
        for issue in result.issues:
            rows.append(
                {
                    "severity": issue.severity,
                    "column": issue.column or "(whole dataset)",
                    "problem": issue.problem.replace("_", " "),
                    "affected": f"{human_number(issue.count)} rows",
                    "share": f"{issue.pct:.1%}",
                }
            )
        frame = pd.DataFrame(rows)
        frame["severity"] = frame["severity"].map(
            lambda s: severity_badge(s.upper())
        )
        st.markdown(
            "<style>div[data-testid='stDataFrame'] table td, "
            "div[data-testid='stDataFrame'] table th{padding:0.3rem 0.5rem;}</style>",
            unsafe_allow_html=True,
        )
        st.dataframe(frame, width="stretch")

        with st.expander("🧪 Show the ugly samples (evidence)"):
            for issue in result.issues[:8]:
                if issue.samples:
                    st.markdown(
                        f"**{issue.column or '(dataset)'} · {issue.problem}** "
                        f"({human_number(issue.count)} rows)"
                    )
                    st.code(" | ".join(str(s) for s in issue.samples[:10]), language="text")

    section("AI explainer")
    text = _run_ai_explanation(result)
    if text:
        ai_callout("AI · what's going on here", text)

    section("The actionable report")
    with st.expander("📄 Full report (markdown — for auditors)"):
        st.code(result.report.to_markdown(), language="text")
        st.download_button(
            "⬇ Download markdown report",
            data=result.report.to_markdown().encode("utf-8"),
            file_name=f"{result.source_name}_quality_report.md",
            mime="text/markdown",
        )