# Deploy On Render

This repo is set up to deploy the Flask dashboard to Render using the checked-in [render.yaml](../render.yaml).

## Before You Start

- Make sure your GitHub repo is up to date.
- Decide whether you want demo data or real KHIS credentials.
- If you use demo mode, the repo is currently verified against `https://demos.dhis2.org/hmis_dev` as of 2026-03-27.

## Render Setup

1. Push the latest `main` branch to GitHub.
2. In Render, choose `New +` and then `Blueprint`.
3. Connect the GitHub repo and select `khis-toolkit`.
4. Let Render read [render.yaml](../render.yaml).
5. Confirm the service name is `khis-toolkit-dashboard`.
6. Confirm the build command is `pip install -r requirements.txt`.
7. Confirm the start command is `gunicorn dashboard.app:app`.
8. Confirm the health check path is `/health`.

## Environment Variables

Render will create `FLASK_SECRET_KEY` automatically from [render.yaml](../render.yaml).

For demo mode, keep these values:

- `DHIS2_BASE_URL=https://demos.dhis2.org/hmis_dev`
- `DHIS2_USERNAME=demo_en`
- `DHIS2_PASSWORD=District1#`

For real KHIS access, replace them with your Ministry of Health credentials:

- `DHIS2_BASE_URL`
- `DHIS2_USERNAME`
- `DHIS2_PASSWORD`

## First Deploy

1. Click `Apply`.
2. Wait for the first build to finish.
3. Open the deployed site and confirm the dashboard loads.
4. Open `/health` on the deployed service and confirm it returns HTTP `200`.
5. Copy the live Render URL into [README.md](../README.md) if Render assigns a different subdomain than `https://khis-toolkit-dashboard.onrender.com`.

## Troubleshooting

- If the dashboard shows demo data, that is expected when you keep the public demo credentials.
- If the public DHIS2 demo server is slow or unavailable, the notebooks and dashboard fall back to deterministic sample data so the workflow still works.
- If Render fails during install, check that the Python environment matches [requirements.txt](../requirements.txt).
- If the health check fails, verify the deployed service is using `gunicorn dashboard.app:app` and that `/health` returns JSON.
