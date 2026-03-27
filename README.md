# KHIS Toolkit

KHIS Toolkit is a Python analytics toolkit for Kenya DHIS2/KHIS health data. The project is designed to support county-level data extraction, cleaning, quality review, forecasting, and dashboard mapping workflows.

## Current Status

Phase 0 is complete in this scaffold:

- Python package structure created
- Flask dashboard scaffold added
- Packaging files added for `pip install -e .`
- CI workflow and smoke tests added
- Roadmap and API draft added

## Planned Modules

- `khis.connector`: DHIS2/KHIS API access
- `khis.counties`: Kenya county lookup and mapping metadata
- `khis.cleaner`: indicator cleaning helpers
- `khis.quality`: completeness and anomaly checks
- `khis.forecast`: county-level time-series forecasting

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pytest -q
```

## Dashboard Scaffold

The scaffolded Flask app responds at `/` with a simple JSON status message:

```bash
gunicorn dashboard.app:app
```

## Docs

- [Roadmap](docs/ROADMAP.md)
- [API draft](docs/API.md)
