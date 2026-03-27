"""County lookup scaffolding for Kenya-specific KHIS analysis helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

KENYA_COUNTIES: dict[str, dict[str, Any]] = {}


def get_county(name_or_id: str) -> dict[str, Any]:
    """Return a county record once the county reference table is implemented."""
    raise NotImplementedError("Implement khis.counties.get_county in Phase 1.")


def get_counties_by_region(region: str) -> list[dict[str, Any]]:
    """Return county records grouped by region once implemented."""
    raise NotImplementedError("Implement khis.counties.get_counties_by_region in Phase 1.")


def list_counties() -> pd.DataFrame:
    """Return the county table as a DataFrame once implemented."""
    return pd.DataFrame(columns=["dhis2_id", "name", "code", "region", "latitude", "longitude"])


def resolve_org_unit_id(name: str) -> str:
    """Resolve a county name to a DHIS2 organisation unit ID."""
    raise NotImplementedError("Implement khis.counties.resolve_org_unit_id in Phase 1.")


def get_county_coordinates() -> pd.DataFrame:
    """Return county coordinates for mapping once implemented."""
    return pd.DataFrame(columns=["county", "latitude", "longitude"])


def update_from_api(connector) -> dict[str, dict[str, Any]]:
    """Refresh placeholder county IDs from a live DHIS2 connector in a future phase."""
    raise NotImplementedError("Implement khis.counties.update_from_api in Phase 1.")
