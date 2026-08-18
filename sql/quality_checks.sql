-- Auditable SQL checks for the relation created by data.load_with_sql.
-- The loader creates weather_raw from the CSV's source columns. Each query
-- casts those columns to the names used by the Python quality checks.

-- Required field completeness
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

-- Logical temperature ordering
WITH weather AS (
    SELECT
        TRY_CAST("Date" AS DATE) AS date,
        TRY_CAST("Max_TemperatureC" AS DOUBLE) AS max_temperature_c,
        TRY_CAST("Mean_TemperatureC" AS DOUBLE) AS mean_temperature_c,
        TRY_CAST("Min_TemperatureC" AS DOUBLE) AS min_temperature_c
    FROM weather_raw
)
SELECT *
FROM weather
WHERE min_temperature_c > mean_temperature_c
   OR mean_temperature_c > max_temperature_c;

-- Plausible range review
WITH weather AS (
    SELECT
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
   OR min_temperature_c NOT BETWEEN -60 AND 60;

-- Chronology review in source row order. Sorting by date before this check
-- would hide a source-order problem, so rowid tracks the CSV insertion order.
WITH weather AS (
    SELECT
        rowid AS source_row_number,
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
