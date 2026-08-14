"""AI Fix Plan — copilot drafts, you approve, the engine executes.

This page is the money shot: an AI drafts a cleanup plan from *metadata only*,
Pydantic validates it against the real schema, and only a fixed set of safe
transforms can ever run. The user stays in the driver's seat.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ai.analyzer import Analyzer, build_metadata
from app.core.pipeline import Pipeline
from app.core.transformer import TRANSFORMATIONS, FixPlan
from app.data.schema import infer_schema
from app.ui.state import get_result, get_raw, set_plan
from app.ui.theme import (
    ai_callout,
    apply_theme,
    hero,
    metric_row,
    panel,
    section,
    severity_badge,
)
from app.utils.config import get_settings
from app.utils.helpers import human_number


def _ask_ai(result) -> tuple | None:
    """Run the metadata-only AI analysis. Returns (analysis, plan, completion)."""
    settings = get_settings()
    if not settings.ai_enabled:
        st.warning("AI is switched off in `.env` (`DATAPILOT_AI_ENABLED=false`).")
        return None
    if not settings.has_api_key:
        st.warning("Add `OPENROUTER_API_KEY` to `.env` to unlock AI fixes.")
        return None

    schema = infer_schema(result.raw)
    metadata = build_metadata(result.profile.to_dict(), schema.to_dict(), result.issues)
    guard = set(result.raw.columns)
    with st.spinner("The copilot is drafting a cleanup plan…"):
        try:
            analysis, plan, completion = Analyzer().analyze_and_plan(metadata, guard)
        except Exception as exc:
            st.error(f"The AI step failed: {exc}. The deterministic engine below "
                     "is unaffected.")
            return None

    st.caption(
        f"⚙️ `{completion.model}` · {completion.total_tokens} tokens · "
        f"{completion.latency_ms} ms"
    )
    return analysis, plan, completion


def render() -> None:
    apply_theme()
    hero(
        "Step 3 · The copilot",
        "Let AI draft the cleanup. You keep the pen.",
        "The model never touches your rows — it reads the profile, schema, and "
        "findings, then proposes a fix plan. Every step is validated against "
        "your real columns and a fixed catalog of safe transforms before it "
        "can run.",
    )

    result = get_result()
    if result is None:
        panel("🤔 No dataset loaded yet. "
              "**Analyze a file first** on the <b>Upload Data</b> page.")
        return

    col_btn, col_cost = st.columns([1, 3])
    with col_btn:
        generate = st.button("🧠 Generate fix plan", type="primary", use_container_width=True)
    with col_cost:
        st.caption("Sends metadata only (schema + stats + findings), never raw rows.")

    if generate:
        outcome = _ask_ai(result)
        if outcome:
            st.session_state["analysis"], plan, completion = outcome
            set_plan(plan)
            st.session_state["completion_meta"] = {
                "model": completion.model,
                "tokens": completion.total_tokens,
                "ms": completion.latency_ms,
            }
            st.toast("Fix plan drafted ✨")

    analysis = st.session_state.get("analysis")
    if analysis is not None:
        section("The proposed plan")
        rows = []
        for issue in analysis.issues:
            fix = issue.fix
            rows.append(
                {
                    "severity": issue.severity,
                    "column": issue.column or "(dataset)",
                    "what's wrong": issue.problem.replace("_", " "),
                    "suggested fix": fix.name if fix else "— review manually",
                    "target column": fix.column or "—" if fix else "—",
                }
            )
        if rows:
            frame = pd.DataFrame(rows)
            frame["severity"] = frame["severity"].map(lambda s: severity_badge(s.upper()))
            st.dataframe(frame, width="stretch")
        else:
            panel("🤷 Nothing to fix. The model thinks this dataset is in good shape.")

        if analysis.explanation:
            ai_callout("AI · why I proposed this", analysis.explanation)

        if analysis.cases_needing_review:
            with st.expander("⚠️ The model flagged these for human eyes"):
                for case in analysis.cases_needing_review:
                    st.markdown(f"- {case}")

        st.divider()
        section("You're in charge")
        approve = st.checkbox("I reviewed the plan and approve it.")
        apply_btn = st.button(
            "✅ Apply approved fixes", type="primary", disabled=not approve, use_container_width=True
        )

        if apply_btn:
            plan = st.session_state.get("plan")
            if plan is None:
                st.error("No plan on hand — run 'Generate fix plan' first.")
            elif plan.steps:
                result = get_result()
                result = Pipeline().apply_plan(result, plan)
                st.session_state["result"] = result

                before_issues = len(analysis.issues)
                st.success(
                    f"Applied **{len(plan.steps)}** transformations. "
                    f"{result.source_name} is one step closer to ship-ready."
                )
                st.toast("Clean dataset ready 🎉")
            else:
                st.info("The plan has no executable steps — nothing to apply.")

    # ------------------------------------------------------------------ #
    # Clean result preview + download
    # ------------------------------------------------------------------ #
    result = get_result()
    if result is not None and result.cleaned is not None and len(result.cleaned):
        section("Ship-ready preview")
        st.dataframe(result.cleaned.head(100), width="stretch")

        summary = result.report.summary()
        metric_row(
            [
                {"label": "Rows", "value": human_number(summary["rows_processed"]), "sub": "after fixes"},
                {"label": "Columns", "value": result.profile.columns, "sub": "unchanged structure"},
                {"label": "Applied", "value": summary["auto_fixed"], "sub": "transformations run", "tone": "ok"},
                {"label": "Remaining", "value": summary["needs_review"], "sub": "for later", "tone": "warn"},
            ]
        )

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇ Download clean CSV",
                data=result.cleaned.to_csv(index=False).encode("utf-8"),
                file_name=f"{result.source_name}_clean.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇ Download clean Parquet",
                data=result.cleaned.to_parquet(index=False),
                file_name=f"{result.source_name}_clean.parquet",
                mime="application/octet-stream",
                use_container_width=True,
            )

    section("The safety net: our transform catalog")
    st.caption("Only these deterministic, audited transforms are ever executed — "
               "nothing else. No arbitrary code, no surprises.")
    catalog = [
        {"transform": name, "what it does": (TRANSFORMATIONS[name].__doc__ or "").strip().split("\n")[0]}
        for name in sorted(TRANSFORMATIONS)
    ]
    st.dataframe(pd.DataFrame(catalog), width="stretch")