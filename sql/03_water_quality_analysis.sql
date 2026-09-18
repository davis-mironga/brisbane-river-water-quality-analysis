-- =============================================================================
-- 03_water_quality_analysis.sql
-- Brisbane River Water Quality Analysis
-- =============================================================================

SELECT
    CASE
        WHEN dissolved_oxygen < 4 THEN 'Low (< 4 mg/L)'
        WHEN dissolved_oxygen < 6 THEN 'Moderate (4-6 mg/L)'
        WHEN dissolved_oxygen < 8 THEN 'Good (6-8 mg/L)'
        ELSE 'High (>= 8 mg/L)'
    END AS oxygen_band,
    COUNT(*) AS reading_count
FROM water_quality
WHERE dissolved_oxygen IS NOT NULL
GROUP BY oxygen_band
ORDER BY reading_count DESC;

SELECT
    year, month,
    COUNT(*) AS high_turbidity_readings
FROM water_quality
WHERE turbidity > 20
GROUP BY year, month
ORDER BY year, month;

SELECT
    season,
    COUNT(*) AS reading_count,
    ROUND(AVG(ph), 3) AS avg_ph,
    ROUND(MIN(ph), 3) AS min_ph,
    ROUND(MAX(ph), 3) AS max_ph
FROM water_quality
WHERE hour >= 6 AND hour < 18 AND ph IS NOT NULL
GROUP BY season
ORDER BY avg_ph DESC;

SELECT
    year, month,
    ROUND(AVG(turbidity), 2) AS avg_turbidity
FROM water_quality
WHERE turbidity IS NOT NULL
GROUP BY year, month
HAVING AVG(turbidity) > (
    SELECT AVG(turbidity) * 2 FROM water_quality WHERE turbidity IS NOT NULL
)
ORDER BY avg_turbidity DESC;

SELECT
    season,
    CASE
        WHEN salinity < 0.5  THEN 'Freshwater (< 0.5)'
        WHEN salinity < 30   THEN 'Brackish (0.5-30)'
        ELSE 'Saline (>= 30)'
    END AS salinity_class,
    COUNT(*) AS reading_count
FROM water_quality
WHERE salinity IS NOT NULL
GROUP BY season, salinity_class
ORDER BY season, reading_count DESC;

SELECT
    year, month, day,
    COUNT(*) AS reading_count,
    ROUND(AVG(dissolved_oxygen), 2) AS avg_dissolved_oxygen
FROM water_quality
WHERE dissolved_oxygen IS NOT NULL
GROUP BY year, month, day
HAVING COUNT(*) >= 40 AND AVG(dissolved_oxygen) < 6
ORDER BY avg_dissolved_oxygen ASC;

SELECT
    season,
    COUNT(*) AS total_readings,
    SUM(CASE WHEN temperature < 15 OR temperature > 30 THEN 1 ELSE 0 END) AS atypical_temp_readings,
    ROUND(
        100.0 * SUM(CASE WHEN temperature < 15 OR temperature > 30 THEN 1 ELSE 0 END)
        / COUNT(*), 2
    ) AS atypical_temp_pct
FROM water_quality
WHERE temperature IS NOT NULL
GROUP BY season
ORDER BY atypical_temp_pct DESC;
