"""Tests for the KHIS DHIS2 connector."""

from __future__ import annotations

from unittest.mock import Mock

import pandas as pd

from khis.connector import DEMO_BASE_URL, DHIS2Connector


def test_connector_falls_back_to_demo_server_when_credentials_missing(
    monkeypatch, capsys
):
    """Missing credentials should trigger the documented demo-server fallback."""
    monkeypatch.delenv("DHIS2_BASE_URL", raising=False)
    monkeypatch.delenv("DHIS2_USERNAME", raising=False)
    monkeypatch.delenv("DHIS2_PASSWORD", raising=False)

    connector = DHIS2Connector()
    captured = capsys.readouterr()

    assert connector.base_url == DEMO_BASE_URL
    assert connector.using_demo_server is True
    assert "public demo server" in captured.out.lower()


def test_get_analytics_returns_expected_dataframe_columns(monkeypatch):
    """Analytics responses should be reshaped into the public tidy schema."""
    connector = DHIS2Connector(
        base_url="https://example.org", username="user", password="pass"
    )

    sample_payload = {
        "headers": [
            {"name": "dx"},
            {"name": "ou"},
            {"name": "pe"},
            {"name": "value"},
        ],
        "rows": [["IND_001", "OU_001", "202401", "17"]],
        "metaData": {
            "items": {
                "IND_001": {"name": "Malaria Cases"},
                "OU_001": {"name": "Nairobi County"},
            }
        },
        "pager": {"page": 1, "pageCount": 1},
    }

    monkeypatch.setattr(
        connector,
        "_get_paginated_payloads",
        lambda path, params: [sample_payload],
    )

    result = connector.get_analytics("IND_001", "OU_001", "202401")

    assert isinstance(result, pd.DataFrame)
    assert result.columns.tolist() == [
        "indicator_id",
        "indicator_name",
        "org_unit_id",
        "org_unit_name",
        "period",
        "value",
    ]
    assert result.loc[0, "indicator_name"] == "Malaria Cases"
    assert result.loc[0, "org_unit_name"] == "Nairobi County"


def test_ping_returns_false_when_server_is_unreachable(monkeypatch):
    """Connection failures should be reported as a false ping result."""
    connector = DHIS2Connector(
        base_url="https://example.org", username="user", password="pass"
    )

    def raise_connection_error(path, params=None):
        raise ConnectionError(
            "Could not reach DHIS2 server at https://example.org: boom"
        )

    monkeypatch.setattr(connector, "_request_json", raise_connection_error)

    status, message = connector.ping()

    assert status is False
    assert "could not reach dhis2 server" in message.lower()


def test_request_json_raises_clear_authentication_error(monkeypatch):
    """HTTP 401 responses should map to a clear authentication exception."""
    connector = DHIS2Connector(
        base_url="https://example.org", username="user", password="pass"
    )
    response = Mock(status_code=401, text="Unauthorized", reason="Unauthorized")
    monkeypatch.setattr(connector.session, "get", lambda *args, **kwargs: response)

    try:
        connector._request_json("/me")
    except PermissionError as exc:
        assert "authentication failed" in str(exc).lower()
    else:
        raise AssertionError("Expected PermissionError for HTTP 401.")


def test_rate_limiting_sleeps_between_requests(monkeypatch):
    """A second request issued too quickly should pause to respect the rate limit."""
    connector = DHIS2Connector(
        base_url="https://example.org", username="user", password="pass"
    )
    response = Mock(status_code=200, text="{}", reason="OK")
    response.json.return_value = {"me": "ok"}
    monkeypatch.setattr(connector.session, "get", lambda *args, **kwargs: response)

    sleep_calls: list[float] = []
    monotonic_values = iter([10.0, 10.2, 10.2])

    monkeypatch.setattr(
        "khis.connector.time.sleep", lambda seconds: sleep_calls.append(seconds)
    )
    monkeypatch.setattr("khis.connector.time.monotonic", lambda: next(monotonic_values))

    connector._request_json("/me")
    connector._request_json("/me")

    assert sleep_calls
    assert abs(sleep_calls[0] - 0.3) < 1e-9
