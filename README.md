# Public Data Quality & EDA Dashboard

[![CI](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml)

A local Streamlit dashboard for inspecting a public Seattle weather CSV. The project loads the source into DuckDB, normalizes the four source fields, runs explicit quality checks, and shows the results alongside simple exploratory summaries.

## Status

This is a local Project 1 implementation, not a hosted demo or a production ingestion service. The repository contains the dashboard code, tests, SQL artifact, and reproducibility metadata; no deployment or screenshot is included. The app was smoke-tested over its local Streamlit HTTP endpoint, but the approved Chrome DevTools browser tool was unavailable for this run, so no screenshot is claimed. No deployment target or credentials were authorized, so no cloud resource was created; the deployment-ready state is the reproducible local app and CI checks.

The dashboard intentionally reports the source issues it finds instead of silently repairing them. A quality score is a summary of the checks implemented here, not a claim that the source is accurate or fit for operational decisions.

## Provenance validation and CI evidence

`data/raw/seattle_weather.csv` is an ignored local file; it is not committed with this repository. The tracked `data/raw/provenance.json` records measurements from the snapshot used for the documented local run, but metadata alone does not prove that the snapshot is present or unchanged in a later checkout.

When the ignored snapshot is available, run the executable validator:

```bash
python scripts/validate_provenance.py
```

A matching result is measured local evidence: the validator compares the SHA-256, byte size, CSV header, and recorded row count. A missing snapshot is an explicit failure in the default mode, with instructions to download it; the validator never invents measurements. CI runs the same check with `--allow-missing` because a clean checkout cannot contain ignored raw data. CI therefore reports an unavailable snapshot as an explicit skip, not as evidence that the recorded local measurements were revalidated. Hash, size, or schema mismatches still fail CI.

## Question and scope

**Question:** What can be responsibly shown from this historical weather file after checking completeness, duplicates, temperature logic, ranges, and source chronology?

The project demonstrates a small SQL-to-Python workflow:

1. Download the public CSV.
2. Load it into a transient DuckDB relation named `weather_raw`.
3. Cast the source fields to the normalized schema while retaining a one-based source row number.
4. Run source-order, completeness, logic, range, and calendar-coverage checks before sorting data for display.
5. Show the evidence, a temperature-anomaly review table, and a descriptive annual summary in Streamlit.

## Measured local snapshot

The following findings were measured from the local `data/raw/seattle_weather.csv` used while updating this repository. A later download can change the file; `data/raw/provenance.json` records the snapshot hash and measurements. They are recorded local-snapshot evidence, not measurements performed by CI or a claim about an unavailable raw file.

| Finding | Local measurement |
|---|---:|
| Rows / source columns | 24,381 / 4 |
| Parsed date range | 1948-01-01 to 2015-12-31 |
| Missing required cells | 6 (5 `Mean_TemperatureC`, 1 `Min_TemperatureC`) |
| Duplicate dates | 0 |
| Temperature-order violations | 34 rows violate `min <= mean <= max` |
| Values outside the review range | 0 rows outside -60°C to 60°C |
| Backward date transitions | 0 in source row order |
| Temperature-order anomaly review rows | 34, available in the dashboard review table and CSV download |
| Calendar coverage | 24,837 expected days; 24,381 present; 456 missing across 8 gaps; 2011 has no rows |
| Implemented core quality score | 71% (5 of the original 7 checks pass) |
| Supplemental calendar-coverage check | FAIL: 24,837 expected days; 24,381 present; 456 missing across 8 gaps; 2011 has no rows |

These results are evidence about this local snapshot, not an endorsement of the upstream data. The dashboard still displays descriptive output when checks fail so that the failures remain visible.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/download_data.py
streamlit run app.py
```

The download script writes the raw file (ignored by Git) and updates `data/raw/provenance.json`. Open the local Streamlit URL shown in the terminal. After downloading, validate that the tracked metadata still describes the local file:

```bash
python scripts/validate_provenance.py
```

Run the automated checks:

```bash
pytest
ruff check .
```

## SQL artifact and relation

`sql/quality_checks.sql` is written for the actual transient relation created by `load_with_sql`: `weather_raw`. The relation keeps the source column names, so each query uses `TRY_CAST` and aliases the fields to the normalized names used in Python. The SQL artifact includes the strict calendar-coverage summary and the temperature-order anomaly review query. The chronology query uses DuckDB `rowid` (CSV insertion order); ordering by date before that check would hide a source-order problem.

The SQL file is an auditable artifact, not a standalone database. To run it manually, first create `weather_raw` with the loader's `CREATE TABLE ... read_csv_auto(...)` step in the same DuckDB session; `load_with_sql` closes its own transient connection after returning. The Streamlit app validates source order first, exposes anomaly rows with their one-based source positions, and then sorts a display copy by date.

## Project structure

```text
.
├── app.py                              # Streamlit dashboard
├── data/raw/                           # Downloaded data; ignored by Git
│   └── provenance.json                 # Tracked source hash and local measurements
├── docs/data_dictionary.md             # Source, normalized fields, and review rules
├── docs/provenance.md                   # Local versus CI provenance states
├── sql/quality_checks.sql              # Auditable checks for weather_raw
├── scripts/download_data.py            # Download and provenance entry point
├── scripts/validate_provenance.py     # Validate ignored snapshot integrity
├── src/data_quality_dashboard/
│   ├── data.py                         # Download, DuckDB load, metadata, summaries
│   ├── provenance.py                   # Hash, size, schema, and availability checks
│   └── quality.py                      # Reusable quality checks
└── tests/
```

## Data source and provenance

- Publisher/repository: [Plotly datasets](https://github.com/plotly/datasets)
- Upstream file: `2016-weather-data-seattle.csv`
- URL: `https://raw.githubusercontent.com/plotly/datasets/0c447c47b757ad74edecab31f0d72f849d2e67c2/2016-weather-data-seattle.csv`
- Local filename: `data/raw/seattle_weather.csv`
- Snapshot metadata: [`data/raw/provenance.json`](data/raw/provenance.json)

The download is pinned to Plotly datasets commit `0c447c47b757ad74edecab31f0d72f849d2e67c2`. The local metadata records the downloaded file's SHA-256 hash, retrieval time, byte size, schema, row count, date range, calendar coverage, and measured quality observations. The snapshot described by the checked-in metadata has SHA-256 `2837c01b75e4dd0f8bd6810dca805a8ac42a4743bf019128366924ef3f857fdf`. That digest is a recorded measurement until the ignored file is locally available and passes `validate_provenance.py`.

The code is MIT-licensed, but the upstream dataset's license or terms have not been independently verified in this project. The provenance file links to the publisher's repository; check its terms before redistributing the data or presenting results outside this local project.

## Limitations and next steps

- The source has missing numeric values and 34 temperature-order violations. The dashboard exposes those rows for review but does not impute, correct, or exclude them.
- The strict calendar-coverage check finds 456 missing days across 8 gaps, including the missing 2011 calendar year and a shorter 2000 record. It is shown separately from the historical seven-check score so the score's denominator and meaning do not change silently. The coverage result is evidence about completeness, not a decision to impute missing periods.
- The range rule is a review threshold, not proof that every value inside it is correct.
- The source's station, measurement, and revision metadata are not independently validated here.
- There is no hosted deployment, scheduled refresh, alerting, or operational database.
- A deterministic diff/freshness check is intentionally not included: the raw snapshot is ignored, and comparing it with a newly downloaded upstream file would depend on network availability, upstream changes, and retrieval time. CI can verify the committed validator and tests, but cannot manufacture a current raw-data diff or freshness result without adding public data to the checkout.

Planned follow-up work is tracked in [`ROADMAP.md`](ROADMAP.md). The current dashboard remains a local descriptive workflow; no trend should be treated as reliable without addressing the documented coverage and source-value issues.

## License

The code is released under the [MIT License](LICENSE). The upstream dataset remains subject to the terms of its publisher.
