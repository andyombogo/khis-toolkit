# KHIS Toolkit

![PyPI Version](https://img.shields.io/pypi/v/khis-toolkit?label=PyPI)
![pip install khis-toolkit](https://img.shields.io/badge/pip%20install-khis--toolkit-blue)
![CI](https://github.com/andyombogo/khis-toolkit/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Kenya-first Python analytics toolkit and Streamlit dashboard for DHIS2/KHIS county health data.

KHIS Toolkit helps health records officers, analysts, public health researchers, and county teams move from routine DHIS2/KHIS pulls to cleaner trend review, data quality checks, short-horizon forecasts, and a shareable county dashboard without rebuilding the same workflow every time.

- Live demo: https://khis-toolkit.streamlit.app/
- GitHub: https://github.com/andyombogo/khis-toolkit
- PyPI: https://pypi.org/project/khis-toolkit/
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- Streamlit deployment guide: [docs/DEPLOY.md](docs/DEPLOY.md)
- Release checklist: [docs/PRELAUNCH_CHECKLIST.md](docs/PRELAUNCH_CHECKLIST.md)
- Launch copy: [docs/LAUNCH_POSTS.md](docs/LAUNCH_POSTS.md)
- Pitch outline: [docs/PITCH.md](docs/PITCH.md)
- KHIS outreach email draft: [docs/KHIS_OUTREACH_EMAIL.md](docs/KHIS_OUTREACH_EMAIL.md)

## Why This Exists

Kenya county teams already use DHIS2/KHIS, but the hardest part is often turning routine pulls into something clean, explainable, and useful for planning. Many DHIS2 Python libraries are generic or lightly maintained, and they do not centre Kenya's county hierarchy, KHIS-style cleaning issues, or the operational forecasting that comes up in county review meetings.

KHIS Toolkit closes that gap with a workflow grounded in Kenya's reporting structure, review cadence, and county-level decision needs.

## What It Does

- Connects to DHIS2 or KHIS and pulls indicator data with a clean Python interface.
- Resolves all 47 Kenya counties with county metadata and placeholder-to-live DHIS2 ID support.
- Bundles real Kenya county boundary geometry for a more credible county dashboard demo.
- Cleans KHIS data quirks such as period parsing, duplicate rows, missingness flags, and bounded imputation.
- Generates county data quality scorecards with completeness, outlier, timeliness, and suspicious-zero checks.
- Produces Prophet, XGBoost, and ensemble forecasts together with a county-facing Streamlit dashboard.
- Adds a mental-health service workflow for curated MNS indicator packages, county summaries, and OHRE-ready downstream integration.

## Quick Start

```powershell
pip install khis-toolkit
```

```python
import khis

conn = khis.connect()  # uses .env credentials
df = khis.get(
    conn,
    "malaria_cases",
    counties=["Nairobi"],
    periods="last_12_months",
)
df_clean = khis.clean(df)
forecast = khis.forecast(df_clean, weeks_ahead=4)
```

Run the Streamlit dashboard locally:

```powershell
$env:KHIS_DATA_MODE = "offline_demo"
py -m streamlit run streamlit_app.py
```

The public dashboard runs in `offline_demo` mode at https://khis-toolkit.streamlit.app/ so the demo stays available even before live KHIS credentials are approved.

## Mental Health Workflow

KHIS Toolkit now includes a Kenya-first mental-health service workflow so you do
not have to start from a blank notebook when exploring MNS indicators. The
package uses a curated indicator catalog, attempts to resolve live KHIS matches,
and falls back to a stable demo frame when public or offline environments do not
expose mental-health metadata.

```python
import khis

conn = khis.connect()
mns = khis.pull_mental_health_data(
    conn,
    counties=["Nairobi", "Mombasa", "Kisumu"],
    periods="last_12_months",
)
county_summary = khis.summarise_county_mental_health(mns)
```

## Demo Notebooks

- [01_quick_start.ipynb](examples/01_quick_start.ipynb): first-run walkthrough for connecting, pulling, and cleaning DHIS2 data.
- [02_kenya_counties.ipynb](examples/02_kenya_counties.ipynb): county metadata, lookup helpers, and mapping-ready coordinates.
- [03_data_quality.ipynb](examples/03_data_quality.ipynb): completeness, outliers, timeliness, and county quality scorecards.
- [04_forecasting.ipynb](examples/04_forecasting.ipynb): Prophet, ensemble forecasts, anomaly detection, and CSV export for review meetings.

## Live Dashboard

The live public demo is available here:

https://khis-toolkit.streamlit.app/

Deployment is currently configured for Streamlit Community Cloud through [streamlit_app.py](streamlit_app.py). Follow the [Streamlit deployment guide](docs/DEPLOY.md) and use `streamlit_app.py` as the main file path.

For the public portfolio/demo link, I use `KHIS_DATA_MODE=offline_demo`. That keeps the dashboard stable even before KHIS credentials are granted, because it uses bundled county demo data instead of depending on external DHIS2/KHIS uptime.

## Demo For KHIS Conversations

The public Streamlit link is intentionally designed to be a stable pre-access demo, not a claim of live KHIS connectivity. In `offline_demo` mode, the dashboard uses bundled county sample data to prove the workflow, interface, and county-review value without needing Ministry of Health credentials first.

At this stage, the demo is useful for three things:

- showing the KHIS team what the county map, quality checks, and short-horizon forecast workflow will look like
- demonstrating that the package already understands Kenya county structure and can support malaria and mental-health indicator paths
- making a narrow ask for read-only access to validate one county workflow instead of requesting a broad national integration up front

What I would have ready before sending an access request:

- public demo link: https://khis-toolkit.streamlit.app/
- [docs/PITCH.md](docs/PITCH.md) for the walkthrough order
- [docs/KHIS_OUTREACH_EMAIL.md](docs/KHIS_OUTREACH_EMAIL.md) for the first access-request draft

## Sample Kenya Counties

| County | Region | Placeholder DHIS2 ID |
| --- | --- | --- |
| Nairobi | Nairobi | KE47 |
| Mombasa | Coast | KE01 |
| Kisumu | Nyanza | KE42 |
| Nakuru | Rift Valley | KE32 |
| Meru | Eastern | KE12 |

## Getting KHIS Credentials

My practical next step after the demo is to request real KHIS access through the Ministry of Health support channel at `khissupport@health.go.ke`. I want that conversation to be based on something concrete, not just an abstract request. A working demo and a public GitHub repo make it easier to show how the data would be used, what the workflow already looks like, and why live county IDs matter.

## For Researchers And Grant Applications

KHIS Toolkit is my Kenya-first Python workflow for extracting, cleaning, validating, forecasting, and visualising routine DHIS2/KHIS county health data. In a grant or methodology section, I would describe it as the reproducible data-engineering and analytics layer I am using to convert county indicator pulls into analysis-ready time series, quality scorecards, short-horizon forecasts, and dashboard outputs. I designed it to stay operational, so the same workflow can support exploratory research, county review meetings, and pilot digital public health deployments without rewriting the pipeline for each new use case.

Suggested citation:

`Andrew, J. (2026). khis-toolkit: Python analytics toolkit for Kenya DHIS2/KHIS health data (Version 0.1.0) [Computer software]. https://github.com/andyombogo/khis-toolkit`

Current indicator support:

- Malaria-oriented DHIS2/KHIS indicators demonstrated in the public notebooks and dashboard
- County indicator pulls by ID or search term for any accessible DHIS2/KHIS metadata item
- County data quality workflows for completeness, outliers, timeliness, and suspicious zeros
- Forecasting workflows for routine weekly or monthly county indicators

Validation and data quality methodology:

- [examples/03_data_quality.ipynb](examples/03_data_quality.ipynb)

Research collaboration contact:

- `andyombogo@gmail.com`

## Contributing

Pull requests are welcome, especially from people who have KHIS access and can help verify real organisation-unit IDs, indicator naming, and county-specific workflow details. If you work in county health information, public health analytics, or DHIS2 support, your practical feedback is especially valuable.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the fuller project plan.

The direction is straightforward:

- keep tightening the Kenya workflow until the package is solid in real use
- extend the mental health indicator path into a stronger county review workflow
- add automated county reporting once the core extraction, cleaning, and forecasting flow is stable

## License

MIT

## Author

John Andrew, Nairobi
