"""Upload — the front door.

Drop a messy file, press one button, and watch the deterministic engine run:
ingest → profile → validate. No AI involved here — this is the honest,
repeatable foundation everything else stands on.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.core.pipeline import Pipeline
from app.data.loader import load_dataframe_from_bytes
from app.ui.state import init_state, set_result
from app.ui.theme import (
    apply_theme,
    hero,
    metric_row,
    stepper,
)
from app.utils.helpers import human_number

ACCEPTED = ["csv", "json", "jsonl", "xlsx", "xls", "parquet"]


def render() -> None:
    apply_theme()
    init_state()
    hero(
        "Step 1 · Feed the machine",
        "Every messy dataset starts here.",
        "Drop a CSV, JSON, or Excel file and hit <b>Analyze</b>. DataPilot runs "
        "its deterministic engine — ingestion, profiling, and quality checks — "
        "so you get an honest baseline before any AI gets involved.",
    )

    uploaded = st.file_uploader(
        "Drag & drop your file (or click to browse)",
        type=ACCEPTED,
        help="CSV, JSON, JSONL, XLSX, XLS, Parquet.",
    )

    if uploaded is None:
        with st.expander("💡 Don't have a dataset handy?"):
            st.markdown(
                "Use the bundled sample to see the whole flow in ~30 seconds:  \n"
                "📁 `data/sample/dirty_cafe_sales.csv` — 10,000 coffee-shop rows "
                "with <b>ERROR</b> sentinels in numeric columns, mixed date "
                "formats, and a third of locations missing."
            )
        return

    st.caption(f"📎 Ready: **{uploaded.name}**  ({human_number(len(uploaded.getvalue()))} bytes)")

    col_run, col_hint = st.columns([1, 2])
    with col_run:
        run = st.button("🚀 Analyze this file", type="primary", use_container_width=True)
    with col_hint:
        st.caption("Deterministic only — no API calls, no tokens spent, works offline.")

    if run:
        with st.status("Running the deterministic engine…", expanded=True) as status:
            stepper([("Ingest", "done"), ("Profile", "active"), ("Validate", "none")])
            df: pd.DataFrame = load_dataframe_from_bytes(uploaded.name, uploaded.getvalue())
            with st.spinner("Profiling every column…"):
                pipe = Pipeline(name=Path(uploaded.name).stem)
                result, _ = pipe.run_deterministic(df)
            status.update(label="Engine finished — baseline ready.", state="complete")

        set_result(result, df)
        st.toast("File analyzed ✨ — see the forensics on the next page.")
        st.success(
            f"**{result.source_name}** scanned · {human_number(result.profile.rows)} rows "
            f"· {result.profile.columns} columns · {len(result.issues)} issues found."
        )

    if st.session_state.get("result") is not None:
        st.divider()
        section_quick(result_all := st.session_state["result"])

        with st.expander("👀 Peek at the raw data"):
            raw = st.session_state.get("raw")
            st.dataframe(raw.head(50), width="stretch")

        quick_links(result_all)


def section_quick(result) -> None:
    st.markdown(
        '<div class="dp-section">Profile snapshot</div>', unsafe_allow_html=True
    )
    stats = result.profile.to_dict()
    metric_row(
        [
            {"label": "Rows", "value": human_number(stats["rows"]), "sub": "records inspected"},
            {"label": "Columns", "value": stats["columns"], "sub": "fields profiled"},
            {"label": "Duplicates", "value": stats["duplicates"], "sub": f'{stats["duplicate_pct"]:.1%} of rows', "tone": "warn" if stats["duplicates"] else "ok"},
            {"label": "Issues", "value": len(result.issues), "sub": "deterministic findings", "tone": "danger" if result.issues else "ok"},
        ]
    )


def quick_links(result) -> None:
    st.markdown(
        '<div class="dp-section">Next move</div>', unsafe_allow_html=True
    )
    st.markdown(
        "🔍 Open **Quality Report** for the full forensics  ·  "
        "🤖 Or skip ahead to **AI Fix Plan** for the cleanup draft.",
        unsafe_allow_html=False,
    )