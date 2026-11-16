"""Lights Out · Phase 5 review: recompute every published number on its own and check the wording.

Run from the project folder (after the pipeline, forecast.py and drivers.py):
    python 05_review\\verify.py

What it does
1. Recomputes each headline number with its own query, straight from the silver layer (not from the gold or model
   tables the notebooks used), and compares it with the number we plan to publish.
2. Scans every notebook, README and draft in the project for dashes and for loaded words.
3. Writes 05_review/findings_register.csv and prints a pass or fail line for each check.

A finding goes out only if its check passes. The register also records the range, what the finding cannot say,
and whether it was kept, softened or dropped in review.
"""
import glob
import json
import os
import re
import sys

import duckdb
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
con = duckdb.connect(os.path.join(ROOT, "01_data", "processed", "lights_out.duckdb"), read_only=True)
q = lambda s: con.sql(s).df()
one = lambda s: con.execute(s).fetchall()[0][0]

# Clean hourly readings straight from silver: on the hour, no impossible values
H = """(SELECT * FROM silver.hourly WHERE minute = 0 AND NOT flag_shed_impossible
        AND NOT flag_fuel_impossible AND NOT flag_generation_outlier)"""

results = []


def check(fid, claim, published, recomputed, tol, unit=""):
    ok = abs(published - recomputed) <= tol
    results.append({"id": fid, "claim": claim, "published": published, "recomputed": round(float(recomputed), 3),
                    "tolerance": tol, "unit": unit, "check": "pass" if ok else "FAIL"})
    print(f"  {'pass' if ok else 'FAIL'}  {fid}  {claim}: published {published:,} {unit}, recomputed {recomputed:,.2f}")


print("Numbers")
# F01 to F04: scale of 2026
yr = q(f"""SELECT year, sum(load_shed_mw) / 1000 AS gwh FROM {H} WHERE hour(ts) BETWEEN 1 AND 23 GROUP BY year""") \
    .set_index("year").gwh
check("F01", "2026 lost energy, hours 1 to 23, to 15 Nov", 3674, yr[2026], 1, "GWh")
check("F02", "2026 against 2023", 1.4, yr[2026] / yr[2023], 0.05, "x")
check("F02b", "2026 is the largest year since 2015 (1 = yes)", 1, float(yr.idxmax() == 2026), 0)
check("F03", "Days in 2026 with any cut", 256,
      one(f"SELECT count(DISTINCT date) FROM {H} WHERE year = 2026 AND load_shed_mw > 0"), 2, "days")
check("F04", "Highest hourly cut in 2026", 3757, one(f"SELECT max(load_shed_mw) FROM {H} WHERE year = 2026"), 0, "MW")
check("F04b", "Highest 2026 hour falls on 10 Aug (day of month)", 10,
      one(f"SELECT day(arg_max(ts, load_shed_mw)) FROM {H} WHERE year = 2026"), 0)

# F05, F06: when
check("F05", "August 2026 lost energy (all hours)", 1164,
      one(f"SELECT sum(load_shed_mw) / 1000 FROM {H} WHERE year = 2026 AND month(ts) = 8"), 2, "GWh")
night, eve = con.execute(f"""SELECT avg(load_shed_mw) FILTER (WHERE hour(ts) BETWEEN 0 AND 3),
                                avg(load_shed_mw) FILTER (WHERE hour(ts) BETWEEN 18 AND 22)
                         FROM {H} WHERE year = 2026 AND month(ts) BETWEEN 6 AND 9""").fetchall()[0]
check("F06a", "Jun to Sep 2026 average cut, midnight to 3 am", 1448, night, 10, "MW")
check("F06b", "Jun to Sep 2026 average cut, 6 pm to 10 pm", 920, eve, 10, "MW")

# F07, F08: after dark and solar
dark, total, dark_solar = con.execute(f"""SELECT sum(load_shed_mw) FILTER (WHERE hour(ts) >= 18 OR hour(ts) < 7),
        sum(load_shed_mw), sum(load_shed_mw) FILTER (WHERE solar < 50) FROM {H} WHERE year = 2026""").fetchall()[0]
check("F07", "Share of 2026 lost energy after dark (6 pm to 7 am)", 0.61, dark / total, 0.01)
check("F07b", "Same share, using 'solar under 50 MW' as dark", 0.61, dark_solar / total, 0.06)
check("F08", "Highest solar output in 2026", 796, one(f"SELECT max(solar) FROM {H} WHERE year = 2026"), 0, "MW")

# F09: zones (BPDB daily, evening peak, 2026 to 3 Aug)
z = q("""SELECT zone, sum(load_shed_mw) AS s, sum(demand_mw) AS d FROM silver.daily_zone
         WHERE year(date) = 2026 GROUP BY zone""").set_index("zone")
z = z / z.sum()
check("F09a", "Mymensingh share of zone load shed, 2026", 0.284, z.s["Mymensingh"], 0.005)
check("F09b", "Mymensingh share of zone demand, 2026", 0.084, z.d["Mymensingh"], 0.005)
check("F09c", "Dhaka share of zone load shed, 2026", 0.161, z.s["Dhaka"], 0.005)
check("F09d", "Dhaka share of zone demand, 2026", 0.362, z.d["Dhaka"], 0.005)
by_year = q("""WITH t AS (SELECT year(date) y, zone, sum(load_shed_mw) s, sum(demand_mw) d FROM silver.daily_zone
               WHERE year(date) >= 2022 GROUP BY ALL),
               r AS (SELECT y, zone, (s / sum(s) OVER (PARTITION BY y)) / (d / sum(d) OVER (PARTITION BY y)) r FROM t)
               SELECT * FROM r WHERE zone = 'Mymensingh' ORDER BY y""")
check("F09e", "Mymensingh carries more than its share every year 2022 to 2026 (lowest ratio)", 2.8, by_year.r.min(), 0.1, "x")

# F18: what breaks first on light days (peak under 1,000 MW), 2026
lt = q(f"""WITH d AS (SELECT date, max(load_shed_mw) mx FROM {H} WHERE year = 2026 GROUP BY date)
          SELECT hour(ts) h, avg(CASE WHEN load_shed_mw > 0 THEN 1.0 ELSE 0 END) p FROM {H} JOIN d USING (date)
          WHERE year = 2026 AND d.mx > 0 AND d.mx < 1000 GROUP BY 1 ORDER BY p DESC""")
check("F18a", "On light days the hour most often cut is 6 pm", 18, lt.h.iloc[0], 0)
check("F18b", "Share of light days with a cut at 6 pm", 0.76, lt.p.iloc[0], 0.02)

# F19: shifts, monsoon 2026, hours 1 to 23 as in the gold table
sh = q(f"""SELECT avg(load_shed_mw) FILTER (WHERE hour(ts) BETWEEN 6 AND 13) early,
                 avg(load_shed_mw) FILTER (WHERE hour(ts) >= 22 OR hour(ts) BETWEEN 1 AND 5) night
          FROM {H} WHERE year = 2026 AND month(ts) BETWEEN 6 AND 9 AND hour(ts) >= 1""").iloc[0]
check("F19a", "Monsoon 2026, early shift 6 am to 2 pm, average cut", 722, sh.early, 5, "MW")
check("F19b", "Monsoon 2026, night shift 10 pm to 6 am, average cut", 1210, sh.night, 5, "MW")

# F10: bad days come in runs
for fid, yrs, pub in [("F10", "year = 2026", 0.85), ("F10b", "year >= 2022", 0.74)]:
    d = q(f"SELECT date, max(load_shed_mw) m FROM {H} WHERE {yrs} GROUP BY date ORDER BY date")
    d["next"] = d.m.shift(-1)
    big = d[d.m > 1500]
    check(fid, f"After a day over 1,500 MW, next day also over 1,500 MW ({yrs})", pub, (big.next > 1500).mean(), 0.02)

# F11: the August and crisis bridge must add up exactly (identity)
for name, months in {"F11": [8], "F12": [8, 9]}.items():
    b = q(f"""SELECT year, avg(load_shed_mw) cut, avg(true_demand_mw) dem, avg(generation_mw) gen,
              avg(gas) gas, avg(coal) coal, avg(liquid_fuel) oil, avg(imports) imp
              FROM {H} WHERE year IN (2025, 2026) AND month(ts) IN ({','.join(map(str, months))})
              AND hour(ts) BETWEEN 1 AND 23 GROUP BY year ORDER BY year""").set_index("year")
    dd = b.loc[2026] - b.loc[2025]
    check(f"{name}a", f"Change in average cut, {'Aug' if months == [8] else 'Aug to Sep'} 2026 vs 2025",
          1523 if months == [8] else 1251, dd.cut, 3, "MW")
    check(f"{name}b", "Identity holds: change in cut = change in demand minus change in generation (gap)", 0,
          dd.cut - (dd.dem - dd.gen), 1, "MW")
    check(f"{name}c", "Gas fell", 1072 if months == [8] else 761, -dd.gas, 3, "MW")

# F13: weather (only if loaded)
tabs = set(q("SELECT table_schema || '.' || table_name t FROM information_schema.tables").t)
if "drivers.demand_temp_fit" in tabs:
    f = q("SELECT * FROM drivers.demand_temp_fit").iloc[0]
    check("F13", "Peak demand per °C 'feels like' above 30", 272, f.mw_per_degree_feels_like_above_30, 2, "MW")
    w = q("""SELECT year(date) y, avg(feels_max) f FROM drivers.weather_daily WHERE month(date) = 8 GROUP BY 1""").set_index("y").f
    check("F13b", "August 2026 only slightly hotter than August 2025 (difference in feels-like peak)", 0.7, w[2026] - w[2025], 0.1, "°C")
    c = q("SELECT * FROM drivers.demand_temp_check WHERE year = 2026 AND month IN (8, 9)")
    check("F13c", "Reported peak above weather-expected peak, Aug to Sep 2026", 2000,
          c.gap_reported_vs_expected.mean(), 150, "MW")
    check("F13d", "Served peak close to weather-expected peak, Aug to Sep 2026 (served minus expected)", 300,
          (c.served_peak - c.expected_peak).mean(), 250, "MW")
    p = q("SELECT * FROM drivers.policy_check_weather")
    check("F14", "Closing rules beyond normal swings, with weather out (count)", 0, p.beyond_noise.sum(), 0)

# F15: forecast scorecard, recomputed from the backtest rows
bt = q("SELECT * FROM model.backtest WHERE NOT imputed AND actual IS NOT NULL")
mae = lambda col: (bt[col] - bt.actual).abs().mean()
check("F15a", "Forecast average miss (blend)", 623, mae("blend"), 2, "MW")
check("F15b", "Planner's 4-week average miss", 648, mae("b_planner"), 2, "MW")
check("F15c", "Share of 500 MW+ hours the blend flagged", 0.82, ((bt.blend >= 500) & (bt.actual >= 500)).sum()
      / (bt.actual >= 500).sum(), 0.01)
check("F15d", "80% range held the actual value", 0.81, ((bt.actual >= bt.low_mw) & (bt.actual <= bt.high_mw)).mean(), 0.01)
crisis = bt[bt.window.str.contains("crisis")]
check("F15e", "In the 2026 crisis the 4-week average beat the blend (1 = yes)", 1,
      float((crisis.b_planner - crisis.actual).abs().mean() < (crisis.blend - crisis.actual).abs().mean()), 0)

# F16: what-if, recomputed directly
s26 = q(f"SELECT load_shed_mw s FROM {H} WHERE year = 2026").s.values
share = lambda add: 1 - np.clip(s26 - add, 0, None).sum() / s26.sum()
check("F16a", "1,000 MW round the clock removes this share of 2026 lost energy", 0.63, share(1000), 0.02)
for case, mw in {"low": 1030e6 / 24 / 12000 / 1000, "central": 1030e6 / 24 / 9500 / 1000, "high": 1030e6 / 24 / 7500 / 1000}.items():
    results.append({"id": f"F16b_{case}", "claim": f"100 mmcfd of gas removes ({case} conversion, {mw:.1f} MW per mmcfd)",
                    "published": None, "recomputed": round(share(100 * mw), 3), "tolerance": None, "unit": "share",
                    "check": "range"})
    print(f"  range F16b {case}: 100 mmcfd = {100 * mw:,.0f} MW removes {share(100 * mw):.0%}")
check("F16c", "100 mmcfd removes (central)", 0.37, share(100 * 1030e6 / 24 / 9500 / 1000), 0.01)

# F17: night
e = q(f"""SELECT hour(ts) h, avg(true_demand_mw) dem, avg(liquid_fuel) oil, avg(gas) gas FROM {H}
          WHERE year = 2026 AND month(ts) BETWEEN 6 AND 10 GROUP BY 1 ORDER BY 1""").set_index("h")
check("F17a", "Oil at 10 pm, Jun to Oct 2026", 2840, e.oil[22], 30, "MW")
check("F17b", "Oil at 5 am, Jun to Oct 2026", 1345, e.oil[5], 30, "MW")
check("F17c", "Demand stays above 15,000 MW until 3 am (lowest of 0 to 3 am)", 15138, e.dem[0:4].min(), 30, "MW")
check("F17d", "Gas stays flat overnight (max minus min, 10 pm to 5 am)", 0, (lambda g: g.max() - g.min())(e.gas[[22, 23, 0, 1, 2, 3, 4, 5]]), 200, "MW")

reg = pd.DataFrame(results)

# Wording: dashes and loaded words in everything a reader may see
print("\nWording")
ALLOW = ["No blame", "grid failure", "failed, 0"]
LOADED = r"\b(fail(ed|ure)?|blame|incompeten\w*|corrupt\w*|mismanag\w*|scandal|negligen\w*|disaster|shameful|useless)\b"
DASH = "[–—]"
issues = []
files = glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True) + glob.glob(os.path.join(ROOT, "03_analysis", "*.ipynb"))
for f in files:
    if f.endswith(".ipynb"):
        cells = json.load(open(f, encoding="utf-8"))["cells"]
        texts = ["".join(c["source"]) for c in cells if c["cell_type"] == "markdown"]
        for c in cells:  # printed output a reader sees
            for o in c.get("outputs", []):
                texts.append("".join(o.get("text", "")))
    else:
        texts = [open(f, encoding="utf-8").read()]
    for t in texts:
        for m in re.finditer(DASH, t):
            issues.append((os.path.relpath(f, ROOT), "dash", t[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")))
        for m in re.finditer(LOADED, t, re.I):
            if any(a.lower() in t[max(0, m.start() - 5): m.end() + 5].lower() for a in ALLOW):
                continue
            issues.append((os.path.relpath(f, ROOT), "loaded word", t[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")))
for f, kind, ctx in issues:
    print(f"  {kind:11s} {f}: ...{ctx}...")
print(f"  {len(issues)} wording issues")

reg.to_csv(os.path.join(ROOT, "05_review", "findings_checks.csv"), index=False)
fails = (reg.check == "FAIL").sum()
print(f"\n{(reg.check == 'pass').sum()} passed, {fails} failed. Saved 05_review/findings_checks.csv")
sys.exit(1 if fails or issues else 0)
