# Public Data Quality & EDA Dashboard

[![CI](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/vesselsystems/public-data-quality-dashboard/actions/workflows/ci.yml)

A local Streamlit dashboard for inspecting a public Seattle weather CSV. The project loads the source into DuckDB, normalizes the four source fields, runs explicit quality checks, and shows the results alongside simple exploratory summaries.

## Status

This is a local Project 1 implementation, not a hosted demo or a production ingestion service. The repository contains the dashboard code, tests, SQL artifact, and reproducibility metadata; no deployment or screenshot is included.

The dashboard intentionally reports the source issues it finds instead of silently repairing them. A quality score is a summary of the checks implemented here, not a claim that the source is accurate or fit for operational decisions.

## Question and scope

**Question:** What can be responsibly shown from this historical weather file after checking completeness, duplicates, temperature logic, ranges, and source chronology?

The project demonstrates a small SQL-to-Python workflow:

1. Download the public CSV.
2. Load it into a transient DuckDB relation named `weather_raw`.
3. Cast the source fields to the normalized schema.
4. Run quality checks before sorting data for display.
5. Show the evidence and a descriptive annual summary in Streamlit.

## Measured local snapshot

The following findings were measured from the local `data/raw/seattle_weather.csv` used while updating this repository. A later download can change the file; `data/raw/provenance.json` records the snapshot hash and measurements.

| Finding | Local measurement |
|---|---:|
| Rows / source columns | 24,381 / 4 |
| Parsed date range | 1948-01-01 to 2015-12-31 |
| Missing required cells | 6 (5 `Mean_TemperatureC`, 1 `Min_TemperatureC`) |
| Duplicate dates | 0 |
| Temperature-order violations | 34 rows violate `min <= mean <= max` |
| Values outside the review range | 0 rows outside -60°C to 60°C |
| Backward date transitions | 0 in source row order |
| Calendar coverage caveat | 2011 has no rows; 2000 has 275 rows; 8 gaps longer than one day occur after sorting available dates |
| Implemented quality score | 71% (5 of 7 checks pass) |

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

The download script writes the raw file (ignored by Git) and updates `data/raw/provenance.json`. Open the local Streamlit URL shown in the terminal.

Run the automated checks:

```bash
pytest
ruff check .
```

## SQL artifact and relation

`sql/quality_checks.sql` is written for the actual transient relation created by `load_with_sql`: `weather_raw`. The relation keeps the source column names, so each query uses `TRY_CAST` and aliases the fields to the normalized names used in Python. The chronology query uses DuckDB `rowid` (CSV insertion order); ordering by date before that check would hide a source-order problem.

The SQL file is an auditable artifact, not a standalone database. To run it manually, first create `weather_raw` with the loader's `CREATE TABLE ... read_csv_auto(...)` step in the same DuckDB session; `load_with_sql` closes its own transient connection after returning. The Streamlit app validates source order first and then sorts a display copy by date.

## Project structure

```text
.
├── app.py                              # Streamlit dashboard
├── data/raw/                           # Downloaded data; ignored by Git
│   └── provenance.json                 # Tracked source hash and local measurements
├── docs/data_dictionary.md             # Source and normalized field definitions
├── sql/quality_checks.sql              # Auditable checks for weather_raw
├── scripts/download_data.py            # Download and provenance entry point
├── src/data_quality_dashboard/
│   ├── data.py                         # Download, DuckDB load, metadata, summaries
│   └── quality.py                      # Reusable quality checks
└── tests/
```

## Data source and provenance

- Publisher/repository: [Plotly datasets](https://github.com/plotly/datasets)
- Upstream file: `2016-weather-data-seattle.csv`
- URL: `https://raw.githubusercontent.com/plotly/datasets/0c447c47b757ad74edecab31f0d72f849d2e67c2/2016-weather-data-seattle.csv`
- Local filename: `data/raw/seattle_weather.csv`
- Snapshot metadata: [`data/raw/provenance.json`](data/raw/provenance.json)

The download is pinned to Plotly datasets commit `0c447c47b757ad74edecab31f0d72f849d2e67c2`. The local metadata records the downloaded file's SHA-256 hash, retrieval time, byte size, schema, row count, date range, and measured quality observations. The snapshot described by the checked-in metadata has SHA-256 `2837c01b75e4dd0f8bd6810dca805a8ac42a4743bf019128366924ef3f857fdf`.

The raw CSV is not tracked to keep the repository small. Check the upstream repository's terms before redistributing the data or presenting results outside this local project.

## Limitations and next steps

- The source has missing numeric values and 34 temperature-order violations; this project does not impute or correct them.
- Chronology checks detect backward transitions, not complete daily coverage. The measured 2011 gap and shorter 2000 record need a separate decision about missing-period handling.
- The range rule is a review threshold, not proof that every value inside it is correct.
- The source's station, measurement, and revision metadata are not independently validated here.
- There is no hosted deployment, scheduled refresh, alerting, or operational database.

Planned follow-up work is tracked in [`ROADMAP.md`](ROADMAP.md). A useful next implementation would add an explicit calendar-coverage check and an anomaly review path before any trend is treated as reliable.

## License

The code is released under the [MIT License](LICENSE). The upstream dataset remains subject to the terms of its publisher.
