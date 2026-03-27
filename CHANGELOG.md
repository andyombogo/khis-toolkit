# Changelog

## 0.1.0 - 2026-03-27

- Added a DHIS2/KHIS connector with environment-based auth, demo fallback, indicator discovery, org-unit lookup, and analytics pagination.
- Added a full Kenya county resolver covering all 47 counties, regional groupings, coordinates, and placeholder-to-live DHIS2 ID updates.
- Added KHIS data cleaning utilities for period parsing, duplicate removal, numeric coercion, missing-data flags, bounded imputation, and county-name standardisation.
- Added county data quality tooling with completeness scoring, outlier detection, timeliness analysis, suspicious-zero checks, scorecards, and heatmaps.
- Added Prophet, XGBoost, and ensemble forecasting with anomaly detection and forecasting notebooks.
- Added a Flask dashboard with county map helpers, trend charts, scorecard rendering, and demo/live data fallbacks.
- Added a FastAPI service layer for counties, indicators, cleaned data pulls, forecasts, and quality responses.
- Added packaging, CI, Render deployment configuration, notebooks, docs, and release-preparation assets.
