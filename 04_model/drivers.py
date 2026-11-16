"""Lights Out · Phase 4 drivers: why the cuts happened and what would have reduced them.

Writes schema `drivers` into 01_data/processed/lights_out.duckdb and CSVs to 01_data/processed/drivers/.

Tables
- bridge_monthly   Each month vs the same days a year earlier: change in average cut split into demand and each
                   supply source. Exact identity: cut = demand - generation, generation = sum of sources.
- bridge_crisis    The Aug to Sep 2026 crisis vs Aug to Sep 2025, for all hours, evening (18 to 22) and night (1 to 5).
- evening_gap      2026 average by hour (Jun to Oct): demand, each source and the cut.
- solar_profile    Average solar output per MW of peak, by month and hour (for the what-if sliders).
- what_if          Lever curves on the real 2026 hours: energy cut and hours with a cut, for extra gas (mmcfd),
                   extra flat supply (MW), extra solar (MW) and evening demand saving (MW).
- gas_conversion   The MW per mmcfd assumption, low, central and high.
- demand_temp      (only when weather is present) daily peak demand vs temperature, and the Aug 2026 check.

Run: python 04_model\\drivers.py   (after 02_pipeline\\run.py)
"""
import glob
import os

import duckdb
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB = os.path.join(ROOT, "01_data", "processed", "lights_out.duckdb")
OUT = os.path.join(ROOT, "01_data", "processed", "drivers")
WEATHER = os.path.join(ROOT, "01_data", "raw", "weather")

# Gas to power. 1 mmcfd is about 1,030 MMBtu a day (43 MMBtu an hour). MW = 42,900 / heat rate (Btu per kWh).
# Bangladesh's gas fleet mixes combined cycle (about 7,500), old steam and open cycle (11,000 to 13,000).
HEAT_RATES = {"low (old plants, 12,000 Btu/kWh)": 12000, "central (fleet mix, 9,500 Btu/kWh)": 9500,
              "high (combined cycle, 7,500 Btu/kWh)": 7500}
MMBTU_PER_MMCF = 1030
GAS_MW_PER_MMCFD = {k: MMBTU_PER_MMCF * 1e6 / 24 / hr / 1000 for k, hr in HEAT_RATES.items()}
CENTRAL = GAS_MW_PER_MMCFD["central (fleet mix, 9,500 Btu/kWh)"]

SOURCES = {"gas": "gas", "coal": "coal", "oil": "liquid_fuel", "imports": "imports", "hydro_solar_wind": "ren",
           "other": "parts_gap_mw"}


def bridge(cur, prev, label):
    """Change in average cut, split. Supply sources enter with a minus sign: more supply means less cut."""
    row = {"period": label, "hours_now": len(cur), "hours_before": len(prev),
           "cut_before_mw": prev.load_shed_mw.mean(), "cut_now_mw": cur.load_shed_mw.mean(),
           "change_in_cut_mw": cur.load_shed_mw.mean() - prev.load_shed_mw.mean(),
           "from_demand_mw": cur.true_demand_mw.mean() - prev.true_demand_mw.mean()}
    for k, col in SOURCES.items():
        row[f"from_{k}_mw"] = -(cur[col].mean() - prev[col].mean())
    return row


def main():
    con = duckdb.connect(DB)
    h = con.sql("""SELECT ts, date, hour, year, month, load_shed_mw, true_demand_mw, generation_mw, gas, coal,
                          liquid_fuel, imports, hydro + solar + wind AS ren, solar, parts_gap_mw
                   FROM gold.hourly
                   WHERE NOT flag_shed_impossible AND NOT flag_fuel_impossible AND NOT flag_generation_outlier""").df()
    h["date"] = pd.to_datetime(h.date)
    h = h.fillna({"parts_gap_mw": 0})
    tables = {}

    # 1. Monthly bridge, like for like: same days of month, hours 01 to 23 (the download has no 00:00)
    c = h[h.hour.between(1, 23)]
    rows = []
    for (y, m), cur in c[c.year >= 2025].groupby(["year", "month"]):
        days = cur.date.dt.day.unique()
        prev = c[(c.year == y - 1) & (c.month == m) & c.date.dt.day.isin(days)]
        if len(prev) > 24 * 5:
            rows.append(bridge(cur, prev, f"{y}-{m:02d}") | {"year": y, "month": m, "days": len(days)})
    tables["bridge_monthly"] = pd.DataFrame(rows)

    # 2. The crisis, Aug to Sep 2026 vs Aug to Sep 2025, by time of day
    rows = []
    for name, hrs in {"all hours (1 to 23)": range(1, 24), "evening (18 to 22)": range(18, 23),
                      "night (1 to 5)": range(1, 6), "daytime (9 to 16)": range(9, 17)}.items():
        cur = c[(c.year == 2026) & c.month.isin([8, 9]) & c.hour.isin(hrs)]
        prev = c[(c.year == 2025) & c.month.isin([8, 9]) & c.hour.isin(hrs)]
        rows.append(bridge(cur, prev, name))
    tables["bridge_crisis"] = pd.DataFrame(rows)

    # 3. Evening gap: 2026 Jun to Oct by hour (all 24 hours, the collector has 00:00)
    e = h[(h.year == 2026) & h.month.between(6, 10)]
    tables["evening_gap"] = e.groupby("hour")[["true_demand_mw", "generation_mw", "load_shed_mw", "gas", "coal",
                                               "liquid_fuel", "imports", "solar"]].mean().reset_index()

    # 4. Solar shape: output per MW of that month's peak solar hour, 2026
    s = h[h.year == 2026].copy()
    s["peak"] = s.groupby("month").solar.transform("max")
    sp = s.assign(per_mw=s.solar / s.peak).groupby(["month", "hour"]).per_mw.mean().reset_index()
    tables["solar_profile"] = sp

    # 5. What-if on the real 2026 hours (all 24 hours, Jan to the latest day)
    w = h[h.year == 2026][["ts", "month", "hour", "load_shed_mw"]].merge(sp, on=["month", "hour"], how="left")
    w["per_mw"] = w.per_mw.fillna(0)
    base_gwh = w.load_shed_mw.sum() / 1000
    levers = {
        "extra gas (mmcfd)": (np.arange(0, 701, 25), lambda x: np.full(len(w), x * CENTRAL)),
        "extra flat supply (MW)": (np.arange(0, 3001, 100), lambda x: np.full(len(w), float(x))),
        "extra solar (MW)": (np.arange(0, 5001, 250), lambda x: x * w.per_mw.values),
        "evening saving 18 to 22 (MW)": (np.arange(0, 1501, 100), lambda x: np.where(w.hour.between(18, 22), x, 0.0)),
    }
    rows = []
    for lever, (xs, add) in levers.items():
        for x in xs:
            left = np.clip(w.load_shed_mw.values - add(x), 0, None)
            rows.append({"lever": lever, "amount": float(x), "energy_cut_gwh": left.sum() / 1000,
                         "energy_avoided_share": 1 - left.sum() / 1000 / base_gwh,
                         "hours_with_cut_500": int((left >= 500).sum()), "peak_cut_mw": left.max()})
    tables["what_if"] = pd.DataFrame(rows)
    tables["gas_conversion"] = pd.DataFrame([{"case": k, "heat_rate_btu_per_kwh": HEAT_RATES[k], "mw_per_mmcfd": v}
                                             for k, v in GAS_MW_PER_MMCFD.items()])

    # 6. Demand vs temperature (needs tools/weather_collect.py)
    files = glob.glob(os.path.join(WEATHER, "weather_*.csv"))
    if files:
        tables.update(demand_temperature(con, h, files))
    else:
        print("No weather files yet: skipping demand vs temperature (run tools\\weather_collect.py).")

    con.execute("CREATE SCHEMA IF NOT EXISTS drivers")
    os.makedirs(OUT, exist_ok=True)
    for name, df in tables.items():
        con.register("tmp", df)
        con.execute(f"CREATE OR REPLACE TABLE drivers.{name} AS SELECT * FROM tmp")
        con.unregister("tmp")
        df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
        print(f"  drivers.{name:16s} {len(df):>6,} rows")
    con.close()


def demand_temperature(con, h, files):
    """Daily peak demand against a demand-weighted temperature, with a yearly growth term.

    Fit on 2023 to 2025 days (holidays and Fri/Sat out), then ask: given the weather of Jun to Oct 2026, what peak
    demand would the 2023 to 2025 pattern expect, and how far above it is the reported 2026 figure?
    """
    wx = pd.concat([pd.read_csv(f, parse_dates=["ts"]) for f in files], ignore_index=True)
    con.register("wx_raw", wx)
    con.execute("CREATE OR REPLACE TABLE silver.weather_hourly AS SELECT * FROM wx_raw")
    con.unregister("wx_raw")
    # zone weights = each zone's share of demand (BPDB daily, 2023 to 2025)
    wts = con.sql("""SELECT zone, avg(demand_mw) AS d FROM silver.daily_zone
                     WHERE year(date) BETWEEN 2023 AND 2025 GROUP BY zone""").df()
    wts["w"] = wts.d / wts.d.sum()
    wx = wx.merge(wts[["zone", "w"]], on="zone")
    wx["date"] = wx.ts.dt.normalize()
    hourly_t = wx.assign(t=wx.temperature_2m * wx.w, at=wx.apparent_temperature * wx.w) \
                 .groupby("ts")[["t", "at"]].sum().reset_index()
    hourly_t["date"] = hourly_t.ts.dt.normalize()
    daily_t = hourly_t.groupby("date").agg(t_max=("t", "max"), t_mean=("t", "mean"), feels_max=("at", "max")).reset_index()

    d = h.groupby("date").agg(peak_demand=("true_demand_mw", "max"), peak_gen=("generation_mw", "max"),
                              hours=("hour", "count")).reset_index()
    cal = con.sql("""SELECT date, CASE WHEN coalesce(holiday_cat, 0) > 0 OR date IN (SELECT date FROM silver.holidays)
                            THEN 'holiday' END AS holiday_name FROM gold.daily""").df()
    cal["date"] = pd.to_datetime(cal.date)
    d = d.merge(daily_t, on="date").merge(cal, on="date", how="left")
    d = d[(d.hours >= 23) & d.holiday_name.isna() & ~d.date.dt.dayofweek.isin([4, 5])]
    d["year"] = d.date.dt.year
    d["cool"] = np.clip(d.feels_max - 30, 0, None)        # cooling need above 30 °C feels-like
    d["month"] = d.date.dt.month

    fit = d[d.year.between(2023, 2025) & d.month.between(4, 10)]
    X = lambda df: np.column_stack([np.ones(len(df)), df.cool, df.year - 2024])
    beta, *_ = np.linalg.lstsq(X(fit), fit.peak_demand, rcond=None)
    resid_sd = (fit.peak_demand - X(fit) @ beta).std()

    chk = d[d.year.between(2023, 2026) & d.month.between(4, 10)].copy()
    chk["expected_peak"] = X(chk) @ beta
    out = chk.groupby(["year", "month"]).agg(days=("date", "count"), feels_max=("feels_max", "mean"),
                                              reported_peak=("peak_demand", "mean"), served_peak=("peak_gen", "mean"),
                                              expected_peak=("expected_peak", "mean")).reset_index()
    out["gap_reported_vs_expected"] = out.reported_peak - out.expected_peak
    coef = pd.DataFrame([{"intercept_2024": beta[0], "mw_per_degree_feels_like_above_30": beta[1],
                          "mw_growth_per_year": beta[2], "residual_sd_mw": resid_sd, "fit_days": len(fit)}])
    print(f"  demand vs temperature: {beta[1]:,.0f} MW per °C feels-like above 30; growth {beta[2]:,.0f} MW a year")
    pol = policy_with_weather(con, h, hourly_t, wx)
    return {"demand_temp_fit": coef, "demand_temp_check": out, "weather_daily": daily_t} | pol


def policy_with_weather(con, h, hourly_t, wx):
    """Phase 2 policy check again, with weather taken out.

    The ratio of evening (19 to 22) to afternoon (14 to 17) demand moves with the weather: a rainy afternoon or a hot
    evening changes it with no rule at all. Fit that link on 2025 (Apr to Oct, a year with no closing rules), take it
    out of 2026, then compare 7 workdays before and after each rule. The noise band comes from doing the same at every
    2025 date (placebo dates).
    """
    rain = wx.assign(r=wx.precipitation * wx.w).groupby("ts").r.sum().rename("rain").reset_index()
    t = hourly_t.merge(rain, on="ts")
    t["hour"] = t.ts.dt.hour
    aft, eve = t[t.hour.between(14, 17)], t[t.hour.between(19, 22)]
    wd = pd.concat([aft.groupby("date").at.mean().rename("feels_aft"), eve.groupby("date").at.mean().rename("feels_eve"),
                    aft.groupby("date").rain.sum().rename("rain_aft"), eve.groupby("date").rain.sum().rename("rain_eve")],
                   axis=1).reset_index()
    dd = pd.concat([h[h.hour.between(19, 22)].groupby("date").true_demand_mw.mean().rename("eve"),
                    h[h.hour.between(14, 17)].groupby("date").true_demand_mw.mean().rename("aft")], axis=1).reset_index()
    hol = set(pd.to_datetime(con.sql("SELECT date FROM silver.holidays").df().date)) | set(pd.to_datetime(
        con.sql("SELECT date FROM gold.daily WHERE coalesce(holiday_cat, 0) > 0").df().date))
    d = dd.merge(wd, on="date").dropna()
    d = d[~d.date.isin(hol)]
    d["ratio"] = d.eve / d.aft
    d["weekend"] = d.date.dt.dayofweek.isin([4, 5]).astype(float)
    d["mon"] = d.date.dt.month
    X = lambda x: np.column_stack([np.ones(len(x)), x.feels_eve - x.feels_aft, x.feels_aft, x.rain_aft, x.rain_eve, x.weekend])
    fit = d[(d.date.dt.year == 2025) & d.mon.between(3, 10)]
    beta, *_ = np.linalg.lstsq(X(fit), fit.ratio, rcond=None)
    d["resid"] = d.ratio - X(d) @ beta

    def effect(day, pool):
        b = pool[(pool.date < day) & (pool.date >= day - pd.Timedelta(days=21))].nlargest(7, "date")
        a = pool[(pool.date > day) & (pool.date <= day + pd.Timedelta(days=21))].nsmallest(7, "date")
        if len(a) < 5 or len(b) < 5:
            return None
        return {"raw_mw": (a.ratio.mean() - b.ratio.mean()) * a.aft.mean(),
                "weather_adjusted_mw": (a.resid.mean() - b.resid.mean()) * a.aft.mean()}

    p25 = d[(d.date.dt.year == 2025) & d.mon.between(3, 10)]
    plac = pd.DataFrame([e for day in p25.date.iloc[10:-10] if (e := effect(day, d))])
    lo, hi = plac.weather_adjusted_mw.quantile([0.05, 0.95])
    ev = con.sql("SELECT date, event, closing_hour FROM silver.events WHERE type = 'rule' AND date IS NOT NULL").df()
    rows = []
    for _, r in ev.iterrows():
        e = effect(pd.Timestamp(r.date), d)
        if e:
            rows.append({"rule_date": r.date, "event": r.event, "closing_hour": r.closing_hour, **e,
                         "noise_low_mw": lo, "noise_high_mw": hi,
                         "beyond_noise": not (lo <= e["weather_adjusted_mw"] <= hi)})
    print(f"  policy check with weather: noise band {lo:,.0f} to {hi:,.0f} MW; "
          f"{sum(r['beyond_noise'] for r in rows)} of {len(rows)} rules beyond it")
    return {"policy_check_weather": pd.DataFrame(rows),
            "policy_placebo": plac.describe().reset_index()}


if __name__ == "__main__":
    main()
