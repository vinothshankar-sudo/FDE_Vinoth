# Release 1: status filter on the Recon table

Scenario 5.5, change 1 of 3. Deployed to the app `fizzco-hub` on 9 October 2026.

## Change

| Item | Detail |
|---|---|
| What the user sees | A "Status" choice (All, MATCH, MISMATCH) above the Recon table and the line "Showing X of 13 rows" |
| Code | `app.py` (Recon tab) and `helpers.py` (`status_options`, `filter_recon`) |
| How it works | The table is read from the warehouse once (cached for 5 minutes) and filtered in the app; the choices come from the data, nothing is hard-coded |
| Also changed | `KeyError` is caught in the Recon tab (a missing column shows a message, not a traceback); two older test files picked the first radio button, which is now the Status filter, so they select the "Model call" radio by its label |

## Validation

| Check | Expected | Seen | Evidence |
|---|---|---|---|
| Offline: filter helpers and page | All 13, MATCH 12, MISMATCH 1 (`RECON-0009`), unknown status 0 rows, original table unchanged | All pass (`test_release.py`); earlier tests (`test_helpers.py`, `test_failure_paths.py`, `test_access_tab.py`) still pass | terminal output |
| Live: All | "Showing 13 of 13 rows", newest dates first | As expected | `01_filter_all_13_of_13.png` |
| Live: MATCH | "Showing 12 of 13 rows", every visible row has status MATCH | As expected | `02_filter_match_12_of_13.png` |
| Live: MISMATCH | "Showing 1 of 13 rows": `RECON-0009`, `JOB-0049`, `sell_in`, 2026-03-31, source 63, trusted 60, diff 3 | As expected; matches `gold_recon_results.csv` | `03_filter_mismatch_1_of_13.png` |
| 12 + 1 = 13 | Counts add up | 12 + 1 = 13 | screenshots 02 and 03 |
| No extra warehouse queries after the first page load | One `recon: start` line for this deployment | The newest `recon: start` is 02:48:18 PM CDT (this deployment's page load); no later entry exists after the three choices were clicked. The screenshots carry no time, so I could not match each click to a time | `04_log_recon_start.png` |

## Limits

- The MATCH screenshot shows 11 of its 12 rows (the table is scrolled); the count of 12 comes from the app's own line and from 13 - 1. I did not compare every MATCH row with the CSV.
- The log check is weak: the data is cached for 5 minutes, so a missing second query in that window would happen with or without the filter. It shows no extra queries, not why.
- The row numbers on the left stay those of the full table (the MATCH list starts at 1, not 0); this is how the table is displayed, not an error.
- The filter option list shows only statuses present in the data; with an empty table the page would show only "All".
