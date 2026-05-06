"""Streamlit Community Cloud entrypoint for the KHIS Toolkit dashboard."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import khis
from dashboard.map import create_trend_chart, render_selected_county_map_html


SECRET_ENV_KEYS = (
    "KHIS_DATA_MODE",
    "DHIS2_BASE_URL",
    "DHIS2_USERNAME",
    "DHIS2_PASSWORD",
)
SECRET_SECTIONS = ("khis", "dhis2", "dashboard")


def main() -> None:
    """Render the Streamlit version of the public KHIS dashboard."""
    st.set_page_config(
        page_title="KHIS Toolkit County Analytics",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_streamlit_runtime_defaults()
    _inject_page_styles()

    state = _load_streamlit_dashboard_state()
    counties = _county_options(state)
    default_county = _dashboard_default_selected_county(state, None)
    selected_county = st.sidebar.selectbox(
        "County",
        counties,
        index=_safe_county_index(counties, default_county),
    )

    st.sidebar.caption(f"Data mode: {state.data_mode}")
    st.sidebar.caption(f"Updated: {state.last_updated}")
    if st.sidebar.button("Refresh data", use_container_width=True):
        _load_streamlit_dashboard_state.clear()
        st.rerun()

    context = _dashboard_demo_context(state)
    st.markdown(
        f"""
        <div class="khis-header">
          <p class="khis-eyebrow">{_escape_html(context["mode_label"])}</p>
          <h1>KHIS Toolkit County Analytics</h1>
          <p>{_escape_html(context["headline"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if state.banner:
        st.info(state.banner)

    _render_summary_metrics(state)

    county_tab, quality_tab, mental_health_tab, feedback_tab = st.tabs(
        ["County view", "Quality", "Mental health", "Pilot feedback"]
    )

    with county_tab:
        _render_county_view(state, selected_county)
    with quality_tab:
        _render_quality_view(state, selected_county)
    with mental_health_tab:
        _render_mental_health_view(state, selected_county)
    with feedback_tab:
        _render_feedback_view(state, selected_county)

    st.caption(context["next_step"])


def _apply_streamlit_runtime_defaults() -> None:
    """Apply Streamlit Cloud defaults before the dashboard state is imported."""
    _apply_streamlit_secrets_to_environment()
    os.environ.setdefault("KHIS_DATA_MODE", "offline_demo")


def _apply_streamlit_secrets_to_environment(
    secrets: Mapping[str, Any] | None = None,
) -> None:
    """Promote Streamlit secrets into environment variables used by khis."""
    try:
        active_secrets: Mapping[str, Any] = st.secrets if secrets is None else secrets
    except Exception:
        return

    for key in SECRET_ENV_KEYS:
        value = _lookup_secret_value(active_secrets, key)
        if value is not None and str(value).strip():
            os.environ[key] = str(value).strip()


def _lookup_secret_value(secrets: Mapping[str, Any], key: str) -> Any | None:
    """Return a top-level or sectioned Streamlit secret value."""
    if key in secrets:
        return secrets[key]

    for section_name in SECRET_SECTIONS:
        section = secrets.get(section_name, {})
        if isinstance(section, Mapping) and key in section:
            return section[key]
    return None


@st.cache_resource(show_spinner="Loading KHIS dashboard data...")
def _load_streamlit_dashboard_state() -> Any:
    """Load and cache the existing dashboard state for Streamlit reruns."""
    from dashboard.app import _load_dashboard_state

    return _load_dashboard_state()


def _render_summary_metrics(state: Any) -> None:
    """Render dashboard scope metrics as compact Streamlit columns."""
    summary_cards = _dashboard_summary_cards(state)
    columns = st.columns(len(summary_cards))
    for column, card in zip(columns, summary_cards):
        column.metric(card["label"].title(), card["value"])
        column.caption(card["detail"])


def _render_county_view(state: Any, selected_county: str) -> None:
    """Render map and trend views for the selected county."""
    latest_values = _dashboard_latest_county_values(state.data)
    map_html = render_selected_county_map_html(
        latest_values,
        value_col="latest_value",
        selected_county=selected_county,
    )
    forecast = _dashboard_forecast_for_county(state, selected_county)
    figure = (
        create_trend_chart(
            forecast,
            county=selected_county,
            indicator=state.indicator_name,
        )
        if not forecast.empty
        else _dashboard_empty_trend_chart(selected_county, state.indicator_name)
    )

    map_column, chart_column = st.columns([1.05, 0.95])
    with map_column:
        st.subheader("County map")
        components.html(map_html, height=620, scrolling=True)
    with chart_column:
        st.subheader("Trend and short outlook")
        st.plotly_chart(figure, use_container_width=True)


def _render_quality_view(state: Any, selected_county: str) -> None:
    """Render county quality data and the full scorecard."""
    quality = _dashboard_quality_payload(state, selected_county)
    st.subheader(f"{selected_county} quality check")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Completeness", _format_percent(quality.get("completeness_score")))
    metric_columns[1].metric("Grade", _format_value(quality.get("overall_quality_grade")))
    metric_columns[2].metric("Outliers", _format_value(quality.get("outlier_count")))
    metric_columns[3].metric("Late reporter", _format_bool(quality.get("late_reporter")))

    if "message" in quality:
        st.warning(str(quality["message"]))
    elif quality.get("summary"):
        st.caption(str(quality["summary"]))

    st.dataframe(
        _quality_row_frame(quality),
        hide_index=True,
        use_container_width=True,
    )
    st.dataframe(
        state.scorecard.sort_values(["overall_quality_grade", "county"], kind="mergesort"),
        hide_index=True,
        use_container_width=True,
    )


def _render_mental_health_view(state: Any, selected_county: str) -> None:
    """Render the mental-health county summary and indicator snapshot."""
    mental_health = _dashboard_mental_health_payload(state, selected_county)
    st.subheader(f"{selected_county} mental-health indicator snapshot")

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Burden band",
        _format_value(mental_health.get("burden_band")),
    )
    metric_columns[1].metric(
        "Tracked indicators",
        _format_value(mental_health.get("tracked_indicators")),
    )
    metric_columns[2].metric(
        "Latest total",
        _format_value(mental_health.get("latest_total_value")),
    )
    metric_columns[3].metric(
        "Trend",
        _format_value(mental_health.get("trend_direction")),
    )

    if "message" in mental_health:
        st.warning(str(mental_health["message"]))

    snapshot = mental_health.get("indicator_snapshot", [])
    snapshot_frame = pd.DataFrame(snapshot)
    if snapshot_frame.empty:
        st.info("No county indicator snapshot is available yet.")
    else:
        st.dataframe(snapshot_frame, hide_index=True, use_container_width=True)


def _render_feedback_view(state: Any, selected_county: str) -> None:
    """Render the structured pilot feedback pack."""
    feedback = _dashboard_pilot_feedback_payload(state, selected_county)
    st.subheader(f"{selected_county} pilot feedback brief")
    st.write(feedback["review_focus"])

    st.text_area(
        "Briefing note",
        value=_feedback_brief_text(feedback),
        height=260,
        disabled=True,
    )

    st.write("Validation questions")
    for question in feedback.get("validation_questions", []):
        st.write(f"- {question}")

    st.write("Next step")
    st.write(feedback.get("suggested_next_action", "No suggested action available."))


def _quality_row_frame(quality: Mapping[str, Any]) -> pd.DataFrame:
    """Convert one quality payload into a compact display frame."""
    fields = [
        ("County", quality.get("county")),
        ("Completeness", _format_percent(quality.get("completeness_score"))),
        ("Quality grade", quality.get("overall_quality_grade")),
        ("Outliers", quality.get("outlier_count")),
        ("Late reporter", _format_bool(quality.get("late_reporter"))),
        ("Suspicious zeros", _format_bool(quality.get("suspicious_zeros"))),
    ]
    return pd.DataFrame(
        [{"Measure": label, "Value": _format_value(value)} for label, value in fields]
    )


def _feedback_brief_text(feedback: Mapping[str, Any]) -> str:
    """Return the reviewer-ready feedback note."""
    briefing_note = feedback.get("briefing_note")
    if briefing_note:
        return str(briefing_note)

    questions = feedback.get("validation_questions", [])
    lines = [
        f"Pilot county: {feedback.get('county', 'Selected county')}",
        f"Primary indicator: {feedback.get('indicator_name', 'Selected indicator')}",
        f"Reviewer focus: {feedback.get('review_focus', 'No reviewer focus available.')}",
        "Validation questions:",
    ]
    lines.extend(f"{index}. {question}" for index, question in enumerate(questions, 1))
    lines.append(
        f"Suggested next action: {feedback.get('suggested_next_action', 'No action available.')}"
    )
    return "\n".join(lines)


def _county_options(state: Any) -> list[str]:
    """Return counties in Kenya reference-list order, limited to loaded data when useful."""
    reference_counties = khis.list_counties()["name"].astype(str).tolist()
    if "org_unit_name" not in state.data.columns or state.data.empty:
        return reference_counties

    loaded_counties = set(
        state.data["org_unit_name"].dropna().astype(str).str.strip().tolist()
    )
    filtered = [county for county in reference_counties if county in loaded_counties]
    return filtered or reference_counties


def _safe_county_index(counties: list[str], county: str) -> int:
    """Return the selectbox index for a county, falling back to the first option."""
    try:
        return counties.index(county)
    except ValueError:
        return 0


def _format_percent(value: Any) -> str:
    """Format a numeric percentage or return a plain fallback."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _format_bool(value: Any) -> str:
    """Format a bool-like value for display."""
    if value is None:
        return "N/A"
    return "Yes" if bool(value) else "No"


def _format_value(value: Any) -> str:
    """Format common scalar values safely for Streamlit display."""
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _escape_html(value: Any) -> str:
    """Escape the small amount of custom HTML used for the page header."""
    from html import escape

    return escape(str(value), quote=True)


def _inject_page_styles() -> None:
    """Apply a little KHIS-specific polish around Streamlit's native controls."""
    st.markdown(
        """
        <style>
          .khis-header {
            border-bottom: 1px solid #d8e2dc;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
          }
          .khis-header h1 {
            color: #16324f;
            font-size: 2.35rem;
            line-height: 1.08;
            margin: 0;
          }
          .khis-header p {
            color: #3c5967;
            font-size: 1.02rem;
            margin: 0.35rem 0 0;
          }
          .khis-eyebrow {
            color: #256d5a !important;
            font-size: 0.78rem !important;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _dashboard_latest_county_values(data: pd.DataFrame) -> pd.DataFrame:
    from dashboard.app import _latest_county_values

    return _latest_county_values(data)


def _dashboard_forecast_for_county(state: Any, selected_county: str) -> pd.DataFrame:
    from dashboard.app import _forecast_for_county

    return _forecast_for_county(state, selected_county)


def _dashboard_empty_trend_chart(selected_county: str, indicator_name: str) -> Any:
    from dashboard.app import _empty_trend_chart

    return _empty_trend_chart(selected_county, indicator_name)


def _dashboard_quality_payload(state: Any, selected_county: str) -> dict[str, Any]:
    from dashboard.app import _quality_payload

    return _quality_payload(state, selected_county)


def _dashboard_mental_health_payload(state: Any, selected_county: str) -> dict[str, Any]:
    from dashboard.app import _mental_health_payload

    return _mental_health_payload(state, selected_county)


def _dashboard_pilot_feedback_payload(state: Any, selected_county: str) -> dict[str, Any]:
    from dashboard.app import _pilot_feedback_payload

    return _pilot_feedback_payload(state, selected_county)


def _dashboard_default_selected_county(state: Any, requested_county: str | None) -> str:
    from dashboard.app import _default_selected_county

    return _default_selected_county(state, requested_county)


def _dashboard_demo_context(state: Any) -> dict[str, str]:
    from dashboard.app import _demo_context

    return _demo_context(state)


def _dashboard_summary_cards(state: Any) -> list[dict[str, str]]:
    from dashboard.app import _summary_cards

    return _summary_cards(state)


if __name__ == "__main__":
    main()
