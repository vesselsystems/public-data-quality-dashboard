"""Data-quality checks that are easy to audit and test."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class QualityCheck:
    """One named quality assertion and its human-readable evidence."""

    name: str
    passed: bool
    detail: str


def run_quality_checks(frame: pd.DataFrame) -> list[QualityCheck]:
    """Run deterministic checks before any trend is interpreted."""
    expected = {"date", "max_temperature_c", "mean_temperature_c", "min_temperature_c"}
    missing_columns = sorted(expected - set(frame.columns))

    if missing_columns:
        return [
            QualityCheck(
                "required_columns",
                False,
                f"Missing columns: {', '.join(missing_columns)}",
            )
        ]

    numeric = ["max_temperature_c", "mean_temperature_c", "min_temperature_c"]
    missing_values = int(frame[list(expected)].isna().sum().sum())
    duplicate_dates = int(frame["date"].duplicated().sum())
    invalid_order = int(
        (
            (frame["min_temperature_c"] > frame["mean_temperature_c"])
            | (frame["mean_temperature_c"] > frame["max_temperature_c"])
        ).sum()
    )
    out_of_range = int(
        ((frame[numeric] < -60) | (frame[numeric] > 60)).any(axis=1).sum()
    )
    dates = pd.to_datetime(frame["date"], errors="coerce")
    date_order_violations = int(
        dates.diff().lt(pd.Timedelta(0)).fillna(False).sum()
    )

    return [
        QualityCheck(
            "required_columns",
            True,
            "All expected fields are present.",
        ),
        QualityCheck(
            "non_empty_dataset",
            len(frame) > 0,
            f"{len(frame):,} rows loaded.",
        ),
        QualityCheck(
            "missing_values",
            missing_values == 0,
            f"{missing_values:,} missing cells across required fields.",
        ),
        QualityCheck(
            "duplicate_dates",
            duplicate_dates == 0,
            f"{duplicate_dates:,} duplicate dates.",
        ),
        QualityCheck(
            "temperature_order",
            invalid_order == 0,
            f"{invalid_order:,} rows violate min <= mean <= max.",
        ),
        QualityCheck(
            "temperature_range",
            out_of_range == 0,
            f"{out_of_range:,} rows fall outside -60°C to 60°C.",
        ),
        QualityCheck(
            "chronological_order",
            date_order_violations == 0,
            f"{date_order_violations:,} backward date transitions in source row order.",
        ),
    ]


def quality_score(checks: list[QualityCheck]) -> int:
    """Return the percentage of passed checks, rounded down."""
    if not checks:
        return 0
    return int(100 * sum(check.passed for check in checks) / len(checks))
