# KHIS Toolkit API Draft

## Planned Public Package Surface

- `khis.DHIS2Connector`
- `khis.get(...)`
- `khis.get_county(...)`
- `khis.get_counties_by_region(...)`
- `khis.list_counties()`
- `khis.resolve_org_unit_id(...)`
- `khis.clean_indicator_frame(...)`
- `khis.compute_quality_summary(...)`
- `khis.forecast_indicator_series(...)`

## Notes

- The connector and county APIs are scaffolded now and will be implemented in Phase 1.
- The cleaner, quality, and forecasting functions currently provide placeholders or smoke-testable helpers only.
