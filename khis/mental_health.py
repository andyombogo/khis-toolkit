"""Mental-health indicator workflows for Kenya DHIS2/KHIS analytics.

This module adds a Kenya-focused starting point for Mental, Neurological, and
Substance-use (MNS) workflows on top of the general KHIS Toolkit connector.
Real KHIS indicator names and IDs vary by deployment and permissions, so the
workflow uses a curated catalog of search terms and falls back to deterministic
demo data when live mental-health indicators are unavailable.

The goal is not to claim a universal national mental-health schema. The goal is
to give county teams and researchers a usable workflow for exploration,
dashboarding, and downstream integration while they wait for live KHIS access
or local indicator mapping.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from .counties import get_county, list_counties

MENTAL_HEALTH_INDICATOR_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "slug": "mental_health_outpatient_visits",
        "display_name": "Mental Health Outpatient Visits",
        "package": "mns_core",
        "domain": "Mental health services",
        "search_terms": (
            "mental health",
            "psychiatry",
            "outpatient mental",
        ),
        "description": "General outpatient visits recorded for mental-health care.",
        "default_periods": "last_12_months",
        "demo_weight": 1.45,
    },
    {
        "slug": "psychosocial_support_sessions",
        "display_name": "Psychosocial Support Sessions",
        "package": "mns_core",
        "domain": "Psychosocial support",
        "search_terms": (
            "psychosocial",
            "counselling",
            "counseling",
        ),
        "description": "Psychosocial or counselling sessions delivered through care services.",
        "default_periods": "last_12_months",
        "demo_weight": 1.15,
    },
    {
        "slug": "substance_use_treatment_visits",
        "display_name": "Substance Use Treatment Visits",
        "package": "mns_core",
        "domain": "Substance use services",
        "search_terms": (
            "substance use",
            "drug treatment",
            "alcohol",
        ),
        "description": "Treatment contacts related to alcohol or substance-use services.",
        "default_periods": "last_12_months",
        "demo_weight": 1.05,
    },
    {
        "slug": "epilepsy_follow_up_visits",
        "display_name": "Epilepsy Follow-up Visits",
        "package": "mns_core",
        "domain": "Neurological follow-up",
        "search_terms": (
            "epilepsy",
            "neurology",
            "seizure",
        ),
        "description": "Follow-up visits for epilepsy and related neurological care.",
        "default_periods": "last_12_months",
        "demo_weight": 0.95,
    },
    {
        "slug": "self_harm_cases",
        "display_name": "Self-Harm Related Cases",
        "package": "mns_core",
        "domain": "Crisis signals",
        "search_terms": (
            "self harm",
            "suicide",
            "attempted suicide",
        ),
        "description": "Facility-recorded cases associated with self-harm or suicide attempts.",
        "default_periods": "last_12_months",
        "demo_weight": 0.65,
    },
)

_URBAN_COUNTY_BONUS = {
    "Nairobi": 1.35,
    "Mombasa": 1.2,
    "Kisumu": 1.14,
    "Kiambu": 1.12,
    "Nakuru": 1.1,
    "Uasin Gishu": 1.08,
}
_REGION_BONUS = {
    "Nairobi": 1.12,
    "Coast": 1.06,
    "Nyanza": 1.08,
    "Western": 1.03,
    "Central": 0.98,
    "Eastern": 1.0,
    "North Eastern": 0.92,
    "Rift Valley": 1.01,
}


def list_mental_health_indicators(package: str | None = None) -> pd.DataFrame:
    """Return the curated mental-health indicator catalog.

    Parameters
    ----------
    package:
        Optional catalog package filter, for example ``"mns_core"``.

    Returns
    -------
    pandas.DataFrame
        Catalog rows with indicator slugs, display labels, domains, search
        terms, and package metadata.
    """
    rows = [_serialise_catalog_row(row) for row in _catalog_rows(package)]
    return pd.DataFrame.from_records(rows)


def get_indicator_package(package: str = "mns_core") -> list[dict[str, Any]]:
    """Return one mental-health indicator package as a list of catalog rows."""
    rows = _catalog_rows(package)
    if not rows:
        raise ValueError(
            f"Unknown mental-health package '{package}'. "
            "Use list_mental_health_indicators() to inspect supported packages."
        )
    return [dict(row) for row in rows]


def resolve_mental_health_indicators(
    connector,
    package: str = "mns_core",
) -> pd.DataFrame:
    """Resolve curated mental-health profiles against live KHIS indicator metadata.

    The returned table is safe to use in dashboards and APIs because it always
    contains one row per curated profile, even when no live KHIS match is
    available.
    """
    rows: list[dict[str, Any]] = []
    for profile in get_indicator_package(package):
        match_row, matched_term = _find_indicator_match(connector, profile)
        rows.append(
            {
                **_serialise_catalog_row(profile),
                "matched_id": None if match_row is None else str(match_row.get("id")),
                "matched_name": (
                    None if match_row is None else str(match_row.get("name", ""))
                ),
                "matched_search_term": matched_term,
                "available": match_row is not None,
                "source": "live" if match_row is not None else "demo_fallback",
            }
        )

    return pd.DataFrame.from_records(rows)


def pull_mental_health_data(
    connector,
    counties: Iterable[str] | str | None = None,
    periods: Iterable[str] | str = "last_12_months",
    package: str = "mns_core",
    fallback_to_demo: bool = True,
) -> pd.DataFrame:
    """Pull live mental-health indicator data or a deterministic fallback frame.

    Parameters
    ----------
    connector:
        Connected DHIS2/KHIS client.
    counties:
        Optional county names. If omitted, all 47 Kenya counties are used for
        the fallback frame and any resolvable live county pulls.
    periods:
        DHIS2 period shortcut or iterable of explicit periods.
    package:
        Curated indicator package to resolve and fetch.
    fallback_to_demo:
        When ``True``, return a deterministic county-level demo frame if live
        mental-health indicators or organisation units cannot be resolved.
    """
    requested_counties = _resolve_requested_counties(counties)
    catalog = resolve_mental_health_indicators(connector, package=package)
    live_catalog = catalog[catalog["available"]].reset_index(drop=True)

    if not getattr(connector, "using_demo_server", False) and not live_catalog.empty:
        resolved_org_units: list[str] = []
        id_to_county: dict[str, str] = {}
        for county in requested_counties:
            try:
                org_unit_id = connector.resolve_org_unit_id_by_name(county["name"])
            except Exception:
                continue
            resolved_org_units.append(org_unit_id)
            id_to_county[org_unit_id] = county["name"]

        if resolved_org_units:
            live_frames: list[pd.DataFrame] = []
            for _, profile in live_catalog.iterrows():
                try:
                    frame = connector.get_analytics(
                        indicator_ids=str(profile["matched_id"]),
                        org_unit_ids=resolved_org_units,
                        periods=periods,
                    )
                except Exception:
                    continue
                if frame.empty:
                    continue
                enriched = frame.copy()
                enriched["org_unit_name"] = (
                    enriched["org_unit_id"]
                    .map(id_to_county)
                    .fillna(enriched["org_unit_name"])
                )
                enriched["indicator_slug"] = profile["slug"]
                enriched["indicator_domain"] = profile["domain"]
                enriched["indicator_package"] = profile["package"]
                enriched["data_source"] = "live"
                live_frames.append(enriched)

            if live_frames:
                return pd.concat(live_frames, ignore_index=True)

    if not fallback_to_demo:
        raise RuntimeError(
            "No live mental-health indicators could be resolved from this KHIS/DHIS2 "
            "connection. Enable fallback_to_demo to keep the workflow usable."
        )

    return _build_demo_mental_health_frame(
        requested_counties,
        periods=periods,
        package=package,
    )


def summarise_county_mental_health(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise the latest mental-health burden snapshot for each county."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "county",
                "latest_period",
                "tracked_indicators",
                "latest_total_value",
                "average_latest_value",
                "trend_direction",
                "burden_band",
                "county_percentile",
                "data_source",
            ]
        )

    working = df.copy()
    working["period"] = pd.to_datetime(working["period"], errors="coerce")
    working = working.dropna(subset=["period"]).copy()
    county_column = "org_unit_name" if "org_unit_name" in working.columns else "county"
    indicator_column = (
        "indicator_slug"
        if "indicator_slug" in working.columns
        else "indicator_name" if "indicator_name" in working.columns else "indicator_id"
    )
    working["value"] = pd.to_numeric(working["value"], errors="coerce")

    latest = (
        working.sort_values(
            [county_column, indicator_column, "period"], kind="mergesort"
        )
        .groupby([county_column, indicator_column], as_index=False)
        .tail(1)
    )

    rows: list[dict[str, Any]] = []
    for county, county_frame in working.groupby(county_column):
        latest_frame = latest[latest[county_column] == county]
        latest_period = latest_frame["period"].max()
        if pd.isna(latest_period):
            continue

        recent_start = latest_period - pd.DateOffset(months=3)
        prior_start = latest_period - pd.DateOffset(months=6)
        recent_mean = county_frame[county_frame["period"] > recent_start][
            "value"
        ].mean()
        prior_mean = county_frame[
            (county_frame["period"] > prior_start)
            & (county_frame["period"] <= recent_start)
        ]["value"].mean()

        rows.append(
            {
                "county": county,
                "latest_period": latest_period.strftime("%Y-%m-%d"),
                "tracked_indicators": int(latest_frame[indicator_column].nunique()),
                "latest_total_value": round(float(latest_frame["value"].sum()), 2),
                "average_latest_value": round(float(latest_frame["value"].mean()), 2),
                "trend_direction": _classify_trend(recent_mean, prior_mean),
                "data_source": _mode_or_default(
                    county_frame.get("data_source", pd.Series(dtype="object")),
                    default="unknown",
                ),
            }
        )

    summary = pd.DataFrame.from_records(rows)
    if summary.empty:
        return summary

    summary["county_percentile"] = (
        summary["latest_total_value"].rank(method="average", pct=True).round(2)
    )
    summary["burden_band"] = summary["county_percentile"].apply(_burden_band)
    return (
        summary[
            [
                "county",
                "latest_period",
                "tracked_indicators",
                "latest_total_value",
                "average_latest_value",
                "trend_direction",
                "burden_band",
                "county_percentile",
                "data_source",
            ]
        ]
        .sort_values(
            ["latest_total_value", "county"],
            ascending=[False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def county_indicator_snapshot(df: pd.DataFrame, county: str) -> pd.DataFrame:
    """Return the latest mental-health indicator values for one county."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "county",
                "indicator_slug",
                "indicator_name",
                "indicator_domain",
                "latest_period",
                "latest_value",
                "data_source",
            ]
        )

    try:
        resolved_county = get_county(county)["name"]
    except ValueError:
        resolved_county = str(county).strip()

    working = df.copy()
    working["period"] = pd.to_datetime(working["period"], errors="coerce")
    working["value"] = pd.to_numeric(working["value"], errors="coerce")
    county_column = "org_unit_name" if "org_unit_name" in working.columns else "county"
    filtered = working[working[county_column].astype(str) == resolved_county].copy()
    if filtered.empty:
        return pd.DataFrame(
            columns=[
                "county",
                "indicator_slug",
                "indicator_name",
                "indicator_domain",
                "latest_period",
                "latest_value",
                "data_source",
            ]
        )

    indicator_column = (
        "indicator_slug"
        if "indicator_slug" in filtered.columns
        else (
            "indicator_name" if "indicator_name" in filtered.columns else "indicator_id"
        )
    )
    latest = (
        filtered.sort_values([indicator_column, "period"], kind="mergesort")
        .groupby(indicator_column, as_index=False)
        .tail(1)
        .copy()
    )
    latest["latest_period"] = latest["period"].dt.strftime("%Y-%m-%d")
    latest["latest_value"] = latest["value"].round(2)
    latest["county"] = resolved_county
    if "indicator_slug" not in latest.columns:
        latest["indicator_slug"] = latest[indicator_column].astype(str)
    if "indicator_domain" not in latest.columns:
        latest["indicator_domain"] = "Mental health services"
    if "data_source" not in latest.columns:
        latest["data_source"] = "unknown"

    columns = [
        "county",
        "indicator_slug",
        "indicator_name",
        "indicator_domain",
        "latest_period",
        "latest_value",
        "data_source",
    ]
    return (
        latest[columns]
        .sort_values(
            ["latest_value", "indicator_name"],
            ascending=[False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def _catalog_rows(package: str | None = None) -> list[dict[str, Any]]:
    """Return catalog rows, optionally filtered by package name."""
    rows = [dict(row) for row in MENTAL_HEALTH_INDICATOR_CATALOG]
    if package is None:
        return rows
    filtered = [row for row in rows if str(row["package"]).lower() == package.lower()]
    return filtered


def _serialise_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a catalog row into a DataFrame-friendly dictionary."""
    payload = dict(row)
    payload["search_terms"] = ", ".join(payload["search_terms"])
    return payload


def _find_indicator_match(
    connector,
    profile: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the best live KHIS indicator match for one curated profile."""
    best_row: dict[str, Any] | None = None
    best_term: str | None = None
    best_score = -1

    for search_term in profile["search_terms"]:
        try:
            candidates = connector.get_indicators(search_term=search_term)
        except Exception:
            candidates = pd.DataFrame()
        if candidates.empty:
            continue

        for row in candidates.to_dict(orient="records"):
            score = _indicator_match_score(row, profile, search_term)
            if score > best_score:
                best_row = row
                best_term = search_term
                best_score = score

    return best_row, best_term


def _indicator_match_score(
    row: dict[str, Any],
    profile: dict[str, Any],
    search_term: str,
) -> int:
    """Score a live indicator candidate against a curated profile."""
    haystack = " ".join(
        [
            str(row.get("name", "")),
            str(row.get("short_name", "")),
            str(row.get("code", "")),
            str(row.get("description", "")),
        ]
    ).lower()
    score = 0
    if search_term.lower() in haystack:
        score += 5
    for token in str(profile["display_name"]).lower().split():
        if token in {"and", "or", "the"}:
            continue
        if token in haystack:
            score += 1
    return score


def _resolve_requested_counties(
    counties: Iterable[str] | str | None,
) -> list[dict[str, Any]]:
    """Resolve county inputs to canonical metadata rows."""
    if counties is None:
        return list_counties().to_dict(orient="records")

    if isinstance(counties, str):
        raw_values = [part.strip() for part in counties.split(",") if part.strip()]
    else:
        raw_values = [str(part).strip() for part in counties if str(part).strip()]

    resolved: list[dict[str, Any]] = []
    for value in raw_values:
        resolved.append(get_county(value))
    return resolved


def _build_demo_mental_health_frame(
    counties: list[dict[str, Any]],
    periods: Iterable[str] | str,
    package: str,
) -> pd.DataFrame:
    """Create a deterministic county mental-health frame for demos and tests."""
    period_index = _period_index(periods)
    records: list[dict[str, Any]] = []
    package_rows = get_indicator_package(package)

    for county in counties:
        county_name = str(county["name"])
        urban_bonus = _URBAN_COUNTY_BONUS.get(county_name, 1.0)
        region_bonus = _REGION_BONUS.get(str(county["region"]), 1.0)

        for indicator_position, profile in enumerate(package_rows):
            base = 5.5 + (int(county["code"]) % 7) * 1.1
            weight = float(profile["demo_weight"])
            for month_position, period in enumerate(period_index):
                seasonal = ((month_position + indicator_position) % 4) * 0.7
                trend = month_position * (0.12 + (weight * 0.04))
                value = round(
                    max(
                        (base * weight * urban_bonus * region_bonus) + seasonal + trend,
                        0.0,
                    ),
                    2,
                )
                records.append(
                    {
                        "indicator_id": f"demo_{profile['slug']}",
                        "indicator_name": profile["display_name"],
                        "indicator_slug": profile["slug"],
                        "indicator_domain": profile["domain"],
                        "indicator_package": profile["package"],
                        "org_unit_id": county["dhis2_id"],
                        "org_unit_name": county_name,
                        "period": period.strftime("%Y-%m-%d"),
                        "value": value,
                        "data_source": "demo_fallback",
                    }
                )

    return pd.DataFrame.from_records(records)


def _period_index(periods: Iterable[str] | str) -> pd.DatetimeIndex:
    """Resolve KHIS-friendly period shortcuts to a stable monthly date range."""
    if isinstance(periods, str):
        shortcut = periods.strip().lower()
        if shortcut == "last_12_months":
            return pd.date_range("2024-01-01", periods=12, freq="MS")
        if shortcut == "last_6_months":
            return pd.date_range("2024-07-01", periods=6, freq="MS")
        if shortcut == "last_3_months":
            return pd.date_range("2024-10-01", periods=3, freq="MS")
        if shortcut == "this_year":
            return pd.date_range("2025-01-01", periods=12, freq="MS")
        explicit_values = [part.strip() for part in periods.split(",") if part.strip()]
    else:
        explicit_values = [str(part).strip() for part in periods if str(part).strip()]

    parsed = pd.to_datetime(explicit_values, format="%Y%m", errors="coerce")
    parsed = pd.DatetimeIndex(parsed[~pd.isna(parsed)])
    return (
        parsed
        if not parsed.empty
        else pd.date_range("2024-01-01", periods=12, freq="MS")
    )


def _classify_trend(recent_mean: float, prior_mean: float) -> str:
    """Classify a county's recent direction of travel using short moving windows."""
    if pd.isna(recent_mean) and pd.isna(prior_mean):
        return "Insufficient data"
    if pd.isna(prior_mean) or prior_mean == 0:
        return "Emerging"

    change_ratio = (recent_mean - prior_mean) / abs(prior_mean)
    if change_ratio >= 0.1:
        return "Rising"
    if change_ratio <= -0.1:
        return "Falling"
    return "Stable"


def _burden_band(percentile: float) -> str:
    """Map county percentiles into readable burden bands."""
    if percentile >= 0.75:
        return "High"
    if percentile >= 0.5:
        return "Elevated"
    if percentile >= 0.25:
        return "Moderate"
    return "Low"


def _mode_or_default(series: pd.Series, default: str) -> str:
    """Return the mode of a series or a default value when it is empty."""
    if series.empty:
        return default
    mode = series.dropna().astype(str).mode()
    if mode.empty:
        return default
    return str(mode.iloc[0])


__all__ = [
    "MENTAL_HEALTH_INDICATOR_CATALOG",
    "county_indicator_snapshot",
    "get_indicator_package",
    "list_mental_health_indicators",
    "pull_mental_health_data",
    "resolve_mental_health_indicators",
    "summarise_county_mental_health",
]
