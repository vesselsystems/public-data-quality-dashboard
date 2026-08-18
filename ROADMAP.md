# Project roadmap

This repository is Project 1 in a four-project learning sequence. The current scope is a local, evidence-first data-quality and EDA workflow. It is not presented as a hosted or production system.

## Current milestone — Project 1: EDA + data quality

Completed in this repository:

- [x] Public Plotly source and reproducible download script
- [x] DuckDB load with tolerant type conversion
- [x] Quality checks for required fields, emptiness, missing values, duplicate dates, temperature ordering, review range, and backward date transitions
- [x] Chronology regression test that verifies source order is not hidden by a date sort
- [x] Streamlit dashboard with a quality score, evidence table, chart, and annual summary
- [x] SQL artifact aligned to the loader's actual `weather_raw` relation
- [x] Tracked provenance metadata with source URL, snapshot hash, schema, size, and measured observations
- [x] Data dictionary, pytest suite, Ruff configuration, and GitHub Actions configuration
- [x] README findings measured from the current local snapshot

The current local snapshot is not fully clean: it contains 6 missing required cells, 34 temperature-order violations, and incomplete calendar coverage. The dashboard surfaces those findings and does not repair the rows.

Still open for Project 1:

- [ ] Add an explicit calendar-coverage check and decide how missing periods should affect analysis
- [ ] Add an anomaly review table or documented exclusion policy for temperature-order violations
- [ ] Review the dashboard output and add a screenshot only if a useful, reproducible view is available
- [ ] Optionally deploy the local app and document the host, URL, and refresh behavior; no deployment is claimed now
- [ ] Capture a stable upstream revision or release identifier if the source provides one

## Next repositories

### Project 2 — Predictive model

Build a baseline-to-production-style supervised model with cross-validation, leakage checks, error analysis, a model card, and a business-facing write-up. Production-style is a future design target, not the status of this repository.

### Project 3 — Governance RAG assistant

Build a cited RAG assistant over public policy or documentation. Measure retrieval quality and test unsupported answers, prompt injection, privacy, and responsible use.

### Project 4 — Deployed AI capstone

Package the strongest model or RAG work behind an API and simple front end. Add Docker, versioning, monitoring, an architecture diagram, and a one-page case study.

The sequence is intended to build explainable evidence over time; completing a checklist item does not by itself establish production readiness or external impact.
