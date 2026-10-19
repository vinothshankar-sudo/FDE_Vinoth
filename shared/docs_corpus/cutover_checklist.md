---
doc_id: CHK-CUTOVER-001
title: Cutover checklist - retire the legacy warehouse
doc_type: checklist
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Cutover checklist: retire the legacy warehouse

## Before cutover (five working days ahead)
- [ ] All four feeds (sell_in, sell_out, inventory, promo) have a reconciliation with status MATCH for the latest month end. A MISMATCH that has a MATCH rerun counts as closed.
- [ ] The object inventory has been validated with its five rules: all template columns present, unique object ids (format `OBJ-###`), every dependency exists, object type is Pipeline, Notebook or Table, and status is Active or Retired.
- [ ] The storage container name is `fizzco-landing` in every pipeline, notebook and configuration file. The container `fizzco-raw-archive` is archive only and keeps its name.
- [ ] The lineage documents are current and mention the archive step for inventory.
- [ ] The runbooks for sell_in, sell_out, inventory and promo, and the general first-response runbook, have been reviewed in the last 30 days.
- [ ] Row-level access is tested: an East manager sees only East data and a West manager sees only West data.

## Cutover day
- [ ] Freeze changes to the pipelines.
- [ ] Run the daily load for each feed with the load_date set explicitly. The parameter has no default value.
- [ ] Run the reconciliation for each feed and record the job id and reconciliation id.
- [ ] Do not proceed if any feed shows MISMATCH. Use the runbook for that feed, rerun, and reconcile again.
- [ ] Confirm that the archive step for inventory finished and that the archive folder holds the landing files.

## After cutover (first working day)
- [ ] Compare the first gold tables with the legacy reports for one region and one week.
- [ ] Keep the legacy warehouse read-only for 30 days before it is switched off.
- [ ] Record the outcome and any open risks in the migration log.

## Rollback
If a Sev 1 problem is found on cutover day, stop the loads, keep the legacy warehouse as the source of truth and raise a ticket in the data-engineering queue. Nothing is deleted from the legacy warehouse during cutover.
