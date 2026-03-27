"""Tests for KHIS data quality helpers."""

import pandas as pd

from khis.quality import completeness_score, compute_quality_summary, county_scorecard


def test_compute_quality_summary_counts_rows_and_missing_values():
    """The quality scaffold should expose a minimal dataset summary."""
    df = pd.DataFrame({"a": [1, None], "b": [2, 3]})
    summary = compute_quality_summary(df)
    assert summary["rows"] == 2
    assert summary["missing_values"] == 1


def test_completeness_score_classifies_county_indicator_series():
    """Completeness should be calculated per county and indicator series."""
    df = pd.DataFrame(
        {
            "org_unit_name": ["Nairobi", "Nairobi", "Nairobi", "Mombasa"],
            "indicator_name": [
                "Malaria Cases",
                "Malaria Cases",
                "Malaria Cases",
                "Malaria Cases",
            ],
            "value": [10, None, 12, 8],
        }
    )

    result = completeness_score(df, expected_periods=3)

    nairobi_row = result[result["county"] == "Nairobi"].iloc[0]
    assert nairobi_row["reported_periods"] == 2
    assert nairobi_row["completeness_pct"] == 66.7
    assert nairobi_row["completeness_class"] == "poor"


def test_county_scorecard_returns_county_summary_and_text():
    """The scorecard should return both a county summary table and narrative text."""
    df = pd.DataFrame(
        {
            "org_unit_name": ["Nairobi"] * 4 + ["Mombasa"] * 4,
            "indicator_name": ["Malaria Cases"] * 8,
            "period": pd.to_datetime(
                ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"] * 2
            ),
            "submission_date": pd.to_datetime(
                [
                    "2024-01-20",
                    "2024-02-20",
                    "2024-03-20",
                    "2024-04-20",
                    "2024-01-10",
                    "2024-02-10",
                    "2024-03-10",
                    "2024-04-10",
                ]
            ),
            "value": [10, 11, 12, 13, 0, 0, 0, 5],
        }
    )

    scorecard, summary = county_scorecard(df)

    assert {
        "county",
        "completeness_score",
        "outlier_count",
        "overall_quality_grade",
    }.issubset(scorecard.columns)
    assert "Reviewed 2 counties" in summary
