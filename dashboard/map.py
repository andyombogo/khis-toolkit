"""Dashboard view helpers for Kenya county maps, trends, and quality tables."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from khis import list_counties

try:
    import folium
    from folium.features import GeoJsonTooltip
except ImportError:  # pragma: no cover - optional in the shared runtime
    folium = None
    GeoJsonTooltip = None


@dataclass
class _FallbackMap:
    """Tiny stand-in object when Folium is unavailable in the local runtime."""

    html: str

    def get_root(self) -> "_FallbackMap":
        """Mirror the Folium map API used by the Flask app."""
        return self

    def render(self) -> str:
        """Return the fallback HTML representation."""
        return self.html

    def _repr_html_(self) -> str:
        """Notebook-friendly HTML rendering."""
        return self.html


def create_county_map(
    data_df: pd.DataFrame,
    value_col: str,
    title: str = "Kenya County Health Map",
):
    """Create a Kenya county map using Folium or a graceful HTML fallback."""
    if "county" not in data_df.columns:
        raise ValueError("create_county_map() requires a 'county' column.")
    if value_col not in data_df.columns:
        raise ValueError(
            f"create_county_map() requires '{value_col}' in the input data."
        )

    counties_df = list_counties().rename(columns={"name": "county"})
    merged = counties_df.merge(data_df[["county", value_col]], on="county", how="left")
    merged[value_col] = pd.to_numeric(merged[value_col], errors="coerce")

    if folium is None:
        return _FallbackMap(
            _fallback_map_html(merged, value_col=value_col, title=title)
        )

    map_object = folium.Map(
        location=[0.2, 37.9],
        zoom_start=6,
        tiles="CartoDB positron",
        control_scale=True,
    )
    geojson = _simplified_county_geojson(merged, value_col=value_col)

    folium.Choropleth(
        geo_data=geojson,
        data=merged,
        columns=["county", value_col],
        key_on="feature.properties.county",
        fill_color="RdYlGn_r",
        fill_opacity=0.75,
        line_opacity=0.35,
        nan_fill_color="#d9d9d9",
        legend_name=value_col.replace("_", " ").title(),
        highlight=True,
    ).add_to(map_object)

    folium.GeoJson(
        geojson,
        style_function=lambda feature: {
            "color": "#4f4f4f",
            "weight": 0.8,
            "fillOpacity": 0.0,
        },
        tooltip=GeoJsonTooltip(
            fields=["county", "region", "display_value"],
            aliases=["County", "Region", value_col.replace("_", " ").title()],
            localize=True,
            sticky=False,
        ),
    ).add_to(map_object)

    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
                background: rgba(255,255,255,0.92); padding: 10px 14px;
                border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                font-family: Georgia, serif; font-size: 16px; font-weight: 600;">
      {escape(title)}
    </div>
    """
    map_object.get_root().html.add_child(folium.Element(title_html))
    return map_object


def create_trend_chart(df: pd.DataFrame, county: str, indicator: str):
    """Create a Plotly trend chart for one county and indicator."""
    if df.empty:
        raise ValueError("create_trend_chart() requires a non-empty DataFrame.")

    working = df.copy()
    if "period" not in working.columns:
        raise ValueError("create_trend_chart() requires a 'period' column.")
    working["period"] = pd.to_datetime(working["period"], errors="coerce")
    working = working.sort_values("period", kind="mergesort")

    if {"county", "forecast"}.issubset(working.columns):
        filtered = working[working["county"].astype(str) == str(county)].copy()
    elif {"org_unit_name", "value"}.issubset(working.columns):
        filtered = working[
            (working["org_unit_name"].astype(str) == str(county))
            & (working.get("indicator_name", indicator).astype(str) == str(indicator))
        ].copy()
        filtered = filtered.rename(columns={"value": "actual"})
        filtered["forecast"] = pd.NA
        filtered["lower_bound"] = pd.NA
        filtered["upper_bound"] = pd.NA
        filtered["is_forecast"] = False
    else:
        raise ValueError(
            "The input data does not contain recognised trend-chart columns."
        )

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=filtered["period"],
            y=filtered["actual"],
            mode="lines+markers",
            name="Actual",
            line={"color": "#145a32", "width": 3},
        )
    )
    if filtered["forecast"].notna().any():
        figure.add_trace(
            go.Scatter(
                x=filtered["period"],
                y=filtered["forecast"],
                mode="lines",
                name="Forecast",
                line={"color": "#b03a2e", "width": 3, "dash": "dash"},
            )
        )
    if filtered["lower_bound"].notna().any() and filtered["upper_bound"].notna().any():
        figure.add_trace(
            go.Scatter(
                x=pd.concat([filtered["period"], filtered["period"].iloc[::-1]]),
                y=pd.concat(
                    [filtered["upper_bound"], filtered["lower_bound"].iloc[::-1]]
                ),
                fill="toself",
                fillcolor="rgba(176, 58, 46, 0.12)",
                line={"color": "rgba(0,0,0,0)"},
                hoverinfo="skip",
                name="Confidence interval",
            )
        )

    figure.update_layout(
        title=f"{county}: {indicator}",
        template="plotly_white",
        margin={"l": 50, "r": 20, "t": 70, "b": 45},
        legend={"orientation": "h", "y": 1.02, "x": 0},
        xaxis_title="Period",
        yaxis_title="Value",
    )
    return figure


def create_quality_table(scorecard_df: pd.DataFrame) -> str:
    """Render a county quality scorecard as a color-coded HTML table."""
    if scorecard_df.empty:
        return "<p>No quality scorecard is available yet.</p>"

    grade_colors = {
        "A": "#d4edda",
        "B": "#e6f4ea",
        "C": "#fff3cd",
        "D": "#ffe5b4",
        "F": "#f8d7da",
    }

    rows = []
    for row in scorecard_df.sort_values(
        ["overall_quality_grade", "county"], kind="mergesort"
    ).to_dict(orient="records"):
        grade = str(row["overall_quality_grade"])
        rows.append(f"""
            <tr style="background:{grade_colors.get(grade, '#ffffff')};">
              <td>{escape(str(row['county']))}</td>
              <td>{float(row['completeness_score']):.1f}</td>
              <td>{int(row['outlier_count'])}</td>
              <td>{'Yes' if bool(row['late_reporter']) else 'No'}</td>
              <td>{'Yes' if bool(row['suspicious_zeros']) else 'No'}</td>
              <td><strong>{escape(grade)}</strong></td>
            </tr>
            """)

    return f"""
    <table style="width:100%; border-collapse:collapse; font-family:Georgia, serif; font-size:14px;">
      <thead>
        <tr style="background:#16324f; color:white;">
          <th style="padding:10px; text-align:left;">County</th>
          <th style="padding:10px; text-align:left;">Completeness</th>
          <th style="padding:10px; text-align:left;">Outliers</th>
          <th style="padding:10px; text-align:left;">Late</th>
          <th style="padding:10px; text-align:left;">Suspicious Zeros</th>
          <th style="padding:10px; text-align:left;">Grade</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    """


def _fallback_map_html(merged: pd.DataFrame, value_col: str, title: str) -> str:
    """Create a readable HTML fallback when Folium is unavailable."""
    preview_source = merged.copy()
    preview_source["_has_value"] = preview_source[value_col].notna().astype(int)
    preview = (
        preview_source.sort_values(
            ["_has_value", "county"], ascending=[False, True], kind="mergesort"
        )[["county", "region", value_col]]
        .fillna("No data")
        .head(12)
    )
    rows = "".join(
        f"<tr><td>{escape(str(row['county']))}</td><td>{escape(str(row['region']))}</td><td>{escape(str(row[value_col]))}</td></tr>"
        for row in preview.to_dict(orient="records")
    )
    return f"""
    <div style="padding:18px; border:1px solid #d8dee9; border-radius:14px; background:#f8fbff;">
      <h3 style="margin-top:0; font-family:Georgia, serif;">{escape(title)}</h3>
      <p style="margin-bottom:12px;">Folium is not installed in this runtime, so this fallback preview shows county values in table form.</p>
      <table style="width:100%; border-collapse:collapse;">
        <thead><tr><th>County</th><th>Region</th><th>Value</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _simplified_county_geojson(merged: pd.DataFrame, value_col: str) -> dict[str, Any]:
    """Build a simplified county polygon GeoJSON from stored county centroids."""
    features = []
    for row in merged.to_dict(orient="records"):
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        lat_step = 0.28
        lon_step = 0.38
        polygon = [
            [lon - lon_step, lat - lat_step],
            [lon + lon_step, lat - lat_step],
            [lon + lon_step, lat + lat_step],
            [lon - lon_step, lat + lat_step],
            [lon - lon_step, lat - lat_step],
        ]
        value = row.get(value_col)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "county": row["county"],
                    "region": row["region"],
                    "display_value": (
                        "No data" if pd.isna(value) else round(float(value), 2)
                    ),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}
