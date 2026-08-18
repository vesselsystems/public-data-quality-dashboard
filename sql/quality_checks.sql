-- Auditable SQL checks for the relation created by data.load_with_sql.
-- The loader creates weather_raw from the CSV's source columns. Each query
-- casts those columns to the names used by the Python quality checks.
-- source_row_number is one-based and preserves CSV insertion order.

-- Required field completeness and non-empty input
WITH weather AS (
    SELECT
        TRY_CAST("Date" AS DATE) AS date,
        TRY_CAST("Max_TemperatureC" AS DOUBLE) AS max_temperature_c,
        TRY_CAST("Mean_TemperatureC" AS DOUBLE) AS mean_temperature_c,
        TRY_CAST("Min_TemperatureC" AS DOUBLE) AS min_temperature_c
    FROM weather_raw
)
SELECT
    COUNT(*) AS rows_total,
    COUNT(*) > 0 AS non_empty_dataset,
    COUNT(*) FILTER (WHERE date IS NULL) AS missing_dates,
    COUNT(*) FILTER (WHERE max_temperature_c IS NULL) AS missing_max_temperature,
    COUNT(*) FILTER (WHERE mean_temperature_c IS NULL) AS missing_mean_temperature,
    COUNT(*) FILTER (WHERE min_temperature_c IS NULL) AS missing_min_temperature
FROM weather;

-- Duplicate dates
WITH weather AS (
    SELECT TRY_CAST("Date" AS DATE) AS date
    FROM weather_raw
)
SELECT date, COUNT(*) AS rows_for_date
FROM weather
GROUP BY date
HAVING COUNT(*) > 1
ORDER BY date;

-- Logical temperature ordering / anomaly review table
WITH weather AS (
    SELECT
        rowid + 1 AS source_row_number,
        TRY_CAST("Date" AS DATE) AS date,
        TRY_CAST("Max_TemperatureC" AS DOUBLE) AS max_temperature_c,
        TRY_CAST("Mean_TemperatureC" AS DOUBLE) AS mean_temperature_c,
        TRY_CAST("Min_TemperatureC" AS DOUBLE) AS min_temperature_c
    FROM weather_raw
)
SELECT
    'temperature_order' AS anomaly_type,
    source_row_number,
    date,
    max_temperature_c,
    mean_temperature_c,
    min_temperature_c
FROM weather
WHERE min_temperature_c > mean_temperature_c
   OR mean_temperature_c > max_temperature_c
ORDER BY source_row_number;

-- Plausible range review
WITH weather AS (
    SELECT
        rowid + 1 AS source_row_number,
        TRY_CAST("Date" AS DATE) AS date,
        TRY_CAST("Max_TemperatureC" AS DOUBLE) AS max_temperature_c,
        TRY_CAST("Mean_TemperatureC" AS DOUBLE) AS mean_temperature_c,
        TRY_CAST("Min_TemperatureC" AS DOUBLE) AS min_temperature_c
    FROM weather_raw
)
SELECT *
FROM weather
WHERE max_temperature_c NOT BETWEEN -60 AND 60
   OR mean_temperature_c NOT BETWEEN -60 AND 60
   OR min_temperature_c NOT BETWEEN -60 AND 60
ORDER BY source_row_number;

-- Strict calendar coverage summary. Python applies the same policy: every
-- distinct date between the valid minimum and maximum must be present, and
-- invalid dates cause the check to fail.
WITH weather AS (
    SELECT TRY_CAST("Date" AS DATE) AS date
    FROM weather_raw
), observed_dates AS (
    SELECT DISTINCT date
    FROM weather
    WHERE date IS NOT NULL
), bounds AS (
    SELECT MIN(date) AS date_min, MAX(date) AS date_max
    FROM observed_dates
), expected_dates AS (
    SELECT CAST(generated_date AS DATE) AS date
    FROM bounds,
    LATERAL generate_series(
        bounds.date_min,
        bounds.date_max,
        INTERVAL '1 day'
    ) AS generated(generated_date)
)
SELECT
    (SELECT date_min FROM bounds) AS date_min,
    (SELECT date_max FROM bounds) AS date_max,
    (SELECT COUNT(*) FROM weather WHERE date IS NULL) AS invalid_dates,
    COUNT(*) AS expected_days,
    COUNT(observed_dates.date) AS observed_days,
    COUNT(*) FILTER (WHERE observed_dates.date IS NULL) AS missing_days
FROM expected_dates
LEFT JOIN observed_dates USING (date);

-- Missing calendar years and long gaps support the coverage summary above.
WITH weather AS (
    SELECT TRY_CAST("Date" AS DATE) AS date
    FROM weather_raw
), observed_dates AS (
    SELECT DISTINCT date
    FROM weather
    WHERE date IS NOT NULL
), bounds AS (
    SELECT MIN(date) AS date_min, MAX(date) AS date_max
    FROM observed_dates
), expected_dates AS (
    SELECT CAST(generated_date AS DATE) AS date
    FROM bounds,
    LATERAL generate_series(
        bounds.date_min,
        bounds.date_max,
        INTERVAL '1 day'
    ) AS generated(generated_date)
), missing_dates AS (
    SELECT expected_dates.date
    FROM expected_dates
    LEFT JOIN observed_dates USING (date)
    WHERE observed_dates.date IS NULL
)
SELECT EXTRACT(YEAR FROM date)::INTEGER AS missing_year, COUNT(*) AS missing_days
FROM missing_dates
GROUP BY 1
ORDER BY 1;

WITH weather AS (
    SELECT DISTINCT TRY_CAST("Date" AS DATE) AS date
    FROM weather_raw
    WHERE TRY_CAST("Date" AS DATE) IS NOT NULL
), ordered_dates AS (
    SELECT
        date,
        LAG(date) OVER (ORDER BY date) AS previous_date
    FROM weather
)
SELECT
    COUNT(*) FILTER (WHERE DATE_DIFF('day', previous_date, date) > 1) AS multi_day_gaps,
    COALESCE(MAX(DATE_DIFF('day', previous_date, date)), 0) AS max_gap_days
FROM ordered_dates;

-- Chronology review in source row order. Sorting by date before this check
-- would hide a source-order problem, so rowid tracks the CSV insertion order.
WITH weather AS (
    SELECT
        rowid + 1 AS source_row_number,
        TRY_CAST("Date" AS DATE) AS date
    FROM weather_raw
), with_previous_date AS (
    SELECT
        source_row_number,
        LAG(date) OVER (ORDER BY source_row_number) AS previous_date,
        date
    FROM weather
)
SELECT source_row_number, previous_date, date
FROM with_previous_date
WHERE previous_date > date
ORDER BY source_row_number;
