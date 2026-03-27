"""Tests for Kenya county lookup helpers."""

from __future__ import annotations

import pandas as pd

from khis.counties import (
    KENYA_COUNTIES,
    get_counties_by_region,
    get_county,
    list_counties,
    update_from_api,
)


def test_list_counties_contains_all_47_kenya_counties():
    """The county reference table should expose one row per Kenya county."""
    counties_df = list_counties()
    assert isinstance(counties_df, pd.DataFrame)
    assert len(counties_df) == 47
    assert counties_df["code"].is_unique


def test_get_county_resolves_case_insensitive_name_and_placeholder_id():
    """County lookup should work with both names and DHIS2 IDs."""
    assert get_county("nairobi")["dhis2_id"] == "KE47"
    assert get_county("KE21")["name"] == "Murang'a"


def test_get_counties_by_region_returns_expected_subset():
    """Regional lookup should return county records for the requested region."""
    rift_valley_counties = get_counties_by_region("Rift Valley")
    county_names = {county["name"] for county in rift_valley_counties}

    assert "Nakuru" in county_names
    assert "Turkana" in county_names
    assert "Nairobi" not in county_names


def test_update_from_api_replaces_placeholder_ids_with_live_matches():
    """Live org unit lookups should overwrite matching placeholder county IDs."""

    class StubConnector:
        def get_org_units(self):
            return pd.DataFrame(
                [
                    {"id": "LIVE_NRB", "name": "Nairobi City County", "level": 2},
                    {"id": "LIVE_MSA", "name": "Mombasa County", "level": 2},
                ]
            )

    original_nairobi_id = KENYA_COUNTIES["Nairobi"]["dhis2_id"]
    original_mombasa_id = KENYA_COUNTIES["Mombasa"]["dhis2_id"]

    try:
        updated = update_from_api(StubConnector())
        assert updated["Nairobi"]["dhis2_id"] == "LIVE_NRB"
        assert updated["Mombasa"]["dhis2_id"] == "LIVE_MSA"
    finally:
        KENYA_COUNTIES["Nairobi"]["dhis2_id"] = original_nairobi_id
        KENYA_COUNTIES["Mombasa"]["dhis2_id"] = original_mombasa_id
