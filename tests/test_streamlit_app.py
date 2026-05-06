"""Tests for the Streamlit Community Cloud dashboard entrypoint."""

from __future__ import annotations

import os

import pandas as pd

from streamlit_app import (
    _apply_streamlit_secrets_to_environment,
    _feedback_brief_text,
    _quality_row_frame,
)


def test_streamlit_secrets_promote_to_environment(monkeypatch):
    """Streamlit secrets should feed the existing KHIS env-based settings."""
    for key in ("KHIS_DATA_MODE", "DHIS2_USERNAME"):
        monkeypatch.delenv(key, raising=False)

    _apply_streamlit_secrets_to_environment(
        {
            "KHIS_DATA_MODE": "offline_demo",
            "dhis2": {
                "DHIS2_USERNAME": "demo_user",
            },
        }
    )

    assert os.environ["KHIS_DATA_MODE"] == "offline_demo"
    assert os.environ["DHIS2_USERNAME"] == "demo_user"


def test_quality_row_frame_formats_dashboard_payload():
    """The Streamlit quality panel should display a compact county summary."""
    frame = _quality_row_frame(
        {
            "county": "Nairobi",
            "completeness_score": 91.24,
            "overall_quality_grade": "A",
            "outlier_count": 1,
            "late_reporter": False,
            "suspicious_zeros": False,
        }
    )

    assert isinstance(frame, pd.DataFrame)
    assert frame.loc[frame["Measure"] == "Completeness", "Value"].iloc[0] == "91.2%"
    assert frame.loc[frame["Measure"] == "Late reporter", "Value"].iloc[0] == "No"


def test_feedback_brief_text_uses_existing_briefing_note():
    """The Streamlit feedback panel should preserve the toolkit feedback copy."""
    text = _feedback_brief_text(
        {
            "briefing_note": "Pilot county: Nairobi\nSuggested next action: Validate.",
            "county": "Nairobi",
        }
    )

    assert text.startswith("Pilot county: Nairobi")
    assert "Suggested next action" in text
