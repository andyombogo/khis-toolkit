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
        selected_county = (
            request.args.get("county")
            or state.data["org_unit_name"].dropna().astype(str).iloc[0]
        )
        initial_forecast = _forecast_for_county(state, selected_county)
        trend_chart = create_trend_chart(
            initial_forecast, county=selected_county, indicator=state.indicator_name
        )
        latest_values = _latest_county_values(state.data)
        map_object = create_county_map(latest_values, value_col="latest_value")
        map_html = map_object.get_root().render()
        quality_table = create_quality_table(state.scorecard)
        selected_quality = _quality_payload(state, selected_county)
        selected_mental_health = _mental_health_payload(state, selected_county)

        return render_template_string(
            INDEX_TEMPLATE,
            banner=state.banner,
            map_html=map_html,
            quality_table=quality_table,
            chart_json=trend_chart.to_json(),
            counties=khis.list_counties().to_dict(orient="records"),
            selected_county=selected_county,
            selected_quality=selected_quality,
            selected_mental_health=selected_mental_health,
            indicator_name=state.indicator_name,
            last_updated=state.last_updated,
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
        return jsonify({"status": "ok", "last_updated": state.last_updated})

    return app


def _state(app: Flask) -> DashboardState:
    """Return the cached dashboard state."""
    return app.config["DASHBOARD_STATE"]


def _load_dashboard_state() -> DashboardState:
    """Connect to DHIS2 or fall back to demo county data for the dashboard."""
    try:
        connector = khis.connect()
        if getattr(connector, "using_demo_server", False):
            data, indicator_name, indicator_id = _load_demo_dashboard_data(connector)
            banner = "Demo using DHIS2 public test data. Connect your KHIS credentials for real Kenya county data."
        else:
            data, indicator_name, indicator_id = _load_khis_dashboard_data(connector)
            banner = "Connected to KHIS credentials. Showing live county-style indicator data."
    except Exception as exc:
        data, indicator_name, indicator_id = _offline_dashboard_data()
        banner = (
            "Demo using locally generated county sample data because live DHIS2 fetch failed. "
            f"Reason: {exc}"
        )
        connector = khis.connect()

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
    )


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
    <title>KHIS Toolkit Dashboard</title>
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
      .sidebar p {
        margin-top: 0;
        line-height: 1.5;
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
      .content {
        display: grid;
        gap: 22px;
      }
      .map-wrap, .chart-wrap, .quality-wrap {
        padding: 18px;
      }
      .map-wrap h2, .chart-wrap h2, .quality-wrap h2 {
        margin: 0 0 12px;
        font-size: 24px;
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
      @media (max-width: 980px) {
        .hero {
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
          <h1>KHIS Toolkit</h1>
          <p>County dashboard for malaria trend review, data quality checks, short-horizon forecasting, and mental-health service monitoring.</p>
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
          <div class="detail-card" id="quality-detail">
            <div><strong>County:</strong> {{ selected_quality.county }}</div>
            <div><strong>Completeness:</strong> {{ selected_quality.completeness_score }}</div>
            <div><strong>Grade:</strong> {{ selected_quality.overall_quality_grade }}</div>
            <div><strong>Late reporter:</strong> {{ 'Yes' if selected_quality.late_reporter else 'No' }}</div>
            <div><strong>Suspicious zeros:</strong> {{ 'Yes' if selected_quality.suspicious_zeros else 'No' }}</div>
          </div>
          <div class="detail-card" id="mental-health-detail">
            <div><strong>Mental Health:</strong> {{ selected_mental_health.burden_band or 'N/A' }}</div>
            <div><strong>Tracked indicators:</strong> {{ selected_mental_health.tracked_indicators or 'N/A' }}</div>
            <div><strong>Latest total:</strong> {{ selected_mental_health.latest_total_value or 'N/A' }}</div>
            <div><strong>Trend:</strong> {{ selected_mental_health.trend_direction or 'N/A' }}</div>
            <div><strong>Data source:</strong> {{ selected_mental_health.data_source or 'N/A' }}</div>
          </div>
        </aside>
        <main class="content">
          <section class="panel map-wrap">
            <h2>Kenya County Map</h2>
            <div class="map-frame">{{ map_html | safe }}</div>
          </section>
          <section class="panel chart-wrap">
            <h2>Trend and Forecast</h2>
            <div id="trend-chart"></div>
          </section>
          <section class="panel quality-wrap">
            <h2>County Quality Scorecard</h2>
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
        document.getElementById('quality-detail').innerHTML = `
          <div><strong>County:</strong> ${quality.county ?? county}</div>
          <div><strong>Completeness:</strong> ${quality.completeness_score ?? 'N/A'}</div>
          <div><strong>Grade:</strong> ${quality.overall_quality_grade ?? 'N/A'}</div>
          <div><strong>Late reporter:</strong> ${quality.late_reporter ? 'Yes' : 'No'}</div>
          <div><strong>Suspicious zeros:</strong> ${quality.suspicious_zeros ? 'Yes' : 'No'}</div>
        `;

        const mentalHealthResponse = await fetch(`/api/mental-health/${encodeURIComponent(county)}`);
        const mentalHealth = await mentalHealthResponse.json();
        document.getElementById('mental-health-detail').innerHTML = `
          <div><strong>Mental Health:</strong> ${mentalHealth.burden_band ?? 'N/A'}</div>
          <div><strong>Tracked indicators:</strong> ${mentalHealth.tracked_indicators ?? 'N/A'}</div>
          <div><strong>Latest total:</strong> ${mentalHealth.latest_total_value ?? 'N/A'}</div>
          <div><strong>Trend:</strong> ${mentalHealth.trend_direction ?? 'N/A'}</div>
          <div><strong>Data source:</strong> ${mentalHealth.data_source ?? 'N/A'}</div>
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
