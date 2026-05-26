# KHIS Toolkit Roadmap

This roadmap reflects how I am building KHIS Toolkit from a practical Kenya-first workflow into something strong enough for real county use, research support, and public health demos.

## What I Have Already Built

- [x] Phase 0: repository scaffold, packaging, docs, notebooks, and CI starter files
- [x] Phase 1: DHIS2 connector, Kenya county resolver, and connector/county tests
- [x] Phase 2: KHIS cleaning layer with period parsing, missingness flags, bounded filling, and public API wrappers
- [x] Phase 3: county data quality scorecard with completeness, outlier, timeliness, and suspicious-zero checks
- [x] Phase 4: Prophet, XGBoost, and ensemble forecasting with anomaly detection and forecasting notebook
- [x] Phase 5: Flask dashboard, county map helpers, and Kenya-focused README
- [x] Phase 6: FastAPI endpoints, CI/CD hardening, and PyPI publication assets
- [x] Phase 7: quick-start and county notebooks for first-time evaluators

## Phase 8: Launch and Outreach

- [x] Package published to PyPI as `khis-toolkit` 0.1.0
- [x] Streamlit dashboard live at https://khis-toolkit.streamlit.app/
- [x] All four demo notebooks run end-to-end in offline_demo mode
- [x] Pre-launch checklist passed (formatting, tests, no hardcoded credentials)
- [x] GitHub release tagged for v0.1.0
- [x] Repo hardened: CONTRIBUTING.md, CITATION.cff, SECURITY.md, issue templates, PR template
- [x] Dev dependencies separated from production requirements
- [ ] KHIS access request submitted to khissupport@health.go.ke
- [ ] One-county pilot conversation initiated with MoH Digital Health division
- [ ] Outreach to WHO AFRO / county health teams / NGO analytics partners
- [ ] Public launch post on LinkedIn and Twitter/X

## Longer-Term Direction

- [x] Add a mental health indicator workflow alongside malaria-focused examples
- [ ] Automated county health review reports from forecasts and scorecards
- [ ] Expand to Uganda and Tanzania DHIS2 deployments after Kenya stabilises
- [ ] OHRE integration once live KHIS access is validated
