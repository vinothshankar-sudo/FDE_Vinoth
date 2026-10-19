---
doc_id: RB-SELL-IN-001
title: Runbook - sell_in load job failure
doc_type: runbook
feed: sell_in
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Runbook: sell_in load job failure

## Purpose and schedule
This runbook covers failures of the pipeline `pl_fizzco_sell_in_load`, which loads sell-in orders (what Fizzco invoiced to retailers). The pipeline copies the file `sell_in_<load_date>.csv` from the SFTP source into the `fizzco-landing` container (folder `raw/sell_in/`) and then runs the notebook `/Fizzco/sell_in_transform` to build the trusted table `trusted_sell_in`. The trusted table adds one column, `net_amount`, which is `gross_amount` minus `discount_amount`. The pipeline runs once a day and takes the parameter `load_date`.

## Symptoms
A sell_in job failure shows up in one of three ways: the pipeline run is marked Failed in the pipeline monitor; the pipeline succeeds but the reconciliation reports MISMATCH; or the trusted row count is lower than the raw row count. Treat all three as a sell_in failure and follow the steps below.

## Triage steps
1. Note the job id (format `JOB-####`) and the load_date of the failed run.
2. Open the failed activity. If `Copy_sell_in_to_raw` failed, the source file is the problem. If `Run_sell_in_transform` failed, the notebook is the problem.
3. Check the parameter `load_date`. It has no default value, so a manual trigger without it fails at the start of the run. Re-trigger with the date in the format YYYY-MM-DD.
4. If both activities succeeded, run the reconciliation: `python3 databricks/recon_utility.py` from the lake folder. A MISMATCH with a small difference usually points to the date window, not to lost data (see the cause list).

## Common causes specific to sell_in
- **Missing source file.** The SFTP folder has no file for the load_date. Ask the sell-in owner to resend the file, then rerun the pipeline. Do not create an empty file.
- **Empty load_date.** The run fails immediately. Rerun with load_date set.
- **End-date filter error.** Reconciliation shows MISMATCH and the rows missing from the trusted count all carry the last day of the window, for example 31 March. Raw and trusted both hold every row; the counting code excluded the end date. This happened on 31 March 2026 (JOB-0049, RECON-0009). The fix is to make the end date inclusive (`<=`, not `<`). See the incident note for sell_in dated 2026-03-31.
- **Bad discount value.** A row where `discount_amount` is larger than `gross_amount` is rejected by the transform and written to the reject file. Send the reject file to the sell-in owner.

## Fix and rerun
Fix the cause first, then rerun the pipeline with the same load_date. A rerun overwrites the trusted rows for that load_date, so it is safe to repeat. After the rerun, run the reconciliation again. Every rerun gets a new job id and a new reconciliation id; write the explanation in the `note` column, for example "rerun after the end-date fix".

## Verify
The job is fixed only when the reconciliation shows status MATCH and diff_rows 0 for the same cut-off date. A green pipeline run alone is not enough.

## Escalation
If the failure is not explained by the causes above, or if the reconciliation still shows MISMATCH after one rerun, raise a ticket in the data-engineering queue with the job id, the load_date, the failed activity name and the reconciliation output. Do not delete rows from the trusted table to make the counts agree.
