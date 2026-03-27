"""Stable demo-data helpers for notebooks, dashboards, and public examples.

The public DHIS2 demo instance is useful for testing connector logic, but its
analytics data can be sparse or out of date relative to rolling periods such as
``LAST_12_MONTHS``. These helpers provide a small, repeatable analytics frame
for package demos by first trying a real demo-server pull and then falling back
to a deterministic synthetic series when the public instance has no data for
the requested slice.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

DEMO_ANALYTICS_PERIODS = tuple(
    f"{year}{month:02d}" for year in (2023, 2024) for month in range(1, 13)
)
DEMO_INDICATOR_ROWS = (
    {
        "id": "demo_malaria_cases",
        "name": "Demo Malaria Cases",
        "short_name": "Demo Malaria",
        "code": "DEMO_MALARIA",
        "description": "Stable fallback indicator metadata for public demo workflows.",
    },
)
DEMO_ORG_UNIT_ROWS = (
    {"id": "DEMO_OU_001", "name": "Demo District One"},
    {"id": "DEMO_OU_002", "name": "Demo District Two"},
    {"id": "DEMO_OU_003", "name": "Demo District Three"},
)


def get_demo_indicators(connector, search_term: str | None = None) -> pd.DataFrame:
    """Return live demo indicators, or a fallback catalog if the demo is down."""
    try:
        indicators = connector.get_indicators(search_term=search_term)
    except Exception:
        indicators = pd.DataFrame()

    if not indicators.empty:
        return indicators

    fallback = pd.DataFrame.from_records(DEMO_INDICATOR_ROWS)
    if not search_term:
        return fallback

    search_value = search_term.lower()
    mask = (
        fallback["name"].str.lower().str.contains(search_value)
        | fallback["short_name"].str.lower().str.contains(search_value)
        | fallback["code"].str.lower().str.contains(search_value)
    )
    filtered = fallback[mask].reset_index(drop=True)
    return filtered if not filtered.empty else fallback


def get_demo_org_units(
    connector, limit: int = 3, level: int | None = 3
) -> pd.DataFrame:
    """Return live demo org units, or a small fallback set when the demo is unavailable."""
    try:
        org_units = (
            connector.get_org_units(level=level)
            if level is not None
            else connector.get_org_units()
        )
        if org_units.empty and level is not None:
            org_units = connector.get_org_units()
    except Exception:
        org_units = pd.DataFrame()

    if not org_units.empty:
        return org_units[["id", "name"]].dropna().head(limit).reset_index(drop=True)

    return (
        pd.DataFrame.from_records(DEMO_ORG_UNIT_ROWS).head(limit).reset_index(drop=True)
    )


def build_demo_indicator_frame(
    connector,
    indicator_id: str,
    indicator_name: str,
    org_units: pd.DataFrame,
    periods: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Return a demo analytics frame that stays usable even when live data is sparse.

    Parameters
    ----------
    connector:
        Connected DHIS2 client used for the initial live analytics request.
    indicator_id:
        DHIS2 indicator identifier selected for the demo workflow.
    indicator_name:
        Display name for the chosen indicator.
    org_units:
        DataFrame containing at least ``id`` and ``name`` columns.
    periods:
        Optional iterable of monthly period IDs. If omitted, a fixed 2023-2024
        monthly window is used because it is more reliable on the public demo
        instance than rolling relative periods.

    Returns
    -------
    pandas.DataFrame
        Analytics-style table with stable demo data suitable for cleaning,
        quality scoring, forecasting, and map previews.
    """
    selected_org_units = (
        org_units[["id", "name"]].dropna().head(3).reset_index(drop=True)
    )
    if selected_org_units.empty:
        raise ValueError("org_units must include at least one row with id and name.")

    resolved_periods = list(periods or DEMO_ANALYTICS_PERIODS)
    try:
        live_frame = connector.get_analytics(
            indicator_ids=indicator_id,
            org_unit_ids=selected_org_units["id"].tolist(),
            periods=resolved_periods,
        )
    except Exception:
        live_frame = pd.DataFrame()

    if not live_frame.empty:
        return live_frame

    period_index = pd.to_datetime(resolved_periods, format="%Y%m", errors="coerce")
    period_index = pd.DatetimeIndex(period_index[~pd.isna(period_index)])
    if period_index.empty:
        period_index = pd.date_range("2023-01-01", periods=24, freq="MS")

    records: list[dict[str, object]] = []
    for org_unit_position, row in selected_org_units.iterrows():
        base = 18.0 + (org_unit_position * 6.0)
        for month_position, period in enumerate(period_index):
            seasonal = ((month_position % 6) + 1) * 1.35
            trend = month_position * 0.45
            value = round(base + seasonal + trend, 2)
            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "org_unit_id": str(row["id"]),
                    "org_unit_name": str(row["name"]),
                    "period": period.strftime("%Y%m"),
                    "value": value,
                }
            )

    return pd.DataFrame.from_records(records)
