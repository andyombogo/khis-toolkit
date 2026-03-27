"""Core DHIS2 connector scaffolding for the KHIS analytics toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class DHIS2Connector:
    """Lightweight placeholder for the future DHIS2 API connector."""

    base_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    def ping(self) -> tuple[bool, str]:
        """Return a placeholder connection status until Phase 1 is implemented."""
        return False, "Connector scaffold ready. Implement Phase 1 to enable API calls."

    def get_analytics(
        self,
        indicator_ids: Iterable[str],
        org_unit_ids: Iterable[str],
        periods: Iterable[str],
        output_format: str = "dataframe",
    ):
        """Placeholder analytics method for the DHIS2 connector."""
        raise NotImplementedError("Implement khis.connector.DHIS2Connector.get_analytics in Phase 1.")

    def get_indicators(self, search_term: Optional[str] = None):
        """Placeholder indicator discovery method."""
        raise NotImplementedError("Implement khis.connector.DHIS2Connector.get_indicators in Phase 1.")

    def get_org_units(self, level: Optional[int] = None, parent_id: Optional[str] = None):
        """Placeholder organisation unit discovery method."""
        raise NotImplementedError("Implement khis.connector.DHIS2Connector.get_org_units in Phase 1.")


def get(
    indicator_ids,
    org_unit_ids=None,
    periods=None,
    output_format: str = "dataframe",
):
    """Convenience wrapper placeholder for quick analytics access."""
    connector = DHIS2Connector()
    return connector.get_analytics(
        indicator_ids=indicator_ids,
        org_unit_ids=org_unit_ids or [],
        periods=periods or [],
        output_format=output_format,
    )
