"""Smoke tests for the KHIS connector scaffold."""

from khis.connector import DHIS2Connector


def test_connector_scaffold_ping_returns_placeholder_status():
    """The connector scaffold should expose a safe placeholder ping method."""
    status, message = DHIS2Connector().ping()
    assert status is False
    assert "scaffold" in message.lower()
