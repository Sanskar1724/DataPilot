"""Central design system: global CSS + reusable UI building blocks.

Every page imports from here so the whole app shares one visual language:
gradient heroes, glass metric cards, severity badges, and callout panels.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Brand
# --------------------------------------------------------------------------- #

BRAND = {
    "primary": "#7C6CFF",
    "primary_deep": "#5B4BFF",
    "gradient": "linear-gradient(135deg, #7C6CFF 0%, #4FB3FF 55%, #38D39F 100%)",
    "gradient_warm": "linear-gradient(135deg, #FFB86B 0%, #FF7A8A 100%)",
    "ok": "#38D39F",
    "warn": "#FFB86B",
    "danger": "#FF6B81",
    "muted": "#8A93A6",
    "text": "#E8ECF4",
    "card": "rgba(255,255,255,0.04)",
    "border": "rgba(255,255,255,0.08)",
}

_GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

/* ---------- Base ---------- */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}
.stApp {{
    background:
        radial-gradient(1200px 600px at 85% -10%, rgba(124,108,255,0.13), transparent 60%),
        radial-gradient(900px 500px at -10% 10%, rgba(79,179,255,0.10), transparent 55%),
        #0D1017;
}}

/* ---------- Hero ---------- */
.dp-hero {{
    border-radius: 18px;
    padding: 2rem 2.2rem;
    margin-bottom: 1.6rem;
    background: linear-gradient(135deg, rgba(124,108,255,0.18) 0%, rgba(79,179,255,0.10) 50%, rgba(56,211,159,0.12) 100%);
    border: 1px solid {BRAND['border']};
    position: relative;
    overflow: hidden;
}}
.dp-hero::after {{
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(600px 240px at 85% 0%, rgba(124,108,255,0.25), transparent 60%);
}}
.dp-hero h1 {{
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin: 0 0 0.35rem;
    background: {BRAND['gradient']};
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    position: relative;
    z-index: 1;
}}
.dp-hero p {{
    font-size: 1.02rem;
    color: {BRAND['muted']};
    max-width: 720px;
    margin: 0;
    line-height: 1.55;
    position: relative;
    z-index: 1;
}}
.dp-eyebrow {{
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: {BRAND['primary']};
    margin-bottom: 0.55rem;
    position: relative;
    z-index: 1;
}}
.dp-badge {{
    display:inline-block;
    padding: 0.22rem 0.7rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.3px;
    line-height: 1.5;
    vertical-align: middle;
}}

/* ---------- Metric cards ---------- */
.dp-metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 1rem;
    margin: 1.1rem 0 1.6rem;
}}
.dp-metric {{
    background: {BRAND['card']};
    border: 1px solid {BRAND['border']};
    border-radius: 14px;
    padding: 1.05rem 1.2rem;
    backdrop-filter: blur(6px);
}}
.dp-metric .label {{
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {BRAND['muted']};
}}
.dp-metric .value {{
    font-size: 1.85rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-top: 0.2rem;
    font-variant-numeric: tabular-nums;
}}
.dp-metric .sub {{
    font-size: 0.8rem;
    color: {BRAND['muted']};
    margin-top: 0.25rem;
}}
.dp-metric .ok    {{ color: {BRAND['ok']}; }}
.dp-metric .warn  {{ color: {BRAND['warn']}; }}
.dp-metric .danger{{ color: {BRAND['danger']}; }}

/* ---------- Panels ---------- */
.dp-panel {{
    background: {BRAND['card']};
    border: 1px solid {BRAND['border']};
    border-radius: 14px;
    padding: 1.15rem 1.35rem;
    margin: 0.6rem 0 1.2rem;
}}
.dp-section {{
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.1px;
    text-transform: uppercase;
    color: {BRAND['primary']};
    margin: 1.5rem 0 0.4rem;
}}
.dp-prose {{ color: {BRAND['muted']}; font-size: 0.94rem; line-height: 1.6; }}

/* ---------- Buttons ---------- */
.stButton>button, .stDownloadButton>button {{
    border-radius: 10px;
    font-weight: 650;
    letter-spacing: 0.2px;
    transition: transform 0.06s ease;
}}
.stButton>button:hover {{
    transform: translateY(-1px);
}}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{
    background: #10141C;
    border-right: 1px solid {BRAND['border']};
}}
.dp-sidebar-brand {{
    padding: 0 0 0.7rem;
    margin-bottom: 0.9rem;
    border-bottom: 1px solid {BRAND['border']};
}}
.dp-sidebar-brand .logo {{
    font-size: 1.5rem;
    font-weight: 800;
    background: {BRAND['gradient']};
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}}
.dp-sidebar-brand .tagline {{
    font-size: 0.78rem;
    color: {BRAND['muted']};
    margin-top: 0.15rem;
}}
.dp-status-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.8rem;
    color: {BRAND['muted']};
    padding: 0.5rem 0.8rem;
    border-radius: 10px;
    background: {BRAND['card']};
    border: 1px solid {BRAND['border']};
    width: 100%;
    margin: 0.3rem 0;
    box-sizing: border-box;
}}
.dp-status-chip .dot {{ height: 8px; width: 8px; border-radius: 50%; display:inline-block; }}
.dot-live {{ background: {BRAND['ok']}; box-shadow: 0 0 8px {BRAND['ok']}; }}

/* ---------- AI callout ---------- */
.dp-ai {{
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin: 0.8rem 0 1.4rem;
    background: linear-gradient(135deg, rgba(124,108,255,0.14), rgba(56,211,159,0.08));
    border: 1px solid rgba(124,108,255,0.35);
}}
.dp-ai .label {{
    font-weight: 800;
    font-size: 0.85rem;
    letter-spacing: 0.4px;
    background: {BRAND['gradient']};
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    display: block;
    margin-bottom: 0.4rem;
}}
.dp-ai .body {{ color: {BRAND['text']}; font-size: 0.95rem; line-height: 1.6; }}

/* ---------- Stepper (pipeline status) ---------- */
.dp-stepper {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin: 0.9rem 0 1.3rem;
    flex-wrap: wrap;
}}
.dp-step {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 650;
    border: 1px solid {BRAND['border']};
    background: {BRAND['card']};
    color: {BRAND['muted']};
    white-space: nowrap;
}}
.dp-step .num {{
    height: 20px; width: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 800;
    background: rgba(255,255,255,0.08);
}}
.dp-step.done  {{ border-color: rgba(56,211,159,0.5); color: {BRAND['ok']}; }}
.dp-step.done .num {{ background: {BRAND['ok']}; color: #0D1017; }}
.dp-step.active {{ border-color: {BRAND['primary']}; color: {BRAND['primary']}; box-shadow: 0 0 0 3px rgba(124,108,255,0.15); }}
.dp-arrow {{ color: {BRAND['muted']}; font-size: 0.85rem; }}

/* ---------- Misc ---------- */
div[data-testid="stMetric"] {{
    background: {BRAND['card']};
    border: 1px solid {BRAND['border']};
    border-radius: 14px;
    padding: 1.05rem 1.2rem;
}}
div[data-testid="stMetricValue"] {{ font-size: 1.6rem; font-weight: 800; }}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
</style>
"""


def apply_theme() -> None:
    """Inject the global stylesheet (idempotent per rerun)."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #


def hero(eyebrow: str, title: str, subtitle: str) -> None:
    """Gradient hero header with an eyebrow label + subtitle."""
    st.markdown(
        f"""
        <div class="dp-hero">
            <span class="dp-eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


SEVERITY_COLORS = {"high": "#FF6B81", "medium": "#FFB86B", "low": "#38D39F"}


def badge(text: str, color: str | None = None) -> str:
    """Return an inline pill badge (HTML fragment)."""
    tone = color or BRAND["primary"]
    return (
        f'<span class="dp-badge" style="background: {tone}22; '
        f'color: {tone}; border: 1px solid {tone}55;">{text}</span>'
    )


def severity_badge(severity: str) -> str:
    """Pill badge coloured by issue severity."""
    return badge(severity.upper(), SEVERITY_COLORS.get(severity, BRAND["primary"]))


def metric_row(items: list[dict[str, Any]]) -> None:
    """Render a responsive grid of metric cards.

    item keys: label, value, sub, tone (ok|warn|danger|None).
    """
    cards = []
    for it in items:
        cls = it.get("tone", "")
        sub = f'<div class="sub">{it.get("sub", "")}</div>' if it.get("sub") else ""
        cards.append(
            f'<div class="dp-metric">'
            f'<div class="label">{it["label"]}</div>'
            f'<div class="value {cls}">{it["value"]}</div>'
            f'{sub}</div>'
        )
    st.markdown(
        f'<div class="dp-metrics">{"".join(cards)}</div>', unsafe_allow_html=True
    )


def panel(payload: str) -> None:
    """Generic bordered card."""
    st.markdown(f'<div class="dp-panel">{payload}</div>', unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="dp-section">{title}</div>', unsafe_allow_html=True)


def ai_callout(label: str, body: str) -> None:
    """Gradient-bordered AI explanation panel."""
    st.markdown(
        f'<div class="dp-ai"><span class="label">{label}</span>'
        f'<div class="body">{body}</div></div>',
        unsafe_allow_html=True,
    )


def stepper(states: list[tuple[str, str]]) -> None:
    """Pipeline progress stepper. states = [(label, state)] state in done/active/none."""
    parts = []
    for i, (label, state) in enumerate(states):
        cls = "dp-step"
        if state in ("done", "active"):
            cls += f" {state}"
        parts.append(
            f'<span class="{cls}"><span class="num">{i + 1}</span>{label}</span>'
        )
        if i < len(states) - 1:
            parts.append('<span class="dp-arrow">›</span>')
    st.markdown(f'<div class="dp-stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def sidebar_brand(title: str = "DataPilot", tagline: str = "AI-assisted data engineering") -> None:
    html = (
        f'<div class="dp-sidebar-brand">'
        f'<div class="logo">🧭 {title}</div>'
        f'<div class="tagline">{tagline}</div>'
        f'</div>'
    )
    st.sidebar.markdown(html, unsafe_allow_html=True)


def status_chip(label: str, live: bool) -> None:
    dot = 'class="dot dot-live"' if live else 'class="dot"'
    st.sidebar.markdown(
        f'<div class="dp-status-chip"><span {dot}></span>{label}</div>',
        unsafe_allow_html=True,
    )


def styled_dataframe(df: pd.DataFrame, *, max_rows: int | None = None) -> None:
    """Dataframe with the project's tone applied to numeric cells (best-effort)."""
    shown = df if max_rows is None else df.head(max_rows)
    style = shown.style

    numeric_cols = [c for c in shown.columns if pd.api.types.is_numeric_dtype(shown[c])]
    if numeric_cols:
        style = style.highlight_min(subset=numeric_cols, color="#7C6CFF44")
        style = style.highlight_max(subset=numeric_cols, color="#38D39F33")
    st.dataframe(style, width="stretch")