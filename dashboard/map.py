"""Mapping helpers for county-level KHIS dashboard views."""

from __future__ import annotations

from typing import Any


def build_county_map(*args, **kwargs) -> dict[str, Any]:
    """Return a placeholder map payload until county visualisation is implemented."""
    return {"status": "not-implemented", "message": "County map support starts in a later phase."}
