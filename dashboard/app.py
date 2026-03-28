"""Flask dashboard for Kenya county health trends, quality, and forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
import os
from urllib.parse import unquote

from flask import Flask, jsonify, render_template_string, request
import pandas as pd

import khis
from dashboard.map import create_county_map, create_quality_table, create_trend_chart
from khis.connector import DEMO_BASE_URL, DEMO_PASSWORD, DEMO_USERNAME


@dataclass
class DashboardState:
    """Cached dashboard inputs built from KHIS or demo data."""

    data: pd.DataFrame
    scorecard: pd.DataFrame
    mental_health_data: pd.DataFrame
    mental_health_summary: pd.DataFrame
    quality_summary: str
    indicator_name: str
    indicator_id: str
    banner: str
    last_updated: str
    data_mode: str


def create_app() -> Flask:
    """Create the Flask application used for local and deployed dashboard demos."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv(
        "FLASK_SECRET_KEY", "change-this-in-production"
    )
    app.config["DASHBOARD_STATE"] = _load_dashboard_state()

    @app.get("/")
    def index():
        """Render the main county dashboard page."""
        state = _state(app)
        counties_table = khis.list_counties()
        selected_county = _default_selected_county(state, request.args.get("county"))
        initial_forecast = _forecast_for_county(state, selected_county)
        trend_chart = (
            create_trend_chart(
                initial_forecast, county=selected_county, indicator=state.indicator_name
            )
            if not initial_forecast.empty
            else _empty_trend_chart(selected_county, state.indicator_name)
        )
        latest_values = _latest_county_values(state.data)
        map_object = create_county_map(latest_values, value_col="latest_value")
        map_html = map_object.get_root().render()
        quality_table = create_quality_table(state.scorecard)
        selected_quality = _quality_payload(state, selected_county)
        selected_mental_health = _mental_health_payload(state, selected_county)
        demo_context = _demo_context(state)
        summary_cards = _summary_cards(state)
        capability_cards = _capability_cards(state)
        next_steps = _pilot_next_steps()

        return render_template_string(
            INDEX_TEMPLATE,
            banner=state.banner,
            map_html=map_html,
            quality_table=quality_table,
            chart_json=trend_chart.to_json(),
            counties=counties_table.to_dict(orient="records"),
            selected_county=selected_county,
            selected_quality=selected_quality,
            selected_mental_health=selected_mental_health,
            indicator_name=state.indicator_name,
            last_updated=state.last_updated,
            demo_context=demo_context,
            summary_cards=summary_cards,
            capability_cards=capability_cards,
            next_steps=next_steps,
        )

    @app.get("/api/counties")
    def api_counties():
        """Return the Kenya county reference list."""
        return jsonify(khis.list_counties().to_dict(orient="records"))

    @app.get("/api/forecast/<county>/<indicator>")
    def api_forecast(county: str, indicator: str):
        """Return forecast records for one county and indicator."""
        state = _state(app)
        method = request.args.get("method", "ensemble")
        periods_ahead = int(request.args.get("periods_ahead", 4))
        resolved_county = _normalise_county_input(county)
        resolved_indicator = _resolve_indicator_name(state, indicator)
        forecast_df = _forecast_for_county(
            state,
            resolved_county,
            indicator=resolved_indicator,
            periods_ahead=periods_ahead,
            method=method,
        ).copy()
        forecast_df["period"] = pd.to_datetime(
            forecast_df["period"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        return jsonify(forecast_df.to_dict(orient="records"))

    @app.get("/api/quality/<county>")
    def api_quality(county: str):
        """Return the county quality-card row for one selected county."""
        state = _state(app)
        return jsonify(_quality_payload(state, _normalise_county_input(county)))

    @app.get("/api/mental-health/<county>")
    def api_mental_health(county: str):
        """Return the mental-health summary row for one selected county."""
        state = _state(app)
        return jsonify(_mental_health_payload(state, _normalise_county_input(county)))

    @app.get("/health")
    def health():
        """Return a basic dashboard health payload."""
        state = _state(app)
        return jsonify(
            {
                "status": "ok",
                "last_updated": state.last_updated,
                "data_mode": state.data_mode,
            }
        )

    return app


def _state(app: Flask) -> DashboardState:
    """Return the cached dashboard state."""
    return app.config["DASHBOARD_STATE"]


def _load_dashboard_state() -> DashboardState:
    """Connect to DHIS2 or fall back to demo county data for the dashboard."""
    data_mode = _resolve_dashboard_data_mode()

    if data_mode == "offline_demo":
        data, indicator_name, indicator_id = _offline_dashboard_data()
        banner = (
            "Offline demo mode. Using bundled synthetic county data so the public "
            "dashboard works without KHIS or public DHIS2 availability."
        )
        connector = None
    else:
        try:
            if data_mode == "dhis2_demo":
                connector = khis.connect(
                    base_url=DEMO_BASE_URL,
                    username=DEMO_USERNAME,
                    password=DEMO_PASSWORD,
                )
                data, indicator_name, indicator_id = _load_demo_dashboard_data(
                    connector
                )
                banner = (
                    "Demo mode using the public DHIS2 HMIS server mapped onto Kenya "
                    "counties."
                )
            elif data_mode == "khis_live":
                connector = khis.connect()
                data, indicator_name, indicator_id = _load_khis_dashboard_data(
                    connector
                )
                banner = (
                    "Connected to KHIS credentials. Showing live county-style "
                    "indicator data."
                )
            else:
                connector = khis.connect()
                if getattr(connector, "using_demo_server", False):
                    data, indicator_name, indicator_id = _load_demo_dashboard_data(
                        connector
                    )
                    banner = (
                        "Demo using DHIS2 public test data. Connect your KHIS "
                        "credentials for real Kenya county data."
                    )
                else:
                    data, indicator_name, indicator_id = _load_khis_dashboard_data(
                        connector
                    )
                    banner = (
                        "Connected to KHIS credentials. Showing live county-style "
                        "indicator data."
                    )
        except Exception as exc:
            data, indicator_name, indicator_id = _offline_dashboard_data()
            banner = (
                "Offline demo fallback is active because live data loading failed. "
                f"Reason: {exc}"
            )
            connector = None

    cleaned = khis.clean(data)
    scorecard, summary = khis.quality_report(cleaned)
    county_names = (
        cleaned["org_unit_name"].dropna().astype(str).drop_duplicates().tolist()
        if "org_unit_name" in cleaned.columns
        else None
    )
    mental_health_data = khis.pull_mental_health_data(
        connector,
        counties=county_names,
    )
    mental_health_summary = khis.summarise_county_mental_health(mental_health_data)
    return DashboardState(
        data=cleaned,
        scorecard=scorecard,
        mental_health_data=mental_health_data,
        mental_health_summary=mental_health_summary,
        quality_summary=summary,
        indicator_name=indicator_name,
        indicator_id=indicator_id,
        banner=banner,
        last_updated=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        data_mode=data_mode,
    )


def _resolve_dashboard_data_mode() -> str:
    """Return the configured dashboard data mode."""
    configured = os.getenv("KHIS_DATA_MODE", "").strip().lower()
    if configured:
        if configured not in {"auto", "offline_demo", "dhis2_demo", "khis_live"}:
            raise ValueError(
                "KHIS_DATA_MODE must be one of: auto, offline_demo, dhis2_demo, khis_live."
            )
        return configured

    if os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL"):
        return "offline_demo"

    return "auto"


def _load_demo_dashboard_data(connector) -> tuple[pd.DataFrame, str, str]:
    """Map public demo-server series onto Kenya counties for illustration."""
    indicators = connector.get_indicators(search_term="malaria")
    if indicators.empty:
        raise RuntimeError(
            "No malaria indicators were available on the demo DHIS2 server."
        )
    indicator_id = str(indicators.iloc[0]["id"])
    indicator_name = str(indicators.iloc[0]["name"])

    org_units = connector.get_org_units(level=3)
    if org_units.empty:
        org_units = connector.get_org_units()
    org_units = org_units.head(6)
    if org_units.empty:
        raise RuntimeError(
            "No organisation units were available on the DHIS2 demo server."
        )

    raw = connector.get_analytics(
        indicator_ids=indicator_id,
        org_unit_ids=org_units["id"].tolist(),
        periods="LAST_12_MONTHS",
    )
    cleaned = khis.clean(raw)
    if cleaned.empty:
        raise RuntimeError("The DHIS2 demo server returned no data for the dashboard.")

    base_series = (
        cleaned.groupby("period", as_index=False)["value"]
        .mean()
        .sort_values("period", kind="mergesort")
        .reset_index(drop=True)
    )
    counties = khis.list_counties()[["name", "code", "region"]].rename(
        columns={"name": "org_unit_name"}
    )
    records: list[dict[str, object]] = []
    for county in counties.to_dict(orient="records"):
        scale = 0.72 + (int(county["code"]) % 9) * 0.06
        for _, row in base_series.iterrows():
            seasonal_bonus = ((pd.Timestamp(row["period"]).month - 1) % 4) * 0.35
            value = max(float(row["value"]) * scale + seasonal_bonus, 0.0)
            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "org_unit_id": f"DEMO_{int(county['code']):02d}",
                    "org_unit_name": county["org_unit_name"],
                    "period": row["period"],
                    "value": round(value, 2),
                }
            )
    return pd.DataFrame(records), indicator_name, indicator_id


def _load_khis_dashboard_data(connector) -> tuple[pd.DataFrame, str, str]:
    """Attempt to build a real county dashboard frame from KHIS credentials."""
    indicators = connector.get_indicators(search_term="malaria")
    if indicators.empty:
        raise RuntimeError(
            "No malaria indicators were found in the connected KHIS instance."
        )
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
        raise RuntimeError(
            "No Kenya county organisation units could be resolved from KHIS."
        )

    raw = connector.get_analytics(
        indicator_ids=indicator_id,
        org_unit_ids=resolved_ids,
        periods="LAST_12_MONTHS",
    )
    raw["org_unit_name"] = (
        raw["org_unit_id"].map(id_to_county).fillna(raw["org_unit_name"])
    )
    return raw, indicator_name, indicator_id


def _offline_dashboard_data() -> tuple[pd.DataFrame, str, str]:
    """Create a fully local county demo frame when network access is unavailable."""
    indicator_id = "offline_malaria_cases"
    indicator_name = "Malaria Cases (Offline Demo)"
    periods = pd.date_range("2024-01-01", periods=12, freq="MS")

    records: list[dict[str, object]] = []
    for county in khis.list_counties()[["name", "code"]].to_dict(orient="records"):
        for period in periods:
            baseline = 12 + (int(county["code"]) % 8) * 2.5
            seasonal = (period.month % 6) * 1.3
            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "org_unit_id": f"OFFLINE_{int(county['code']):02d}",
                    "org_unit_name": county["name"],
                    "period": period,
                    "value": round(baseline + seasonal, 2),
                }
            )
    return pd.DataFrame(records), indicator_name, indicator_id


def _latest_county_values(data: pd.DataFrame) -> pd.DataFrame:
    """Extract the latest observed value per county for the map."""
    working = data.copy()
    working["period"] = pd.to_datetime(working["period"], errors="coerce")
    latest = (
        working.sort_values(["org_unit_name", "period"], kind="mergesort")
        .groupby("org_unit_name", as_index=False)
        .tail(1)
        .rename(columns={"org_unit_name": "county", "value": "latest_value"})
    )
    return latest[["county", "latest_value"]]


def _forecast_for_county(
    state: DashboardState,
    county: str,
    indicator: str | None = None,
    periods_ahead: int = 4,
    method: str = "ensemble",
) -> pd.DataFrame:
    """Create the chart dataset, falling back to observed data if forecasting fails."""
    resolved_indicator = indicator or state.indicator_name
    try:
        return khis.forecast_indicator_series(
            state.data,
            county=county,
            indicator=resolved_indicator,
            periods_ahead=periods_ahead,
            method=method,
        ).assign(county=county)
    except Exception:
        return _observed_series_for_county(
            state,
            county=county,
            indicator=resolved_indicator,
        )


def _observed_series_for_county(
    state: DashboardState,
    county: str,
    indicator: str,
) -> pd.DataFrame:
    """Return an observed-only chart frame when forecast generation is unavailable."""
    county_frame = state.data[
        (state.data["org_unit_name"].astype(str) == str(county))
        & (state.data["indicator_name"].astype(str) == str(indicator))
    ].copy()
    if county_frame.empty:
        county_frame = state.data[
            state.data["org_unit_name"].astype(str) == str(county)
        ].copy()
    if county_frame.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "actual",
                "forecast",
                "lower_bound",
                "upper_bound",
                "is_forecast",
                "county",
            ]
        )

    county_frame["period"] = pd.to_datetime(county_frame["period"], errors="coerce")
    county_frame["actual"] = pd.to_numeric(county_frame["value"], errors="coerce")
    county_frame["forecast"] = county_frame["actual"]
    county_frame["lower_bound"] = county_frame["actual"]
    county_frame["upper_bound"] = county_frame["actual"]
    county_frame["is_forecast"] = False
    county_frame["county"] = county
    return county_frame[
        [
            "period",
            "actual",
            "forecast",
            "lower_bound",
            "upper_bound",
            "is_forecast",
            "county",
        ]
    ].sort_values("period", kind="mergesort")


def _default_selected_county(
    state: DashboardState, requested_county: str | None
) -> str:
    """Choose a safe county for the dashboard even when the loaded data is empty."""
    if requested_county and str(requested_county).strip():
        return _normalise_county_input(str(requested_county))

    if "org_unit_name" in state.data.columns:
        county_candidates = state.data["org_unit_name"].dropna().astype(str).str.strip()
        county_candidates = county_candidates[county_candidates != ""]
        if not county_candidates.empty:
            return str(county_candidates.iloc[0])

    return str(khis.list_counties().iloc[0]["name"])


def _demo_context(state: DashboardState) -> dict[str, str]:
    """Return pitch-ready copy that explains the current dashboard mode."""
    mode_details = {
        "offline_demo": {
            "mode_label": "Offline demo",
            "headline": "Pitch-ready county analytics walkthrough before KHIS access",
            "summary": (
                "This public link intentionally runs on bundled county demo data so "
                "the workflow is stable during early conversations with the KHIS team."
            ),
            "next_step": (
                "After access is granted, the same workflow can switch from demo "
                "series to real KHIS credentials without rebuilding the dashboard."
            ),
        },
        "dhis2_demo": {
            "mode_label": "DHIS2 demo",
            "headline": "County analytics workflow mapped from a public DHIS2 demo",
            "summary": (
                "This mode uses a public DHIS2 sandbox and maps the trends onto Kenya "
                "county views for a product demonstration."
            ),
            "next_step": (
                "Replace the demo credentials with KHIS access to validate real county "
                "org units and indicator naming."
            ),
        },
        "khis_live": {
            "mode_label": "KHIS live",
            "headline": "Live county analytics connected to KHIS credentials",
            "summary": (
                "This dashboard is connected to live credentials and is showing "
                "county-style operational analytics from KHIS."
            ),
            "next_step": (
                "The next step is validating indicator definitions, county mappings, "
                "and review-meeting usefulness with the KHIS team."
            ),
        },
        "auto": {
            "mode_label": "Auto mode",
            "headline": "County analytics workflow that adapts to the available data source",
            "summary": (
                "This mode decides between demo and live connections based on the "
                "available credentials and runtime environment."
            ),
            "next_step": (
                "For public demos, pin the deployment to offline demo mode so the "
                "experience stays stable."
            ),
        },
    }
    return mode_details.get(state.data_mode, mode_details["auto"])


def _summary_cards(state: DashboardState) -> list[dict[str, str]]:
    """Return headline metrics that explain the demo scope at a glance."""
    county_count = 0
    period_count = 0
    quality_count = 0
    mental_health_count = 0

    if "org_unit_name" in state.data.columns:
        county_count = int(
            state.data["org_unit_name"].dropna().astype(str).str.strip().nunique()
        )
    if "period" in state.data.columns:
        period_count = int(
            pd.to_datetime(state.data["period"], errors="coerce").nunique()
        )
    if "county" in state.scorecard.columns:
        quality_count = int(
            state.scorecard["county"].dropna().astype(str).str.strip().nunique()
        )
    if "county" in state.mental_health_summary.columns:
        mental_health_count = int(
            state.mental_health_summary["county"]
            .dropna()
            .astype(str)
            .str.strip()
            .nunique()
        )

    return [
        {
            "value": str(county_count),
            "label": "counties covered",
            "detail": "County-level trend and map view ready for walkthroughs.",
        },
        {
            "value": str(period_count),
            "label": "reporting periods",
            "detail": "Enough history to show trend movement and short outlooks.",
        },
        {
            "value": str(quality_count),
            "label": "quality scorecards",
            "detail": "Completeness and reporting issues surfaced before review meetings.",
        },
        {
            "value": str(mental_health_count),
            "label": "mental-health summaries",
            "detail": "A second workflow beyond malaria to show how the toolkit can expand.",
        },
    ]


def _capability_cards(state: DashboardState) -> list[dict[str, str]]:
    """Return the three big things the demo should prove to reviewers."""
    indicator_name = state.indicator_name
    return [
        {
            "title": "County visibility",
            "body": (
                f"One dashboard brings the current county map, latest {indicator_name} "
                "signal, and a selected county drill-down into one view."
            ),
        },
        {
            "title": "Quality before action",
            "body": (
                "Completeness, suspicious zeros, late reporting, and overall county "
                "quality grades are visible before anyone trusts the chart."
            ),
        },
        {
            "title": "Pilot-ready next step",
            "body": (
                "The same structure can switch from demo data to KHIS credentials, "
                "making this a realistic pilot conversation rather than a mockup."
            ),
        },
    ]


def _pilot_next_steps() -> list[str]:
    """Return the short ask to make after showing the public demo."""
    return [
        "Validate one county workflow with a KHIS reviewer or county data team.",
        "Swap the demo credentials for read-only KHIS access and verify real org-unit IDs.",
        "Compare one live malaria or mental-health indicator pack against the existing review process.",
    ]


def _empty_trend_chart(county: str, indicator: str):
    """Return a readable placeholder chart when no trend data is available."""
    from plotly import graph_objects as go

    figure = go.Figure()
    figure.update_layout(
        title=f"{county}: {indicator}",
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 70, "b": 45},
        xaxis_title="Period",
        yaxis_title="Value",
        annotations=[
            {
                "text": "No usable series is available for this county yet.",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "#64748b"},
            }
        ],
    )
    return figure


def _quality_payload(state: DashboardState, county: str) -> dict[str, object]:
    """Return the quality-card payload for one county."""
    row = state.scorecard[state.scorecard["county"].astype(str) == str(county)]
    if row.empty:
        return {
            "county": county,
            "message": "No quality scorecard row is available for this county.",
        }
    payload = row.iloc[0].to_dict()
    payload["summary"] = state.quality_summary
    return payload


def _mental_health_payload(state: DashboardState, county: str) -> dict[str, object]:
    """Return a mental-health snapshot payload for one county."""
    row = state.mental_health_summary[
        state.mental_health_summary["county"].astype(str) == str(county)
    ]
    snapshot = khis.county_indicator_snapshot(state.mental_health_data, county)
    if row.empty:
        return {
            "county": county,
            "message": "No mental-health summary is available for this county.",
            "indicator_snapshot": [],
        }
    payload = row.iloc[0].to_dict()
    payload["indicator_snapshot"] = snapshot.to_dict(orient="records")
    return payload


def _resolve_indicator_name(state: DashboardState, indicator_path_value: str) -> str:
    """Resolve a path parameter into the cached indicator name."""
    candidate = unquote(indicator_path_value).replace("_", " ").strip().lower()
    if candidate in {
        state.indicator_name.lower(),
        state.indicator_id.lower(),
        "malaria",
        "malaria cases",
    }:
        return state.indicator_name
    return state.indicator_name


def _normalise_county_input(county_path_value: str) -> str:
    """Resolve a county route parameter into the canonical Kenya county name."""
    candidate = unquote(county_path_value).replace("_", " ").strip()
    try:
        return khis.get_county(candidate)["name"]
    except ValueError:
        return candidate


INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KHIS Toolkit County Analytics Demo</title>
    <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
    <style>
      :root {
        --ink: #16324f;
        --paper: #f7f4ed;
        --accent: #b03a2e;
        --leaf: #256d5a;
        --card: #ffffff;
        --line: #d9d4c8;
      }
      body {
        margin: 0;
        font-family: Georgia, serif;
        background:
          radial-gradient(circle at top right, rgba(37,109,90,0.12), transparent 28%),
          linear-gradient(180deg, #fffdf7 0%, var(--paper) 100%);
        color: var(--ink);
      }
      .shell {
        max-width: 1280px;
        margin: 0 auto;
        padding: 24px;
      }
      .banner {
        background: rgba(255, 244, 217, 0.96);
        border: 1px solid #e2c97f;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 22px;
        font-size: 15px;
      }
      .eyebrow {
        margin: 0 0 10px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--leaf);
      }
      .hero {
        display: grid;
        grid-template-columns: 280px 1fr;
        gap: 22px;
        align-items: start;
      }
      .panel {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 14px 34px rgba(22,50,79,0.08);
      }
      .sidebar {
        padding: 20px;
        position: sticky;
        top: 18px;
      }
      .sidebar h1 {
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 30px;
      }
      .mode-pill {
        display: inline-flex;
        align-items: center;
        padding: 7px 12px;
        border-radius: 999px;
        background: rgba(37,109,90,0.1);
        color: var(--leaf);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      .sidebar p {
        margin-top: 0;
        line-height: 1.5;
      }
      .sidebar-lead {
        font-size: 17px;
      }
      label {
        display: block;
        margin: 18px 0 8px;
        font-weight: 700;
      }
      select {
        width: 100%;
        padding: 11px 12px;
        border-radius: 10px;
        border: 1px solid var(--line);
        font-family: Georgia, serif;
        font-size: 15px;
      }
      .meta {
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--line);
        font-size: 14px;
      }
      .note-card {
        margin-top: 14px;
        padding: 16px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(22,50,79,0.05), rgba(37,109,90,0.08));
        border: 1px solid #c8d9d3;
      }
      .note-card h3 {
        margin: 0 0 10px;
        font-size: 18px;
      }
      .note-card p {
        margin: 0;
        font-size: 14px;
      }
      .content {
        display: grid;
        gap: 22px;
      }
      .summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
      }
      .summary-card {
        padding: 18px;
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,250,255,0.96));
        border: 1px solid #dfe7f2;
      }
      .summary-value {
        font-size: 34px;
        font-weight: 700;
        line-height: 1;
      }
      .summary-label {
        margin-top: 8px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--leaf);
      }
      .summary-detail {
        margin-top: 8px;
        font-size: 14px;
        line-height: 1.5;
      }
      .section-copy {
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 18px;
      }
      .capability-grid {
        display: grid;
        gap: 14px;
      }
      .capability-card {
        padding: 16px 18px;
        border-radius: 16px;
        background: #fbfcfe;
        border: 1px solid #dfe7f2;
      }
      .capability-card h3 {
        margin: 0 0 8px;
        font-size: 19px;
      }
      .capability-card p {
        margin: 0;
        line-height: 1.55;
      }
      .map-wrap, .chart-wrap, .quality-wrap {
        padding: 18px;
      }
      .map-wrap h2, .chart-wrap h2, .quality-wrap h2 {
        margin: 0 0 12px;
        font-size: 24px;
      }
      .subtext {
        margin: 0 0 16px;
        color: #506070;
        line-height: 1.55;
      }
      .map-frame {
        min-height: 480px;
        border-radius: 14px;
        overflow: hidden;
      }
      #trend-chart {
        min-height: 420px;
      }
      .detail-card {
        margin-top: 14px;
        padding: 14px;
        border-radius: 14px;
        background: #f8fbff;
        border: 1px solid #dbe6f0;
      }
      .detail-card strong {
        display: inline-block;
        min-width: 140px;
      }
      .mini-list {
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid #dbe6f0;
      }
      .mini-list h4 {
        margin: 0 0 8px;
        font-size: 15px;
      }
      .mini-list ul {
        margin: 0;
        padding-left: 18px;
      }
      .mini-list li {
        margin-bottom: 6px;
        line-height: 1.45;
      }
      .cta-list {
        margin: 12px 0 0;
        padding-left: 18px;
      }
      .cta-list li {
        margin-bottom: 8px;
        line-height: 1.5;
      }
      @media (max-width: 980px) {
        .hero {
          grid-template-columns: 1fr;
        }
        .summary-grid,
        .section-copy {
          grid-template-columns: 1fr;
        }
        .sidebar {
          position: static;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="banner">{{ banner }}</div>
      <div class="hero">
        <aside class="panel sidebar">
          <div class="eyebrow">Kenya county analytics demo</div>
          <div class="mode-pill">{{ demo_context.mode_label }}</div>
          <h1>KHIS Toolkit</h1>
          <p class="sidebar-lead">{{ demo_context.headline }}</p>
          <p>{{ demo_context.summary }}</p>
          <label for="county-select">County</label>
          <select id="county-select">
            {% for county in counties %}
            <option value="{{ county.name }}" {% if county.name == selected_county %}selected{% endif %}>{{ county.name }} ({{ county.region }})</option>
            {% endfor %}
          </select>
          <div class="meta">
            <div><strong>Indicator:</strong> {{ indicator_name }}</div>
            <div><strong>Last updated:</strong> {{ last_updated }}</div>
          </div>
          <div class="note-card">
            <h3>What happens after access is granted?</h3>
            <p>{{ demo_context.next_step }}</p>
          </div>
          <div class="detail-card" id="quality-detail">
            <div><strong>County:</strong> {{ selected_quality.county }}</div>
            <div><strong>Completeness:</strong> {{ selected_quality.completeness_score }}</div>
            <div><strong>Grade:</strong> {{ selected_quality.overall_quality_grade }}</div>
            <div><strong>Late reporter:</strong> {{ 'Yes' if selected_quality.late_reporter else 'No' }}</div>
            <div><strong>Suspicious zeros:</strong> {{ 'Yes' if selected_quality.suspicious_zeros else 'No' }}</div>
            {% if selected_quality.summary %}
            <div class="mini-list">
              <h4>Why this matters</h4>
              <div>{{ selected_quality.summary }}</div>
            </div>
            {% endif %}
          </div>
          <div class="detail-card" id="mental-health-detail">
            <div><strong>Mental Health:</strong> {{ selected_mental_health.burden_band or 'N/A' }}</div>
            <div><strong>Tracked indicators:</strong> {{ selected_mental_health.tracked_indicators or 'N/A' }}</div>
            <div><strong>Latest total:</strong> {{ selected_mental_health.latest_total_value or 'N/A' }}</div>
            <div><strong>Trend:</strong> {{ selected_mental_health.trend_direction or 'N/A' }}</div>
            <div><strong>Data source:</strong> {{ selected_mental_health.data_source or 'N/A' }}</div>
            {% if selected_mental_health.get('indicator_snapshot') %}
            <div class="mini-list">
              <h4>Latest indicator snapshot</h4>
              <ul>
                {% for row in selected_mental_health.get('indicator_snapshot', [])[:3] %}
                <li>{{ row.indicator_name }}: {{ row.latest_value }} ({{ row.latest_period }})</li>
                {% endfor %}
              </ul>
            </div>
            {% endif %}
          </div>
        </aside>
        <main class="content">
          <section class="summary-grid">
            {% for card in summary_cards %}
            <article class="panel summary-card">
              <div class="summary-value">{{ card.value }}</div>
              <div class="summary-label">{{ card.label }}</div>
              <div class="summary-detail">{{ card.detail }}</div>
            </article>
            {% endfor %}
          </section>
          <section class="section-copy">
            <article class="panel quality-wrap">
              <h2>What This Demo Proves</h2>
              <p class="subtext">This public link is designed for early KHIS conversations. It shows the workflow, the county framing, and the review value before any live credentials are shared.</p>
              <div class="capability-grid">
                {% for card in capability_cards %}
                <div class="capability-card">
                  <h3>{{ card.title }}</h3>
                  <p>{{ card.body }}</p>
                </div>
                {% endfor %}
              </div>
            </article>
            <article class="panel quality-wrap">
              <h2>Pilot Ask</h2>
              <p class="subtext">The smallest useful next step is a read-only validation pass with one county or one indicator pack. The product does not need a full national rollout to prove value.</p>
              <ol class="cta-list">
                {% for step in next_steps %}
                <li>{{ step }}</li>
                {% endfor %}
              </ol>
            </article>
          </section>
          <section class="panel map-wrap">
            <h2>Kenya County Map</h2>
            <p class="subtext">Latest county-level value for the selected indicator. In offline demo mode, the map uses stable bundled county series so the public walkthrough does not depend on live KHIS uptime.</p>
            <div class="map-frame">{{ map_html | safe }}</div>
          </section>
          <section class="panel chart-wrap">
            <h2>Trend and Forecast</h2>
            <p class="subtext">Observed series and short-horizon forecast for the selected county. This is the part of the workflow that can later be validated against a real county reporting cycle.</p>
            <div id="trend-chart"></div>
          </section>
          <section class="panel quality-wrap">
            <h2>County Quality Scorecard</h2>
            <p class="subtext">A county-facing view of completeness, outliers, timeliness, and suspicious zeros so that the data quality conversation happens before action is taken on the chart.</p>
            {{ quality_table | safe }}
          </section>
        </main>
      </div>
    </div>
    <script>
      const chartFigure = {{ chart_json | safe }};
      Plotly.newPlot('trend-chart', chartFigure.data, chartFigure.layout, {responsive: true});

      async function refreshCountyViews(county) {
        const indicatorPath = encodeURIComponent("{{ indicator_name }}");
        const forecastResponse = await fetch(`/api/forecast/${encodeURIComponent(county)}/${indicatorPath}`);
        const forecastData = await forecastResponse.json();

        const periods = forecastData.map(row => row.period);
        const actual = forecastData.map(row => row.actual);
        const forecast = forecastData.map(row => row.forecast);
        const lower = forecastData.map(row => row.lower_bound);
        const upper = forecastData.map(row => row.upper_bound);

        Plotly.react('trend-chart', [
          {
            x: periods,
            y: actual,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Actual',
            line: {color: '#145a32', width: 3}
          },
          {
            x: periods,
            y: forecast,
            type: 'scatter',
            mode: 'lines',
            name: 'Forecast',
            line: {color: '#b03a2e', width: 3, dash: 'dash'}
          },
          {
            x: periods.concat([...periods].reverse()),
            y: upper.concat([...lower].reverse()),
            type: 'scatter',
            fill: 'toself',
            fillcolor: 'rgba(176, 58, 46, 0.12)',
            line: {color: 'rgba(0,0,0,0)'},
            hoverinfo: 'skip',
            name: 'Confidence interval'
          }
        ], {
          title: `${county}: {{ indicator_name }}`,
          template: 'plotly_white',
          margin: {l: 50, r: 20, t: 70, b: 45},
          legend: {orientation: 'h', y: 1.02, x: 0},
          xaxis: {title: 'Period'},
          yaxis: {title: 'Value'}
        }, {responsive: true});

        const qualityResponse = await fetch(`/api/quality/${encodeURIComponent(county)}`);
        const quality = await qualityResponse.json();
        const qualitySummary = quality.summary ? `
          <div class="mini-list">
            <h4>Why this matters</h4>
            <div>${quality.summary}</div>
          </div>
        ` : '';
        document.getElementById('quality-detail').innerHTML = `
          <div><strong>County:</strong> ${quality.county ?? county}</div>
          <div><strong>Completeness:</strong> ${quality.completeness_score ?? 'N/A'}</div>
          <div><strong>Grade:</strong> ${quality.overall_quality_grade ?? 'N/A'}</div>
          <div><strong>Late reporter:</strong> ${quality.late_reporter ? 'Yes' : 'No'}</div>
          <div><strong>Suspicious zeros:</strong> ${quality.suspicious_zeros ? 'Yes' : 'No'}</div>
          ${qualitySummary}
        `;

        const mentalHealthResponse = await fetch(`/api/mental-health/${encodeURIComponent(county)}`);
        const mentalHealth = await mentalHealthResponse.json();
        const mentalHealthSnapshot = Array.isArray(mentalHealth.indicator_snapshot) && mentalHealth.indicator_snapshot.length
          ? `
            <div class="mini-list">
              <h4>Latest indicator snapshot</h4>
              <ul>
                ${mentalHealth.indicator_snapshot.slice(0, 3).map(row =>
                  `<li>${row.indicator_name}: ${row.latest_value} (${row.latest_period})</li>`
                ).join('')}
              </ul>
            </div>
          `
          : '';
        document.getElementById('mental-health-detail').innerHTML = `
          <div><strong>Mental Health:</strong> ${mentalHealth.burden_band ?? 'N/A'}</div>
          <div><strong>Tracked indicators:</strong> ${mentalHealth.tracked_indicators ?? 'N/A'}</div>
          <div><strong>Latest total:</strong> ${mentalHealth.latest_total_value ?? 'N/A'}</div>
          <div><strong>Trend:</strong> ${mentalHealth.trend_direction ?? 'N/A'}</div>
          <div><strong>Data source:</strong> ${mentalHealth.data_source ?? 'N/A'}</div>
          ${mentalHealthSnapshot}
        `;
      }

      document.getElementById('county-select').addEventListener('change', (event) => {
        refreshCountyViews(event.target.value);
      });
    </script>
  </body>
</html>
"""


app = create_app()
