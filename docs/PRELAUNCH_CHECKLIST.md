# Pre-Launch Checklist

## Results

- PASS: Python modules have top-level docstrings. Verified with an AST audit across `khis/`, `dashboard/`, `src/`, and `tests/` on 2026-03-27.
- PASS: Public package exports are present in [khis/__init__.py](../khis/__init__.py), including connector, counties, cleaning, quality, forecasting, and demo-safe helpers.
- PASS: README includes GitHub, PyPI, and Streamlit deployment links in [README.md](../README.md).
- PASS: `.env` is gitignored in [.gitignore](../.gitignore), and [.env.example](../.env.example) includes demo, KHIS, dashboard, and API settings.
- PASS: All four notebooks executed end to end on 2026-03-27 with the public demo configuration, using demo-safe fallbacks when the public DHIS2 host was slow.
- PASS: `pytest tests -q` passed on 2026-03-27 with `28 passed, 3 skipped`.
- PASS: `black --check` passed for `khis/`, `dashboard/`, `tests/`, and `src/` on 2026-03-27.
- PASS: No sensitive or production credentials are hardcoded in the repo. The only embedded credentials are the public DHIS2 demo credentials intentionally documented in [khis/connector.py](../khis/connector.py), [.env.example](../.env.example), [render.yaml](../render.yaml), and [.streamlit/secrets.example.toml](../.streamlit/secrets.example.toml).
- PASS: [CHANGELOG.md](../CHANGELOG.md) is current for the `0.1.0` release.
- PASS: `/health` returns HTTP `200` in the legacy local Flask app verification for [dashboard/app.py](../dashboard/app.py).
- PASS: Streamlit dashboard runs locally with `KHIS_DATA_MODE=offline_demo python -m streamlit run streamlit_app.py`. All four tabs (County view, Quality, Mental health, Pilot feedback) render. County selector, map, trend chart, and quality metrics all function as expected.
- PASS: CONTRIBUTING.md, CITATION.cff, SECURITY.md, issue templates, and PR template added on 2026-05-26.
- PASS: Dev dependencies separated into `requirements-dev.txt`; `requirements.txt` is now production-only.
- PASS: GitHub v0.1.0 release created with full release notes.
- NOTE: GitHub Actions CI badge may show as failing if your GitHub account has a billing lock. This is a billing account issue, not a code issue. Resolve at github.com/settings/billing. All checks passed locally.

## Notes

- Notebook execution still emits non-fatal Windows/Jupyter runtime warnings about the event loop selector thread during `nbclient` runs. The notebooks completed successfully despite those warnings.
- `pytest` emits a non-fatal cache warning in this OneDrive workspace because `.pytest_cache` creation is restricted.
- CI badge shows red due to GitHub billing account lock (not code bugs). Fix at github.com/settings/billing to restore the green badge before outreach.
