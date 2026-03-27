"""FastAPI service endpoints for KHIS Toolkit data, quality, and forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from typing import Annotated, Any
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
import pandas as pd

import khis

VERSION = "0.1.0"


class ForecastRequest(BaseModel):
    """Validated forecast request body."""

    county: str = Field(..., min_length=1)
    indicator: str = Field(..., min_length=1)
    weeks_ahead: int = Field(4, ge=1, le=26)
    method: str = Field("ensemble")


@dataclass
class APISettings:
    """Runtime settings for the KHIS API service."""

    api_key: str | None


@dataclass
class CachedAPIState:
    """Cached dataset and scorecard used by quality and demo endpoints."""

    data: pd.DataFrame
    scorecard: pd.DataFrame
    summary: str
    indicator_name: str
    indicator_id: str
    last_updated: str
    banner: str


def create_app(api_key: str | None = None) -> FastAPI:
    """Create the KHIS Toolkit FastAPI application."""
    settings = APISettings(api_key=(api_key or os.getenv("KHIS_API_KEY") or "").strip() or None)
    if settings.api_key is None:
        print(
            "WARNING: KHIS_API_KEY is not set. FastAPI is running without auth for development only."
        )

    app = FastAPI(
        title="KHIS Toolkit API",
        version=VERSION,
        description=(
            "REST API for Kenya DHIS2/KHIS county metadata, cleaned indicator data, "
            "quality scorecards, and short-horizon forecasting."
        ),
    )
    app.state.settings = settings
    app.state.cached_state = None

    async def require_api_key(
        request: Request,
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        """Protect endpoints when KHIS_API_KEY is configured."""
        expected_key = request.app.state.settings.api_key
        if expected_key is None:
            return
        if x_api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Key header.",
            )

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Return the current service health and auth mode."""
        return {
            "status": "ok",
            "version": VERSION,
            "auth_enabled": settings.api_key is not None,
        }

    @app.get("/counties", dependencies=[Depends(require_api_key)])
    def counties() -> list[dict[str, Any]]:
        """Return all 47 Kenya counties with metadata."""
        counties_df = khis.list_counties().rename(columns={"dhis2_id": "id"})
        return counties_df[
            ["id", "name", "region", "latitude", "longitude", "code", "capital"]
        ].to_dict(orient="records")

    @app.get("/indicators", dependencies=[Depends(require_api_key)])
    def indicators(search: str | None = None) -> list[dict[str, Any]]:
        """Search indicators available to the configured DHIS2/KHIS connection."""
        connector = khis.connect()
        return connector.get_indicators(search_term=search).to_dict(orient="records")

    @app.get("/data/{county}/{indicator}", dependencies=[Depends(require_api_key)])
    def data(county: str, indicator: str, periods: str = "last_12_months") -> list[dict[str, Any]]:
        """Fetch and clean indicator data for one county."""
        series_df = _fetch_series(
            request_app=app,
            county=_resolve_county_name(county),
            indicator=_resolve_indicator_label(indicator),
            periods=periods,
        )
        output = series_df.copy()
        output["period"] = pd.to_datetime(output["period"], errors="coerce").dt.strftime("%Y-%m-%d")
        return output.to_dict(orient="records")

    @app.post("/forecast", dependencies=[Depends(require_api_key)])
    def forecast(payload: ForecastRequest) -> list[dict[str, Any]]:
        """Forecast a county-indicator series with the selected method."""
        county = _resolve_county_name(payload.county)
        indicator = _resolve_indicator_label(payload.indicator)
        series_df = _fetch_series(
            request_app=app,
            county=county,
            indicator=indicator,
            periods="last_12_months",
        )
        forecast_df = khis.forecast_indicator_series(
            series_df,
            county=county,
            indicator=indicator,
            weeks_ahead=payload.weeks_ahead,
            method=payload.method,
        ).copy()
        forecast_df["period"] = pd.to_datetime(forecast_df["period"], errors="coerce").dt.strftime("%Y-%m-%d")
        return forecast_df.to_dict(orient="records")

    @app.get("/quality/{county}", dependencies=[Depends(require_api_key)])
    def quality(county: str) -> dict[str, Any]:
        """Return the quality scorecard row for one county from the cached dataset."""
        state = _ensure_cached_state(app)
        county_name = _resolve_county_name(county)
        row = state.scorecard[state.scorecard["county"].astype(str) == county_name]
        if row.empty:
            raise HTTPException(status_code=404, detail=f"No quality scorecard found for {county_name}.")
        payload = row.iloc[0].to_dict()
        payload["summary"] = state.summary
        payload["indicator"] = state.indicator_name
        return payload

    return app


def _ensure_cached_state(app: FastAPI) -> CachedAPIState:
    """Load and cache the default county dataset on first use."""
    cached_state = getattr(app.state, "cached_state", None)
    if cached_state is None:
        cached_state = _load_cached_state()
        app.state.cached_state = cached_state
    return cached_state


def _load_cached_state() -> CachedAPIState:
    """Build a default cached dataset from KHIS, demo DHIS2, or offline fallback."""
    try:
        connector = khis.connect()
        if getattr(connector, "using_demo_server", False):
            data, indicator_name, indicator_id, banner = _load_demo_state(connector)
        else:
            data, indicator_name, indicator_id, banner = _load_live_state(connector)
    except Exception as exc:
        data, indicator_name, indicator_id = _offline_data()
        banner = f"Offline demo fallback was used because live data loading failed: {exc}"

    cleaned = khis.clean(data)
    scorecard, summary = khis.quality_report(cleaned)
    return CachedAPIState(
        data=cleaned,
        scorecard=scorecard,
        summary=summary,
        indicator_name=indicator_name,
        indicator_id=indicator_id,
        last_updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        banner=banner,
    )


def _load_demo_state(connector) -> tuple[pd.DataFrame, str, str, str]:
    """Build a demo county dataset from public DHIS2 values."""
    indicators = connector.get_indicators(search_term="malaria")
    if indicators.empty:
        raise RuntimeError("No malaria indicators were available on the demo server.")
    indicator_id = str(indicators.iloc[0]["id"])
    indicator_name = str(indicators.iloc[0]["name"])

    org_units = connector.get_org_units(level=3)
    if org_units.empty:
        org_units = connector.get_org_units()
    org_units = org_units.head(5)
    raw = connector.get_analytics(
        indicator_ids=indicator_id,
        org_unit_ids=org_units["id"].tolist(),
        periods="LAST_12_MONTHS",
    )
    cleaned = khis.clean(raw)
    base_series = (
        cleaned.groupby("period", as_index=False)["value"]
        .mean()
        .sort_values("period", kind="mergesort")
        .reset_index(drop=True)
    )
    records: list[dict[str, object]] = []
    for county in khis.list_counties()[["name", "code"]].to_dict(orient="records"):
        factor = 0.75 + (int(county["code"]) % 11) * 0.05
        for _, row in base_series.iterrows():
            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "org_unit_id": f"DEMO_{int(county['code']):02d}",
                    "org_unit_name": county["name"],
                    "period": row["period"],
                    "value": round(float(row["value"]) * factor, 2),
                }
            )
    banner = "Using public DHIS2 demo data mapped onto Kenya counties for API development."
    return pd.DataFrame(records), indicator_name, indicator_id, banner


def _load_live_state(connector) -> tuple[pd.DataFrame, str, str, str]:
    """Attempt to fetch real county-style data from a KHIS instance."""
    indicators = connector.get_indicators(search_term="malaria")
    if indicators.empty:
        raise RuntimeError("No malaria indicators were found in KHIS.")
    indicator_id = str(indicators.iloc[0]["id"])
    indicator_name = str(indicators.iloc[0]["name"])

    resolved_ids: list[str] = []
    id_to_county: dict[str, str] = {}
    for county_name in khis.list_counties()["name"].tolist():
        try:
            org_unit_id = connector.resolve_org_unit_id_by_name(county_name)
        except Exception:
            continue
        resolved_ids.append(org_unit_id)
        id_to_county[org_unit_id] = county_name

    if not resolved_ids:
        raise RuntimeError("No county organisation units could be resolved from KHIS.")

    raw = connector.get_analytics(
        indicator_ids=indicator_id,
        org_unit_ids=resolved_ids,
        periods="LAST_12_MONTHS",
    )
    raw["org_unit_name"] = raw["org_unit_id"].map(id_to_county).fillna(raw["org_unit_name"])
    banner = "Using live KHIS county data."
    return raw, indicator_name, indicator_id, banner


def _offline_data() -> tuple[pd.DataFrame, str, str]:
    """Generate a local offline demo dataset for API development and tests."""
    indicator_id = "offline_malaria_cases"
    indicator_name = "Malaria Cases (Offline Demo)"
    periods = pd.date_range("2024-01-01", periods=12, freq="MS")

    records: list[dict[str, object]] = []
    for county in khis.list_counties()[["name", "code"]].to_dict(orient="records"):
        for period in periods:
            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "org_unit_id": f"OFFLINE_{int(county['code']):02d}",
                    "org_unit_name": county["name"],
                    "period": period,
                    "value": round(10 + int(county["code"]) * 0.4 + (period.month % 5), 2),
                }
            )
    return pd.DataFrame(records), indicator_name, indicator_id


def _fetch_series(
    request_app: FastAPI,
    county: str,
    indicator: str,
    periods: str,
) -> pd.DataFrame:
    """Fetch a live series where possible, otherwise serve the cached fallback."""
    try:
        connector = khis.connect()
        if not getattr(connector, "using_demo_server", False):
            indicators = connector.get_indicators(search_term=indicator)
            if indicators.empty:
                raise RuntimeError(f"Indicator '{indicator}' was not found in KHIS.")
            indicator_id = str(indicators.iloc[0]["id"])
            indicator_name = str(indicators.iloc[0]["name"])
            org_unit_id = connector.resolve_org_unit_id_by_name(county)
            raw = connector.get_analytics(
                indicator_ids=indicator_id,
                org_unit_ids=[org_unit_id],
                periods=periods,
            )
            raw["org_unit_name"] = county
            raw["indicator_name"] = indicator_name
            return khis.clean(raw)
    except Exception:
        pass

    cached = _ensure_cached_state(request_app).data
    indicator_column = "indicator_name" if "indicator_name" in cached.columns else "indicator_id"
    filtered = cached[
        (cached["org_unit_name"].astype(str) == county)
        & (
            (cached[indicator_column].astype(str).str.lower() == indicator.lower())
            | (cached.get("indicator_id", pd.Series(dtype="object")).astype(str).str.lower() == indicator.lower())
        )
    ].copy()
    if filtered.empty:
        fallback_indicator = _ensure_cached_state(request_app).indicator_name
        filtered = cached[
            (cached["org_unit_name"].astype(str) == county)
            & (cached[indicator_column].astype(str) == fallback_indicator)
        ].copy()
    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"No cached data found for county='{county}'.")
    return filtered


def _resolve_indicator_label(value: str) -> str:
    """Convert a path or body indicator value into a readable label."""
    return unquote(value).replace("_", " ").strip()


def _resolve_county_name(value: str) -> str:
    """Resolve a route or body county value into the canonical county name."""
    candidate = unquote(value).replace("_", " ").strip()
    try:
        return khis.get_county(candidate)["name"]
    except ValueError:
        return candidate


app = create_app()
