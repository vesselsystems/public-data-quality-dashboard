# Data dictionary

## Source and snapshot

- Publisher/repository: [Plotly datasets](https://github.com/plotly/datasets)
- Upstream file: `2016-weather-data-seattle.csv`
- Local file: `data/raw/seattle_weather.csv`
- Local relation: `weather_raw` in the transient DuckDB connection created by `load_with_sql`
- Snapshot metadata: [`data/raw/provenance.json`](../data/raw/provenance.json)

The download is pinned to Plotly datasets commit `0c447c47b757ad74edecab31f0d72f849d2e67c2`. The provenance file records the local file hash, retrieval time, and measurements so a later download can be distinguished from the snapshot described here.

## Source fields and normalized fields

DuckDB reads the source fields into `weather_raw`. `load_with_sql` applies `TRY_CAST`; a failed cast becomes `NULL` and is then visible to the missing-value check.

| Source field | Normalized field | Type after normalization | Meaning |
|---|---|---|---|
| `Date` | `date` | date | Observation date |
| `Max_TemperatureC` | `max_temperature_c` | double | Reported daily maximum temperature in °C |
| `Mean_TemperatureC` | `mean_temperature_c` | double | Reported daily mean temperature in °C |
| `Min_TemperatureC` | `min_temperature_c` | double | Reported daily minimum temperature in °C |

The project uses the source labels and does not independently verify the station, instrument, or calculation method behind them.

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

The quality score is the floor of passed checks divided by all checks. For this snapshot, 5 of 7 checks pass, producing 71%. It is not a probability of correctness.

## Measured coverage notes

The local snapshot has parsed dates from `1948-01-01` through `2015-12-31`. It has no null dates and no duplicate dates, but it is not a complete daily calendar:

- 2011 has no observations.
- 2000 has 275 observations rather than 365 or 366.
- There are 8 gaps longer than one day after sorting the available dates (including the gap across the missing 2011 period).

The chronology rule checks ordering only. It does not treat a missing day or missing year as an ordering violation; calendar coverage is a separate follow-up check.

## Interpretation notes

- The -60°C to 60°C range is a review rule, not proof that values inside it are valid.
- The 34 ordering violations are surfaced as source evidence; this project does not silently swap, delete, or impute temperature fields.
- A passing check means only that the implemented assertion passed for this snapshot.
- Descriptive charts and annual summaries should be read with the missing values, ordering violations, and coverage gaps in view.
