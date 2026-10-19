---
doc_id: RB-PROMO-001
title: Runbook - promo load job failure
doc_type: runbook
feed: promo
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Runbook: promo load job failure

## Purpose and schedule
This runbook covers failures of the pipeline `pl_fizzco_promo_load`, which loads promotions. The pipeline copies the promotions file into the `fizzco-landing` container (folder `raw/promo/`) and runs the notebook `/Fizzco/promo_transform` to build `trusted_promo`. The trusted table adds one column, `promo_days`, which is end_date minus start_date. Promotion ids have the format `PROMO-2026-####`. The pipeline takes the parameter `load_date`.

## Symptoms
A promo job failure shows up as a Failed run, as a reconciliation MISMATCH, or as a promotion that is missing from the promotion performance report.

## Triage steps
1. Note the job id (format `JOB-####`) and the load_date.
2. Open the failed activity. `Copy_promo_to_raw` failing means a source file problem; `Run_promo_transform` failing means a notebook problem.
3. Open the reject file written by the transform. Promo rejects are almost always a data-quality problem in the promotion itself, not a pipeline fault.
4. If both activities succeeded, run the reconciliation.

## Common causes specific to promo
- **End date before start date.** A promotion whose end_date is earlier than its start_date cannot have a valid promo_days and is rejected. Ask the promotion owner to correct the dates.
- **Invalid discount.** The discount_pct must be 5, 10, 15 or 20. Any other value is rejected.
- **Unknown retailer or sku.** The retailer_id (R001 to R010) or sku is not in the dimensions. Fix the dimension or the promotion, then rerun.
- **Duplicate promo_id.** Two rows with the same promo_id are treated as one promotion; the later row wins and the earlier row is written to the reject file.
- **Overlapping promotions.** Two promotions for the same sku and retailer that overlap in time are loaded, but the promotion performance gold table will double count baseline units. Flag overlaps to the commercial team.

## Fix and rerun
Correct the source promotion or the dimension, then rerun the pipeline. A promo rerun replaces all trusted promotions for the load_date. Each rerun gets a new job id and reconciliation id.

## Verify
Run the reconciliation and expect MATCH. Then check that the promotion appears in `gold_promo_performance` with a non-null uplift_pct.

## Escalation
Raise a ticket in the data-engineering queue with the job id and the reject file. Promotion data belongs to the commercial team, so copy the promotion owner on the ticket.
