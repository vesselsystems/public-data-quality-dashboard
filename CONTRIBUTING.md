# Contributing

This repository favors small, explainable changes over broad rewrites.

Before opening a change:

1. Create an isolated Python 3.11+ environment and install `.[dev]`.
2. Run `pytest` and `ruff check .`.
3. If the source snapshot changes, regenerate `data/raw/provenance.json` and explain the new measurements.
4. Do not commit downloaded raw data, credentials, or personal information.

Changes to quality rules should include a test and a short explanation of what the rule can—and cannot—prove.
