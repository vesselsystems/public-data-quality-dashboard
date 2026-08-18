"""Data acquisition and SQL-backed analytical queries."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import duckdb
import pandas as pd

from .quality import calendar_coverage, temperature_order_anomalies

DATA_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/"
    "0c447c47b757ad74edecab31f0d72f849d2e67c2/2016-weather-data-seattle.csv"
)
SOURCE_FILE = "2016-weather-data-seattle.csv"
PROVENANCE_FILENAME = "provenance.json"
REQUIRED_COLUMNS = [
    "Date",
    "Max_TemperatureC",
    "Mean_TemperatureC",
    "Min_TemperatureC",
]


def download_dataset(destination: Path, url: str = DATA_URL) -> Path:
    """Download the public CSV to *destination* and return its path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=30) as response:  # noqa: S310 - URL is a project constant
        destination.write_bytes(response.read())
    return destination


def read_weather_csv(path: Path) -> pd.DataFrame:
    """Read and normalize the source CSV without hiding source-level issues."""
    frame = pd.read_csv(path)
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in REQUIRED_COLUMNS[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def load_with_sql(path: Path) -> pd.DataFrame:
    """Load the source through DuckDB in source row order.

    The quality checks need to see the source order to detect a backward date
    transition. Sorting by date in this loader would make that check vacuous,
    so callers should sort a copy only after validation. The returned
    ``source_row_number`` is a one-based CSV data-row position for review.
    """
    connection = duckdb.connect()
    try:
        connection.execute(
            """
            CREATE OR REPLACE TABLE weather_raw AS
            SELECT * FROM read_csv_auto(?, HEADER = TRUE)
            """,
            [str(path)],
        )
        return connection.execute(
            """
            SELECT
                rowid + 1 AS source_row_number,
                TRY_CAST(Date AS DATE) AS date,
                TRY_CAST(Max_TemperatureC AS DOUBLE) AS max_temperature_c,
                TRY_CAST(Mean_TemperatureC AS DOUBLE) AS mean_temperature_c,
                TRY_CAST(Min_TemperatureC AS DOUBLE) AS min_temperature_c
            FROM weather_raw
            ORDER BY rowid
            """
        ).fetchdf()
    finally:
        connection.close()


def write_provenance(
    path: Path,
    *,
    source_url: str = DATA_URL,
    retrieved_at: datetime | None = None,
) -> Path:
    """Write reproducibility metadata for a downloaded local snapshot."""
    frame = read_weather_csv(path)
    normalized = frame.rename(
        columns={
            "Date": "date",
            "Max_TemperatureC": "max_temperature_c",
            "Mean_TemperatureC": "mean_temperature_c",
            "Min_TemperatureC": "min_temperature_c",
        }
    )
    dates = normalized["date"].dropna().sort_values()
    coverage = calendar_coverage(normalized)
    anomalies = temperature_order_anomalies(normalized)
    numeric = [
        "max_temperature_c",
        "mean_temperature_c",
        "min_temperature_c",
    ]
    out_of_range = int(
        ((normalized[numeric] < -60) | (normalized[numeric] > 60)).any(axis=1).sum()
    )
    date_order_violations = int(
        normalized["date"].diff().dropna().lt(pd.Timedelta(0)).sum()
    )
    metadata = {
        "source": {
            "publisher": "Plotly datasets repository",
            "repository_url": "https://github.com/plotly/datasets",
            "file": SOURCE_FILE,
            "url": source_url,
            "upstream_ref": "0c447c47b757ad74edecab31f0d72f849d2e67c2",
            "retrieval_script": "scripts/download_data.py",
            "license_or_terms": (
                "Not independently verified in this project; consult the publisher's "
                "repository terms before redistribution."
            ),
            "license_or_terms_url": "https://github.com/plotly/datasets",
        },
        "local_snapshot": {
            "path": _relative_project_path(path),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            "retrieved_at_utc": retrieved_at.isoformat() if retrieved_at else None,
            "metadata_generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_columns": list(frame.columns),
            "row_count": len(frame),
            "date_min": dates.min().date().isoformat() if not dates.empty else None,
            "date_max": dates.max().date().isoformat() if not dates.empty else None,
        },
        "quality_observations": {
            "missing_values_by_field": {
                column: int(frame[column].isna().sum()) for column in REQUIRED_COLUMNS
            },
            "duplicate_dates": int(frame["Date"].duplicated().sum()),
            "temperature_order_violations": len(anomalies),
            "temperature_range_violations": out_of_range,
            "backward_date_order_violations": date_order_violations,
            "multi_day_gaps_after_sorting": coverage.multi_day_gaps,
            "calendar_coverage": {
                "expected_days": coverage.expected_days,
                "observed_days": coverage.observed_days,
                "missing_days": coverage.missing_days,
                "missing_years": list(coverage.missing_years),
                "max_gap_days": coverage.max_gap_days,
                "invalid_dates": coverage.invalid_dates,
            },
        },
    }
    destination = path.with_name(PROVENANCE_FILENAME)
    destination.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return destination


def _relative_project_path(path: Path) -> str:
    """Return a portable path for metadata instead of a machine-specific path."""
    project_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def yearly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Create an annual summary using DuckDB SQL."""
    connection = duckdb.connect()
    try:
        connection.register("weather", frame)
        return connection.execute(
            """
            SELECT
                EXTRACT(YEAR FROM date)::INTEGER AS year,
                COUNT(*) AS observations,
                ROUND(AVG(mean_temperature_c), 2) AS avg_mean_temperature_c,
                ROUND(MIN(min_temperature_c), 2) AS coldest_temperature_c,
                ROUND(MAX(max_temperature_c), 2) AS hottest_temperature_c
            FROM weather
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchdf()
    finally:
        connection.close()
