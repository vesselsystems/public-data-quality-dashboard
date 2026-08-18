# Data dictionary

## Source and snapshot

- Publisher/repository: [Plotly datasets](https://github.com/plotly/datasets)
- Upstream file: `2016-weather-data-seattle.csv`
- Local file: `data/raw/seattle_weather.csv`
- Local relation: `weather_raw` in the transient DuckDB connection created by `load_with_sql`
- Snapshot metadata: [`data/raw/provenance.json`](../data/raw/provenance.json)

The download is pinned to Plotly datasets commit `0c447c47b757ad74edecab31f0d72f849d2e67c2`. The provenance file records the local file hash, retrieval time, and measurements so a later download can be distinguished from the snapshot described here. The upstream license or terms have not been independently verified in this project; consult the publisher's repository before redistribution.

## Source fields and normalized fields

DuckDB reads the source fields into `weather_raw`. `load_with_sql` applies `TRY_CAST`; a failed cast becomes `NULL` and is then visible to the missing-value check.

| Source field | Normalized field | Type after normalization | Meaning |
|---|---|---|---|
| `Date` | `date` | date | Observation date |
| `Max_TemperatureC` | `max_temperature_c` | double | Reported daily maximum temperature in °C |
| `Mean_TemperatureC` | `mean_temperature_c` | double | Reported daily mean temperature in °C |
| `Min_TemperatureC` | `min_temperature_c` | double | Reported daily minimum temperature in °C |

The project uses the source labels and does not independently verify the station, instrument, or calculation method behind them. The loader also adds `source_row_number`, a one-based row position from the CSV, so chronology and anomaly reviews can point back to source order.

## Quality rules

| Check | Implementation | Local snapshot result |
|---|---|---:|
| Required columns | All four normalized fields must be present | Pass |
| Non-empty dataset | At least one row must load | Pass; 24,381 rows |
| Missing values | Count nulls across the four required fields | **Fail; 6 cells** (5 mean, 1 min) |
| Duplicate dates | Count repeated values in `date` | Pass; 0 duplicates |
| Temperature ordering | Each non-null comparison must satisfy `min <= mean <= max` | **Fail; 34 rows** |
| Temperature range | Review any temperature outside inclusive -60°C to 60°C | Pass; 0 rows outside |
| Chronological order | Count backward date transitions in the original source row order | Pass; 0 transitions |
| Calendar coverage | Require every distinct day from the valid minimum through maximum date; invalid dates fail | **Fail; 456 missing days across 8 gaps**, including missing year 2011 |

The core quality score is the floor of passed original checks divided by the original seven-check denominator. For this snapshot, 5 of 7 core checks pass, producing 71%. Calendar coverage is an explicit supplemental check and is not added to that denominator, so the score remains comparable with earlier runs. It is not a probability of correctness.

## Measured coverage notes

The local snapshot has parsed dates from `1948-01-01` through `2015-12-31`. It has no null dates and no duplicate dates, but it is not a complete daily calendar:

- The inclusive range contains 24,837 expected days; 24,381 distinct dates are present, leaving 456 missing days.
- 2011 has no observations, accounting for 365 missing days.
- 2000 has 275 observations rather than 366, accounting for 91 missing days.
- There are 8 gaps longer than one day after sorting the available dates; the longest observed-date gap is 366 days.

The chronology rule checks ordering only. It does not treat a missing day or missing year as an ordering violation. Calendar coverage is now an explicit, separate check implemented in `calendar_coverage`.

## Anomaly review path

The 34 temperature-order violations are exposed by `temperature_order_anomalies` and the dashboard path **Quality checks → Temperature-order anomaly review**. The table includes the source row number, date, three reported temperatures, and the anomaly type; it can be downloaded as CSV. The matching query is in [`sql/quality_checks.sql`](../sql/quality_checks.sql). This is a review path, not an exclusion policy: the project does not silently swap, delete, or impute these rows.

## Interpretation notes

- The -60°C to 60°C range is a review rule, not proof that values inside it are valid.
- A passing check means only that the implemented assertion passed for this snapshot.
- Descriptive charts and annual summaries should be read with the missing values, ordering violations, and coverage gaps in view.
