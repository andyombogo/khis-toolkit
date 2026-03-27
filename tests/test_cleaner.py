"""Placeholder tests for the Week 2 KHIS cleaning layer."""

import pytest
import pandas as pd

from khis.cleaner import clean_indicator_frame


def test_clean_indicator_frame_handles_empty_dataframe_without_crashing():
    """An empty DataFrame should round-trip safely through the scaffold cleaner."""
    df = pd.DataFrame(columns=["indicator_id", "org_unit_name", "period", "value"])
    cleaned = clean_indicator_frame(df)
    assert cleaned.equals(df)
    assert cleaned is not df


@pytest.mark.skip(
    reason="TODO: verify KHIS period parsing once clean() is implemented."
)
def test_clean_will_parse_monthly_weekly_quarterly_and_annual_periods():
    """TODO: ensure KHIS/DHIS2 period strings map to proper datetimes."""
    pass


@pytest.mark.skip(
    reason="TODO: verify missing-data flagging once flag_missing() is implemented."
)
def test_flag_missing_will_mark_high_missing_series():
    """TODO: ensure county-indicator combinations above the missing threshold are flagged."""
    pass


@pytest.mark.skip(
    reason="TODO: verify bounded imputation once fill_missing() is implemented."
)
def test_fill_missing_will_not_fill_gaps_longer_than_three_periods():
    """TODO: ensure long reporting gaps remain missing after imputation."""
    pass
