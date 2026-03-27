"""Kenya county lookup and organisation-unit resolution helpers.

County DHIS2 IDs are placeholders. Once you have KHIS credentials, run
``khis.counties.update_from_api()`` to replace them with real IDs from
``hiskenya.org``.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

_COUNTY_ROWS: list[dict[str, Any]] = [
    {
        "dhis2_id": "KE01",
        "name": "Mombasa",
        "code": 1,
        "capital": "Mombasa City",
        "region": "Coast",
        "latitude": -4.039015,
        "longitude": 39.648424,
    },
    {
        "dhis2_id": "KE02",
        "name": "Kwale",
        "code": 2,
        "capital": "Kwale",
        "region": "Coast",
        "latitude": -4.183607,
        "longitude": 39.105095,
    },
    {
        "dhis2_id": "KE03",
        "name": "Kilifi",
        "code": 3,
        "capital": "Kilifi",
        "region": "Coast",
        "latitude": -3.150739,
        "longitude": 39.675072,
    },
    {
        "dhis2_id": "KE04",
        "name": "Tana River",
        "code": 4,
        "capital": "Hola",
        "region": "Coast",
        "latitude": -1.536512,
        "longitude": 39.550837,
    },
    {
        "dhis2_id": "KE05",
        "name": "Lamu",
        "code": 5,
        "capital": "Lamu",
        "region": "Coast",
        "latitude": -2.064521,
        "longitude": 40.728099,
    },
    {
        "dhis2_id": "KE06",
        "name": "Taita-Taveta",
        "code": 6,
        "capital": "Voi",
        "region": "Coast",
        "latitude": -3.417835,
        "longitude": 38.367068,
    },
    {
        "dhis2_id": "KE07",
        "name": "Garissa",
        "code": 7,
        "capital": "Garissa",
        "region": "North Eastern",
        "latitude": -0.523603,
        "longitude": 40.356387,
    },
    {
        "dhis2_id": "KE08",
        "name": "Wajir",
        "code": 8,
        "capital": "Wajir",
        "region": "North Eastern",
        "latitude": 1.93944,
        "longitude": 40.024494,
    },
    {
        "dhis2_id": "KE09",
        "name": "Mandera",
        "code": 9,
        "capital": "Mandera",
        "region": "North Eastern",
        "latitude": 3.228533,
        "longitude": 40.705616,
    },
    {
        "dhis2_id": "KE10",
        "name": "Marsabit",
        "code": 10,
        "capital": "Marsabit",
        "region": "Eastern",
        "latitude": 2.857958,
        "longitude": 37.715489,
    },
    {
        "dhis2_id": "KE11",
        "name": "Isiolo",
        "code": 11,
        "capital": "Isiolo",
        "region": "Eastern",
        "latitude": 1.00606,
        "longitude": 38.747895,
    },
    {
        "dhis2_id": "KE12",
        "name": "Meru",
        "code": 12,
        "capital": "Meru",
        "region": "Eastern",
        "latitude": 0.225451,
        "longitude": 37.777262,
    },
    {
        "dhis2_id": "KE13",
        "name": "Tharaka-Nithi",
        "code": 13,
        "capital": "Chuka",
        "region": "Eastern",
        "latitude": -0.193708,
        "longitude": 37.961405,
    },
    {
        "dhis2_id": "KE14",
        "name": "Embu",
        "code": 14,
        "capital": "Embu",
        "region": "Eastern",
        "latitude": -0.535948,
        "longitude": 37.665288,
    },
    {
        "dhis2_id": "KE15",
        "name": "Kitui",
        "code": 15,
        "capital": "Kitui",
        "region": "Eastern",
        "latitude": -1.564222,
        "longitude": 38.372812,
    },
    {
        "dhis2_id": "KE16",
        "name": "Machakos",
        "code": 16,
        "capital": "Machakos",
        "region": "Eastern",
        "latitude": -1.279005,
        "longitude": 37.39527,
    },
    {
        "dhis2_id": "KE17",
        "name": "Makueni",
        "code": 17,
        "capital": "Wote",
        "region": "Eastern",
        "latitude": -2.257093,
        "longitude": 37.877171,
    },
    {
        "dhis2_id": "KE18",
        "name": "Nyandarua",
        "code": 18,
        "capital": "Ol Kalou",
        "region": "Central",
        "latitude": -0.391553,
        "longitude": 36.497768,
    },
    {
        "dhis2_id": "KE19",
        "name": "Nyeri",
        "code": 19,
        "capital": "Nyeri",
        "region": "Central",
        "latitude": -0.32121,
        "longitude": 36.929562,
    },
    {
        "dhis2_id": "KE20",
        "name": "Kirinyaga",
        "code": 20,
        "capital": "Kerugoya/Kutus",
        "region": "Central",
        "latitude": -0.468878,
        "longitude": 37.302768,
    },
    {
        "dhis2_id": "KE21",
        "name": "Murang'a",
        "code": 21,
        "capital": "Murang'a",
        "region": "Central",
        "latitude": -0.830915,
        "longitude": 37.004861,
    },
    {
        "dhis2_id": "KE22",
        "name": "Kiambu",
        "code": 22,
        "capital": "Kiambu",
        "region": "Central",
        "latitude": -1.032077,
        "longitude": 36.815687,
    },
    {
        "dhis2_id": "KE23",
        "name": "Turkana",
        "code": 23,
        "capital": "Lodwar",
        "region": "Rift Valley",
        "latitude": 2.765566,
        "longitude": 35.597723,
    },
    {
        "dhis2_id": "KE24",
        "name": "West Pokot",
        "code": 24,
        "capital": "Kapenguria",
        "region": "Rift Valley",
        "latitude": 1.879861,
        "longitude": 35.210613,
    },
    {
        "dhis2_id": "KE25",
        "name": "Samburu",
        "code": 25,
        "capital": "Maralal",
        "region": "Rift Valley",
        "latitude": 1.539446,
        "longitude": 36.942166,
    },
    {
        "dhis2_id": "KE26",
        "name": "Trans-Nzoia",
        "code": 26,
        "capital": "Kitale",
        "region": "Rift Valley",
        "latitude": 1.045458,
        "longitude": 34.979044,
    },
    {
        "dhis2_id": "KE27",
        "name": "Uasin Gishu",
        "code": 27,
        "capital": "Eldoret",
        "region": "Rift Valley",
        "latitude": 0.477194,
        "longitude": 35.30506,
    },
    {
        "dhis2_id": "KE28",
        "name": "Elgeyo-Marakwet",
        "code": 28,
        "capital": "Iten",
        "region": "Rift Valley",
        "latitude": 0.742219,
        "longitude": 35.561808,
    },
    {
        "dhis2_id": "KE29",
        "name": "Nandi",
        "code": 29,
        "capital": "Kapsabet",
        "region": "Rift Valley",
        "latitude": 0.225393,
        "longitude": 35.124493,
    },
    {
        "dhis2_id": "KE30",
        "name": "Baringo",
        "code": 30,
        "capital": "Kabarnet",
        "region": "Rift Valley",
        "latitude": 0.72444,
        "longitude": 36.020142,
    },
    {
        "dhis2_id": "KE31",
        "name": "Laikipia",
        "code": 31,
        "capital": "Rumuruti",
        "region": "Rift Valley",
        "latitude": 0.285845,
        "longitude": 36.825771,
    },
    {
        "dhis2_id": "KE32",
        "name": "Nakuru",
        "code": 32,
        "capital": "Nakuru",
        "region": "Rift Valley",
        "latitude": -0.459821,
        "longitude": 36.100804,
    },
    {
        "dhis2_id": "KE33",
        "name": "Narok",
        "code": 33,
        "capital": "Narok",
        "region": "Rift Valley",
        "latitude": -1.277937,
        "longitude": 35.477423,
    },
    {
        "dhis2_id": "KE34",
        "name": "Kajiado",
        "code": 34,
        "capital": "Kajiado",
        "region": "Rift Valley",
        "latitude": -2.121717,
        "longitude": 36.786255,
    },
    {
        "dhis2_id": "KE35",
        "name": "Kericho",
        "code": 35,
        "capital": "Kericho",
        "region": "Rift Valley",
        "latitude": -0.320997,
        "longitude": 35.226128,
    },
    {
        "dhis2_id": "KE36",
        "name": "Bomet",
        "code": 36,
        "capital": "Bomet",
        "region": "Rift Valley",
        "latitude": -0.719605,
        "longitude": 35.239638,
    },
    {
        "dhis2_id": "KE37",
        "name": "Kakamega",
        "code": 37,
        "capital": "Kakamega",
        "region": "Western",
        "latitude": 0.49571,
        "longitude": 34.801549,
    },
    {
        "dhis2_id": "KE38",
        "name": "Vihiga",
        "code": 38,
        "capital": "Vihiga",
        "region": "Western",
        "latitude": 0.08312,
        "longitude": 34.708034,
    },
    {
        "dhis2_id": "KE39",
        "name": "Bungoma",
        "code": 39,
        "capital": "Bungoma",
        "region": "Western",
        "latitude": 0.782924,
        "longitude": 34.719168,
    },
    {
        "dhis2_id": "KE40",
        "name": "Busia",
        "code": 40,
        "capital": "Busia",
        "region": "Western",
        "latitude": 0.371205,
        "longitude": 34.264795,
    },
    {
        "dhis2_id": "KE41",
        "name": "Siaya",
        "code": 41,
        "capital": "Siaya",
        "region": "Nyanza",
        "latitude": -0.060401,
        "longitude": 34.200135,
    },
    {
        "dhis2_id": "KE42",
        "name": "Kisumu",
        "code": 42,
        "capital": "Kisumu",
        "region": "Nyanza",
        "latitude": -0.197126,
        "longitude": 34.777857,
    },
    {
        "dhis2_id": "KE43",
        "name": "Homa Bay",
        "code": 43,
        "capital": "Homa Bay",
        "region": "Nyanza",
        "latitude": -0.56396,
        "longitude": 34.318782,
    },
    {
        "dhis2_id": "KE44",
        "name": "Migori",
        "code": 44,
        "capital": "Migori",
        "region": "Nyanza",
        "latitude": -1.021162,
        "longitude": 34.309643,
    },
    {
        "dhis2_id": "KE45",
        "name": "Kisii",
        "code": 45,
        "capital": "Kisii",
        "region": "Nyanza",
        "latitude": -0.738943,
        "longitude": 34.753986,
    },
    {
        "dhis2_id": "KE46",
        "name": "Nyamira",
        "code": 46,
        "capital": "Nyamira",
        "region": "Nyanza",
        "latitude": -0.652254,
        "longitude": 34.934131,
    },
    {
        "dhis2_id": "KE47",
        "name": "Nairobi",
        "code": 47,
        "capital": "Nairobi City",
        "region": "Nairobi",
        "latitude": -1.303169,
        "longitude": 36.826068,
    },
]

KENYA_COUNTIES: dict[str, dict[str, Any]] = {
    row["name"]: row.copy() for row in _COUNTY_ROWS
}


def get_county(name_or_id: str) -> dict[str, Any]:
    """Return a county record by official name or DHIS2 ID."""
    if not name_or_id or not str(name_or_id).strip():
        raise ValueError("County name or ID cannot be empty.")

    search_value = str(name_or_id).strip()
    normalized = _normalise_county_name(search_value)

    for county in KENYA_COUNTIES.values():
        if county["dhis2_id"].lower() == search_value.lower():
            return county.copy()
        if _normalise_county_name(county["name"]) == normalized:
            return county.copy()

    raise ValueError(
        f"County '{name_or_id}' not found. Use list_counties() to inspect supported counties."
    )


def get_counties_by_region(region: str) -> list[dict[str, Any]]:
    """Return county records grouped by Kenya region."""
    if not region or not str(region).strip():
        raise ValueError("Region cannot be empty.")

    normalized_region = _normalise_region_name(region)
    matches = [
        county.copy()
        for county in sorted(KENYA_COUNTIES.values(), key=lambda item: item["code"])
        if _normalise_region_name(county["region"]) == normalized_region
    ]
    if not matches:
        raise ValueError(
            f"Region '{region}' not found. Valid regions are: {', '.join(_valid_regions())}."
        )
    return matches


def list_counties() -> pd.DataFrame:
    """Return the county table as a DataFrame."""
    return pd.DataFrame(
        sorted(KENYA_COUNTIES.values(), key=lambda item: item["code"])
    ).reset_index(drop=True)


def resolve_org_unit_id(name: str) -> str:
    """Return the DHIS2 organisation unit ID for a county name."""
    return str(get_county(name)["dhis2_id"])


def get_county_coordinates() -> pd.DataFrame:
    """Return county coordinates for mapping."""
    counties_df = list_counties()
    return counties_df.rename(columns={"name": "county"})[
        ["county", "latitude", "longitude"]
    ]


def update_from_api(connector: Any) -> dict[str, dict[str, Any]]:
    """Use a live connector to replace placeholder DHIS2 county IDs."""
    if not hasattr(connector, "get_org_units"):
        raise TypeError("connector must provide a get_org_units() method.")

    org_units = connector.get_org_units()
    if not isinstance(org_units, pd.DataFrame):
        raise TypeError("connector.get_org_units() must return a pandas DataFrame.")
    required_columns = {"id", "name"}
    if not required_columns.issubset(org_units.columns):
        missing = ", ".join(sorted(required_columns - set(org_units.columns)))
        raise ValueError(
            f"connector.get_org_units() is missing required columns: {missing}."
        )

    for county_name, county in KENYA_COUNTIES.items():
        county_norm = _normalise_county_name(county_name)
        matches = org_units[
            org_units["name"].astype(str).map(_normalise_county_name) == county_norm
        ].copy()
        if matches.empty:
            continue

        if "level" in matches.columns:
            matches["level"] = pd.to_numeric(matches["level"], errors="coerce")
            matches = matches.sort_values(by=["level", "name"], na_position="last")

        county["dhis2_id"] = str(matches.iloc[0]["id"])

    return {name: details.copy() for name, details in KENYA_COUNTIES.items()}


def _normalise_county_name(value: str) -> str:
    """Normalise county names for tolerant matching."""
    normalized = str(value).strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace("'", "")
    normalized = normalized.replace("’", "")
    normalized = normalized.replace(" county", " ")
    normalized = normalized.replace(" city", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalise_region_name(value: str) -> str:
    """Normalise region labels for case-insensitive lookup."""
    return re.sub(r"\s+", " ", str(value).strip().lower()).strip()


def _valid_regions() -> list[str]:
    """Return the sorted list of supported region labels."""
    return sorted({county["region"] for county in KENYA_COUNTIES.values()})
