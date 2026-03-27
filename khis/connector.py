"""DHIS2/KHIS API connector utilities.

This module provides a reusable connector for DHIS2-compatible analytics APIs,
including the Kenya Health Information System (KHIS). It handles environment-
based credentials, a public demo-server fallback, pagination, respectful
rate-limiting, and DataFrame-friendly output parsing.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterable

import pandas as pd
import requests
from dotenv import load_dotenv

DEMO_BASE_URL = "https://play.dhis2.org/demo"
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "district"
REQUEST_DELAY_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 30
NO_CREDENTIALS_WARNING = (
    "No credentials found. Using DHIS2 public demo server. "
    "Data is for testing only — not real Kenya health data."
)
PERIOD_SHORTCUTS = {
    "last_12_months": "LAST_12_MONTHS",
    "last_6_months": "LAST_6_MONTHS",
    "last_3_months": "LAST_3_MONTHS",
    "this_year": "THIS_YEAR",
    "last_year": "LAST_YEAR",
    "last_12_weeks": "LAST_12_WEEKS",
}


class DHIS2Connector:
    """Client for DHIS2 analytics, metadata, and organisation unit endpoints.

    Parameters
    ----------
    base_url:
        Base DHIS2 server URL, with or without the trailing ``/api`` segment.
        If omitted, the connector attempts to load ``DHIS2_BASE_URL`` from the
        environment.
    username:
        DHIS2 username. If omitted, ``DHIS2_USERNAME`` is loaded from the
        environment.
    password:
        DHIS2 password. If omitted, ``DHIS2_PASSWORD`` is loaded from the
        environment.

    Notes
    -----
    If no credentials are available, the connector falls back to the public
    DHIS2 demo server and prints a warning so the caller knows the data is only
    suitable for testing workflows, not Kenya production analysis.
    """

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        load_dotenv()

        env_base_url = os.getenv("DHIS2_BASE_URL", "").strip()
        env_username = os.getenv("DHIS2_USERNAME", "").strip()
        env_password = os.getenv("DHIS2_PASSWORD", "").strip()

        resolved_base_url = (base_url or env_base_url).strip()
        resolved_username = (username or env_username).strip()
        resolved_password = (password or env_password).strip()

        if not resolved_username or not resolved_password:
            print(NO_CREDENTIALS_WARNING)
            resolved_base_url = DEMO_BASE_URL
            resolved_username = DEMO_USERNAME
            resolved_password = DEMO_PASSWORD
            self.using_demo_server = True
        else:
            resolved_base_url = resolved_base_url or DEMO_BASE_URL
            self.using_demo_server = False

        self.base_url = resolved_base_url.rstrip("/")
        self.api_base_url = (
            self.base_url if self.base_url.endswith("/api") else f"{self.base_url}/api"
        )
        self.username = resolved_username
        self.password = resolved_password
        self.request_delay_seconds = REQUEST_DELAY_SECONDS
        self.request_timeout_seconds = REQUEST_TIMEOUT_SECONDS
        self._last_request_finished_at: float | None = None

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({"Accept": "application/json"})

    def ping(self) -> tuple[bool, str]:
        """Check whether the configured DHIS2 server is reachable and authenticated.

        Returns
        -------
        tuple[bool, str]
            A success flag plus a human-readable status message. This method does
            not raise on connection or authentication errors because it is
            intended as a quick health check for dashboards and notebooks.
        """
        try:
            payload = self._request_json("/me")
        except (ConnectionError, PermissionError, RuntimeError) as exc:
            return False, str(exc)

        user_name = payload.get("displayName") or payload.get("username") or self.username
        return True, f"Connected to DHIS2 server at {self.base_url} as {user_name}."

    def get_analytics(
        self,
        indicator_ids: Iterable[str] | str,
        org_unit_ids: Iterable[str] | str,
        periods: Iterable[str] | str,
        output_format: str = "dataframe",
    ) -> pd.DataFrame | dict[str, Any]:
        """Fetch analytics data from the DHIS2 ``/api/analytics`` endpoint.

        Parameters
        ----------
        indicator_ids:
            One indicator/data-element dimension ID or an iterable of IDs.
        org_unit_ids:
            One organisation unit ID or an iterable of IDs.
        periods:
            One period ID or an iterable of period IDs. Relative period aliases
            such as ``last_12_months`` are also supported.
        output_format:
            ``"dataframe"`` returns a tidy pandas DataFrame. ``"json"`` returns
            the combined analytics payload.

        Returns
        -------
        pandas.DataFrame | dict[str, Any]
            A clean analytics table with columns ``indicator_id``,
            ``indicator_name``, ``org_unit_id``, ``org_unit_name``, ``period``,
            and ``value``, or the raw combined JSON payload.

        Raises
        ------
        ValueError
            If required dimensions are missing or the output format is invalid.
        ConnectionError
            If the server is unreachable.
        PermissionError
            If authentication fails.
        RuntimeError
            If the DHIS2 API returns another HTTP or parsing error.
        """
        indicator_values = self._normalise_dimension_values(indicator_ids, "indicator_ids")
        org_unit_values = self._normalise_dimension_values(org_unit_ids, "org_unit_ids")
        period_values = self._normalise_periods(periods)

        params: dict[str, Any] = {
            "dimension": [
                f"dx:{';'.join(indicator_values)}",
                f"ou:{';'.join(org_unit_values)}",
                f"pe:{';'.join(period_values)}",
            ],
            "displayProperty": "NAME",
            "paging": "true",
            "pageSize": 1000,
        }

        pages = self._get_paginated_payloads("/analytics", params)
        combined_payload = self._combine_analytics_payloads(pages)

        if output_format == "json":
            return combined_payload
        if output_format != "dataframe":
            raise ValueError("output_format must be either 'dataframe' or 'json'.")

        return self._analytics_payload_to_dataframe(combined_payload)

    def get_indicators(self, search_term: str | None = None) -> pd.DataFrame:
        """Return indicator metadata available to the authenticated user.

        Parameters
        ----------
        search_term:
            Optional case-insensitive text filter applied to indicator display
            names on the DHIS2 side.

        Returns
        -------
        pandas.DataFrame
            Indicator metadata with columns ``id``, ``name``, ``short_name``,
            ``code``, and ``description``.
        """
        params: dict[str, Any] = {
            "fields": "id,displayName,shortName,code,description",
            "paging": "true",
            "pageSize": 250,
        }
        if search_term:
            params["filter"] = f"displayName:ilike:{search_term}"

        indicator_rows = self._get_paginated_collection("/indicators", params, "indicators")
        records = [
            {
                "id": row.get("id"),
                "name": row.get("displayName"),
                "short_name": row.get("shortName"),
                "code": row.get("code"),
                "description": row.get("description"),
            }
            for row in indicator_rows
        ]
        return pd.DataFrame(records, columns=["id", "name", "short_name", "code", "description"])

    def get_org_units(
        self,
        level: int | None = None,
        parent_id: str | None = None,
    ) -> pd.DataFrame:
        """Return organisation unit metadata from the DHIS2 API.

        Parameters
        ----------
        level:
            Optional organisation unit hierarchy level filter.
        parent_id:
            Optional parent organisation unit ID filter.

        Returns
        -------
        pandas.DataFrame
            Organisation units with columns ``id``, ``name``, ``level``,
            ``parent_id``, ``parent_name``, and ``path``.
        """
        params: dict[str, Any] = {
            "fields": "id,displayName,level,path,parent[id,displayName]",
            "paging": "true",
            "pageSize": 250,
        }
        filters: list[str] = []
        if level is not None:
            filters.append(f"level:eq:{level}")
        if parent_id:
            filters.append(f"parent.id:eq:{parent_id}")
        if filters:
            params["filter"] = filters

        org_unit_rows = self._get_paginated_collection(
            "/organisationUnits",
            params,
            "organisationUnits",
        )
        records = [
            {
                "id": row.get("id"),
                "name": row.get("displayName"),
                "level": row.get("level"),
                "parent_id": (row.get("parent") or {}).get("id"),
                "parent_name": (row.get("parent") or {}).get("displayName"),
                "path": row.get("path"),
            }
            for row in org_unit_rows
        ]
        return pd.DataFrame(
            records,
            columns=["id", "name", "level", "parent_id", "parent_name", "path"],
        )

    def resolve_org_unit_id_by_name(self, name: str) -> str:
        """Resolve a human-readable organisation unit name to a DHIS2 ID.

        This helper is primarily used by the module-level ``get()`` convenience
        function so callers can pass county names directly before the dedicated
        county resolver module is implemented.
        """
        if not name or not name.strip():
            raise ValueError("Organisation unit name cannot be empty.")

        params = {
            "fields": "id,displayName,level",
            "paging": "true",
            "pageSize": 50,
            "filter": f"displayName:ilike:{name.strip()}",
        }
        matches = self._get_paginated_collection(
            "/organisationUnits",
            params,
            "organisationUnits",
        )
        if not matches:
            raise ValueError(f"No organisation unit matched '{name}'.")

        exact_matches = [
            row for row in matches if str(row.get("displayName", "")).lower() == name.strip().lower()
        ]
        best_match = exact_matches[0] if exact_matches else matches[0]
        return str(best_match["id"])

    def _get_paginated_collection(
        self,
        path: str,
        params: dict[str, Any],
        collection_key: str,
    ) -> list[dict[str, Any]]:
        """Fetch and combine paginated collection responses from a DHIS2 endpoint."""
        payloads = self._get_paginated_payloads(path, params)
        combined_rows: list[dict[str, Any]] = []
        for payload in payloads:
            combined_rows.extend(payload.get(collection_key, []))
        return combined_rows

    def _get_paginated_payloads(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch all pages for a DHIS2 endpoint that returns a ``pager`` object."""
        payloads: list[dict[str, Any]] = []
        page = 1

        while True:
            page_params = dict(params)
            page_params["page"] = page
            payload = self._request_json(path, page_params)
            payloads.append(payload)

            pager = payload.get("pager") or {}
            page_count = int(pager.get("pageCount", page))
            current_page = int(pager.get("page", page))
            if current_page >= page_count:
                break
            page += 1

        return payloads

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a GET request and return a JSON payload with clear errors."""
        self._respect_rate_limit()
        url = self._build_url(path)

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.request_timeout_seconds,
            )
        except requests.exceptions.RequestException as exc:
            self._last_request_finished_at = time.monotonic()
            raise ConnectionError(
                f"Could not reach DHIS2 server at {self.base_url}: {exc}"
            ) from exc

        self._last_request_finished_at = time.monotonic()

        if response.status_code == 401:
            raise PermissionError(
                "Authentication failed for the DHIS2 API. Check your username and password."
            )
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason or "Unknown error"
            raise RuntimeError(
                f"DHIS2 API request failed with status {response.status_code}: {detail}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"DHIS2 API returned a non-JSON response from {url}."
            ) from exc

    def _respect_rate_limit(self) -> None:
        """Pause between DHIS2 API requests to avoid hammering the server."""
        if self._last_request_finished_at is None:
            return

        elapsed = time.monotonic() - self._last_request_finished_at
        if elapsed < self.request_delay_seconds:
            time.sleep(self.request_delay_seconds - elapsed)

    def _build_url(self, path: str) -> str:
        """Construct a full API URL from a relative path."""
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{self.api_base_url}{clean_path}"

    def _combine_analytics_payloads(self, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge paginated analytics payloads into a single response object."""
        if not payloads:
            return {"headers": [], "rows": [], "metaData": {"items": {}}}

        first_payload = payloads[0]
        merged_rows: list[list[Any]] = []
        merged_items: dict[str, Any] = {}
        pager = first_payload.get("pager") or {}

        for payload in payloads:
            merged_rows.extend(payload.get("rows", []))
            merged_items.update((payload.get("metaData") or {}).get("items", {}))
            pager = payload.get("pager") or pager

        return {
            **first_payload,
            "rows": merged_rows,
            "metaData": {
                **(first_payload.get("metaData") or {}),
                "items": merged_items,
            },
            "pager": pager,
        }

    def _analytics_payload_to_dataframe(self, payload: dict[str, Any]) -> pd.DataFrame:
        """Convert a DHIS2 analytics payload to a tidy pandas DataFrame."""
        headers = payload.get("headers", [])
        rows = payload.get("rows", [])
        meta_items = (payload.get("metaData") or {}).get("items", {})
        header_names = [str(header.get("name", "")).lower() for header in headers]

        records: list[dict[str, Any]] = []
        for row in rows:
            row_map = dict(zip(header_names, row))
            indicator_id = row_map.get("dx")
            org_unit_id = row_map.get("ou")
            period = row_map.get("pe")
            value = row_map.get("value")

            records.append(
                {
                    "indicator_id": indicator_id,
                    "indicator_name": self._metadata_name(meta_items, indicator_id),
                    "org_unit_id": org_unit_id,
                    "org_unit_name": self._metadata_name(meta_items, org_unit_id),
                    "period": period,
                    "value": pd.to_numeric(value, errors="coerce"),
                }
            )

        return pd.DataFrame(
            records,
            columns=[
                "indicator_id",
                "indicator_name",
                "org_unit_id",
                "org_unit_name",
                "period",
                "value",
            ],
        )

    def _metadata_name(self, metadata_items: dict[str, Any], item_id: Any) -> str | None:
        """Look up a display name from the DHIS2 metadata map."""
        if item_id is None:
            return None

        item = metadata_items.get(str(item_id))
        if isinstance(item, dict):
            return item.get("name") or item.get("displayName")
        return str(item) if item is not None else None

    def _normalise_dimension_values(
        self,
        values: Iterable[str] | str,
        field_name: str,
    ) -> list[str]:
        """Normalise one or many dimension IDs into a non-empty string list."""
        normalised_values = _coerce_to_string_list(values)
        if not normalised_values:
            raise ValueError(f"{field_name} must contain at least one value.")
        return normalised_values

    def _normalise_periods(self, periods: Iterable[str] | str) -> list[str]:
        """Normalise period IDs and friendly shortcuts into DHIS2 period values."""
        normalised_periods = _coerce_to_string_list(periods)
        if not normalised_periods:
            raise ValueError("periods must contain at least one value.")

        return [
            PERIOD_SHORTCUTS.get(period.lower(), period)
            for period in normalised_periods
        ]


def get(
    indicator_ids: Iterable[str] | str,
    county: Iterable[str] | str | None = None,
    org_unit_ids: Iterable[str] | str | None = None,
    periods: Iterable[str] | str = "last_12_months",
    output_format: str = "dataframe",
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> pd.DataFrame | dict[str, Any]:
    """Fetch analytics quickly without manually instantiating a connector.

    Parameters
    ----------
    indicator_ids:
        One or more indicator IDs.
    county:
        Optional county or organisation-unit name. The connector resolves names
        via the DHIS2 organisation unit API.
    org_unit_ids:
        Optional organisation unit IDs. If both ``county`` and ``org_unit_ids``
        are supplied, they are combined.
    periods:
        One or more period IDs or friendly shortcuts such as
        ``"last_12_months"``.
    output_format:
        Either ``"dataframe"`` or ``"json"``.
    base_url, username, password:
        Optional explicit connection overrides. If omitted, environment
        variables are used before the demo-server fallback.
    """
    connector = DHIS2Connector(base_url=base_url, username=username, password=password)
    resolved_org_units = _coerce_to_string_list(org_unit_ids)

    for county_name in _coerce_to_string_list(county):
        resolved_org_units.append(connector.resolve_org_unit_id_by_name(county_name))

    if not resolved_org_units:
        raise ValueError("Provide either org_unit_ids or county when calling khis.get().")

    return connector.get_analytics(
        indicator_ids=indicator_ids,
        org_unit_ids=resolved_org_units,
        periods=periods,
        output_format=output_format,
    )


def _coerce_to_string_list(values: Iterable[str] | str | None) -> list[str]:
    """Convert a string or iterable of strings into a clean list of strings."""
    if values is None:
        return []
    if isinstance(values, str):
        raw_parts = values.split(",")
    else:
        raw_parts = list(values)

    return [str(part).strip() for part in raw_parts if str(part).strip()]
