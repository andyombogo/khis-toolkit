"""Tests for the high-level khis package API wrappers."""

from __future__ import annotations

import pandas as pd

import khis


def test_get_resolves_indicator_search_terms_before_fetching():
    """The public `khis.get()` helper should accept human-readable indicator terms."""

    class StubConnector:
        def get_indicators(self, search_term=None):
            return pd.DataFrame(
                [
                    {
                        "id": "IND_MALARIA",
                        "name": "Malaria Cases",
                        "short_name": "Malaria",
                        "code": "MALARIA_CASES",
                        "description": "Demo indicator",
                    }
                ]
            )

        def resolve_org_unit_id_by_name(self, name):
            return "OU_NAIROBI"

        def get_analytics(self, indicator_ids, org_unit_ids, periods, output_format="dataframe"):
            return {
                "indicator_ids": indicator_ids,
                "org_unit_ids": org_unit_ids,
                "periods": periods,
                "output_format": output_format,
            }

    result = khis.get(
        conn=StubConnector(),
        indicator="malaria",
        counties=["Nairobi"],
        periods="last_12_months",
        output_format="json",
    )

    assert result["indicator_ids"] == ["IND_MALARIA"]
    assert result["org_unit_ids"] == ["OU_NAIROBI"]
