"""Tests for dashboard helper utilities."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from dashboard.app import DashboardState, create_app
from dashboard.map import (
    create_county_map,
    create_quality_table,
    create_trend_chart,
    render_selected_county_map_html,
)


def test_create_county_map_returns_renderable_object():
    """The county map helper should return an object that can render HTML."""
    data = pd.DataFrame(
        {
            "county": ["Nairobi", "Mombasa", "Kisumu"],
            "latest_value": [18.4, 12.0, 9.7],
        }
    )

    map_object = create_county_map(data, value_col="latest_value")
    rendered = map_object.get_root().render()

    assert "Nairobi" in rendered


def test_render_selected_county_map_html_highlights_one_county():
    """The dashboard map HTML should include a visible selected-county summary."""
    data = pd.DataFrame(
        {
            "county": ["Nairobi", "Mombasa", "Kisumu"],
            "latest_value": [18.4, 12.0, 9.7],
        }
    )

    rendered = render_selected_county_map_html(
        data,
        value_col="latest_value",
        selected_county="Nairobi",
    )

    assert "<svg" in rendered
    assert "Nairobi" in rendered
    assert "Nairobi highlighted" in rendered


def test_create_quality_table_renders_grade_labels():
    """The quality table helper should render county grade values into HTML."""
    scorecard = pd.DataFrame(
        {
            "county": ["Nairobi", "Mombasa"],
            "completeness_score": [91.4, 76.8],
            "outlier_count": [1, 3],
            "late_reporter": [False, True],
            "suspicious_zeros": [False, False],
            "overall_quality_grade": ["A", "C"],
        }
    )

    html = create_quality_table(scorecard)
    assert "Nairobi" in html
    assert "<strong>A</strong>" in html


def test_create_trend_chart_returns_plotly_figure():
    """The trend helper should render a chart from forecast-like data."""
    forecast_df = pd.DataFrame(
        {
            "county": ["Nairobi"] * 4,
            "period": pd.date_range("2024-01-01", periods=4, freq="MS"),
            "actual": [11, 13, 15, None],
            "forecast": [11.5, 12.8, 15.4, 16.1],
            "lower_bound": [10.0, 11.2, 13.8, 14.9],
            "upper_bound": [13.0, 14.5, 17.1, 17.4],
            "is_forecast": [False, False, False, True],
        }
    )

    figure = create_trend_chart(
        forecast_df, county="Nairobi", indicator="Malaria Cases"
    )
    assert figure.layout.title.text == "Nairobi: Malaria Cases"


def test_dashboard_exposes_mental_health_county_endpoint():
    """The Flask dashboard should return cached mental-health county summaries."""
    state = DashboardState(
        data=pd.DataFrame(
            {
                "indicator_id": ["offline_malaria_cases"],
                "indicator_name": ["Malaria Cases (Offline Demo)"],
                "org_unit_id": ["OFFLINE_47"],
                "org_unit_name": ["Nairobi"],
                "period": [pd.Timestamp("2024-12-01")],
                "value": [18.0],
            }
        ),
        scorecard=pd.DataFrame(
            {
                "county": ["Nairobi"],
                "completeness_score": [100.0],
                "outlier_count": [0],
                "late_reporter": [False],
                "suspicious_zeros": [False],
                "overall_quality_grade": ["A"],
            }
        ),
        mental_health_data=pd.DataFrame(
            {
                "indicator_id": ["demo_mental_health_outpatient_visits"],
                "indicator_name": ["Mental Health Outpatient Visits"],
                "indicator_slug": ["mental_health_outpatient_visits"],
                "indicator_domain": ["Mental health services"],
                "indicator_package": ["mns_core"],
                "org_unit_id": ["KE47"],
                "org_unit_name": ["Nairobi"],
                "period": [pd.Timestamp("2024-12-01")],
                "value": [21.0],
                "data_source": ["demo_fallback"],
            }
        ),
        mental_health_summary=pd.DataFrame(
            {
                "county": ["Nairobi"],
                "latest_period": ["2024-12-01"],
                "tracked_indicators": [1],
                "latest_total_value": [21.0],
                "average_latest_value": [21.0],
                "trend_direction": ["Rising"],
                "burden_band": ["High"],
                "county_percentile": [1.0],
                "data_source": ["demo_fallback"],
            }
        ),
        quality_summary="Demo summary",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        banner="Offline demo banner",
        last_updated="2026-03-27 12:00 UTC",
        data_mode="offline_demo",
    )
    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/api/mental-health/Nairobi")

    assert response.status_code == 200
    assert response.get_json()["burden_band"] == "High"


def test_dashboard_exposes_county_map_endpoint():
    """The dashboard should return county map HTML for the selected county."""
    state = DashboardState(
        data=pd.DataFrame(
            {
                "indicator_id": ["offline_malaria_cases"] * 2,
                "indicator_name": ["Malaria Cases (Offline Demo)"] * 2,
                "org_unit_id": ["OFFLINE_47", "OFFLINE_01"],
                "org_unit_name": ["Nairobi", "Mombasa"],
                "period": [pd.Timestamp("2024-12-01"), pd.Timestamp("2024-12-01")],
                "value": [18.0, 14.0],
            }
        ),
        scorecard=pd.DataFrame(
            {
                "county": ["Nairobi", "Mombasa"],
                "completeness_score": [100.0, 98.0],
                "outlier_count": [0, 1],
                "late_reporter": [False, False],
                "suspicious_zeros": [False, False],
                "overall_quality_grade": ["A", "B"],
            }
        ),
        mental_health_data=pd.DataFrame(),
        mental_health_summary=pd.DataFrame(),
        quality_summary="Demo summary",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        banner="Offline demo banner",
        last_updated="2026-03-30 12:00 UTC",
        data_mode="offline_demo",
    )
    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/api/map/Nairobi")

    assert response.status_code == 200
    assert "<svg" in response.get_json()["html"]
    assert response.get_json()["county"] == "Nairobi"


def test_dashboard_forecast_endpoint_falls_back_to_observed_series():
    """The dashboard should not 500 when forecast generation fails."""
    state = DashboardState(
        data=pd.DataFrame(
            {
                "indicator_id": ["offline_malaria_cases"] * 2,
                "indicator_name": ["Malaria Cases (Offline Demo)"] * 2,
                "org_unit_id": ["OFFLINE_47"] * 2,
                "org_unit_name": ["Nairobi"] * 2,
                "period": [pd.Timestamp("2024-11-01"), pd.Timestamp("2024-12-01")],
                "value": [18.0, 19.0],
            }
        ),
        scorecard=pd.DataFrame(
            {
                "county": ["Nairobi"],
                "completeness_score": [100.0],
                "outlier_count": [0],
                "late_reporter": [False],
                "suspicious_zeros": [False],
                "overall_quality_grade": ["A"],
            }
        ),
        mental_health_data=pd.DataFrame(
            {
                "indicator_id": ["demo_mental_health_outpatient_visits"],
                "indicator_name": ["Mental Health Outpatient Visits"],
                "indicator_slug": ["mental_health_outpatient_visits"],
                "indicator_domain": ["Mental health services"],
                "indicator_package": ["mns_core"],
                "org_unit_id": ["KE47"],
                "org_unit_name": ["Nairobi"],
                "period": [pd.Timestamp("2024-12-01")],
                "value": [21.0],
                "data_source": ["demo_fallback"],
            }
        ),
        mental_health_summary=pd.DataFrame(
            {
                "county": ["Nairobi"],
                "latest_period": ["2024-12-01"],
                "tracked_indicators": [1],
                "latest_total_value": [21.0],
                "average_latest_value": [21.0],
                "trend_direction": ["Rising"],
                "burden_band": ["High"],
                "county_percentile": [1.0],
                "data_source": ["demo_fallback"],
            }
        ),
        quality_summary="Demo summary",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        banner="Offline demo banner",
        last_updated="2026-03-27 12:00 UTC",
        data_mode="offline_demo",
    )

    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    with patch(
        "dashboard.app.khis.forecast_indicator_series",
        side_effect=RuntimeError("forecast unavailable"),
    ):
        client = app.test_client()
        forecast_response = client.get(
            "/api/forecast/Nairobi/Malaria%20Cases%20(Offline%20Demo)"
        )
        root_response = client.get("/")

    assert forecast_response.status_code == 200
    payload = forecast_response.get_json()
    assert len(payload) == 2
    assert payload[0]["is_forecast"] is False
    assert root_response.status_code == 200


def test_dashboard_root_handles_empty_loaded_dataset():
    """The dashboard home page should still render when no county data loaded."""
    state = DashboardState(
        data=pd.DataFrame(
            columns=[
                "indicator_id",
                "indicator_name",
                "org_unit_id",
                "org_unit_name",
                "period",
                "value",
            ]
        ),
        scorecard=pd.DataFrame(
            columns=[
                "county",
                "completeness_score",
                "outlier_count",
                "late_reporter",
                "suspicious_zeros",
                "overall_quality_grade",
            ]
        ),
        mental_health_data=pd.DataFrame(
            columns=[
                "indicator_id",
                "indicator_name",
                "indicator_slug",
                "indicator_domain",
                "indicator_package",
                "org_unit_id",
                "org_unit_name",
                "period",
                "value",
                "data_source",
            ]
        ),
        mental_health_summary=pd.DataFrame(
            columns=[
                "county",
                "latest_period",
                "tracked_indicators",
                "latest_total_value",
                "average_latest_value",
                "trend_direction",
                "burden_band",
                "county_percentile",
                "data_source",
            ]
        ),
        quality_summary="No quality scorecard is available yet.",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        banner="Offline demo banner",
        last_updated="2026-03-27 12:00 UTC",
        data_mode="offline_demo",
    )

    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert "No usable series is available for this county yet." in response.get_data(
        as_text=True
    )


def test_dashboard_offline_mode_avoids_external_connector_calls(monkeypatch):
    """offline_demo mode should boot from bundled data without connecting outward."""
    monkeypatch.setenv("KHIS_DATA_MODE", "offline_demo")

    def _unexpected_connect(*args, **kwargs):
        raise AssertionError("khis.connect() should not be called in offline_demo mode")

    with patch("dashboard.app.khis.connect", side_effect=_unexpected_connect):
        app = create_app()

    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["data_mode"] == "offline_demo"


def test_dashboard_root_surfaces_pitch_ready_demo_copy():
    """The homepage should explain that the public link is a pre-access KHIS demo."""
    state = DashboardState(
        data=pd.DataFrame(
            {
                "indicator_id": ["offline_malaria_cases"] * 2,
                "indicator_name": ["Malaria Cases (Offline Demo)"] * 2,
                "org_unit_id": ["OFFLINE_47"] * 2,
                "org_unit_name": ["Nairobi", "Mombasa"],
                "period": [pd.Timestamp("2024-11-01"), pd.Timestamp("2024-12-01")],
                "value": [18.0, 15.0],
            }
        ),
        scorecard=pd.DataFrame(
            {
                "county": ["Nairobi", "Mombasa"],
                "completeness_score": [100.0, 92.0],
                "outlier_count": [0, 1],
                "late_reporter": [False, False],
                "suspicious_zeros": [False, False],
                "overall_quality_grade": ["A", "B"],
            }
        ),
        mental_health_data=pd.DataFrame(
            {
                "indicator_id": ["demo_mental_health_outpatient_visits"],
                "indicator_name": ["Mental Health Outpatient Visits"],
                "indicator_slug": ["mental_health_outpatient_visits"],
                "indicator_domain": ["Mental health services"],
                "indicator_package": ["mns_core"],
                "org_unit_id": ["KE47"],
                "org_unit_name": ["Nairobi"],
                "period": [pd.Timestamp("2024-12-01")],
                "value": [21.0],
                "data_source": ["demo_fallback"],
            }
        ),
        mental_health_summary=pd.DataFrame(
            {
                "county": ["Nairobi"],
                "latest_period": ["2024-12-01"],
                "tracked_indicators": [1],
                "latest_total_value": [21.0],
                "average_latest_value": [21.0],
                "trend_direction": ["Rising"],
                "burden_band": ["High"],
                "county_percentile": [1.0],
                "data_source": ["demo_fallback"],
            }
        ),
        quality_summary="Demo summary",
        indicator_name="Malaria Cases (Offline Demo)",
        indicator_id="offline_malaria_cases",
        banner="Offline demo banner",
        last_updated="2026-03-28 09:30 UTC",
        data_mode="offline_demo",
    )

    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Pitch-ready county analytics walkthrough before KHIS access" in html
    assert "What This Demo Proves" in html
    assert "Pilot Ask" in html
    assert "<svg" in html
