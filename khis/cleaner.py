"""Data cleaning helpers for KHIS indicator extracts."""

from __future__ import annotations

import pandas as pd


def clean_indicator_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a shallow cleaned copy of an indicator frame scaffold."""
    return df.copy()
