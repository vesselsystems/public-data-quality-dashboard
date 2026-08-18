# Public Data Quality & EDA Dashboard

A portfolio project built from the AI Career Training Plan's first project brief:

> EDA + data quality dashboard on a public dataset, pulled via SQL.

This project loads the public Seattle weather dataset into DuckDB, checks data quality, and presents an explainable EDA dashboard with Streamlit. It demonstrates SQL-to-Python fluency, reproducible data checks, and clear communication of findings.

## Why this is portfolio-ready

- **Business question:** How complete and trustworthy is the historical weather data, and what patterns are visible after quality checks?
- **Governance angle:** The dashboard makes schema, completeness, duplicates, ordering constraints, and valid ranges visible before analysis.
- **Technical proof:** SQL extraction with DuckDB, Python/pandas transformations, automated tests, Streamlit presentation, and a documented data dictionary.
- **Honest limitations:** Weather observations are not a business forecast; this is a foundation project demonstrating reliable analysis and communication.

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

Open the local Streamlit URL shown in the terminal.

Run checks:

```bash
pytest
ruff check .
```

## Project structure

```text
.
├── app.py                              # Streamlit dashboard
├── data/raw/                           # Downloaded data; ignored by Git
├── docs/data_dictionary.md
├── sql/quality_checks.sql              # Auditable SQL checks
├── scripts/download_data.py
├── src/data_quality_dashboard/
│   ├── data.py                         # Download, SQL load, summary queries
│   └── quality.py                      # Reusable quality checks
└── tests/
```

## Data source

- Source: [Plotly public datasets](https://github.com/plotly/datasets)
- File: `2016-weather-data-seattle.csv`
- Download URL is stored in `src/data_quality_dashboard/data.py`.
- The raw file is not committed; use the download script so the repository stays small and the source remains explicit.

## What to improve next

1. Add a second public dataset and compare the same quality framework across sources.
2. Add a data-quality score with documented weights rather than a single pass/fail label.
3. Add an interactive year/month filter and a small anomaly review table.
4. Publish a short LinkedIn or portfolio write-up using the README's business question, findings, and limitations.

## Portfolio talking points

- I used SQL first to create a controlled analytical table, then used pandas for exploration and Plotly/Streamlit for communication.
- I checked data quality before interpreting trends: required columns, missing values, duplicates, temperature ordering, and valid ranges.
- I kept the raw source out of Git and documented how to reproduce the download.
- The next production improvement would be scheduled ingestion, quality alerts, and lineage metadata.
