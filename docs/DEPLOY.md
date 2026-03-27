# Deploy On Render

This repo is set up to deploy the Flask dashboard to Render using the checked-in [render.yaml](../render.yaml).

## Before You Start

- Make sure your GitHub repo is up to date.
- Decide whether you want demo data or real KHIS credentials.
- If you use demo mode, the repo is currently verified against `https://demos.dhis2.org/hmis_dev` as of 2026-03-27.
- This blueprint now pins `PYTHON_VERSION=3.11.11` because the repo is tested on Python `3.9-3.11`, and Render's current default Python version for newly created services can move independently of that support window.
- The public Render demo should use `KHIS_DATA_MODE=offline_demo` so the app does not depend on external DHIS2/KHIS availability just to load.

## Render Setup

1. Push the latest `main` branch to GitHub.
2. In Render, choose `New +` and then `Blueprint`.
3. Connect the GitHub repo and select `khis-toolkit`.
4. Let Render read [render.yaml](../render.yaml).
5. Confirm the service name is `khis-toolkit-dashboard`.
6. Confirm the runtime is Python and the plan is the one you want to use for the first demo.
7. Confirm the build command is `pip install -r requirements.txt`.
8. Confirm the start command is `gunicorn dashboard.app:app`.
9. Confirm the health check path is `/health`.
10. Confirm the environment variables include `PYTHON_VERSION=3.11.11`.
11. Confirm `KHIS_DATA_MODE=offline_demo` for the public demo deployment.

## Environment Variables

Render will create `FLASK_SECRET_KEY` automatically from [render.yaml](../render.yaml).

For demo mode, keep these values:

- `DHIS2_BASE_URL=https://demos.dhis2.org/hmis_dev`
- `DHIS2_USERNAME=demo_en`
- `DHIS2_PASSWORD=District1#`
- `PYTHON_VERSION=3.11.11`
- `KHIS_DATA_MODE=offline_demo`

For real KHIS access, replace them with your Ministry of Health credentials:

- `DHIS2_BASE_URL`
- `DHIS2_USERNAME`
- `DHIS2_PASSWORD`
- Keep `PYTHON_VERSION=3.11.11` unless you have tested a different version locally and in CI.
- Change `KHIS_DATA_MODE` to `khis_live` only after you have verified the credentials and live indicator availability.

## First Deploy

1. Click `Apply`.
2. Wait for the first build to finish.
3. Open the deployed site and confirm the dashboard loads.
4. Open `/health` on the deployed service and confirm it returns HTTP `200`.
5. Copy the live Render URL into [README.md](../README.md) if Render assigns a different subdomain than `https://khis-toolkit-dashboard.onrender.com`.

## Troubleshooting

- If the dashboard shows demo data, that is expected for the public Render link.
- `offline_demo` is the recommended public-demo mode because it never depends on KHIS or public DHIS2 uptime.
- If you intentionally switch to `dhis2_demo`, the notebooks and dashboard still fall back to deterministic sample data when the public demo host is slow or unavailable.
- If Render fails during install, check that the Python environment matches [requirements.txt](../requirements.txt).
- If the health check fails, verify the deployed service is using `gunicorn dashboard.app:app` and that `/health` returns JSON.
