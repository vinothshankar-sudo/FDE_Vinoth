---
doc_id: INC-2026-03-31-001
title: Incident note - sell_in reconciliation mismatch on 31 March 2026
doc_type: incident
feed: sell_in
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Incident note: sell_in reconciliation mismatch on 31 March 2026

## Summary
On 31 March 2026 the quarter-end reconciliation for the sell_in feed (job JOB-0049, reconciliation RECON-0009) reported MISMATCH. The source had 63 rows, the trusted table was counted as 60, and the difference was 3 rows. No data was lost. The cause was an off-by-one error in the date filter used to count trusted rows: the end date of the window was excluded. The three rows dated 2026-03-31 were in the trusted table but were not counted. The rerun, job JOB-0053 with reconciliation RECON-0013, showed 63 and 63 with status MATCH.

## Timeline
| Step | What happened |
|---|---|
| Reconciliation run | JOB-0049 compared raw and trusted sell_in rows from 2026-01-01 to 2026-03-31 and reported source 63, trusted 60, diff 3, MISMATCH (RECON-0009) |
| Same-day checks | The other three feeds reconciled with MATCH on the same date: sell_out JOB-0050 (127 rows), inventory JOB-0051 (40 rows), promo JOB-0052 (12 rows) |
| Diagnosis | Raw and trusted files both held 63 rows. The two counting functions in `recon_utility.py` treated the end date differently: the source count used `<=` and the trusted count used `<` |
| Fix | One character changed: `<` to `<=` in `count_trusted_rows` |
| Rerun | JOB-0053 reran the sell_in reconciliation and reported MATCH with 63 and 63 (RECON-0013), note "rerun after the end-date fix" |

## Root cause
The trusted-row counter filtered with `d < end` while the source-row counter filtered with `d <= end`. A reconciliation window is inclusive of its end date, so rows dated on the last day were dropped from the trusted count only. The pattern is easy to spot: the missing rows all carry the last day of the window, and the number of missing rows equals the number of rows on that day.

## How it was verified
Four tests were written first. On the old code 3 of the 4 failed; after the one-character fix all 4 passed. One of the tests runs the reconciliation on the real raw and trusted files and expects MATCH with 63 and 63. Another test confirms that a genuinely missing row still produces a MISMATCH, so the fix does not hide real data loss.

## What to do if it happens again
If a reconciliation shows a small MISMATCH on a month-end or quarter-end date, count the rows dated on the last day of the window in both raw and trusted. If that number equals the difference, suspect the end-date filter before suspecting data loss. Follow the sell_in runbook and use the reconciliation policy for the rerun rules.
