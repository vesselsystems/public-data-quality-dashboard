# Provenance validation

Project 1 keeps the raw CSV out of Git. `data/raw/provenance.json` is tracked so the source, pinned upstream revision, hash, size, schema, and local measurements remain reviewable without publishing the raw file.

## Validation states

Run this from the project root after the local download:

```bash
python scripts/validate_provenance.py
```

The validator reads the tracked metadata and, when present, checks the ignored `data/raw/seattle_weather.csv` for:

- SHA-256 digest;
- byte size;
- CSV header/schema; and
- recorded row count, when that field is present.

A match is measured evidence about the file currently on the local filesystem. A hash, size, or schema mismatch fails with field-specific output. If the raw file is unavailable, the default command fails clearly and does not substitute a new hash, size, or quality result. Use `python scripts/download_data.py` to obtain the pinned public snapshot before retrying.

## CI state

A clean CI checkout does not include ignored raw data. The quality workflow runs:

```bash
python scripts/validate_provenance.py --allow-missing
```

This makes the absence explicit: CI reports a skipped local-snapshot validation and continues to run tests and Ruff. If a snapshot is supplied to a checkout, mismatches still fail; `--allow-missing` does not allow bad metadata or stale hash/size/schema values. Consequently, CI evidence covers the validator implementation and repository checks, not a fresh measurement of the unavailable raw snapshot.

## Why there is no freshness diff

A deterministic raw-data diff or freshness assertion is not included. The raw file is intentionally ignored, while a new upstream download would introduce network availability, upstream revision changes, and retrieval-time-dependent metadata. Without committing public raw data or relying on a private/local file, CI has no stable pair of files to compare. The pinned upstream reference and recorded local measurements are therefore provenance context, not a current freshness claim.
