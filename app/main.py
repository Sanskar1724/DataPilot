"""DataPilot Streamlit entrypoint — command center for your data.

Flow of pages mirrors the hero's journey: land on the dashboard, upload a messy
file, watch the quality forensics, let AI draft the cleanup, approve, download
a clean dataset.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when launched as `streamlit run app/main.py`
# (Streamlit only adds the script's own directory to sys.path).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.ui import dashboard, pipeline_view, quality_report, upload  # noqa: E402
from app.ui.theme import apply_theme, sidebar_brand, status_chip  # noqa: E402
from app.utils.config import get_settings  # noqa: E402
from app.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

st.set_page_config(
    page_title="DataPilot — AI-Assisted Data Engineering",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "🔭 Dashboard": dashboard.render,
    "📤 Upload Data": upload.render,
    "🔍 Quality Report": quality_report.render,
    "🤖 AI Fix Plan": pipeline_view.render,
}


def main() -> None:
    apply_theme()
    settings = get_settings()
    sidebar_brand()
    st.sidebar.caption("_Local-first. Deterministic engine, AI reasoning._")

    status_chip("Engine · Pandas rules", live=True)
    ai_live = settings.ai_enabled and settings.has_api_key
    status_chip(f"AI · {settings.openrouter_model}"[:34], live=ai_live)

    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navigate",
        list(PAGES),
        label_visibility="collapsed",
        captions=["Your data, at a glance", "Feed the machine", "Forensics & AI story", "Plan, approve, ship"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Made with 💜 for analytics people")

    PAGES[page]()


if __name__ == "__main__":
    main()