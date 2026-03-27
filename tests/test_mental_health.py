"""Tests for the curated KHIS mental-health workflow."""

from __future__ import annotations

from unittest.mock import Mock

import pandas as pd

import khis


def test_list_mental_health_indicators_exposes_curated_catalog():
    """The public catalog should include the MNS core indicator package."""
    catalog = khis.list_mental_health_indicators()

    assert not catalog.empty
    assert "mental_health_outpatient_visits" in catalog["slug"].tolist()
    assert (catalog["package"] == "mns_core").any()


def test_pull_mental_health_data_falls_back_to_demo_series_when_live_lookup_fails():
    """The workflow should stay usable even when live MNS indicators are unavailable."""
    connector = Mock()
    connector.using_demo_server = True
    connector.get_indicators.side_effect = ConnectionError("demo unavailable")

    result = khis.pull_mental_health_data(
        connector,
        counties=["Nairobi", "Mombasa"],
        periods="last_6_months",
    )

    assert not result.empty
    assert set(result["org_unit_name"]) == {"Nairobi", "Mombasa"}
    assert "indicator_slug" in result.columns
    assert (result["data_source"] == "demo_fallback").all()


def test_pull_mental_health_data_supports_offline_mode_without_connector():
    """Offline demo mode should not require a live connector object."""
    result = khis.pull_mental_health_data(
        connector=None,
        counties=["Nairobi"],
        periods="last_3_months",
    )

    assert not result.empty
    assert set(result["org_unit_name"]) == {"Nairobi"}
    assert (result["data_source"] == "demo_fallback").all()


def test_summarise_county_mental_health_builds_county_snapshot():
    """County summaries should expose burden bands and trend direction."""
    frame = pd.DataFrame(
        {
            "indicator_id": [
                "demo_mental_health_outpatient_visits",
                "demo_mental_health_outpatient_visits",
                "demo_psychosocial_support_sessions",
                "demo_psychosocial_support_sessions",
            ],
            "indicator_name": [
                "Mental Health Outpatient Visits",
                "Mental Health Outpatient Visits",
                "Psychosocial Support Sessions",
                "Psychosocial Support Sessions",
            ],
            "indicator_slug": [
                "mental_health_outpatient_visits",
                "mental_health_outpatient_visits",
                "psychosocial_support_sessions",
                "psychosocial_support_sessions",
            ],
            "indicator_domain": [
                "Mental health services",
                "Mental health services",
                "Psychosocial support",
                "Psychosocial support",
            ],
            "org_unit_name": ["Nairobi", "Nairobi", "Nairobi", "Nairobi"],
            "period": ["2024-11-01", "2024-12-01", "2024-11-01", "2024-12-01"],
            "value": [13, 17, 8, 11],
            "data_source": ["demo_fallback"] * 4,
        }
    )

    summary = khis.summarise_county_mental_health(frame)
    snapshot = khis.county_indicator_snapshot(frame, "Nairobi")

    assert len(summary) == 1
    assert summary.iloc[0]["county"] == "Nairobi"
    assert summary.iloc[0]["tracked_indicators"] == 2
    assert summary.iloc[0]["trend_direction"] in {
        "Rising",
        "Stable",
        "Falling",
        "Emerging",
    }
    assert not snapshot.empty
    assert snapshot.iloc[0]["county"] == "Nairobi"
