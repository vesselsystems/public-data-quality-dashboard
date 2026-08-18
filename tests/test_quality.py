from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from data_quality_dashboard.data import load_with_sql
from data_quality_dashboard.quality import (
    calendar_coverage,
    quality_score,
    run_quality_checks,
    temperature_order_anomalies,
)


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 2)],
            "max_temperature_c": [10.0, 12.0],
            "mean_temperature_c": [7.0, 8.0],
            "min_temperature_c": [4.0, 5.0],
        }
    )


def test_valid_frame_passes_all_checks() -> None:
    checks = run_quality_checks(valid_frame())

    assert all(check.passed for check in checks)
    assert quality_score(checks) == 100


def test_quality_checks_catch_bad_rows() -> None:
    frame = valid_frame()
    frame.loc[1, "mean_temperature_c"] = 20.0
    frame.loc[1, "min_temperature_c"] = 80.0
    frame.loc[0, "date"] = frame.loc[1, "date"]

    checks = run_quality_checks(frame)
    failed_names = {check.name for check in checks if not check.passed}

    assert {"duplicate_dates", "temperature_order", "temperature_range"} <= failed_names
    assert quality_score(checks) < 100


def test_calendar_coverage_catches_missing_days() -> None:
    frame = valid_frame()
    frame.loc[1, "date"] = date(2024, 1, 3)

    coverage = calendar_coverage(frame)
    checks = run_quality_checks(frame)
    calendar_check = next(check for check in checks if check.name == "calendar_coverage")

    assert coverage.expected_days == 3
    assert coverage.observed_days == 2
    assert coverage.missing_days == 1
    assert coverage.multi_day_gaps == 1
    assert calendar_check.passed is False
    assert "1 missing calendar day" in calendar_check.detail
    # Calendar coverage is supplemental; it must not silently redefine the
    # historical core-check score.
    assert quality_score(checks) == 100


def test_calendar_coverage_reports_missing_year() -> None:
    frame = pd.DataFrame(
        {
            "date": [date(2024, 12, 31), date(2026, 1, 1)],
            "max_temperature_c": [10.0, 11.0],
            "mean_temperature_c": [7.0, 8.0],
            "min_temperature_c": [4.0, 5.0],
        }
    )

    coverage = calendar_coverage(frame)

    assert coverage.missing_years == (2025,)
    assert coverage.missing_days == 365


def test_temperature_order_anomaly_review_keeps_source_row() -> None:
    frame = valid_frame()
    frame["source_row_number"] = [17, 18]
    frame.loc[1, "mean_temperature_c"] = 20.0

    review = temperature_order_anomalies(frame)

    assert review.columns.tolist() == [
        "anomaly_type",
        "source_row_number",
        "date",
        "max_temperature_c",
        "mean_temperature_c",
        "min_temperature_c",
    ]
    assert review["source_row_number"].tolist() == [18]
    assert review["anomaly_type"].tolist() == ["temperature_order"]


def test_sql_artifact_contains_the_python_review_paths() -> None:
    sql = Path(__file__).parents[1].joinpath("sql", "quality_checks.sql").read_text(
        encoding="utf-8"
    )

    assert "generate_series" in sql
    assert "missing_days" in sql
    assert "temperature_order" in sql
    assert "rowid + 1 AS source_row_number" in sql


def test_sql_anomaly_and_coverage_results_match_python(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text(
        "Date,Max_TemperatureC,Mean_TemperatureC,Min_TemperatureC\n"
        "2024-01-01,10,7,4\n"
        "2024-01-03,8,9,7\n",
        encoding="utf-8",
    )
    frame = load_with_sql(source)
    python_review = temperature_order_anomalies(frame)
    sql = Path(__file__).parents[1].joinpath("sql", "quality_checks.sql").read_text(
        encoding="utf-8"
    )
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]

    connection = duckdb.connect()
    try:
        connection.execute(
            "CREATE OR REPLACE TABLE weather_raw AS "
            "SELECT * FROM read_csv_auto(?, HEADER = TRUE)",
            [str(source)],
        )
        sql_review = connection.execute(statements[2]).fetchdf()
        sql_coverage = connection.execute(statements[4]).fetchdf().iloc[0]
    finally:
        connection.close()

    assert sql_review.to_dict("records") == python_review.to_dict("records")
    assert sql_coverage["expected_days"] == 3
    assert sql_coverage["observed_days"] == 2
    assert sql_coverage["missing_days"] == 1


def test_sql_loader_preserves_source_order_for_chronology_check(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text(
        "Date,Max_TemperatureC,Mean_TemperatureC,Min_TemperatureC\n"
        "2024-01-02,10,7,4\n"
        "2024-01-01,12,8,5\n",
        encoding="utf-8",
    )

    frame = load_with_sql(source)
    checks = run_quality_checks(frame)
    chronology = next(check for check in checks if check.name == "chronological_order")

    assert frame["source_row_number"].tolist() == [1, 2]
    assert frame["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2024-01-02",
        "2024-01-01",
    ]
    assert chronology.passed is False
    assert chronology.detail == "1 backward date transitions in source row order."


def test_missing_columns_are_reported() -> None:
    checks = run_quality_checks(valid_frame().drop(columns=["min_temperature_c"]))

    assert checks[0].name == "required_columns"
    assert checks[0].passed is False
    assert "min_temperature_c" in checks[0].detail
