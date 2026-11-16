# Lights Out · Phase 5 review

Every finding we plan to publish, checked against our checklist: **source, range, what it cannot say, neutral
wording**. Numbers were recomputed on their own by `05_review/verify.py`, straight from the silver layer, not from the
tables the notebooks used. Result: **45 checks passed, 0 failed, 0 wording issues** (`findings_checks.csv`).

Status: **kept** as written · **softened** (true but the wording claimed too much) · **corrected** (a fact was wrong)
· **dropped** (not strong enough to publish).

## Rules for every public number

- Load shed is **PGCB's estimate** at grid level (demand estimate minus generation). It is not a measurement of
  outages at homes, and it misses local outages from distribution faults. We say "PGCB estimates" every time.
- Year totals count 1 am to 11 pm only, because the older data has no midnight readings.
- Zone figures are BPDB's daily evening peak report, which ends on 3 Aug 2026.
- Weather is ERA5 reanalysis from Open-Meteo, weighted by each zone's share of demand. It is not station data.
- No blame, no parties, no named officials. Findings, then options, each with who could act.

## The register

| # | Finding, as we will word it | Check | Range or caveat | What it cannot say | Status |
|---|---|---|---|---|---|
| 1 | 2026 is the worst year for load shedding in the public record since 2015: PGCB estimates about 3,670 GWh lost by 15 November, 1.4 times 2023, the previous worst. | F01, F02 | About 3,920 GWh if midnight hours (collected from March) are counted | Energy lost at the customer meter | kept |
| 2 | Cuts on 256 of the 319 days to 15 November. | F03 | | How long each home was without power | kept |
| 3 | The deepest hour of 2026: 3,757 MW at 1 am on 10 August. | F04 | Not a record: 4 Oct 2022, the day of the national grid failure, shows 5,443 MW | | softened (never call it a record) |
| 4 | August was the worst month, about 1,160 GWh. | F05 | | | kept |
| 5 | From June to September the deepest cuts came after midnight: 1,450 MW on average from midnight to 3 am, against 920 MW from 6 to 10 pm. | F06 | | Which feeders were cut | kept |
| 6 | 61% of 2026's lost energy was after dark (6 pm to 7 am). Solar peaked at 796 MW, so more solar alone cannot reach most of the gap. | F07, F08 | 62% if "dark" means solar under 50 MW | | softened: the "26.6 GWh of storage a night" line is **dropped**; storage needs spare power to charge, which the data does not show |
| 7 | At night demand stays above 15,000 MW until 3 am, while oil plants step down from about 2,840 MW at 10 pm to about 1,350 MW at 5 am; gas, coal and imports stay flat. | F17 | Jun to Oct 2026 averages | **Why** oil is stepped down (cost, fuel stock, plant limits): a question for the load dispatch centre | kept as an observation and a question |
| 8 | The Mymensingh zone carried 28% of zone load shed in 2026 with 8% of demand, 3.4 times its share. It has carried more than its share every year since 2022 (2.8 to 4.9 times). Dhaka carried 16% with 36% of demand. | F09 | BPDB evening peak figures, to 3 Aug 2026 | Why (network limits, allocation rules, local supply); no intent implied | kept |
| 9 | August and September 2026 against 2025: the average cut rose by about 1,250 MW. Gas plants produced about 760 MW less; coal and oil plants added about 1,450 MW; imports barely moved. | F11, F12 | Exact identity, nothing modelled | | kept |
| 10 | Reported demand in August and September was about 2,000 MW above what weather and normal growth expect, while the peak the grid actually served was close to it (about 300 MW above). | F13c, F13d | Typical miss of the weather fit is about 840 MW a day | Whether the gap is real unmet demand or a high estimate | softened: "demand rose 2,468 MW" is no longer quoted as a fact |
| 11 | Each °C of "feels like" temperature above 30 °C adds about 270 MW to peak demand (2023 to 2025). August 2026 was only about 0.7 °C warmer than August 2025, worth under 200 MW. | F13, F13b | 270 to 330 MW per °C depending on the measure | | corrected: replaces the Phase 2 figure of 331 MW per °C (Dhaka air temperature only) |
| 12 | After the crisis, the grid served 800 to 900 MW of new load beyond weather and growth. | | Peak-based check shows only about 300 MW in October, inside normal error | | **dropped**: not robust |
| 13 | Supply shocks: QatarEnergy force majeure on 4 March; fire at the Excelerate terminal on 21 July (about 450 million cubic feet a day lost); partial restart on 6 August; Summit terminal carrier unable to berth around 12 August. | sources | | | corrected: Qatar date was "to confirm" and one secondary source said 23 July; the mall rule date is 1 June, not September |
| 14 | None of the seven shop closing changes moved evening demand by more than normal week to week swings, with or without weather taken out. The April rules point the expected way (about 510 MW lower). This data cannot show an effect; meter data from shops could. | F14 | Normal swing −643 to +567 MW | That the rules did not work | kept, worded as "cannot show", never "did not work" |
| 15 | A 7-day forecast from public data misses by about 620 MW an hour on average, against 650 for a simple 4-week average, and flags 82% of hours with a 500 MW+ cut. In the 2026 crisis the simple average did better: history cannot see supply shocks. | F15 | 80% range held 81% of the time | That the load dispatch centre forecasts badly | kept |
| 16 | Bad days come in runs: in 2026, after a day with a peak cut above 1,500 MW, the next day was also above it 85% of the time. | F10 | 74% across 2022 to 2026 | | softened: always give both figures |
| 17 | 1,000 MW more at every hour, from any source, would have removed about 63% of 2026's lost energy. | F16a | Applied to the real 2026 hours; ignores grid limits | Cost or feasibility | kept |
| 18 | 100 million cubic feet a day more gas for power plants would have removed about 37% of 2026's lost energy. | F16b, F16c | 31% to 43% (3.6 to 5.7 MW per mmcfd) | Where the gas would come from | softened: always shown with the range |
| 19 | 1,000 MW of new solar would have removed about 16% and left the worst hour unchanged. 500 MW saved from 6 to 10 pm would have removed about 9%. | what-if | | | kept |
| 20 | "Every 100 MW less gas generation went with 53 MW more load shed." | | Regression confounded by coal and oil filling in | | **dropped**: replaced by 9 and 18 |
| 21 | On lighter days the first hour cut is 6 pm (76% of light days). | F18 | Light day: peak cut under 1,000 MW | | kept |
| 22 | In the 2026 monsoon every work shift was cut almost daily; the lightest was 6 am to 2 pm (about 720 MW on average), the heaviest 10 pm to 6 am (about 1,210 MW). | F19 | | | kept |

## Fixed during review

- Question numbers in the drivers notebook now match the plan (Q11 why, Q2 and Q4 levers, Q7 night).
- Labels that a reader sees no longer use dashes: "Monsoon (Jun to Sep)", "Night shift 10 pm to 6 am" and so on.
  The pipeline was rerun.
- `policy_events_2026.csv` and `10_sources/sources.md` were updated with dated, sourced supply events.

## Open questions for the brief (not findings)

1. Why oil output is stepped down overnight while demand stays high.
2. How load shedding is allocated between zones, and why Mymensingh's share stays high.
3. Whether PGCB's demand estimate in a crisis is published with its method.
4. Petrobangla's daily gas allocation to power, to replace our engineering conversion.
