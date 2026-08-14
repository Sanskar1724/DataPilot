"""Shared session-state helpers for the Streamlit app."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.pipeline import PipelineResult
from app.core.transformer import FixPlan


def init_state() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("plan", None)
    st.session_state.setdefault("source_name", None)
    st.session_state.setdefault("raw", None)


def set_result(result: PipelineResult, raw: pd.DataFrame) -> None:
    st.session_state["result"] = result
    st.session_state["raw"] = raw
    st.session_state["source_name"] = result.source_name


def set_plan(plan: FixPlan | None) -> None:
    st.session_state["plan"] = plan


def get_result() -> PipelineResult | None:
    return st.session_state.get("result")


def get_plan() -> FixPlan | None:
    return st.session_state.get("plan")


def get_raw() -> pd.DataFrame | None:
    return st.session_state.get("raw")


def get_source_name() -> str | None:
    return st.session_state.get("source_name")