# Deploy On Streamlit Community Cloud

This repo is set up to deploy the KHIS Toolkit dashboard on Streamlit Community Cloud using [streamlit_app.py](../streamlit_app.py).

Render support is no longer the active hosting path for the public demo. The old [render.yaml](../render.yaml) file is kept for reference while the project uses Streamlit for now.

## Before You Start

- Make sure your GitHub repo is up to date.
- Keep the public demo in `offline_demo` mode unless you are intentionally testing approved KHIS credentials.
- Use Python `3.11` in Streamlit Advanced settings because the toolkit is tested on Python `3.9-3.11`.
- Confirm [requirements.txt](../requirements.txt) includes Streamlit and the dashboard dependencies.
- Never commit real KHIS credentials or local `.streamlit/secrets.toml`.

Streamlit Community Cloud runs `streamlit run` from the repository root and asks for the app entrypoint file during setup. The active entrypoint for this repo is:

```text
streamlit_app.py
```

## Streamlit Setup

1. Push the latest `main` branch to GitHub.
2. Go to `https://share.streamlit.io`.
3. Click `Create app`.
4. Choose `Yup, I have an app`.
5. Select repository `andyombogo/khis-toolkit`.
6. Select branch `main`.
7. Set the main file path to `streamlit_app.py`.
8. Choose a memorable app URL such as `khis-toolkit` if it is available.
9. Open `Advanced settings`.
10. Select Python `3.11`.
11. Paste the demo secrets from [.streamlit/secrets.example.toml](../.streamlit/secrets.example.toml), or set only `KHIS_DATA_MODE = "offline_demo"`.
12. Click `Deploy`.

## Public Demo Settings

For the stable public demo, use:

```toml
KHIS_DATA_MODE = "offline_demo"
```

That keeps the dashboard fully local to the repository's bundled demo workflow and avoids depending on public DHIS2/KHIS uptime.

If you want to test the DHIS2 public demo server, use:

```toml
KHIS_DATA_MODE = "dhis2_demo"
DHIS2_BASE_URL = "https://demos.dhis2.org/hmis_dev"
DHIS2_USERNAME = "demo_en"
DHIS2_PASSWORD = "District1#"
```

For real KHIS access, replace those with approved Ministry of Health credentials and set:

```toml
KHIS_DATA_MODE = "khis_live"
```

Only use `khis_live` after the credentials, indicator access, and county organisation-unit mapping have been verified.

## Local Smoke Test

From the repository root:

```powershell
py -m streamlit run streamlit_app.py
```

The app should open locally at Streamlit's printed URL, usually `http://localhost:8501`.

## First Deploy Check

After deployment:

- confirm the Streamlit app loads without external KHIS credentials
- confirm the county selector changes the map, chart, quality panel, mental-health panel, and feedback brief
- confirm the sidebar shows `Data mode: offline_demo`
- copy the deployed `streamlit.app` URL into [README.md](../README.md), [LAUNCH_POSTS.md](LAUNCH_POSTS.md), and [KHIS_OUTREACH_EMAIL.md](KHIS_OUTREACH_EMAIL.md)

## Troubleshooting

- If the app tries to call live DHIS2/KHIS during a public demo, check that `KHIS_DATA_MODE` is set to `offline_demo`.
- If dependencies fail, confirm Streamlit is reading [requirements.txt](../requirements.txt) from the repository root.
- If the app uses an unexpected Python version, delete and redeploy the app with Python `3.11` selected in Advanced settings.
- If secrets are missing, edit the app settings in Streamlit Community Cloud and paste the TOML values again.
