# KHIS Toolkit

![PyPI Version](https://img.shields.io/pypi/v/khis-toolkit?label=PyPI)
![pip install khis-toolkit](https://img.shields.io/badge/pip%20install-khis--toolkit-blue)
![CI](https://github.com/andyombogo/khis-toolkit/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Python analytics toolkit for Kenya DHIS2/KHIS health data.

KHIS Toolkit is built for people who work with county health data and need to move quickly from extraction to action. It helps a Kenya Health Records Officer pull DHIS2 data, clean routine reporting issues, check data quality, and generate short forecasts without building a custom workflow from scratch. The package is written with Kenya's county structure, reporting cadence, and review-meeting needs in mind.

- GitHub: https://github.com/andyombogo/khis-toolkit
- PyPI: https://pypi.org/project/khis-toolkit/
- Render deployment guide: [docs/DEPLOY.md](docs/DEPLOY.md)
- Release checklist: [docs/PRELAUNCH_CHECKLIST.md](docs/PRELAUNCH_CHECKLIST.md)
- Launch copy: [docs/LAUNCH_POSTS.md](docs/LAUNCH_POSTS.md)
- Expected Render URL after first deploy: `https://khis-toolkit-dashboard.onrender.com`

## Why This Exists

Kenya county teams already use DHIS2/KHIS, but the analytics gap remains real: pulling data is one thing, turning it into something clean, explainable, and useful for county planning is another. In practice, many DHIS2 Python libraries are generic or lightly maintained, and they do not centre Kenya's county hierarchy, KHIS-style data cleaning, or operational forecasting workflows. KHIS Toolkit exists to close that gap with a package that feels familiar to Kenya's health system rather than a generic data-science template.

## What It Does

- Connects to DHIS2 or KHIS and pulls indicator data with a clean Python interface.
- Resolves all 47 Kenya counties with county metadata and placeholder-to-live DHIS2 ID support.
- Cleans KHIS data quirks such as period parsing, duplicate rows, missingness flags, and bounded imputation.
- Generates county data quality scorecards with completeness, outlier, timeliness, and suspicious-zero checks.
- Produces Prophet, XGBoost, and ensemble forecasts together with a county-facing Flask dashboard.

## Quick Start

```
pip install khis-toolkit

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

## Demo Notebooks

- [01_quick_start.ipynb](examples/01_quick_start.ipynb): first-run walkthrough for connecting, pulling, and cleaning DHIS2 data.
- [02_kenya_counties.ipynb](examples/02_kenya_counties.ipynb): county metadata, lookup helpers, and mapping-ready coordinates.
- [03_data_quality.ipynb](examples/03_data_quality.ipynb): completeness, outliers, timeliness, and county quality scorecards.
- [04_forecasting.ipynb](examples/04_forecasting.ipynb): Prophet, ensemble forecasts, anomaly detection, and CSV export for review meetings.

## Live Dashboard

Deployment is configured in [render.yaml](render.yaml). Follow the [Render deployment guide](docs/DEPLOY.md) to publish the Flask dashboard with demo or KHIS credentials. Render will usually assign `https://khis-toolkit-dashboard.onrender.com` if the service name is available; confirm the actual URL after the first deploy and update this section if Render gives you a different subdomain.

## All 47 Kenya Counties Supported

| County | Region | Placeholder DHIS2 ID |
| --- | --- | --- |
| Nairobi | Nairobi | KE47 |
| Mombasa | Coast | KE01 |
| Kisumu | Nyanza | KE42 |
| Nakuru | Rift Valley | KE32 |
| Meru | Eastern | KE12 |

## Getting KHIS Credentials

Once you have a working demo to show, the next step is to request real KHIS access through the Ministry of Health support channel at `khissupport@health.go.ke`. Having a concrete demo or GitHub repo makes that conversation much easier because you can show exactly how the data will be used and why live county IDs matter.

## Contributing

Pull requests are welcome, especially from people who have KHIS access and can help verify real organisation-unit IDs, indicator naming, and county-specific workflow details. If you work in county health information, public health analytics, or DHIS2 support, your practical feedback is especially valuable.

## Roadmap

- Uganda and Tanzania DHIS2 support once the Kenya workflow is stable.
- A mental health indicator module for county burden tracking and review.
- Automated county health report generation from scorecards and forecasts.

## License

MIT

## Author

John Andrew, Nairobi
