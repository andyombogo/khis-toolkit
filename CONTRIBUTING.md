# Contributing to KHIS Toolkit

Thank you for your interest in contributing. KHIS Toolkit is a Kenya-first project and benefits most from people who understand DHIS2, county health data, or public health analytics in Kenya.

## What We Need Most

- **KHIS/DHIS2 practitioners** who can verify real organisation-unit IDs, indicator naming, and county-specific metadata.
- **County health information officers** who can flag workflow gaps or test the package against real county data pulls.
- **Python developers** who can improve test coverage, fix bugs, or extend the forecasting and quality modules.
- **Researchers** who want to use the toolkit in a grant project and can share feedback on the API surface.

## Getting Started

```bash
git clone https://github.com/andyombogo/khis-toolkit.git
cd khis-toolkit
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
```

Run the tests:

```bash
pytest tests/ -v
```

Run the formatter check:

```bash
black --check khis/ dashboard/ tests/ src/
```

Start the Streamlit dashboard in demo mode:

```bash
KHIS_DATA_MODE=offline_demo python -m streamlit run streamlit_app.py
```

## Pull Request Guidelines

1. Open an issue first for non-trivial changes so we can align on approach.
2. Write or update tests for any logic you add or change.
3. Run `black khis/ dashboard/ tests/ src/` before pushing — CI checks formatting.
4. Keep PRs focused. One thing per PR is easier to review.
5. Add a short description of what changed and why.

## Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) on GitHub Issues. Include your Python version, OS, and a minimal reproducer if possible.

## KHIS Metadata Contributions

If you have access to real KHIS organisation-unit IDs or indicator UIDs, open an issue or PR that targets `khis/counties.py` or `khis/connector.py`. Even a single verified county ID is useful — placeholder IDs in the current release are clearly marked.

## Code Style

- Formatter: `black` (enforced in CI).
- No unused imports. No commented-out code.
- Docstrings on all public functions. One-line for simple helpers, short summary block for complex ones.
- Prefer explicit over implicit.

## Contact

If you prefer to reach out directly before opening an issue, email `andyombogo@gmail.com`.
