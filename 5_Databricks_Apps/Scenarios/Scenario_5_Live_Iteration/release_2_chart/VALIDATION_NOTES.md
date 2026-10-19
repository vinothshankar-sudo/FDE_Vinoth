# Release 2: chart of differing rows

Scenario 5.5, change 2 of 3. Deployed to the app `fizzco-hub` on 9 October 2026. Builds on release 1 (the chart follows the Status filter).

## Change

| Item | Detail |
|---|---|
| What the user sees | Under the Recon table, a bar chart of `diff_rows` for each recon run, with the line "Rows that differ between source and trusted, by recon run (total in this view: N)" |
| Code | `app.py` (Recon tab) and `helpers.py` (`diff_chart_frame`: one column, indexed and sorted by `recon_id`) |
| Behaviour | The chart shows the rows currently shown by the Status filter; with no rows it is not drawn |
| Tests | `test_release.py` (new, chart) and `test_release_1.py` (release 1 checks, kept); earlier test files still pass |

## Validation

| Check | Expected | Seen | Evidence |
|---|---|---|---|
| Offline: chart table | 13 bars in id order, values equal the table's `diff_rows`, total 3, only `RECON-0009` above 0 | All pass | terminal output |
| Live: All | "Showing 13 of 13 rows", one bar at `RECON-0009` with height 3, line says total 3 | As expected; the other 12 runs have no visible bar (value 0) | `01_chart_all_one_bar_total_3.png` |
| Live: MISMATCH | "Showing 1 of 13 rows", one bar `RECON-0009` height 3, total 3 | As expected | `02_chart_mismatch_one_bar.png` |
| Live: MATCH | "Showing 12 of 13 rows", total 0, no bars, 12 run labels without `RECON-0009` | As expected | `03_chart_match_total_0.png` |
| Chart equals table | Bar at the run whose `diff_rows` is 3 (`RECON-0009`, 63 source rows, 60 trusted rows) | Same run, same value as in the table and the source CSV | screenshots 01 and 02 |
| Release 1 still works | Filter counts 13, 12, 1 | Same as release 1 | screenshots 01 to 03 |

## Limits

- The chart has no value labels: the number 3 is read from the axis and the line above it.
- In the MISMATCH view the single bar fills most of the width; this is how the chart sizes one bar, not an error.
- In the MATCH view the chart shows only the axis and labels because every value is 0; the line above states the total.
- The first screenshot shows the table scrolled inside its box, so its first rows are hidden; the filter count and the chart are visible.
- The x-axis labels are cut at the bottom edge of two screenshots; the run ids can still be read from the table.
- The chart colour and layout are the Streamlit defaults; no custom design was done.
