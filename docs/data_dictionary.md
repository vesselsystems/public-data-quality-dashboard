# Data dictionary

Source file: `2016-weather-data-seattle.csv` from the public Plotly datasets repository.

| Field | Type after normalization | Meaning | Quality rule |
|---|---|---|---|
| `date` | date | Observation date | Required, unique, chronologically ordered |
| `max_temperature_c` | float | Daily maximum temperature in Celsius | Required; -60°C to 60°C review range |
| `mean_temperature_c` | float | Daily mean temperature in Celsius | Required; must be between min and max |
| `min_temperature_c` | float | Daily minimum temperature in Celsius | Required; -60°C to 60°C review range |

## Interpretation notes

- The range check is a review rule, not proof that every value outside the range is impossible.
- A passing quality score means the implemented checks passed; it does not guarantee that the source is free of every issue.
- Trend interpretation should account for the historical source, location, measurement process, and any missing observations.
