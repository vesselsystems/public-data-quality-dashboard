"""Data-quality checks that are easy to audit and test."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

NORMALIZED_FIELDS = (
    "date",
    "max_temperature_c",
    "mean_temperature_c",
    "min_temperature_c",
)
TEMPERATURE_FIELDS = NORMALIZED_FIELDS[1:]


@dataclass(frozen=True)
class QualityCheck:
    """One named quality assertion and its human-readable evidence."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CalendarCoverage:
    """Coverage measurements for the inclusive daily range in the source."""

    date_min: pd.Timestamp | None
    date_max: pd.Timestamp | None
    expected_days: int
    observed_days: int
    missing_days: int
    missing_years: tuple[int, ...]
    multi_day_gaps: int
    max_gap_days: int
    invalid_dates: int

    @property
    def is_complete(self) -> bool:
        """Whether every day in the observed range has one parseable date."""
        return (
            self.observed_days > 0
            and self.invalid_dates == 0
            and self.missing_days == 0
        )


def calendar_coverage(frame: pd.DataFrame) -> CalendarCoverage:
    """Measure daily coverage between the minimum and maximum valid dates.

    The check is deliberately strict: every calendar day in the inclusive
    observed range must be present.  Duplicate dates are measured separately,
    so ``observed_days`` counts distinct valid dates here.
    """
    dates = pd.to_datetime(frame["date"], errors="coerce")
    invalid_dates = int(dates.isna().sum())
    valid_dates = dates.dropna().dt.normalize().drop_duplicates().sort_values()

    if valid_dates.empty:
        return CalendarCoverage(
            date_min=None,
            date_max=None,
            expected_days=0,
            observed_days=0,
            missing_days=0,
            missing_years=(),
            multi_day_gaps=0,
            max_gap_days=0,
            invalid_dates=invalid_dates,
        )

    observed = pd.DatetimeIndex(valid_dates)
    date_min = observed[0]
    date_max = observed[-1]
    expected = pd.date_range(date_min, date_max, freq="D")
    gaps = valid_dates.diff().dropna()
    expected_years = set(range(int(date_min.year), int(date_max.year) + 1))
    observed_years = {int(year) for year in observed.year}

    return CalendarCoverage(
        date_min=date_min,
        date_max=date_max,
        expected_days=len(expected),
        observed_days=len(observed),
        missing_days=len(expected.difference(observed)),
        missing_years=tuple(sorted(expected_years - observed_years)),
        multi_day_gaps=int((gaps > pd.Timedelta(days=1)).sum()),
        max_gap_days=int(gaps.dt.days.max()) if not gaps.empty else 0,
        invalid_dates=invalid_dates,
    )


def temperature_order_anomalies(frame: pd.DataFrame) -> pd.DataFrame:
    """Return rows that violate ``min <= mean <= max`` for review.

    ``source_row_number`` is supplied by :func:`load_with_sql` for the
    dashboard path.  For a standalone frame, the one-based frame position is
    used so tests and exploratory callers still receive a stable review key.
    Missing values are not classified as ordering anomalies; they are covered
    by the separate missing-values check.
    """
    review_columns = ["date", *TEMPERATURE_FIELDS]
    output_columns = ["anomaly_type", "source_row_number", *review_columns]
    missing_columns = sorted(set(review_columns) - set(frame.columns))
    if missing_columns:
        return pd.DataFrame(columns=output_columns)

    numeric = frame[list(TEMPERATURE_FIELDS)].apply(pd.to_numeric, errors="coerce")
    anomaly_mask = (
        (numeric["min_temperature_c"] > numeric["mean_temperature_c"])
        | (numeric["mean_temperature_c"] > numeric["max_temperature_c"])
    )
    dates = pd.to_datetime(frame["date"], errors="coerce")
    source_rows = frame.get("source_row_number")
    if source_rows is None:
        source_rows = pd.Series(range(1, len(frame) + 1), index=frame.index)

    review = frame.loc[anomaly_mask, review_columns].copy()
    review["date"] = dates.loc[anomaly_mask]
    review.insert(0, "anomaly_type", "temperature_order")
    review.insert(1, "source_row_number", source_rows.loc[anomaly_mask].to_numpy())
    return review.reset_index(drop=True)[output_columns]


def _calendar_detail(coverage: CalendarCoverage) -> str:
    if coverage.observed_days == 0:
        return f"No valid dates; {coverage.invalid_dates:,} invalid date values."

    date_range = (
        f"{coverage.date_min.strftime('%Y-%m-%d')} through "
        f"{coverage.date_max.strftime('%Y-%m-%d')}"
    )
    if coverage.is_complete:
        return f"Complete daily coverage from {date_range} ({coverage.expected_days:,} days)."

    detail = (
        f"{coverage.missing_days:,} missing calendar days across "
        f"{coverage.multi_day_gaps:,} gaps between {date_range}."
    )
    if coverage.missing_years:
        years = ", ".join(str(year) for year in coverage.missing_years)
        detail += f" Missing calendar years: {years}."
    if coverage.invalid_dates:
        detail += f" {coverage.invalid_dates:,} invalid date values."
    return detail


def run_quality_checks(frame: pd.DataFrame) -> list[QualityCheck]:
    """Run deterministic checks before any trend is interpreted."""
    expected = set(NORMALIZED_FIELDS)
    missing_columns = sorted(expected - set(frame.columns))

    if missing_columns:
        return [
            QualityCheck(
                "required_columns",
                False,
                f"Missing columns: {', '.join(missing_columns)}",
            )
        ]

    dates = pd.to_datetime(frame["date"], errors="coerce")
    numeric = frame[list(TEMPERATURE_FIELDS)].apply(pd.to_numeric, errors="coerce")
    missing_values = int(dates.isna().sum() + numeric.isna().sum().sum())
    duplicate_dates = int(dates.duplicated().sum())
    invalid_order = int(
        (
            (numeric["min_temperature_c"] > numeric["mean_temperature_c"])
            | (numeric["mean_temperature_c"] > numeric["max_temperature_c"])
        ).sum()
    )
    out_of_range = int(
        ((numeric < -60) | (numeric > 60)).any(axis=1).sum()
    )
    date_order_violations = int(
        dates.diff().lt(pd.Timedelta(0)).fillna(False).sum()
    )
    coverage = calendar_coverage(frame)

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
        QualityCheck(
            "calendar_coverage",
            coverage.is_complete,
            _calendar_detail(coverage),
        ),
    ]


def quality_score(checks: list[QualityCheck]) -> int:
    """Return the original core-check score, rounded down.

    Calendar coverage is reported as a supplemental check because adding it to
    this denominator would silently change the meaning of the score used by
    earlier runs.  The dashboard therefore shows both the historical score and
    the separate coverage result.
    """
    scored_checks = [check for check in checks if check.name != "calendar_coverage"]
    if not scored_checks:
        return 0
    return int(100 * sum(check.passed for check in scored_checks) / len(scored_checks))
