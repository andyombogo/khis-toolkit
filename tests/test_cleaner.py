"""Smoke tests for KHIS cleaning helpers."""

import pandas as pd

from khis.cleaner import clean_indicator_frame


def test_clean_indicator_frame_returns_copy():
    """The scaffold cleaner should return a copy so callers can mutate safely."""
    df = pd.DataFrame({"value": [1, 2, 3]})
    cleaned = clean_indicator_frame(df)
    assert cleaned.equals(df)
    assert cleaned is not df
