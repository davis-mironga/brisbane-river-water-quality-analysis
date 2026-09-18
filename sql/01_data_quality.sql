-- =============================================================================
-- 01_data_quality.sql
-- Brisbane River Water Quality Analysis
--
-- Purpose: verify the cleaned dataset (loaded into the `water_quality` table)
-- is structurally sound before any analytical querying happens on top of it.
-- These checks mirror, in SQL, the same data-quality investigation already
-- performed in Notebook 1 (Python) -- this is intentional: it demonstrates
-- the same conclusions can be reached with SQL directly against the database.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Row count
-- Expected: 30,894 (matches the cleaned CSV exported by Notebook 1)
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS total_rows
FROM water_quality;


-- -----------------------------------------------------------------------------
-- 2. Distinct values in key categorical columns
-- Confirms season/day_of_week were engineered correctly (4 seasons, 7 weekdays)
-- and gives a sanity check on the monitoring period's year/month coverage.
-- -----------------------------------------------------------------------------
SELECT DISTINCT season
FROM water_quality
ORDER BY season;

SELECT DISTINCT day_of_week
FROM water_quality
ORDER BY day_of_week;

SELECT DISTINCT year, month
FROM water_quality
ORDER BY year, month;


-- -----------------------------------------------------------------------------
-- 3. NULL checks per measurement column
-- Reproduces the missing-value percentages from Notebook 1's missingness
-- analysis, this time computed directly in SQL.
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                    AS total_rows,
    SUM(CASE WHEN water_speed              IS NULL THEN 1 ELSE 0 END) AS null_water_speed,
    SUM(CASE WHEN water_direction          IS NULL THEN 1 ELSE 0 END) AS null_water_direction,
    SUM(CASE WHEN chlorophyll              IS NULL THEN 1 ELSE 0 END) AS null_chlorophyll,
    SUM(CASE WHEN temperature              IS NULL THEN 1 ELSE 0 END) AS null_temperature,
    SUM(CASE WHEN dissolved_oxygen         IS NULL THEN 1 ELSE 0 END) AS null_dissolved_oxygen,
    SUM(CASE WHEN dissolved_oxygen_pct_sat IS NULL THEN 1 ELSE 0 END) AS null_do_pct_sat,
    SUM(CASE WHEN ph                       IS NULL THEN 1 ELSE 0 END) AS null_ph,
    SUM(CASE WHEN salinity                 IS NULL THEN 1 ELSE 0 END) AS null_salinity,
    SUM(CASE WHEN specific_conductance     IS NULL THEN 1 ELSE 0 END) AS null_specific_conductance,
    SUM(CASE WHEN turbidity                IS NULL THEN 1 ELSE 0 END) AS null_turbidity
FROM water_quality;


-- Same missingness check, expressed as a percentage and pivoted into rows
-- (easier to read than one very wide row above).
SELECT 'temperature'              AS parameter, ROUND(100.0 * SUM(CASE WHEN temperature              IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS missing_pct FROM water_quality
UNION ALL
SELECT 'dissolved_oxygen',        ROUND(100.0 * SUM(CASE WHEN dissolved_oxygen         IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'dissolved_oxygen_pct_sat',ROUND(100.0 * SUM(CASE WHEN dissolved_oxygen_pct_sat IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'salinity',                ROUND(100.0 * SUM(CASE WHEN salinity                 IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'turbidity',               ROUND(100.0 * SUM(CASE WHEN turbidity                IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'specific_conductance',    ROUND(100.0 * SUM(CASE WHEN specific_conductance     IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'ph',                      ROUND(100.0 * SUM(CASE WHEN ph                       IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'chlorophyll',             ROUND(100.0 * SUM(CASE WHEN chlorophyll              IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'water_speed',             ROUND(100.0 * SUM(CASE WHEN water_speed              IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
UNION ALL
SELECT 'water_direction',         ROUND(100.0 * SUM(CASE WHEN water_direction          IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) FROM water_quality
ORDER BY missing_pct DESC;


-- -----------------------------------------------------------------------------
-- 4. Duplicate detection
-- (a) Fully duplicated rows (every column identical) -- expect 0, per Notebook 1
-- (b) Duplicate record_number values -- record_number should be a unique key
-- -----------------------------------------------------------------------------
SELECT record_number, COUNT(*) AS occurrences
FROM water_quality
GROUP BY record_number
HAVING COUNT(*) > 1;

-- Rows sharing the same timestamp (NOT necessarily duplicates -- Notebook 1
-- found these reflect a coarser logging resolution, not true duplication).
SELECT timestamp, COUNT(*) AS occurrences
FROM water_quality
GROUP BY timestamp
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 5. Basic physical-plausibility validation
-- Confirms no impossible values slipped through cleaning (mirrors Notebook 1's
-- invalid-value checks). Expect zero rows returned by each query below.
-- -----------------------------------------------------------------------------

-- pH must be within the 0-14 scale
SELECT COUNT(*) AS invalid_ph_rows
FROM water_quality
WHERE ph IS NOT NULL AND (ph < 0 OR ph > 14);

-- Water direction must be a valid compass bearing (0-360 degrees)
SELECT COUNT(*) AS invalid_direction_rows
FROM water_quality
WHERE water_direction IS NOT NULL AND (water_direction < 0 OR water_direction > 360);

-- Dissolved oxygen % saturation: sensor readings can exceed 100% (supersaturation
-- is a real phenomenon, e.g. during algal blooms), but flag anything implausibly
-- high (>200%) as worth a second look.
SELECT COUNT(*) AS implausible_do_saturation_rows
FROM water_quality
WHERE dissolved_oxygen_pct_sat IS NOT NULL AND dissolved_oxygen_pct_sat > 200;

-- No measurement column should be negative (all represent physical quantities
-- that cannot go below zero).
SELECT COUNT(*) AS negative_value_rows
FROM water_quality
WHERE (water_speed IS NOT NULL AND water_speed < 0)
   OR (chlorophyll IS NOT NULL AND chlorophyll < 0)
   OR (dissolved_oxygen IS NOT NULL AND dissolved_oxygen < 0)
   OR (salinity IS NOT NULL AND salinity < 0)
   OR (specific_conductance IS NOT NULL AND specific_conductance < 0)
   OR (turbidity IS NOT NULL AND turbidity < 0);


-- -----------------------------------------------------------------------------
-- 6. Rows that are entirely missing every measurement (would indicate a
-- completely dead sensor reading that adds no value) -- expect 0.
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS fully_empty_measurement_rows
FROM water_quality
WHERE water_speed IS NULL
  AND water_direction IS NULL
  AND chlorophyll IS NULL
  AND temperature IS NULL
  AND dissolved_oxygen IS NULL
  AND dissolved_oxygen_pct_sat IS NULL
  AND ph IS NULL
  AND salinity IS NULL
  AND specific_conductance IS NULL
  AND turbidity IS NULL;
