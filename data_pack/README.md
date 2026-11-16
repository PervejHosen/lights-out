# Data pack

Small tables behind the findings. All figures are MW or GWh from PGCB's hourly data unless noted; load shedding is
PGCB's grid-level estimate. Year comparisons use 1 am to 11 pm, because the older data has no midnight readings.

| File | What it holds |
|---|---|
| `yearly.csv` | Each year since 2015: energy lost, hours and days with a cut, deepest hour |
| `monthly.csv` | Each month: energy lost, average cut, generation by fuel, imports |
| `zone_share.csv` | Each BPDB zone by year: share of demand, share of load shed, burden ratio (evening peak report, to 3 Aug 2026) |
| `shift_windows.csv` | Work shifts by year and season: share of hours cut and average cut |
| `evening_gap.csv` | June to October 2026, average by hour: demand, generation, cut, each source |
| `bridge_crisis.csv` | August and September 2026 against 2025: change in the cut split into demand and each source |
| `bridge_monthly.csv` | The same split for every month of 2025 and 2026 against the same days a year earlier |
| `demand_temp_check.csv` | Reported, served and weather-expected daily peak by month, April to October |
| `policy_check_weather.csv` | Each shop closing rule: change in evening demand, before and after taking weather out |
| `what_if.csv` | Share of 2026 lost energy removed by each lever, at each size |
| `scorecard.csv`, `scorecard_all.csv` | Forecast accuracy by test window and method |
| `forecast_next_week.csv` | The forecast made from 16 November 2026 |

Credit: Lights Out, Pervej Hosen, using public PGCB and BPDB data.
