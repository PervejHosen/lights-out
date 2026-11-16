# 04_model

| Script | Status | What it does |
|---|---|---|
| `forecast.py` | done | 7-day load shedding forecast, scored on four test windows |
| `drivers` | Phase 4 | daily shortfall split by fuel, imports and heat |
| `policy_check` | Phase 4 | matched before and after comparisons for each saving rule, with hourly weather |
| `what_if` | Phase 4 | scenario maths behind the report sliders |

## forecast.py · Q8 (how many MW will be cut each hour of the next 7 days) and Q5 (can cuts be forecast)

### Run

```
pip install lightgbm pandas duckdb
python 04_model\forecast.py
```

It reads `01_data/processed/lights_out.duckdb` (build it first with `python 02_pipeline\run.py`) and takes about a
minute. It writes the `model` schema into the same file and CSVs into `01_data/processed/model/`. 
### Method

- **Forecast setup.** Every forecast is made at midnight for the next 168 hours. It uses only data from before
  midnight.
- **Two baselines.**
  - Same hour last week.
  - The 4-week average for that hour (the planner's rule of thumb).
- **Model.** One LightGBM regression for all 7 days ahead. Its inputs:
  - recent cuts
  - demand
  - gas, oil and coal generation, and imports
  - hour, day of week, weekend, holiday and season
- **Final forecast.** Half the model plus half the 4-week average. This beat both parts on their own.
- **Test.** Four windows, each scored with a model trained only on data before it:
  - 2023 summer
  - 2024 heatwave
  - 2026 early monsoon
  - 2026 crisis (Aug to Sep)
- **80% range.** Taken from the blend's real misses in those windows:
  - grouped by the average cut over the past 7 days (4 levels) and by day ahead
  - only allowed to widen as the days go on
  - held the actual value 81% of the time

  All test windows were in summer, so in winter the range is on the cautious side.
- **Cut risk.** The share of the last 28 days on which that hour had a cut of 500 MW or more.

### Results (27,622 test hours)

| Method | Average miss (MW) | Hours with 500 MW+ cut caught |
|---|---|---|
| Same hour last week | 735 | 60% |
| 4-week hour average | 648 | 75% |
| LightGBM model | 650 | 63% |
| **Blend (final)** | **623** | **82%** |

In the 2026 crisis the plain 4-week average did best. Cuts there followed supply shocks (the LNG terminal fire, the
terminal outage) that the grid's history cannot see. A reliable 7-day outlook needs the supply plan held by the load
dispatch centre.

### Tables (`model.*`)

| Table | What it holds |
|---|---|
| `backtest` | Every test hour: actual, baselines, model, blend, range, cut risk |
| `scorecard` | Scores by window and method |
| `scorecard_all` | Scores for all windows, plus range coverage and the cut-risk Brier score |
| `error_by_horizon` | Average miss by day ahead |
| `range_table` | 80% range offsets by regime and day ahead |
| `forecast_next_week` | Live forecast from the latest midnight |
| `feature_importance` | What the model leans on |
