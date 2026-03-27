"""Smoke tests for KHIS data quality helpers."""

import pandas as pd

from khis.quality import compute_quality_summary


def test_compute_quality_summary_counts_rows_and_missing_values():
    """The quality scaffold should expose a minimal dataset summary."""
    df = pd.DataFrame({"a": [1, None], "b": [2, 3]})
    summary = compute_quality_summary(df)
    assert summary["rows"] == 2
    assert summary["missing_values"] == 1
