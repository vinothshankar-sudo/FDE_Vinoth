---
doc_id: RB-INVENTORY-001
title: Runbook - inventory load job failure
doc_type: runbook
feed: inventory
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Runbook: inventory load job failure

## Purpose and schedule
This runbook covers failures of the pipeline `pl_fizzco_inventory_load`, which loads distribution-centre stock snapshots. The pipeline has three activities in order: `Copy_inventory_to_raw` copies the snapshot file into the `fizzco-landing` container (folder `raw/inventory/`); `Run_inventory_transform` runs the notebook `/Fizzco/inventory_transform` to build `trusted_inventory` (columns: snapshot_date, dc_id, sku, stock_on_hand); and `Archive_Landing_Files` copies the landing files to the archive container `fizzco-raw-archive` (folder `inventory/`). Inventory is the only feed with the archive step. The pipeline takes the parameter `load_date`.

## Symptoms
An inventory job failure shows up as a Failed run, as a reconciliation MISMATCH, or as a stock_on_hand value that looks wrong for a distribution centre.

## Triage steps
1. Note the job id (format `JOB-####`) and the load_date.
2. Open the run and find which of the three activities failed. The recovery is different for each one.
3. If the first activity failed, check that the snapshot file for the load_date exists in the SFTP folder.
4. If the second activity failed, read the notebook error. Most failures are an unknown dc_id or an unknown sku.
5. If only the third activity, `Archive_Landing_Files`, failed, the trusted data is already correct. Do not rerun the whole pipeline.

## Common causes specific to inventory
- **Archive step failed after a successful transform.** The trusted table is complete and the reconciliation is MATCH, but the landing files were not archived. Rerun only the archive activity. Do not delete anything from `fizzco-landing` until the archive copy is confirmed. Be careful with container names: `fizzco-raw-archive` is the archive container; `fizzco-landing` is the landing container. They are different containers and must not be swapped.
- **Missing snapshot.** One distribution centre did not send its snapshot. The trusted table then has fewer rows than expected for that snapshot_date. Ask the warehouse team to resend it.
- **Unknown dc_id or sku.** The transform rejects rows whose dc_id or sku is not in the reference data. Fix the reference data and rerun.
- **Negative stock_on_hand.** A negative value is rejected. Ask the warehouse team to confirm the count.

## Fix and rerun
For a failure in the copy or transform activity, fix the cause and rerun the pipeline with the same load_date; the trusted rows for that snapshot_date are replaced. For a failure in the archive activity only, rerun the archive activity alone.

## Verify
Run the reconciliation. Expect MATCH. Then confirm that the archive folder `inventory/` in `fizzco-raw-archive` holds the file for the load_date.

## Escalation
Raise a ticket in the data-engineering queue with the job id, the load_date and the failed activity name. Mention whether the archive step is the only one that failed.
