-- Bronze: raw files exactly as downloaded or collected. Nothing is changed here.
CREATE SCHEMA IF NOT EXISTS bronze;

CREATE OR REPLACE TABLE bronze.hourly_download AS
SELECT * FROM read_csv('${RAW}/hourly_pgcb_2015_2026/pgcb_V1_raw.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE bronze.hourly_portal AS
SELECT * FROM read_csv('${RAW}/pgcb_portal_2026/pgcb_hourly_*.csv', header = true, all_varchar = true,
                       filename = true, union_by_name = true);

CREATE OR REPLACE TABLE bronze.daily_bpdb AS
SELECT * FROM read_csv('${RAW}/daily_bpdb_2019_2026/Bangladesh_Electricity_Dataset_2019_2026.csv',
                       header = true, all_varchar = true);

CREATE OR REPLACE TABLE bronze.events AS
SELECT * FROM read_csv('${REF}/policy_events_2026.csv', header = true, all_varchar = true);

CREATE OR REPLACE TABLE bronze.holidays AS
SELECT * FROM read_csv('${REF}/holidays_2026.csv', header = true, all_varchar = true);
