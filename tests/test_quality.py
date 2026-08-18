from datetime import date
from pathlib import Path

import pandas as pd

from data_quality_dashboard.data import load_with_sql
from data_quality_dashboard.quality import quality_score, run_quality_checks


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
