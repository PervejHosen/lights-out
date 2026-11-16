# Notes on the portal data (collected 16 Nov 2026)

**Coverage.** 1 Mar to 15 Nov 2026, 260 days, 6,507 rows: every hour plus the 19:30 evening-peak reading
(and 18:30 on a few days). No missing days.

**Columns that are hidden on the page.**
- `demand_mw_raw`: filled only from 1 Mar to 23 Apr 2026, empty after that.
- `demand_calc_raw`: demand minus generation (matches in 99% of rows); meaningless once demand is empty.
- `loadshed_mw_raw`: filled throughout. Peaks at 3,757 MW (10 Aug 2026), in line with the 3,500 MW-plus peak
  reported for the crisis. Treated as PGCB's grid-level load shedding; still to be checked against the
  downloaded hourly dataset for March 2026.

**Quirks to fix in silver.**
- 12 May 2026 has two 21:00 rows and 11 May only 24 rows: one row is probably mislabelled.
- 31 rows where generation differs from the sum of fuels and imports by more than 100 MW (e.g. 18 Mar 04:00,
  21 Apr 14:00): flag, do not drop.
- 15 Nov 23:00 looks like liquid fuel and coal swapped (4,458 and 524 against about 755 and 4,580 the hour after).

**First look (to confirm later).**

| Month | Avg load shed (MW) | Max (MW) | Share of hours with shedding | Energy shed (GWh) |
|---|---|---|---|---|
| Mar | 36 | 499 | 22% | 28 |
| Apr | 697 | 2,754 | 77% | 523 |
| May | 94 | 1,403 | 52% | 73 |
| Jun | 745 | 3,431 | 97% | 559 |
| Jul | 463 | 2,556 | 95% | 359 |
| Aug | 1,564 | 3,757 | 97% | 1,212 |
| Sep | 1,145 | 3,557 | 99% | 859 |
| Oct | 540 | 3,458 | 71% | 419 |
| Nov (to 15th) | 20 | 791 | 22% | 8 |

July to September, the heaviest shedding fell after midnight (about 1,600 MW on average at 00:00 to 01:00),
not at the evening peak (about 1,000 to 1,100 MW).
