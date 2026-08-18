# Project roadmap

This repository is Project 1 in a four-project learning sequence. The current scope is a local, evidence-first data-quality and EDA workflow. It is not presented as a hosted or production system.

## Current milestone — Project 1: EDA + data quality

Completed in this repository:

- [x] Public Plotly source and reproducible download script
- [x] DuckDB load with tolerant type conversion
- [x] Quality checks for required fields, emptiness, missing values, duplicate dates, temperature ordering, review range, backward date transitions, and strict calendar coverage
- [x] Chronology regression test that verifies source order is not hidden by a date sort
- [x] Streamlit dashboard with a quality score, evidence table, anomaly review table/download, chart, and annual summary
- [x] SQL artifact aligned to the loader's actual `weather_raw` relation, including coverage and anomaly queries
- [x] Tracked provenance metadata with source URL, pinned revision, snapshot hash, retrieval time, schema, size, terms caveat, and measured observations
- [x] Data dictionary, pytest suite, Ruff configuration, and GitHub Actions configuration
- [x] README findings measured from the current local snapshot
- [x] Data dictionary documents the coverage policy and anomaly review path

The current local snapshot is not fully clean: it contains 6 missing required cells, 34 temperature-order violations, and 456 missing calendar days across 8 gaps. The dashboard surfaces those findings and does not repair or exclude the rows. The strict coverage policy makes the missing 2011 calendar year explicit.

Still open for Project 1:

- [ ] Review the dashboard output and add a screenshot only if a useful, reproducible view is available
- [ ] Optionally deploy the local app and document the host, URL, and refresh behavior; no deployment is claimed now

## Next repositories

### Project 2 — Predictive model

Build a baseline-to-production-style supervised model with cross-validation, leakage checks, error analysis, a model card, and a business-facing write-up. Production-style is a future design target, not the status of this repository.

### Project 3 — Governance RAG assistant

Build a cited RAG assistant over public policy or documentation. Measure retrieval quality and test unsupported answers, prompt injection, privacy, and responsible use.

### Project 4 — Deployed AI capstone

Package the strongest model or RAG work behind an API and simple front end. Add Docker, versioning, monitoring, an architecture diagram, and a one-page case study.

The sequence is intended to build explainable evidence over time; completing a checklist item does not by itself establish production readiness or external impact. The calendar check is a completeness assertion over the observed date range, and the anomaly table is a review aid—not an automatic correction or exclusion policy.
