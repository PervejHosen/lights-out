"""Lights Out, Phase 3: hourly load shedding forecast for the next 7 days.

    python 04_model\\forecast.py          (after 02_pipeline\\run.py; needs: pip install lightgbm duckdb pandas)

How it works
- A forecast is made at midnight for the next 168 hours, using only data before midnight.
- Two baselines a planner could use: (1) same hour last week; (2) the average for that hour over the last 4 weeks.
- One LightGBM model for all hours and horizons. The final forecast blends it 50/50 with the 4-week average,
  which beat both in the backtest; the 80% range comes from the blend's real backtest errors by day ahead.
- Cut risk per hour: the share of the last 28 days on which that hour had 500 MW or more cut.
- Rolling-origin backtest: for each test window the model is trained only on data before the window starts.
- Results go into the DuckDB database (schema `model`) and to 01_data/processed/model/*.csv.
"""
import os
import time

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB = os.path.join(ROOT, "01_data", "processed", "lights_out.duckdb")
OUT = os.path.join(ROOT, "01_data", "processed", "model")
os.makedirs(OUT, exist_ok=True)

H = 168                      # forecast length, hours
BIG = 500                    # an hour with 500 MW or more cut counts as a "significant cut"
WINDOWS = {                  # test windows: daily forecasts made at midnight on each day in the window
    "2023 summer (1 Jun to 12 Jul)": ("2023-06-01", "2023-07-12"),
    "2024 heat (15 Apr to 26 May)": ("2024-04-15", "2024-05-26"),
    "2026 early monsoon (1 Jun to 12 Jul)": ("2026-06-01", "2026-07-12"),
    "2026 crisis (1 Aug to 11 Sep)": ("2026-08-01", "2026-09-11"),
}
PARAMS = dict(n_estimators=500, learning_rate=0.04, num_leaves=63, min_child_samples=80, subsample=0.8,
              subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=7)


def load():
    con = duckdb.connect(DB, read_only=True)
    h = con.sql("""SELECT ts, load_shed_mw AS shed, true_demand_mw AS demand, gas, liquid_fuel AS oil, coal, imports
                   FROM gold.hourly WHERE ts >= TIMESTAMP '2019-01-01' ORDER BY ts""").df()
    hol = set(pd.to_datetime(con.sql("SELECT date FROM silver.holidays").df().date).dt.date)
    con.close()
    grid = pd.DataFrame({"ts": pd.date_range(h.ts.min().normalize(), h.ts.max(), freq="h")})
    h = grid.merge(h, on="ts", how="left")
    h["imputed"] = h.shed.isna()
    cols = ["shed", "demand", "gas", "oil", "coal", "imports"]
    h[cols] = h[cols].interpolate(limit=3, limit_direction="both")      # mostly the missing 00:00 before 2026
    h["shed"] = h.shed.clip(lower=0)
    h["is_holiday"] = h.ts.dt.date.isin(hol)
    return h.set_index("ts"), hol


def origin_features(h, origins):
    """Features known at each origin (midnight), from the history before it."""
    s, d = h.shed, h.demand
    daily = pd.DataFrame({
        "shed_mean": s.resample("D").mean(), "shed_max": s.resample("D").max(),
        "shed_pct": (s > 0).resample("D").mean(), "dem_mean": d.resample("D").mean(),
        "gas": h.gas.resample("D").mean(), "oil": h.oil.resample("D").mean(),
        "coal": h.coal.resample("D").mean(), "imports": h.imports.resample("D").mean()})
    days = pd.date_range(daily.index.min(), daily.index.max() + pd.Timedelta(days=1), freq="D")
    daily = daily.reindex(days)                              # add tomorrow, so it can be a forecast origin
    p = daily.shift(1)                                       # day before the origin
    f = pd.DataFrame(index=daily.index)
    f["shed_1d_mean"], f["shed_1d_max"] = p.shed_mean, p.shed_max
    f["shed_7d_mean"] = p.shed_mean.rolling(7).mean()
    f["shed_7d_max"] = p.shed_max.rolling(7).max()
    f["shed_7d_pct_hours"] = p.shed_pct.rolling(7).mean()
    f["shed_28d_mean"] = p.shed_mean.rolling(28).mean()
    f["shed_trend"] = p.shed_mean.rolling(3).mean() - p.shed_mean.shift(3).rolling(4).mean()
    f["dem_7d_mean"] = p.dem_mean.rolling(7).mean()
    f["dem_trend"] = p.dem_mean.rolling(3).mean() - p.dem_mean.shift(3).rolling(4).mean()
    for c in ["gas", "oil", "coal", "imports"]:
        f[f"{c}_1d"] = p[c]
        f[f"{c}_7d"] = p[c].rolling(7).mean()
    f["gas_drop"] = p.gas - p.gas.rolling(28).mean()
    # hour-of-day profile over the last 7 days (shed and demand), one column per hour
    hod_s = s.groupby([s.index.normalize(), s.index.hour]).mean().unstack()
    hod_d = d.groupby([d.index.normalize(), d.index.hour]).mean().unstack()
    hod_s, hod_d = hod_s.reindex(days), hod_d.reindex(days)
    prof_s = hod_s.shift(1).rolling(7).mean(); prof_d = hod_d.shift(1).rolling(7).mean()
    prof_s28 = hod_s.shift(1).rolling(28).mean()
    # cut risk: share of the last 28 days on which this hour had a significant cut (500 MW or more)
    big = (s >= BIG).astype(float)
    hod_b = big.groupby([big.index.normalize(), big.index.hour]).mean().unstack().reindex(days)
    risk28 = hod_b.shift(1).rolling(28).mean()
    return f.loc[f.index.isin(origins)], prof_s, prof_d, prof_s28, risk28


def make_rows(h, origins):
    f, prof_s, prof_d, prof_s28, risk28 = origin_features(h, origins)
    rows = []
    for o in origins:
        o = pd.Timestamp(o)
        if o not in f.index:
            continue
        ts = pd.date_range(o, periods=H, freq="h")
        r = pd.DataFrame({"ts": ts, "origin": o})
        r["horizon_day"] = (r.ts - o).dt.days
        r["hour"], r["dow"], r["month"] = r.ts.dt.hour, r.ts.dt.dayofweek, r.ts.dt.month
        r["is_weekend"] = r.dow.isin([4, 5])                      # Friday, Saturday
        r["is_holiday"] = h.is_holiday.reindex(ts).fillna(False).astype(bool).values
        doy = r.ts.dt.dayofyear; r["doy_sin"], r["doy_cos"] = np.sin(2*np.pi*doy/365), np.cos(2*np.pi*doy/365)
        for c in f.columns:
            r[c] = f.at[o, c]
        r["shed_same_hour_7d"] = prof_s.loc[o].reindex(r.hour).values if o in prof_s.index else np.nan
        r["dem_same_hour_7d"] = prof_d.loc[o].reindex(r.hour).values if o in prof_d.index else np.nan
        r["shed_last_week"] = h.shed.reindex(ts - pd.Timedelta(days=7)).values      # always before the origin
        # baselines
        r["b_last_week"] = r.shed_last_week
        r["b_planner"] = prof_s28.loc[o].reindex(r.hour).values if o in prof_s28.index else np.nan
        r["cut_risk"] = risk28.loc[o].reindex(r.hour).values if o in risk28.index else np.nan
        r["actual"] = h.shed.reindex(ts).values
        r["imputed"] = h.imputed.reindex(ts).fillna(True).astype(bool).values
        rows.append(r)
    return pd.concat(rows, ignore_index=True)


FEATURES = None


def fit_predict(train, test):
    X = train[FEATURES]; y = train.actual
    keep = y.notna()
    m = lgb.LGBMRegressor(objective="regression", **PARAMS).fit(X[keep], y[keep])
    out = test.copy()
    out["lgbm"] = np.clip(m.predict(test[FEATURES]), 0, None)
    # Final forecast: half model, half the planner's 4-week average. In the backtest the blend beat both on
    # their own; the model alone fell behind in the 2026 crisis, when sudden supply shocks broke the old patterns.
    out["blend"] = 0.5 * out.lgbm + 0.5 * out.b_planner.fillna(out.lgbm)
    return out, m


def score(df, method):
    d = df[~df.imputed & df.actual.notna() & df[method].notna()]
    err = (d[method] - d.actual).abs()
    big_a, big_p = d.actual >= BIG, d[method] >= BIG
    return pd.Series({
        "MAE (MW)": err.mean(),
        "WAPE": err.sum() / d.actual.sum(),
        "right call on 500 MW+ hours": (big_a == big_p).mean(),
        "500 MW+ hours caught": (big_a & big_p).sum() / max(big_a.sum(), 1),
        "false alarms": (~big_a & big_p).sum() / max(big_p.sum(), 1),
        "hours scored": len(d)})


def main():
    global FEATURES
    t0 = time.time()
    h, _ = load()
    all_origins = pd.date_range("2019-02-01", h.index.max().normalize() + pd.Timedelta(days=1), freq="D")
    rows = make_rows(h, all_origins)
    FEATURES = [c for c in rows.columns
                if c not in ("ts", "origin", "actual", "imputed", "b_last_week", "b_planner", "cut_risk")]
    print(f"rows: {len(rows):,}  features: {len(FEATURES)}  ({time.time()-t0:.0f}s)")
    methods = [("b_last_week", "Same hour last week"), ("b_planner", "4-week hour average"),
               ("lgbm", "LightGBM model"), ("blend", "Blend (final forecast)")]

    preds, cards = [], []
    for name, (a, b) in WINDOWS.items():
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        train = rows[(rows.ts < a) & (rows.origin <= a - pd.Timedelta(days=7))]   # no target inside or after the window
        test = rows[rows.origin.between(a, b)]
        out, _ = fit_predict(train, test)
        out["window"] = name
        preds.append(out)
        for meth, label in methods:
            cards.append(score(out, meth).rename((name, label)))
        print(f"  {name}: trained on {len(train):,} rows ({time.time()-t0:.0f}s)")

    bt = pd.concat(preds, ignore_index=True)
    card = pd.DataFrame(cards); card.index = pd.MultiIndex.from_tuples(card.index, names=["window", "method"])
    allw = pd.DataFrame({lab: score(bt, m) for m, lab in methods}).T
    d = bt[~bt.imputed & bt.actual.notna()].copy()

    # 80% range from the blend's real backtest errors, grouped by the situation at the origin (average cut over the
    # last 7 days: quiet weeks get narrow ranges, crisis weeks wide ones) and by day ahead (the range is only allowed to widen with each day, so it grows smoothly)
    REGIMES = [-1, 50, 300, 800, 1e9]
    def keys(df):
        return (pd.cut(df.shed_7d_mean, REGIMES, labels=False).fillna(0).astype(int),
                df.horizon_day.astype(int))
    bt["regime"], bt["hgroup"] = keys(bt)
    d["regime"], d["hgroup"] = keys(d)
    d["resid"] = d.actual - d.blend
    q = d.groupby(["regime", "hgroup"]).resid.quantile([0.1, 0.9]).unstack()
    q.columns = ["lo", "hi"]
    q["lo"] = q.groupby(level=0).lo.cummin(); q["hi"] = q.groupby(level=0).hi.cummax()
    bt = bt.merge(q, left_on=["regime", "hgroup"], right_index=True, how="left")
    bt["low_mw"] = (bt.blend + bt.lo).clip(lower=0); bt["high_mw"] = (bt.blend + bt.hi).clip(lower=0)
    d = bt[~bt.imputed & bt.actual.notna()]
    coverage = ((d.actual >= d.low_mw) & (d.actual <= d.high_mw)).mean()
    y = (d.actual >= BIG).astype(float)
    brier_risk = ((d.cut_risk.fillna(0) - y) ** 2).mean()
    by_h = pd.DataFrame({lab: d.assign(e=(d[m] - d.actual).abs()).groupby("horizon_day").e.mean() for m, lab in methods})
    print("\nAll windows together:\n", allw.round(3).to_string())
    print(f"\n80% range coverage (backtest): {coverage:.0%};  cut-risk Brier score: {brier_risk:.3f}")

    # Final model on everything, forecast from the next midnight
    nxt = h.index.max().normalize() + pd.Timedelta(days=1)
    train = rows[rows.origin <= nxt - pd.Timedelta(days=7)]
    test = rows[rows.origin == nxt]
    fc, model = fit_predict(train, test)
    fc["regime"], fc["hgroup"] = keys(fc)
    fc = fc.merge(q, left_on=["regime", "hgroup"], right_index=True, how="left")
    fc["low_mw"] = (fc.blend + fc.lo).clip(lower=0); fc["high_mw"] = (fc.blend + fc.hi).clip(lower=0)
    imp = pd.DataFrame({"feature": FEATURES, "importance": model.booster_.feature_importance("gain")}) \
            .sort_values("importance", ascending=False)
    imp["share"] = imp.importance / imp.importance.sum()
    print(f"\nNext-week forecast from {nxt:%d %b %Y}: peak {fc.blend.max():,.0f} MW, total {fc.blend.sum()/1000:,.1f} GWh")

    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS model")
    tables = {
        "backtest": bt[["window", "origin", "ts", "horizon_day", "actual", "imputed", "b_last_week", "b_planner",
                        "lgbm", "blend", "low_mw", "high_mw", "cut_risk"]],
        "scorecard": card.reset_index(),
        "range_table": q.rename_axis(["regime", "horizon_day"]).reset_index(),
        "scorecard_all": allw.reset_index().rename(columns={"index": "method"})
                             .assign(range_coverage_80=coverage, cut_risk_brier=brier_risk),
        "error_by_horizon": by_h.reset_index(),
        "forecast_next_week": fc[["origin", "ts", "horizon_day", "hour", "blend", "low_mw", "high_mw", "cut_risk", "lgbm", "b_planner"]]
                               .rename(columns={"blend": "forecast_mw", "b_planner": "four_week_avg_mw", "lgbm": "model_mw"}),
        "feature_importance": imp,
    }
    for name, df in tables.items():
        con.register("tmp", df)
        con.execute(f"CREATE OR REPLACE TABLE model.{name} AS SELECT * FROM tmp")
        con.unregister("tmp")
        df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
    con.close()
    print(f"\nSaved model.* tables and CSVs ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
