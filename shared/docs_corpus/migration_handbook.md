---
doc_id: HB-MIGRATION-001
title: Migration operations handbook
doc_type: handbook
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Migration operations handbook

## 1. Architecture in one page
Fizzco is retiring its legacy warehouse and moving four feeds into a lake with three layers. Files arrive from retailers and internal systems by SFTP. A pipeline copies each file into the landing container `fizzco-landing`, in a folder named `raw/<feed>/`. This is the raw layer: files exactly as received. A Databricks notebook then reads the raw files, applies the cleaning rules and writes the trusted tables: `trusted_sell_in`, `trusted_sell_out`, `trusted_inventory` and `trusted_promo`. Gold tables are built on top of the trusted tables for reporting: `gold_sell_in_vs_sell_out`, `gold_promo_performance` and `gold_recon_results`. Analysts and managers read only the gold layer. Data engineers work in all three layers.

The four feeds are sell_in (orders invoiced to retailers), sell_out (retailer scan data), inventory (distribution-centre stock snapshots) and promo (promotions). The container name `fizzco-landing` was previously `fizzco-raw`; the container `fizzco-raw-archive` is a different container that holds archived files only.

## 2. Naming conventions
Pipelines are named `pl_fizzco_<feed>_load`, for example `pl_fizzco_promo_load`. Notebooks are stored under `/Fizzco/` and named `<feed>_transform`. Identifiers follow fixed formats: objects `OBJ-###`, jobs `JOB-####`, reconciliations `RECON-####`, promotions `PROMO-2026-####`, retailers `R###`. Regions are always East or West. Code and documents use the exact feed names sell_in, sell_out, inventory and promo, with the underscore.

## 3. The daily run
Each feed has one file per load date, named `<feed>_<load_date>.csv`, with the date written as YYYY-MM-DD. The daily run processes the feeds in a fixed order: sell_in, sell_out, inventory, promo. The same order is used for reconciliation, so reconciliation ids for one cut-off date run in that order. The load date is always passed to the pipeline as the parameter `load_date`; the parameter has no default.

Every run produces a job id. The job id is the key that links a pipeline run to its reconciliation result. When a support engineer reports a failure, the first question is always "what is the job id and the load date?"

## 4. Reject files
When a notebook cannot accept a row, it does not stop the whole load. It writes the row to a reject file for that feed and load date and carries on. Rejected rows are therefore a normal reason for the trusted table to hold fewer rows than the raw file. Every reject must be explained in the reconciliation note. The feed owners are: the sell-in owner for sell_in, the retailer owner for sell_out, the warehouse team for inventory and the commercial team for promo. A reject file is always sent to the feed owner, never fixed by hand in the trusted table.

## 5. Access and roles
Data engineers can trigger and rerun pipelines and can read every layer. Analysts can read the gold tables and ask questions through the analytics assistant. Regional managers see only their own region: an East manager sees East rows and a West manager sees West rows. This is enforced by a row filter on the gold tables, not by separate copies of the data. Nobody edits trusted or gold tables by hand; corrections are made at the source and the pipeline is rerun.

## 6. Reruns in practice
A rerun uses the same load date as the failed run and replaces the trusted rows for that date, so it is safe to repeat. A rerun is a new job with a new job id. After every rerun the reconciliation is run again and the result is recorded with a new reconciliation id and a note. The old failed result stays in the history. A failure is closed only when a rerun reconciles with MATCH.

## 7. Frequently asked questions
**What is a MATCH?** A reconciliation where the source rows and the trusted rows for the window are equal, so the difference is zero.

**What is a MISMATCH?** Any difference at all between source and trusted rows. There is no tolerance.

**A reconciliation shows a difference of three rows on a month end. Where do I look first?** Count the rows dated on the last day of the window in raw and in trusted. If the count equals the difference, suspect the end-date filter.

**Is it safe to rerun a pipeline?** Yes. A rerun replaces the trusted rows for the load date and never appends duplicates.

**Which container holds archived inventory files?** `fizzco-raw-archive`, in the folder `inventory/`. Only the inventory pipeline has an archive step.

**Who owns promotion data?** The commercial team. Copy the promotion owner on any ticket about a promo reject.

**Where do I find the history of a reconciliation?** In the reconciliation results table `gold_recon_results` and in the Q1 2026 job register.

**What does the load_date look like?** A date in the format YYYY-MM-DD, for example 2026-03-31.

**Do the pipelines retry on their own?** No. There is no automatic retry, no timeout policy and no failure alert. A failed run waits for a person.

**Which regions exist?** East and West.

## 8. Known gaps
The pipelines have no retry or timeout settings and no alert on failure, and the trusted target is not recorded in the pipeline definition. The container and notebook paths are fixed in the pipeline definitions rather than passed as parameters. These gaps are listed in the lineage documents and are accepted for the migration period.
