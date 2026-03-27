"""Tests for stable public-demo analytics helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pandas as pd

from khis.demo import (
    DEMO_ANALYTICS_PERIODS,
    build_demo_indicator_frame,
    get_demo_indicators,
    get_demo_org_units,
)


def test_get_demo_indicators_falls_back_when_live_lookup_fails():
    """Demo indicator discovery should still return a malaria-like catalog when offline."""
    connector = Mock()
    connector.get_indicators.side_effect = ConnectionError("demo down")

    result = get_demo_indicators(connector, search_term="malaria")

    assert not result.empty
    assert "malaria" in result.iloc[0]["name"].lower()


def test_get_demo_org_units_fall_back_when_live_lookup_fails():
    """Demo org-unit discovery should still yield a small displayable frame."""
    connector = Mock()
    connector.get_org_units.side_effect = ConnectionError("demo down")

    result = get_demo_org_units(connector, limit=2)

    assert result.columns.tolist() == ["id", "name"]
    assert len(result) == 2


def test_build_demo_indicator_frame_returns_live_data_when_available():
    """Live demo analytics should be passed through unchanged when present."""
    connector = Mock()
    live_frame = pd.DataFrame(
        [
            {
                "indicator_id": "abc123",
                "indicator_name": "Malaria Cases",
                "org_unit_id": "OU_1",
                "org_unit_name": "Demo One",
                "period": "202401",
                "value": 17.0,
            }
        ]
    )
    connector.get_analytics.return_value = live_frame
    org_units = pd.DataFrame([{"id": "OU_1", "name": "Demo One"}])

    result = build_demo_indicator_frame(
        connector,
        indicator_id="abc123",
        indicator_name="Malaria Cases",
        org_units=org_units,
    )

    assert result.equals(live_frame)


def test_build_demo_indicator_frame_falls_back_to_synthetic_series():
    """Empty live pulls should still produce a deterministic monthly demo frame."""
    connector = Mock()
    connector.get_analytics.return_value = pd.DataFrame()
    org_units = pd.DataFrame(
        [
            {"id": "OU_1", "name": "Demo One"},
            {"id": "OU_2", "name": "Demo Two"},
        ]
    )

    result = build_demo_indicator_frame(
        connector,
        indicator_id="abc123",
        indicator_name="Malaria Cases",
        org_units=org_units,
    )

    assert not result.empty
    assert result["org_unit_name"].nunique() == 2
    assert result["period"].nunique() == len(DEMO_ANALYTICS_PERIODS)
    assert (result["value"] > 0).all()
