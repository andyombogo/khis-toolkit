"""Dashboard view helpers for Kenya county maps, trends, and quality tables."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from html import escape
from importlib.resources import files
import json
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

    merged = _merge_county_values(data_df, value_col=value_col)

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
    geojson = _county_boundary_geojson(merged, value_col=value_col)

    folium.Choropleth(
        geo_data=geojson,
        data=merged,
        columns=["county", value_col],
        key_on="feature.properties.county",
        fill_color="RdYlGn_r",
        fill_opacity=0.82,
        line_opacity=0.85,
        nan_fill_color="#d9d9d9",
        legend_name=value_col.replace("_", " ").title(),
        highlight=True,
    ).add_to(map_object)

    folium.GeoJson(
        geojson,
        style_function=lambda feature: {
            "color": "#243b53",
            "weight": 1.4,
            "fillOpacity": 0.02,
        },
        highlight_function=lambda feature: {
            "color": "#0f172a",
            "weight": 2.2,
            "fillOpacity": 0.18,
        },
        tooltip=GeoJsonTooltip(
            fields=["county", "region", "display_value"],
            aliases=["County", "Region", value_col.replace("_", " ").title()],
            localize=True,
            sticky=False,
        ),
    ).add_to(map_object)

    _fit_map_to_counties(map_object, merged)

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


def render_county_map_html(map_object, aspect_ratio: str = "68%") -> str:
    """Render the county map as embeddable HTML that behaves reliably in Flask."""
    if isinstance(map_object, _FallbackMap):
        return map_object.render()

    html = map_object.get_root().render()
    escaped = escape(html, quote=True)
    return (
        '<iframe title="KHIS Toolkit county map" '
        'style="width:100%; min-height:520px; border:0; border-radius:14px;" '
        'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
        f'srcdoc="{escaped}"></iframe>'
    )


def render_selected_county_map_html(
    data_df: pd.DataFrame,
    value_col: str,
    selected_county: str | None = None,
    title: str = "Kenya County Health Map",
) -> str:
    """Render a stable inline county map with the selected county highlighted."""
    merged = _merge_county_values(data_df, value_col=value_col)
    return _svg_county_map_html(
        merged,
        value_col=value_col,
        selected_county=selected_county,
        title=title,
    )


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


def _merge_county_values(data_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Join Kenya county metadata onto the current county values."""
    counties_df = list_counties().rename(columns={"name": "county"})
    merged = counties_df.merge(data_df[["county", value_col]], on="county", how="left")
    merged[value_col] = pd.to_numeric(merged[value_col], errors="coerce")
    return merged


@lru_cache(maxsize=1)
def _load_county_boundary_geojson() -> dict[str, Any] | None:
    """Load the bundled Kenya county boundary GeoJSON if available."""
    try:
        resource = files("khis").joinpath("data/kenya_counties.geojson")
        with resource.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def _county_boundary_geojson(merged: pd.DataFrame, value_col: str) -> dict[str, Any]:
    """Return county boundary GeoJSON enriched with dashboard values."""
    source = _load_county_boundary_geojson()
    if not source:
        return _simplified_county_geojson(merged, value_col=value_col)

    county_lookup = {
        str(row["county"]): row for row in merged.to_dict(orient="records")
    }
    features: list[dict[str, Any]] = []
    for feature in source.get("features", []):
        properties = dict(feature.get("properties", {}))
        county_name = str(properties.get("county", "")).strip()
        row = county_lookup.get(county_name)
        raw_value = row.get(value_col) if row else None
        properties.update(
            {
                "county": county_name,
                "region": row.get("region", "Unknown") if row else "Unknown",
                "display_value": (
                    "No data" if pd.isna(raw_value) else round(float(raw_value), 2)
                ),
                "raw_value": None if pd.isna(raw_value) else float(raw_value),
            }
        )
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": feature.get("geometry"),
            }
        )

    return {"type": "FeatureCollection", "features": features}


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


def _fit_map_to_counties(map_object, merged: pd.DataFrame) -> None:
    """Fit the map viewport to the county centroids with a small padding."""
    latitudes = pd.to_numeric(merged["latitude"], errors="coerce").dropna()
    longitudes = pd.to_numeric(merged["longitude"], errors="coerce").dropna()
    if latitudes.empty or longitudes.empty:
        return

    padding_lat = 0.8
    padding_lon = 0.8
    southwest = [
        float(latitudes.min() - padding_lat),
        float(longitudes.min() - padding_lon),
    ]
    northeast = [
        float(latitudes.max() + padding_lat),
        float(longitudes.max() + padding_lon),
    ]
    map_object.fit_bounds([southwest, northeast])


def _svg_county_map_html(
    merged: pd.DataFrame,
    value_col: str,
    selected_county: str | None,
    title: str,
) -> str:
    """Render a reliable inline SVG map for the dashboard demo."""
    width = 920
    height = 560
    margin = 34
    geojson = _county_boundary_geojson(merged, value_col=value_col)
    rings_by_feature = [
        _feature_outer_rings(feature.get("geometry")) for feature in geojson["features"]
    ]
    points = [
        coord
        for feature_rings in rings_by_feature
        for ring in feature_rings
        for coord in ring
    ]
    if not points:
        return _fallback_map_html(merged, value_col=value_col, title=title)

    lon_min = min(float(lon) for lon, _ in points) - 0.2
    lon_max = max(float(lon) for lon, _ in points) + 0.2
    lat_min = min(float(lat) for _, lat in points) - 0.2
    lat_max = max(float(lat) for _, lat in points) + 0.2

    def _project(lon: float, lat: float) -> tuple[float, float]:
        x = margin + ((lon - lon_min) / (lon_max - lon_min)) * (width - 2 * margin)
        y = (
            height
            - margin
            - ((lat - lat_min) / (lat_max - lat_min)) * (height - 2 * margin)
        )
        return round(x, 1), round(y, 1)

    values = pd.to_numeric(merged[value_col], errors="coerce")
    finite_values = values.dropna()
    min_value = float(finite_values.min()) if not finite_values.empty else 0.0
    max_value = float(finite_values.max()) if not finite_values.empty else 1.0
    selected_label = str(selected_county).strip() if selected_county else ""

    polygons: list[str] = []
    selected_summary = {
        "county": selected_label or "No county selected",
        "region": "N/A",
        "value": "No data",
    }
    for feature, rings in zip(geojson["features"], rings_by_feature):
        props = feature.get("properties", {})
        county_name = str(props.get("county", "")).strip()
        region = str(props.get("region", "Unknown"))
        raw_value = props.get("raw_value")
        is_selected = county_name == selected_label
        fill = _county_fill_color(raw_value, min_value=min_value, max_value=max_value)
        stroke = "#0f172a" if is_selected else "#385170"
        stroke_width = "4" if is_selected else "1.25"
        opacity = "1.0" if is_selected else "0.92"
        display_value = "No data" if pd.isna(raw_value) else f"{float(raw_value):.1f}"
        if is_selected:
            selected_summary = {
                "county": county_name,
                "region": region,
                "value": display_value,
            }
        title_text = (
            f"{escape(county_name)} | {escape(region)} | {escape(display_value)}"
        )
        for ring in rings:
            point_string = " ".join(
                f"{x},{y}"
                for x, y in (_project(float(lon), float(lat)) for lon, lat in ring)
            )
            polygons.append(f"""
                <polygon points="{point_string}" fill="{fill}" stroke="{stroke}"
                  stroke-width="{stroke_width}" fill-opacity="{opacity}">
                  <title>{title_text}</title>
                </polygon>
                """)

    indicator_label = value_col.replace("_", " ").title()
    selected_copy = (
        f"{escape(selected_summary['county'])} highlighted"
        if selected_label
        else "Select a county to highlight it on the map"
    )
    return f"""
    <div style="background:#f8fbff; border:1px solid #dbe6f0; border-radius:16px; overflow:hidden;">
      <div style="display:flex; justify-content:space-between; gap:18px; padding:16px 18px 8px; font-family:Georgia, serif; flex-wrap:wrap;">
        <div>
          <div style="font-size:20px; font-weight:700; color:#16324f;">{escape(title)}</div>
          <div style="margin-top:6px; color:#476175; font-size:14px;">{escape(selected_copy)}</div>
        </div>
        <div style="display:flex; gap:18px; flex-wrap:wrap; color:#16324f; font-size:14px;">
          <div><strong>County:</strong> {escape(selected_summary['county'])}</div>
          <div><strong>Region:</strong> {escape(selected_summary['region'])}</div>
          <div><strong>{escape(indicator_label)}:</strong> {escape(selected_summary['value'])}</div>
        </div>
      </div>
      <svg viewBox="0 0 {width} {height}" style="display:block; width:100%; height:auto; background:linear-gradient(180deg, #eef5fb 0%, #f9fcff 100%);">
        <rect x="0" y="0" width="{width}" height="{height}" fill="transparent"></rect>
        {''.join(polygons)}
      </svg>
      <div style="padding:10px 18px 18px; font-family:Georgia, serif; font-size:13px; color:#506070;">
        Real Kenya county boundaries bundled for the demo. The selected county is outlined in dark navy.
      </div>
    </div>
    """


def _feature_outer_rings(geometry: Any) -> list[list[list[float]]]:
    """Return the outer polygon rings from Polygon or MultiPolygon geometry."""
    if not isinstance(geometry, dict):
        return []

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        return [coordinates[0]] if coordinates else []
    if geometry_type == "MultiPolygon":
        return [polygon[0] for polygon in coordinates if polygon]
    return []


def _county_fill_color(value: Any, min_value: float, max_value: float) -> str:
    """Return a county fill color on a green-yellow-red scale."""
    if pd.isna(value):
        return "#e5e7eb"
    if max_value <= min_value:
        ratio = 0.5
    else:
        ratio = (float(value) - min_value) / (max_value - min_value)

    palette = [
        (26, 152, 80),
        (254, 224, 139),
        (215, 48, 39),
    ]
    if ratio <= 0.5:
        local = ratio / 0.5
        start, end = palette[0], palette[1]
    else:
        local = (ratio - 0.5) / 0.5
        start, end = palette[1], palette[2]

    red = int(start[0] + (end[0] - start[0]) * local)
    green = int(start[1] + (end[1] - start[1]) * local)
    blue = int(start[2] + (end[2] - start[2]) * local)
    return f"rgb({red},{green},{blue})"
