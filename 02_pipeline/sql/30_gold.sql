-- Gold: small tables that answer the questions and feed the report pages.
CREATE SCHEMA IF NOT EXISTS gold;

-- On-the-hour readings only (the 18:30 and 19:30 peak readings stay in silver)
CREATE OR REPLACE TABLE gold.hourly AS
SELECT * EXCLUDE (minute, is_peak_reading) FROM silver.hourly WHERE minute = 0;

-- Note: the downloaded data has no 00:00 readings before March 2026, so yearly comparisons use
-- *_comparable columns that count hours 01 to 23 only, the same for every year.
CREATE OR REPLACE TABLE gold.monthly AS
SELECT date_trunc('month', ts)::DATE AS month, year,
       round(sum(load_shed_mw) / 1000, 1)                               AS energy_shed_gwh,
       round(sum(load_shed_mw) FILTER (WHERE hour >= 1) / 1000, 1)      AS energy_shed_gwh_comparable,
       count(*) FILTER (WHERE load_shed_mw > 0)                         AS hours_with_shed,
       round(100.0 * count(*) FILTER (WHERE load_shed_mw > 0) / count(*), 1) AS pct_hours_with_shed,
       max(load_shed_mw) AS peak_shed_mw, round(avg(load_shed_mw)) AS avg_shed_mw,
       round(avg(generation_mw)) AS avg_generation_mw, round(max(true_demand_mw)) AS peak_true_demand_mw,
       round(avg(gas)) AS avg_gas_mw, round(avg(coal)) AS avg_coal_mw, round(avg(liquid_fuel)) AS avg_oil_mw,
       round(avg(imports)) AS avg_imports_mw, round(avg(coalesce(hydro,0) + coalesce(solar,0) + coalesce(wind,0))) AS avg_renewable_mw,
       count(*) AS hours_in_data
FROM gold.hourly GROUP BY ALL ORDER BY month;

CREATE OR REPLACE TABLE gold.yearly AS
SELECT year,
       round(sum(load_shed_mw) / 1000, 1)                               AS energy_shed_gwh,
       round(sum(load_shed_mw) FILTER (WHERE hour >= 1) / 1000, 1)      AS energy_shed_gwh_comparable,
       count(*) FILTER (WHERE load_shed_mw > 0)                         AS hours_with_shed,
       count(DISTINCT date) FILTER (WHERE load_shed_mw > 0)             AS days_with_shed,
       max(load_shed_mw) AS peak_shed_mw,
       round(max(true_demand_mw)) AS peak_true_demand_mw, round(max(generation_mw)) AS peak_generation_mw,
       min(date) AS first_day, max(date) AS last_day
FROM gold.hourly GROUP BY year ORDER BY year;

CREATE OR REPLACE TABLE gold.hour_profile AS
SELECT year, season, hour,
       round(avg(load_shed_mw)) AS avg_shed_mw,
       round(100.0 * avg(CASE WHEN load_shed_mw > 0 THEN 1 ELSE 0 END), 1) AS pct_hours_with_shed,
       round(avg(true_demand_mw)) AS avg_true_demand_mw, round(avg(generation_mw)) AS avg_generation_mw,
       round(avg(solar)) AS avg_solar_mw, count(*) AS n_hours
FROM gold.hourly GROUP BY ALL ORDER BY year, season, hour;

CREATE OR REPLACE TABLE gold.daily AS
WITH h AS (
    SELECT date, year,
           max(load_shed_mw) AS max_shed_mw, round(sum(load_shed_mw)) AS energy_shed_mwh,
           count(*) FILTER (WHERE load_shed_mw > 0) AS hours_with_shed,
           round(max(true_demand_mw)) AS max_true_demand_mw, round(avg(generation_mw)) AS avg_generation_mw,
           round(avg(gas)) AS avg_gas_mw, round(avg(coal)) AS avg_coal_mw, round(avg(liquid_fuel)) AS avg_oil_mw,
           round(avg(imports)) AS avg_imports_mw, max(solar) AS max_solar_mw,
           round(sum(load_shed_mw) FILTER (WHERE hour BETWEEN 7 AND 17)) AS shed_daylight_mwh,
           round(sum(load_shed_mw) FILTER (WHERE hour BETWEEN 18 AND 23)) AS shed_evening_mwh,
           round(sum(load_shed_mw) FILTER (WHERE hour BETWEEN 0 AND 6)) AS shed_night_mwh,
           count(*) AS hours_in_data, bool_or(hour = 0) AS has_midnight
    FROM gold.hourly GROUP BY date, year
),
z AS (SELECT date, sum(load_shed_mw) AS zone_shed_total_mw, sum(demand_mw) AS zone_demand_total_mw FROM silver.daily_zone GROUP BY date)
SELECT h.*, d.dhaka_max_temp_c, d.limit_gas_fuel_mw, d.limit_coal_mw, d.limit_hydro_mw, d.plants_maintenance_mw,
       d.max_demand_eve_peak_mw, z.zone_shed_total_mw, z.zone_demand_total_mw, d.holiday_name, d.holiday_cat
FROM h LEFT JOIN silver.daily d USING (date) LEFT JOIN z USING (date)
ORDER BY date;

CREATE OR REPLACE TABLE gold.zone_share AS
WITH y AS (
    SELECT year(date) AS year, zone, sum(demand_mw) AS demand, sum(load_shed_mw) AS shed
    FROM silver.daily_zone GROUP BY ALL
)
SELECT year, zone,
       round(100.0 * demand / sum(demand) OVER (PARTITION BY year), 1) AS pct_of_demand,
       round(100.0 * shed / nullif(sum(shed) OVER (PARTITION BY year), 0), 1) AS pct_of_load_shed,
       round(100.0 * shed / nullif(demand, 0), 2) AS shed_as_pct_of_own_demand,
       round((shed / nullif(sum(shed) OVER (PARTITION BY year), 0)) / (demand / sum(demand) OVER (PARTITION BY year)), 2) AS burden_ratio
FROM y ORDER BY year, zone;

-- Working windows a factory or office might use
CREATE OR REPLACE TABLE gold.shift_windows AS
WITH w(window_name, start_hour, end_hour) AS (VALUES
    ('Early shift 6 am to 2 pm', 6, 13), ('Office day 9 am to 5 pm', 9, 16), ('Day shift 8 am to 8 pm', 8, 19),
    ('Evening shift 2 pm to 10 pm', 14, 21), ('Night shift 10 pm to 6 am', 22, 5)),
x AS (
    SELECT w.window_name, w.start_hour, h.year, h.season, h.date, h.load_shed_mw
    FROM gold.hourly h JOIN w ON CASE WHEN w.start_hour < w.end_hour + 1 THEN h.hour BETWEEN w.start_hour AND w.end_hour
                                      ELSE h.hour >= w.start_hour OR h.hour <= w.end_hour END
    WHERE h.hour >= 1                                   -- comparable across years (no 00:00 before 2026)
)
SELECT year, season, window_name,
       round(100.0 * avg(CASE WHEN load_shed_mw > 0 THEN 1 ELSE 0 END), 1) AS pct_hours_with_shed,
       round(avg(load_shed_mw)) AS avg_shed_mw,
       round(100.0 * count(DISTINCT date) FILTER (WHERE load_shed_mw > 0) / count(DISTINCT date), 1) AS pct_days_hit
FROM x GROUP BY ALL ORDER BY year, season, window_name;

-- Policy check, within-day design: evening demand (19:00 to 22:00) as a share of afternoon demand (14:00 to 17:00),
-- on the 7 nearest non-holiday days before vs the 7 after each rule. Weather moves both parts of the day,
-- so it largely cancels out; holidays are skipped because they change the shape of the day.
CREATE OR REPLACE TABLE gold.policy_check AS
WITH day_ratio AS (
    SELECT date,
           avg(true_demand_mw) FILTER (WHERE hour BETWEEN 19 AND 22) AS evening_mw,
           avg(true_demand_mw) FILTER (WHERE hour BETWEEN 14 AND 17) AS afternoon_mw
    FROM gold.hourly WHERE year = 2026 AND date NOT IN (SELECT date FROM silver.holidays) GROUP BY date
),
r AS (SELECT date, afternoon_mw, evening_mw / afternoon_mw AS ratio FROM day_ratio),
e AS (SELECT date AS rule_date, event, closing_hour FROM silver.events WHERE type = 'rule' AND date IS NOT NULL),
w AS (
    SELECT e.*, r.*, CASE WHEN r.date < e.rule_date THEN 'before' ELSE 'after' END AS side,
           row_number() OVER (PARTITION BY e.rule_date, r.date < e.rule_date ORDER BY abs(r.date - e.rule_date)) AS k
    FROM e JOIN r ON r.date <> e.rule_date AND abs(r.date - e.rule_date) <= 21
)
SELECT rule_date, event, closing_hour,
       round(avg(ratio) FILTER (WHERE side = 'before'), 4) AS ratio_before,
       round(avg(ratio) FILTER (WHERE side = 'after'), 4) AS ratio_after,
       round(avg(afternoon_mw) FILTER (WHERE side = 'after')) AS afternoon_mw_after,
       round((avg(ratio) FILTER (WHERE side = 'after') - avg(ratio) FILTER (WHERE side = 'before'))
             * avg(afternoon_mw) FILTER (WHERE side = 'after')) AS evening_change_mw,
       min(date) AS first_day_used, max(date) AS last_day_used
FROM w WHERE k <= 7 GROUP BY ALL ORDER BY rule_date;
