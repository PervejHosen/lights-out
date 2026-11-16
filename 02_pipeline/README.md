# Pipeline

DuckDB SQL in three layers. Run from the project folder:

```
pip install duckdb
python 02_pipeline\run.py
```

It writes `01_data/processed/lights_out.duckdb` and one CSV per gold table in `01_data/processed/gold/`
(both generated, so not kept in git). Re-run it whenever the raw data changes, for example after the collector
adds new days.

| File | Layer | What it does |
|---|---|---|
| `sql/10_bronze.sql` | bronze | Loads the raw files as they are: hourly download, collector CSVs, daily BPDB, events, holidays |
| `sql/20_silver_hourly.sql` | silver | One clean row per reading: download up to 28 Feb 2026, collector from 1 Mar; fixes the 12 May 2026 duplicate; flags impossible values (load shed over 6,000 MW, a fuel over 20,000 MW, generation outside 3,000 to 20,000 MW) and sets them to missing; true demand = generation + load shed |
| `sql/21_silver_daily.sql` | silver | Daily BPDB in snake_case, one row per zone per day, events, holidays |
| `sql/30_gold.sql` | gold | `hourly`, `monthly`, `yearly`, `hour_profile`, `daily`, `zone_share`, `shift_windows`, `policy_check` |

Yearly comparisons use the `*_comparable` columns (hours 01 to 23), because the downloaded data has no 00:00
readings before March 2026.
