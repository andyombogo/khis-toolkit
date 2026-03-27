"""County-level forecasting tools for KHIS routine health indicators.

Short-horizon forecasting matters in county health management because teams are
often making operational decisions before the next reporting cycle arrives.
Four-week or four-period forecasts can support malaria commodity planning,
facility staffing, outreach scheduling, and early warning for unusual mental
health or disease-burden shifts. This module turns cleaned KHIS/DHIS2 time
series into practical forward-looking tables and charts using Prophet,
XGBoost, and a combined ensemble.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from tqdm.auto import tqdm
from xgboost import XGBRegressor

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover - optional dependency in the shared runtime
    Prophet = None

FREQ_ALIASES = {
    "M": "MS",
    "W": "W-MON",
    "Q": "QS",
}


@dataclass(frozen=True)
class SeriesContext:
    """Prepared metadata for a single county-indicator time series."""

    county: str
    indicator: str
    df: pd.DataFrame


def prophet_forecast(
    df: pd.DataFrame,
    indicator: str,
    county: str,
    periods_ahead: int = 4,
    freq: str = "M",
) -> pd.DataFrame:
    """Forecast one county-indicator series with Prophet when available."""
    series = _prepare_series(df, indicator=indicator, county=county)
    _warn_if_short_series(series.df)

    if Prophet is None:
        warnings.warn(
            "prophet is not installed; using a linear trend fallback for prophet_forecast().",
            stacklevel=2,
        )
        return _trend_fallback_forecast(series, periods_ahead=periods_ahead, freq=freq)

    model_df = series.df.rename(columns={"period": "ds", "value": "y"})[["ds", "y"]]
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=(freq.upper() == "W"),
        daily_seasonality=False,
        interval_width=0.8,
        holidays=_kenya_holidays(model_df["ds"], periods_ahead=periods_ahead, freq=freq),
    )
    model.fit(model_df)

    future = model.make_future_dataframe(
        periods=periods_ahead,
        freq=_prophet_freq(freq),
        include_history=True,
    )
    forecast = model.predict(future)[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    result = forecast.rename(
        columns={
            "ds": "period",
            "yhat": "forecast",
            "yhat_lower": "lower_bound",
            "yhat_upper": "upper_bound",
        }
    )
    history_map = series.df.set_index("period")["value"]
    result["actual"] = result["period"].map(history_map)
    result["is_forecast"] = ~result["period"].isin(series.df["period"])
    return result[["period", "actual", "forecast", "lower_bound", "upper_bound", "is_forecast"]]


def xgboost_forecast(
    df: pd.DataFrame,
    indicator: str,
    county: str,
    periods_ahead: int = 4,
) -> pd.DataFrame:
    """Forecast one county-indicator series with lagged XGBoost features."""
    series = _prepare_series(df, indicator=indicator, county=county)
    _warn_if_short_series(series.df)
    freq = _infer_freq(series.df["period"])

    design = _build_xgboost_training_frame(series.df)
    if len(design) < 6:
        warnings.warn(
            "Not enough data points to train XGBoost robustly; using the trend fallback instead.",
            stacklevel=2,
        )
        return _trend_fallback_forecast(series, periods_ahead=periods_ahead, freq=freq)

    feature_columns = [
        "lag_1",
        "lag_2",
        "lag_3",
        "lag_4",
        "rolling_mean_3",
        "rolling_mean_6",
        "time_index",
        "month",
        "quarter",
        "year",
        "week_of_year",
    ]
    model = XGBRegressor(
        n_estimators=160,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(design[feature_columns], design["target"])

    fitted = pd.Series(model.predict(design[feature_columns]), index=design.index)
    residuals = design["target"] - fitted
    interval_width = max(float(residuals.std(ddof=0)) * 1.28, 1.0)

    history_result = series.df.copy()
    history_result["forecast"] = history_result["value"]
    history_result.loc[design.index, "forecast"] = fitted
    history_result["lower_bound"] = history_result["forecast"] - interval_width
    history_result["upper_bound"] = history_result["forecast"] + interval_width
    history_result["actual"] = history_result["value"]
    history_result["is_forecast"] = False
    history_result = history_result.drop(columns=["value"])

    future_rows = _recursive_xgboost_forecast(
        model=model,
        history=series.df[["period", "value"]].copy(),
        periods_ahead=periods_ahead,
        freq=freq,
        interval_width=interval_width,
    )

    combined = pd.concat([history_result, future_rows], ignore_index=True)
    return combined[["period", "actual", "forecast", "lower_bound", "upper_bound", "is_forecast"]]


def ensemble_forecast(
    df: pd.DataFrame,
    indicator: str,
    county: str,
    periods_ahead: int = 4,
) -> pd.DataFrame:
    """Combine Prophet and XGBoost forecasts with a 60/40 weighted average."""
    prophet_result = prophet_forecast(
        df,
        indicator=indicator,
        county=county,
        periods_ahead=periods_ahead,
        freq=_infer_freq(_prepare_series(df, indicator=indicator, county=county).df["period"]),
    )
    xgb_result = xgboost_forecast(
        df,
        indicator=indicator,
        county=county,
        periods_ahead=periods_ahead,
    )

    combined = prophet_result.merge(
        xgb_result,
        on="period",
        how="outer",
        suffixes=("_prophet", "_xgb"),
    ).sort_values("period", kind="mergesort")

    combined["actual"] = combined["actual_prophet"].combine_first(combined["actual_xgb"])
    combined["forecast"] = combined["forecast_prophet"].fillna(0) * 0.6 + combined["forecast_xgb"].fillna(0) * 0.4
    combined["lower_bound"] = (
        combined["lower_bound_prophet"].fillna(combined["forecast"]) * 0.6
        + combined["lower_bound_xgb"].fillna(combined["forecast"]) * 0.4
    )
    combined["upper_bound"] = (
        combined["upper_bound_prophet"].fillna(combined["forecast"]) * 0.6
        + combined["upper_bound_xgb"].fillna(combined["forecast"]) * 0.4
    )
    combined["is_forecast"] = combined["is_forecast_prophet"].fillna(False) | combined["is_forecast_xgb"].fillna(False)

    return combined[
        ["period", "actual", "forecast", "lower_bound", "upper_bound", "is_forecast"]
    ].reset_index(drop=True)


def forecast_all_counties(
    df: pd.DataFrame,
    indicator: str,
    periods_ahead: int = 4,
    method: str = "ensemble",
) -> pd.DataFrame:
    """Run the selected forecast method across every county in the dataset."""
    county_column = _county_column(df)
    counties = [
        county
        for county in sorted(df[county_column].dropna().astype(str).unique())
        if county.strip()
    ]
    forecast_fn = _forecast_method(method)

    results: list[pd.DataFrame] = []
    for county in tqdm(counties, desc="Forecasting counties", leave=False):
        county_df = df[df[county_column].astype(str) == county]
        if len(county_df.dropna(subset=["value"])) < 6:
            warnings.warn(
                f"Skipping {county}: not enough observed data points for a stable forecast.",
                stacklevel=2,
            )
            continue

        county_result = forecast_fn(
            df,
            indicator=indicator,
            county=county,
            periods_ahead=periods_ahead,
        )
        county_result.insert(0, "county", county)
        results.append(county_result)

    if not results:
        return pd.DataFrame(
            columns=["county", "period", "actual", "forecast", "lower_bound", "upper_bound", "is_forecast"]
        )

    return pd.concat(results, ignore_index=True)


def plot_forecast(forecast_df: pd.DataFrame, title: str | None = None):
    """Plot actuals, forecast, confidence interval, and forecast boundary."""
    if forecast_df.empty:
        raise ValueError("plot_forecast() requires a non-empty forecast DataFrame.")

    ordered = forecast_df.sort_values("period", kind="mergesort").copy()
    future_periods = ordered.loc[ordered["is_forecast"], "period"]
    boundary = future_periods.min() if not future_periods.empty else None

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=ordered["period"],
            y=ordered["actual"],
            mode="lines+markers",
            name="Actual",
            line={"color": "#1f4e79", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=ordered["period"],
            y=ordered["forecast"],
            mode="lines",
            name="Forecast",
            line={"color": "#c0392b", "dash": "dash", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=pd.concat([ordered["period"], ordered["period"].iloc[::-1]]),
            y=pd.concat([ordered["upper_bound"], ordered["lower_bound"].iloc[::-1]]),
            fill="toself",
            fillcolor="rgba(192, 57, 43, 0.15)",
            line={"color": "rgba(0,0,0,0)"},
            hoverinfo="skip",
            name="Confidence interval",
        )
    )

    if boundary is not None:
        figure.add_shape(
            type="line",
            x0=boundary,
            x1=boundary,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line={"dash": "dot", "color": "#555555"},
        )
        figure.add_annotation(
            x=boundary,
            y=1.02,
            xref="x",
            yref="paper",
            text="Forecast start",
            showarrow=False,
            font={"color": "#555555"},
        )

    figure.update_layout(
        title=title or "County Indicator Forecast",
        template="plotly_white",
        xaxis_title="Period",
        yaxis_title="Value",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
        margin={"l": 60, "r": 30, "t": 70, "b": 50},
    )
    return figure


def anomaly_detection(df: pd.DataFrame, indicator: str, county: str) -> pd.DataFrame:
    """Flag actual observations that fall outside the forecast confidence interval."""
    forecast_df = prophet_forecast(
        df,
        indicator=indicator,
        county=county,
        periods_ahead=4,
        freq=_infer_freq(_prepare_series(df, indicator=indicator, county=county).df["period"]),
    )
    anomalies = forecast_df[~forecast_df["is_forecast"]].copy()
    anomalies["anomaly_flag"] = (
        (anomalies["actual"] < anomalies["lower_bound"])
        | (anomalies["actual"] > anomalies["upper_bound"])
    )
    return anomalies


def forecast_indicator_series(
    df: pd.DataFrame,
    indicator: str | None = None,
    county: str | None = None,
    periods_ahead: int = 4,
    weeks_ahead: int | None = None,
    method: str = "ensemble",
) -> pd.DataFrame:
    """Forecast one series using the package's recommended method wrapper."""
    if weeks_ahead is not None:
        periods_ahead = weeks_ahead

    resolved_indicator, resolved_county = _resolve_series_identity(df, indicator=indicator, county=county)
    forecast_fn = _forecast_method(method)
    return forecast_fn(
        df,
        indicator=resolved_indicator,
        county=resolved_county,
        periods_ahead=periods_ahead,
    )


def _forecast_method(method: str):
    """Map a method label to the corresponding forecast function."""
    methods = {
        "prophet": prophet_forecast,
        "xgboost": xgboost_forecast,
        "ensemble": ensemble_forecast,
    }
    try:
        return methods[method.lower()]
    except KeyError as exc:
        raise ValueError("method must be one of: prophet, xgboost, ensemble.") from exc


def _resolve_series_identity(
    df: pd.DataFrame,
    indicator: str | None,
    county: str | None,
) -> tuple[str, str]:
    """Infer indicator and county when the input frame already contains one series."""
    county_column = _county_column(df)
    indicator_column = _indicator_column(df)

    if county is None:
        counties = [value for value in df[county_column].dropna().astype(str).unique() if value.strip()]
        if len(counties) != 1:
            raise ValueError("Pass county explicitly when the DataFrame contains multiple counties.")
        county = counties[0]

    if indicator is None:
        indicators = [value for value in df[indicator_column].dropna().astype(str).unique() if value.strip()]
        if len(indicators) != 1:
            raise ValueError("Pass indicator explicitly when the DataFrame contains multiple indicators.")
        indicator = indicators[0]

    return indicator, county


def _prepare_series(df: pd.DataFrame, indicator: str, county: str) -> SeriesContext:
    """Filter and normalise one county-indicator series from a cleaned KHIS table."""
    if "period" not in df.columns or "value" not in df.columns:
        raise ValueError("Forecasting requires 'period' and 'value' columns.")

    county_column = _county_column(df)
    indicator_column = _indicator_column(df)
    working = df.copy()
    working["period"] = pd.to_datetime(working["period"], errors="coerce")
    working["value"] = pd.to_numeric(working["value"], errors="coerce")

    filtered = working[
        (working[county_column].astype(str) == str(county))
        & (working[indicator_column].astype(str) == str(indicator))
    ][["period", "value"]].dropna(subset=["period"]).copy()

    if filtered.empty:
        raise ValueError(f"No data found for county='{county}' and indicator='{indicator}'.")

    filtered = (
        filtered.groupby("period", as_index=False)["value"]
        .mean()
        .sort_values("period", kind="mergesort")
        .reset_index(drop=True)
    )
    return SeriesContext(county=county, indicator=indicator, df=filtered)


def _warn_if_short_series(series_df: pd.DataFrame) -> None:
    """Warn when there are fewer than 12 observed points for forecasting."""
    observed_points = int(series_df["value"].notna().sum())
    if observed_points < 12:
        warnings.warn(
            "Fewer than 12 data points are available; forecast reliability may be limited.",
            stacklevel=3,
        )


def _trend_fallback_forecast(
    series: SeriesContext,
    periods_ahead: int,
    freq: str,
) -> pd.DataFrame:
    """Fallback forecast when Prophet is unavailable in the current runtime."""
    working = series.df.copy()
    working["time_index"] = np.arange(len(working), dtype=float)
    working["month"] = working["period"].dt.month
    working["quarter"] = working["period"].dt.quarter
    working["week_of_year"] = working["period"].dt.isocalendar().week.astype(int)

    features = pd.get_dummies(
        working[["time_index", "month", "quarter", "week_of_year"]].astype({"month": str, "quarter": str, "week_of_year": str}),
        drop_first=False,
    )
    model = LinearRegression()
    model.fit(features, working["value"])
    fitted = pd.Series(model.predict(features), index=working.index)

    residual_std = max(float((working["value"] - fitted).std(ddof=0)), 1.0)

    future_periods = _future_periods(working["period"], periods_ahead=periods_ahead, freq=freq)
    future_time_index = np.arange(len(working), len(working) + len(future_periods), dtype=float)
    future_features = pd.DataFrame(
        {
            "time_index": future_time_index,
            "month": future_periods.dt.month.astype(str),
            "quarter": future_periods.dt.quarter.astype(str),
            "week_of_year": future_periods.dt.isocalendar().week.astype(int).astype(str),
        }
    )
    future_features = pd.get_dummies(future_features, drop_first=False)
    future_features = future_features.reindex(columns=features.columns, fill_value=0)
    future_forecast = model.predict(future_features)

    history = pd.DataFrame(
        {
            "period": working["period"],
            "actual": working["value"],
            "forecast": fitted,
            "lower_bound": fitted - residual_std * 1.28,
            "upper_bound": fitted + residual_std * 1.28,
            "is_forecast": False,
        }
    )
    future = pd.DataFrame(
        {
            "period": future_periods,
            "actual": np.nan,
            "forecast": future_forecast,
            "lower_bound": future_forecast - residual_std * 1.28,
            "upper_bound": future_forecast + residual_std * 1.28,
            "is_forecast": True,
        }
    )
    return pd.concat([history, future], ignore_index=True)


def _build_xgboost_training_frame(series_df: pd.DataFrame) -> pd.DataFrame:
    """Create lagged and calendar features for XGBoost training."""
    working = series_df.copy().sort_values("period", kind="mergesort")
    working["lag_1"] = working["value"].shift(1)
    working["lag_2"] = working["value"].shift(2)
    working["lag_3"] = working["value"].shift(3)
    working["lag_4"] = working["value"].shift(4)
    working["rolling_mean_3"] = working["value"].shift(1).rolling(window=3, min_periods=3).mean()
    working["rolling_mean_6"] = working["value"].shift(1).rolling(window=6, min_periods=6).mean()
    working["time_index"] = np.arange(len(working), dtype=float)
    working["month"] = working["period"].dt.month
    working["quarter"] = working["period"].dt.quarter
    working["year"] = working["period"].dt.year
    working["week_of_year"] = working["period"].dt.isocalendar().week.astype(int)
    working["target"] = working["value"]
    return working.dropna().reset_index(drop=True)


def _recursive_xgboost_forecast(
    model: XGBRegressor,
    history: pd.DataFrame,
    periods_ahead: int,
    freq: str,
    interval_width: float,
) -> pd.DataFrame:
    """Forecast future periods iteratively using prior predictions as lags."""
    history = history.sort_values("period", kind="mergesort").reset_index(drop=True)
    future_rows: list[dict[str, object]] = []

    for _ in range(periods_ahead):
        next_period = _future_periods(history["period"], periods_ahead=1, freq=freq).iloc[0]
        next_features = _build_next_xgb_features(history, next_period)
        next_prediction = float(model.predict(next_features)[0])
        future_rows.append(
            {
                "period": next_period,
                "actual": np.nan,
                "forecast": next_prediction,
                "lower_bound": next_prediction - interval_width,
                "upper_bound": next_prediction + interval_width,
                "is_forecast": True,
            }
        )
        history = pd.concat(
            [
                history,
                pd.DataFrame({"period": [next_period], "value": [next_prediction]}),
            ],
            ignore_index=True,
        )

    return pd.DataFrame(future_rows)


def _build_next_xgb_features(history: pd.DataFrame, next_period: pd.Timestamp) -> pd.DataFrame:
    """Construct the next-step lag feature row for recursive XGBoost forecasting."""
    values = history["value"].tolist()
    recent = values[-6:]
    lag_values = list(reversed(recent[-4:]))
    while len(lag_values) < 4:
        lag_values.append(values[0])

    feature_row = pd.DataFrame(
        {
            "lag_1": [lag_values[0]],
            "lag_2": [lag_values[1]],
            "lag_3": [lag_values[2]],
            "lag_4": [lag_values[3]],
            "rolling_mean_3": [float(np.mean(recent[-3:])) if len(recent) >= 3 else float(np.mean(recent))],
            "rolling_mean_6": [float(np.mean(recent))],
            "time_index": [float(len(history))],
            "month": [int(next_period.month)],
            "quarter": [int(next_period.quarter)],
            "year": [int(next_period.year)],
            "week_of_year": [int(next_period.isocalendar().week)],
        }
    )
    return feature_row


def _future_periods(periods: pd.Series, periods_ahead: int, freq: str) -> pd.Series:
    """Generate future period starts aligned to the cleaned series cadence."""
    last_period = pd.to_datetime(periods).sort_values().iloc[-1]
    pandas_freq = _pandas_freq(freq)
    future_index = pd.date_range(
        start=last_period,
        periods=periods_ahead + 1,
        freq=pandas_freq,
    )[1:]
    return pd.Series(future_index)


def _prophet_freq(freq: str) -> str:
    """Map public frequency labels to Prophet-compatible values."""
    freq_key = freq.upper()
    if freq_key not in FREQ_ALIASES:
        raise ValueError("freq must be one of 'M', 'W', or 'Q'.")
    return FREQ_ALIASES[freq_key]


def _pandas_freq(freq: str) -> str:
    """Map a simple forecast frequency to a pandas date_range alias."""
    return _prophet_freq(freq)


def _infer_freq(periods: pd.Series) -> str:
    """Infer a simple M/W/Q label from the observed period spacing."""
    sorted_periods = pd.to_datetime(periods).dropna().sort_values()
    if len(sorted_periods) < 2:
        return "M"
    median_gap = float(sorted_periods.diff().dropna().dt.days.median())
    if median_gap <= 10:
        return "W"
    if median_gap >= 80:
        return "Q"
    return "M"


@lru_cache(maxsize=32)
def _holiday_years(start_year: int, end_year: int) -> tuple[int, ...]:
    """Cache the inclusive year range used for Prophet holiday tables."""
    return tuple(range(start_year, end_year + 1))


def _kenya_holidays(periods: pd.Series, periods_ahead: int, freq: str) -> pd.DataFrame:
    """Build a fixed-date Kenya holiday table for Prophet models."""
    start_year = int(pd.to_datetime(periods).min().year)
    end_year = int(_future_periods(pd.Series([pd.to_datetime(periods).max()]), periods_ahead, freq).max().year)

    rows: list[dict[str, object]] = []
    for year in _holiday_years(start_year, end_year):
        rows.extend(
            [
                {"holiday": "New Year", "ds": pd.Timestamp(year=year, month=1, day=1)},
                {"holiday": "Labour Day", "ds": pd.Timestamp(year=year, month=5, day=1)},
                {"holiday": "Madaraka Day", "ds": pd.Timestamp(year=year, month=6, day=1)},
                {"holiday": "Mashujaa Day", "ds": pd.Timestamp(year=year, month=10, day=20)},
                {"holiday": "Jamhuri Day", "ds": pd.Timestamp(year=year, month=12, day=12)},
                {"holiday": "Christmas Day", "ds": pd.Timestamp(year=year, month=12, day=25)},
                {"holiday": "Boxing Day", "ds": pd.Timestamp(year=year, month=12, day=26)},
            ]
        )
    return pd.DataFrame(rows)


def _county_column(df: pd.DataFrame) -> str:
    """Return the county/org-unit column name present in the DataFrame."""
    for candidate in ("county", "org_unit_name"):
        if candidate in df.columns:
            return candidate
    raise ValueError("Expected a 'county' or 'org_unit_name' column for forecasting.")


def _indicator_column(df: pd.DataFrame) -> str:
    """Return the indicator column name present in the DataFrame."""
    for candidate in ("indicator", "indicator_name", "indicator_id"):
        if candidate in df.columns:
            return candidate
    raise ValueError("Expected an 'indicator', 'indicator_name', or 'indicator_id' column for forecasting.")
