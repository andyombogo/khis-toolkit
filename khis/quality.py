"""Data quality utilities for KHIS indicator completeness checks."""

from __future__ import annotations

from typing import Any

import pandas as pd


def compute_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return a simple dataset summary until richer quality checks are implemented."""
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_values": int(df.isna().sum().sum()),
    }
