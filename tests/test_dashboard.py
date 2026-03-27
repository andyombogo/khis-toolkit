"""Tests for dashboard helper utilities."""

from __future__ import annotations

import pandas as pd

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

    figure = create_trend_chart(forecast_df, county="Nairobi", indicator="Malaria Cases")
    assert figure.layout.title.text == "Nairobi: Malaria Cases"
