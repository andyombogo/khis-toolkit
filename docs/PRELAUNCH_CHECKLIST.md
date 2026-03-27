# Pre-Launch Checklist

## Results

- PASS: Python modules have top-level docstrings. Verified with an AST audit across `khis/`, `dashboard/`, `src/`, and `tests/` on 2026-03-27.
- PASS: Public package exports are present in [khis/__init__.py](../khis/__init__.py), including connector, counties, cleaning, quality, forecasting, and demo-safe helpers.
- PASS: README includes GitHub, PyPI, and Render deployment links in [README.md](../README.md).
- PASS: `.env` is gitignored in [.gitignore](../.gitignore), and [.env.example](../.env.example) includes demo, KHIS, dashboard, and API settings.
- PASS: All four notebooks executed end to end on 2026-03-27 with the public demo configuration, using demo-safe fallbacks when the public DHIS2 host was slow.
- PASS: `pytest tests -q` passed on 2026-03-27 with `28 passed, 3 skipped`.
- PASS: `black --check` passed for `khis/`, `dashboard/`, `tests/`, and `src/` on 2026-03-27.
- PASS: No sensitive or production credentials are hardcoded in the repo. The only embedded credentials are the public DHIS2 demo credentials intentionally documented in [khis/connector.py](../khis/connector.py), [.env.example](../.env.example), and [render.yaml](../render.yaml).
- PASS: [CHANGELOG.md](../CHANGELOG.md) is current for the `0.1.0` release.
- PASS: `/health` returns HTTP `200` in the local Flask app verification for [dashboard/app.py](../dashboard/app.py).

## Notes

- Notebook execution still emits non-fatal Windows/Jupyter runtime warnings about the event loop selector thread during `nbclient` runs. The notebooks completed successfully despite those warnings.
- `pytest` emits a non-fatal cache warning in this OneDrive workspace because `.pytest_cache` creation is restricted.
