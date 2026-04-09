"""Pilot-feedback helpers for post-demo county validation conversations.

Phase 8 of the toolkit is less about adding another chart and more about
turning a public demo into a structured validation pass with KHIS reviewers or
county data teams. These helpers build a small, reusable feedback pack from the
current dashboard or API state so one county walkthrough can lead to concrete
next steps.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_pilot_feedback_payload(
    county: str,
    indicator_name: str,
    data_mode: str,
    quality_payload: Mapping[str, Any] | None = None,
    mental_health_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured county-validation prompt for KHIS pilot feedback."""
    county_name = str(county).strip() or "Selected county"
    indicator_label = str(indicator_name).strip() or "Selected indicator"
    quality = dict(quality_payload or {})
    mental_health = dict(mental_health_payload or {})

    quality_grade = _string_or_none(quality.get("overall_quality_grade"))
    completeness_label = _score_label(quality.get("completeness_score"))
    late_reporter = _bool_or_none(quality.get("late_reporter"))
    suspicious_zeros = _bool_or_none(quality.get("suspicious_zeros"))
    tracked_indicators = _int_or_none(mental_health.get("tracked_indicators"))
    burden_band = _string_or_none(mental_health.get("burden_band"))

    review_focus = _review_focus(
        quality_grade=quality_grade,
        late_reporter=late_reporter,
        suspicious_zeros=suspicious_zeros,
        tracked_indicators=tracked_indicators,
    )
    validation_questions = _validation_questions(
        county_name=county_name,
        indicator_label=indicator_label,
        quality_grade=quality_grade,
        late_reporter=late_reporter,
        suspicious_zeros=suspicious_zeros,
        tracked_indicators=tracked_indicators,
    )
    suggested_next_action = _suggested_next_action(
        data_mode=data_mode,
        tracked_indicators=tracked_indicators,
    )
    recommended_reviewer = _recommended_reviewer(data_mode)

    briefing_lines = [
        f"Pilot county: {county_name}",
        f"Dashboard mode: {_mode_label(data_mode)}",
        f"Primary indicator: {indicator_label}",
    ]
    if completeness_label:
        briefing_lines.append(f"Current completeness score: {completeness_label}")
    if quality_grade:
        briefing_lines.append(f"Current quality grade: {quality_grade}")
    if tracked_indicators is not None:
        briefing_lines.append(
            f"Mental-health indicators tracked: {tracked_indicators}"
        )
    if burden_band:
        briefing_lines.append(f"Mental-health burden band: {burden_band}")
    briefing_lines.append(f"Reviewer focus: {review_focus}")
    briefing_lines.append("Validation questions:")
    briefing_lines.extend(
        f"{index}. {question}"
        for index, question in enumerate(validation_questions, start=1)
    )
    briefing_lines.append(f"Suggested next action: {suggested_next_action}")

    return {
        "county": county_name,
        "indicator_name": indicator_label,
        "data_mode": data_mode,
        "quality_grade": quality_grade,
        "completeness_label": completeness_label,
        "tracked_indicators": tracked_indicators,
        "mental_health_burden_band": burden_band,
        "review_focus": review_focus,
        "recommended_reviewer": recommended_reviewer,
        "validation_questions": validation_questions,
        "suggested_next_action": suggested_next_action,
        "briefing_note": "\n".join(briefing_lines),
    }


def _review_focus(
    *,
    quality_grade: str | None,
    late_reporter: bool | None,
    suspicious_zeros: bool | None,
    tracked_indicators: int | None,
) -> str:
    """Choose the most useful validation emphasis for the pilot conversation."""
    data_quality_flags: list[str] = []
    if quality_grade in {"C", "D", "F"}:
        data_quality_flags.append(f"county quality grade {quality_grade}")
    if late_reporter:
        data_quality_flags.append("late reporting")
    if suspicious_zeros:
        data_quality_flags.append("suspicious zero patterns")

    if data_quality_flags:
        joined_flags = ", ".join(data_quality_flags)
        return (
            "Start with data-quality validation before interpreting the trend, "
            f"especially around {joined_flags}."
        )

    if tracked_indicators and tracked_indicators > 0:
        return (
            "Validate the core malaria trend and one mental-health indicator pack "
            "so the pilot proves the toolkit can support more than one county "
            "review workflow."
        )

    return (
        "Validate county mapping, indicator definitions, and whether the trend view "
        "would be useful in a real county review meeting."
    )


def _validation_questions(
    *,
    county_name: str,
    indicator_label: str,
    quality_grade: str | None,
    late_reporter: bool | None,
    suspicious_zeros: bool | None,
    tracked_indicators: int | None,
) -> list[str]:
    """Build a short set of questions for the first KHIS validation pass."""
    questions = [
        (
            f"Does {county_name} map to the same organisation unit used in your "
            "current KHIS review workflow?"
        ),
        (
            f"Is '{indicator_label}' the right indicator name and definition for "
            "the first validation pass?"
        ),
    ]

    if quality_grade in {"C", "D", "F"} or late_reporter or suspicious_zeros:
        questions.append(
            "Do the completeness, late-reporting, or suspicious-zero flags match "
            "what the county team would expect from the current review cycle?"
        )
    else:
        questions.append(
            "Does the latest reporting period shown here line up with the county's "
            "recent review cycle and reporting cadence?"
        )

    if tracked_indicators and tracked_indicators > 0:
        questions.append(
            "Which one or two mental-health indicators should be validated live "
            "first after the demo?"
        )
    else:
        questions.append(
            "Which live indicator pack should replace the current demo series first?"
        )

    questions.append(
        "What is the smallest read-only pilot outcome that would make this useful "
        "for the next county review meeting?"
    )
    return questions


def _suggested_next_action(data_mode: str, tracked_indicators: int | None) -> str:
    """Recommend the next operational move after the walkthrough."""
    if data_mode == "khis_live":
        if tracked_indicators and tracked_indicators > 0:
            return (
                "Log the county feedback, confirm one live mental-health indicator "
                "pack, and decide whether the next validation should expand to a "
                "second county or a second indicator domain."
            )
        return (
            "Log the county feedback, confirm live indicator naming, and choose one "
            "additional county for the next validation pass."
        )

    if data_mode == "dhis2_demo":
        return (
            "Swap the demo credentials for a read-only KHIS account and confirm the "
            "county organisation-unit mapping before broadening the pilot."
        )

    if data_mode == "offline_demo":
        return (
            "Keep the public deployment in offline demo mode, then run one read-only "
            "KHIS validation for this county and compare the live pull against the "
            "current review process."
        )

    return (
        "Pin the public deployment to offline demo mode, collect one county review, "
        "and only then widen the pilot scope."
    )


def _recommended_reviewer(data_mode: str) -> str:
    """Choose the smallest useful reviewer set for the first pilot pass."""
    if data_mode == "khis_live":
        return (
            "County reviewer plus the KHIS focal person who owns the live indicator "
            "definition."
        )
    return "County Health Records Officer plus one KHIS reviewer."


def _mode_label(data_mode: str) -> str:
    """Convert the runtime data mode into a reader-friendly label."""
    labels = {
        "offline_demo": "Offline demo",
        "dhis2_demo": "DHIS2 demo",
        "khis_live": "KHIS live",
        "auto": "Auto mode",
    }
    return labels.get(str(data_mode).strip(), "Unknown mode")


def _score_label(value: Any) -> str | None:
    """Format a quality score for display when it is available."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    """Return a stripped string unless the value is missing-like."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    return text


def _bool_or_none(value: Any) -> bool | None:
    """Coerce a value to bool while preserving missing values."""
    if value is None:
        return None
    return bool(value)


def _int_or_none(value: Any) -> int | None:
    """Coerce a numeric value to int when available."""
    try:
        if value is None:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


__all__ = ["build_pilot_feedback_payload"]
