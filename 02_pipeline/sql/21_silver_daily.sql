-- Silver: daily BPDB records, snake_case, plus one row per zone per day.
CREATE OR REPLACE TABLE silver.daily AS
SELECT
    CAST("Date" AS DATE) AS date,
    "Day of the week" AS weekday_label,
    dayname(CAST("Date" AS DATE)) <> "Day of the week" AS flag_weekday_mismatch,     -- source warns about these
    TRY_CAST("Max. Demand at eve. peak (Generation end)" AS DOUBLE)   AS max_demand_eve_peak_mw,
    TRY_CAST("Max. Demand at eve. peak (Sub-station end)" AS DOUBLE)  AS max_demand_eve_peak_substation_mw,
    TRY_CAST("Highest Generation (Generation end)" AS DOUBLE)         AS highest_generation_mw,
    TRY_CAST("Minimum Generation (Generation end)" AS DOUBLE)         AS minimum_generation_mw,
    TRY_CAST("Day-peak Generation (Generation end)" AS DOUBLE)        AS day_peak_generation_mw,
    TRY_CAST("Evening-peak Generation (Generation end)" AS DOUBLE)    AS eve_peak_generation_mw,
    TRY_CAST("Maximum Temperature in Dhaka was" AS DOUBLE)            AS dhaka_max_temp_c,
    TRY_CAST("Gas/LF limitation" AS DOUBLE)                           AS limit_gas_fuel_mw,
    TRY_CAST("Coal supply Limitation" AS DOUBLE)                      AS limit_coal_mw,
    TRY_CAST("Low water level in Kaptai lake" AS DOUBLE)              AS limit_hydro_mw,
    TRY_CAST("Plants under shut down/ maintenance" AS DOUBLE)         AS plants_maintenance_mw,
    "Holiday name" AS holiday_name,
    TRY_CAST("Holiday_cat" AS INT) AS holiday_cat
FROM bronze.daily_bpdb;

CREATE OR REPLACE TABLE silver.daily_zone AS
WITH z AS (
    SELECT CAST("Date" AS DATE) AS date, UNNEST([
        {zone:'Dhaka', d:"Dhaka_demand", s:"Dhaka_supply", l:"Dhaka_load"},
        {zone:'Chattogram', d:"Chattogram_demand", s:"Chattogram_supply", l:"Chattogram_load"},
        {zone:'Rajshahi', d:"Rajshahi_demand", s:"Rajshahi_supply", l:"Rajshahi_load"},
        {zone:'Mymensingh', d:"Mymensingh_demand", s:"Mymensingh_supply", l:"Mymensingh_load"},
        {zone:'Sylhet', d:"Sylhet_demand", s:"Sylhet_supply", l:"Sylhet_load"},
        {zone:'Barishal', d:"Barishal_demand", s:"Barishal_supply", l:"Barishal_load"},
        {zone:'Rangpur', d:"Rangpur_demand", s:"Rangpur_supply", l:"Rangpur_load"},
        {zone:'Cumilla', d:"Cumilla_demand", s:"Cumilla_supply", l:"Cumilla_load"},
        {zone:'Khulna', d:"Khulna_demand", s:"Khulna_supply", l:"Khulna_load"}]) AS r
    FROM bronze.daily_bpdb
)
SELECT date, r.zone AS zone, TRY_CAST(r.d AS DOUBLE) AS demand_mw, TRY_CAST(r.s AS DOUBLE) AS supply_mw,
       TRY_CAST(r.l AS DOUBLE) AS load_shed_mw
FROM z;

CREATE OR REPLACE TABLE silver.events AS
SELECT CASE WHEN length(date) = 10 THEN CAST(date AS DATE) END AS date, date AS date_text, type, event,
       TRY_CAST(closing_hour AS INT) AS closing_hour, source, note
FROM bronze.events;

-- Holidays: from the daily dataset up to 2024, plus our 2026 list (the dataset stops recording them after 2024)
CREATE OR REPLACE TABLE silver.holidays AS
SELECT date, holiday_name AS holiday FROM silver.daily WHERE holiday_cat > 0
UNION
SELECT CAST(d AS DATE) AS date, holiday
FROM bronze.holidays, LATERAL (SELECT UNNEST(generate_series(CAST(start_date AS DATE), CAST(end_date AS DATE), INTERVAL 1 DAY)) AS d);
