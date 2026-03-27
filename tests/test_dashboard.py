"""Tests for dashboard helper utilities."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from dashboard.app import DashboardState, create_app
from dashboard.map import create_county_map, create_quality_table, create_trend_chart


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
    )
    with patch("dashboard.app._load_dashboard_state", return_value=state):
        app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/api/mental-health/Nairobi")

    assert response.status_code == 200
    assert response.get_json()["burden_band"] == "High"


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
