"""Streamlit app smoke tests using streamlit.testing (no real browser)."""

from pathlib import Path

import pandas as pd
import pytest

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "main.py"


@pytest.mark.skipif(
    not hasattr(__import__("streamlit.testing.v1", fromlist=["AppTest"]), "AppTest"),
    reason="streamlit.testing not available",
)
def test_app_renders_dashboard_default():
    at = AppTest.from_file(str(APP), default_timeout=15)
    at.run()
    assert not at.exception
    assert any("Dashboard" in str(r.value) for r in at.radio)
    assert any("Is your data ready" in str(h.value) for h in at.markdown)


def test_app_upload_run_pipeline():
    csv = b"a,b\n1,x\n2,y\n3,z\n"

    at = AppTest.from_file(str(APP), default_timeout=15)
    at.run()

    # navigate to Upload page via sidebar radio
    at.sidebar.radio[0].set_value("📤 Upload Data")
    at.run()
    assert not at.exception

    # drop a file, the action button label is "Analyze this file"
    at.file_uploader[0].set_value([("demo.csv", csv, "text/csv")])
    assert len(at.button) == 0 or any("Analyze this file" in b.label for b in at.button) or any("🚀 Analyze this file" in str(b.label) for b in at.button)
    at.run()
    assert not at.exception

    hit = None
    for b in at.button:
        if "Analyze this file" in b.label:
            hit = b
    assert hit is not None, [b.label for b in at.button]
    hit.click()
    at.run()
    assert not at.exception
    assert any("scanned" in str(m.value) for m in at.success)