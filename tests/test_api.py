"""Tests for the KHIS FastAPI service layer."""

from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api import CachedAPIState, create_app


def _cached_state() -> CachedAPIState:
    """Create a deterministic cached API state for endpoint tests."""
    periods = pd.date_range("2024-01-01", periods=12, freq="MS")
    data = pd.DataFrame(
        {
            "indicator_id": ["offline_malaria_cases"] * 12,
            "indicator_name": ["Malaria Cases (Offline Demo)"] * 12,
            "org_unit_id": ["OFFLINE_47"] * 12,
            "org_unit_name": ["Nairobi"] * 12,
            "period": periods,
            "value": [12, 13, 15, 14, 17, 18, 20, 19, 21, 22, 24, 25],
        }
    )
    scorecard = pd.DataFrame(
        {
            "county": ["Nairobi"],
            "completeness_score": [100.0],
            "outlier_count": [0],
            "late_reporter": [False],
            "suspicious_zeros": [False],
            "overall_quality_grade": ["A"],
        }
    )
    mental_health_data = pd.DataFrame(
        {
            "indicator_id": [
                "demo_mental_health_outpatient_visits",
                "demo_psychosocial_support_sessions",
            ],
            "indicator_name": [
                "Mental Health Outpatient Visits",
                "Psychosocial Support Sessions",
            ],
            "indicator_slug": [
                "mental_health_outpatient_visits",
                "psychosocial_support_sessions",
            ],
            "indicator_domain": [
                "Mental health services",
                "Psychosocial support",
            ],
            "indicator_package": ["mns_core", "mns_core"],
            "org_unit_id": ["KE47", "KE47"],
            "org_unit_name": ["Nairobi", "Nairobi"],
            "period": [periods[-1], periods[-1]],
            "value": [18.0, 11.0],
            "data_source": ["demo_fallback", "demo_fallback"],
        }
    )
    mental_health_summary = pd.DataFrame(
        {
            "county": ["Nairobi"],
            "latest_period": ["2024-12-01"],
            "tracked_indicators": [2],
            "latest_total_value": [29.0],
            "average_latest_value": [14.5],
            "trend_direction": ["Rising"],
            "burden_band": ["High"],
            "county_percentile": [1.0],
            "data_source": ["demo_fallback"],
        }
    )
    return CachedAPIState(
        data=data,
        scorecard=scorecard,
        mental_health_data=mental_health_data,
        mental_health_summary=mental_health_summary,
        summary="Reviewed 1 counties. 1 counties scored A or B, while 0 counties scored D or F. 0 counties were late reporters and 0 showed suspicious zero patterns.",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        last_updated="2026-03-27 12:00 UTC",
        banner="Offline test state",
    )


def test_health_and_counties_endpoints_work_in_development_mode():
    """Health and counties endpoints should work without auth when no key is configured."""
    app = create_app(api_key=None)
    client = TestClient(app)

    health = client.get("/health")
    counties = client.get("/counties")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "data_mode" in health.json()
    assert counties.status_code == 200
    assert len(counties.json()) == 47


def test_counties_endpoint_requires_api_key_when_configured():
    """Protected endpoints should reject requests without the configured API key."""
    app = create_app(api_key="secret-key")
    client = TestClient(app)

    unauthorized = client.get("/counties")
    authorized = client.get("/counties", headers={"X-API-Key": "secret-key"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_quality_and_forecast_endpoints_use_cached_state():
    """Quality, forecast, and mental-health endpoints should use cached state."""
    app = create_app(api_key=None)
    app.state.cached_state = _cached_state()
    client = TestClient(app)

    quality = client.get("/quality/Nairobi")
    mental_health = client.get("/mental-health/Nairobi")
    mental_health_summary = client.get("/mental-health/summary")
    forecast = client.post(
        "/forecast",
        json={
            "county": "Nairobi",
            "indicator": "Malaria Cases (Offline Demo)",
            "weeks_ahead": 2,
            "method": "xgboost",
        },
    )

    assert quality.status_code == 200
    assert quality.json()["county"] == "Nairobi"
    assert mental_health.status_code == 200
    assert mental_health.json()["burden_band"] == "High"
    assert len(mental_health.json()["indicator_snapshot"]) == 2
    assert mental_health_summary.status_code == 200
    assert mental_health_summary.json()[0]["county"] == "Nairobi"
    assert forecast.status_code == 200
    assert len(forecast.json()) >= 2


def test_api_offline_mode_avoids_external_connector_calls(monkeypatch):
    """offline_demo mode should allow the API to boot without external DHIS2 access."""
    monkeypatch.setenv("KHIS_DATA_MODE", "offline_demo")

    def _unexpected_connect(*args, **kwargs):
        raise AssertionError("khis.connect() should not be called in offline_demo mode")

    with patch("src.api.khis.connect", side_effect=_unexpected_connect):
        app = create_app(api_key=None)

    client = TestClient(app)
    health = client.get("/health")
    summary = client.get("/mental-health/summary")

    assert health.status_code == 200
    assert health.json()["data_mode"] == "offline_demo"
    assert summary.status_code == 200
