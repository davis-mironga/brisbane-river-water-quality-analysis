-- =============================================================================
-- 04_environmental_insights.sql
-- Brisbane River Water Quality Analysis
-- =============================================================================

WITH daily_turbidity AS (
    SELECT DATE(timestamp) AS reading_date, ROUND(AVG(turbidity), 2) AS avg_turbidity
    FROM water_quality
    WHERE turbidity IS NOT NULL
    GROUP BY DATE(timestamp)
)
SELECT
    reading_date,
    avg_turbidity,
    ROUND(AVG(avg_turbidity) OVER (ORDER BY reading_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_7day_avg_turbidity
FROM daily_turbidity
ORDER BY reading_date;

WITH daily_turbidity AS (
    SELECT DATE(timestamp) AS reading_date, AVG(turbidity) AS avg_turbidity
    FROM water_quality
    WHERE turbidity IS NOT NULL
    GROUP BY DATE(timestamp)
),
stats AS (
    SELECT
        AVG(avg_turbidity) AS overall_mean,
        SQRT(AVG((avg_turbidity - (SELECT AVG(avg_turbidity) FROM daily_turbidity)) *
                  (avg_turbidity - (SELECT AVG(avg_turbidity) FROM daily_turbidity)))) AS overall_stddev
    FROM daily_turbidity
)
SELECT
    d.reading_date,
    ROUND(d.avg_turbidity, 2) AS avg_turbidity,
    ROUND(s.overall_mean, 2) AS dataset_mean_turbidity,
    ROUND((d.avg_turbidity - s.overall_mean) / s.overall_stddev, 2) AS z_score
FROM daily_turbidity d
CROSS JOIN stats s
WHERE (d.avg_turbidity - s.overall_mean) / s.overall_stddev > 3
ORDER BY z_score DESC;

SELECT
    year, month,
    ROUND(AVG(turbidity), 2) AS avg_turbidity,
    RANK() OVER (ORDER BY AVG(turbidity) DESC) AS turbidity_rank
FROM water_quality
WHERE turbidity IS NOT NULL
GROUP BY year, month
ORDER BY turbidity_rank;

SELECT
    timestamp,
    turbidity,
    ROUND(AVG(turbidity) OVER (PARTITION BY DATE(timestamp)), 2) AS day_avg_turbidity,
    ROUND(turbidity - AVG(turbidity) OVER (PARTITION BY DATE(timestamp)), 2) AS deviation_from_day_avg
FROM water_quality
WHERE turbidity IS NOT NULL
ORDER BY deviation_from_day_avg DESC
LIMIT 15;

WITH daily_do AS (
    SELECT DATE(timestamp) AS reading_date, AVG(dissolved_oxygen) AS avg_do
    FROM water_quality
    WHERE dissolved_oxygen IS NOT NULL
    GROUP BY DATE(timestamp)
)
SELECT
    reading_date,
    ROUND(avg_do, 2) AS avg_do,
    ROUND(AVG(avg_do) OVER (ORDER BY reading_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS cumulative_avg_do
FROM daily_do
ORDER BY reading_date;

WITH daily_turbidity AS (
    SELECT DATE(timestamp) AS reading_date, AVG(turbidity) AS avg_turbidity
    FROM water_quality
    WHERE turbidity IS NOT NULL
    GROUP BY DATE(timestamp)
),
flagged AS (
    SELECT reading_date, avg_turbidity, CASE WHEN avg_turbidity > 10 THEN 1 ELSE 0 END AS is_high
    FROM daily_turbidity
),
grouped AS (
    SELECT
        reading_date, avg_turbidity, is_high,
        SUM(CASE WHEN is_high = 0 THEN 1 ELSE 0 END) OVER (ORDER BY reading_date) AS reset_group
    FROM flagged
)
SELECT
    MIN(reading_date) AS streak_start,
    MAX(reading_date) AS streak_end,
    COUNT(*) AS streak_length_days,
    ROUND(AVG(avg_turbidity), 2) AS streak_avg_turbidity
FROM grouped
WHERE is_high = 1
GROUP BY reset_group
HAVING COUNT(*) >= 2
ORDER BY streak_length_days DESC;
