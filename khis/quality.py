"""Automated data quality assessment for KHIS/DHIS2 county health datasets.

In the KHIS/DHIS2 context, "data quality" is not just about whether a table
loads successfully. County teams need to know whether facilities reported
consistently, whether unusual values are plausible, whether reports arrived on
time, and whether repeated zeros probably mean "nothing happened" or "nothing
was entered". These checks matter because county decisions on commodity
distribution, staffing, outreach, and supervision are only as reliable as the
routine data underneath them.

This module provides a scorecard-oriented view of those issues for Kenya county
health teams:

- completeness shows whether expected reporting periods were actually reported
- outlier detection highlights extreme values that may need validation
- timeliness reveals counties that submit too late for operational action
- zero-pattern analysis flags places where zeros may be masking missing data
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover - plotting is optional at import time
    go = None


def compute_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return a lightweight summary of the supplied dataset."""
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "missing_values": int(df.isna().sum().sum()),
    }


def completeness_score(df: pd.DataFrame, expected_periods: int = 12) -> pd.DataFrame:
    """Score reporting completeness for each county-indicator series."""
    county_column = _county_column(df)
    indicator_column = _indicator_column(df)
    if "value" not in df.columns:
        raise ValueError("completeness_score() requires a 'value' column.")

    grouped = (
        df.groupby([county_column, indicator_column], dropna=False)["value"]
        .agg(reported_periods=lambda series: int(series.notna().sum()))
        .reset_index()
        .rename(columns={county_column: "county", indicator_column: "indicator"})
    )
    grouped["expected_periods"] = int(expected_periods)
    grouped["completeness_pct"] = (
        grouped["reported_periods"] / grouped["expected_periods"] * 100.0
    ).round(1)
    grouped["completeness_class"] = grouped["completeness_pct"].map(
        _classify_completeness
    )
    return grouped[
        [
            "county",
            "indicator",
            "expected_periods",
            "reported_periods",
            "completeness_pct",
            "completeness_class",
        ]
    ]


def outlier_report(
    df: pd.DataFrame,
    method: str = "iqr",
    threshold: float = 3.0,
) -> pd.DataFrame:
    """Flag suspiciously extreme values within each county-indicator series."""
    if method not in {"iqr", "zscore"}:
        raise ValueError("method must be 'iqr' or 'zscore'.")
    if "value" not in df.columns:
        raise ValueError("outlier_report() requires a 'value' column.")

    county_column = _county_column(df)
    indicator_column = _indicator_column(df)

    report = df.copy()
    report["outlier_flag"] = False
    report["outlier_score"] = 0.0
    report["outlier_context"] = "Within expected range."

    for _, indices in report.groupby(
        [county_column, indicator_column], dropna=False
    ).groups.items():
        values = pd.to_numeric(report.loc[indices, "value"], errors="coerce")
        flags, scores = _compute_outlier_flags(
            values, method=method, threshold=threshold
        )
        average_value = values.mean(skipna=True)

        report.loc[indices, "outlier_flag"] = flags.to_numpy()
        report.loc[indices, "outlier_score"] = scores.round(3).to_numpy()
        report.loc[indices, "outlier_context"] = [
            _outlier_context(value, average_value, flag)
            for value, flag in zip(values, flags, strict=False)
        ]

    return report


def timeliness_report(df: pd.DataFrame) -> pd.DataFrame:
    """Assess how long counties take to submit reports after a period ends."""
    county_column = _county_column(df)
    counties = (
        df[[county_column]]
        .drop_duplicates()
        .rename(columns={county_column: "county"})
        .reset_index(drop=True)
    )
    if "submission_date" not in df.columns or "period" not in df.columns:
        counties["avg_delay_days"] = pd.NA
        counties["late_reporter"] = False
        return counties

    working = df.copy()
    working["submission_date"] = pd.to_datetime(
        working["submission_date"], errors="coerce"
    )
    working["period"] = pd.to_datetime(working["period"], errors="coerce")

    period_end_chunks = []
    for _, group in working.groupby(
        [county_column, _indicator_column(working)], dropna=False, sort=False
    ):
        period_end_chunks.append(_group_period_end_dates(group))
    working["period_end"] = pd.concat(period_end_chunks).sort_index()
    working["delay_days"] = (working["submission_date"] - working["period_end"]).dt.days

    summary = (
        working.groupby(county_column, dropna=False)["delay_days"]
        .mean()
        .round(1)
        .reset_index(name="avg_delay_days")
        .rename(columns={county_column: "county"})
    )
    summary["late_reporter"] = summary["avg_delay_days"].fillna(0) > 30
    return summary


def zero_report_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Identify county-indicator series with suspiciously frequent zero values."""
    if "value" not in df.columns:
        raise ValueError("zero_report_analysis() requires a 'value' column.")

    county_column = _county_column(df)
    indicator_column = _indicator_column(df)

    grouped = (
        df.groupby([county_column, indicator_column], dropna=False)["value"]
        .agg(
            observed_periods=lambda series: int(series.notna().sum()),
            zero_periods=lambda series: int(
                (pd.to_numeric(series, errors="coerce") == 0).sum()
            ),
            missing_periods=lambda series: int(series.isna().sum()),
            max_value=lambda series: (
                float(pd.to_numeric(series, errors="coerce").max(skipna=True))
                if series.notna().any()
                else np.nan
            ),
        )
        .reset_index()
        .rename(columns={county_column: "county", indicator_column: "indicator"})
    )
    grouped["zero_pct"] = np.where(
        grouped["observed_periods"] > 0,
        (grouped["zero_periods"] / grouped["observed_periods"] * 100.0).round(1),
        np.nan,
    )
    grouped["suspicious_zero_pattern"] = (grouped["zero_pct"].fillna(0) > 50.0) & (
        (grouped["missing_periods"] > 0) | (grouped["max_value"].fillna(0) > 0)
    )
    grouped["zero_pattern"] = np.where(
        grouped["suspicious_zero_pattern"],
        "zero_as_missing",
        np.where(grouped["zero_pct"].fillna(0) > 50.0, "true_zero", "normal"),
    )
    return grouped[
        [
            "county",
            "indicator",
            "observed_periods",
            "zero_periods",
            "zero_pct",
            "suspicious_zero_pattern",
            "zero_pattern",
        ]
    ]


def county_scorecard(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Generate the county-level quality scorecard and a narrative summary."""
    county_column = _county_column(df)
    completeness = completeness_score(df)
    outliers = outlier_report(df)
    timeliness = timeliness_report(df)
    zero_patterns = zero_report_analysis(df)

    completeness_by_county = (
        completeness.groupby("county", dropna=False)["completeness_pct"]
        .mean()
        .round(1)
        .reset_index(name="completeness_score")
    )
    outlier_count = (
        outliers.groupby(county_column, dropna=False)["outlier_flag"]
        .sum()
        .reset_index(name="outlier_count")
        .rename(columns={county_column: "county"})
    )
    suspicious_zero_counties = (
        zero_patterns.groupby("county", dropna=False)["suspicious_zero_pattern"]
        .any()
        .reset_index(name="suspicious_zeros")
    )

    scorecard = completeness_by_county.merge(outlier_count, on="county", how="left")
    scorecard = scorecard.merge(timeliness, on="county", how="left")
    scorecard = scorecard.merge(suspicious_zero_counties, on="county", how="left")

    scorecard["outlier_count"] = scorecard["outlier_count"].fillna(0).astype(int)
    scorecard["late_reporter"] = scorecard["late_reporter"].fillna(False).astype(bool)
    scorecard["suspicious_zeros"] = (
        scorecard["suspicious_zeros"].fillna(False).astype(bool)
    )

    quality_points = (
        scorecard["completeness_score"].fillna(0)
        - scorecard["outlier_count"].clip(upper=10) * 2.0
        - scorecard["late_reporter"].astype(int) * 10.0
        - scorecard["suspicious_zeros"].astype(int) * 10.0
    ).clip(lower=0, upper=100)
    scorecard["overall_quality_grade"] = quality_points.map(_grade_quality_score)
    scorecard = (
        scorecard[
            [
                "county",
                "completeness_score",
                "outlier_count",
                "late_reporter",
                "suspicious_zeros",
                "overall_quality_grade",
            ]
        ]
        .sort_values(["overall_quality_grade", "county"], ascending=[True, True])
        .reset_index(drop=True)
    )

    text_summary = _build_scorecard_summary(scorecard)
    return scorecard, text_summary


def plot_quality_heatmap(scorecard_df: pd.DataFrame):
    """Create a Plotly heatmap for completeness or county scorecard output."""
    if go is None:  # pragma: no cover - depends on optional plotting dependency
        raise RuntimeError("Plotly is required to create the quality heatmap.")

    if {"county", "indicator", "completeness_pct"}.issubset(scorecard_df.columns):
        pivot = scorecard_df.pivot_table(
            index="county",
            columns="indicator",
            values="completeness_pct",
            aggfunc="mean",
        )
        colorbar_title = "Completeness %"
        title = "County Reporting Completeness by Indicator"
    elif {"county", "completeness_score"}.issubset(scorecard_df.columns):
        pivot = scorecard_df.set_index("county")[["completeness_score"]]
        pivot.columns = ["overall_quality"]
        colorbar_title = "Quality Score"
        title = "County Quality Scorecard"
    else:
        raise ValueError(
            "plot_quality_heatmap() expects either completeness_score() output "
            "or the county-level scorecard DataFrame."
        )

    figure = go.Figure(
        data=[
            go.Heatmap(
                z=pivot.to_numpy(),
                x=[str(column) for column in pivot.columns],
                y=[str(index) for index in pivot.index],
                colorscale=[
                    [0.0, "#c0392b"],
                    [0.5, "#f4b942"],
                    [1.0, "#2e8b57"],
                ],
                zmin=0,
                zmax=100,
                colorbar={"title": colorbar_title},
                hovertemplate="County: %{y}<br>Metric: %{x}<br>Value: %{z:.1f}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        title=title,
        xaxis_title="Indicator",
        yaxis_title="County",
        template="plotly_white",
        margin={"l": 80, "r": 30, "t": 80, "b": 60},
    )
    return figure


def _county_column(df: pd.DataFrame) -> str:
    """Resolve the county column name used in the supplied DataFrame."""
    for candidate in ("county", "org_unit_name"):
        if candidate in df.columns:
            return candidate
    raise ValueError("Expected a 'county' or 'org_unit_name' column.")


def _indicator_column(df: pd.DataFrame) -> str:
    """Resolve the indicator column name used in the supplied DataFrame."""
    for candidate in ("indicator", "indicator_name", "indicator_id"):
        if candidate in df.columns:
            return candidate
    raise ValueError(
        "Expected an 'indicator', 'indicator_name', or 'indicator_id' column."
    )


def _classify_completeness(value: float) -> str:
    """Convert a completeness percentage to a human-readable class."""
    if value >= 90:
        return "good"
    if value >= 75:
        return "moderate"
    return "poor"


def _compute_outlier_flags(
    series: pd.Series,
    method: str,
    threshold: float,
) -> tuple[pd.Series, pd.Series]:
    """Return the outlier flag mask and numeric outlier score."""
    clean_values = series.astype("float64")
    if clean_values.dropna().empty:
        return pd.Series(False, index=series.index), pd.Series(0.0, index=series.index)

    if method == "iqr":
        q1 = clean_values.quantile(0.25)
        q3 = clean_values.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            return pd.Series(False, index=series.index), pd.Series(
                0.0, index=series.index
            )
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        flags = (clean_values < lower_bound) | (clean_values > upper_bound)
        distance = np.maximum(lower_bound - clean_values, clean_values - upper_bound)
        scores = pd.Series(
            np.where(flags, np.abs(distance) / iqr, 0.0), index=series.index
        )
        return flags.fillna(False), scores.fillna(0.0)

    mean_value = clean_values.mean()
    std_value = clean_values.std(ddof=0)
    if pd.isna(std_value) or std_value == 0:
        return pd.Series(False, index=series.index), pd.Series(0.0, index=series.index)
    z_scores = (clean_values - mean_value) / std_value
    flags = z_scores.abs() > threshold
    return flags.fillna(False), z_scores.abs().fillna(0.0)


def _outlier_context(value: float, average_value: float, is_flagged: bool) -> str:
    """Create a human-readable outlier explanation string."""
    if not is_flagged or pd.isna(value):
        return "Within expected range."
    if pd.isna(average_value) or average_value == 0:
        return "Flagged as an outlier, but county average was unavailable."
    multiple = abs(float(value) / float(average_value))
    return f"This value is {multiple:.2f} times the county average for this indicator."


def _group_period_end_dates(group: pd.DataFrame) -> pd.Series:
    """Estimate each row's period end date from the observed reporting cadence."""
    sorted_group = group.sort_values("period", kind="mergesort").copy()
    valid_periods = sorted_group["period"].dropna().sort_values()

    if len(valid_periods) >= 2:
        median_days = float(valid_periods.diff().dropna().dt.days.median())
    else:
        median_days = 30.0

    if median_days <= 10:
        offset = pd.Timedelta(days=6)
    elif median_days <= 35:
        offset = pd.Timedelta(days=30)
    elif median_days <= 100:
        offset = pd.Timedelta(days=89)
    else:
        offset = pd.Timedelta(days=364)

    period_end = sorted_group["period"] + offset
    period_end.index = sorted_group.index
    return period_end.reindex(group.index)


def _grade_quality_score(score: float) -> str:
    """Map a numeric quality score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _build_scorecard_summary(scorecard: pd.DataFrame) -> str:
    """Create a short narrative summary for county quality reporting."""
    total_counties = int(len(scorecard))
    strong_counties = int(scorecard["overall_quality_grade"].isin(["A", "B"]).sum())
    weak_counties = int(scorecard["overall_quality_grade"].isin(["D", "F"]).sum())
    late_counties = int(scorecard["late_reporter"].sum())
    suspicious_zero_counties = int(scorecard["suspicious_zeros"].sum())

    return (
        f"Reviewed {total_counties} counties. "
        f"{strong_counties} counties scored A or B, while {weak_counties} counties scored D or F. "
        f"{late_counties} counties were late reporters and {suspicious_zero_counties} showed suspicious zero patterns."
    )
