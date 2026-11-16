"""Collect hourly weather for the 9 BPDB zone centres from Open-Meteo (free, no key, CC BY 4.0).

Source: Open-Meteo historical weather API (ERA5 reanalysis), https://open-meteo.com/en/docs/historical-weather-api
Attribution: "Weather data by Open-Meteo.com" (keep this in the report and the data pack).

Usage (from the project folder):
    python tools\\weather_collect.py                    # 2015 to about 5 days ago (ERA5 runs a few days behind)
    python tools\\weather_collect.py --start 2026-01-01

Writes one CSV per zone and year to 01_data/raw/weather/, and skips years already saved
(the current year is always fetched again). About 110 small requests; takes a minute or two.
"""
import argparse
import csv
import datetime as dt
import json
import os
import time
import urllib.request

try:                      # use the Windows certificate store, as in pgcb_collect.py
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date={s}&end_date={e}&timezone=Asia%2FDhaka"
       "&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,cloud_cover")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "01_data", "raw", "weather")

# Zone centres (city where each BPDB zone is based)
ZONES = {
    "Dhaka": (23.81, 90.41), "Chattogram": (22.36, 91.78), "Khulna": (22.85, 89.54),
    "Rajshahi": (24.37, 88.60), "Cumilla": (23.46, 91.18), "Mymensingh": (24.75, 90.41),
    "Sylhet": (24.90, 91.87), "Barishal": (22.70, 90.37), "Rangpur": (25.75, 89.25),
}
COLS = ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "cloud_cover"]


def fetch(lat, lon, s, e):
    req = urllib.request.Request(URL.format(lat=lat, lon=lon, s=s, e=e),
                                 headers={"User-Agent": "LightsOut independent research"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["hourly"]
        except Exception as ex:  # rate limit or network blip: wait and retry
            wait = 10 * (attempt + 1)
            print(f"    retry in {wait}s ({ex})")
            time.sleep(wait)
    raise SystemExit("Open-Meteo did not answer after 4 tries. Run again later; saved years are kept.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2015-04-01")
    ap.add_argument("--end", default=str(dt.date.today() - dt.timedelta(days=5)))
    a = ap.parse_args()
    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    os.makedirs(OUT, exist_ok=True)

    for zone, (lat, lon) in ZONES.items():
        for year in range(start.year, end.year + 1):
            path = os.path.join(OUT, f"weather_{zone.lower()}_{year}.csv")
            if os.path.exists(path) and year < end.year:
                continue
            s = max(start, dt.date(year, 1, 1)); e = min(end, dt.date(year, 12, 31))
            h = fetch(lat, lon, s, e)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["zone", "ts"] + COLS)
                for i, ts in enumerate(h["time"]):
                    w.writerow([zone, ts.replace("T", " ")] + [h[c][i] for c in COLS])
            print(f"  {zone:11s} {year}: {len(h['time']):,} hours")
            time.sleep(1.0)
    print(f"Done. Files in {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
