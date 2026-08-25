# Contributing

This repository favors small, explainable changes over broad rewrites.

Before opening a change:

1. Create an isolated Python 3.11+ environment and install `.[dev]`.
2. Run `pytest`, `ruff check .`, and `python scripts/validate_reviews.py`.
3. For human-review changes, follow [`docs/review_workflow.md`](docs/review_workflow.md); do not infer or pre-fill decisions, reviewers, dates, or evidence.
4. If the source snapshot changes, regenerate `data/raw/provenance.json` and explain the new measurements.
5. Do not commit downloaded raw data, credentials, or personal information.

Changes to quality rules should include a test and a short explanation of what the rule can—and cannot—prove. The review validator must continue to reject malformed or incomplete terminal decisions.
