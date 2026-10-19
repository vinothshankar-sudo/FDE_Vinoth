---
doc_id: RB-SELL-OUT-001
title: Runbook - sell_out load job failure
doc_type: runbook
feed: sell_out
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Runbook: sell_out load job failure

## Purpose and schedule
This runbook covers failures of the pipeline `pl_fizzco_sell_out_load`, which loads sell-out data: units and value that retailers sold to shoppers, taken from retailer scan files. The pipeline copies `sell_out_<load_date>.csv` into the `fizzco-landing` container (folder `raw/sell_out/`) and runs the notebook `/Fizzco/sell_out_transform` to build `trusted_sell_out` (columns: sale_date, retailer_id, sku, units, sale_amount). Sell-out is the largest feed: the trusted table has more rows than any other feed. The pipeline runs once a day and takes the parameter `load_date`.

## Symptoms
A sell_out job failure shows up as a Failed pipeline run, a reconciliation MISMATCH, or a retailer that has no sell-out rows for a week in which it had sell-in.

## Triage steps
1. Note the job id (format `JOB-####`) and the load_date.
2. Open the failed activity. `Copy_sell_out_to_raw` failing means a source file problem; `Run_sell_out_transform` failing means a notebook problem.
3. Check which retailers are in the file. Every active retailer (R001 to R010) should appear at least once per week. A missing retailer means a late scan file, not a pipeline fault.
4. If both activities succeeded, run the reconciliation and compare source and trusted rows.

## Common causes specific to sell_out
- **Late retailer scan file.** One retailer sends its file after the daily run. The pipeline succeeds but that retailer is absent. Wait for the file, then rerun with the same load_date.
- **Duplicate scan lines.** The same sale_date, retailer_id and sku appears twice in the raw file. The transform keeps one line and writes the duplicates to the reject file, so the trusted count is lower than the raw count by the number of duplicates. This is expected; record the number in the reconciliation note.
- **Negative units.** Returns are sent as negative units by some retailers. The transform rejects negative units. Ask the retailer owner whether the return should be sent through the returns process instead.
- **Unknown sku.** A sku that is not in the product dimension is rejected. Add the sku to the product dimension first, then rerun.

## Fix and rerun
Fix the cause, then rerun the pipeline for the same load_date. The sell_out rerun is idempotent: it replaces the trusted rows for the load_date. Each rerun gets a new job id and reconciliation id.

## Verify
Run the reconciliation. The expected status is MATCH with diff_rows 0, or a documented difference that equals the rejected duplicates. A difference with no explanation is a MISMATCH and must be escalated.

## Escalation
Raise a ticket in the data-engineering queue with the job id, the load_date and the list of retailers missing from the file. Do not edit the trusted table by hand.
