"""Data acquisition and SQL-backed analytical queries."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import duckdb
import pandas as pd

DATA_URL = "https://raw.githubusercontent.com/plotly/datasets/master/2016-weather-data-seattle.csv"
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
    """Load the source through DuckDB and return a typed analytical table."""
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
                TRY_CAST(Date AS DATE) AS date,
                TRY_CAST(Max_TemperatureC AS DOUBLE) AS max_temperature_c,
                TRY_CAST(Mean_TemperatureC AS DOUBLE) AS mean_temperature_c,
                TRY_CAST(Min_TemperatureC AS DOUBLE) AS min_temperature_c
            FROM weather_raw
            ORDER BY date
            """
        ).fetchdf()
    finally:
        connection.close()


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
