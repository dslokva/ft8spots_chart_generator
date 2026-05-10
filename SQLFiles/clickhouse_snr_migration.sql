-- Migration: add snr column to existing spots_sum_grid_ll_* tables
-- Run once per table that was loaded before the SNR change.
-- Python's ensure_table_snr_column() does this automatically for new imports;
-- use these queries for any tables already in ClickHouse.

-- Step 1: add snr column (DEFAULT 0 — historical rows have no SNR data)
ALTER TABLE default.spots_sum_grid_ll_YYYY_MM ADD COLUMN `snr` Int32 DEFAULT 0;

-- Step 2: upgrade cnt from UInt8 (max 255) to UInt32
-- Necessary because SummingMergeTree accumulates counts far beyond 255.
ALTER TABLE default.spots_sum_grid_ll_YYYY_MM MODIFY COLUMN `cnt` UInt32;

-- Verify result
SELECT name, type
FROM system.columns
WHERE database = 'default' AND table = 'spots_sum_grid_ll_YYYY_MM'
ORDER BY position;


-- ============================================================
-- Grafana query examples
-- ============================================================

-- 1. Zone-pair heatmap (VOACAP-style): date × UTC quarter-hour, colored by spot count
--    Grafana panel: Heatmap  |  X = day, Y = quarter_hour, Value = spots
SELECT
    toStartOfDay(toDateTime(utc))                                         AS day,
    toHour(toDateTime(utc)) * 4 + intDiv(toMinute(toDateTime(utc)), 15)  AS quarter_hour,
    sum(cnt)                                                              AS spots
FROM default.spots_sum_grid_ll_2023_01
WHERE band = '20m'
  AND ((zone1 = 8 AND zone2 = 27) OR (zone1 = 27 AND zone2 = 8))
GROUP BY day, quarter_hour
ORDER BY day, quarter_hour;


-- 2. Average SNR heatmap: same structure, value = avg SNR
--    Overlay this on the count heatmap to see signal quality
SELECT
    toStartOfDay(toDateTime(utc))                                         AS day,
    toHour(toDateTime(utc)) * 4 + intDiv(toMinute(toDateTime(utc)), 15)  AS quarter_hour,
    sum(cnt)                                                              AS spots,
    if(sum(cnt) > 0, sum(snr) / sum(cnt), 0)                            AS avg_snr
FROM default.spots_sum_grid_ll_2023_01
WHERE band = '20m'
  AND ((zone1 = 8 AND zone2 = 27) OR (zone1 = 27 AND zone2 = 8))
GROUP BY day, quarter_hour
ORDER BY day, quarter_hour;


-- 3. Band comparison: activity by hour across all bands for a zone pair
SELECT
    band,
    toHour(toDateTime(utc))               AS utc_hour,
    sum(cnt)                              AS spots,
    if(sum(cnt) > 0, sum(snr) / sum(cnt), 0) AS avg_snr
FROM default.spots_sum_grid_ll_2023_01
WHERE (zone1 = 8 AND zone2 = 27) OR (zone1 = 27 AND zone2 = 8)
GROUP BY band, utc_hour
ORDER BY band, utc_hour;


-- 4. SNR distribution by band (histogram input)
SELECT
    band,
    round(snr / cnt) AS snr_bucket,
    sum(cnt)         AS spots
FROM default.spots_sum_grid_ll_2023_01
WHERE (zone1 = 8 AND zone2 = 27) OR (zone1 = 27 AND zone2 = 8)
GROUP BY band, snr_bucket
ORDER BY band, snr_bucket;
