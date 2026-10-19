---
doc_id: POL-RECON-001
title: Reconciliation policy
doc_type: policy
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Reconciliation policy

## Purpose
Reconciliation proves that nothing was lost between the raw and trusted layers. It compares the number of rows in the raw data with the number of rows in the trusted table for the same feed and the same date window. This policy applies to all four feeds: sell_in, sell_out, inventory and promo.

## Rules
1. **Window.** The window starts on 1 January 2026 and ends on the cut-off date. The cut-off date is inclusive: rows dated on the cut-off date are counted on both sides.
2. **Cut-off dates.** A reconciliation is run at every month end (31 January, 28 February, 31 March) and after every rerun.
3. **Tolerance.** The accepted difference is zero rows. A difference of one row or more is a MISMATCH, however small.
4. **Result record.** Every run writes one line to the reconciliation results with a reconciliation id (format `RECON-####`), the job id (format `JOB-####`), the feed, the cut-off date, the row counts, the difference, the status and a note.
5. **Notes.** The note is mandatory for every MISMATCH and for every rerun. It must say what caused the difference or why the rerun was needed.
6. **Reruns.** A rerun is a new job with a new job id and a new reconciliation id. The old result is never edited or deleted, so the history shows both the failure and the fix.
7. **No cosmetic fixes.** Never delete or add rows in the trusted table only to make the counts agree.
8. **Sign-off.** A MISMATCH is closed only when a rerun shows MATCH. The data owner signs off the closure.

## Investigating a MISMATCH
Work through the checks in this order, stopping at the first one that explains the difference:
1. **Date window.** Count the rows dated on the cut-off date in raw and in trusted. If that number equals the difference, the end-date filter is the suspect. This was the cause of RECON-0009 on 31 March 2026.
2. **Duplicates.** Look for duplicate keys in the raw data that the transform collapsed. Document the number in the note.
3. **Rejects.** Count the rows in the reject file for the load. Rejected rows explain a lower trusted count and must be reported to the feed owner.
4. **Missing source rows.** Compare the file names and row counts of the source files with the raw layer.

## Reporting
The reconciliation results feed the migration health view. A feed is healthy for a cut-off date when its latest reconciliation for that date is MATCH. A quarter is clean when every feed is healthy at the last cut-off date of the quarter.
