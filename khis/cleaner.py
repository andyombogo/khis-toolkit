"""Kenya-specific DHIS2/KHIS data cleaning utilities.

The KHIS analytics endpoint is useful, but raw DHIS2 extracts still need a
Kenya-aware cleaning pass before they are ready for analysis. County reports
often mix monthly, quarterly, weekly, and annual period codes; numeric values
may arrive as strings; and missing or not-applicable values are sometimes
encoded as negative sentinel numbers. This module standardises those quirks so
county trend analysis, scorecards, and forecasting can work from the same tidy
foundation.
"""

from __future__ import annotations

from datetime import date
from difflib import get_close_matches
import re
import warnings
from typing import Callable

import pandas as pd

from .counties import KENYA_COUNTIES

COUNTY_COLUMNS = ("org_unit_name", "county")
INDICATOR_COLUMNS = ("indicator_name", "indicator_id")
MAX_IMPUTED_GAP = 3


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a raw KHIS/DHIS2 indicator extract into an analysis-ready table.

    Parameters
    ----------
    df:
        Raw analytics DataFrame returned by the connector.

    Returns
    -------
    pandas.DataFrame
        Cleaned data with duplicate indicator/county/period rows removed,
        ``period`` normalised to ``datetime64[ns]``, numeric ``value`` entries,
        DHIS2 negative sentinel values converted to ``NaN``, and records sorted
        for downstream time-series work.
    """
    cleaned = df.copy()
    if cleaned.empty:
        return cleaned

    duplicate_subset = [
        column
        for column in (
            "indicator_id",
            "indicator_name",
            "org_unit_id",
            "org_unit_name",
            "period",
        )
        if column in cleaned.columns
    ]
    if duplicate_subset:
        # KHIS exports can repeat the same indicator/county/period row after
        # metadata refreshes or manual re-exports, so we collapse true duplicates.
        cleaned = cleaned.drop_duplicates(subset=duplicate_subset, keep="first")

    if "period" in cleaned.columns:
        # DHIS2 period codes are compact strings; converting them once here keeps
        # every later county trend, scorecard, and forecast on real dates.
        cleaned["period"] = cleaned["period"].map(_parse_period_value)

    if "value" in cleaned.columns:
        raw_values = cleaned["value"].copy()
        cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")
        coerced_mask = raw_values.notna() & cleaned["value"].isna()
        if bool(coerced_mask.any()):
            warnings.warn(
                "Some KHIS values could not be parsed as numbers and were set to NaN.",
                stacklevel=2,
            )

        # DHIS2 implementations sometimes encode "not applicable" or withheld
        # data as negative values, which should not be treated as real counts.
        negative_mask = cleaned["value"] < 0
        if bool(negative_mask.any()):
            cleaned.loc[negative_mask, "value"] = pd.NA

    sort_columns = [
        column
        for column in ("org_unit_name", "indicator_name", "period")
        if column in cleaned.columns
    ]
    if sort_columns:
        cleaned = cleaned.sort_values(sort_columns, kind="mergesort")

    return cleaned.reset_index(drop=True)


def flag_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Annotate county-indicator series with missing-data percentages.

    Parameters
    ----------
    df:
        Cleaned KHIS analytics table containing a ``value`` column.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with ``missing_pct`` and ``high_missing`` columns added.
    """
    flagged = df.copy()
    flagged["missing_pct"] = pd.Series(dtype="float64")
    flagged["high_missing"] = pd.Series(dtype="bool")
    if flagged.empty:
        return flagged

    county_column = _first_present_column(flagged, COUNTY_COLUMNS)
    indicator_column = _first_present_column(flagged, INDICATOR_COLUMNS)
    if "value" not in flagged.columns:
        raise ValueError("flag_missing() requires a 'value' column.")

    missing_summary = (
        flagged.groupby([county_column, indicator_column], dropna=False)["value"]
        .apply(lambda series: float(series.isna().mean() * 100.0))
        .reset_index(name="missing_pct")
    )
    missing_summary["high_missing"] = missing_summary["missing_pct"] > 20.0

    return flagged.merge(
        missing_summary,
        on=[county_column, indicator_column],
        how="left",
    )


def fill_missing(df: pd.DataFrame, method: str = "interpolate") -> pd.DataFrame:
    """Fill short KHIS time-series gaps while marking which values were imputed.

    Parameters
    ----------
    df:
        Cleaned or flagged KHIS analytics table.
    method:
        ``"interpolate"`` for linear interpolation, ``"forward_fill"`` to carry
        forward the last known value, or ``"none"`` to leave gaps untouched.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with ``value_imputed`` added and eligible short gaps
        filled according to the selected method.
    """
    if method not in {"interpolate", "forward_fill", "none"}:
        raise ValueError("method must be 'interpolate', 'forward_fill', or 'none'.")

    filled = df.copy()
    filled["value_imputed"] = False
    if filled.empty or "value" not in filled.columns:
        return filled

    county_column = _first_present_column(filled, COUNTY_COLUMNS)
    indicator_column = _first_present_column(filled, INDICATOR_COLUMNS)
    sort_columns = [
        column
        for column in (county_column, indicator_column, "period")
        if column in filled.columns
    ]
    if sort_columns:
        filled = filled.sort_values(sort_columns, kind="mergesort").reset_index(
            drop=True
        )

    if method == "none":
        return filled

    for _, group_index in filled.groupby(
        [county_column, indicator_column], dropna=False
    ).groups.items():
        group_series = filled.loc[group_index, "value"]
        filled_series = _fill_series(group_series, method)
        imputed_mask = group_series.isna() & filled_series.notna()
        filled.loc[group_index, "value"] = filled_series
        filled.loc[group_index, "value_imputed"] = imputed_mask.to_numpy()

    return filled


def standardise_county_names(df: pd.DataFrame, county_col: str) -> pd.DataFrame:
    """Correct county name misspellings with fuzzy matching against official counties.

    Parameters
    ----------
    df:
        Input table containing a county-name column.
    county_col:
        Name of the column to standardise.

    Returns
    -------
    pandas.DataFrame
        Copy of ``df`` with corrected county names and a ``name_corrected``
        boolean flag.
    """
    if county_col not in df.columns:
        raise ValueError(f"Column '{county_col}' was not found in the DataFrame.")

    official_names = list(KENYA_COUNTIES.keys())
    normalised_lookup = {_normalise_name(name): name for name in official_names}

    corrected = df.copy()
    corrected["name_corrected"] = False

    updated_values: list[object] = []
    corrected_flags: list[bool] = []
    for value in corrected[county_col]:
        if pd.isna(value):
            updated_values.append(value)
            corrected_flags.append(False)
            continue

        raw_value = str(value).strip()
        normalised_value = _normalise_name(raw_value)

        if normalised_value in normalised_lookup:
            canonical = normalised_lookup[normalised_value]
        else:
            candidate = get_close_matches(
                normalised_value,
                list(normalised_lookup.keys()),
                n=1,
                cutoff=0.75,
            )
            canonical = normalised_lookup[candidate[0]] if candidate else raw_value

        updated_values.append(canonical)
        corrected_flags.append(canonical != raw_value)

    corrected[county_col] = updated_values
    corrected["name_corrected"] = corrected_flags
    return corrected


def full_pipeline(df: pd.DataFrame, fill_method: str = "none") -> pd.DataFrame:
    """Run the full KHIS cleaning sequence with safe defaults."""
    cleaned = clean(df)
    flagged = flag_missing(cleaned)
    return fill_missing(flagged, method=fill_method)


def clean_indicator_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible alias for the main KHIS cleaning entrypoint."""
    return clean(df)


def _first_present_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    """Return the first available column from a preferred list."""
    for column in candidates:
        if column in df.columns:
            return column
    raise ValueError(
        f"Expected one of these columns to be present: {', '.join(candidates)}."
    )


def _fill_series(series: pd.Series, method: str) -> pd.Series:
    """Fill short gaps in a grouped indicator series."""
    numeric_series = pd.to_numeric(series, errors="coerce")
    if method == "interpolate":
        # Short linear interpolation works well for routine DHIS2 counts, but
        # we cap it to avoid fabricating long gaps in county reporting.
        return numeric_series.interpolate(
            method="linear",
            limit=MAX_IMPUTED_GAP,
            limit_direction="forward",
            limit_area="inside",
        )
    return numeric_series.ffill(limit=MAX_IMPUTED_GAP)


def _parse_period_value(value: object) -> pd.Timestamp | pd.NaT:
    """Convert a DHIS2 period code into the corresponding period-start date."""
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value.normalize()

    raw_value = str(value).strip()
    if not raw_value:
        return pd.NaT

    try:
        if re.fullmatch(r"\d{6}", raw_value):
            return pd.Timestamp(
                year=int(raw_value[:4]), month=int(raw_value[4:6]), day=1
            )
        if re.fullmatch(r"\d{4}", raw_value):
            return pd.Timestamp(year=int(raw_value), month=1, day=1)
        if re.fullmatch(r"\d{4}Q[1-4]", raw_value):
            quarter = int(raw_value[-1])
            return pd.Timestamp(
                year=int(raw_value[:4]), month=((quarter - 1) * 3) + 1, day=1
            )
        if re.fullmatch(r"\d{4}W\d{1,2}", raw_value):
            year = int(raw_value[:4])
            week = int(raw_value.split("W", maxsplit=1)[1])
            return pd.Timestamp(date.fromisocalendar(year, week, 1))

        parsed = pd.to_datetime(raw_value, errors="raise")
        return pd.Timestamp(parsed).normalize()
    except (TypeError, ValueError) as exc:
        warnings.warn(
            f"Could not parse KHIS period value '{raw_value}'. It has been set to NaT.",
            stacklevel=2,
        )
        return pd.NaT


def _normalise_name(value: str) -> str:
    """Normalise county labels before fuzzy matching."""
    normalized = str(value).strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("'", "")
    normalized = normalized.replace(" county", "")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
