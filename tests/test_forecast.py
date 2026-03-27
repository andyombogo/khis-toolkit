"""Tests for the KHIS forecasting helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from khis.forecast import (
    anomaly_detection,
    forecast_all_counties,
    forecast_indicator_series,
    plot_forecast,
)


def _sample_forecast_frame() -> pd.DataFrame:
    """Create a deterministic monthly dataset for forecast smoke tests."""
    periods = pd.date_range("2023-01-01", periods=18, freq="MS")
    nairobi_values = np.linspace(20, 45, num=18)
    mombasa_values = np.linspace(12, 30, num=18)

    return pd.DataFrame(
        {
            "org_unit_name": ["Nairobi"] * 18 + ["Mombasa"] * 18,
            "indicator_name": ["Malaria Cases"] * 36,
            "period": list(periods) * 2,
            "value": list(nairobi_values) + list(mombasa_values),
        }
    )


def test_forecast_indicator_series_returns_required_columns():
    """The forecast wrapper should return the common output schema."""
    forecast_df = forecast_indicator_series(
        _sample_forecast_frame(),
        county="Nairobi",
        indicator="Malaria Cases",
        weeks_ahead=4,
        method="ensemble",
    )

    assert {
        "period",
        "actual",
        "forecast",
        "lower_bound",
        "upper_bound",
        "is_forecast",
    }.issubset(forecast_df.columns)
    assert int(forecast_df["is_forecast"].sum()) == 4


def test_forecast_all_counties_combines_each_county_result():
    """County batch forecasting should preserve the county label in the output."""
    combined = forecast_all_counties(
        _sample_forecast_frame(),
        indicator="Malaria Cases",
        periods_ahead=2,
        method="xgboost",
    )

    assert "county" in combined.columns
    assert {"Nairobi", "Mombasa"} == set(combined["county"])


def test_anomaly_detection_adds_anomaly_flag():
    """Anomaly detection should annotate observed periods with a boolean flag."""
    anomalies = anomaly_detection(
        _sample_forecast_frame(),
        county="Nairobi",
        indicator="Malaria Cases",
    )

    assert "anomaly_flag" in anomalies.columns
    assert anomalies["is_forecast"].eq(False).all()


def test_plot_forecast_returns_plotly_figure():
    """Forecast plots should be returned as Plotly figures."""
    forecast_df = forecast_indicator_series(
        _sample_forecast_frame(),
        county="Nairobi",
        indicator="Malaria Cases",
        weeks_ahead=2,
        method="xgboost",
    )

    figure = plot_forecast(forecast_df, title="Test Forecast")
    assert figure.layout.title.text == "Test Forecast"
