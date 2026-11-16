-- Silver: one clean row per reading, Dhaka time, typed, with flags. Nothing is dropped silently.
CREATE SCHEMA IF NOT EXISTS silver;

CREATE OR REPLACE TABLE silver.hourly AS
WITH download AS (
    SELECT CAST(datetime AS TIMESTAMP) AS ts, 'download' AS source,
           TRY_CAST(generation_mw AS DOUBLE) AS generation_mw, TRY_CAST(demand_mw AS DOUBLE) AS demand_reported_mw,
           TRY_CAST(load_shedding AS DOUBLE) AS load_shed_raw,
           TRY_CAST(gas AS DOUBLE) AS gas, TRY_CAST(liquid_fuel AS DOUBLE) AS liquid_fuel, TRY_CAST(coal AS DOUBLE) AS coal,
           TRY_CAST(hydro AS DOUBLE) AS hydro, TRY_CAST(solar AS DOUBLE) AS solar, TRY_CAST(wind AS DOUBLE) AS wind,
           TRY_CAST(india_bheramara_hvdc AS DOUBLE) AS india_bheramara_hvdc, TRY_CAST(india_tripura AS DOUBLE) AS india_tripura,
           TRY_CAST(india_adani AS DOUBLE) AS india_adani, TRY_CAST(nepal AS DOUBLE) AS nepal, remarks
    FROM bronze.hourly_download
    WHERE CAST(datetime AS TIMESTAMP) < TIMESTAMP '2026-03-01'          -- the collector covers 1 March onward
),
portal_raw AS (
    SELECT *, strptime(date || ' ' || time, '%d-%m-%Y %H:%M:%S') AS ts0
    FROM bronze.hourly_portal WHERE TRY_CAST(cell_count AS INT) > 0
),
portal AS (
    SELECT
        -- Known fix: the 12 May 2026 page repeats 21:00 with 11 May's 21:00 reading (14,360 MW sits between
        -- 11 May 20:00 and 22:00, and 11 May lacks that hour).
        CASE WHEN ts0 = TIMESTAMP '2026-05-12 21:00:00' AND generation_mw = '14360'
             THEN TIMESTAMP '2026-05-11 21:00:00' ELSE ts0 END AS ts,
        'collector' AS source,
        TRY_CAST(generation_mw AS DOUBLE), TRY_CAST(demand_mw_raw AS DOUBLE), TRY_CAST(loadshed_mw_raw AS DOUBLE),
        TRY_CAST(gas AS DOUBLE), TRY_CAST(liquid_fuel AS DOUBLE), TRY_CAST(coal AS DOUBLE), TRY_CAST(hydro AS DOUBLE),
        TRY_CAST(solar AS DOUBLE), TRY_CAST(wind AS DOUBLE), TRY_CAST(india_bheramara_hvdc AS DOUBLE),
        TRY_CAST(india_tripura AS DOUBLE), TRY_CAST(india_adani AS DOUBLE), TRY_CAST(nepal AS DOUBLE), remarks
    FROM portal_raw
),
unioned AS (SELECT * FROM download UNION ALL SELECT * FROM portal),
deduped AS (
    SELECT * FROM unioned
    QUALIFY row_number() OVER (PARTITION BY ts ORDER BY source) = 1
),
flagged AS (
    SELECT *,
        load_shed_raw > 6000 OR load_shed_raw < 0                                          AS flag_shed_impossible,
        greatest(gas, liquid_fuel, coal, hydro, solar, wind) > 20000                        AS flag_fuel_impossible,
        generation_mw < 3000 OR generation_mw > 20000                                       AS flag_generation_outlier
    FROM deduped
)
SELECT
    ts, CAST(ts AS DATE) AS date, hour(ts) AS hour, minute(ts) AS minute, minute(ts) <> 0 AS is_peak_reading,
    year(ts) AS year, month(ts) AS month, dayofweek(ts) AS dow,                       -- 0 = Sunday
    dayofweek(ts) IN (5, 6) AS is_weekend,                                              -- Friday and Saturday
    CASE WHEN month(ts) IN (3,4,5) THEN 'Pre-monsoon (Mar to May)' WHEN month(ts) IN (6,7,8,9) THEN 'Monsoon (Jun to Sep)'
         WHEN month(ts) IN (10,11) THEN 'Post-monsoon (Oct to Nov)' ELSE 'Winter (Dec to Feb)' END AS season,
    source,
    CASE WHEN flag_generation_outlier THEN NULL ELSE generation_mw END AS generation_mw,
    CASE WHEN flag_shed_impossible THEN NULL ELSE load_shed_raw END AS load_shed_mw,
    -- Reported demand often just repeats generation and is empty after 23 Apr 2026, so we measure demand one way:
    CASE WHEN flag_generation_outlier OR flag_shed_impossible THEN NULL ELSE generation_mw + load_shed_raw END AS true_demand_mw,
    demand_reported_mw,
    CASE WHEN gas > 20000 THEN NULL ELSE gas END AS gas,
    CASE WHEN liquid_fuel > 20000 THEN NULL ELSE liquid_fuel END AS liquid_fuel,
    CASE WHEN coal > 20000 THEN NULL ELSE coal END AS coal,
    hydro, solar, wind, india_bheramara_hvdc, india_tripura, india_adani, nepal,
    coalesce(india_bheramara_hvdc,0) + coalesce(india_tripura,0) + coalesce(india_adani,0) + coalesce(nepal,0) AS imports,
    generation_mw - (coalesce(gas,0) + coalesce(liquid_fuel,0) + coalesce(coal,0) + coalesce(hydro,0) + coalesce(solar,0)
        + coalesce(wind,0) + coalesce(india_bheramara_hvdc,0) + coalesce(india_tripura,0) + coalesce(india_adani,0)
        + coalesce(nepal,0)) AS parts_gap_mw,
    remarks, flag_shed_impossible, flag_fuel_impossible, flag_generation_outlier,
    abs(generation_mw - (coalesce(gas,0) + coalesce(liquid_fuel,0) + coalesce(coal,0) + coalesce(hydro,0) + coalesce(solar,0)
        + coalesce(wind,0) + coalesce(india_bheramara_hvdc,0) + coalesce(india_tripura,0) + coalesce(india_adani,0)
        + coalesce(nepal,0))) > 100 AS flag_parts_gap
FROM flagged
ORDER BY ts;
