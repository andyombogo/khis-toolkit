"""Simple tools for pulling, cleaning, and exploring county health data.

This package is designed for Kenya Health Records Officers and analysts who
work with DHIS2/KHIS data and need a straightforward workflow: connect to the
server, fetch county indicator data, clean the common reporting issues, review
data quality, and prepare simple forecasts or dashboards without stitching the
pieces together by hand.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .cleaner import clean, clean_indicator_frame, fill_missing, flag_missing, full_pipeline, standardise_county_names
from .connector import DHIS2Connector
from .counties import (
    KENYA_COUNTIES,
    get_counties_by_region,
    get_county,
    get_county_coordinates,
    list_counties,
    resolve_org_unit_id,
    update_from_api,
)
from .forecast import (
    anomaly_detection,
    ensemble_forecast,
    forecast_all_counties,
    forecast_indicator_series,
    plot_forecast,
    prophet_forecast,
    xgboost_forecast,
)
from .quality import (
    completeness_score,
    compute_quality_summary,
    county_scorecard,
    outlier_report,
    plot_quality_heatmap,
    timeliness_report,
    zero_report_analysis,
)


def connect(
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> DHIS2Connector:
    """Create a DHIS2/KHIS connector, loading `.env` values automatically."""
    return DHIS2Connector(base_url=base_url, username=username, password=password)


def list_indicators(
    conn: DHIS2Connector | None = None,
    search: str | None = None,
) -> Any:
    """List indicators available to the current KHIS/DHIS2 connection."""
    connector = conn or connect()
    return connector.get_indicators(search_term=search)


def get(
    conn: DHIS2Connector | None = None,
    indicator: Iterable[str] | str | None = None,
    counties: Iterable[str] | str | None = None,
    periods: Iterable[str] | str = "last_12_months",
    *,
    county: Iterable[str] | str | None = None,
    org_unit_ids: Iterable[str] | str | None = None,
    output_format: str = "dataframe",
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> Any:
    """Fetch analytics data using the guide-style KHIS public API."""
    connector = conn or connect(base_url=base_url, username=username, password=password)
    indicator_ids = indicator
    if indicator_ids is None:
        raise ValueError("Pass an indicator ID or iterable of indicator IDs via 'indicator'.")
    resolved_indicator_ids = _resolve_indicator_ids(connector, indicator_ids)

    resolved_org_units = _coerce_to_string_list(org_unit_ids)
    requested_counties = _coerce_to_string_list(counties) + _coerce_to_string_list(county)
    for county_name in requested_counties:
        try:
            resolved_org_units.append(connector.resolve_org_unit_id_by_name(county_name))
        except (ConnectionError, PermissionError, RuntimeError, ValueError):
            resolved_org_units.append(resolve_org_unit_id(county_name))

    if not resolved_org_units:
        raise ValueError("Pass county/counties or org_unit_ids when calling khis.get().")

    return connector.get_analytics(
        indicator_ids=resolved_indicator_ids,
        org_unit_ids=resolved_org_units,
        periods=periods,
        output_format=output_format,
    )


def quality_report(df: Any) -> Any:
    """Run the county-level quality scorecard and return its outputs."""
    return county_scorecard(df)


def forecast(df: Any, weeks_ahead: int = 4, **kwargs: Any) -> Any:
    """Run the current forecasting entrypoint with a friendly package wrapper."""
    return forecast_indicator_series(df, weeks_ahead=weeks_ahead, **kwargs)


__all__ = [
    "DHIS2Connector",
    "KENYA_COUNTIES",
    "anomaly_detection",
    "clean",
    "clean_indicator_frame",
    "connect",
    "compute_quality_summary",
    "completeness_score",
    "county_scorecard",
    "ensemble_forecast",
    "fill_missing",
    "flag_missing",
    "forecast",
    "forecast_all_counties",
    "forecast_indicator_series",
    "full_pipeline",
    "get",
    "get_counties_by_region",
    "get_county",
    "get_county_coordinates",
    "list_indicators",
    "list_counties",
    "outlier_report",
    "plot_forecast",
    "plot_quality_heatmap",
    "prophet_forecast",
    "quality_report",
    "resolve_org_unit_id",
    "standardise_county_names",
    "timeliness_report",
    "update_from_api",
    "xgboost_forecast",
    "zero_report_analysis",
]


def _coerce_to_string_list(values: Iterable[str] | str | None) -> list[str]:
    """Convert a string or iterable of strings into a clean string list."""
    if values is None:
        return []
    if isinstance(values, str):
        raw_parts = values.split(",")
    else:
        raw_parts = list(values)
    return [str(part).strip() for part in raw_parts if str(part).strip()]


def _resolve_indicator_ids(
    connector: DHIS2Connector,
    indicator_values: Iterable[str] | str,
) -> list[str]:
    """Resolve friendly indicator terms to DHIS2 indicator IDs when possible."""
    resolved: list[str] = []
    for value in _coerce_to_string_list(indicator_values):
        try:
            matches = connector.get_indicators(search_term=value)
        except Exception:
            matches = None

        if matches is None or matches.empty:
            resolved.append(value)
            continue

        exact_mask = (
            matches["id"].astype(str).str.lower().eq(value.lower())
            | matches["name"].astype(str).str.lower().eq(value.lower())
            | matches["code"].fillna("").astype(str).str.lower().eq(value.lower())
        )
        chosen = matches[exact_mask].iloc[0] if exact_mask.any() else matches.iloc[0]
        resolved.append(str(chosen["id"]))
    return resolved
