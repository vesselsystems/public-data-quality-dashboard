# Public Data Quality Dashboard

[![CI](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml)

A Streamlit dashboard that loads a public Seattle weather CSV through DuckDB, runs explicit quality checks, and shows what it finds before any chart.

## Why I built it

I wanted a project where the checks come before the plot. Most EDA dashboards I have used quietly drop bad rows on the way to a clean-looking chart. I wanted to see what one looks like when it refuses to fix anything and just reports what it found.

## What it does

The dashboard loads 24,381 rows of daily Seattle weather spanning 1948-01-01 to 2015-12-31 and runs eight checks against them.

| Finding | Measured |
|---|---:|
| Rows / source columns | 24,381 / 4 |
| Missing required cells | 6 (5 mean, 1 min) |
| Duplicate dates | 0 |
| Rows violating min ≤ mean ≤ max | 34 |
| Values outside −60 °C to 60 °C | 0 |
| Missing calendar days | 456 across 8 gaps; 2011 entirely absent |
| Core quality score | 71% (5 of 7 checks pass) |

The score fails on missing values and temperature ordering, and the trend chart still renders. That is the point: you get the trend and the reason to distrust it on the same screen.

## How it works

- DuckDB reads the CSV into a transient relation named `weather_raw` and `TRY_CAST`s the four source fields into the normalized schema, keeping a one-based source row number so every finding points back to a specific row.
- A failed cast becomes a null, which the missing-value check then counts. Nothing is dropped on the floor.
- Chronology is checked in source row order before any sort. Sorting first would hide a reordering problem.
- Calendar coverage is reported separately from the seven-check score so the score's denominator has not moved between runs.
- The chart reindexes to a full daily calendar, so missing periods render as blank gaps instead of a line quietly connecting across them.

<!-- TODO: add screenshot of the Quality checks tab with the temperature-order anomaly table visible -->

## Run it

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

The raw CSV is gitignored. Download it, then start the app:

```bash
python scripts/download_data.py
streamlit run app.py
```

`download_data.py` writes the file and updates `data/raw/provenance.json` with its hash, size, and measurements. Check that the tracked metadata still matches your copy:

```bash
python scripts/validate_provenance.py
```

## Tests and CI

21 tests plus Ruff, run on Python 3.11 and 3.12.

```bash
pytest
ruff check .
```

## Limits and what's next

The dashboard reports problems, it does not repair them. Nothing gets imputed, swapped, or excluded, and the 34 anomaly rows stay in every summary. The −60 °C to 60 °C range is a review threshold I picked, not a physical bound. The upstream dataset's license has not been checked by a person. There is no hosted deployment or scheduled refresh.

Next: get a human to confirm the publisher's terms, commit a pinned snapshot so CI can diff it, and put the app on a host with a documented refresh schedule.

## License

MIT for the code. The upstream dataset stays under its publisher's terms.
