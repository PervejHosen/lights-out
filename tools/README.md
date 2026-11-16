# Tools

## pgcb_collect.py

Collects hourly generation from PGCB's public portal
(https://erp.powergrid.gov.bd/web/generations/view_generations), one request per day of data,
into `01_data/raw/pgcb_portal_2026/pgcb_hourly_YYYY-MM.csv`.

```
pip install truststore        # Windows: use the system certificate store for the portal
python tools/pgcb_collect.py                      # 1 March 2026 to yesterday
python tools/pgcb_collect.py --start 2015-04-01   # full history, about 4,000 requests
```

Safe to stop and run again: days already saved are skipped. Keep the delay at 1.5 seconds or more.

The page hides its Demand and Loadshed cells in HTML comments, but they are still sent. The collector saves them as
`demand_mw_raw`, `demand_calc_raw` and `loadshed_mw_raw`. On the overlap (March 2026) they match the Mendeley hourly
dataset exactly; see `01_data/raw/pgcb_portal_2026/NOTES.md`.

## weather_collect.py

Hourly temperature, humidity, feels-like temperature, rain and cloud for the 9 BPDB zone cities, 2015 to about five
days ago, from the Open-Meteo historical API (ERA5). Writes `01_data/raw/weather/`. Credit: "Weather data by Open-Meteo.com".

```
python tools/weather_collect.py
```
