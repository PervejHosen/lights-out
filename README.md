# Lights Out

An independent analysis of Bangladesh's 2026 load shedding: when power was cut, who carried it, why it happened,
what the shop closing rules could and could not show, and what would have helped. Built from the grid's own public
hourly data, 2015 to 2026.

Pervej Hosen, independent analysis, using public PGCB and BPDB data. The interactive report is on
[pervejhosen.com](https://pervejhosen.com).

## Findings in brief

- **2026 is the worst year in the public record since 2015.** PGCB estimates about 3,670 GWh lost to load shedding
  by 15 November (1 am to 11 pm), 1.4 times 2023, the previous worst. Cuts landed on 256 of 319 days.
- **The deepest cuts came after midnight.** From June to September, midnight to 3 am averaged about 1,450 MW cut,
  against 920 MW in the 6 to 10 pm evening peak. 61% of the energy lost in 2026 was lost after dark.
- **Mymensingh carried far more than its share.** In BPDB's zone report for 2026 it carried 28% of the load shed
  with 8% of the demand, and it has carried more than its share every year since 2022.
- **Less gas, and the rest could not fill the gap.** In August and September the average cut was about 1,250 MW
  higher than a year earlier. Gas plants produced about 760 MW less; coal and oil added about 1,450 MW. August was
  only about 0.7 °C warmer than in 2025, so heat explains little.
- **The shop closing rules show no effect this data can measure.** None of seven changes moved evening demand
  beyond ordinary week to week swings, with or without the weather taken out.
- **A week ahead is partly forecastable.** A forecast built from public data missed by about 620 MW an hour and
  caught 82% of hours with a cut of 500 MW or more. In the August crisis a plain 4-week average did better.
- **Power at every hour helps most.** 1,000 MW more at every hour would have removed about 63% of the lost energy;
  100 million cubic feet a day more gas, 31% to 43%; 1,000 MW of new solar, about 16%.

Every number above is recomputed a second way by `05_review/verify.py`. `05_review/REVIEW.md` lists each finding
with its check, its range and what it cannot say.

## What this cannot tell you

Load shedding figures are PGCB's grid-level estimates (estimated demand minus generation), not meter readings at
homes, and they miss local faults on the distribution network. Zone figures come from BPDB's daily evening peak
report, which ends on 3 August 2026. The older hourly data has no midnight readings.

## What is here

| Folder | What it holds |
|---|---|
| `01_data/raw/pgcb_portal_2026` | Hourly data collected from the PGCB portal, March to November 2026 |
| `01_data/reference` | 2026 holidays, shop closing rules and supply events, each with a source |
| `02_pipeline` | DuckDB SQL, bronze to silver to gold |
| `03_analysis` | Notebooks: data profile, first answers, forecast scorecard, drivers |
| `04_model` | `forecast.py` (7-day forecast) and `drivers.py` (why, weather, what-if) |
| `05_review` | `verify.py` and `REVIEW.md` |
| `data_pack` | Small CSVs behind the findings, for anyone who wants to check them |
| `tools` | PGCB and weather collectors |
| `10_sources` | Every source cited, with links |

## Rebuild it

Download the two Mendeley datasets listed in `10_sources/sources.md` into `01_data/raw`, then:

```
pip install duckdb pandas numpy lightgbm truststore
python tools/pgcb_collect.py
python tools/weather_collect.py
python 02_pipeline/run.py
python 04_model/forecast.py
python 04_model/drivers.py
python 05_review/verify.py
```

`verify.py` should end with 0 failed.

## Credits and corrections

Data: Power Grid Company of Bangladesh (PGCB) and Bangladesh Power Development Board (BPDB), via the PGCB portal and
Mendeley Data. Weather data by Open-Meteo.com (CC BY 4.0).

Spotted a number or formula that looks wrong? Open an issue or message me through pervejhosen.com. Corrections are
welcome and will be credited.
