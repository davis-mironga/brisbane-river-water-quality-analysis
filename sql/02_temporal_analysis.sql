-- =============================================================================
-- 02_temporal_analysis.sql
-- Brisbane River Water Quality Analysis
-- =============================================================================

SELECT
    year, month,
    COUNT(*) AS reading_count,
    COUNT(DISTINCT day) AS distinct_days_with_readings
FROM water_quality
GROUP BY year, month
ORDER BY year, month;

SELECT
    year, month,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(MIN(temperature), 2) AS min_temperature,
    ROUND(MAX(temperature), 2) AS max_temperature,
    ROUND(AVG(dissolved_oxygen), 2) AS avg_dissolved_oxygen,
    ROUND(MIN(dissolved_oxygen), 2) AS min_dissolved_oxygen,
    ROUND(MAX(dissolved_oxygen), 2) AS max_dissolved_oxygen,
    ROUND(AVG(turbidity), 2) AS avg_turbidity,
    ROUND(MIN(turbidity), 2) AS min_turbidity,
    ROUND(MAX(turbidity), 2) AS max_turbidity
FROM water_quality
GROUP BY year, month
ORDER BY year, month;

SELECT
    season,
    COUNT(*) AS reading_count,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(dissolved_oxygen), 2) AS avg_dissolved_oxygen,
    ROUND(AVG(dissolved_oxygen_pct_sat), 2) AS avg_do_pct_sat,
    ROUND(AVG(salinity), 2) AS avg_salinity,
    ROUND(AVG(turbidity), 2) AS avg_turbidity,
    ROUND(AVG(ph), 2) AS avg_ph
FROM water_quality
GROUP BY season
ORDER BY CASE season WHEN 'Summer' THEN 1 WHEN 'Autumn' THEN 2 WHEN 'Winter' THEN 3 WHEN 'Spring' THEN 4 END;

SELECT
    day_of_week,
    COUNT(*) AS reading_count,
    ROUND(AVG(turbidity), 2) AS avg_turbidity,
    ROUND(AVG(dissolved_oxygen), 2) AS avg_dissolved_oxygen
FROM water_quality
GROUP BY day_of_week
ORDER BY CASE day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END;

SELECT
    hour,
    COUNT(*) AS reading_count,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(dissolved_oxygen_pct_sat), 2) AS avg_do_pct_sat
FROM water_quality
GROUP BY hour
ORDER BY hour;

WITH monthly_avg AS (
    SELECT year, month, ROUND(AVG(temperature), 2) AS avg_temperature
    FROM water_quality
    GROUP BY year, month
)
SELECT
    curr.year, curr.month, curr.avg_temperature,
    prev.avg_temperature AS prev_month_avg_temperature,
    ROUND(curr.avg_temperature - prev.avg_temperature, 2) AS change_from_prev_month
FROM monthly_avg curr
LEFT JOIN monthly_avg prev
    ON (curr.year = prev.year AND curr.month = prev.month + 1)
    OR (curr.month = 1 AND prev.month = 12 AND curr.year = prev.year + 1)
ORDER BY curr.year, curr.month;

SELECT MIN(timestamp) AS first_reading, MAX(timestamp) AS last_reading
FROM water_quality;
