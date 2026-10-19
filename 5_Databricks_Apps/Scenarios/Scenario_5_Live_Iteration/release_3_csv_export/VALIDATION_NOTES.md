# Release 3: CSV export of the rows shown

Scenario 5.5, change 3 of 3. Deployed to the app `fizzco-hub` on 9 October 2026. Builds on releases 1 and 2 (the file holds the rows chosen by the Status filter).

## Change

| Item | Detail |
|---|---|
| What the user sees | A button under the chart: "Download CSV (N rows)" |
| Code | `app.py` (Recon tab) and `helpers.py` (`to_csv_bytes`, `export_filename`) |
| Behaviour | The file holds exactly the rows shown, with a header line, UTF-8, no row-number column; the file name says which rows: `recon_status_all.csv`, `recon_status_match.csv`, `recon_status_mismatch.csv` |
| Tests | `test_release.py` (new, export) plus `test_release_1.py` and `test_release_2.py` (kept) and the earlier test files |

## Validation

| Check | Expected | Seen | Evidence |
|---|---|---|---|
| Offline: export content | All 13, MATCH 12, MISMATCH 1 data rows, 8 columns, no row-number column, every value equals the table; MISMATCH file text is `RECON-0009,JOB-0049,sell_in,2026-03-31,63,60,3,MISMATCH` after the header; safe file names; header-only file for an empty selection | All pass | terminal output |
| Offline: page | One download button, labelled "(13 rows)", then "(1 row)" after choosing MISMATCH | Pass | terminal output |
| Live: button with All | "Download CSV (13 rows)" | As expected | `01_button_all_13_rows.png` |
| Live: button with MATCH | "Download CSV (12 rows)" | As expected | `02_button_match_12_rows.png` |
| Live: button with MISMATCH | "Download CSV (1 row)" | As expected | `03_button_mismatch_1_row.png` |
| Release 1 and 2 still work | Filter counts 13, 12, 1; chart total 3, 0, 3 | Same as in releases 1 and 2; seen again in the three screenshots above | screenshots 01 to 03 |

## Limits

- **The downloaded file was not opened and screenshotted in the live app.** What the file contains is proved only by the offline tests, which run the same two helper functions the button uses; the live check covers the button and its label, not the bytes the browser saved.
- The file names and the browser's download behaviour were not checked live.
- The screenshots are cropped at the right edge of the page; the page itself was not damaged.
- The export is the unfiltered column set (8 columns); the `note` column of the source CSV is not part of the table, so it is not in the export.
- Spreadsheet programs can treat a cell that starts with `=`, `+`, `-` or `@` as a formula. The data here is synthetic and has no such values; a real deployment would need to guard against it.
