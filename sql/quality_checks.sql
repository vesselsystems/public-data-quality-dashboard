-- Auditable SQL checks for the normalized weather table.
-- The Streamlit app runs equivalent checks in Python so the results can be displayed.

-- Required field completeness
SELECT
    COUNT(*) AS rows_total,
    COUNT(*) FILTER (WHERE date IS NULL) AS missing_dates,
    COUNT(*) FILTER (WHERE max_temperature_c IS NULL) AS missing_max_temperature,
    COUNT(*) FILTER (WHERE mean_temperature_c IS NULL) AS missing_mean_temperature,
    COUNT(*) FILTER (WHERE min_temperature_c IS NULL) AS missing_min_temperature
FROM weather;

-- Duplicate dates
SELECT date, COUNT(*) AS rows_for_date
FROM weather
GROUP BY date
HAVING COUNT(*) > 1
ORDER BY date;

-- Logical temperature ordering
SELECT *
FROM weather
WHERE min_temperature_c > mean_temperature_c
   OR mean_temperature_c > max_temperature_c;

-- Plausible range review
SELECT *
FROM weather
WHERE max_temperature_c NOT BETWEEN -60 AND 60
   OR mean_temperature_c NOT BETWEEN -60 AND 60
   OR min_temperature_c NOT BETWEEN -60 AND 60;
